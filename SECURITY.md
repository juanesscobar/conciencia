# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| main (latest) | ✅ |

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately to **escobarbvega.juanandres21@gmail.com** with:

- A description of the vulnerability
- Steps to reproduce (minimal)
- Affected component (backend route, module, auth, etc.)
- Suggested fix (optional)

You should receive a response within **48 hours**. We will coordinate a fix
and disclosure timeline with you.

## Security notes for self-hosting

- Production runs behind nginx (80/443 only); Postgres and Redis are NOT
  exposed to the internet (docker network internal).
- All secrets (API keys, email app passwords) are stored encrypted (Fernet,
  derived from `SECRET_KEY`) — never in plain text.
- `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` and `LOCAL_ADMIN_PASSWORD`
  must be set via environment (`.env`), never committed.
