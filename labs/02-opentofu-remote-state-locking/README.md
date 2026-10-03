# Lab 2: OpenTofu Remote State and Locking with PostgreSQL

> Use OpenTofu with the `pg` backend on a local PostgreSQL container to see remote state, workspaces, and state locking. No cloud account is needed.

**Time:** about 30 minutes. **Level:** Intermediate.

## What you practise

- Moving state off your laptop into a shared backend
- How workspaces store separate state for the same code
- What a state lock is, and what happens when two people run at the same time
- Why state can contain secrets, and who should be able to read it
- The concepts in [terraform/03-state-and-backends.md](../../terraform/03-state-and-backends.md) and [terraform/05-environments-and-workspaces.md](../../terraform/05-environments-and-workspaces.md)

## Prerequisites

| Tool | Tested with | Notes |
| --- | --- | --- |
| Docker with Compose v2 | Docker 29.1, Compose 2.39 | Runs PostgreSQL 17 |
| OpenTofu | v1.12.2 | Terraform also works: replace `tofu` with `terraform`. |

You do not need `psql` on your laptop. The steps run it inside the container with `docker exec`.

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Starts PostgreSQL as container `lab-pg` on `127.0.0.1:15432` |
| `.env.example` | Template for the database password. Copy it to `.env`. |
| `backend.tf` | The `pg` backend. It reads the connection from environment variables, so no password is in code. |
| `main.tf` | Only `random`, `local`, and `terraform_data` resources, so nothing is created in any cloud |
| `.gitignore` | Keeps `.env`, `.terraform/`, state files, and `out/` out of Git |

## How the pg backend works

- On the first `tofu init`, OpenTofu creates the schema `terraform_remote_state` and a table `states`.
- Each workspace is one row in that table: an `id`, a `name` (the workspace name), and `data` (the state JSON).
- Locking uses a PostgreSQL **advisory lock** keyed on the row `id`. The lock lives in the database session, so it is released when the OpenTofu process ends, even if it crashes.

## Steps

### 1. Start PostgreSQL

```bash
cp .env.example .env
# Edit .env and set your own POSTGRES_PASSWORD
docker compose up -d --wait
docker ps --filter name=lab-pg
```

`--wait` returns when the health check passes. The status shows `(healthy)`.

### 2. Point OpenTofu at the database

Run this in every terminal you use for the lab:

```bash
set -a; . ./.env; set +a
export PGPASSWORD="$POSTGRES_PASSWORD"
export PG_CONN_STR="postgres://tofu@localhost:15432/tofu_state?sslmode=disable"
```

The `pg` backend reads `PG_CONN_STR` and the standard PostgreSQL client variables such as `PGPASSWORD`. `sslmode=disable` is only fine because the database is local. In a real setup, use TLS.

### 3. Initialize and apply with remote state

```bash
tofu init
tofu apply
ls *.tfstate
```

Type `yes` at the prompt. `tofu init` prints `Successfully configured the backend "pg"!`. `ls` finds no state file, because the state is in PostgreSQL. Look at it there:

```bash
docker exec lab-pg psql -U tofu -d tofu_state \
  -c 'SELECT id, name, length(data) AS bytes FROM terraform_remote_state.states ORDER BY id;'
```

Now read a "sensitive" output straight from the state:

```bash
docker exec lab-pg psql -U tofu -d tofu_state -tAc \
  "SELECT data::jsonb #>> '{outputs,db_password,value}' FROM terraform_remote_state.states WHERE name = 'default';"
```

The password prints in plain text. `sensitive = true` only hides a value in CLI output. It does not encrypt state.

### 4. Use a second workspace

```bash
tofu workspace new dev
tofu apply
tofu workspace list
docker exec lab-pg psql -U tofu -d tofu_state \
  -c 'SELECT id, name, length(data) AS bytes FROM terraform_remote_state.states ORDER BY id;'
cat out/default.txt out/dev.txt
```

The table now has two rows, `default` and `dev`. The same code created two sets of resources with different names, because `main.tf` uses `terraform.workspace`.

### 5. See the state lock in action

Open two terminals in the lab folder. Run the step 2 commands in both. Both are on the `dev` workspace, because the selected workspace is saved in `.terraform/`.

1. In terminal 1, start a change and **leave it waiting** at the `Enter a value:` prompt. OpenTofu holds the lock while it waits.

   ```bash
   tofu apply -var release_version=1.1.0
   ```

2. In terminal 2, try a plan, then look at the lock in PostgreSQL:

   ```bash
   tofu plan
   docker exec lab-pg psql -U tofu -d tofu_state -c \
     "SELECT l.objid AS state_id, s.name AS workspace, l.mode, l.granted
        FROM pg_locks l JOIN terraform_remote_state.states s ON s.id = l.objid
       WHERE l.locktype = 'advisory';"
   ```

3. Still in terminal 2, plan the `default` workspace. It works, because each workspace has its own lock:

   ```bash
   TF_WORKSPACE=default tofu plan
   ```

4. Answer `no` in terminal 1. The prompt shows `Apply cancelled.` and the lock is released. Run `tofu plan` again in terminal 2: it now works.

<details><summary>Optional: wait for a lock, and see what happens after a crash</summary>

- `tofu plan -lock-timeout=5s` retries for 5 seconds before it fails, instead of failing at once. CI pipelines often set a timeout like this.
- Start `tofu apply -var release_version=1.1.0` in terminal 1 again, then kill it from terminal 2 with `pkill -9 -f "tofu apply"`. Run `tofu plan` in terminal 2. It works, because PostgreSQL drops the advisory lock when the session closes. Other backends, such as `azurerm`, can leave a stale lock after a crash. Then you clear it with `tofu force-unlock <LOCK_ID>`.

</details>

## Expected result

These outputs come from a real run with OpenTofu v1.12.2 and PostgreSQL 17.

```text
$ docker ps --filter name=lab-pg
NAMES     STATUS                   PORTS
lab-pg    Up 2 seconds (healthy)   127.0.0.1:15432->5432/tcp

$ tofu init
Successfully configured the backend "pg"! OpenTofu will automatically
use this backend unless the backend configuration changes.
...
OpenTofu has been successfully initialized!

$ tofu apply
Apply complete! Resources: 4 added, 0 changed, 0 destroyed.

Outputs:

app_name = "default-balanced-tapir"
db_password = <sensitive>

$ ls *.tfstate
ls: cannot access '*.tfstate': No such file or directory

$ tofu workspace list            # after step 4
  default
* dev

$ docker exec lab-pg psql ... states
 id |  name   | bytes
----+---------+-------
  1 | default |  2857
  2 | dev     |  2812
(2 rows)

$ tofu plan                      # terminal 2, while terminal 1 waits
Error: Error acquiring the state lock

Error message: Workspace is already locked: dev
Lock Info:
  ID:        72c411a5-4576-adea-8c9a-fe25599ffcf7
  Path:
  Operation: OperationTypePlan
  Who:       user@laptop
  Version:   1.12.2
  Created:   2026-10-03 04:22:26.921993237 +0000 UTC
  Info:

$ docker exec lab-pg psql ... pg_locks
 state_id | workspace |     mode      | granted
----------+-----------+---------------+---------
        2 | dev       | ExclusiveLock | t
(1 row)

$ TF_WORKSPACE=default tofu plan
No changes. Your infrastructure matches the configuration.
```

- No state file is on your disk. Each workspace is a row in `terraform_remote_state.states`.
- While terminal 1 waits at the prompt, terminal 2 fails with `Error acquiring the state lock`. Other workspaces are not blocked.
- The pg backend cannot record who holds an advisory lock. So `Lock Info` describes the run that failed (here the `plan` in terminal 2), not the waiting `apply`.

Pet names, sizes, lock IDs, and times will be different on your machine.

## Clean up

```bash
tofu destroy                     # in the dev workspace
tofu workspace select default
tofu workspace delete dev
tofu destroy
docker compose down -v           # removes the container and its data
rm -rf .terraform out
```

## Interview takeaways

- Remote state gives a team one source of truth. Locking stops two runs from writing the same state at the same time.
- A lock is per state, so per workspace. A run in `dev` does not block `default`.
- Do not use `-lock=false` to get past a lock. Find out who holds it first. Use `tofu force-unlock` only when you are sure the other run is dead.
- State stores secrets in plain text, even values marked `sensitive`. Restrict who can read the backend. OpenTofu can also encrypt state, for example with the `pbkdf2` or `azure_vault` key provider.
- In Azure, the usual equivalent is the `azurerm` backend: state is a blob in an Azure Storage container, and locking uses a **blob lease**. A crashed run can leave the lease in place, so you may need `tofu force-unlock`. Turn on blob versioning and soft delete, and use Entra ID auth (`use_azuread_auth = true`) with a Managed Identity or workload identity federation instead of storage account keys.
- Related reading: [terraform/03-state-and-backends.md](../../terraform/03-state-and-backends.md) and [terraform/11-opentofu-vs-terraform.md](../../terraform/11-opentofu-vs-terraform.md).
