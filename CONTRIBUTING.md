# Contributing Guide — ft_transcendence

> Read this before your first commit. These rules are mandatory for every team member.

---

## 0. One-time setup

Commit with **your own** GitHub account. The subject requires commits from every member,
and GitHub only attributes a commit to you if its email belongs to your account.

```bash
git config --global user.name  "Your Name"
git config --global user.email "the-email-of-your-github-account"
```

Then copy the environment file and fill in the secrets:

```bash
cp .env.example .env   # never commit .env
openssl rand -hex 32   # run once per secret and paste the result
```

Secrets may only contain `A-Z a-z 0-9 _ -`: `openssl rand -hex 32` always does.

### Updating your `.env`

`.env` is not versioned, so it does not change when you pull. When a PR adds, renames or
removes a variable in `.env.example`, update your `.env` by hand.

1. See which variable names differ (only names are compared, values are never printed):

   ```bash
   diff <(grep -o '^[A-Z_]*=' .env.example | sort) <(grep -o '^[A-Z_]*=' .env | sort)
   ```

   Lines starting with `<` are missing in your `.env`: add them.
   Lines starting with `>` no longer exist: remove them.

2. Give every new secret its own value with `openssl rand -hex 32`. Never reuse one.

3. If database or Elasticsearch credentials changed, the old volumes still hold the old ones.
   Recreate them (this **deletes local data**):

   ```bash
   docker compose -f docker-compose.dev.yml down -v
   docker compose -f docker-compose.dev.yml up --build
   ```

The PR that changes `.env.example` lists the changes in its description.

---

## 1. Languages

| What | Language |
|------|----------|
| Code, comments, commit messages, PR titles, files in the repository | **English** |
| Issues, PR descriptions, reviews and comments on GitHub | **Spanish** |

---

## 2. Commit convention

We use **Conventional Commits**:

```
<type>(<scope>): <short description>

feat(map): add real-time attack animation
fix(auth): reject expired refresh tokens
chore(docker): add healthcheck to elasticsearch
docs(readme): add database schema section
test(users): add unit tests for friends service
refactor(realtime): extract room logic into a service
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `chore` | Config, setup, dependencies, infrastructure, CI |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither adds a feature nor fixes a bug |
| `style` | Formatting only |

### Scopes

```
auth, users, friends, chat, notifications, alerts, attacks, api-keys,
realtime, websocket, elasticsearch, logstash, kibana, elk, map, dashboard, ui,
backend, config, types, docker, nginx, ci, simulator, cowrie,
docs, readme, contributing
```

### Rules

- Description in **English**, **imperative mood** ("add", not "added")
- First line ≤ **72 characters**, no capital letter at the start, no final period
- One logical change per commit

---

## 3. Branches

```
main      ← stable, receives merges from develop only
develop   ← integration branch
feature/P{n}-{short-description}   e.g. feature/P2-nestjs-setup
fix/…  docs/…  chore/…
```

Always branch off `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/P2-my-task
```

---

## 4. Pull requests

- Target `develop` (never `main`)
- Title in English following the commit convention; description in Spanish with `Closes #<issue>`
- **1 approval from another member** to merge into `develop`, 2 for `main`
- **Never approve or merge your own PR**
- The author resolves conflicts and review comments
- No PR stays more than 48 h without review — ping the team on Discord

### Template

```
## What does this PR do?

## Related issue
Closes #

## How to test it

## Checklist
- [ ] npm run lint passes with 0 errors and 0 warnings
- [ ] npm run test passes
- [ ] No console.log left (use the NestJS Logger in the backend)
- [ ] No secrets, tokens or real credentials in the diff
- [ ] If .env.example changed: the changes are listed for the team
- [ ] Feature is demonstrable
```

---

## 5. Code style

- **TypeScript** everywhere, `strict` mode
- **ESLint** and **Prettier** (`npm run format`) before pushing
- No commented-out code, no `console.log` in committed code
- Validate every input: DTOs with `class-validator` in the backend, zod schemas in the frontend
- Never use `dangerouslySetInnerHTML`: honeypot data is hostile input

---

## 6. Security rules

- Secrets only in `.env`. `.env.example` contains names and placeholder values only
- Never commit certificates or keys (`*.pem`, `*.key`, `*.crt`)
- Never publish a port in Compose other than Nginx (80/443) and the honeypot ports
- Never mount `/var/run/docker.sock` into a container
- Services connect to Elasticsearch with their own least-privilege user, never as `elastic`
- If a secret is ever pushed, tell the team and **rotate it** — deleting the commit is not enough

---

## 7. Before pushing

```bash
# Backend
cd backend && npx eslint "{src,test}/**/*.ts" --max-warnings 0 && npm test

# Frontend
cd frontend && npx eslint . --max-warnings 0 && npm test
```

The full list of checks is in [Continuous Integration](#8-continuous-integration).

---

## 8. Continuous Integration

Every pull request to `develop` or `main` runs two workflows in GitHub Actions.
A PR cannot be merged until the required checks are green.

### What is checked

| Job | Runs when the PR changes | What it does |
|-----|--------------------------|--------------|
| **Backend** | `backend/**` | `npm ci`, `npm audit` of production dependencies (fails on high or critical), type check, ESLint (0 warnings), unit tests, e2e tests, build |
| **Frontend** | `frontend/**` | `npm ci`, ESLint (0 warnings), build |
| **Docker** | `docker-compose*.yml`, `**/Dockerfile*`, `nginx/**`, `.env.example` | `docker compose config -q` and hadolint on every Dockerfile |
| **Secret scan** | always | gitleaks on every commit of the PR |
| **CI result** | always | Fails if any job above failed. A job skipped because its folder did not change counts as passed |
| **CodeQL** | always | Static security analysis of JavaScript/TypeScript |

Required checks in branch protection: **CI result** and **Analyze (javascript-typescript)**.

### Reproduce it locally

```bash
# Backend
cd backend
npm ci
npm audit --omit=dev --audit-level=high
npx tsc --noEmit -p tsconfig.json
npx eslint "{src,test}/**/*.ts" --max-warnings 0   # not `npm run lint`: it uses --fix
npm test
npm run test:e2e
npm run build

# Frontend
cd frontend
npm ci
npx eslint . --max-warnings 0
npm run build

# Docker (from the repository root)
docker compose -f docker-compose.dev.yml --env-file .env.example config -q
docker run --rm -i hadolint/hadolint:v2.15.1 hadolint --failure-threshold warning - < nginx/Dockerfile

# Secrets: commits of your branch that are not in develop yet
gitleaks git --redact --log-opts="origin/develop..HEAD"
```

If `npm audit` fails, run `npm audit fix` (never `--force`: it can jump to a new
major version) and then `npm ci`, so `node_modules` matches the updated lockfile.
A new advisory can turn a PR red even if it does not touch dependencies.

If gitleaks reports a real secret, removing it in a new commit is not enough:
it is still in the history. Rotate the secret and ask for help to rewrite the branch.

---

## 9. Issue workflow

1. Pick an issue from **To Do** and assign it to yourself
2. Move it to **In Progress** and create your branch
3. Commit following the convention
4. Open a PR → move the issue to **In Review**
5. Another member approves → merge → the issue moves to **Done**
