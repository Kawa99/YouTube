# Phase 14: Security and Compliance

Phase 14 adds a private-use security baseline while keeping local development friction low.

## Implemented

- Optional admin-password mode.
- `/login` and `/logout` routes.
- `ADMIN_PASSWORD` and `ADMIN_PASSWORD_HASH` environment variables.
- `healthz` remains unauthenticated for deployment checks.
- Existing collection, export, and refresh route rate limits remain in place.
- Security scan remains part of the verification gate through Bandit.

## Admin Auth Mode

Authentication is disabled unless either variable is set:

- `ADMIN_PASSWORD`
- `ADMIN_PASSWORD_HASH`

For local private use, `ADMIN_PASSWORD` is acceptable. For hosted use, prefer `ADMIN_PASSWORD_HASH`.

Generate a hash with:

```bash
python - <<'PY'
from werkzeug.security import generate_password_hash
print(generate_password_hash("replace-this-password"))
PY
```

Then set:

```env
ADMIN_PASSWORD_HASH=scrypt:...
```

## Secrets Rules

- `.env` stays ignored.
- `.env.example` contains names only, not real secrets.
- OAuth tokens are not stored in the database; owned analytics stores only `token_secret_ref`.
- API keys and passwords are not printed in logs.

## Remaining Future Work

- Add CSRF protection if this is exposed beyond a trusted private network.
- Add pip-audit or an equivalent dependency vulnerability scan to CI.
- Move from single-admin-password mode to real user accounts if multiple people use the app.
