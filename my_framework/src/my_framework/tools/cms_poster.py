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
    
    # FIXED: Ensure character limits
    # Website callout - keep it short (first sentence truncated to 200 chars)
    website_callout = first_sentence[:200] if len(first_sentence) > 200 else first_sentence
    
    # Social media callout - must be under 250 chars including hashtags
    hashtags_str = ' '.join(hashtags[:3])  # Limit to 3 hashtags
    social_base = first_sentence[:180] if len(first_sentence) > 180 else first_sentence
    social_media_callout = f"{social_base} {hashtags_str}"
    
    # Ensure social media callout is under 250 chars
    if len(social_media_callout) > 250:
        # Trim the sentence part further
        available_chars = 250 - len(hashtags_str) - 1
        social_base = first_sentence[:available_chars]
        social_media_callout = f"{social_base} {hashtags_str}"
    
    log(f"   Website callout length: {len(website_callout)} chars")
    log(f"   Social media callout length: {len(social_media_callout)} chars")

    # Set proper values
    article_content["weekly_title_value"] = title
    article_content["website_callout_value"] = website_callout
    article_content["social_media_callout_value"] = social_media_callout
    article_content["byline_value"] = username  # FORCE byline to be username
    
    # Ensure required fields have defaults and valid values
    log("Validating required dropdown fields...")
    log(f"   Current daily_subject_value: '{article_content.get('daily_subject_value')}'")
    log(f"   Current key_point_value: '{article_content.get('key_point_value')}'")
    
    if not article_content.get("daily_subject_value") or article_content.get("daily_subject_value") not in ["Macroeconomic News", "Banking And Finance", "Companies and Industries", "Political"]:
        log("   ⚠️ Invalid daily_subject_value, setting default: 'Companies and Industries'")
        article_content["daily_subject_value"] = "Companies and Industries"
    
    if not article_content.get("key_point_value") or article_content.get("key_point_value") not in ["Yes", "No"]:
        log("   ⚠️ Invalid key_point_value, setting default: 'No'")
        article_content["key_point_value"] = "No"
    
    if not article_content.get("machine_written_value") or article_content.get("machine_written_value") not in ["Yes", "No"]:
        log("   Setting machine_written_value: 'Yes'")
        article_content["machine_written_value"] = "Yes"
    
    if not article_content.get("ballot_box_value") or article_content.get("ballot_box_value") not in ["Yes", "No"]:
        log("   Setting ballot_box_value: 'No'")
        article_content["ballot_box_value"] = "No"
    
    log(f"   Final daily_subject_value: '{article_content.get('daily_subject_value')}'")
    log(f"   Final key_point_value: '{article_content.get('key_point_value')}'")
    log("✅ Validation complete")
    
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
            # First, click all collapsed fieldset legends
            collapsed_fieldsets = driver.find_elements(By.CSS_SELECTOR, "fieldset.collapsed legend")
            log(f"   Found {len(collapsed_fieldsets)} collapsed sections")
            for idx, legend in enumerate(collapsed_fieldsets, 1):
                try:
                    driver.execute_script("arguments[0].click();", legend)
                    time.sleep(0.3)  # Give time for expansion
                    log(f"      Expanded section {idx}")
                except Exception as e:
                    log(f"      Failed to expand section {idx}: {e}")
            
            # Wait a moment for all sections to fully expand
            time.sleep(2)
            log(f"✅ Section expansion complete")
        except Exception as e:
            log(f"⚠️ Could not expand sections: {e}")

        # --- DEBUG: Check if dropdown fields exist ---
        log("🔍 Checking for required dropdown field elements...")
        
        # Check Daily Subject (CORRECTED ID)
        daily_subject_check = driver.execute_script("""
            var select = document.getElementById('edit-field-subject-und');
            if (!select) {
                var allSelects = document.getElementsByTagName('select');
                var matches = [];
                for (var i = 0; i < allSelects.length; i++) {
                    var id = allSelects[i].id || '';
                    var name = allSelects[i].name || '';
                    if (id.toLowerCase().includes('subject') ||
                        name.toLowerCase().includes('subject')) {
                        matches.push({id: id, name: name});
                    }
                }
                return {found: false, matches: matches};
            }
            return {found: true, id: select.id, optionsCount: select.options.length};
        """)
        
        if daily_subject_check['found']:
            log(f"   ✅ Found Daily Subject dropdown (ID: edit-field-subject-und, {daily_subject_check['optionsCount']} options)")
        else:
            log("   ❌ Daily Subject dropdown NOT FOUND at ID: edit-field-subject-und")
            if daily_subject_check['matches']:
                log(f"   🔍 Found {len(daily_subject_check['matches'])} similar selects:")
                for match in daily_subject_check['matches'][:5]:
                    log(f"      - ID: '{match['id']}', Name: '{match['name']}'")
        
        # Check Key Point (CORRECTED ID)
        key_point_check = driver.execute_script("""
            var select = document.getElementById('edit-field-key-und');
            if (!select) {
                var allSelects = document.getElementsByTagName('select');
                var matches = [];
                for (var i = 0; i < allSelects.length; i++) {
                    var id = allSelects[i].id || '';
                    var name = allSelects[i].name || '';
                    if (id.toLowerCase().includes('key') ||
                        name.toLowerCase().includes('key')) {
                        matches.push({id: id, name: name});
                    }
                }
                return {found: false, matches: matches};
            }
            return {found: true, id: select.id, optionsCount: select.options.length};
        """)
        
        if key_point_check['found']:
            log(f"   ✅ Found Key Point dropdown (ID: edit-field-key-und, {key_point_check['optionsCount']} options)")
        else:
            log("   ❌ Key Point dropdown NOT FOUND at ID: edit-field-key-und")
            if key_point_check['matches']:
                log(f"   🔍 Found {len(key_point_check['matches'])} similar selects:")
                for match in key_point_check['matches'][:5]:
                    log(f"      - ID: '{match['id']}', Name: '{match['name']}'")
        
        # If either required field is missing, stop here
        if not daily_subject_check['found'] or not key_point_check['found']:
            log("🔥 CRITICAL: Required dropdown fields not found in DOM!")
            log("   Possible causes:")
            log("   1. Field IDs have changed in CMS")
            log("   2. Fields are in a section that wasn't expanded")
            log("   3. Page hasn't fully loaded")
            log("   Taking screenshot for debugging...")
            try:
                driver.save_screenshot("cms_debug_screenshot.png")
                log("   Screenshot saved: cms_debug_screenshot.png")
            except:
                pass
            driver.quit()
            return json.dumps({"error": "Required dropdown fields not found in CMS form"})

        # --- HELPER FUNCTIONS ---
        def safe_fill(field_id, value, field_name):
            """Fill text input using JavaScript for better reliability."""
            try:
                if value:
                    # Properly escape value for JavaScript
                    value_str = str(value)
                    # Escape backslashes first, then quotes
                    value_escaped = value_str.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
                    
                    # Use JavaScript to set value directly
                    js_script = f"""
                    var element = document.getElementById('{field_id}');
                    if (element) {{
                        element.value = '{value_escaped}';
                        // Trigger input event
                        var event = new Event('input', {{ bubbles: true }});
                        element.dispatchEvent(event);
                        return true;
                    }}
                    return false;
                    """
                    result = driver.execute_script(js_script)
                    if result:
                        log(f"   ✅ {field_name}")
                    else:
                        log(f"   ⚠️ Failed {field_name}: Element not found (ID: {field_id})")
            except Exception as e:
                log(f"   ⚠️ Failed {field_name}: {str(e)[:80]}")

        def tick_checkboxes(id_list, section_name):
            """Tick checkboxes using JavaScript."""
            if not id_list:
                log(f"   ⚠️ No {section_name} to tick")
                return
            log(f"   Ticking {len(id_list)} {section_name}...")
            for checkbox_id in id_list:
                try:
                    js_script = f"""
                    var checkbox = document.getElementById('{checkbox_id}');
                    if (checkbox && !checkbox.checked) {{
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                    return false;
                    """
                    result = driver.execute_script(js_script)
                    if result:
                        log(f"      ✅ Ticked {section_name}")
                except Exception as e:
                    log(f"      ⚠️ Failed checkbox: {str(e)[:30]}")

        # --- DEBUG: Find text input field IDs ---
        log("🔍 Searching for text input field IDs...")
        field_search = driver.execute_script("""
            var fields = {
                byline: null,
                abstract: null,
                seo_description: null,
                seo_keywords: null,
                google_news_keywords: null,
                hashtags: null
            };
            
            var allInputs = document.querySelectorAll('input[type="text"], textarea');
            
            for (var i = 0; i < allInputs.length; i++) {
                var el = allInputs[i];
                var id = el.id || '';
                var name = el.name || '';
                
                if (id.includes('byline') || name.includes('byline')) {
                    fields.byline = id;
                }
                if (id.includes('abstract') || name.includes('abstract')) {
                    fields.abstract = id;
                }
                if (id.includes('seo-description') || name.includes('seo_description')) {
                    fields.seo_description = id;
                }
                if (id.includes('seo-keywords') || name.includes('seo_keywords')) {
                    fields.seo_keywords = id;
                }
                if (id.includes('google-news-keywords') || name.includes('google_news_keywords')) {
                    fields.google_news_keywords = id;
                }
                if (id.includes('hashtag') || name.includes('hashtag')) {
                    fields.hashtags = id;
                }
            }
            
            return fields;
        """)
        
        log("   Text input field IDs found:")
        for field_name, field_id in field_search.items():
            if field_id:
                log(f"      ✅ {field_name}: {field_id}")
            else:
                log(f"      ❌ {field_name}: NOT FOUND")
        
        # Update field IDs if found
        if field_search.get('byline'):
            byline_id = field_search['byline']
        else:
            byline_id = "edit-field-byline-und-0-value"  # fallback
            
        if field_search.get('abstract'):
            abstract_id = field_search['abstract']
        else:
            abstract_id = "edit-field-abstract-und-0-value"  # fallback
            
        if field_search.get('seo_description'):
            seo_desc_id = field_search['seo_description']
        else:
            seo_desc_id = "edit-field-seo-description-und-0-value"  # fallback
            
        if field_search.get('seo_keywords'):
            seo_keywords_id = field_search['seo_keywords']
        else:
            seo_keywords_id = "edit-field-seo-keywords-und-0-value"  # fallback
            
        if field_search.get('google_news_keywords'):
            google_news_id = field_search['google_news_keywords']
        else:
            google_news_id = "edit-field-google-news-keywords-und-0-value"  # fallback
            
        if field_search.get('hashtags'):
            hashtags_id = field_search['hashtags']
        else:
            hashtags_id = "edit-field-hashtags-und-0-value"  # fallback

        # --- FILL BASIC FIELDS ---
        log("Filling basic fields...")
        safe_fill("edit-title", title, "Title")
        safe_fill(byline_id, username, "Byline")
        
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
        safe_fill(abstract_id, article_content.get('abstract_value'), "Abstract")

        # --- SEO FIELDS ---
        log("Filling SEO fields...")
        safe_fill("edit-field-seo-title-und-0-value", article_content.get('seo_title_value'), "SEO Title")
        safe_fill(seo_desc_id, article_content.get('seo_description'), "SEO Description")
        safe_fill(seo_keywords_id, article_content.get('seo_keywords'), "SEO Keywords")
        safe_fill(google_news_id, article_content.get('google_news_keywords_value'), "Google News Keywords")
        safe_fill(hashtags_id, " ".join(hashtags), "Hashtags")

        # --- CHECKBOXES ---
        log("Setting publications...")
        tick_checkboxes(article_content.get('publication_id_selections', []), "Publications")
        
        log("Setting countries...")
        tick_checkboxes(article_content.get('country_id_selections', []), "Countries")
        
        log("Setting industries...")
        tick_checkboxes(article_content.get('industry_id_selections', []), "Industries")

        # --- DROPDOWN FIELDS (using VALUE selection with CORRECTED IDs) ---
        log("Setting dropdowns (using option values)...")
        
        # REQUIRED FIELDS - Mark as required (CORRECTED IDs)
        log("Setting REQUIRED dropdowns...")
        success = True
        
        if not select_dropdown_by_value(driver, "edit-field-subject-und",  # CORRECTED ID
                                 article_content.get('daily_subject_value'), 
                                 DAILY_SUBJECT_MAP, log, "Daily Subject (REQUIRED)", required=True):
            success = False
            
        if not select_dropdown_by_value(driver, "edit-field-key-und",  # CORRECTED ID
                                 article_content.get('key_point_value'), 
                                 KEY_POINT_MAP, log, "Key Point (REQUIRED)", required=True):
            success = False
        
        if not success:
            log("🔥 CRITICAL: Required fields not filled! CMS will reject submission.")
            driver.quit()
            return json.dumps({"error": "Required dropdown fields (Daily Subject, Key Point) not filled properly."})
        
        # OPTIONAL FIELDS
        log("Setting optional dropdowns...")
        select_dropdown_by_value(driver, "edit-field-machine-written-und", 
                                 article_content.get('machine_written_value'), 
                                 MACHINE_WRITTEN_MAP, log, "Machine Written")
        select_dropdown_by_value(driver, "edit-field-ballot-box-und", 
                                 article_content.get('ballot_box_value'), 
                                 BALLOT_BOX_MAP, log, "Ballot Box")

        # Regional section dropdowns
        select_dropdown_by_value(driver, "edit-field-africa-daily-section-und", 
                                 article_content.get('africa_daily_section_value'), 
                                 AFRICA_DAILY_SECTION_MAP, log, "Africa Daily Section")
        select_dropdown_by_value(driver, "edit-field-southeast-europe-today-se-und", 
                                 article_content.get('southeast_europe_today_sections_value'), 
                                 SOUTHEAST_EUROPE_SECTIONS_MAP, log, "Southeast Europe Section")
        select_dropdown_by_value(driver, "edit-field-cee-news-watch-country-se-und", 
                                 article_content.get('cee_news_watch_country_sections_value'), 
                                 CEE_NEWS_WATCH_MAP, log, "CEE News Watch Section")
        select_dropdown_by_value(driver, "edit-field-n-africa-today-section-und", 
                                 article_content.get('n_africa_today_section_value'), 
                                 N_AFRICA_TODAY_MAP, log, "N.Africa Today Section")
        select_dropdown_by_value(driver, "edit-field-middle-east-today-section-und", 
                                 article_content.get('middle_east_today_section_value'), 
                                 MIDDLE_EAST_TODAY_MAP, log, "Middle East Today Section")
        select_dropdown_by_value(driver, "edit-field-baltic-states-today-secti-und", 
                                 article_content.get('baltic_states_today_sections_value'), 
                                 BALTIC_STATES_TODAY_MAP, log, "Baltic States Today Section")
        select_dropdown_by_value(driver, "edit-field-asia-today-sections-und", 
                                 article_content.get('asia_today_sections_value'), 
                                 ASIA_TODAY_SECTIONS_MAP, log, "Asia Today Section")
        select_dropdown_by_value(driver, "edit-field-latam-today-und", 
                                 article_content.get('latam_today_value'), 
                                 LATAM_TODAY_MAP, log, "LatAm Today")

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