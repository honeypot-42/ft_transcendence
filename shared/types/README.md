# shared/types

This folder contains the **shared TypeScript type definitions** for the entire project.

Every team member must import data structures from here instead of defining their own.
This ensures the frontend, backend and data pipeline always speak the same language.

---

## Why does this folder exist?

Without shared types, this happens:

```
P2 (backend) sends:   { source_ip: "1.2.3.4", country: "Russia" }
P1 (frontend) reads:  { ip: "1.2.3.4",        pais: "Russia"    }
                              different name     different name
                              = runtime bug, very hard to debug
```

With shared types, TypeScript catches this at compile time before it reaches production.

---

## Files

| File | Description |
|------|-------------|
| `attack.types.ts` | All attack-related interfaces: `AttackEvent`, `WebSocketEvent`, `HoneypotStatus`, `AttackStats` and more |

---

## How to use it

### In the frontend (React)

```typescript
import type { AttackEvent, AttackStats } from '../../shared/types/attack.types'

function AttackCard({ attack }: { attack: AttackEvent }) {
  return <div>{attack.source_country} — {attack.severity}</div>
}
```

### In the backend (NestJS)

```typescript
import type { AttackEvent, WebSocketEvent } from '../../shared/types/attack.types'

this.server.emit('new-attack', {
  event: 'new-attack',
  data: attack as AttackEvent,
} satisfies WebSocketEvent)
```

### In the data pipeline (if using TypeScript)

```typescript
import type { AttackEvent } from '../../shared/types/attack.types'

function validateAttack(raw: unknown): AttackEvent {
  // validate and cast
}
```

---

## How to add or change a field

1. Open `attack.types.ts`
2. Make your change
3. Open a PR with the change — **mention in the PR description which team members are affected**
4. Affected members update their code accordingly in the same sprint

> Never change a field name without telling the team first.
> A renamed field breaks the frontend, backend and pipeline at the same time.

---

## Main types reference

### AttackEvent

The core object. Emitted by WebSocket (`new-attack` event) and returned by the REST API.

| Field | Type | Example |
|-------|------|---------|
| `id` | `string` | `"abc123"` |
| `timestamp` | `string` (ISO 8601) | `"2026-08-11T18:00:00.000Z"` |
| `source_ip` | `string` | `"185.234.12.5"` |
| `source_country` | `string` (ISO alpha-2) | `"RU"` |
| `source_lat` | `number` | `55.7558` |
| `source_lng` | `number` | `37.6173` |
| `protocol` | `Protocol` | `"ssh"` |
| `honeypot_type` | `HoneypotType` | `"cowrie"` |
| `severity` | `Severity` | `"critical"` |
| `mitre_tactic` | `string` | `"TA0006 - Credential Access"` |
| `mitre_technique` | `string` | `"T1110 - Brute Force"` |

### WebSocketEvent

Wrapper for all events sent through the Socket.io connection.

```typescript
// Frontend listens like this:
socket.on('new-attack', (event: WebSocketEvent) => {
  const attack = event.data as AttackEvent
  paintOnMap(attack)
})
```

### AttackStats

Returned by `GET /api/v1/attacks/stats`. Used by the analytics dashboard charts.

---

## Severity levels

Severity is assigned by **rules in Logstash** from the Cowrie event type (it is not AI and
does not depend on VirusTotal). The mapping lives in `elk/logstash/mappings/severity.yml`.

| Level | Cowrie event | Meaning |
|-------|--------------|---------|
| `critical` | `cowrie.session.file_download` | The attacker downloaded a tool or malware |
| `high` | `cowrie.command.input` | The attacker is running commands in the fake shell |
| `medium` | `cowrie.login.success` | A brute-force attempt "succeeded" |
| `low` | `cowrie.login.failed`, `cowrie.session.connect` | Scans and failed logins |

VirusTotal reputation (`IpReputation`) is fetched **on demand** by the backend when an analyst
opens an IP, and cached for 24 h. It is optional: without an API key the app still works.
