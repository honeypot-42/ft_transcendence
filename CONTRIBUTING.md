# Contributing Guide — ft_transcendence

> Read this before making your first commit. These rules are mandatory for all team members.

---

## Commit Convention

We use **Conventional Commits**. Every commit message must follow this format:

```
<type>(<scope>): <short description>

Examples:
  feat(map): add real-time attack animation on D3 globe
  fix(auth): resolve JWT refresh token expiry bug
  chore(docker): add elasticsearch service to dev compose
  docs(api): add Swagger decorators to attacks endpoints
  test(users): add unit tests for friends service
  refactor(websocket): extract room logic into separate service
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or functionality |
| `fix` | Bug fix |
| `chore` | Config, setup, dependencies, infrastructure |
| `docs` | Documentation only (README, comments, guides) |
| `test` | Adding or updating tests |
| `refactor` | Code change that does not add a feature or fix a bug |
| `style` | Formatting, missing semicolons (no logic change) |

### Scopes

Use the area of the codebase you are working on:

```
auth, users, friends, chat, notifications, attacks, api-keys,
websocket, elasticsearch, map, dashboard, docker, nginx, simulator,
cowrie, logstash, grafana, docs
```

### Rules

- Description must be in **English**
- Use **imperative mood**: "add feature" not "added feature"
- Maximum **72 characters** in the first line
- No capital letter at the start of the description
- No period at the end

---

## Branch Naming

```
feature/P{number}-{short-description}

Examples:
  feature/P2-nestjs-setup
  feature/P2-websocket-gateway
  feature/P4-cowrie-honeypot
  feature/P1-d3-world-map
  feature/P5-auth-jwt
```

Always branch off from `develop`, never from `main`.

```bash
git checkout develop
git pull origin develop
git checkout -b feature/P2-my-task
```

---

## Pull Request Rules

- Every PR must target `develop` (not `main`)
- PR title must match the issue title
- PR description must include `Closes #<issue-number>`
- Minimum **1 approval** required to merge into `develop`
- Minimum **2 approvals** required to merge into `main`
- You cannot approve your own PR
- Resolve all review comments before merging
- Do not merge if there are unresolved conflicts — fix them first

### PR Description Template

```
## What does this PR do?
Brief description of the changes.

## Related issue
Closes #42

## How to test it
Steps to verify the feature works.

## Checklist
- [ ] npm run lint passes with 0 errors
- [ ] No console.log left in the code
- [ ] Feature is demonstrable
```

---

## Code Style

- **Language:** TypeScript everywhere (strict mode)
- **Linting:** ESLint — run `npm run lint` before pushing. Zero errors, zero warnings.
- **Formatting:** Prettier — run `npm run format` before pushing
- No commented-out code in PRs
- No `console.log` left in production code (use NestJS Logger in the backend)

---

## Before Pushing

```bash
# Backend
cd backend
npm run lint       # 0 errors, 0 warnings
npm run test       # 0 failing tests

# Frontend
cd frontend
npm run lint       # 0 errors, 0 warnings
```

---

## Issue Workflow

1. Pick an issue from the **To Do** column in the Project board
2. Assign it to yourself
3. Move it to **In Progress**
4. Create your feature branch
5. Work and commit following the convention above
6. Open a PR → move issue to **In Review**
7. Get at least 1 approval → merge → issue moves to **Done**

For more details on how to use GitHub Issues, Projects and Milestones, read [docs/github_workflow.md](./docs/github_workflow.md).

---

## Continuous Integration

Every pull request to `develop` or `main` runs two workflows in GitHub Actions.
A PR cannot be merged until the required checks are green.

### What is checked

| Job | Runs when the PR changes | What it does |
|-----|--------------------------|--------------|
| **Backend** | `backend/**` | `npm ci`, type check, ESLint (0 warnings), unit tests, e2e tests, build |
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
docker run --rm -i hadolint/hadolint:v2.15.1 hadolint --failure-threshold warning - < backend/Dockerfile

# Secrets: commits of your branch that are not in develop yet
gitleaks git --redact --log-opts="origin/develop..HEAD"
```

If gitleaks reports a real secret, removing it in a new commit is not enough:
it is still in the history. Rotate the secret and ask for help to rewrite the branch.
