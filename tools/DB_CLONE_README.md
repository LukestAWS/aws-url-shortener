# DB Clone & Rotation Helpers

This folder contains helper scripts to clone a Postgres database and rotate database credentials safely.

Files
- `clone-db.sh`: Dump and restore a Postgres database. Supports file-based custom-format dump/restore (recommended) and a streaming plain-SQL mode.
- `rotate-db-creds.sh`: Create a new DB role, update the Fly app `DATABASE_URL` secret to use the new role, and provide guidance for dropping old roles.

Prerequisites
- `pg_dump`, `pg_restore`, `psql` (from `postgresql-client`)
- `openssl` (for strong password generation)
- `flyctl` authenticated (`fly auth login`) for updating Fly secrets

Security
- Never paste credentials in public logs.
- Use temporary admin credentials only from a trusted host.
- Keep backups (pg_dump) before doing destructive operations.

Typical workflow
1. Create a new DB instance (via Fly Managed Postgres or another provider).
2. Run `clone-db.sh` to copy data from the source to the destination.
3. Test the new DB by deploying to a staging app or setting a temporary `DATABASE_URL` secret.
4. Use `rotate-db-creds.sh` (with admin DB access) to create an application-specific role and update the Fly secret.
5. After monitoring and verifying, revoke/drop old roles.

Examples
See header comments at the top of each script for exact example usage and flags.
