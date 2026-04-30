# Selenium Tests — Odoo 15 Group Project

This directory contains **Selenium WebDriver** UI tests for the two custom Odoo modules:

| Module | Test file |
|--------|-----------|
| `om_hospital` | `test_hospital_selenium.py` |
| Fleet (built-in) | `test_fleet_selenium.py` |

Each file contains **5 test cases** following the required breakdown:

| # | Test Case | Type |
|---|-----------|------|
| 01 | Login with valid admin credentials | ✅ Positive (Login — **mandatory**) |
| 02 | Create a record with valid data | ✅ Positive (normal operation) |
| 03 | Perform a follow-up operation (appointment / odometer) | ✅ Positive (normal operation) |
| 04 | Login with wrong password | ❌ Negative (failed) |
| 05 | Save a form with a missing required field | ❌ Negative (failed) |

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | ≥ 3.9 |
| Google Chrome | Latest stable |
| Odoo | Running at `http://localhost:8069` |
| Modules | `om_hospital` **and** `fleet` installed on the demo database |
| Demo data | At least one Patient, one Doctor, and one Vehicle record must exist (needed by TC-H-03 and TC-F-03) |

---

## Setup

```bash
# 1. Start Odoo (from repo root)
docker compose up -d

# 2. Install Python dependencies
cd selenium_tests
pip install -r requirements.txt
```

> **`webdriver-manager`** automatically downloads the matching ChromeDriver.  
> If you prefer to manage ChromeDriver manually, install Chrome + a matching ChromeDriver on your `PATH` and remove `webdriver-manager` from `requirements.txt`.

---

## macOS Setup Guide

### 1 — Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2 — Install Python ≥ 3.9

macOS ships an old system Python. Install a modern version via Homebrew:

```bash
brew install python@3.11
```

Verify:

```bash
python3 --version   # should print 3.11.x or later
```

### 3 — Install Google Chrome

Download and install from <https://www.google.com/chrome/>, **or** use Homebrew Cask:

```bash
brew install --cask google-chrome
```

> `webdriver-manager` downloads the matching ChromeDriver automatically, so you do **not** need to install ChromeDriver separately.

### 4 — Install Docker Desktop (to run Odoo)

Download from <https://www.docker.com/products/docker-desktop/> or install via Homebrew:

```bash
brew install --cask docker
open /Applications/Docker.app   # start Docker Desktop
```

Wait until the Docker whale icon in the menu bar is steady (not animated).

### 5 — Start Odoo

From the **repository root**:

```bash
docker compose up -d
```

Open <http://localhost:8069> in your browser and confirm Odoo loads before running the tests.

### 6 — Create and activate a virtual environment (recommended)

```bash
cd selenium_tests
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 7 — Run the tests

```bash
# All tests
python -m pytest test_hospital_selenium.py test_fleet_selenium.py -v

# Hospital module only
python -m pytest test_hospital_selenium.py -v

# Fleet module only
python -m pytest test_fleet_selenium.py -v
```

### macOS-specific notes

| Topic | Detail |
|-------|--------|
| **Apple Silicon (M1/M2/M3)** | `webdriver-manager` downloads an ARM64 ChromeDriver automatically; no extra steps needed. |
| **Gatekeeper / "developer cannot be verified"** | If macOS blocks ChromeDriver, run: `xattr -d com.apple.quarantine $(which chromedriver)` |
| **Headless vs. visible window** | Tests run headless by default. To watch them live, comment out `--headless` in `base_test.py` (see [Notes](#notes) below). |
| **Python path on Apple Silicon** | Homebrew installs Python in `/opt/homebrew/bin/`. If `python3` is not found, add `/opt/homebrew/bin` to your `PATH` in `~/.zshrc`: `export PATH="/opt/homebrew/bin:$PATH"` |

---

## Running the Tests

```bash
# Run all Selenium tests
python -m pytest test_hospital_selenium.py test_fleet_selenium.py -v

# Run only hospital tests
python -m pytest test_hospital_selenium.py -v

# Run only fleet tests
python -m pytest test_fleet_selenium.py -v

# Run a single test case (e.g. TC-H-01)
python -m pytest test_hospital_selenium.py::HospitalSeleniumTests::test_01_login_valid -v
```

### Alternative: `unittest` runner

```bash
python -m unittest test_hospital_selenium -v
python -m unittest test_fleet_selenium -v
```

---

## Configuration

All configurable constants live in **`base_test.py`**:

```python
BASE_URL   = "http://localhost:8069"   # Odoo URL
ADMIN_USER = "admin"                   # Odoo admin username
ADMIN_PASS = "admin"                   # Odoo admin password
DEFAULT_WAIT = 10                      # Max seconds to wait for elements
```

Edit `base_test.py` to point at a different host, port, or credentials.

---

## Test-case Summaries

### Hospital module (`test_hospital_selenium.py`)

| ID | Method | Description |
|----|--------|-------------|
| TC-H-01 | `test_01_login_valid` | Login with `admin` / `admin` — browser leaves `/web/login` and the navbar is present |
| TC-H-02 | `test_02_create_patient` | Open Patients list → New → fill Name/Age/Gender → Save — no error, reference field visible |
| TC-H-03 | `test_03_create_appointment` | Open Appointments list → New → pick patient & doctor → Save — no error, sequence reference visible |
| TC-H-04 | `test_04_login_invalid` | Login with wrong password — browser stays on `/web/login` and an error banner is shown |
| TC-H-05 | `test_05_create_patient_no_name` | Open Patients form → fill Age only → Save — `name` field highlighted as invalid **or** error dialog shown |

### Fleet module (`test_fleet_selenium.py`)

| ID | Method | Description |
|----|--------|-------------|
| TC-F-01 | `test_01_login_valid` | Login with `admin` / `admin` — browser leaves `/web/login` and the navbar is present |
| TC-F-02 | `test_02_create_vehicle` | Open Fleet list → New → fill License Plate + Model → Save — no error |
| TC-F-03 | `test_03_add_odometer_reading` | Open first vehicle → Odometer button → New → fill value → Save — no error |
| TC-F-04 | `test_04_login_invalid` | Login with wrong password — stays on login page with error banner |
| TC-F-05 | `test_05_create_vehicle_no_model` | Open Fleet form → fill License Plate only → Save — `model_id` highlighted **or** error dialog shown |

---

## Notes

- Tests run in **headless Chrome** by default. Remove `--headless` from `base_test.py` to watch them run in a visible window.
- The test classes share a single browser session per class (`setUpClass` / `tearDownClass`).  Tests are **ordered** (01 → 05) to avoid state conflicts.
- TC-H-03 and TC-F-03 rely on at least one existing record; if the demo database is empty, seed it first via the Odoo UI or the Docker-based test setup described in the root `README.md`.
