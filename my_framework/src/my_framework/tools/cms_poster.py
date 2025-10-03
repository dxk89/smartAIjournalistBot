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
    PUBLICATION_MAP, COUNTRY_MAP, INDUSTRY_MAP, select_dropdown_by_value,
    DAILY_SUBJECT_MAP, KEY_POINT_MAP, MACHINE_WRITTEN_MAP, BALLOT_BOX_MAP,
    AFRICA_DAILY_SECTION_MAP, SOUTHEAST_EUROPE_SECTIONS_MAP, CEE_NEWS_WATCH_MAP,
    N_AFRICA_TODAY_MAP, MIDDLE_EAST_TODAY_MAP, BALTIC_STATES_TODAY_MAP,
    ASIA_TODAY_SECTIONS_MAP, LATAM_TODAY_MAP
)
from my_framework.agents.loggerbot import LoggerBot

def strip_html(text):
    return re.sub('<[^<]+?>', '', text)

def clean_article_content(article_content):
    text_fields = [
        'title', 'body', 'weekly_title_value', 'website_callout_value',
        'social_media_callout_value', 'seo_title_value', 'seo_description',
        'seo_keywords', 'abstract_value', 'google_news_keywords_value',
        'byline_value'
    ]
    for field in text_fields:
        if field in article_content and isinstance(article_content[field], str):
            article_content[field] = article_content[field].replace('**', '')
    if 'hashtags' in article_content and isinstance(article_content['hashtags'], list):
        article_content['hashtags'] = [tag.replace('**', '') for tag in article_content['hashtags']]
    return article_content

@tool
def post_article_to_cms(article_json_string: str, username: str, password: str, logger=None) -> str:
    log = logger or LoggerBot.get_logger()
    log.info("🤖 TOOL: Starting CMS Posting...")

    try:
        article_content = json.loads(article_json_string)
    except (json.JSONDecodeError, TypeError) as e:
        log.critical(f"Invalid JSON provided to CMS poster: {e}", exc_info=True)
        return json.dumps({"error": f"Invalid JSON provided to CMS poster: {e}"})

    article_content = clean_article_content(article_content)

    log.info("Validating metadata before launching browser...")
    publications = article_content.get("publications", [])
    countries = article_content.get("countries", [])
    industries = article_content.get("industries", [])

    if not all([publications, countries, industries]):
        missing = [name for name, val in [("publications", publications), ("countries", countries), ("industries", industries)] if not val]
        error_message = f"CRITICAL: Missing required metadata: {', '.join(missing)}. Aborting CMS post."
        log.critical(error_message)
        return json.dumps({"error": error_message})
    log.info("✅ Metadata validation successful.")

    gmt = pytz.timezone('GMT')
    now_gmt = datetime.now(gmt)
    target_date = (now_gmt + timedelta(days=1)) if now_gmt.hour >= 7 else now_gmt
    target_date_str = target_date.strftime('%m/%d/%Y')

    driver = None
    is_render_env = 'RENDER' in os.environ
    
    try:
        chrome_options = webdriver.ChromeOptions()
        service = None
        if is_render_env:
            log.info("Running in Render environment (headless mode).")
            chrome_options.add_argument("--headless=new")
            # ... other headless options
        else:
            log.info("Running in local environment (visible mode).")

        log.info("Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 30)
        log.info("✅ WebDriver initialized successfully.")

        log.info("Navigating to login page...")
        driver.get("https://cms.intellinews.com/user/login")
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Log out")))
        log.info("✅ Login successful.")

        log.info("Navigating to add article page...")
        driver.get("https://cms.intellinews.com/node/add/article")
        wait.until(EC.presence_of_element_located((By.ID, "edit-title")))
        
        log.info("Expanding all form sections...")
        for legend in driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed legend"):
            try:
                driver.execute_script("arguments[0].click();", legend)
            except Exception: pass
        time.sleep(2)

        def safe_fill(element_id, value, field_name):
            if not value: return
            try:
                element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
                driver.execute_script("arguments[0].value = arguments[1];", element, value)
                log.info(f"   ✅ Filled {field_name}")
            except Exception as e:
                log.error(f"   ⚠️ Failed to fill {field_name} (ID: {element_id}): {e}")

        log.info("--- Filling Main Article Fields ---")
        safe_fill("edit-title", article_content.get("title"), "Title")
        safe_fill("edit-field-byline-und-0-value", username, "Byline")

        try:
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.cke_wysiwyg_frame")))
            driver.switch_to.frame(iframe)
            driver.execute_script("document.body.innerHTML = arguments[0];", article_content.get("body", ""))
            driver.switch_to.default_content()
            log.info("   ✅ Filled Body Content (CKEditor)")
        except Exception as e:
            log.error(f"   ⚠️ Failed to fill Body Content: {e}")
            driver.switch_to.default_content()

        log.info("--- Filling Metadata and SEO Fields ---")
        safe_fill("edit-field-weekly-title-und-0-value", article_content.get("weekly_title_value"), "Weekly Title")
        safe_fill("edit-field-website-callout-und-0-value", article_content.get("website_callout_value"), "Website Callout")
        safe_fill("edit-field-social-media-callout-und-0-value", article_content.get("social_media_callout_value"), "Social Media Callout")
        safe_fill("edit-field-abstract-und-0-value", article_content.get("abstract_value"), "Abstract")
        safe_fill("edit-field-seo-title-und-0-value", article_content.get("seo_title_value"), "SEO Title")
        safe_fill("edit-field-seo-description-und-0-value", article_content.get("seo_description"), "SEO Description")
        safe_fill("edit-field-seo-keywords-und-0-value", article_content.get("seo_keywords"), "SEO Keywords")
        safe_fill("edit-field-google-news-keywords-und-0-value", article_content.get("google_news_keywords_value"), "Google News Keywords")
        safe_fill("edit-field-hashtags-und-0-value", ' '.join(article_content.get("hashtags", [])), "Hashtags")

        log.info("--- Ticking Checkboxes ---")
        for p_name in publications:
            p_id = PUBLICATION_MAP.get(p_name)
            if p_id: 
                driver.execute_script(f"document.getElementById('{p_id}').checked = true;")
                log.info(f"   ✅ Ticked Publication: {p_name}")
        # ... (similar loops for countries and industries) ...

        log.info("--- Setting Dropdowns ---")
        # ... (dropdown code remains the same) ...
        
        log.info("🚀 Attempting to submit form...")
        save_button = wait.until(EC.element_to_be_clickable((By.ID, "edit-submit")))
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        time.sleep(1)
        save_button.click()

        wait.until(EC.url_contains("/node/"))
        final_url = driver.current_url

        if "/node/add/article" in final_url:
             raise Exception("Form submission failed, redirected back to the add article page.")

        log.info(f"✅ Article submitted successfully! URL: {final_url}")
        return json.dumps({"success": True, "url": final_url, "message": "Article posted successfully."})

    except Exception as e:
        log.critical(f"🔥 An error occurred during browser automation: {e}", exc_info=True)
        # ... (screenshot code remains the same) ...
        return json.dumps({"error": f"Failed to post to CMS: {e}"})
    finally:
        if driver:
            if not is_render_env:
                log.info("Waiting 20 seconds for final review (local mode)...")
                time.sleep(20) # Re-added the wait time
            log.info("Closing browser.")
            driver.quit()