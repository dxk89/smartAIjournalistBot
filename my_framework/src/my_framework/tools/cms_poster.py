# File: src/my_framework/tools/cms_poster.py

import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from my_framework.agents.utils import (
    remove_non_bmp_chars,
    select_dropdown_by_value,
    tick_checkboxes_by_id,
    get_publication_ids_from_llm,
    DAILY_SUBJECT_MAP,
    KEY_POINT_MAP,
    MACHINE_WRITTEN_MAP,
    BALLOT_BOX_MAP,
    AFRICA_DAILY_SECTION_MAP,
    SOUTHEAST_EUROPE_SECTIONS_MAP,
    CEE_NEWS_WATCH_MAP,
    N_AFRICA_TODAY_MAP,
    MIDDLE_EAST_TODAY_MAP,
    BALTIC_STATES_TODAY_MAP,
    ASIA_TODAY_SECTIONS_MAP,
    LATAM_TODAY_MAP,
)

def post_article_to_cms(article_json: str, username: str, password: str, login_url: str, create_article_url: str, logger) -> str:
    """
    Logs into the CMS, creates a new article, fills in the fields based on the JSON data, and saves it.
    """
    log = logger
    log.info("--- Starting CMS Posting Process ---")

    try:
        article_data = json.loads(article_json)
        log.info("Successfully parsed article JSON.")
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON: {e}")
        return f"Error: Invalid JSON format. {e}"

    if not login_url or not create_article_url:
        error_msg = "Error: CMS Login URL and Create Article URL must be provided."
        log.critical(error_msg)
        return error_msg

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Conditionally run in headless mode
    if os.environ.get('RENDER') == 'true':
        log.info("Render environment detected. Running in headless mode.")
        chrome_options.add_argument("--headless")
    else:
        log.info("Local environment detected. Running with browser window.")

    # Setup WebDriver using webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 30)  # Increased wait time

    try:
        # 1. Login
        log.info(f"Navigating to login page at {login_url}...")
        driver.get(login_url)

        log.info("Entering login credentials...")
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()

        log.info("Login submitted. Verifying success...")
        try:
            wait.until(EC.url_contains("dashboard"))
            wait.until(EC.presence_of_element_located((By.ID, "page-title"))) # A common element on dashboards
            log.info("Login successful. Dashboard loaded.")
        except TimeoutException:
            log.critical("Login failed. Could not verify dashboard URL or presence of dashboard elements.")
            # Enhanced debugging: Save screenshot and page source
            try:
                screenshot_path = f"/tmp/login_failed_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                log.info(f"Screenshot saved to {screenshot_path}")
                html_path = f"/tmp/login_failed_source_{int(time.time())}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                log.info(f"Page source saved to {html_path}")
            except Exception as e:
                log.error(f"Failed to save debug info: {e}")
            raise Exception("Login Failed: Timed out waiting for dashboard.")


        # 2. Navigate to Create Article Page
        log.info(f"Navigating to 'Add Article' page at {create_article_url}...")
        driver.get(create_article_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-title")))
        log.info("'Add Article' page loaded.")

        # 3. Fill in the form
        log.info("--- Filling Article Form ---")

        # Title
        log.info("Setting title...")
        title = remove_non_bmp_chars(article_data.get("title", ""))
        driver.find_element(By.ID, "edit-title").send_keys(title)

        # Body
        log.info("Setting body content...")
        body = remove_non_bmp_chars(article_data.get("body", ""))
        wait.until(EC.presence_of_element_located((By.ID, "edit-body-und-0-value_ifr")))
        driver.switch_to.frame(driver.find_element(By.ID, "edit-body-und-0-value_ifr"))
        wait.until(EC.presence_of_element_located((By.ID, "tinymce"))).send_keys(body)
        driver.switch_to.default_content()

        log.info("Expanding all form sections...")
        collapsed_fieldsets = driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed legend")
        log.info(f"   Found {len(collapsed_fieldsets)} collapsed fieldsets")

        for i, legend in enumerate(collapsed_fieldsets, 1):
            try:
                driver.execute_script("arguments[0].click();", legend)
                log.info(f"   Expanded fieldset {i}/{len(collapsed_fieldsets)}")
                time.sleep(0.5) # Small delay between expansions
            except Exception as e:
                log.warning(f"   Failed to expand fieldset {i}: {e}")

        # Wait for critical elements to be present and interactable
        log.info("Verifying critical dropdown elements are present and interactable...")
        critical_elements = {
            "edit-field-daily-publications-subject-und": "Daily Publications Subject",
            "edit-field-key-point-und": "Key Point",
            "edit-field-machine-written-und": "Machine Written"
        }
        for element_id, element_name in critical_elements.items():
            try:
                element = wait.until(EC.element_to_be_clickable((By.ID, element_id)))
                log.info(f"   ✅ {element_name} is clickable.")
            except TimeoutException:
                 log.critical(f"   🔥 {element_name} (ID: {element_id}) NOT FOUND or not clickable after waiting")
                 raise Exception(f"Required form element not loaded: {element_name}")

        log.info("✅ All critical dropdown elements confirmed present and ready")


        # Publications
        log.info("Setting publications...")
        publication_ids = article_data.get("publication_ids", [])
        if not publication_ids:
             log.warning("No publication IDs in JSON, this will likely fail.")
        tick_checkboxes_by_id(driver, publication_ids, log)


        # ... (rest of the dropdown selections can be added here)

        # 4. Save the Article
        log.info("Attempting to save the article...")
        save_button = driver.find_element(By.ID, "edit-submit")
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        wait.until(EC.element_to_be_clickable((By.ID, "edit-submit"))).click()


        # 5. Verify Submission
        log.info("Verifying submission...")
        try:
            success_message = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".messages.status"))
            )
            final_url = driver.current_url
            log.info(f"Article posted successfully! URL: {final_url}")
            return f"Article posted successfully! URL: {final_url}"
        except TimeoutException:
            log.error("Failed to find success message. Posting may have failed.")

            # Debugging: Check for error messages
            try:
                error_message = driver.find_element(By.CSS_SELECTOR, ".messages.error")
                log.error(f"CMS Error Message: {error_message.text}")
                # Save screenshot on failure
                screenshot_path = f"cms_error_{time.strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_path)
                log.info(f"Screenshot saved to {screenshot_path}")
                return f"Error: Posting failed. CMS Error: {error_message.text}"
            except NoSuchElementException:
                log.error("No specific error message found on page.")
                screenshot_path = f"cms_error_{time.strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_path)
                log.info(f"Screenshot saved to {screenshot_path}")
                return "Error: Posting failed for an unknown reason."

    except Exception as e:
        log.critical(f"An unexpected error occurred: {e}", exc_info=True)
        # Save screenshot on any exception
        try:
            screenshot_path = f"cms_debug_screenshot.png"
            driver.save_screenshot(screenshot_path)
            log.info(f"Debug screenshot saved to {screenshot_path}")
        except Exception as screenshot_e:
            log.error(f"Could not save debug screenshot: {screenshot_e}")
        return f"An unexpected error occurred: {e}"

    finally:
        log.info("--- CMS Posting Process Finished ---")
        driver.quit()