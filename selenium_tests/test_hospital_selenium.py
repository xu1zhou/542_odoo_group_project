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

_TEST_DOCTOR_NAME = "Adam"


class HospitalSeleniumTests(OdooBaseTest):
    """Five Selenium test cases covering the om_hospital module."""

    # IDs of records created during the test run (populated by each test).
    _created_doctor_id: int | None = None
    _created_patient_id: int | None = None
    _created_appointment_id: int | None = None

    # ── RPC helper ────────────────────────────────────────────────────────────

    @classmethod
    def _odoo_rpc(cls):
        """Return (db_name, uid, models_proxy) for XML-RPC calls."""
        req = Request(
            f"{BASE_URL}/web/database/list",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1, "params": {}}).encode(),
            headers={"Content-Type": "application/json"},
        )
        db_name = json.loads(urlopen(req, timeout=5).read())["result"][0]
        common = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/common")
        uid = common.authenticate(db_name, ADMIN_USER, ADMIN_PASS, {})
        models = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/object")
        return db_name, uid, models

    # ── Setup / teardown ──────────────────────────────────────────────────────

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._ensure_test_doctor()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_data()
        super().tearDownClass()

    @classmethod
    def _ensure_test_doctor(cls):
        """Create a doctor record via XML-RPC if none exist (needed for TC-H-03)."""
        try:
            db_name, uid, models = cls._odoo_rpc()
            existing = models.execute_kw(
                db_name, uid, ADMIN_PASS,
                "hospital.doctor", "search_read", [[]],
                {"fields": ["id", "doctor_name"], "limit": 1},
            )
            if not existing:
                cls._created_doctor_id = models.execute_kw(
                    db_name, uid, ADMIN_PASS,
                    "hospital.doctor", "create",
                    [{"doctor_name": _TEST_DOCTOR_NAME, "gender": "male"}],
                )
        except Exception as exc:
            print(f"\nWarning: could not ensure test doctor via RPC: {exc}")

    @classmethod
    def _cleanup_test_data(cls):
        """Delete every record created during this test run, plus any stale test
        records left by earlier runs (identified by well-known test names).

        Note: hospital.appointment.unlink() is overridden to call ensure_one(),
        so appointments must be deleted individually.
        """
        try:
            db_name, uid, models = cls._odoo_rpc()

            def unlink_one(model, rec_id):
                if rec_id:
                    models.execute_kw(db_name, uid, ADMIN_PASS, model, "unlink", [[rec_id]])

            def unlink_many(model, ids):
                for rec_id in (ids or []):
                    unlink_one(model, rec_id)

            # --- Delete records tracked by ID for this run (most precise) ---
            # Appointments first (FK references patients/doctors).
            unlink_one("hospital.appointment", cls._created_appointment_id)
            unlink_one("hospital.patient",     cls._created_patient_id)
            unlink_one("hospital.doctor",      cls._created_doctor_id)

            # --- Sweep any leftover test patients and their appointments -----
            stale_patient_ids = models.execute_kw(
                db_name, uid, ADMIN_PASS,
                "hospital.patient", "search",
                [[["name", "=", "Selenium Test Patient"]]],
            )
            if stale_patient_ids:
                stale_appt_ids = models.execute_kw(
                    db_name, uid, ADMIN_PASS,
                    "hospital.appointment", "search",
                    [[["patient_id", "in", stale_patient_ids]]],
                )
                unlink_many("hospital.appointment", stale_appt_ids)
                unlink_many("hospital.patient",     stale_patient_ids)
        except Exception as exc:
            print(f"\nWarning: test-data cleanup failed: {exc}")

    @staticmethod
    def _id_from_url(url: str) -> int | None:
        """Parse the record id from an Odoo form URL fragment (id=N)."""
        m = re.search(r"[#&]id=(\d+)", url)
        return int(m.group(1)) if m else None

    # ── Navigation helper ─────────────────────────────────────────────────────

    def _navigate_to_hospital_section(self, section_label: str):
        """Navigate to a Hospital module section via the UI menu.

        Steps:
        1. Click the top-left home/apps nav button.
        2. Click the 'Hospital' app tile in the apps menu.
        3. Click *section_label* in the top horizontal menu bar
           (e.g. 'Patients' or 'Appointments').
        """
        # 1. Click the top-left nav button (home/apps toggle)
        self.click_home_menu_toggle()

        # 2. Click the 'Hospital' app tile
        hospital_app = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//*[contains(@class,'o_app') and normalize-space(.)='Hospital']")
            )
        )
        hospital_app.click()
        # Wait until the Hospital section menu bar is visible in the top navbar
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//nav[contains(@class,'o_main_navbar')]"
                 "//*[contains(@class,'o_menu_sections') or contains(@class,'o_nav_entry')]")
            )
        )

        # 3. Click the section in the top horizontal menu bar
        section_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 f"//nav[contains(@class,'o_main_navbar')]"
                 f"//*[normalize-space(text())='{section_label}'] | "
                 f"//*[contains(@class,'o_nav_entry') and "
                 f"normalize-space(text())='{section_label}'] | "
                 f"//*[contains(@class,'o_menu_sections')]"
                 f"//*[normalize-space(text())='{section_label}']")
            )
        )
        section_btn.click()
        # If the section is a dropdown, click the matching sub-item
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
            pass  # no sub-menu; section navigated directly
        # Wait until the list view for the section has loaded
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//*[contains(@class,'o_list_view') or contains(@class,'o_kanban_view')]")
            )
        )

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

        # Navigate: home toggle → Hospital app → Patients (top bar) → New
        self._navigate_to_hospital_section("Patients")
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_list_view")))

        self.click_new()

        # Fill in the patient form
        self.fill_field("name", "Selenium Test Patient")
        self.fill_field("age", "30")

        # Select gender – Odoo renders a <select> or a list of radio buttons
        gender_select = self.find_or_none(By.NAME, "gender")
        if gender_select and gender_select.tag_name == "select":
            from selenium.webdriver.support.ui import Select
            Select(gender_select).select_by_visible_text("Male")
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

        # Store created patient ID so tearDownClass can clean it up.
        self.__class__._created_patient_id = self._id_from_url(self.driver.current_url)

        # Verify the record was saved – reference field becomes visible
        reference = self.find_or_none(
            By.XPATH,
            "//span[@name='reference'] | "
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

        # Navigate: home toggle → Hospital app → Appointments (top bar) → New
        self._navigate_to_hospital_section("Appointments")
        # Confirm we landed on the appointment model before proceeding
        self.wait.until(EC.url_contains("appointment"))
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_list_view")))

        self.click_new()

        # Patient field (Many2one) – type and select from dropdown
        patient_input = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@name='patient_id']//input")
            )
        )
        patient_input.send_keys("a")  # start typing to trigger search

        # Pick the first suggestion from the many2one dropdown
        first_option = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//ul[contains(@class,'ui-autocomplete')]//li[1] | "
                 "//div[contains(@class,'o_dropdown_menu')]//li[1]")
            )
        )
        first_option.click()
        time.sleep(0.5)  # wait for onchange to settle before interacting with doctor field

        # Doctor field – ActionChains ensures move+click+type fires atomically,
        # which reliably triggers the Many2one autocomplete dropdown.
        doctor_input = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@name='doctor_id']//input")
            )
        )
        ActionChains(self.driver).move_to_element(doctor_input).click().send_keys("a").perform()

        first_doctor = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "(//ul[contains(@class,'ui-autocomplete')"
                 " and not(contains(@style,'display: none'))]"
                 "//li[contains(@class,'ui-menu-item')])[1]")
            )
        )
        first_doctor.click()

        self.click_save()

        # Store created appointment ID so tearDownClass can clean it up.
        self.__class__._created_appointment_id = self._id_from_url(self.driver.current_url)

        self.assertFalse(
            self.has_error_message(),
            "An error message appeared after saving the appointment.",
        )
        # The appointment reference should now be a sequence like APT/2024/0001
        appt_name = self.find_or_none(
            By.XPATH,
            "//span[@name='name'] | //input[@name='name']"
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

        # Navigate: home toggle → Hospital app → Patients (top bar) → New
        self._navigate_to_hospital_section("Patients")
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_list_view")))

        self.click_new()

        # Intentionally leave the 'name' field blank and attempt to save
        self.fill_field("age", "25")

        self.click_save()

        # Odoo should show a validation tooltip or dialog about the required field.
        # Wait briefly for the error indicator to appear.
        try:
            self.wait.until(
                lambda d: self.has_error_message()
                or d.find_elements(By.XPATH,
                    "//input[@name='name' and contains(@class,'o_field_invalid')] | "
                    "//div[@name='name' and contains(@class,'o_field_invalid')]")
            )
        except TimeoutException:
            pass
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
