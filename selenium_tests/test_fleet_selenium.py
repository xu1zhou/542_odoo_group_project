# -*- coding: utf-8 -*-
"""
Selenium test suite for the **Fleet** Odoo module.

Test cases
──────────
TC-F-01  test_01_login_valid            Login with valid admin credentials         (positive / login)
TC-F-02  test_02_create_vehicle         Create a new fleet vehicle                 (positive)
TC-F-03  test_03_add_odometer_reading   Add an odometer reading to an existing vehicle (positive)
TC-F-04  test_04_login_invalid          Login with wrong password – expect error   (negative)
TC-F-05  test_05_create_vehicle_no_model  Save a vehicle form without the required Model – expect validation error (negative)

Prerequisites
─────────────
- Odoo running at http://localhost:8069 with the Fleet module installed.
- Run:  pip install -r requirements.txt
        python -m pytest test_fleet_selenium.py -v
"""

import json
import re
import time
import unittest
import xmlrpc.client
from urllib.request import Request, urlopen

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_test import ADMIN_PASS, ADMIN_USER, BASE_URL, OdooBaseTest


class FleetSeleniumTests(OdooBaseTest):
    """Five Selenium test cases covering the Fleet module."""

    _created_vehicle_id: int | None = None
    _created_odometer_id: int | None = None

    # ── Class-level setup / teardown ─────────────────────────────────────────

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_data()
        super().tearDownClass()

    # ── RPC helpers ──────────────────────────────────────────────────────────

    @classmethod
    def _odoo_rpc(cls):
        """Return (db_name, uid, models_proxy) for XML-RPC calls."""
        req = Request(
            f"{BASE_URL}/web/database/list",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        db_name = json.loads(urlopen(req).read())["result"][0]
        common = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/common")
        uid = common.authenticate(db_name, ADMIN_USER, ADMIN_PASS, {})
        models = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/object")
        return db_name, uid, models

    @classmethod
    def _cleanup_test_data(cls):
        """Delete every record created during this test run plus stale test records."""
        try:
            db_name, uid, models = cls._odoo_rpc()

            def unlink_one(model, rec_id):
                if rec_id:
                    models.execute_kw(db_name, uid, ADMIN_PASS, model, "unlink", [[rec_id]])

            # Odometer first (references vehicle)
            unlink_one("fleet.vehicle.odometer", cls._created_odometer_id)
            unlink_one("fleet.vehicle", cls._created_vehicle_id)

            # Sweep any leftover vehicles from previous runs
            stale_ids = models.execute_kw(
                db_name, uid, ADMIN_PASS,
                "fleet.vehicle", "search",
                [[["license_plate", "like", "SEL-"]]],
            )
            for vid in stale_ids:
                odo_ids = models.execute_kw(
                    db_name, uid, ADMIN_PASS,
                    "fleet.vehicle.odometer", "search",
                    [[["vehicle_id", "=", vid]]],
                )
                for oid in odo_ids:
                    unlink_one("fleet.vehicle.odometer", oid)
                unlink_one("fleet.vehicle", vid)
        except Exception as exc:
            print(f"\nWarning: fleet test-data cleanup failed: {exc}")

    @staticmethod
    def _id_from_url(url: str) -> int | None:
        """Extract the record id from an Odoo URL fragment (#...&id=N)."""
        m = re.search(r"[#&]id=(\d+)", url)
        return int(m.group(1)) if m else None

    # ── Navigation helper ────────────────────────────────────────────────────

    def _dismiss_any_modal(self):
        """Close any blocking modal dialog (e.g. Fleet onboarding tour)."""
        from selenium.webdriver.common.keys import Keys
        modal = self.find_or_none(
            By.XPATH, "//div[@role='dialog' and contains(@class,'modal')]"
        )
        if modal and modal.is_displayed():
            # Try common close/dismiss buttons first
            close_btn = self.find_or_none(
                By.XPATH,
                "//div[@role='dialog'][not(contains(@class,'d-none'))]"
                "//*[contains(@class,'btn-close') or "
                "contains(normalize-space(.),'Close') or "
                "contains(normalize-space(.),'Discard') or "
                "@data-bs-dismiss='modal']"
            )
            if close_btn:
                close_btn.click()
            else:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

    def _navigate_to_fleet_section(self, section_label: str = "Fleet"):
        """Navigate to the Fleet app and click *section_label* in the top navbar.

        For the default "Fleet" section the app auto-loads the vehicles list, so
        no extra click is required. For other sections (Reporting, Configuration)
        the relevant nav entry is clicked explicitly.
        """
        self.click_home_menu_toggle()

        # Dismiss any modal that may be blocking the app tile (e.g. Fleet tour dialog)
        self._dismiss_any_modal()

        fleet_app = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//*[contains(@class,'o_app') and normalize-space(.)='Fleet']")
            )
        )
        fleet_app.click()

        # Wait for the Fleet section menu bar to be visible
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//nav[contains(@class,'o_main_navbar')]"
                 "//*[contains(@class,'o_menu_sections') or contains(@class,'o_nav_entry')]")
            )
        )

        # If a non-default section is requested, click it explicitly
        if section_label != "Fleet":
            section_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     f"//nav[contains(@class,'o_main_navbar')]"
                     f"//*[normalize-space(text())='{section_label}'] | "
                     f"//*[contains(@class,'o_nav_entry') and normalize-space(text())='{section_label}'] | "
                     f"//*[contains(@class,'o_menu_sections')]//*[normalize-space(text())='{section_label}']")
                )
            )
            section_btn.click()
            try:
                sub_item = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         f"//nav[contains(@class,'o_main_navbar')]"
                         f"//div[contains(@class,'dropdown-menu') and contains(@class,'d-block')]"
                         f"//a[normalize-space(text())='{section_label}']")
                    )
                )
                sub_item.click()
            except TimeoutException:
                pass

        # Fleet app auto-loads the vehicle list; wait for it
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//*[contains(@class,'o_list_view') or contains(@class,'o_kanban_view')]")
            )
        )

        # Switch to list view if we landed on kanban (list view makes New button reliable)
        if not self.find_or_none(By.CLASS_NAME, "o_list_view"):
            list_btn = self.find_or_none(
                By.XPATH,
                "//button[contains(@class,'o_switch_view') and contains(@class,'o_list')] | "
                "//button[@data-tooltip='List']"
            )
            if list_btn:
                list_btn.click()
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "o_list_view"))
                )

    # ── TC-F-01  Login (positive / must-have) ────────────────────────────────

    def test_01_login_valid(self):
        """TC-F-01: Logging in with valid admin credentials redirects to the home page."""
        result = self.login(ADMIN_USER, ADMIN_PASS)
        self.assertTrue(
            result,
            "Expected successful login to redirect away from /web/login, "
            "but the browser stayed on the login page.",
        )
        self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "o_main_navbar"))
        )
        current_url = self.driver.current_url
        self.assertNotIn(
            "/web/login",
            current_url,
            f"URL still contains /web/login after successful login: {current_url}",
        )

    # ── TC-F-02  Create vehicle (positive) ───────────────────────────────────

    def test_02_create_vehicle(self):
        """TC-F-02: Create a new fleet vehicle with a license plate and model."""
        self.login()
        self._navigate_to_fleet_section()

        self.click_new()

        self.fill_field("license_plate", "SEL-TEST-001")

        # Model (Many2one) – ActionChains to reliably trigger the autocomplete
        model_input = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@name='model_id']//input")
            )
        )
        ActionChains(self.driver).move_to_element(model_input).click().send_keys("a").perform()

        first_option = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//ul[contains(@class,'ui-autocomplete')"
                 " and not(contains(@style,'display: none'))]//li[1] | "
                 "//div[contains(@class,'o_dropdown_menu')]//li[1]")
            )
        )
        first_option.click()

        self.click_save()

        self.__class__._created_vehicle_id = self._id_from_url(self.driver.current_url)

        self.assertFalse(
            self.has_error_message(),
            "An error message appeared after saving the vehicle.",
        )
        plate_field = self.find_or_none(
            By.XPATH,
            "//input[@name='license_plate'] | //span[@name='license_plate']",
        )
        self.assertIsNotNone(
            plate_field,
            "Could not find the license plate field on the saved vehicle form.",
        )

    # ── TC-F-03  Add odometer reading (positive) ─────────────────────────────

    def test_03_add_odometer_reading(self):
        """TC-F-03: Open the first vehicle and add a new odometer reading via the smart button."""
        self.login()
        self._navigate_to_fleet_section()

        # Open the first vehicle record in the list
        first_record = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//table[contains(@class,'o_list_table')]//tbody//tr[1] | "
                 "//div[contains(@class,'o_kanban_record')][1]")
            )
        )
        first_record.click()
        self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "o_form_view"))
        )

        # Click the Odometer smart button in the button box
        odometer_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//div[contains(@class,'oe_button_box')]"
                 "//button[contains(normalize-space(.),'km') or "
                 "contains(normalize-space(.),'mi') or "
                 "contains(normalize-space(.),'Odometer')]")
            )
        )
        odometer_btn.click()
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//*[contains(@class,'o_list_view') or contains(@class,'o_form_view')]")
            )
        )

        self.click_new()

        self.fill_field("value", "5000")

        self.click_save()

        self.__class__._created_odometer_id = self._id_from_url(self.driver.current_url)

        self.assertFalse(
            self.has_error_message(),
            "An error message appeared after saving the odometer reading.",
        )

    # ── TC-F-04  Login with invalid credentials (negative) ───────────────────

    def test_04_login_invalid(self):
        """TC-F-04: Attempting login with a wrong password must display an error."""
        result = self.login(ADMIN_USER, "bad_fleet_password_999")
        self.assertFalse(
            result,
            "Expected login to fail with an invalid password, "
            "but the browser was redirected away from /web/login.",
        )
        error_present = False
        error_selectors = [
            (By.XPATH, "//div[contains(@class,'alert-danger')]"),
            (By.XPATH, "//p[contains(@class,'alert')]"),
            (By.XPATH, "//*[contains(text(),'Wrong login/password')]"),
            (By.XPATH, "//*[contains(text(),'Invalid credentials')]"),
        ]
        for by, value in error_selectors:
            el = self.find_or_none(by, value)
            if el and el.is_displayed():
                error_present = True
                break

        self.assertTrue(
            error_present,
            "No error message was displayed after submitting invalid credentials.",
        )

    # ── TC-F-05  Save vehicle without required model field (negative) ─────────

    def test_05_create_vehicle_no_model(self):
        """TC-F-05: Saving a new vehicle without the required Model field must raise a validation error."""
        self.login()
        self._navigate_to_fleet_section()

        self.click_new()

        self.fill_field("license_plate", "SEL-FAIL-002")

        # Clear the model field if it has a default value
        model_inputs = self.driver.find_elements(
            By.XPATH, "//div[@name='model_id']//input"
        )
        for inp in model_inputs:
            inp.clear()

        self.click_save()

        try:
            self.wait.until(
                lambda d: self.has_error_message()
                or d.find_elements(
                    By.XPATH,
                    "//div[@name='model_id' and contains(@class,'o_field_invalid')] | "
                    "//input[@name='model_id' and contains(@class,'o_field_invalid')]",
                )
            )
        except TimeoutException:
            pass

        validation_present = (
            self.has_error_message()
            or self.find_or_none(
                By.XPATH,
                "//div[@name='model_id' and contains(@class,'o_field_invalid')] | "
                "//input[@name='model_id' and contains(@class,'o_field_invalid')]",
            ) is not None
        )
        self.assertTrue(
            validation_present,
            "Expected a validation error when saving a vehicle without a model, "
            "but no error indicator was found.",
        )
        self.click_discard()


if __name__ == "__main__":
    unittest.main(verbosity=2)

