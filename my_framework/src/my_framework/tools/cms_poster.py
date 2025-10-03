# File: src/my_framework/tools/cms_poster.py
# COMPLETE FIXED VERSION - All 3 critical fixes implemented

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
from selenium.common.exceptions import TimeoutException
from my_framework.agents.tools import tool
from my_framework.agents.utils import (
    PUBLICATION_MAP, COUNTRY_MAP, INDUSTRY_MAP, select_dropdown_by_value, tick_checkboxes_by_id,
    DAILY_SUBJECT_MAP, KEY_POINT_MAP, MACHINE_WRITTEN_MAP, BALLOT_BOX_MAP,
    AFRICA_DAILY_SECTION_MAP, SOUTHEAST_EUROPE_SECTIONS_MAP, CEE_NEWS_WATCH_MAP,
    N_AFRICA_TODAY_MAP, MIDDLE_EAST_TODAY_MAP, BALTIC_STATES_TODAY_MAP,
    ASIA_TODAY_SECTIONS_MAP, LATAM_TODAY_MAP
)
from my_framework.agents.loggerbot import LoggerBot

def strip_html(text):
    return re.sub('<[^<]+?>', '', text)

def clean_article_content(article_content):
    """Remove markdown formatting from all text fields"""
    text_fields = [
        'title', 'body', 'weekly_title_value', 'website_callout_value',
        'social_media_callout_value', 'seo_title_value', 'seo_keywords',
        'abstract_value', 'google_news_keywords_value', 'byline_value'
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

    # Calculate publication date
    gmt = pytz.timezone('GMT')
    now_gmt = datetime.now(gmt)
    
    if now_gmt.hour >= 7:
        target_date = now_gmt + timedelta(days=1)
        log.info(f"   Current time is {now_gmt.strftime('%H:%M')} GMT (>= 7am) - using next day")
    else:
        target_date = now_gmt
        log.info(f"   Current time is {now_gmt.strftime('%H:%M')} GMT (< 7am) - using today")
    
    target_date_str = target_date.strftime('%m/%d/%Y')
    log.info(f"   Publication date set to: {target_date_str}")

    driver = None
    is_render_env = 'RENDER' in os.environ
    
    try:
        chrome_options = webdriver.ChromeOptions()
        service = None
        if is_render_env:
            log.info("Running in Render environment (headless mode).")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_binary = os.environ.get("GOOGLE_CHROME_BIN")
            chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
            if chrome_binary: chrome_options.binary_location = chrome_binary
            if chromedriver_path: service = Service(executable_path=chromedriver_path)
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
        
        # ============================================================================
        # FIX #1: INCREASED WAIT TIME + VERIFICATION
        # ============================================================================
        log.info("Expanding all form sections...")
        for legend in driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed legend"):
            try:
                driver.execute_script("arguments[0].click();", legend)
            except Exception: pass

        # CRITICAL FIX: Wait longer for all fieldsets to fully load
        log.info("Waiting for all form elements to load...")
        time.sleep(5)  # Increased from 2 to 5 seconds

        # Verify critical elements are present before proceeding
        try:
            wait.until(EC.presence_of_element_located((By.ID, "edit-field-daily-publications-subject-und")))
            wait.until(EC.presence_of_element_located((By.ID, "edit-field-key-point-und")))
            wait.until(EC.presence_of_element_located((By.ID, "edit-field-machine-written-und")))
            log.info("✅ Critical dropdown elements confirmed present")
        except TimeoutException as e:
            log.critical(f"🔥 CRITICAL: Required dropdown elements not found after waiting: {e}")
            # Take a screenshot for debugging
            try:
                driver.save_screenshot(f"/tmp/missing_dropdowns_{int(time.time())}.png")
            except: pass
            raise Exception("Required form elements not loaded. Cannot proceed.")

        # ============================================================================
        # DIAGNOSTIC CODE
        # ============================================================================
        log.info("--- DIAGNOSTIC: Checking Page State ---")
        try:
            current_url = driver.current_url
            log.info(f"   Current URL: {current_url}")
            
            all_selects = driver.find_elements(By.TAG_NAME, "select")
            log.info(f"   Total <select> elements found: {len(all_selects)}")
            
            select_ids = [s.get_attribute('id') for s in all_selects if s.get_attribute('id')]
            log.info(f"   Select element IDs found: {select_ids[:10]}")
            
            page_source = driver.page_source
            if "edit-field-daily-publications-subject-und" in page_source:
                log.info("   ✅ Daily Publications Subject element exists in page source")
            else:
                log.critical("   🔥 Daily Publications Subject element NOT in page source!")
            
            if "edit-field-key-point-und" in page_source:
                log.info("   ✅ Key Point element exists in page source")
            else:
                log.critical("   🔥 Key Point element NOT in page source!")
                
        except Exception as e:
            log.error(f"   Diagnostic check failed: {e}")

        # ============================================================================
        # FILL STANDARD FIELDS
        # ============================================================================
        def safe_fill(element_id, value, field_name):
            if not value: 
                log.info(f"   ⊘ Skipping {field_name} (empty)")
                return
            try:
                element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
                driver.execute_script("arguments[0].value = arguments[1];", element, value)
                log.info(f"   ✅ Filled {field_name}")
            except Exception as e:
                log.error(f"   ⚠️ Failed to fill {field_name} (ID: {element_id}): {e}")

        log.info("--- Filling Main Article Fields ---")
        safe_fill("edit-title", article_content.get("title"), "Title")
        
        byline = article_content.get("byline_value", "").strip()
        if byline:
            safe_fill("edit-field-byline-und-0-value", byline, "Byline")
        else:
            log.info("   ⊘ Byline left blank (as per specification)")

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
        
        log.info("   ⊘ Skipping SEO Description (auto-filled by CMS)")
        
        safe_fill("edit-field-seo-keywords-und-0-value", article_content.get("seo_keywords"), "SEO Keywords")
        safe_fill("edit-field-google-news-keywords-und-0-value", article_content.get("google_news_keywords_value"), "Google News Keywords")
        safe_fill("edit-field-hashtags-und-0-value", ' '.join(article_content.get("hashtags", [])), "Hashtags")

        log.info("--- Ticking Publication Checkboxes ---")
        publication_ids = [PUBLICATION_MAP[p] for p in publications if p in PUBLICATION_MAP]
        tick_checkboxes_by_id(driver, publication_ids, log.info)

        log.info("--- Ticking Country Checkboxes (REQUIRED) ---")
        country_ids = [COUNTRY_MAP[c] for c in countries if c in COUNTRY_MAP]
        if not country_ids:
            log.critical("🔥 CRITICAL: No valid country checkboxes to tick! This will cause form submission to fail.")
        tick_checkboxes_by_id(driver, country_ids, log.info)

        log.info("--- Ticking Industry Checkboxes ---")
        industry_ids = [INDUSTRY_MAP[i] for i in industries if i in INDUSTRY_MAP]
        tick_checkboxes_by_id(driver, industry_ids, log.info)

        # ============================================================================
        # FIX #3: RETRY LOGIC FOR REQUIRED DROPDOWNS WITH INCREASED TIMEOUT
        # ============================================================================
        log.info("--- Setting REQUIRED Dropdown Fields ---")

        # CRITICAL: Daily Subject (REQUIRED)
        daily_subject = article_content.get("daily_subject_value", "Companies and Industries")
        for attempt in range(3):  # Retry up to 3 times
            success = select_dropdown_by_value(
                driver, 
                "edit-field-daily-publications-subject-und",
                daily_subject,
                DAILY_SUBJECT_MAP,
                log.info,
                "Daily Publications Subject",
                required=True,
                wait_timeout=20  # Increased timeout
            )
            if success:
                break
            if attempt < 2:
                log.info(f"   - Retry attempt {attempt + 2} for Daily Publications Subject...")
                time.sleep(2)
            else:
                log.critical("🔥 CRITICAL: Failed to set Daily Publications Subject after 3 attempts!")

        # CRITICAL: Key Point (REQUIRED)
        key_point = article_content.get("key_point_value", "No")
        for attempt in range(3):  # Retry up to 3 times
            success = select_dropdown_by_value(
                driver,
                "edit-field-key-point-und",
                key_point,
                KEY_POINT_MAP,
                log.info,
                "Key Point",
                required=True,
                wait_timeout=20  # Increased timeout
            )
            if success:
                break
            if attempt < 2:
                log.info(f"   - Retry attempt {attempt + 2} for Key Point...")
                time.sleep(2)
            else:
                log.critical("🔥 CRITICAL: Failed to set Key Point after 3 attempts!")

        # CRITICAL: Machine Written (REQUIRED)
        machine_written = article_content.get("machine_written_value", "Yes")
        for attempt in range(3):  # Retry up to 3 times
            success = select_dropdown_by_value(
                driver,
                "edit-field-machine-written-und",
                machine_written,
                MACHINE_WRITTEN_MAP,
                log.info,
                "Machine Written",
                required=True,
                wait_timeout=20  # Increased timeout
            )
            if success:
                break
            if attempt < 2:
                log.info(f"   - Retry attempt {attempt + 2} for Machine Written...")
                time.sleep(2)
            else:
                log.critical("🔥 CRITICAL: Failed to set Machine Written after 3 attempts!")
        
        log.info("--- Setting Optional Dropdown Fields ---")
        
        # Ballot Box (elections)
        ballot_box = article_content.get("ballot_box_value", "No")
        select_dropdown_by_value(
            driver,
            "edit-field-ballot-box-und",
            ballot_box,
            BALLOT_BOX_MAP,
            log.info,
            "Ballot Box",
            required=False,
            wait_timeout=20
        )
        
        # Regional Sections
        africa_section = article_content.get("africa_daily_section_value", "- None -")
        if africa_section and africa_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-africa-daily-section-und",
                africa_section,
                AFRICA_DAILY_SECTION_MAP,
                log.info,
                "Africa Daily Section",
                required=False,
                wait_timeout=20
            )
        
        se_europe_section = article_content.get("southeast_europe_today_sections_value", "- None -")
        if se_europe_section and se_europe_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-southeast-europe-today-sec-und",
                se_europe_section,
                SOUTHEAST_EUROPE_SECTIONS_MAP,
                log.info,
                "Southeast Europe Today Section",
                required=False,
                wait_timeout=20
            )
        
        cee_section = article_content.get("cee_news_watch_country_sections_value", "- None -")
        if cee_section and cee_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-cee-news-watch-country-sec-und",
                cee_section,
                CEE_NEWS_WATCH_MAP,
                log.info,
                "CEE News Watch Country Section",
                required=False,
                wait_timeout=20
            )
        
        n_africa_section = article_content.get("n_africa_today_section_value", "- None -")
        if n_africa_section and n_africa_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-n-africa-today-section-und",
                n_africa_section,
                N_AFRICA_TODAY_MAP,
                log.info,
                "N.Africa Today Section",
                required=False,
                wait_timeout=20
            )
        
        middle_east_section = article_content.get("middle_east_today_section_value", "- None -")
        if middle_east_section and middle_east_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-middle-east-today-section-und",
                middle_east_section,
                MIDDLE_EAST_TODAY_MAP,
                log.info,
                "Middle East Today Section",
                required=False,
                wait_timeout=20
            )
        
        baltic_section = article_content.get("baltic_states_today_sections_value", "- None -")
        if baltic_section and baltic_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-baltic-states-today-sectio-und",
                baltic_section,
                BALTIC_STATES_TODAY_MAP,
                log.info,
                "Baltic States Today Section",
                required=False,
                wait_timeout=20
            )
        
        asia_section = article_content.get("asia_today_sections_value", "- None -")
        if asia_section and asia_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-asia-today-sections-und",
                asia_section,
                ASIA_TODAY_SECTIONS_MAP,
                log.info,
                "Asia Today Section",
                required=False,
                wait_timeout=20
            )
        
        latam_section = article_content.get("latam_today_value", "- None -")
        if latam_section and latam_section != "- None -":
            select_dropdown_by_value(
                driver,
                "edit-field-latam-today-und",
                latam_section,
                LATAM_TODAY_MAP,
                log.info,
                "LatAm Today",
                required=False,
                wait_timeout=20
            )
        
        log.info("--- Setting Publication Date ---")
        try:
            date_field = wait.until(EC.presence_of_element_located((By.ID, "edit-field-publication-date-und-0-value-datepicker-popup-0")))
            driver.execute_script("arguments[0].value = arguments[1];", date_field, target_date_str)
            log.info(f"   ✅ Set Publication Date: {target_date_str}")
        except Exception as e:
            log.error(f"   ⚠️ Failed to set Publication Date: {e}")
        
        log.info("🚀 Attempting to submit form...")
        save_button = wait.until(EC.element_to_be_clickable((By.ID, "edit-submit")))
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        time.sleep(1)
        save_button.click()

        wait.until(EC.url_contains("/node/"))
        final_url = driver.current_url

        if "/node/add/article" in final_url:
            log.critical("🔥 Form submission failed - redirected back to add article page")
            try:
                error_messages = driver.find_elements(By.CSS_SELECTOR, ".messages.error")
                if error_messages:
                    for msg in error_messages:
                        log.critical(f"   CMS Error: {msg.text}")
            except: pass
            raise Exception("Form submission failed, redirected back to the add article page.")

        log.info(f"✅ Article submitted successfully! URL: {final_url}")
        return json.dumps({"success": True, "url": final_url, "message": "Article posted successfully."})

    except Exception as e:
        log.critical(f"🔥 An error occurred during browser automation: {e}", exc_info=True)
        try:
            screenshot_path = f"/tmp/cms_error_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            log.info(f"Screenshot saved to {screenshot_path}")
        except: pass
        return json.dumps({"error": f"Failed to post to CMS: {e}"})
    finally:
        if driver:
            if not is_render_env:
                log.info("Waiting 20 seconds for final review (local mode)...")
                time.sleep(20)
            log.info("Closing browser.")
            driver.quit()