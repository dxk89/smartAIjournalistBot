# File: src/my_framework/tools/cms_poster.py

import json
import os
import time
from datetime import datetime, timedelta
import pytz
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from my_framework.agents.tools import tool
from my_framework.agents.utils import (
    remove_non_bmp_chars,
    select_dropdown_option,
    tick_checkboxes_by_id,
    PUBLICATION_MAP,
    COUNTRY_MAP,
    INDUSTRY_MAP,
)

def log(message):
    print(f"   - {message}", flush=True)

def strip_html(text):
    """Removes HTML tags from a string."""
    return re.sub('<[^<]+?>', '', text)

@tool
def post_article_to_cms(article_json_string: str, username: str, password: str) -> str:
    """
    Logs into the CMS and submits an article using browser automation, filling all fields.
    This tool works both locally and on the Render deployment environment.
    """
    log("🤖 TOOL: Starting CMS Posting...")

    login_url = "https://cms.intellinews.com/user/login"
    add_article_url = "https://cms.intellinews.com/node/add/article"
    save_button_id = "edit-submit"

    try:
        article_content = json.loads(article_json_string)
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"error": f"Invalid JSON provided to CMS poster: {e}"})

    # --- Pre-computation of fields based on user's logic ---
    gmt = pytz.timezone('GMT')
    now_gmt = datetime.now(gmt)
    if now_gmt.hour >= 7:
        target_date = now_gmt + timedelta(days=1)
    else:
        target_date = now_gmt
    target_date_str = target_date.strftime('%m/%d/%Y')

    title = article_content.get("title", "")
    body_html = article_content.get("body", "")
    body_text = strip_html(body_html)
    first_sentence = body_text.split('.')[0] + '.' if '.' in body_text else body_text

    hashtags = article_content.get("hashtags", [])
    social_media_callout = f"{first_sentence} {' '.join(hashtags)}"

    article_content["weekly_title_value"] = title
    article_content["website_callout_value"] = first_sentence
    article_content["social_media_callout_value"] = social_media_callout
    article_content["publication_id_selections"] = [PUBLICATION_MAP[name] for name in article_content.get("publications", []) if name in PUBLICATION_MAP]
    article_content["country_id_selections"] = [COUNTRY_MAP[name] for name in article_content.get("countries", []) if name in COUNTRY_MAP]
    article_content["industry_id_selections"] = [INDUSTRY_MAP[name] for name in article_content.get("industries", []) if name in INDUSTRY_MAP]
    article_content["byline_value"] = username


    driver = None
    is_render_env = 'RENDER' in os.environ
    try:
        chrome_options = webdriver.ChromeOptions()
        service = None

        if is_render_env:
            log("   - Running in Render environment (headless mode).")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            binary_path = os.environ.get("GOOGLE_CHROME_BIN")
            driver_path = os.environ.get("CHROMEDRIVER_PATH")

            if not binary_path or not os.path.isfile(binary_path):
                return json.dumps({"error": f"Chrome binary not found on Render. GOOGLE_CHROME_BIN='{binary_path}'"})
            if not driver_path or not os.path.isfile(driver_path):
                 return json.dumps({"error": f"ChromeDriver not found on Render. CHROMEDRIVER_PATH='{driver_path}'"})

            chrome_options.binary_location = binary_path
            service = Service(executable_path=driver_path)
        else:
            log("   - Running in local environment (visible mode).")
            # For local development, Selenium Manager will handle the driver.
            service = None

        log("   - Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # Use an explicit wait to make the script more reliable
        wait = WebDriverWait(driver, 20)
        log("   - ✅ WebDriver initialized successfully.")

        log(f"Navigating to login URL: {login_url}")
        driver.get(login_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()

        # Wait for a known element on the next page to ensure login was successful
        wait.until(EC.presence_of_element_located((By.ID, "main-content")))
        log("Login successful.")

        driver.get(add_article_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-title")))
        log("📝 Filling article form...")

        # --- Date Logic ---
        driver.execute_script(f"document.getElementById('edit-field-sending-date-und-0-value-datepicker-popup-0').value = '{target_date_str}';")

        # Primary Content & Metadata
        driver.find_element(By.ID, "edit-title").send_keys(remove_non_bmp_chars(article_content.get('title', '')))
        driver.find_element(By.ID, "edit-field-weekly-title-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('weekly_title_value', '')))
        driver.find_element(By.ID, "edit-field-website-callout-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('website_callout_value', '')))
        driver.find_element(By.ID, "edit-field-social-media-callout-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('social_media_callout_value', '')))


        # --- FIX: Switch to the CKEditor iframe to input the body content ---
        log("Switching to CKEditor iframe...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe.cke_wysiwyg_frame")))
        body_element = driver.find_element(By.TAG_NAME, "body")
        body_element.send_keys(body_html)  # Send the original HTML to the editor
        driver.switch_to.default_content() # IMPORTANT: Switch back to the main document
        log("Switched back to default content.")

        # Checkbox selections
        tick_checkboxes_by_id(driver, article_content.get('country_id_selections', []), log)
        tick_checkboxes_by_id(driver, article_content.get('publication_id_selections', []), log)
        tick_checkboxes_by_id(driver, article_content.get('industry_id_selections', []), log)


        # Continue filling the rest of the fields
        driver.find_element(By.ID, "edit-field-seo-title-und-0-value").send_keys(remove_non_bmp_chars(article_content.get("seo_title_value", "")))
        driver.find_element(By.ID, "edit-field-seo-description-und-0-value").send_keys(remove_non_bmp_chars(article_content.get("seo_description", "")))
        driver.find_element(By.ID, "edit-field-seo-keywords-und-0-value").send_keys(remove_non_bmp_chars(article_content.get("seo_keywords", "")))
        driver.find_element(By.ID, "edit-field-hashtags-und-0-value").send_keys(remove_non_bmp_chars(" ".join(article_content.get("hashtags", []))))
        driver.find_element(By.ID, "edit-field-abstract-und-0-value").send_keys(remove_non_bmp_chars(article_content.get("abstract_value", "")))
        driver.find_element(By.ID, "edit-field-google-news-keywords-und-0-value").send_keys(remove_non_bmp_chars(article_content.get("google_news_keywords_value", "")))


        if save_button_id:
            log("🚀 Clicking the final 'Save' button...")
            # Use JavaScript to click, as it can be more reliable for complex pages
            save_button = wait.until(EC.element_to_be_clickable((By.ID, save_button_id)))
            driver.execute_script("arguments[0].click();", save_button)
            time.sleep(10) # Wait for submission to process
            log("✅ TOOL: Finished. Article submitted successfully!")
            return "Article posted successfully."
        else:
            log("⚠️ Save button ID not configured. Form filled but not saved.")
            return "Form filled but not saved as no save button ID was provided."

    except Exception as e:
        log(f"🔥 An unexpected error occurred in the CMS tool: {e}")
        return json.dumps({"error": f"Failed to post to CMS. Error: {e}"})
    finally:
        if driver:
            if not is_render_env:
                log("   - Local environment detected. Waiting 30 seconds before closing browser...")
                time.sleep(30)
            log("Closing the browser window.")
            driver.quit()