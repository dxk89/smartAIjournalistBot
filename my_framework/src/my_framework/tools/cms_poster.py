# File: src/my_framework/tools/cms_poster.py

import json
import os
import time
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, JavascriptException
from my_framework.agents.utils import (
    remove_non_bmp_chars,
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

def select_dropdown_option(driver, element_id, value_to_select, log, element_name):
    """
    Selects an option from a dropdown menu by its value using JavaScript.
    """
    if not value_to_select:
        return
    try:
        script = f"""
        var select = document.getElementById('{element_id}');
        if (select) {{
            select.value = '{value_to_select}';
            var event = new Event('change', {{ 'bubbles': true }});
            select.dispatchEvent(event);
            return true;
        }} else {{
            return false;
        }}
        """
        result = driver.execute_script(script)
        if result:
            log.info(f"   - ✅ Selected '{value_to_select}' for {element_name}.")
        else:
            log.warning(f"   - ⚠️ Dropdown '{element_name}' (ID: {element_id}) not found.")
    except Exception as e:
        log.error(f"   - 🔥 Could not select '{value_to_select}' for {element_name}: {e}")

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

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    if os.environ.get('RENDER') == 'true':
        log.info("Render environment detected. Running in headless mode.")
        chrome_options.add_argument("--headless")
    else:
        log.info("Local environment detected. Running with browser window.")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        log.info(f"Navigating to login page at {login_url}...")
        driver.get(login_url)

        log.info("Entering login credentials...")
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()

        log.info("Login submitted. Verifying success...")
        wait.until(EC.url_to_be("https://cms.intellinews.com/workflow/mycontent"))
        log.info("Login successful.")

        log.info(f"Navigating to 'Add Article' page at {create_article_url}...")
        driver.get(create_article_url)
        wait.until(EC.element_to_be_clickable((By.ID, "edit-submit")))
        log.info("'Add Article' page loaded and ready.")
        time.sleep(2)  # A crucial pause for all JavaScript to initialize

        log.info("--- Filling Article Form in Order ---")

        # --- Top of the Form ---
        driver.find_element(By.ID, "edit-title").send_keys(remove_non_bmp_chars(article_data.get("title_value", "")))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-field-weekly-title-und-0-value").send_keys(remove_non_bmp_chars(article_data.get('weekly_title_value', '')))
        time.sleep(0.3)
        
        # --- Machine Written & Date ---
        try:
            # First, try to find the element and click it normally
            machine_written_checkbox = driver.find_element(By.ID, "edit-field-machine-written-und-yes")
            machine_written_checkbox.click()
            log.info("   - ✅ Ticked 'Machine Written' checkbox using standard click.")
        except (NoSuchElementException, JavascriptException):
            try:
                # If that fails, fall back to the JavaScript click
                driver.execute_script("document.getElementById('edit-field-machine-written-und-Yes').click();")
                log.info("   - ✅ Ticked 'Machine Written' checkbox using JavaScript click.")
            except JavascriptException as e:
                log.error(f"   - 🔥 Failed to tick 'Machine Written' checkbox with both methods: {e}")

        time.sleep(0.3)
        
        gmt = pytz.timezone('GMT')
        now_gmt = datetime.now(gmt)
        target_date = now_gmt + timedelta(days=1) if now_gmt.hour >= 7 else now_gmt
        target_date_str = target_date.strftime('%m/%d/%Y')
        driver.execute_script(f"document.getElementById('edit-field-sending-date-und-0-value-datepicker-popup-0').value = '{target_date_str}';")
        log.info(f"   - ✅ Set sending date to {target_date_str}.")
        time.sleep(0.3)
        
        # --- Main Content ---
        driver.find_element(By.ID, "edit-field-bylines-und-0-field-byline-und").send_keys(remove_non_bmp_chars(article_data.get('byline_value', '')))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-field-website-callout-und-0-value").send_keys(remove_non_bmp_chars(article_data.get('website_callout_value', '')))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-field-social-media-callout-und-0-value").send_keys(remove_non_bmp_chars(article_data.get('social_media_callout_value', '')))
        time.sleep(0.3)

        body_content = remove_non_bmp_chars(article_data.get('body_value', ''))
        escaped_body = json.dumps(body_content)
        driver.execute_script(f"CKEDITOR.instances['edit-body-und-0-value'].setData({escaped_body});")
        log.info("   - ✅ Set body content.")
        time.sleep(0.5)

        # --- Taxonomy and Selections ---
        tick_checkboxes_by_id(driver, article_data.get('country_id_selections'), log)
        time.sleep(0.3)
        tick_checkboxes_by_id(driver, article_data.get('publication_id_selections'), log)
        time.sleep(0.3)
        tick_checkboxes_by_id(driver, article_data.get('industry_id_selections'), log)
        time.sleep(0.3)

        # --- Dropdown Selections ---
        select_dropdown_option(driver, 'edit-field-subject-und', article_data.get('daily_subject_value'), log, "Daily Publications Subject")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-ballot-box-und', article_data.get('ballot_box_value'), log, "Ballot Box")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-key-und', article_data.get('key_point_value'), log, "Key Point")
        time.sleep(0.3)
        
        # --- Section Dropdowns ---
        select_dropdown_option(driver, 'edit-field-africa-daily-section-und', article_data.get('africa_daily_section_value'), log, "Africa Daily Section")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-southeast-europe-today-sec-und', article_data.get('southeast_europe_today_sections_value'), log, "Southeast Europe Today Sections")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-cee-middle-east-africa-tod-und', article_data.get('cee_news_watch_country_sections_value'), log, "CEE News Watch Country Sections")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-middle-east-n-africa-today-und', article_data.get('n_africa_today_section_value'), log, "N.Africa Today Section")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-middle-east-today-section-und', article_data.get('middle_east_today_section_value'), log, "Middle East Today Section")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-baltic-states-today-sectio-und', article_data.get('baltic_states_today_sections_value'), log, "Baltic States Today Sections")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-asia-today-sections-und', article_data.get('asia_today_sections_value'), log, "Asia Today Sections")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-latam-today-und', article_data.get('latam_today_value'), log, "LatAm Today")
        time.sleep(0.3)
        
        # --- Final Metadata ---
        driver.find_element(By.ID, "edit-metatags-und-abstract-value").send_keys(remove_non_bmp_chars(article_data.get('abstract_value', '')))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-metatags-und-keywords-value").send_keys(remove_non_bmp_chars(article_data.get('seo_keywords_value', '')))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-metatags-und-news-keywords-value").send_keys(remove_non_bmp_chars(article_data.get('google_news_keywords_value', '')))
        time.sleep(0.3)

        log.info("Attempting to save the article...")
        save_button = driver.find_element(By.ID, "edit-submit")
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        save_button.click()

        log.info("Verifying submission...")
        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".messages.status")))
        final_url = driver.current_url
        log.info(f"Article posted successfully! URL: {final_url}")
        return f"Article posted successfully! URL: {final_url}"

    except TimeoutException:
        log.error("Failed to find success message. Posting may have failed.")
        try:
            error_message = driver.find_element(By.CSS_SELECTOR, ".messages.error")
            log.error(f"CMS Error Message: {error_message.text}")
            return f"Error: Posting failed. CMS Error: {error_message.text}"
        except NoSuchElementException:
            log.error("No specific error message found on page.")
            return "Error: Posting failed for an unknown reason."
    except Exception as e:
        log.critical(f"An unexpected error occurred: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"
    finally:
        if driver:
            log.info("--- CMS Posting Process Finished ---")
            driver.quit()