# -*- coding: utf-8 -*-
"""
Shared base class for all Odoo Selenium tests.

Provides:
- Chrome WebDriver setup / teardown
- Helper to log in to Odoo
- Helper to log out
"""

import time
import unittest

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    _WDM_AVAILABLE = True
except ImportError:
    _WDM_AVAILABLE = False

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8069"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
DEFAULT_WAIT = 10  # seconds
# ─────────────────────────────────────────────────────────────────────────────


class OdooBaseTest(unittest.TestCase):
    """Base test class shared by all Odoo Selenium test suites."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        if _WDM_AVAILABLE:
            cls.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
            )
        else:
            cls.driver = webdriver.Chrome(options=options)

        cls.driver.implicitly_wait(DEFAULT_WAIT)
        cls.wait = WebDriverWait(cls.driver, DEFAULT_WAIT)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def login(self, username: str = ADMIN_USER, password: str = ADMIN_PASS) -> bool:
        """Navigate to the Odoo login page and submit credentials.

        Returns True if login succeeded (redirected away from /web/login),
        False if an error message is visible on the login page.
        """
        self.driver.get(f"{BASE_URL}/web/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "login")))

        self.driver.find_element(By.ID, "login").clear()
        self.driver.find_element(By.ID, "login").send_keys(username)

        self.driver.find_element(By.ID, "password").clear()
        self.driver.find_element(By.ID, "password").send_keys(password)

        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

        try:
            # If we land on a page other than /web/login the login succeeded
            self.wait.until(EC.url_contains("/web#"))
            return True
        except TimeoutException:
            return False

    def logout(self):
        """Log out via the user menu."""
        self.driver.get(f"{BASE_URL}/web/session/logout")
        time.sleep(1)

    def find_or_none(self, by, value):
        """Return an element or None (does not raise)."""
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None

    def click_home_menu_toggle(self):
        """Click the home/apps toggle button in the top-left corner of the navbar."""
        toggle = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//*[contains(@class,'o_home_menu_toggle')] | "
                 "//nav[contains(@class,'o_main_navbar')]"
                 "//*[contains(@class,'o_menu_toggle')] | "
                 "//nav[contains(@class,'o_main_navbar')]//a[@href='/odoo' or @href='/web']")
            )
        )
        toggle.click()
        time.sleep(0.5)

    def navigate_to_menu(self, *menu_labels: str):
        """Click a sequence of menu items by their visible text labels."""
        for label in menu_labels:
            el = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//a[normalize-space(.)='{label}'] | "
                               f"//span[normalize-space(.)='{label}']")
                )
            )
            el.click()
            time.sleep(0.5)

    def click_new(self):
        """Click the 'New' button to open a blank form."""
        new_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space(.)='New']")
            )
        )
        new_btn.click()
        time.sleep(0.5)

    def click_save(self):
        """Click the 'Save manually' / save button in the toolbar."""
        save_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//button[contains(@class,'o_form_button_save')] | "
                 "//button[normalize-space(.)='Save']")
            )
        )
        save_btn.click()
        time.sleep(0.5)

    def click_discard(self):
        """Click the 'Discard' button to cancel unsaved changes."""
        discard_btn = self.find_or_none(
            By.XPATH,
            "//button[normalize-space(.)='Discard']"
        )
        if discard_btn:
            discard_btn.click()
            time.sleep(0.5)

    def fill_field(self, field_name: str, value: str):
        """Fill a standard Odoo form input field by its name attribute."""
        field = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//input[@id='{field_name}'] | "
                           f"//input[@name='{field_name}'] | "
                           f"//textarea[@name='{field_name}']")
            )
        )
        field.clear()
        field.send_keys(value)

    def has_error_message(self) -> bool:
        """Return True if any Odoo validation/error dialog or toast is visible."""
        selectors = [
            "//div[contains(@class,'o_error_dialog')]",
            "//div[contains(@class,'o_notification') and contains(@class,'bg-danger')]",
            "//div[contains(@class,'alert-danger')]",
            "//div[contains(@class,'o_dialog') and .//div[contains(@class,'modal-title') "
            "and normalize-space(.)='Validation Error']]",
        ]
        for sel in selectors:
            el = self.find_or_none(By.XPATH, sel)
            if el and el.is_displayed():
                return True
        return False
