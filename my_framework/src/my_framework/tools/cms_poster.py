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
)

def log(message):
    print(f"   - {message}", flush=True)

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
def post_article_to_cms(article_json_string: str, username: str, password: str) -> str:
    """
    Logs into the CMS and submits an article using browser automation with hardcoded field IDs.
    """
    log("🤖 TOOL: Starting CMS Posting...")

    login_url = "https://cms.intellinews.com/user/login"
    add_article_url = "https://cms.intellinews.com/node/add/article"

    try:
        article_content = json.loads(article_json_string)
    except (json.JSONDecodeError, TypeError) as e:
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
    social_media_callout = f"{first_sentence} {' '.join(hashtags)}"

    # Set proper values
    article_content["weekly_title_value"] = title
    article_content["website_callout_value"] = first_sentence
    article_content["social_media_callout_value"] = social_media_callout
    article_content["byline_value"] = username  # FORCE byline to be username
    
    # Ensure required fields have defaults
    if not article_content.get("daily_subject_value"):
        article_content["daily_subject_value"] = "Companies and Industries"  # Default
    
    if not article_content.get("key_point_value"):
        article_content["key_point_value"] = "No"  # Default
    
    # Extract 5 keywords from seo_keywords if present
    seo_keywords_str = article_content.get("seo_keywords", "")
    if isinstance(seo_keywords_str, str):
        keywords_list = [k.strip() for k in seo_keywords_str.split(',') if k.strip()]
        # Take first 5 keywords
        keywords_5 = ', '.join(keywords_list[:5])
        article_content["seo_keywords"] = keywords_5
        article_content["google_news_keywords_value"] = keywords_5
    
    # Get checkbox IDs
    article_content["publication_id_selections"] = [PUBLICATION_MAP[name] for name in article_content.get("publications", []) if name in PUBLICATION_MAP]
    article_content["country_id_selections"] = [COUNTRY_MAP[name] for name in article_content.get("countries", []) if name in COUNTRY_MAP]
    article_content["industry_id_selections"] = [INDUSTRY_MAP[name] for name in article_content.get("industries", []) if name in INDUSTRY_MAP]

    driver = None
    is_render_env = 'RENDER' in os.environ
    
    try:
        chrome_options = webdriver.ChromeOptions()
        service = None

        if is_render_env:
            log("Running in Render environment (headless mode).")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            binary_path = os.environ.get("GOOGLE_CHROME_BIN")
            driver_path = os.environ.get("CHROMEDRIVER_PATH")

            if not binary_path or not os.path.isfile(binary_path):
                return json.dumps({"error": f"Chrome binary not found. GOOGLE_CHROME_BIN='{binary_path}'"})
            if not driver_path or not os.path.isfile(driver_path):
                return json.dumps({"error": f"ChromeDriver not found. CHROMEDRIVER_PATH='{driver_path}'"})

            chrome_options.binary_location = binary_path
            service = Service(executable_path=driver_path)
        else:
            log("Running in local environment (visible mode).")

        log("Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 30)
        log("✅ WebDriver initialized successfully.")

        # --- LOGIN ---
        log(f"Navigating to login: {login_url}")
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
        time.sleep(2)  # Extra wait for full page load
        log("📝 Article form loaded.")

        # --- EXPAND ALL COLLAPSED FIELDSETS ---
        log("Expanding collapsed sections...")
        try:
            # Click all collapsed fieldset legends
            collapsed_fieldsets = driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed legend")
            for legend in collapsed_fieldsets:
                try:
                    driver.execute_script("arguments[0].click();", legend)
                    time.sleep(0.2)
                except:
                    pass
            log(f"✅ Expanded {len(collapsed_fieldsets)} sections")
        except Exception as e:
            log(f"⚠️ Could not expand sections: {e}")

        time.sleep(1)  # Wait for sections to expand

        # --- HELPER FUNCTIONS ---
        def safe_fill(field_id, value, field_name):
            try:
                if value:
                    element = wait.until(EC.presence_of_element_located((By.ID, field_id)))
                    element.clear()
                    element.send_keys(remove_non_bmp_chars(str(value)))
                    log(f"   ✅ {field_name}")
            except Exception as e:
                log(f"   ⚠️ Failed {field_name}: {str(e)[:50]}")

        def safe_select(field_id, value, field_name):
            try:
                if value and str(value).strip() and str(value).lower() != "- none -":
                    element = wait.until(EC.presence_of_element_located((By.ID, field_id)))
                    select = Select(element)
                    select.select_by_visible_text(str(value))
                    log(f"   ✅ {field_name}: {value}")
            except Exception as e:
                log(f"   ⚠️ Failed {field_name}: {str(e)[:50]}")

        def tick_checkboxes(id_list, section_name):
            if not id_list:
                log(f"   ⚠️ No {section_name} to tick")
                return
            log(f"   Ticking {len(id_list)} {section_name}...")
            for checkbox_id in id_list:
                try:
                    checkbox = driver.find_element(By.ID, checkbox_id)
                    driver.execute_script("arguments[0].click();", checkbox)
                    log(f"      ✅ Ticked {section_name}")
                except Exception as e:
                    log(f"      ⚠️ Failed checkbox {checkbox_id[:30]}: {str(e)[:30]}")

        # --- FILL BASIC FIELDS ---
        log("Filling basic fields...")
        safe_fill("edit-title", title, "Title")
        safe_fill("edit-field-byline-und-0-value", username, "Byline")  # FORCE username as byline
        
        # Date field
        try:
            date_field = driver.find_element(By.ID, "edit-field-sending-date-und-0-value-datepicker-popup-0")
            driver.execute_script(f"arguments[0].value = '{target_date_str}';", date_field)
            log(f"   ✅ Date: {target_date_str}")
        except Exception as e:
            log(f"   ⚠️ Failed Date: {str(e)[:50]}")

        # --- BODY CONTENT (CKEditor) ---
        log("Filling body content...")
        try:
            time.sleep(1)
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.cke_wysiwyg_frame")))
            driver.switch_to.frame(iframe)
            body_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            driver.execute_script("arguments[0].innerHTML = arguments[1];", body_element, body_html)
            driver.switch_to.default_content()
            log("   ✅ Body content filled")
        except Exception as e:
            log(f"   ⚠️ Failed body: {str(e)[:50]}")
            driver.switch_to.default_content()

        # --- METADATA FIELDS ---
        log("Filling metadata...")
        safe_fill("edit-field-weekly-title-und-0-value", article_content.get('weekly_title_value'), "Weekly Title")
        safe_fill("edit-field-website-callout-und-0-value", article_content.get('website_callout_value'), "Website Callout")
        safe_fill("edit-field-social-media-callout-und-0-value", article_content.get('social_media_callout_value'), "Social Media Callout")
        safe_fill("edit-field-abstract-und-0-value", article_content.get('abstract_value'), "Abstract")

        # --- SEO FIELDS ---
        log("Filling SEO fields...")
        safe_fill("edit-field-seo-title-und-0-value", article_content.get('seo_title_value'), "SEO Title")
        safe_fill("edit-field-seo-description-und-0-value", article_content.get('seo_description'), "SEO Description")
        safe_fill("edit-field-seo-keywords-und-0-value", article_content.get('seo_keywords'), "SEO Keywords")
        safe_fill("edit-field-google-news-keywords-und-0-value", article_content.get('google_news_keywords_value'), "Google News Keywords")
        safe_fill("edit-field-hashtags-und-0-value", " ".join(hashtags), "Hashtags")

        # --- CHECKBOXES ---
        log("Setting publications...")
        tick_checkboxes(article_content.get('publication_id_selections', []), "Publications")
        
        log("Setting countries...")
        tick_checkboxes(article_content.get('country_id_selections', []), "Countries")
        
        log("Setting industries...")
        tick_checkboxes(article_content.get('industry_id_selections', []), "Industries")

        # --- DROPDOWN FIELDS ---
        log("Setting dropdowns...")
        safe_select("edit-field-daily-subject-und", article_content.get('daily_subject_value'), "Daily Subject")
        safe_select("edit-field-key-point-und", article_content.get('key_point_value'), "Key Point")
        safe_select("edit-field-machine-written-und", article_content.get('machine_written_value'), "Machine Written")
        safe_select("edit-field-ballot-box-und", article_content.get('ballot_box_value'), "Ballot Box")

        # Regional section dropdowns (if applicable)
        safe_select("edit-field-africa-daily-section-und", article_content.get('africa_daily_section_value'), "Africa Daily Section")
        safe_select("edit-field-southeast-europe-today-se-und", article_content.get('southeast_europe_today_sections_value'), "Southeast Europe Section")
        safe_select("edit-field-cee-news-watch-country-se-und", article_content.get('cee_news_watch_country_sections_value'), "CEE News Watch Section")
        safe_select("edit-field-n-africa-today-section-und", article_content.get('n_africa_today_section_value'), "N.Africa Today Section")
        safe_select("edit-field-middle-east-today-section-und", article_content.get('middle_east_today_section_value'), "Middle East Today Section")
        safe_select("edit-field-baltic-states-today-secti-und", article_content.get('baltic_states_today_sections_value'), "Baltic States Today Section")
        safe_select("edit-field-asia-today-sections-und", article_content.get('asia_today_sections_value'), "Asia Today Section")
        safe_select("edit-field-latam-today-und", article_content.get('latam_today_value'), "LatAm Today")

        # --- SCROLL AND SAVE ---
        log("Scrolling to save button...")
        save_button = wait.until(EC.presence_of_element_located((By.ID, "edit-submit")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
        time.sleep(1)

        log("🚀 Clicking Save...")
        driver.execute_script("arguments[0].click();", save_button)
        
        # Wait for redirect
        try:
            wait.until(EC.url_changes(add_article_url))
            time.sleep(2)
            final_url = driver.current_url
            log(f"✅ Article submitted! URL: {final_url}")
            return json.dumps({"success": True, "url": final_url, "message": "Article posted successfully."})
        except:
            log("⚠️ Could not confirm submission")
            return json.dumps({"success": False, "message": "Form filled but submission unclear."})

    except Exception as e:
        log(f"🔥 Error: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": f"Failed to post to CMS: {e}"})
    finally:
        if driver:
            if not is_render_env:
                log("Waiting 30 seconds (local mode)...")
                time.sleep(30)
            log("Closing browser.")
            driver.quit()