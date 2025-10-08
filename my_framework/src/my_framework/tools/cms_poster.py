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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, JavascriptException
from my_framework.agents.utils import (
    remove_non_bmp_chars,
    tick_checkboxes_by_id,
    COUNTRY_MAP,
    PUBLICATION_MAP,
    INDUSTRY_MAP,
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

def transform_article_data(article_data: dict, log) -> dict:
    """
    Transform editor output into CMS-compatible format.
    Maps country/publication/industry names to checkbox IDs.
    """
    log.info("Transforming article data for CMS...")
    
    transformed = {}
    
    # Title and Body - use correct keys
    transformed['title_value'] = article_data.get('title', '')
    transformed['body_value'] = article_data.get('body', '')
    transformed['weekly_title_value'] = article_data.get('weekly_title_value', article_data.get('title', ''))
    transformed['byline_value'] = article_data.get('byline_value', '')
    transformed['website_callout_value'] = article_data.get('website_callout_value', '')
    transformed['social_media_callout_value'] = article_data.get('social_media_callout_value', '')
    transformed['abstract_value'] = article_data.get('abstract_value', '')
    transformed['google_news_keywords_value'] = article_data.get('google_news_keywords_value', '')
    
    # SEO Keywords - handle both string and list
    seo_keywords = article_data.get('seo_keywords', '')
    if isinstance(seo_keywords, list):
        transformed['seo_keywords_value'] = ', '.join(seo_keywords)
    else:
        transformed['seo_keywords_value'] = seo_keywords
    
    # Map country names to IDs
    countries = article_data.get('countries', [])
    if countries:
        country_ids = [COUNTRY_MAP[name] for name in countries if name in COUNTRY_MAP]
        transformed['country_id_selections'] = country_ids
        log.info(f"   - Mapped {len(country_ids)} countries to IDs")
    else:
        transformed['country_id_selections'] = []
        log.warning("   - ⚠️ No countries provided!")
    
    # Map publication names to IDs
    publications = article_data.get('publications', [])
    if publications:
        publication_ids = [PUBLICATION_MAP[name] for name in publications if name in PUBLICATION_MAP]
        transformed['publication_id_selections'] = publication_ids
        log.info(f"   - Mapped {len(publication_ids)} publications to IDs")
    else:
        transformed['publication_id_selections'] = []
        log.warning("   - ⚠️ No publications provided!")
    
    # Map industry names to IDs
    industries = article_data.get('industries', [])
    if industries:
        industry_ids = [INDUSTRY_MAP[name] for name in industries if name in INDUSTRY_MAP]
        transformed['industry_id_selections'] = industry_ids
        log.info(f"   - Mapped {len(industry_ids)} industries to IDs")
    else:
        transformed['industry_id_selections'] = []
    
    # Map dropdown values
    daily_subject = article_data.get('daily_subject_value', 'Companies and Industries')
    transformed['daily_subject_value'] = DAILY_SUBJECT_MAP.get(daily_subject, '1024')
    
    transformed['key_point_value'] = KEY_POINT_MAP.get(article_data.get('key_point_value', 'No'), 'No')
    transformed['machine_written_value'] = MACHINE_WRITTEN_MAP.get(article_data.get('machine_written_value', 'Yes'), 'Yes')
    transformed['ballot_box_value'] = BALLOT_BOX_MAP.get(article_data.get('ballot_box_value', 'No'), 'No')
    
    # Map regional section dropdowns
    africa_section = article_data.get('africa_daily_section_value', '- None -')
    transformed['africa_daily_section_value'] = AFRICA_DAILY_SECTION_MAP.get(africa_section, '_none')
    
    se_europe_section = article_data.get('southeast_europe_today_sections_value', '- None -')
    transformed['southeast_europe_today_sections_value'] = SOUTHEAST_EUROPE_SECTIONS_MAP.get(se_europe_section, '_none')
    
    cee_section = article_data.get('cee_news_watch_country_sections_value', '- None -')
    transformed['cee_news_watch_country_sections_value'] = CEE_NEWS_WATCH_MAP.get(cee_section, '_none')
    
    n_africa_section = article_data.get('n_africa_today_section_value', '- None -')
    transformed['n_africa_today_section_value'] = N_AFRICA_TODAY_MAP.get(n_africa_section, '_none')
    
    me_section = article_data.get('middle_east_today_section_value', '- None -')
    transformed['middle_east_today_section_value'] = MIDDLE_EAST_TODAY_MAP.get(me_section, '_none')
    
    baltic_section = article_data.get('baltic_states_today_sections_value', '- None -')
    transformed['baltic_states_today_sections_value'] = BALTIC_STATES_TODAY_MAP.get(baltic_section, '_none')
    
    asia_section = article_data.get('asia_today_sections_value', '- None -')
    transformed['asia_today_sections_value'] = ASIA_TODAY_SECTIONS_MAP.get(asia_section, '_none')
    
    latam_section = article_data.get('latam_today_value', '- None -')
    transformed['latam_today_value'] = LATAM_TODAY_MAP.get(latam_section, '_none')
    
    log.info("✅ Article data transformation complete")
    return transformed

def select_dropdown_option(driver, element_id, value_to_select, log, element_name):
    """
    Selects an option from a dropdown menu by its value using JavaScript.
    """
    if not value_to_select or value_to_select == '_none':
        log.info(f"   - Skipping {element_name} (no value or 'None')")
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
            log.info(f"   - ✅ Selected value '{value_to_select}' for {element_name}")
        else:
            log.warning(f"   - ⚠️ Dropdown '{element_name}' (ID: {element_id}) not found")
    except Exception as e:
        log.error(f"   - 🔥 Could not select '{value_to_select}' for {element_name}: {e}")

def post_article_to_cms(article_json: str, username: str, password: str, login_url: str, create_article_url: str, logger) -> str:
    """
    Logs into the CMS, creates a new article, fills in the fields based on the JSON data, and saves it.
    """
    log = logger
    log.info("=" * 70)
    log.info("STARTING CMS POSTING PROCESS")
    log.info("=" * 70)

    close_delay_seconds = 30
    close_delay_override = os.getenv("CMS_POSTER_CLOSE_DELAY_SECONDS")
    if close_delay_override is not None:
        try:
            close_delay_seconds = max(0, int(close_delay_override))
        except ValueError:
            log.warning(
                "CMS_POSTER_CLOSE_DELAY_SECONDS must be an integer number of seconds; defaulting to 30."
            )
            close_delay_seconds = 30

    # Parse and transform article data
    try:
        raw_article_data = json.loads(article_json)
        log.info("✅ Successfully parsed article JSON")
        
        # Transform data to CMS-compatible format
        article_data = transform_article_data(raw_article_data, log)
        
        # Validate required fields
        if not article_data.get('title_value'):
            log.error("🔥 CRITICAL: Title is missing!")
            return "Error: Title field is required"
        if not article_data.get('body_value'):
            log.error("🔥 CRITICAL: Body is missing!")
            return "Error: Body field is required"
        if not article_data.get('country_id_selections'):
            log.error("🔥 CRITICAL: No countries selected!")
            return "Error: At least one country is required"
        if not article_data.get('publication_id_selections'):
            log.error("🔥 CRITICAL: No publications selected!")
            return "Error: At least one publication is required"
        
        log.info("✅ All required fields present")
        
    except json.JSONDecodeError as e:
        log.error(f"🔥 Error decoding JSON: {e}")
        return f"Error: Invalid JSON format. {e}"

    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    if os.environ.get('RENDER') == 'true':
        log.info("Render environment detected - running headless")
        chrome_options.add_argument("--headless")
    else:
        log.info("Local environment detected - showing browser")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        # Login
        log.info(f"\n[1/3] Logging in to {login_url}...")
        driver.get(login_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-name"))).send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        wait.until(EC.url_to_be("https://cms.intellinews.com/workflow/mycontent"))
        log.info("✅ Login successful")

        # Navigate to create article page
        log.info(f"\n[2/3] Opening article creation page...")
        driver.get(create_article_url)
        wait.until(EC.element_to_be_clickable((By.ID, "edit-submit")))
        time.sleep(2)  # Wait for JavaScript to initialize
        log.info("✅ Page loaded")

        # Fill form
        log.info("\n[3/3] Filling article form...")
        
        # Title (REQUIRED)
        log.info("   - Setting title...")
        driver.find_element(By.ID, "edit-title").send_keys(remove_non_bmp_chars(article_data['title_value']))
        time.sleep(0.3)
        
        # Weekly title
        driver.find_element(By.ID, "edit-field-weekly-title-und-0-value").send_keys(remove_non_bmp_chars(article_data['weekly_title_value']))
        time.sleep(0.3)
        
        # Machine written checkbox
        try:
            driver.execute_script("document.getElementById('edit-field-machine-written-und-yes').click();")
            log.info("   - ✅ Ticked 'Machine Written' checkbox")
        except JavascriptException:
            log.warning("   - ⚠️ Could not tick 'Machine Written' checkbox")
        time.sleep(0.3)
        
        # Sending date
        gmt = pytz.timezone('GMT')
        now_gmt = datetime.now(gmt)
        target_date = now_gmt + timedelta(days=1) if now_gmt.hour >= 7 else now_gmt
        target_date_str = target_date.strftime('%m/%d/%Y')
        driver.execute_script(f"document.getElementById('edit-field-sending-date-und-0-value-datepicker-popup-0').value = '{target_date_str}';")
        log.info(f"   - ✅ Set sending date to {target_date_str}")
        time.sleep(0.3)
        
        # Byline
        driver.find_element(By.ID, "edit-field-bylines-und-0-field-byline-und").send_keys(remove_non_bmp_chars(article_data['byline_value']))
        time.sleep(0.3)
        
        # Callouts
        driver.find_element(By.ID, "edit-field-website-callout-und-0-value").send_keys(remove_non_bmp_chars(article_data['website_callout_value']))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-field-social-media-callout-und-0-value").send_keys(remove_non_bmp_chars(article_data['social_media_callout_value']))
        time.sleep(0.3)

        # Body (REQUIRED)
        log.info("   - Setting body content...")
        body_content = remove_non_bmp_chars(article_data['body_value'])
        escaped_body = json.dumps(body_content)
        driver.execute_script(f"CKEDITOR.instances['edit-body-und-0-value'].setData({escaped_body});")
        log.info("   - ✅ Body content set")
        time.sleep(0.5)

        # Countries (REQUIRED)
        log.info(f"   - Selecting {len(article_data['country_id_selections'])} countries...")
        tick_checkboxes_by_id(driver, article_data['country_id_selections'], log)
        time.sleep(0.3)
        
        # Publications (REQUIRED)
        log.info(f"   - Selecting {len(article_data['publication_id_selections'])} publications...")
        tick_checkboxes_by_id(driver, article_data['publication_id_selections'], log)
        time.sleep(0.3)
        
        # Industries
        if article_data.get('industry_id_selections'):
            log.info(f"   - Selecting {len(article_data['industry_id_selections'])} industries...")
            tick_checkboxes_by_id(driver, article_data['industry_id_selections'], log)
        time.sleep(0.3)

        # Daily Subject (REQUIRED)
        log.info(f"   - Setting Daily Subject to: {article_data['daily_subject_value']}")
        select_dropdown_option(driver, 'edit-field-subject-und', article_data['daily_subject_value'], log, "Daily Publications Subject")
        time.sleep(0.3)
        
        # Other dropdowns
        select_dropdown_option(driver, 'edit-field-ballot-box-und', article_data['ballot_box_value'], log, "Ballot Box")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-key-und', article_data['key_point_value'], log, "Key Point")
        time.sleep(0.3)
        
        # Regional sections
        select_dropdown_option(driver, 'edit-field-africa-daily-section-und', article_data['africa_daily_section_value'], log, "Africa Daily Section")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-southeast-europe-today-sec-und', article_data['southeast_europe_today_sections_value'], log, "Southeast Europe Today")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-cee-middle-east-africa-tod-und', article_data['cee_news_watch_country_sections_value'], log, "CEE News Watch")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-middle-east-n-africa-today-und', article_data['n_africa_today_section_value'], log, "N.Africa Today")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-middle-east-today-section-und', article_data['middle_east_today_section_value'], log, "Middle East Today")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-baltic-states-today-sectio-und', article_data['baltic_states_today_sections_value'], log, "Baltic States Today")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-asia-today-sections-und', article_data['asia_today_sections_value'], log, "Asia Today")
        time.sleep(0.3)
        select_dropdown_option(driver, 'edit-field-latam-today-und', article_data['latam_today_value'], log, "LatAm Today")
        time.sleep(0.3)
        
        # Meta tags
        driver.find_element(By.ID, "edit-metatags-und-abstract-value").send_keys(remove_non_bmp_chars(article_data['abstract_value']))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-metatags-und-keywords-value").send_keys(remove_non_bmp_chars(article_data['seo_keywords_value']))
        time.sleep(0.3)
        driver.find_element(By.ID, "edit-metatags-und-news-keywords-value").send_keys(remove_non_bmp_chars(article_data['google_news_keywords_value']))
        time.sleep(0.3)

        # Save
        log.info("\n💾 Saving article...")
        save_button = driver.find_element(By.ID, "edit-submit")
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        save_button.click()

        # Verify success
        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".messages.status")))
        final_url = driver.current_url
        
        log.info("=" * 70)
        log.info("✅ ARTICLE POSTED SUCCESSFULLY!")
        log.info(f"URL: {final_url}")
        log.info("=" * 70)
        return f"Article posted successfully! URL: {final_url}"

    except TimeoutException:
        log.error("🔥 Timeout waiting for success message")
        try:
            error_message = driver.find_element(By.CSS_SELECTOR, ".messages.error")
            log.error(f"CMS Error: {error_message.text}")
            return f"Error: {error_message.text}"
        except NoSuchElementException:
            return "Error: Posting failed - timeout"
    except Exception as e:
        log.critical(f"🔥 Unexpected error: {e}", exc_info=True)
        return f"Error: {e}"
    finally:
        if close_delay_seconds > 0:
            log.info(
                f"Waiting {close_delay_seconds} second{'s' if close_delay_seconds != 1 else ''} before closing the browser..."
            )
            time.sleep(close_delay_seconds)


        driver.quit()
        log.info("Browser closed")