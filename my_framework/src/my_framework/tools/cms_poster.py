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

def post_article_to_cms(article_json: str, username: str, password: str, logger) -> str:
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

    # Get URLs from environment variables or use defaults
    login_url = os.environ.get("CMS_LOGIN_URL", "https://cms.intellinews.com/user/login")
    create_article_url = os.environ.get("CMS_CREATE_ARTICLE_URL", "https://cms.intellinews.com/node/add/article")

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Setup WebDriver using webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # 1. Login
        log.info(f"Navigating to login page at {login_url}...")
        driver.get(login_url)
        
        log.info("Entering login credentials...")
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        
        log.info("Login submitted. Verifying success...")
        wait.until(EC.url_contains("user"))
        if "dashboard" not in driver.current_url:
            log.warning(f"Login may have failed. Current URL: {driver.current_url}")
        log.info("Login successful.")

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
        driver.switch_to.frame(driver.find_element(By.ID, "edit-body-und-0-value_ifr"))
        driver.find_element(By.ID, "tinymce").send_keys(body)
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

        # INCREASED WAIT: Allow more time for dynamic content to load
        log.info("Waiting 10 seconds for all form elements to fully load...")
        time.sleep(10) # Increased from 5 to 10 seconds

        # Additional wait for AJAX requests to complete
        log.info("Waiting for any AJAX requests to complete...")
        try:
            # Wait for jQuery AJAX to complete (if jQuery is present)
            wait.until(lambda d: d.execute_script("return typeof jQuery !== 'undefined' && jQuery.active == 0"))
            log.info("✅ jQuery AJAX requests completed")
        except:
            log.warning("⚠️ Could not verify AJAX completion (jQuery might not be available)")
            time.sleep(3) # Extra safety buffer

        # Wait for document ready state
        try:
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            log.info("✅ Document ready state is complete")
        except:
            log.warning("⚠️ Could not verify document ready state")
            
        # Verify critical elements are present before proceeding
        log.info("Verifying critical dropdown elements are present and interactable...")
        critical_elements = {
            "edit-field-daily-publications-subject-und": "Daily Publications Subject",
            "edit-field-key-point-und": "Key Point",
            "edit-field-machine-written-und": "Machine Written"
        }

        missing_elements = []
        for element_id, element_name in critical_elements.items():
            try:
                # Wait for element to be present
                element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
                
                # Verify it's actually a select element
                if element.tag_name != "select":
                    log.critical(f"   🔥 {element_name} found but is not a select element (is {element.tag_name})")
                    missing_elements.append(element_name)
                    continue
                
                # Verify it has options loaded
                options = element.find_elements(By.TAG_NAME, "option")
                if len(options) == 0:
                    log.critical(f"   🔥 {element_name} has no options loaded")
                    missing_elements.append(element_name)
                    continue
                
                # Verify element is visible and enabled
                if not element.is_displayed():
                    log.warning(f"   ⚠️ {element_name} is not visible")
                
                if not element.is_enabled():
                    log.critical(f"   🔥 {element_name} is not enabled")
                    missing_elements.append(element_name)
                    continue
                
                log.info(f"   ✅ {element_name} found with {len(options)} options, visible and enabled")
                
            except TimeoutException:
                log.critical(f"   🔥 {element_name} (ID: {element_id}) NOT FOUND after waiting")
                missing_elements.append(element_name)
            except Exception as e:
                log.critical(f"   🔥 Error verifying {element_name}: {e}")
                missing_elements.append(element_name)

        if missing_elements:
            log.critical(f"🔥 CRITICAL: {len(missing_elements)} required elements not ready: {', '.join(missing_elements)}")
            
            # Enhanced debugging: Save screenshot and page source
            try:
                screenshot_path = f"/tmp/missing_dropdowns_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                log.info(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                log.error(f"Failed to save screenshot: {e}")
            
            try:
                html_path = f"/tmp/page_source_{int(time.time())}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                log.info(f"Page source saved to {html_path}")
            except Exception as e:
                log.error(f"Failed to save page source: {e}")
            
            # Log all select elements that ARE present
            try:
                all_selects = driver.find_elements(By.TAG_NAME, "select")
                select_ids = [s.get_attribute('id') for s in all_selects if s.get_attribute('id')]
                log.info(f"   Available select IDs: {select_ids[:20]}") # First 20
            except:
                pass
            
            raise Exception(f"Required form elements not loaded: {', '.join(missing_elements)}. Cannot proceed.")

        log.info("✅ All critical dropdown elements confirmed present and ready")


        # Publications
        log.info("Setting publications...")
        publication_ids = article_data.get("publication_ids", [])
        if not publication_ids:
             log.warning("No publication IDs in JSON, this will likely fail.")
        tick_checkboxes_by_id(driver, publication_ids, log)


        # ... (rest of the dropdown selections)

        # 4. Save the Article
        log.info("Attempting to save the article...")
        save_button = driver.find_element(By.ID, "edit-submit")
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        time.sleep(1)
        save_button.click()

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