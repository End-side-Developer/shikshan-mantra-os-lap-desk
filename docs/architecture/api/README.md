# docs/architecture/api/

Versioned API contracts for Shikshan Mantra OS backends. Documents only —
no client or server implementation here.

| File | Purpose | Frozen by |
|------|---------|-----------|
| [auth-v1.yaml](auth-v1.yaml) | Auth + role exchange (login / refresh / logout). | [ADR-0009](../../adr/0009-login-branding-auth.md) / SMO-0407 |

## Viewing the spec

Open in a Redoc / Swagger UI of your choice:

```bash
npx @redocly/cli preview-docs docs/architecture/api/auth-v1.yaml
```

Or parse-check with Python:

```bash
python3 -c "import yaml; yaml.safe_load(open('docs/architecture/api/auth-v1.yaml'))"
```

The runtime config at `/etc/shikshan/auth.yml` (schema at
`modules/catalogs/schemas/auth-config.schema.json`) declares which backend
URL the client targets. Both files validate via the `lint-manifest` skill.

## Out of scope for this batch

- Client implementation (PAM/NSS/webview) — tracked against SMO-0299.
- Server reference implementation — separate follow-up.
- Wiring the welcome dialog's Institution button to the contract — depends
  on the client landing first.
