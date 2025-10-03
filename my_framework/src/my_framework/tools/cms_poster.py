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
    PUBLICATION_MAP,
    COUNTRY_MAP,
    INDUSTRY_MAP,
    select_dropdown_by_value,
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
    LATAM_TODAY_MAP
)
from my_framework.agents.loggerbot import LoggerBot

def strip_html(text):
    """Removes HTML tags from a string."""
    return re.sub('<[^<]+?>', '', text)

def remove_bold_formatting(text):
    """Removes ** markdown bold formatting from text."""
    if not isinstance(text, str):
        return text
    return re.sub(r'\*\*', '', text)

def clean_article_content(article_content):
    """Removes ** formatting from all text fields in the article."""
    text_fields = [
        'title', 'body', 'weekly_title_value', 'website_callout_value',
        'social_media_callout_value', 'seo_title_value', 'seo_description',
        'seo_keywords', 'abstract_value', 'google_news_keywords_value',
        'byline_value'
    ]
    
    for field in text_fields:
        if field in article_content and isinstance(article_content[field], str):
            article_content[field] = remove_bold_formatting(article_content[field])
    
    # Clean hashtags list
    if 'hashtags' in article_content and isinstance(article_content['hashtags'], list):
        article_content['hashtags'] = [remove_bold_formatting(tag) for tag in article_content['hashtags']]
    
    return article_content

@tool
def post_article_to_cms(article_json_string: str, username: str, password: str, logger=None) -> str:
    """
    Logs into the CMS and submits an article using browser automation with hardcoded field IDs.
    """
    log = logger or LoggerBot.get_logger()
    log.info("🤖 TOOL: Starting CMS Posting...")

    login_url = "https://cms.intellinews.com/user/login"
    add_article_url = "https://cms.intellinews.com/node/add/article"

    try:
        article_content = json.loads(article_json_string)
    except (json.JSONDecodeError, TypeError) as e:
        log.error(f"Invalid JSON provided to CMS poster: {e}", exc_info=True)
        return json.dumps({"error": f"Invalid JSON provided to CMS poster: {e}"})

    # Clean all ** formatting from the article
    article_content = clean_article_content(article_content)

    # --- Pre-computation of fields ---
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
    
    # FIXED: Ensure character limits
    website_callout = first_sentence[:200]
    
    hashtags_str = ' '.join(hashtags[:3])
    social_base = first_sentence[:180]
    social_media_callout = f"{social_base} {hashtags_str}"
    
    if len(social_media_callout) > 250:
        available_chars = 250 - len(hashtags_str) - 1
        social_base = first_sentence[:available_chars]
        social_media_callout = f"{social_base} {hashtags_str}"
    
    log.debug(f"   Website callout length: {len(website_callout)} chars")
    log.debug(f"   Social media callout length: {len(social_media_callout)} chars")

    article_content["weekly_title_value"] = title
    article_content["website_callout_value"] = website_callout
    article_content["social_media_callout_value"] = social_media_callout
    article_content["byline_value"] = username
    
    log.info("Validating required dropdown fields...")
    log.debug(f"   Current daily_subject_value: '{article_content.get('daily_subject_value')}'")
    log.debug(f"   Current key_point_value: '{article_content.get('key_point_value')}'")
    
    if not article_content.get("daily_subject_value") or article_content.get("daily_subject_value") not in ["Macroeconomic News", "Banking And Finance", "Companies and Industries", "Political"]:
        log.warning("   ⚠️ Invalid daily_subject_value, setting default: 'Companies and Industries'")
        article_content["daily_subject_value"] = "Companies and Industries"
    
    if not article_content.get("key_point_value") or article_content.get("key_point_value") not in ["Yes", "No"]:
        log.warning("   ⚠️ Invalid key_point_value, setting default: 'No'")
        article_content["key_point_value"] = "No"
    
    if not article_content.get("machine_written_value") or article_content.get("machine_written_value") not in ["Yes", "No"]:
        log.info("   Setting machine_written_value: 'Yes'")
        article_content["machine_written_value"] = "Yes"
    
    if not article_content.get("ballot_box_value") or article_content.get("ballot_box_value") not in ["Yes", "No"]:
        log.info("   Setting ballot_box_value: 'No'")
        article_content["ballot_box_value"] = "No"
    
    log.debug(f"   Final daily_subject_value: '{article_content.get('daily_subject_value')}'")
    log.debug(f"   Final key_point_value: '{article_content.get('key_point_value')}'")
    log.info("✅ Validation complete")
    
    seo_keywords_str = article_content.get("seo_keywords", "")
    if isinstance(seo_keywords_str, str):
        keywords_list = [k.strip() for k in seo_keywords_str.split(',') if k.strip()]
        keywords_5 = ', '.join(keywords_list[:5])
        article_content["seo_keywords"] = keywords_5
        article_content["google_news_keywords_value"] = keywords_5
    
    article_content["publication_id_selections"] = [PUBLICATION_MAP[name] for name in article_content.get("publications", []) if name in PUBLICATION_MAP]
    article_content["country_id_selections"] = [COUNTRY_MAP[name] for name in article_content.get("countries", []) if name in COUNTRY_MAP]
    article_content["industry_id_selections"] = [INDUSTRY_MAP[name] for name in article_content.get("industries", []) if name in INDUSTRY_MAP]

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

            binary_path = os.environ.get("GOOGLE_CHROME_BIN")
            driver_path = os.environ.get("CHROMEDRIVER_PATH")

            if not binary_path or not os.path.isfile(binary_path):
                log.critical(f"Chrome binary not found. GOOGLE_CHROME_BIN='{binary_path}'")
                return json.dumps({"error": f"Chrome binary not found. GOOGLE_CHROME_BIN='{binary_path}'"})
            if not driver_path or not os.path.isfile(driver_path):
                log.critical(f"ChromeDriver not found. CHROMEDRIVER_PATH='{driver_path}'")
                return json.dumps({"error": f"ChromeDriver not found. CHROMEDRIVER_PATH='{driver_path}'"})

            chrome_options.binary_location = binary_path
            service = Service(executable_path=driver_path)
        else:
            log.info("Running in local environment (visible mode).")

        log.info("Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 30)
        log.info("✅ WebDriver initialized successfully.")

        # --- LOGIN ---
        log.info(f"Navigating to login: {login_url}")
        driver.get(login_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        wait.until(EC.presence_of_element_located((By.ID, "main-content")))
        log.info("✅ Login successful.")

        # --- NAVIGATE TO ADD ARTICLE ---
        log.info("Navigating to add article page...")
        driver.get(add_article_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-title")))
        time.sleep(2)
        log.info("📝 Article form loaded.")

        # --- EXPAND ALL COLLAPSED FIELDSETS ---
        log.info("Expanding collapsed sections...")
        try:
            collapsed_fieldsets = driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed legend")
            log.debug(f"   Found {len(collapsed_fieldsets)} collapsed sections")
            for idx, legend in enumerate(collapsed_fieldsets, 1):
                try:
                    driver.execute_script("arguments[0].click();", legend)
                    time.sleep(0.3)
                    log.debug(f"      Expanded section {idx}")
                except Exception as e:
                    log.warning(f"      Failed to expand section {idx}: {e}")
            
            time.sleep(2)
            log.info(f"✅ Section expansion complete")
        except Exception as e:
            log.error(f"⚠️ Could not expand sections: {e}", exc_info=True)

        # --- DEBUG: Check if dropdown fields exist ---
        log.info("🔍 Checking for required dropdown field elements...")
        
        daily_subject_check = driver.execute_script("""
            var select = document.getElementById('edit-field-subject-und');
            if (!select) { return {found: false}; }
            return {found: true, id: select.id, optionsCount: select.options.length};
        """)
        
        if daily_subject_check['found']:
            log.debug(f"   ✅ Found Daily Subject dropdown (ID: edit-field-subject-und, {daily_subject_check['optionsCount']} options)")
        else:
            log.critical("   ❌ Daily Subject dropdown NOT FOUND at ID: edit-field-subject-und")
        
        key_point_check = driver.execute_script("""
            var select = document.getElementById('edit-field-key-und');
            if (!select) { return {found: false}; }
            return {found: true, id: select.id, optionsCount: select.options.length};
        """)
        
        if key_point_check['found']:
            log.debug(f"   ✅ Found Key Point dropdown (ID: edit-field-key-und, {key_point_check['optionsCount']} options)")
        else:
            log.critical("   ❌ Key Point dropdown NOT FOUND at ID: edit-field-key-und")
        
        if not daily_subject_check['found'] or not key_point_check['found']:
            log.critical("🔥 CRITICAL: Required dropdown fields not found in DOM!")
            try:
                driver.save_screenshot("cms_debug_screenshot.png")
                log.info("   Screenshot saved: cms_debug_screenshot.png")
            except:
                pass
            driver.quit()
            return json.dumps({"error": "Required dropdown fields not found in CMS form"})

        # --- HELPER FUNCTIONS ---
        def safe_fill(field_id, value, field_name):
            try:
                if value:
                    value_str = str(value)
                    value_escaped = value_str.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
                    
                    js_script = f"document.getElementById('{field_id}').value = '{value_escaped}';"
                    driver.execute_script(js_script)
                    log.debug(f"   ✅ {field_name}")
            except Exception as e:
                log.error(f"   ⚠️ Failed {field_name}: {str(e)[:80]}", exc_info=True)

        def tick_checkboxes(id_list, section_name):
            if not id_list:
                log.warning(f"   ⚠️ No {section_name} to tick")
                return
            log.info(f"   Ticking {len(id_list)} {section_name}...")
            for checkbox_id in id_list:
                try:
                    js_script = f"document.getElementById('{checkbox_id}').checked = true;"
                    driver.execute_script(js_script)
                    log.debug(f"      ✅ Ticked {section_name}")
                except Exception as e:
                    log.error(f"      ⚠️ Failed checkbox: {str(e)[:30]}", exc_info=True)

        # --- FILL BASIC FIELDS ---
        log.info("Filling basic fields...")
        safe_fill("edit-title", title, "Title")
        safe_fill("edit-field-byline-und-0-value", username, "Byline")
        
        try:
            date_field = driver.find_element(By.ID, "edit-field-sending-date-und-0-value-datepicker-popup-0")
            driver.execute_script(f"arguments[0].value = '{target_date_str}';", date_field)
            log.debug(f"   ✅ Date: {target_date_str}")
        except Exception as e:
            log.error(f"   ⚠️ Failed Date: {str(e)[:50]}", exc_info=True)

        # --- BODY CONTENT (CKEditor) ---
        log.info("Filling body content...")
        try:
            time.sleep(1)
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.cke_wysiwyg_frame")))
            driver.switch_to.frame(iframe)
            body_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            driver.execute_script("arguments[0].innerHTML = arguments[1];", body_element, body_html)
            driver.switch_to.default_content()
            log.info("   ✅ Body content filled")
        except Exception as e:
            log.error(f"   ⚠️ Failed body: {str(e)[:50]}", exc_info=True)
            driver.switch_to.default_content()

        # --- METADATA FIELDS ---
        log.info("Filling metadata...")
        safe_fill("edit-field-weekly-title-und-0-value", article_content.get('weekly_title_value'), "Weekly Title")
        safe_fill("edit-field-website-callout-und-0-value", article_content.get('website_callout_value'), "Website Callout")
        safe_fill("edit-field-social-media-callout-und-0-value", article_content.get('social_media_callout_value'), "Social Media Callout")
        safe_fill("edit-field-abstract-und-0-value", article_content.get('abstract_value'), "Abstract")

        # --- SEO FIELDS ---
        log.info("Filling SEO fields...")
        safe_fill("edit-field-seo-title-und-0-value", article_content.get('seo_title_value'), "SEO Title")
        safe_fill("edit-field-seo-description-und-0-value", article_content.get('seo_description'), "SEO Description")
        safe_fill("edit-field-seo-keywords-und-0-value", article_content.get('seo_keywords'), "SEO Keywords")
        safe_fill("edit-field-google-news-keywords-und-0-value", article_content.get('google_news_keywords_value'), "Google News Keywords")
        safe_fill("edit-field-hashtags-und-0-value", " ".join(hashtags), "Hashtags")

        # --- CHECKBOXES ---
        tick_checkboxes(article_content.get('publication_id_selections', []), "Publications")
        tick_checkboxes(article_content.get('country_id_selections', []), "Countries")
        tick_checkboxes(article_content.get('industry_id_selections', []), "Industries")

        # --- DROPDOWN FIELDS (using VALUE selection with CORRECTED IDs) ---
        log.info("Setting dropdowns (using option values)...")
        
        log.info("Setting REQUIRED dropdowns...")
        success = True
        
        if not select_dropdown_by_value(driver, "edit-field-subject-und", article_content.get('daily_subject_value'), DAILY_SUBJECT_MAP, log.debug, "Daily Subject (REQUIRED)", required=True):
            success = False
            
        if not select_dropdown_by_value(driver, "edit-field-key-und", article_content.get('key_point_value'), KEY_POINT_MAP, log.debug, "Key Point (REQUIRED)", required=True):
            success = False
        
        if not success:
            log.critical("🔥 CRITICAL: Required fields not filled! CMS will reject submission.")
            driver.quit()
            return json.dumps({"error": "Required dropdown fields (Daily Subject, Key Point) not filled properly."})
        
        log.info("Setting optional dropdowns...")
        select_dropdown_by_value(driver, "edit-field-machine-written-und", article_content.get('machine_written_value'), MACHINE_WRITTEN_MAP, log.debug, "Machine Written")
        select_dropdown_by_value(driver, "edit-field-ballot-box-und", article_content.get('ballot_box_value'), BALLOT_BOX_MAP, log.debug, "Ballot Box")

        # Regional section dropdowns
        select_dropdown_by_value(driver, "edit-field-africa-daily-section-und", article_content.get('africa_daily_section_value'), AFRICA_DAILY_SECTION_MAP, log.debug, "Africa Daily Section")
        select_dropdown_by_value(driver, "edit-field-southeast-europe-today-se-und", article_content.get('southeast_europe_today_sections_value'), SOUTHEAST_EUROPE_SECTIONS_MAP, log.debug, "Southeast Europe Section")
        select_dropdown_by_value(driver, "edit-field-cee-news-watch-country-se-und", article_content.get('cee_news_watch_country_sections_value'), CEE_NEWS_WATCH_MAP, log.debug, "CEE News Watch Section")
        select_dropdown_by_value(driver, "edit-field-n-africa-today-section-und", article_content.get('n_africa_today_section_value'), N_AFRICA_TODAY_MAP, log.debug, "N.Africa Today Section")
        select_dropdown_by_value(driver, "edit-field-middle-east-today-section-und", article_content.get('middle_east_today_section_value'), MIDDLE_EAST_TODAY_MAP, log.debug, "Middle East Today Section")
        select_dropdown_by_value(driver, "edit-field-baltic-states-today-secti-und", article_content.get('baltic_states_today_sections_value'), BALTIC_STATES_TODAY_MAP, log.debug, "Baltic States Today Section")
        select_dropdown_by_value(driver, "edit-field-asia-today-sections-und", article_content.get('asia_today_sections_value'), ASIA_TODAY_SECTIONS_MAP, log.debug, "Asia Today Section")
        select_dropdown_by_value(driver, "edit-field-latam-today-und", article_content.get('latam_today_value'), LATAM_TODAY_MAP, log.debug, "LatAm Today")

        # --- SCROLL AND SAVE ---
        log.info("Scrolling to save button...")
        save_button = wait.until(EC.presence_of_element_located((By.ID, "edit-submit")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
        time.sleep(1)

        log.info("🚀 Clicking Save...")
        driver.execute_script("arguments[0].click();", save_button)
        
        try:
            wait.until(EC.url_changes(add_article_url))
            time.sleep(2)
            final_url = driver.current_url
            log.info(f"✅ Article submitted! URL: {final_url}")
            return json.dumps({"success": True, "url": final_url, "message": "Article posted successfully."})
        except:
            log.warning("⚠️ Could not confirm submission")
            return json.dumps({"success": False, "message": "Form filled but submission unclear."})

    except Exception as e:
        log.critical(f"🔥 Error: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to post to CMS: {e}"})
    finally:
        if driver:
            if not is_render_env:
                log.info("Waiting 30 seconds (local mode)...")
                time.sleep(30)
            log.info("Closing browser.")
            driver.quit()