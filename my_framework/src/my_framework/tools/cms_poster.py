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
from selenium.webdriver.support.ui import Select
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
            service = None

        log("   - Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 30)  # Increased timeout
        log("   - ✅ WebDriver initialized successfully.")

        # --- LOGIN ---
        log(f"Navigating to login URL: {login_url}")
        driver.get(login_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        wait.until(EC.presence_of_element_located((By.ID, "main-content")))
        log("✅ Login successful.")

        # --- NAVIGATE TO ADD ARTICLE ---
        log("Navigating to add article page...")
        driver.get(add_article_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-title")))
        log("📝 Article form loaded. Starting to fill fields...")

        # --- FILL FORM FIELDS ---
        # Date
        log("Setting publication date...")
        date_field = driver.find_element(By.ID, "edit-field-sending-date-und-0-value-datepicker-popup-0")
        driver.execute_script(f"arguments[0].value = '{target_date_str}';", date_field)

        # Title and basic fields
        log("Filling title and basic metadata...")
        driver.find_element(By.ID, "edit-title").send_keys(remove_non_bmp_chars(title))
        driver.find_element(By.ID, "edit-field-weekly-title-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('weekly_title_value', '')))
        driver.find_element(By.ID, "edit-field-website-callout-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('website_callout_value', '')))
        driver.find_element(By.ID, "edit-field-social-media-callout-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('social_media_callout_value', '')))

        # --- BODY CONTENT (CKEditor) ---
        log("Filling body content in CKEditor...")
        try:
            # Wait for CKEditor to be fully loaded
            time.sleep(2)
            
            # Try to find and switch to the CKEditor iframe
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.cke_wysiwyg_frame")))
            driver.switch_to.frame(iframe)
            
            # Get the body element inside the iframe
            body_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Use JavaScript to set the HTML content
            driver.execute_script("arguments[0].innerHTML = arguments[1];", body_element, body_html)
            log("✅ Body content filled successfully")
            
            # Switch back to default content
            driver.switch_to.default_content()
            
        except Exception as e:
            log(f"⚠️ Error filling CKEditor: {e}")
            driver.switch_to.default_content()

        # --- CHECKBOXES (Publications, Countries, Industries) ---
        log("Ticking publication checkboxes...")
        tick_checkboxes_by_id(driver, article_content.get('publication_id_selections', []), log)
        
        log("Ticking country checkboxes...")
        tick_checkboxes_by_id(driver, article_content.get('country_id_selections', []), log)
        
        log("Ticking industry checkboxes...")
        tick_checkboxes_by_id(driver, article_content.get('industry_id_selections', []), log)

        # --- EXPAND ALL FIELDSETS (to reveal hidden fields) ---
        log("Expanding all collapsed sections...")
        try:
            fieldsets = driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed")
            for fieldset in fieldsets:
                try:
                    legend = fieldset.find_element(By.TAG_NAME, "legend")
                    driver.execute_script("arguments[0].click();", legend)
                    time.sleep(0.3)
                except:
                    pass
            log(f"✅ Expanded {len(fieldsets)} fieldsets")
        except Exception as e:
            log(f"⚠️ Could not expand fieldsets: {e}")

        # --- SEO FIELDS (with safe filling) ---
        log("Filling SEO metadata...")
        
        def safe_fill_field(field_id, value, field_name):
            """Safely fills a field if it exists"""
            try:
                element = driver.find_element(By.ID, field_id)
                element.clear()
                element.send_keys(remove_non_bmp_chars(value))
                log(f"   ✅ Filled {field_name}")
            except Exception as e:
                log(f"   ⚠️ Could not fill {field_name} (ID: {field_id}): {e}")
        
        safe_fill_field("edit-field-seo-title-und-0-value", article_content.get("seo_title_value", ""), "SEO Title")
        safe_fill_field("edit-field-seo-description-und-0-value", article_content.get("seo_description", ""), "SEO Description")
        safe_fill_field("edit-field-seo-keywords-und-0-value", article_content.get("seo_keywords", ""), "SEO Keywords")
        safe_fill_field("edit-field-hashtags-und-0-value", " ".join(article_content.get("hashtags", [])), "Hashtags")
        safe_fill_field("edit-field-abstract-und-0-value", article_content.get("abstract_value", ""), "Abstract")
        safe_fill_field("edit-field-google-news-keywords-und-0-value", article_content.get("google_news_keywords_value", ""), "Google News Keywords")

        # --- DROPDOWNS (if any) ---
        log("Setting dropdown values...")
        select_dropdown_option(driver, "edit-field-daily-subject-und", article_content.get("daily_subject_value"), log, "Daily Subject")
        select_dropdown_option(driver, "edit-field-key-point-und", article_content.get("key_point_value"), log, "Key Point")
        select_dropdown_option(driver, "edit-field-machine-written-und", article_content.get("machine_written_value"), log, "Machine Written")
        select_dropdown_option(driver, "edit-field-ballot-box-und", article_content.get("ballot_box_value"), log, "Ballot Box")

        # Byline
        log("Setting byline...")
        driver.find_element(By.ID, "edit-field-byline-und-0-value").send_keys(remove_non_bmp_chars(article_content.get("byline_value", "")))

        # --- SCROLL TO SAVE BUTTON ---
        log("Scrolling to save button...")
        save_button = wait.until(EC.presence_of_element_located((By.ID, save_button_id)))
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        time.sleep(1)

        # --- SAVE THE ARTICLE ---
        log("🚀 Clicking the 'Save' button...")
        driver.execute_script("arguments[0].click();", save_button)
        
        # Wait for success message or URL change
        try:
            wait.until(EC.url_changes(add_article_url))
            log("✅ Article submitted successfully!")
            final_url = driver.current_url
            log(f"Article URL: {final_url}")
            return json.dumps({"success": True, "url": final_url, "message": "Article posted successfully."})
        except:
            log("⚠️ Could not confirm submission. Check manually.")
            return json.dumps({"success": False, "message": "Form filled but submission could not be confirmed."})

    except Exception as e:
        log(f"🔥 An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": f"Failed to post to CMS. Error: {e}"})
    finally:
        if driver:
            if not is_render_env:
                log("   - Local environment: Waiting 30 seconds before closing browser...")
                time.sleep(30)
            log("Closing the browser.")
            driver.quit()