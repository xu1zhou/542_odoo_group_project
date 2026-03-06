# Odoo 15 Group Project (Docker)

This repository provides a **reproducible Odoo 15 Community** development environment using **Docker Compose**, plus the addons and Python tests required for the project:
- `addons/om_hospital` (module + 5 Python tests)
- `addons/fleet_tests` (Fleet-focused module + 5 Python tests)

---

## Contents

- [Prerequisites](#prerequisites)
- [Install Docker & Compose](#install-docker--compose)
- [Clone the Repository](#clone-the-repository)
- [Start Odoo](#start-odoo)
- [Create Databases](#create-databases)
- [Install Modules in Odoo (Demo DB)](#install-modules-in-odoo-demo-db)
- [Run Tests (Test DB)](#run-tests-test-db)
- [Useful Commands](#useful-commands)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Ubuntu (24.04 LTS recommended, 22.04 works)
- Internet access (to pull Docker images)
- GitHub access to this repository

---

## Install Docker & Compose

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-v2
sudo systemctl enable --now docker
```
Allow Docker without sudo:
```bash
sudo usermod -aG docker $USER
newgrp docker
```
Verify:
```bash
docker --version
docker compose version
docker ps
```
If docker ps shows a permission error, log out and log back in, then retry.

## Clone the Repository
```bash
cd ~
git clone https://github.com/KDSingh277/542_odoo_group_project.git
cd 542_odoo_group_project
```

## Start Odoo

Start the stack:
```bash
docker compose up -d
```
Check containers:
```bash
docker compose ps
```
Follow logs (optional):
```bash
docker compose logs -f odoo
```
Open Odoo in your browser:

http://localhost:8069

## Create Databases

Go to the Odoo Database Manager:
http://localhost:8069/web/database/manager

Create two databases (recommended):

Demo DB (any name, ) i used db Karan, doesn't matter what you use
✅ Load Demo Data (for exploring UI)
Test DB (name: testdb)
❌ Do NOT load demo data (for running automated tests)

## Install Modules in Odoo (Demo DB)
In your Demo DB (the one with demo data):

Enable Developer Mode:
Settings → **Activate the developer mode**

Go to **Apps**

Click **Update Apps List**

Clear any filter chips (e.g., “Apps”, “Module …”) if present

Install these modules:

**fleet**
**om_hospital**
**fleet_tests**

`om_hospital` and `fleet_tests` come from the repo’s `addons/` folder.

## Run Tests (Test DB)

We run only our module tests (not the full Odoo test suite) using --test-tags.

Run Fleet tests (5 tests)
```bash
docker compose exec odoo odoo -d testdb -u fleet_tests \
  --test-tags /fleet_tests \
  --stop-after-init --no-http --log-level=test
```
Run Hospital tests (5 tests)
```bash
docker compose exec odoo odoo -d testdb -u om_hospital \
  --test-tags /om_hospital \
  --stop-after-init --no-http --log-level=test
```
