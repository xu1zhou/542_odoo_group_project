# CI Workflow Documentation: Deploy & Test Actions

This document explains the two GitHub Actions workflows used in this project:
- **Test** (`test.yml`) — runs automated module tests on every push to `main` or `develop`
- **Deploy** (`deploy.yml`) — spins up a full Odoo stack and deploys modules on pushes/PRs to `main`

Both workflows run on a **self-hosted runner** and rely on Docker to keep the runner environment clean (no Python or Odoo is installed directly on the host).

---

## Table of Contents

- [Infrastructure Overview](#infrastructure-overview)
- [Test Workflow (`test.yml`)](#test-workflow-testyml)
  - [Trigger](#trigger-test)
  - [Step-by-Step Walkthrough](#step-by-step-walkthrough-test)
  - [Flow Diagram](#flow-diagram-test)
- [Deploy Workflow (`deploy.yml`)](#deploy-workflow-deployyml)
  - [Trigger](#trigger-deploy)
  - [Step-by-Step Walkthrough](#step-by-step-walkthrough-deploy)
  - [Flow Diagram](#flow-diagram-deploy)
- [Key Design Decisions](#key-design-decisions)

---

## Infrastructure Overview

```
Self-hosted runner (Ubuntu)
├── snap Docker  (AppArmor restricts bind-mounts to /home/**)
├── $GITHUB_WORKSPACE  →  /opt/actions-runner/_work/...  (blocked by AppArmor)
└── $HOME/odoo-ci-*    →  staging area (allowed by AppArmor)
```

Because the runner runs Docker via **snap**, AppArmor prevents Docker from bind-mounting directories under `/opt/` (where `$GITHUB_WORKSPACE` lives). Both workflows work around this by copying files into `$HOME` before any Docker bind-mount.

Additionally, the runner service is started with `PrivateTmp=yes` (systemd), so `/tmp` inside the runner process is a private mount namespace invisible to Docker daemon processes. Intermediate files are therefore never written to `/tmp`; instead, compose manifests are streamed via stdin (`-f -`).

---

## Test Workflow (`test.yml`)

### Trigger (Test)

```
Push  →  branches: [main, develop]
```

### Step-by-Step Walkthrough (Test)

| # | Step | What it does |
|---|------|-------------|
| 1 | **Checkout repository** | Clones the repository into `$GITHUB_WORKSPACE` using `actions/checkout@v4`. |
| 2 | **Start Postgres** | Runs a standalone `postgres:13` container (`postgres-ci`) with `sudo docker run`. Any leftover container from a previous run is removed first. The step polls `pg_isready` up to 30 times (3 s apart) until Postgres is accepting connections on port 5432. |
| 3 | **Build Odoo CI image** | Builds a custom Docker image (`odoo-ci`) from `.github/docker/Dockerfile` using `sudo docker build … < Dockerfile` (stdin) to avoid AppArmor path restrictions. The image contains Python 3.9, all system libraries required by Odoo 15, a shallow clone of Odoo 15 source, and all Python dependencies. Nothing is installed on the runner. |
| 4 | **Stage workspace for Docker** | Copies the entire workspace from `$GITHUB_WORKSPACE` to `$HOME/odoo-ci-workspace/` so Docker can bind-mount it (AppArmor `home/**` rule). |
| 5 | **Configure Odoo** | Writes `odoo.conf` into the staged workspace. Key settings: `db_host=localhost`, `addons_path` includes both the stock Odoo addons and `/workspace/addons`, `data_dir=/workspace/.odoo-data`. |
| 6 | **Initialize test database** | Runs a temporary container (`--rm`) from `odoo-ci` with `--network host` (so it can reach `postgres-ci` on `localhost:5432`). Creates the `odoo_test` database with `createdb`, then initialises it with `odoo-bin -i base --stop-after-init`. |
| 7 | **Run fleet_tests module tests** | Runs `odoo-bin -i fleet_tests --test-tags /fleet_tests --stop-after-init --log-level=test` in a new container. Only tests tagged with the `fleet_tests` module tag are executed (5 tests). A non-zero exit code fails the workflow. |
| 8 | **Run om_hospital module tests** | Same as above but for the `om_hospital` module (5 tests). |
| 9 | **Stop Postgres** (`always`) | Always runs — removes the `postgres-ci` container and deletes `$HOME/odoo-ci-workspace` to clean up regardless of success or failure. |

### Flow Diagram (Test)

```
Push to main/develop
        │
        ▼
  Checkout code
        │
        ▼
  Start postgres:13 container ──── poll pg_isready (max 90 s)
        │
        ▼
  Build odoo-ci Docker image
  (from .github/docker/Dockerfile via stdin)
        │
        ▼
  Copy workspace → $HOME/odoo-ci-workspace
        │
        ▼
  Write odoo.conf into staged workspace
        │
        ▼
  Init test DB (createdb + odoo-bin -i base)
        │
        ├─── PASS ──▶  Run fleet_tests ──── PASS ──▶  Run om_hospital
        │                    │                               │
        │                  FAIL                            FAIL
        │                    │                               │
        └────────────────────┴───────────────────────────────┘
                                      │
                             Always: cleanup
                    (rm postgres-ci, rm $HOME/odoo-ci-workspace)
```

---

## Deploy Workflow (`deploy.yml`)

### Trigger (Deploy)

```
Push            →  branches: [main]
Pull Request    →  branches: [main, develop]
workflow_dispatch  (manual trigger from GitHub UI)
```

### Step-by-Step Walkthrough (Deploy)

| # | Step | What it does |
|---|------|-------------|
| 1 | **Checkout repository** | Clones the repository into `$GITHUB_WORKSPACE` using `actions/checkout@v4`. |
| 2 | **Stage addons for Docker** | Copies only the `addons/` directory from `$GITHUB_WORKSPACE` to `$HOME/odoo-ci-addons` to satisfy AppArmor's `home/**` bind-mount rule. No `sudo` needed since the runner user owns `$HOME`. |
| 3 | **Start services with Docker Compose** | Streams `docker-compose.yml` through `sed` (replacing `./addons` with `$HOME/odoo-ci-addons`) into `sudo docker compose -p odoo-deploy-ci -f - up -d`. Using a fixed project name (`odoo-deploy-ci`) ensures all subsequent steps share the same compose project. The stack starts two services: `db` (postgres:13) and `odoo` (odoo:15 on port 8069). |
| 4 | **Wait for Postgres to be healthy** | Polls `pg_isready -U odoo` inside the `db` container up to 30 times (3 s apart) using `docker compose exec`. Final call asserts readiness (fails the step if still not ready). |
| 5 | **Initialize test database** | Creates the `odoo_test` database with `createdb` inside `db`, then runs `odoo-bin -i base --stop-after-init` via `docker compose run --no-deps odoo` so a second `db` container is not started. |
| 6 | **Deploy modules** | Placeholder step — prints the module names (`fleet_tests`, `om_hospital`). This is where real deployment steps (SSH, Docker push, registry upload, etc.) would be added. |
| 7 | **Stop services** (`on failure only`) | If **any** previous step fails, tears down the compose stack (`down -v`) and removes `$HOME/odoo-ci-addons`. On success the containers are **intentionally left running** so the deployed Odoo instance stays live. |

### Flow Diagram (Deploy)

```
Push to main / PR to main or develop / manual dispatch
        │
        ▼
  Checkout code
        │
        ▼
  Copy addons → $HOME/odoo-ci-addons
        │
        ▼
  docker compose up -d  (db + odoo)
  [project: odoo-deploy-ci]
        │
        ▼
  Poll pg_isready in db container (max 90 s)
        │
        ▼
  createdb odoo_test  +  odoo-bin -i base (--stop-after-init)
        │
        ▼
  Deploy modules (fleet_tests, om_hospital)
        │
        ├─── SUCCESS ──▶  Containers left running (Odoo live on :8069)
        │
        └─── FAILURE ──▶  docker compose down -v
                          rm $HOME/odoo-ci-addons
```

---

## Key Design Decisions

| Problem | Solution |
|---------|----------|
| snap Docker's AppArmor blocks `/opt/**` bind-mounts | Files are copied to `$HOME` before any Docker volume mount |
| Runner's `PrivateTmp=yes` makes `/tmp` invisible to Docker | Compose YAML is streamed via stdin (`-f -`) instead of written to a temp file |
| Runner user is not in the `docker` group | All `docker` and `docker compose` commands are prefixed with `sudo` |
| Avoid starting duplicate services in the deploy workflow | `docker compose run --no-deps` reuses the already-running `db` container |
| Keep runner environment clean | Python, Odoo, and all system dependencies live only inside Docker images |
| Prevent stale containers from breaking the next run | Test workflow always removes `postgres-ci`; deploy workflow removes on failure |
