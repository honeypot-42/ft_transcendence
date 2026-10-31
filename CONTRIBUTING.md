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
