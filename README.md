# OdooGuard (PoC)

OdooGuard is a lightweight proof of concept showing how to automate Odoo backups inside an isolated container.  
It is **not production-ready** and exists only as a minimal technical demonstration.

## What it does

- Runs `pg_dump` against a PostgreSQL database  
- Copies the Odoo filestore  
- Produces a ZIP archive compatible with Odoo's standard backup format  
- Executes on a cron schedule inside the container  
- Keeps simple backup rotation

## Not suitable for production

This PoC lacks essential production features:

- robust error handling  
- encryption and integrity checks  
- monitoring or healthchecks  
- secure secret management (env vars are placeholder only)  
- offsite storage (S3, SFTP, etc.)

Use secrets through a proper secret manager in real environments (Docker secrets, Kubernetes Secrets, Vault, etc.).

## Example (Docker Compose)

```yaml
services:
  odooguard:
    image: ghcr.io/apikcloud/odooguard:latest
    environment:
      DB_NAME: test
      PGHOST: postgres
      PGPORT: 5432
      PGUSER: odoo
      PGPASSWORD: odoo
      CRON_SCHEDULE: "0 2 * * *"
      TZ: "Europe/Paris"
      LANG: "fr_FR.UTF-8"
      LC_ALL: "fr_FR.UTF-8"
    volumes:
      - odoo-data:/var/lib/odoo:ro
      - backups:/backups
```

## Known Issues

- Locale and timezone variables may not be applied  
- Retention policy is not fully accurate  

## License

MIT
