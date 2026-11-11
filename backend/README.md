# Backend — SENTINEL Honeypot Dashboard

REST API + WebSocket server for the SENTINEL project. Built with NestJS + TypeScript.

---

## What does this backend do?

This server is the **brain of the dashboard**. Its responsibilities are:

1. Receive HTTP requests from the frontend (React) and respond with data
2. Query Elasticsearch to retrieve attacks detected by the honeypots
3. Push real-time events to the frontend via WebSocket
4. Handle user management, authentication and chat

---

## Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **NestJS** | v11 | Main framework (structure, modules, dependency injection) |
| **TypeScript** | strict | Strict typing — 0 implicit `any` |
| **class-validator** | — | Validate incoming request payloads |
| **@nestjs/config** | — | Read environment variables safely |
| **@nestjs/jwt** | — | Generate and verify JWT tokens |
| **joi** | — | Validate that all required environment variables are set |
| **@nestjs/websockets** + **socket.io** | v11 | Real-time events to the dashboard |

---

## How to run locally

### 1. Prerequisites

- Node.js ≥ 20
- npm ≥ 10
- A `.env` file at the **repository root** (copy from `.env.example`, see below)

### 2. Install dependencies

```bash
cd backend
npm install
```

### 3. Start in development mode (with hot-reload)

```bash
npm run start:dev
```

The server listens on the **internal** port 3001. You should see this in the terminal:

```
[Nest] ... LOG [Bootstrap] SENTINEL backend listening on internal port 3001
```

> Port 3001 is for local development only. In the Docker stack the backend is never
> published on the host: every request goes through Nginx over HTTPS
> (`https://localhost/api/v1/...`).

### 4. Other useful commands

```bash
npm run build      # Compile TypeScript → JavaScript (output: dist/)
npm run start      # Start in production mode (requires build first)
npm run lint       # Check code style with ESLint (applies automatic fixes)
npm run test       # Run unit tests with Jest
npm run test:e2e   # Run integration tests (end-to-end)
```

---

## Folder structure

```
backend/
├── src/
│   ├── main.ts                    # Entry point — starts the server
│   ├── app.module.ts              # Root module — registers all other modules
│   │
│   ├── auth/                      # [P5] Authentication: register, login, JWT
│   │   ├── auth.module.ts
│   │   ├── auth.controller.ts     # Routes: POST /auth/register, POST /auth/login
│   │   └── auth.service.ts        # Logic: bcrypt, JWT, credential validation
│   │
│   ├── users/                     # [P5] User management and profiles
│   │   ├── users.module.ts
│   │   ├── users.controller.ts    # Routes: GET /users/me, PATCH /users/me
│   │   └── users.service.ts       # Logic: user CRUD, avatar upload
│   │
│   ├── attacks/                   # [P2] Honeypot attack data
│   │   ├── attacks.module.ts
│   │   ├── attacks.controller.ts  # Routes: GET /attacks, POST /attacks/search
│   │   └── attacks.service.ts     # Logic: Elasticsearch queries
│   │
│   ├── websocket/                 # [P2] Real-time communication
│   │   ├── websocket.module.ts
│   │   └── websocket.gateway.ts   # Socket.io gateway (registered once the handshake is authenticated)
│   │
│   └── elasticsearch/             # [P2] Elasticsearch connection
│       ├── elasticsearch.module.ts
│       └── elasticsearch.service.ts  # ES client wrapper
│
├── test/
│   └── app.e2e-spec.ts            # Integration tests (completed in S11)
│
├── package.json                   # Dependencies and npm scripts
├── tsconfig.json                  # TypeScript config (strict mode)
└── nest-cli.json                  # NestJS CLI config
```

---

## How NestJS works — simplified

NestJS organizes code into **modules**. Each module has 3 parts:

```
HTTP Request
     │
     ▼
Controller        ← Receives the request and decides what to do
     │                Example: "incoming GET /attacks"
     ▼
Service           ← Contains the business logic
     │                Example: "queries Elasticsearch and returns the data"
     ▼
HTTP Response
```

The **`AppModule`** (`app.module.ts`) is the root module that imports all others.
Think of it as the `index.js` of the structure — if a module is not listed here, the server does not know it exists.

### `main.ts` — the entry point

```typescript
// Create the NestJS application
const app = await NestFactory.create(AppModule);

// Enable automatic validation of incoming data
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true, // Strip properties not declared in the DTO
    forbidNonWhitelisted: true, // Unexpected field → 400 Bad Request
    transform: true, // Convert the payload into a DTO instance
  }),
);

// All endpoints are prefixed with /api/v1
// Example: /api/v1/attacks, /api/v1/auth/login
app.setGlobalPrefix('api/v1');

// Listen on the internal port (PORT, default 3001)
const port = process.env['PORT'] ?? 3001;
await app.listen(port);
Logger.log(`SENTINEL backend listening on internal port ${port}`, 'Bootstrap');
```

---

## Environment variables

All secrets live in a single `.env` file at the **repository root**. It is created from
the template and never committed:

```bash
# from the repository root
cp .env.example .env
```

With Docker Compose, the backend receives these variables from `docker-compose.dev.yml`
(which reads them from `.env`):

| Variable | Source in `.env` | Purpose |
|----------|------------------|---------|
| `NODE_ENV`, `PORT` | set by compose | Runtime mode and internal port (default `3001`) |
| `JWT_SECRET`, `JWT_EXPIRES_IN` | `JWT_SECRET`, `JWT_EXPIRES_IN` | Sign and expire JWT tokens |
| `DB_HOST`, `DB_PORT` | set by compose | PostgreSQL service address |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL credentials |
| `ES_HOST` | set by compose | Elasticsearch service address |
| `ES_USER`, `ES_PASSWORD` | `ELASTIC_USER`, `ELASTIC_PASSWORD` | Elasticsearch credentials |

> ⚠️ **Never commit the real `.env` file.** It is listed in `.gitignore`.
> Only `.env.example` with placeholder values is committed. The list of variables
> lives in `.env.example`; this table only explains how the backend uses them.

---

## Current module status

| Module | Owner | Status in S2 | Implemented in |
|--------|-------|-------------|----------------|
| `auth/` | P5 | Empty stub | S2 (register/login endpoints) |
| `users/` | P5 | Empty stub | S3 (user CRUD) |
| `attacks/` | P2 | Empty stub | S4–S6 (ES queries) |
| `websocket/` | P2 | Gateway skeleton, not registered | S3 (authenticated Socket.io gateway) |
| `elasticsearch/` | P2 | Empty stub | S4 (queries) |

---

## Typical request flow

```
Frontend (React)
      │  HTTP GET /api/v1/attacks
      ▼
  Nginx (port 443)
      │  proxy → backend:3001
      ▼
  NestJS backend
      │
      ├── AttacksController.findAll()
      │         │
      │         ▼
      │   AttacksService.getAttacks()
      │         │
      │         ▼
      │   ElasticsearchService.search(query)
      │         │
      │         ▼
      │   Elasticsearch (port 9200)
      │         │  returns documents
      │         ▼
      └── JSON response to frontend
```
