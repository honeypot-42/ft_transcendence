# Attack Simulator

A small Python program that writes **fake honeypot events in the exact format of Cowrie** to a shared log file. It lets the whole SENTINEL pipeline run (and be evaluated) on any machine without exposing a real honeypot to the internet.

> **Status:** design document. The interface below is the contract agreed with the data pipeline (Logstash). The implementation is tracked in issue #25.

## Why it exists

The simulator decouples the teams. Nobody waits for real attacks:

```
simulator ──writes──► volume honeypot_logs/cowrie.json ──reads──► Logstash ──► Elasticsearch ──► backend ──► frontend
```

Because the events have the same shape as real Cowrie logs, the pipeline is identical with simulated and real data. In the VPS deployment the simulator is simply not started and Cowrie writes the same file.

## Output

| Item | Value |
|------|-------|
| File | `/var/log/honeypot/cowrie.json` |
| Format | JSON Lines: one complete JSON object per line, UTF-8 |
| Volume | `honeypot_logs` (the simulator writes, Logstash mounts it **read-only**) |
| Network | `network_mode: none`: the simulator has no network access |

Every line is flushed immediately so Logstash (file input) picks it up in real time. The file is only ever appended to.

## Modes

| Mode | Rate | Use |
|------|------|-----|
| `basic` | ~10 events/min | Daily development |
| `enriched` | ~30 events/min | Demos and evaluation: more countries, brute-force bursts, commands |
| `stress` | ~200 events/min | Load tests (the dashboard must hold 200 events/min) |

## Usage (planned interface)

```bash
python simulator.py --mode basic
python simulator.py --mode enriched --output /var/log/honeypot/cowrie.json
```

| Option | Env variable | Default | Description |
|--------|--------------|---------|-------------|
| `--mode` | `SIM_MODE` | `basic` | `basic`, `enriched` or `stress` |
| `--output` | `SIM_OUTPUT` | `/var/log/honeypot/cowrie.json` | Log file to append to |

In Docker Compose the mode is selected with `SIM_MODE`, so no external key or manual step is needed.

## Event format

The simulator reproduces the fields of Cowrie's JSON log. Common fields on every event:

| Field | Example | Notes |
|-------|---------|-------|
| `eventid` | `cowrie.login.failed` | Event type (see below) |
| `src_ip` | `198.51.100.23` | Attacker IP |
| `src_port` | `51234` | |
| `dst_ip` | `172.18.0.2` | Honeypot IP |
| `dst_port` | `2222` | |
| `session` | `a1b2c3d4e5f6` | Shared by all events of one attack session |
| `protocol` | `ssh` | `ssh` or `telnet` |
| `sensor` | `honeypot-sim` | Sensor name |
| `message` | `login attempt [root/123456] failed` | Human-readable summary |
| `timestamp` | `2026-10-30T10:15:42.123456Z` | ISO 8601, UTC |

### Event types

The pipeline derives severity and the MITRE ATT&CK technique from `eventid`, so the simulator must emit all of these:

| `eventid` | Extra fields | Severity | MITRE technique |
|-----------|--------------|----------|-----------------|
| `cowrie.session.connect` | | low | T1046 |
| `cowrie.client.version` | `version` | n/a | n/a |
| `cowrie.login.failed` | `username`, `password` | low | T1110.001 |
| `cowrie.login.success` | `username`, `password` | medium | T1078 |
| `cowrie.command.input` | `input` | high | T1059.004 |
| `cowrie.session.file_download` | `url`, `outfile`, `shasum` | critical | T1105 |
| `cowrie.session.closed` | `duration` | n/a | n/a |

The mapping lives in `elk/logstash/mappings/` and is maintained by the data pipeline owner.

### Example lines

```json
{"eventid":"cowrie.session.connect","src_ip":"198.51.100.23","src_port":51234,"dst_ip":"172.18.0.2","dst_port":2222,"session":"a1b2c3d4e5f6","protocol":"ssh","sensor":"honeypot-sim","message":"New connection: 198.51.100.23:51234","timestamp":"2026-10-30T10:15:42.123456Z"}
{"eventid":"cowrie.login.failed","username":"root","password":"123456","src_ip":"198.51.100.23","session":"a1b2c3d4e5f6","protocol":"ssh","sensor":"honeypot-sim","message":"login attempt [root/123456] failed","timestamp":"2026-10-30T10:15:43.401002Z"}
{"eventid":"cowrie.command.input","input":"uname -a","src_ip":"198.51.100.23","session":"a1b2c3d4e5f6","protocol":"ssh","sensor":"honeypot-sim","message":"CMD: uname -a","timestamp":"2026-10-30T10:15:50.870311Z"}
```

The IPs above are documentation ranges, only to keep this README harmless. The simulator itself uses **real public IP ranges from several countries**, because private or reserved addresses are not geolocated and would leave the map empty.

## Rules the simulator must follow

1. **Valid Cowrie format.** Same field names and types as real Cowrie; a line that breaks the format breaks the pipeline.
2. **Unique events.** Logstash builds `event.id` as a SHA-256 over `session`, `timestamp` and `eventid`, and the real-time cursor (`search_after`) depends on it. Two events must never share all three.
3. **Coherent sessions.** Events of one `session` appear in a realistic order: connect, login attempts, optional commands/download, closed.
4. **Geographic diversity.** Attackers come from many countries, with brute-force bursts (several failed logins from the same IP in a few seconds) in `enriched` and `stress`.
5. **Fake data only.** Credentials and commands come from a built-in list of common attack patterns. No real third-party credentials. `shasum` values are random hashes: **no real malware, no real URLs that serve payloads**.
6. **Hostile-looking content stays text.** Commands may contain things like `<script>alert(1)</script>`; the dashboard must display them escaped (see the security checklist).
7. **Append-only and flushed.** Never truncate or rewrite the log file.

## Verification

Acceptance criteria for the first version:

- `cowrie.json` grows with valid events (each line parses as JSON).
- Logstash indexes them into `logs-honeypot-default` with `source.geo.location`.
- Events show diverse countries on the map.
- `stress` mode sustains 200 events/min without errors.

Quick manual checks inside the container:

```bash
tail -f /var/log/honeypot/cowrie.json
python -c "import json,sys; [json.loads(l) for l in open('/var/log/honeypot/cowrie.json')]; print('all lines valid')"
```

## Ownership

Maintained by **astefane** (backend / DevOps). The event format is a contract with the data pipeline owner (**migugar2**): any change to field names or event types must be agreed with them first.