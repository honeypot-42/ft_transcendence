# Attack Simulator

A small Python program that writes **fake honeypot events in the exact format of Cowrie** to a shared log file. It lets the whole SENTINEL pipeline run (and be evaluated) on any machine without exposing a real honeypot to the internet.

> **Status:** implemented (issue #25). The event format below is the contract with the data pipeline (Logstash).

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

Every line is flushed immediately so Logstash (file input) picks it up in real time. The file is only ever appended to, until it is rotated (see [Rotation](#rotation)).

## Modes

| Mode | Rate | Use |
|------|------|-----|
| `basic` | ~10 events/min | Daily development |
| `enriched` | ~30 events/min | Demos and evaluation: more countries, brute-force bursts, commands |
| `stress` | ~200 events/min | Load tests (the dashboard must hold 200 events/min) |

The mode sets the behaviour (how many sessions run in parallel, how many brute-force bursts) and a default rate. `SIMULATOR_RATE` (or `--rate`) overrides only the rate, so you can, for example, run `enriched` traffic at 100 events/min.

## Usage

```bash
python simulate_attacks.py --mode basic --output ./cowrie.json
python simulate_attacks.py --mode enriched --output /var/log/honeypot/cowrie.json
python simulate_attacks.py --mode stress --rate 500 --output ./cowrie.json
```

| Option | Env variable | Default | Description |
|--------|--------------|---------|-------------|
| `--mode` | `SIMULATOR_MODE` | `basic` | `basic`, `enriched` or `stress` |
| `--rate` | `SIMULATOR_RATE` | rate of the mode | Events per minute, integer from 1 to 1000. Empty means "use the mode's rate" |
| `--output` | `OUTPUT_FILE` | `/var/log/honeypot/cowrie.json` | Log file to append to |

Command-line options take precedence over the environment variables. An invalid mode or rate stops the simulator at start-up with a clear error instead of running with a wrong value.

No external key or manual step is needed. The output directory is created if it does not exist. Outside Docker, pass `--output` with a path you can write to: the default is under `/var/log`, which normally needs root.

## Docker Compose

```yaml
simulator:
  build:
    context: ./simulator
    dockerfile: Dockerfile
  container_name: transcendence-simulator
  restart: unless-stopped
  network_mode: none
  environment:
    - SIMULATOR_MODE=${SIMULATOR_MODE:-basic}
    - SIMULATOR_RATE=${SIMULATOR_RATE:-}
  volumes:
    - honeypot_logs:/var/log/honeypot
  cap_drop:
    - ALL
  security_opt:
    - no-new-privileges:true
  deploy:
    resources:
      limits:
        memory: 128m
```

Notes:

- `SIMULATOR_MODE` and `SIMULATOR_RATE` come from `.env`. If `SIMULATOR_RATE` is missing or empty, the rate of the mode is used. Keep in mind that a value in `.env` overrides the rate of every mode: to try `stress` at 200 events/min, change or empty `SIMULATOR_RATE` too.
- `network_mode: none`: the simulator has no network. The volume is its only output, as for a real honeypot.
- The image defines a `HEALTHCHECK`: the container is healthy while the log file keeps being written (modified in the last 120 s).
- The container runs as a non-root user (uid 10001). The image creates `/var/log/honeypot` owned by that user, so a new named volume inherits the ownership. Logstash must mount the same volume read-only (`honeypot_logs:/var/log/honeypot:ro`).
- In the development compose Logstash is not started yet, so the file simply grows. This is expected: the first deliverable is a `cowrie.json` with valid events.

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
{"eventid":"cowrie.login.failed","username":"root","password":"123456","src_ip":"198.51.100.23","src_port":51234,"dst_ip":"172.18.0.2","dst_port":2222,"session":"a1b2c3d4e5f6","protocol":"ssh","sensor":"honeypot-sim","message":"login attempt [root/123456] failed","timestamp":"2026-10-30T10:15:43.401002Z"}
{"eventid":"cowrie.command.input","input":"uname -a","src_ip":"198.51.100.23","src_port":51234,"dst_ip":"172.18.0.2","dst_port":2222,"session":"a1b2c3d4e5f6","protocol":"ssh","sensor":"honeypot-sim","message":"CMD: uname -a","timestamp":"2026-10-30T10:15:50.870311Z"}
```

The IPs above are documentation ranges, only to keep this README harmless. The simulator itself uses **real public IP ranges from several countries**, because private or reserved addresses are not geolocated and would leave the map empty.

## Rules the simulator must follow

1. **Valid Cowrie format.** Same field names and types as real Cowrie; a line that breaks the format breaks the pipeline.
2. **Unique events.** Logstash builds `event.id` as a SHA-256 over `session`, `timestamp` and `eventid`, and the real-time cursor (`search_after`) depends on it. Two events must never share all three.
3. **Coherent sessions.** Events of one `session` appear in a realistic order: connect, login attempts, optional commands/download, closed.
4. **Geographic diversity.** Attackers come from many countries, with brute-force bursts (several failed logins from the same IP in a few seconds) in `enriched` and `stress`.
5. **Fake data only.** Credentials and commands come from a built-in list of common attack patterns. No real third-party credentials. `shasum` values are random hashes: **no real malware, no real URLs that serve payloads**.
6. **Hostile-looking content stays text.** Commands may contain things like `<script>alert(1)</script>`; the dashboard must display them escaped (see the security checklist).
7. **Append-only and flushed.** Never truncate or rewrite the log file: rotation renames it.

## Rotation

So the file does not grow without limit (`stress` writes ~85 MB/day), the simulator rotates it when it reaches **50 MB**:

1. It closes `cowrie.json`.
2. It renames it to `cowrie.json.1`, replacing the previous `cowrie.json.1`.
3. It opens a new, empty `cowrie.json` and keeps writing there.

Rotation happens between two events, so a line is never split across files. At most two files exist (~100 MB in total), so the simulator cannot fill the host disk.

The file is **renamed, never truncated**. The Logstash file input follows files by inode, so it finishes reading the renamed file and then picks up the new one. Truncating in place (`copytruncate`) can lose or repeat lines.

For Logstash to finish reading the lines that were still pending when the file was renamed, its `path` must also match the rotated name:

```
path => "/var/log/honeypot/cowrie.json*"
```

To start from scratch, remove the volume with `docker compose down -v`.

## Verification

Acceptance criteria (issue #25):

- `cowrie.json` grows with valid events (each line parses as JSON).
- The rate changes with `SIMULATOR_MODE` and `SIMULATOR_RATE`.

Indexing in Elasticsearch is checked in issue #55 (GeoIP) and issue #56 (severity).

Quick manual checks inside the container:

```bash
tail -f /var/log/honeypot/cowrie.json
python -c "import json,sys; [json.loads(l) for l in open('/var/log/honeypot/cowrie.json')]; print('all lines valid')"
```

## Ownership

Maintained by **astefane** (backend / DevOps). The event format is a contract with the data pipeline owner (**migugar2**): any change to field names or event types must be agreed with them first.