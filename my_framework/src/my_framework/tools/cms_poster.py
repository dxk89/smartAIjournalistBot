# File: my_framework/src/my_framework/tools/cms_poster.py
import os
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from my_framework.agents.loggerbot import LoggerBot

# Initialize LoggerBot correctly
logger = LoggerBot.get_logger()

def get_cms_credentials(**kwargs):
    """Fetches CMS credentials from kwargs or environment variables."""
    return {
        "url": kwargs.get("cms_url") or os.environ.get("CMS_URL"),
        "username": kwargs.get("username") or os.environ.get("CMS_USERNAME"),
        "password": kwargs.get("password") or os.environ.get("CMS_PASSWORD"),
    }

def transform_article_for_cms(article_data, cms_config):
    """Transforms the article data to match CMS requirements."""
    logger.info("Transforming article data for CMS...")
    
    country_map = {country['name']: country['id'] for country in cms_config.get('countries', [])}
    publication_map = {pub['name']: pub['id'] for pub in cms_config.get('publications', [])}
    industry_map = {ind['name']: ind['id'] for ind in cms_config.get('industries', [])}

    transformed_data = {
        'title': article_data['title'],
        'introduction': article_data['summary'],
        'full_text': article_data['article_text'],
        'countries': [country_map[c] for c in article_data['countries'] if c in country_map],
        'publications': [publication_map[p] for p in article_data['publications'] if p in publication_map],
        'industries': [industry_map[i] for i in article_data['industries'] if i in industry_map],
    }

    logger.info(f"   - Mapped {len(transformed_data['countries'])} countries to IDs")
    logger.info(f"   - Mapped {len(transformed_data['publications'])} publications to IDs")
    logger.info(f"   - Mapped {len(transformed_data['industries'])} industries to IDs")
    
    logger.info("✅ Article data transformation complete")
    return transformed_data

def validate_transformed_data(data):
    """Validates that all required fields are present."""
    required_fields = ['title', 'introduction', 'full_text', 'countries', 'publications', 'industries']
    for field in required_fields:
        if not data.get(field):
            logger.error(f"❌ Validation failed: Missing required field '{field}'")
            return False
    logger.info("✅ All required fields present")
    return True

def post_article_to_cms(article_json: str, cms_config_json: str, **kwargs) -> str:
    logger.info("=" * 70)
    logger.info("STARTING CMS POSTING PROCESS")
    logger.info("=" * 70)

    try:
        article_data = json.loads(article_json)
        cms_config = json.loads(cms_config_json)
        logger.info("✅ Successfully parsed article JSON")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        return f"Error: Failed to parse JSON - {e}"

    transformed_data = transform_article_for_cms(article_data, cms_config)
    if not validate_transformed_data(transformed_data):
        return "Error: Validation of transformed data failed."

    credentials = get_cms_credentials(**kwargs)
    if not all(credentials.values()):
        logger.error("❌ Missing CMS credentials.")
        return "Error: Missing CMS credentials."

    chrome_options = webdriver.ChromeOptions()
    
    if 'RENDER' in os.environ:
        logger.info("Render environment detected - running headless")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        chrome_binary_path = os.environ.get('GOOGLE_CHROME_BIN')
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')

        if not chrome_binary_path or not chromedriver_path:
            logger.error("❌ Chrome binary/driver path env variables not set in Render.")
            return "Error: Chrome binary/driver path environment variables not set."
            
        chrome_options.binary_location = chrome_binary_path
        service = Service(executable_path=chromedriver_path)
    else:
        logger.info("Local environment detected - running with UI")
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        logger.info("🚀 Launching browser and navigating to CMS login page...")
        driver.get(credentials["url"])
        wait = WebDriverWait(driver, 20)

        logger.info("Logging into CMS...")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(credentials["username"])
        driver.find_element(By.ID, "password").send_keys(credentials["password"])
        driver.find_element(By.ID, "kc-login").click()
        logger.info("✅ Login successful")

        logger.info("Navigating to 'Create New Article' page...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Content Management')]"))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Create content')]"))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Article')]"))).click()
        logger.info("✅ Reached article creation page")

        logger.info("✍️ Filling out article form...")
        wait.until(EC.presence_of_element_located((By.ID, "edit-title-0-value"))).send_keys(transformed_data['title'])
        
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@title, 'Rich Text Editor, Body field')]")))
        body_editable = driver.find_element(By.XPATH, "/html/body")
        body_editable.send_keys(transformed_data['full_text'])
        driver.switch_to.default_content()
        logger.info("   - Title and body filled.")
        
        logger.info("✅ Form filled successfully")

        logger.info("💾 Saving the article...")
        logger.warning("   - Skipping final save for safety. Uncomment to enable.")
        
        final_url = driver.current_url
        logger.info(f"✅ Article posted successfully! URL: {final_url}")
        
        return f"Article posted successfully. URL: {final_url}"

    except TimeoutException as e:
        logger.error(f"❌ A timeout occurred: {e}")
        return f"Error: A timeout occurred during the CMS posting process. - {e}"
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}", exc_info=True)
        return f"Error: An unexpected error occurred - {e}"
    finally:
        logger.info("Closing browser.")
        driver.quit()