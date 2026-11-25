*This project has been created as part of the 42 curriculum by gafreire, astefane, alejagom, migugar2, alejaro2.*

# SENTINEL — Honeypot Threat Intelligence Dashboard

> 🚧 **Work in progress.** This README follows the structure required by the ft_transcendence subject
> and is completed as the project advances.

## Description

SENTINEL is a real-time threat intelligence dashboard built on top of a honeypot.
Decoy services capture attack attempts; an ELK pipeline enriches them (geolocation,
MITRE ATT&CK technique, severity) and a web application lets a team of analysts
watch, investigate and discuss them live.

### Key features (planned)

- 🌍 **Live threat map** — animated world map of incoming attacks
- 📊 **Analytics dashboard** — interactive charts, filters, CSV/PDF export
- 🍯 **Honeypot pipeline** — Cowrie → Logstash → Elasticsearch
- ⚡ **Real-time updates** — Socket.IO push for attacks, chat and notifications
- 🔑 **Public API** — API keys, rate limiting, Swagger documentation
- 💬 **Analyst collaboration** — direct messages, profiles, team contacts
- 🔒 **Security first** — HTTPS only, hashed passwords, HttpOnly cookies, 2FA

## Instructions

### Prerequisites

| Tool | Version |
|------|---------|
| Docker Engine | ≥ 24 |
| Docker Compose | v2 (≥ 2.20) |
| Git | any recent version |
| Free RAM | ≥ 6 GB |
| Google Chrome | latest stable |

### Setup

```bash
git clone https://github.com/honeypot-42/ft_transcendence.git
cd ft_transcendence
cp .env.example .env
# Fill in every secret (generate each one with: openssl rand -hex 32)
```

No external API key is required to run the project.

### Run

```bash
docker compose up --build                              # evaluation stack (planned)
docker compose -f docker-compose.dev.yml up --build    # development stack
```

| URL | Service |
|-----|---------|
| https://localhost | Application |
| https://localhost/api/v1 | REST API |
| https://localhost/api/docs | API documentation (planned) |

All traffic goes through Nginx over HTTPS; `http://localhost` redirects to HTTPS. The local
certificate is self-signed, so the browser shows a warning the first time. Nginx is the only
service that publishes ports: see [nginx/README.md](./nginx/README.md).

## Resources

To be completed. AI usage will be described here (which tasks and which parts of the project).

## Team Information

| Login | Role(s) | Responsibilities |
|-------|---------|------------------|
| gafreire | Project Manager · Developer | Backend security, Nginx/HTTPS, honeypot isolation, API keys, ELK security |
| astefane | Developer | Backend (NestJS), real-time gateway, Docker, attack simulator |
| alejagom | Tech Lead (to be confirmed) · Developer | Frontend, threat map, analytics dashboard, design system |
| migugar2 | Developer | ELK stack, Logstash pipeline, data export/import |
| alejaro2 | Product Owner (to be confirmed) · Developer | Users, authentication, chat, notifications, legal pages |

## Project Management

Two-week sprints, sync meetings twice a week, GitHub Issues + Projects + milestones,
pull requests reviewed by another member, Discord for communication.
See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Technical Stack

React 18 · Vite · TypeScript · Tailwind CSS · NestJS 11 · TypeORM · PostgreSQL 16 ·
Elasticsearch / Logstash / Kibana 8 · Socket.IO · Nginx · Docker Compose.

## Database Schema

To be completed (users, friendships, messages, notifications, api_keys, alerts).

## Features List

To be completed.

## Modules

Planned: 7 Major + 2 Minor (16 points), plus 3 Minor once the core is done (19 points).
To be completed with justification and owners.

## Individual Contributions

To be completed by each member.
