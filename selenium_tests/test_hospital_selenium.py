# -*- coding: utf-8 -*-
"""
Selenium test suite for the **om_hospital** Odoo module.

Test cases
──────────
TC-H-01  test_01_login_valid          Login with valid admin credentials          (positive / login)
TC-H-02  test_02_create_patient       Create a new patient with valid data         (positive)
TC-H-03  test_03_create_appointment   Create an appointment for an existing patient (positive)
TC-H-04  test_04_login_invalid        Login with wrong password – expect error     (negative)
TC-H-05  test_05_create_patient_no_name  Save a patient form without a name – expect validation error (negative)

Prerequisites
─────────────
- Odoo running at http://localhost:8069 with the om_hospital module installed.
- At least one patient record already exists in the database (needed for TC-H-03).
- Run:  pip install -r requirements.txt
        python -m pytest test_hospital_selenium.py -v
"""

import time
import unittest

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from base_test import ADMIN_PASS, ADMIN_USER, BASE_URL, OdooBaseTest


class HospitalSeleniumTests(OdooBaseTest):
    """Five Selenium test cases covering the om_hospital module."""

    # ── TC-H-01  Login (positive / must-have) ────────────────────────────────

    def test_01_login_valid(self):
        """TC-H-01: Logging in with valid admin credentials redirects to the home page."""
        result = self.login(ADMIN_USER, ADMIN_PASS)
        self.assertTrue(
            result,
            "Expected successful login to redirect away from /web/login, "
            "but the browser stayed on the login page.",
        )
        # Confirm the Odoo home bar is present
        self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "o_main_navbar"))
        )
        current_url = self.driver.current_url
        self.assertNotIn(
            "/web/login",
            current_url,
            f"URL still contains /web/login after successful login: {current_url}",
        )

    # ── TC-H-02  Create patient (positive) ───────────────────────────────────

    def test_02_create_patient(self):
        """TC-H-02: Create a new patient record with name, age and gender."""
        self.login()

        # Navigate: Hospital → Patients → Patients
        self.driver.get(f"{BASE_URL}/odoo/hospital/patients")
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_list_view")))

        self.click_new()

        # Fill in the patient form
        self.fill_field("name", "Selenium Test Patient")
        self.fill_field("age", "30")

        # Select gender – Odoo renders a <select> or a list of radio buttons
        gender_select = self.find_or_none(By.NAME, "gender")
        if gender_select and gender_select.tag_name == "select":
            from selenium.webdriver.support.ui import Select
            Select(gender_select).select_by_value("male")
        else:
            male_option = self.find_or_none(
                By.XPATH,
                "//div[contains(@class,'o_field_widget') and @name='gender']"
                "//option[@value='male'] | "
                "//select[@name='gender']/option[@value='male']",
            )
            if male_option:
                male_option.click()

        self.click_save()
        time.sleep(1)

        # Verify the record was saved – reference field becomes visible
        reference = self.find_or_none(
            By.XPATH,
            "//div[@name='reference']//span | "
            "//input[@name='reference']",
        )
        self.assertIsNotNone(
            reference,
            "Could not find the reference field on the saved patient form.",
        )
        self.assertFalse(
            self.has_error_message(),
            "An error message appeared after saving the patient.",
        )

    # ── TC-H-03  Create appointment (positive) ───────────────────────────────

    def test_03_create_appointment(self):
        """TC-H-03: Create an appointment by selecting an existing patient and doctor."""
        self.login()

        # Navigate to Appointments list
        self.driver.get(f"{BASE_URL}/odoo/hospital/appointments")
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_list_view")))

        self.click_new()

        # Patient field (Many2one) – type and select from dropdown
        patient_input = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@name='patient_id']//input")
            )
        )
        patient_input.send_keys("a")  # start typing to trigger search
        time.sleep(1)

        # Pick the first suggestion from the many2one dropdown
        first_option = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//ul[contains(@class,'ui-autocomplete')]//li[1] | "
                 "//div[contains(@class,'o_dropdown_menu')]//li[1]")
            )
        )
        first_option.click()
        time.sleep(0.5)

        # Doctor field
        doctor_input = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@name='doctor_id']//input")
            )
        )
        doctor_input.send_keys("a")
        time.sleep(1)

        first_doctor = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//ul[contains(@class,'ui-autocomplete')]//li[1] | "
                 "//div[contains(@class,'o_dropdown_menu')]//li[1]")
            )
        )
        first_doctor.click()
        time.sleep(0.5)

        self.click_save()
        time.sleep(1)

        self.assertFalse(
            self.has_error_message(),
            "An error message appeared after saving the appointment.",
        )
        # The appointment reference should now be a sequence like APT/2024/0001
        appt_name = self.find_or_none(
            By.XPATH,
            "//div[@name='name']//span | //input[@name='name']"
        )
        self.assertIsNotNone(
            appt_name,
            "Could not find the appointment reference after saving.",
        )

    # ── TC-H-04  Login with invalid credentials (negative) ───────────────────

    def test_04_login_invalid(self):
        """TC-H-04: Attempting login with a wrong password must display an error."""
        result = self.login(ADMIN_USER, "wrong_password_xyz")
        self.assertFalse(
            result,
            "Expected login to fail with an invalid password, "
            "but the browser was redirected away from /web/login.",
        )
        # Odoo renders an alert box or red text on the login page
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

    # ── TC-H-05  Save patient without required name (negative) ───────────────

    def test_05_create_patient_no_name(self):
        """TC-H-05: Saving a patient form without the required Name field must raise a validation error."""
        self.login()

        self.driver.get(f"{BASE_URL}/odoo/hospital/patients")
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_list_view")))

        self.click_new()

        # Intentionally leave the 'name' field blank and attempt to save
        self.fill_field("age", "25")

        self.click_save()
        time.sleep(1)

        # Odoo should show a validation tooltip or dialog about the required field
        validation_present = (
            self.has_error_message()
            or self.find_or_none(
                By.XPATH,
                "//input[@name='name' and contains(@class,'o_field_invalid')] | "
                "//div[@name='name' and contains(@class,'o_field_invalid')]",
            ) is not None
        )
        self.assertTrue(
            validation_present,
            "Expected a validation error when saving a patient without a name, "
            "but no error indicator was found.",
        )
        self.click_discard()


if __name__ == "__main__":
    unittest.main(verbosity=2)
