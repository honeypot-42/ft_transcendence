"""Unit tests for the attack simulator.

The event format is the contract with Logstash, so these tests check it.
Run them from this folder with: python3 -m unittest -v
"""

import argparse
import ipaddress
import os
import random
import re
import signal
import tempfile
import threading
import time
import unittest
from unittest import mock

import simulate_attacks as sim

COMMON_FIELDS = {"eventid", "timestamp", "session", "src_ip", "src_port", "dst_port", "protocol", "sensor"}
KINDS = ["scan", "login", "intrusion", "burst"]
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


def drain(session):
    """Return every event of a session, in order."""
    events = []
    while not session.done:
        events.append(session.next_event())
    return events


class SessionFormatTest(unittest.TestCase):
    def setUp(self):
        random.seed(42)  # same sessions on every run
        self.sessions = [drain(sim.Session(kind)) for kind in KINDS for _ in range(200)]
        self.events = [event for session in self.sessions for event in session]

    def test_session_starts_with_connect_and_ends_with_closed(self):
        for events in self.sessions:
            self.assertEqual(events[0]["eventid"], "cowrie.session.connect")
            self.assertEqual(events[-1]["eventid"], "cowrie.session.closed")

    def test_every_event_has_common_fields(self):
        for event in self.events:
            missing = COMMON_FIELDS - set(event)
            self.assertFalse(missing, "%s is missing %s" % (event["eventid"], sorted(missing)))

    def test_event_specific_fields(self):
        required = {
            "cowrie.login.failed": {"username", "password"},
            "cowrie.login.success": {"username", "password"},
            "cowrie.command.input": {"input"},
            "cowrie.session.file_download": {"shasum", "url"},
        }
        seen = set()
        for event in self.events:
            fields = required.get(event["eventid"])
            if fields:
                seen.add(event["eventid"])
                self.assertTrue(fields <= set(event), "%s is missing %s" % (event["eventid"], fields))
        self.assertEqual(seen, set(required), "some event types were never generated")

    def test_ips_are_public(self):
        for event in self.events:
            self.assertTrue(ipaddress.ip_address(event["src_ip"]).is_global, event["src_ip"])

    def test_every_prefix_is_public(self):
        # Lowest and highest address random_ip() can build from each prefix.
        for prefix in sim.IP_PREFIXES:
            for suffix in ("1.1", "254.254"):
                ip = "%s.%s" % (prefix, suffix)
                self.assertTrue(ipaddress.ip_address(ip).is_global, ip)


class NowUtcTest(unittest.TestCase):
    def setUp(self):
        # now_utc() remembers the last timestamp: restore it after each test.
        self.addCleanup(setattr, sim, "_last_us", sim._last_us)

    def assert_strictly_increasing(self, stamps):
        for previous, current in zip(stamps, stamps[1:]):
            self.assertLess(previous, current)

    def test_format(self):
        self.assertRegex(sim.now_utc(), TIMESTAMP)

    def test_strictly_increasing(self):
        self.assert_strictly_increasing([sim.now_utc() for _ in range(1000)])

    def test_strictly_increasing_when_the_clock_does_not_advance(self):
        sim._last_us = None
        frozen = 1794848400 * 10**9  # 2026-11-16T17:00:00Z, in nanoseconds
        with mock.patch.object(sim.time, "time_ns", return_value=frozen):
            stamps = [sim.now_utc() for _ in range(1000)]
        self.assertEqual(stamps[0], "2026-11-16T17:00:00.000000Z")
        self.assertEqual(stamps[-1], "2026-11-16T17:00:00.000999Z")
        self.assert_strictly_increasing(stamps)

    def test_strictly_increasing_when_the_clock_goes_back(self):
        before = sim.now_utc()
        with mock.patch.object(sim.time, "time_ns", return_value=0):
            after = sim.now_utc()
        self.assertLess(before, after)


class ParseRateTest(unittest.TestCase):
    def test_accepts_limits(self):
        self.assertEqual(sim.parse_rate("1"), 1)
        self.assertEqual(sim.parse_rate("1000"), 1000)

    def test_rejects_invalid_values(self):
        for value in ("0", "1001", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    sim.parse_rate(value)


class RotateTest(unittest.TestCase):
    def test_rotate_keeps_old_content_and_starts_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "cowrie.json")
            fh = sim.open_log(output)
            fh.write('{"eventid":"old"}\n')
            with mock.patch("builtins.print"):
                fh = sim.rotate(fh, output)
            fh.close()

            with open(output + ".1", encoding="utf-8") as rotated:
                self.assertEqual(rotated.read(), '{"eventid":"old"}\n')
            self.assertEqual(os.path.getsize(output), 0)

    def test_rotate_replaces_previous_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "cowrie.json")
            with open(output + ".1", "w", encoding="utf-8") as old:
                old.write("previous\n")
            fh = sim.open_log(output)
            fh.write("current\n")
            with mock.patch("builtins.print"):
                sim.rotate(fh, output).close()

            with open(output + ".1", encoding="utf-8") as rotated:
                self.assertEqual(rotated.read(), "current\n")


class RunLoopTest(unittest.TestCase):
    def setUp(self):
        sim._stop_event.clear()
        self.addCleanup(sim._stop_event.clear)

    def test_one_event_per_wait_and_pause_below_healthcheck(self):
        """The healthcheck fails after 120 s without writes."""
        random.seed(7)
        waits = []

        def fake_wait(seconds):
            waits.append(seconds)
            if len(waits) >= 300:
                sim._stop_event.set()

        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "cowrie.json")
            with mock.patch.object(sim._stop_event, "wait", fake_wait), mock.patch("builtins.print"):
                sim.run("stress", sim.MIN_RATE, output)
            with open(output, encoding="utf-8") as fh:
                lines = fh.read().splitlines()

        self.assertEqual(len(lines), len(waits))
        self.assertLessEqual(max(waits), 60.0 / sim.MIN_RATE * 1.3)
        self.assertLess(max(waits), 120)

    @unittest.skipIf(os.name == "nt", "POSIX signals only")
    def test_sigterm_stops_at_once_at_the_minimum_rate(self):
        """docker compose stop sends SIGKILL 10 s after SIGTERM."""
        previous = signal.signal(signal.SIGTERM, sim.stop)
        self.addCleanup(signal.signal, signal.SIGTERM, previous)
        timer = threading.Timer(0.2, os.kill, (os.getpid(), signal.SIGTERM))

        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "cowrie.json")
            started = time.monotonic()
            timer.start()
            with mock.patch("builtins.print") as printed:
                sim.run("basic", sim.MIN_RATE, output)  # waits 42-78 s between events
            elapsed = time.monotonic() - started
            timer.join()

        self.assertLess(elapsed, 5)
        self.assertIn("stopped after", printed.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
