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
- At least one vehicle record already exists (needed for TC-F-03).
- Run:  pip install -r requirements.txt
        python -m pytest test_fleet_selenium.py -v
"""

import time
import unittest

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from base_test import ADMIN_PASS, ADMIN_USER, BASE_URL, OdooBaseTest


class FleetSeleniumTests(OdooBaseTest):
    """Five Selenium test cases covering the Fleet module."""

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

        # Navigate to Fleet > Vehicles > Fleet
        self.driver.get(f"{BASE_URL}/odoo/fleet")
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'o_list_view') or contains(@class,'o_kanban_view')]")
            )
        )

        self.click_new()

        # License plate field
        self.fill_field("license_plate", "SEL-TEST-001")

        # Model (Many2one) – type a character to trigger search and pick first result
        model_input = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@name='model_id']//input")
            )
        )
        model_input.send_keys("a")
        time.sleep(1)

        first_option = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//ul[contains(@class,'ui-autocomplete')]//li[1] | "
                 "//div[contains(@class,'o_dropdown_menu')]//li[1]")
            )
        )
        first_option.click()
        time.sleep(0.5)

        self.click_save()
        time.sleep(1)

        self.assertFalse(
            self.has_error_message(),
            "An error message appeared after saving the vehicle.",
        )
        # Verify the license plate is shown on the saved record
        plate_field = self.find_or_none(
            By.XPATH,
            "//input[@name='license_plate'] | "
            "//span[@name='license_plate']",
        )
        self.assertIsNotNone(
            plate_field,
            "Could not find the license plate field on the saved vehicle form.",
        )

    # ── TC-F-03  Add odometer reading (positive) ─────────────────────────────

    def test_03_add_odometer_reading(self):
        """TC-F-03: Open the first vehicle in the list and add a new odometer reading."""
        self.login()

        self.driver.get(f"{BASE_URL}/odoo/fleet")
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'o_list_view') or contains(@class,'o_kanban_view')]")
            )
        )

        # Open the first vehicle record
        first_record = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//table[contains(@class,'o_list_table')]//tbody//tr[1] | "
                 "//div[contains(@class,'o_kanban_record')][1]")
            )
        )
        first_record.click()
        time.sleep(1)

        # Click the 'Odometer' smart button or navigate via the action menu
        odometer_btn = self.find_or_none(
            By.XPATH,
            "//button[.//span[contains(text(),'Odometer')] or "
            "contains(normalize-space(.),'Odometer')]"
        )
        if odometer_btn:
            odometer_btn.click()
            time.sleep(1)
            self.click_new()
        else:
            # Fallback: navigate directly to odometer list
            self.driver.get(f"{BASE_URL}/odoo/fleet/odometer")
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "o_list_view"))
            )
            self.click_new()

        # Fill in the odometer value
        self.fill_field("value", "5000")

        self.click_save()
        time.sleep(1)

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

        self.driver.get(f"{BASE_URL}/odoo/fleet")
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'o_list_view') or contains(@class,'o_kanban_view')]")
            )
        )

        self.click_new()

        # Fill in only the license plate; intentionally leave the required Model empty
        self.fill_field("license_plate", "SEL-FAIL-002")

        # Clear the model field if it has a default value
        try:
            model_input = self.driver.find_element(
                By.XPATH, "//div[@name='model_id']//input"
            )
            model_input.clear()
        except Exception:
            pass

        self.click_save()
        time.sleep(1)

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
