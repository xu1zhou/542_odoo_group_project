#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 test_01|test_02|test_03"
  exit 1
fi

case "$1" in
  test_01)
    TEST_TAG="test_01"
    TEST_NAME="test_01 — Delete vehicle"
    TEST_MESSAGE="Create a vehicle and verify it can be deleted successfully."
    TEST_NODE="TestVehicleDelete.test_01_vehicle_delete"
    ;;
  test_02)
    TEST_TAG="test_02"
    TEST_NAME="test_02 — Delete service log"
    TEST_MESSAGE="Create a service log and verify it can be deleted successfully."
    TEST_NODE="TestDeleteServiceLog.test_02_delete_service_log"
    ;;
  test_03)
    TEST_TAG="test_03"
    TEST_NAME="test_03 — Update contract log"
    TEST_MESSAGE="Create a contract log and verify its fields can be updated."
    TEST_NODE="TestUpdateContractLog.test_03_update_contract_log"
    ;;
  *)
    echo "Invalid test name: $1"
    echo "Valid values: test_01, test_02, test_03"
    exit 1
    ;;
esac

HIGHLIGHT="\033[1;36m"
LABEL="\033[1;33m"
RESET="\033[0m"

printf "${HIGHLIGHT}=== Fleet Individual Test Run ===${RESET}\n"
printf "${LABEL}Test Name:${RESET} %s\n" "$TEST_NAME"
printf "${LABEL}Test Message:${RESET} %s\n\n" "$TEST_MESSAGE"

sudo docker compose up -d db >/dev/null
DB_NAME="fleet_${1}_db"
LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT

set +e
sudo docker compose run --rm --no-deps odoo bash -lc "export PGPASSWORD=odoo; dropdb -h db -U odoo --if-exists '$DB_NAME'; createdb -h db -U odoo '$DB_NAME'; odoo --db_host db --db_user odoo --db_password odoo -d '$DB_NAME' -i fleet_tests --without-demo=all --test-tags '$TEST_TAG' --stop-after-init --no-http --log-level=test" 2>&1 | tee "$LOG_FILE"
RUN_STATUS=${PIPESTATUS[0]}
set -e

START_LINE="$(grep -m1 -F "Starting ${TEST_NODE} ..." "$LOG_FILE" || true)"
RESULT_LINE="$(grep -m1 -E "odoo.tests.runner: .* of [0-9]+ tests" "$LOG_FILE" || true)"

printf "\n${HIGHLIGHT}=== Highlighted Output ===${RESET}\n"
if [[ -n "$START_LINE" ]]; then
  printf "${LABEL}Test Start:${RESET} %s\n" "$START_LINE"
fi
if [[ -n "$RESULT_LINE" ]]; then
  printf "${LABEL}Result:${RESET} %s\n" "$RESULT_LINE"
fi

exit "$RUN_STATUS"
