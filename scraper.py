import os
import re
import logging
from datetime import datetime, timezone, timedelta 
import asyncio
import time
import subprocess
import shutil
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException

# --- Custom Exception for Path Errors ---
class BrowserPathError(Exception):
    """Custom exception for when Chrome or ChromeDriver paths are not found."""
    pass

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TIKTOK_SESSION_DATA_DIR = os.path.join(SCRIPT_DIR, "tiktok_session_data")
TIKTOK_BROWSER_USER_DATA_DIR = os.path.join(SCRIPT_DIR, "tiktok_browser_user_data")

os.makedirs(TIKTOK_SESSION_DATA_DIR, exist_ok=True)
os.makedirs(TIKTOK_BROWSER_USER_DATA_DIR, exist_ok=True)

# Global variables for Chrome binary and ChromeDriver executable paths
CHROME_BINARY_LOCATION = None
CHROMEDRIVER_EXECUTABLE_PATH = None


# Function to get Chrome and ChromeDriver versions by auto-detection with robust fallbacks
def get_browser_and_driver_versions():
    global CHROME_BINARY_LOCATION, CHROMEDRIVER_EXECUTABLE_PATH
    
    chrome_version = "N/A"
    driver_version = "N/A"

    # --- Auto-detect Chrome Binary Location ---
    logging.info("Attempting to auto-detect Chrome binary location using multiple strategies...")
    
    portable_chrome_path = os.path.join(SCRIPT_DIR, "chrome-win64", "chrome.exe")
    if os.path.exists(portable_chrome_path):
        CHROME_BINARY_LOCATION = portable_chrome_path
        logging.info(f"Found Chrome binary at portable path: {CHROME_BINARY_LOCATION}")
    
    if not CHROME_BINARY_LOCATION:
        if sys.platform.startswith('win'):
            candidate_paths = [
                os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "Application", "chrome.exe")
            ]
            for path in candidate_paths:
                if os.path.exists(path):
                    CHROME_BINARY_LOCATION = path
                    logging.info(f"Found Chrome binary at standard Windows installation path: {CHROME_BINARY_LOCATION}")
                    break
        elif sys.platform.startswith('darwin'):
            candidate_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            ]
            for path in candidate_paths:
                if os.path.exists(path):
                    CHROME_BINARY_LOCATION = path
                    logging.info(f"Found Chrome binary at standard macOS installation path: {CHROME_BINARY_LOCATION}")
                    break
        elif sys.platform.startswith('linux'):
            if shutil.which("google-chrome"):
                CHROME_BINARY_LOCATION = shutil.which("google-chrome")
                logging.info(f"Found Chrome binary via 'google-chrome' in PATH: {CHROME_BINARY_LOCATION}")
            elif shutil.which("chrome"):
                CHROME_BINARY_LOCATION = shutil.which("chrome")
                logging.info(f"Found Chrome binary via 'chrome' in PATH: {CHROME_BINARY_LOCATION}")

    if not CHROME_BINARY_LOCATION:
        logging.error("CRITICAL: Chrome binary (chrome.exe or Google Chrome.app) NOT FOUND after all auto-detection attempts.")
        logging.error("Please ensure Google Chrome browser is installed in a standard location, or ensure your 'chrome-win64' folder is correctly placed next to your script.")
    else:
        logging.info(f"Chrome binary confirmed to exist at: {CHROME_BINARY_LOCATION}")


    # --- Auto-detect ChromeDriver Executable Path ---
    logging.info("Attempting to auto-detect ChromeDriver executable location using multiple strategies...")
    
    portable_chromedriver_path = os.path.join(SCRIPT_DIR, "chromedriver-win64", "chromedriver.exe")
    if os.path.exists(portable_chromedriver_path):
        CHROMEDRIVER_EXECUTABLE_PATH = portable_chromedriver_path
        logging.info(f"Found ChromeDriver executable at portable path: {portable_chromedriver_path}")
    
    if not CHROMEDRIVER_EXECUTABLE_PATH:
        # Fallback to webdriver_manager if not found locally or in PATH
        try:
            logging.info("Attempting to install/use ChromeDriver via webdriver_manager...")
            CHROMEDRIVER_EXECUTABLE_PATH = ChromeDriverManager().install()
            logging.info(f"ChromeDriver installed/found by webdriver_manager: {CHROMEDRIVER_EXECUTABLE_PATH}")
        except Exception as e:
            logging.error(f"Failed to install/find ChromeDriver via webdriver_manager: {e}", exc_info=True)
            logging.error("CRITICAL: ChromeDriver executable NOT FOUND after all auto-detection attempts.")
            logging.error("Please ensure chromedriver is installed (e.g., via npm, brew, or manual download) and its directory is added to your system's PATH environmental variable, or it's placed correctly in 'chromedriver-win64' next to your script.")

    if CHROMEDRIVER_EXECUTABLE_PATH and os.path.exists(CHROMEDRIVER_EXECUTABLE_PATH):
        try:
            if sys.platform.startswith('win'):
                result = subprocess.run([CHROMEDRIVER_EXECUTABLE_PATH, "--version"], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run([CHROMEDRIVER_EXECUTABLE_PATH, "--version"], capture_output=True, text=True, check=True)
            match = re.search(r'ChromeDriver ([\d.]+)', result.stdout)
            if match:
                driver_version = match.group(1)
            logging.info(f"Detected ChromeDriver Version: {driver_version} from {CHROMEDRIVER_EXECUTABLE_PATH}")
        except Exception as e:
            logging.warning(f"Could not retrieve ChromeDriver version from '{CHROMEDRIVER_EXECUTABLE_PATH}': {e}", exc_info=True)
    else:
        logging.error("ChromeDriver executable path is still not set or accessible after all attempts.")
    
    logging.info(f"Final Summary: Chrome Binary Path: {CHROME_BINARY_LOCATION if CHROME_BINARY_LOCATION else 'NOT FOUND'}")
    logging.info(f"Final Summary: ChromeDriver Path: {CHROMEDRIVER_EXECUTABLE_PATH if CHROMEDRIVER_EXECUTABLE_PATH else 'NOT FOUND'}")
    

get_browser_and_driver_versions()


HEADERS = {
    "User-Agent": (
        "Mozilla/50 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/94.0.4606.81 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 15


# ------------------
# Helper Functions
# ------------------

def get_tiktok_video_id_from_url(url: str) -> str or None:
    """Extracts a TikTok video ID from a URL."""
    if not isinstance(url, str):
        return None
    match = re.search(r'(?:tiktok\.com/@[\w.]+/video/|vm\.tiktok\.com/|tiktok\.com/t/)([0-9]+)', url)
    if match:
        return match.group(1)
    
    if re.fullmatch(r"[0-9]+", url):
        return url
        
    return None

def get_username_from_tiktok_url(url: str) -> str or None:
    """Extracts the username from a TikTok post or profile URL."""
    if not isinstance(url, str):
        return None
    # Matches patterns like tiktok.com/@username/video/ or tiktok.com/@username
    match = re.search(r'tiktok\.com/@([^/?#&]+)', url)
    if match:
        return match.group(1).strip()
    return None


def calculate_engagement_rate_post(likes, comments, views, shares, saves):
    """Calculates engagement rate for TikTok posts."""
    likes = int(likes) if isinstance(likes, (int, str)) and str(likes).isdigit() else 0
    comments = int(comments) if isinstance(comments, (int, str)) and str(comments).isdigit() else 0
    shares = int(shares) if isinstance(shares, (int, str)) and str(shares).isdigit() else 0
    saves = int(saves) if isinstance(saves, (int, str)) and str(saves).isdigit() else 0

    total_interactions = likes + comments + shares + saves 

    views = int(views) if isinstance(views, (int, str)) and str(views).isdigit() else 0

    if views == 0:
        return "N/A"
    er = (total_interactions / views) * 100
    return round(er, 2)

def parse_count_text(count_text):
    """Converts abbreviated counts (e.g., '10.5K') to integers."""
    if not isinstance(count_text, str):
        return None
    text = count_text.lower().replace(",", "").strip()
    multiplier = 1
    if 'k' in text:
        multiplier = 1_000
        text = text.replace('k', '')
    elif 'm' in text:
        multiplier = 1_000_000
        text = text.replace('m', '')
    elif 'b' in text:
        multiplier = 1_000_000_000
        text = text.replace('b', '')
    try:
        return int(float(text) * multiplier)
    except ValueError:
        logging.warning(f"Could not parse count from '{count_text}'")
        return None

def parse_relative_time(relative_time_str):
    """
    Parses a relative time string (e.g., "3d ago", "2w ago", "1m ago", "1y ago")
    or an absolute date (e.g., "2023-01-15", "1-15") into a datetime object.
    """
    now = datetime.now(timezone.utc)
    relative_time_str = relative_time_str.lower().strip()

    if "just now" in relative_time_str or "now" in relative_time_str:
        return now
    elif "m" in relative_time_str and "ago" in relative_time_str and "mo" not in relative_time_str: # Avoid confusion with "mo" for months
        try:
            minutes = int(re.search(r'(\d+)\s*m', relative_time_str).group(1))
            return now - timedelta(minutes=minutes)
        except (AttributeError, ValueError):
            pass
    elif "h" in relative_time_str and "ago" in relative_time_str:
        try:
            hours = int(re.search(r'(\d+)\s*h', relative_time_str).group(1))
            return now - timedelta(hours=hours)
        except (AttributeError, ValueError):
            pass
    elif "d" in relative_time_str and "ago" in relative_time_str:
        try:
            days = int(re.search(r'(\d+)\s*d', relative_time_str).group(1))
            return now - timedelta(days=days)
        except (AttributeError, ValueError):
            pass
    elif "w" in relative_time_str and "ago" in relative_time_str:
        try:
            weeks = int(re.search(r'(\d+)\s*w', relative_time_str).group(1))
            return now - timedelta(weeks=weeks)
        except (AttributeError, ValueError):
            pass
    elif "mo" in relative_time_str and "ago" in relative_time_str: # for "months"
        try:
            months = int(re.search(r'(\d+)\s*mo', relative_time_str).group(1))
            return now - timedelta(days=months * 30.44) # Approximate average days in a month
        except (AttributeError, ValueError):
            pass
    elif "y" in relative_time_str and "ago" in relative_time_str:
        try:
            years = int(re.search(r'(\d+)\s*y', relative_time_str).group(1))
            return now - timedelta(days=years * 365.25) # Approximate for leap years
        except (AttributeError, ValueError):
            pass
    
    # Handle absolute date formats like "YYYY-MM-DD" or "MM-DD"
    try:
        # Full揮-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", relative_time_str):
            return datetime.strptime(relative_time_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        # MM-DD (assume current year)
        elif re.match(r"^\d{1,2}-\d{1,2}$", relative_time_str):
            month, day = map(int, relative_time_str.split('-'))
            return datetime(now.year, month, day).replace(tzinfo=timezone.utc)
    except ValueError:
        pass # Not a parsable absolute date

    return None # Could not parse the relative time string


# ------------------------------
# Selenium Driver Management
# ------------------------------

def _initialize_driver():
    """Initializes and returns a Selenium WebDriver instance."""
    options = Options()
    # options.add_argument("--headless=new") # Keep browser visible for now
    options.add_argument("--window-size=1280,800")
    options.add_argument(f"user-data-dir={TIKTOK_BROWSER_USER_DATA_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-gpu")
    options.add_argument("--mute-audio")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    if CHROME_BINARY_LOCATION:
        options.binary_location = CHROME_BINARY_LOCATION
    else:
        logging.error("Selenium: CHROME_BINARY_LOCATION is not found. Please verify Chrome installation.")
        raise BrowserPathError("Chrome binary not found.")

    if CHROMEDRIVER_EXECUTABLE_PATH is None or not os.path.exists(CHROMEDRIVER_EXECUTABLE_PATH):
        logging.error(f"Selenium: ChromeDriver executable NOT FOUND or not accessible at {CHROMEDRIVER_EXECUTABLE_PATH}.")
        raise BrowserPathError(f"ChromeDriver not found at {CHROMEDRIVER_EXECUTABLE_PATH}")

    try:
        service = Service(executable_path=CHROMEDRIVER_EXECUTABLE_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});")
        driver.execute_script("Object.defineProperty(navigator, 'chrome', { get: () => ({ runtime: {}, loadTimes: () => {}, csi: () => {}, app: {} }) });")
        driver.set_page_load_timeout(60)
        return driver
    except WebDriverException as e:
        logging.critical(f"Selenium: Driver initialization failed: {e}", exc_info=True)
        raise e
    except Exception as e:
        logging.critical(f"Selenium: Unexpected error during driver initialization: {e}", exc_info=True)
        raise e

def _close_driver(driver):
    """Closes the Selenium WebDriver instance."""
    if driver:
        try:
            # Attempt to close any open modal before quitting
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, 'div[data-e2e="feed-video-detail-close"]')
                if close_button.is_displayed():
                    driver.execute_script("arguments[0].click();", close_button)
                    logging.info("Selenium: Closed video detail modal before quitting.")
                    time.sleep(1) # Give time to close
            except (NoSuchElementException, TimeoutException):
                pass 
            except Exception as e:
                logging.warning(f"Selenium: Error attempting to close modal before quitting: {e}", exc_info=True)

            time.sleep(1) # Short delay before quitting
            driver.quit()
            logging.debug("Selenium: Browser closed.")
        except Exception as e:
            logging.debug(f"Selenium: Error closing driver: {e}")

def _handle_popups(driver):
    """Attempts to dismiss common TikTok pop-ups."""
    pop_up_selectors = [
        (By.XPATH, "//button[contains(., 'Not now')]"), 
        (By.XPATH, "//button[contains(., 'Accept all cookies')]"),
        (By.CSS_SELECTOR, 'div[data-e2e="sign-up-modal-close-button"]'), 
        (By.CSS_SELECTOR, 'div[role="dialog"] button[class*="StyledButton"], div[role="dialog"] div[class*="ModalCloseIcon"]'),
        (By.CSS_SELECTOR, 'div[tabindex="-1"][role="dialog"]'), 
        (By.CSS_SELECTOR, 'button[id*="dialog-close"]') 
    ]
    for by_strategy, selector in pop_up_selectors:
        try:
            # Use a short wait for pop-ups as they might not always appear
            popup_elem = WebDriverWait(driver, 3).until(EC.presence_of_element_located((by_strategy, selector)))
            if popup_elem.is_displayed() and popup_elem.is_enabled():
                driver.execute_script("arguments[0].click();", popup_elem)
                logging.info(f"Selenium: Dismissed pop-up using selector: {selector}.")
                time.sleep(1) 
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException):
            pass
        except Exception as e:
            logging.warning(f"Selenium: Error dismissing pop-up with {selector}: {e}", exc_info=True)

def _is_captcha_present(driver):
    """Checks if a CAPTCHA challenge is currently displayed."""
    captcha_selectors = [
        (By.CSS_SELECTOR, 'div.captcha_verify_container'),
        (By.XPATH, "//*[contains(text(), 'Drag the slider to fit the puzzle')]"),
        (By.XPATH, "//*[contains(@class, 'verify-bar-tip') or contains(@class, 'verify-image-wrapper')]")
    ]
    for by_strategy, selector in captcha_selectors:
        try:
            # Use a very short wait to check for CAPTCHA to avoid delaying normal flow too much
            captcha_elem = WebDriverWait(driver, 2).until(EC.presence_of_element_located((by_strategy, selector)))
            if captcha_elem.is_displayed():
                return True
        except (TimeoutException, NoSuchElementException):
            continue # CAPTCHA element not found, try next selector
        except Exception as e:
            logging.warning(f"Selenium: Error checking for CAPTCHA with selector {selector}: {e}", exc_info=True)
    return False

# ------------------------------
# Core Scraping Logic (from a loaded page)
# ------------------------------

def _scrape_data_from_loaded_page(driver, video_id, data):
    """
    Extracts data from the currently loaded TikTok post page or modal using Selenium.
    Updates the provided 'data' dictionary.
    """
    logging.info(f"Selenium: Scraping data from loaded page for video {video_id}.")

    # --- Pause the video ---
    try:
        # Find the video element within the player, typically a <video> tag
        video_player_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, 'video'))
        )
        driver.execute_script("arguments[0].pause();", video_player_element)
        logging.info("Selenium: Video paused successfully.")
        time.sleep(1) # Give a moment for the UI to settle after pausing
    except (TimeoutException, NoSuchElementException):
        logging.warning("Selenium: Video element not found on post page. Cannot pause video.")
    except Exception as e:
        logging.error(f"Selenium: Error pausing video: {e}", exc_info=True)


    # --- Primary Data Extraction: From SIGI_STATE JSON ---
    sigi_state_found = False
    try:
        sigi_state_script = WebDriverWait(driver, 10).until( # Shorter wait as page should be loaded
            EC.presence_of_element_located((By.ID, "SIGI_STATE"))
        )
        sigi_state_json_str = driver.execute_script("return arguments[0].innerHTML;", sigi_state_script)
        sigi_state_data = json.loads(sigi_state_json_str)
        
        item_module = sigi_state_data.get("ItemModule", {})
        post_data_from_sigi = item_module.get(video_id, {})

        if post_data_from_sigi:
            stats = post_data_from_sigi.get("stats", {})
            author = post_data_from_sigi.get("author", {})

            data["likes"] = stats.get("diggCount", data["likes"])
            data["comments"] = stats.get("commentCount", data["comments"])
            data["shares"] = stats.get("shareCount", data["shares"])
            data["saves"] = stats.get("collectCount", data["saves"]) 
            data["views"] = stats.get("playCount", data["views"])
            data["owner"] = author.get("uniqueId", data["owner"])
            
            if "createTime" in post_data_from_sigi:
                try:
                    dt = datetime.fromtimestamp(int(post_data_from_sigi['createTime']), timezone.utc)
                    data["post_date"] = dt.strftime("%Y-%m-%d %H:%M:%S (UTC)")
                except (ValueError, TypeError):
                    pass

            logging.info(f"Selenium: Successfully extracted metrics from SIGI_STATE: {data}")
            sigi_state_found = True
        else:
            logging.warning(f"Selenium: Video ID {video_id} not found in SIGI_STATE ItemModule on loaded page.")
            # Fallback within SIGI_STATE (if primary key fails)
            first_item_key = next(iter(item_module), None)
            if first_item_key:
                post_data_from_sigi = item_module.get(first_item_key, {})
                if post_data_from_sigi and str(post_data_from_sigi.get('id')) == video_id:
                    stats = post_data_from_sigi.get("stats", {})
                    author = post_data_from_sigi.get("author", {})
                    data["likes"] = stats.get("diggCount", data["likes"])
                    data["comments"] = stats.get("commentCount", data["comments"])
                    data["shares"] = stats.get("shareCount", data["shares"])
                    data["saves"] = stats.get("collectCount", data["saves"])
                    data["views"] = stats.get("playCount", data["views"])
                    data["owner"] = author.get("uniqueId", data["owner"])
                    if "createTime" in post_data_from_sigi:
                        try:
                            dt = datetime.fromtimestamp(int(post_data_from_sigi['createTime']), timezone.utc)
                            data["post_date"] = dt.strftime("%Y-%m-%d %H:%M:%S (UTC)")
                        except (ValueError, TypeError):
                            pass
                    logging.info(f"Selenium: Extracted metrics from SIGI_STATE (fallback key) on loaded page: {data}")
                    sigi_state_found = True
        
    except (TimeoutException, NoSuchElementException):
        logging.warning("Selenium: SIGI_STATE script tag not found on loaded page.")
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logging.error(f"Selenium: Error parsing SIGI_STATE JSON from script element on loaded page: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Selenium: Unexpected error during SIGI_STATE extraction on loaded page for {video_id}: {e}", exc_info=True)
    

    # --- Fallback to Element Scraping if SIGI_STATE failed or incomplete ---
    if not sigi_state_found or any(data[key] == "N/A" for key in ["likes", "comments", "shares", "saves", "views", "owner", "post_date"]):
        logging.warning("Selenium: SIGI_STATE data incomplete or failed. Attempting element scraping.")
        
        # Owner from element if still N/A
        if data["owner"] == "N/A":
            try:
                owner_elem_xpath = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[1]/div/a[2]/span[1]"))
                )
                data["owner"] = owner_elem_xpath.text.strip().replace('@', '')
                logging.info(f"Selenium: Extracted owner (XPath fallback): {data['owner']}")
            except (TimeoutException, NoSuchElementException):
                pass
            except Exception as e:
                logging.warning(f"Selenium: Error getting owner from element (XPath fallback): {e}", exc_info=True)
            
            if data["owner"] == "N/A": # Try data-e2e if XPath fails
                try:
                    # No longer using BeautifulSoup here, directly using Selenium
                    owner_elem_e2e = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-e2e="video-author-uniqueid"]'))
                    )
                    data["owner"] = owner_elem_e2e.text.strip().replace('@', '')
                    logging.info(f"Selenium: Extracted owner (data-e2e fallback): {data['owner']}")
                except (TimeoutException, NoSuchElementException):
                    pass
                except Exception as e:
                    logging.warning(f"Selenium: Error getting owner from element (data-e2e fallback): {e}", exc_info=True)


        # Post Date Scrape (from full post page)
        if data["post_date"] == "N/A":
            try:
                # Use the user's provided XPath for the post date on the opened page
                post_date_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@id=\"app\"]/div[2]/div[4]/div/div[2]/div[1]/div/div[1]/div[1]/div[1]/a[2]/span[2]/span[3]"))
                )
                raw_date_text = post_date_elem.text.strip()
                parsed_date = parse_relative_time(raw_date_text)
                if parsed_date:
                    data["post_date"] = parsed_date.strftime("%Y-%m-%d %H:%M:%S (UTC)")
                    logging.info(f"Selenium: Extracted and parsed post_date from opened post page (XPath): {data['post_date']}")
                else:
                    data["post_date"] = raw_date_text
                    logging.warning(f"Selenium: Could not parse post_date '{raw_date_text}' from opened post page (XPath).")
            except (TimeoutException, NoSuchElementException):
                logging.warning("Selenium: Post date element not found on opened post page via XPath.")
            except Exception as e:
                logging.error(f"Selenium: Error scraping post date from opened page: {e}", exc_info=True)

        # Views Scrape (from full post page) - enhanced to find 'video-views' or 'video-play-count'
        if data["views"] == "N/A":
            # Prioritize the data-e2e="video-views" as provided by the user
            try:
                views_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="video-views"]'))
                )
                views_text = views_elem.text.strip()
                parsed_views = parse_count_text(views_text)
                if parsed_views is not None:
                    data["views"] = parsed_views
                    logging.info(f"Selenium: Extracted views ({data['views']}) from opened post page (data-e2e=\"video-views\").")
                else:
                    logging.warning(f"Selenium: Failed to parse views '{views_text}' from opened post page (data-e2e=\"video-views\").")
            except (TimeoutException, NoSuchElementException):
                logging.warning("Selenium: data-e2e=\"video-views\" element not found. Trying data-e2e=\"video-play-count\".")
                # Fallback to data-e2e="video-play-count"
                try:
                    views_elem = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="video-play-count"]'))
                    )
                    views_text = views_elem.text.strip()
                    parsed_views = parse_count_text(views_text)
                    if parsed_views is not None:
                        data["views"] = parsed_views
                        logging.info(f"Selenium: Extracted views ({data['views']}) from opened post page (data-e2e=\"video-play-count\").")
                    else:
                        logging.warning(f"Selenium: Failed to parse views '{views_text}' from opened post page (data-e2e=\"video-play-count\").")
                except (TimeoutException, NoSuchElementException):
                    logging.warning("Selenium: data-e2e=\"video-play-count\" element not found. Trying generic 'views' class names.")
                    # Fallback to general 'views' class names or text
                    # No longer using BeautifulSoup here, directly using Selenium
                    try:
                        views_elem_selenium = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, ".//strong[contains(@class, 'video-count') or contains(@class, 'views-count') or contains(@class, 'post-views')]"))
                        )
                        views_text = views_elem_selenium.text.strip()
                        parsed_views = parse_count_text(views_text)
                        if parsed_views is not None:
                            data["views"] = parsed_views
                            logging.info(f"Selenium: Extracted views ({data['views']}) from opened post page (class-based fallback).")
                        else:
                            logging.warning(f"Selenium: Failed to parse views '{views_text}' from opened post page (class-based fallback).")
                    except (TimeoutException, NoSuchElementException):
                        logging.warning("Selenium: Views count element not found on opened post page via any CSS/class method.")
            except Exception as e:
                logging.error(f"Selenium: Error scraping views from opened page: {e}", exc_info=True)


        # Metric Fallbacks (likes, comments, shares, saves)
        metric_locators_e2e = {
            "likes": 'strong[data-e2e="like-count"]',
            "comments": 'strong[data-e2e="comment-count"]',
            "shares": 'strong[data-e2e="share-count"]',
            "saves": 'strong[data-e2e="undefined-count"]', # Updated to data-e2e="undefined-count"
        }
        for metric_name, css_selector in metric_locators_e2e.items():
            if data[metric_name] == "N/A":
                try:
                    elem = WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
                    )
                    count_str = driver.execute_script("return arguments[0].innerText;", elem).strip()
                    parsed_count = parse_count_text(count_str)
                    if parsed_count is not None:
                        data[metric_name] = parsed_count
                        logging.info(f"Selenium: Extracted {metric_name}={parsed_count} via data-e2e CSS (Fallback).")
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                    pass
                except Exception as e:
                    logging.warning(f"Selenium: Error with {metric_name} data-e2e fallback: {e}", exc_info=True)

        # Removed the proxy logic for 'saves' as we are now specifically targeting its element
        if data["saves"] == "N/A": # Keep this check if saves is still N/A after all attempts
            logging.warning(f"Selenium: Could not find a reliable count for 'saves' for {video_id} after all attempts.")


# ------------------------------
# Main Scrape Function
# ------------------------------

async def scrape_post_data(post_url: str, app_instance=None) -> dict:
    """
    Main function to scrape TikTok post data.
    1. Extracts video ID and owner username.
    2. Attempts direct page scrape.
    3. If direct scrape is insufficient for key metrics, navigates to profile, finds video, clicks, and scrapes again.
    4. Calculates engagement rate.
    """
    data = {
        "url": post_url,
        "link": post_url,
        "video_id": "N/A",
        "owner": "N/A",
        "likes": "N/A",
        "comments": "N/A",
        "shares": "N/A",
        "saves": "N/A",
        "views": "N/A",
        "post_date": "N/A",
        "last_record": None,
        "engagement_rate": "N/A",
        "error": None,
        "is_video": True
    }

    video_id = get_tiktok_video_id_from_url(post_url)
    if not video_id:
        data["error"] = "Invalid URL (no TikTok video ID found)."
        logging.error(f"[scrape_post_data] Invalid URL: {post_url}")
        return data
    data["video_id"] = video_id

    # Pre-extract owner from URL as it's critical for profile navigation fallback
    owner_from_url = get_username_from_tiktok_url(post_url)
    if owner_from_url:
        data["owner"] = owner_from_url
    else:
        # Cannot proceed meaningfully without owner for profile navigation fallback
        data["error"] = "Owner username could not be extracted from URL."
        logging.error(f"[scrape_post_data] Owner username missing for {post_url}.")
        return data

    driver = None
    try:
        driver = _initialize_driver()
        
        # --- Phase 1: Direct Page Scrape Attempt ---
        app_instance.set_status_from_thread(f"Selenium: Attempting direct scrape of {video_id} from post URL...")
        logging.info(f"Selenium: Navigating directly to post URL: {post_url}")
        driver.get(post_url)
        _handle_popups(driver) # Handle pop-ups on the direct post page
        
        # Check for CAPTCHA immediately after loading the page
        if _is_captcha_present(driver):
            data["error"] = "CAPTCHA detected on direct post page. Manual intervention required."
            app_instance.set_status_from_thread(data["error"])
            logging.error(data["error"])
            _close_driver(driver)
            return data

        # Perform initial scrape from this direct page
        _scrape_data_from_loaded_page(driver, video_id, data)

        # Check if critical data is still missing, then proceed to profile navigation fallback
        # Critical data: views, post_date. Owner, likes, comments, shares, saves might also be N/A.
        # We assume owner is populated from URL at this point.
        needs_profile_scrape = (
            data["views"] == "N/A" or
            data["post_date"] == "N/A" or
            data["likes"] == "N/A" or
            data["comments"] == "N/A" or
            data["shares"] == "N/A" or
            data["saves"] == "N/A"
        )
        
        if needs_profile_scrape:
            logging.info(f"Direct scrape incomplete for {video_id}. Falling back to profile navigation and detailed scrape.")
            app_instance.set_status_from_thread(f"Direct scrape insufficient; navigating to {data['owner']}'s profile to find post {video_id}...")

            profile_url = f"https://www.tiktok.com/@{data['owner']}"
            driver.get(profile_url)
            _handle_popups(driver) # Handle pop-ups on the profile page
            time.sleep(3) # Give time for initial profile load

            # Check for CAPTCHA on profile page
            if _is_captcha_present(driver):
                data["error"] = "CAPTCHA detected on profile page. Manual intervention required."
                app_instance.set_status_from_thread(data["error"])
                logging.error(data["error"])
                _close_driver(driver)
                return data

            # --- Find Video on Profile Grid (with robust scrolling and shortcode check) ---
            target_video_found_on_grid = False
            video_element_to_click = None # This will be the <a> tag to click
            
            last_height = -1
            scroll_attempts = 0
            max_scroll_attempts = 50 # Increased for more robust scrolling
            previous_item_count = 0 # Track number of items to detect new loads

            while scroll_attempts < max_scroll_attempts:
                # Wait for at least some video items to be present before proceeding
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-e2e="user-post-item"]'))
                    )
                except TimeoutException:
                    logging.warning(f"Selenium: No video items found on profile for {data['owner']} after initial load/scroll.")
                    # If no items are found at all, break the loop
                    break

                # Find all video items currently loaded
                video_items = driver.find_elements(By.CSS_SELECTOR, 'div[data-e2e="user-post-item"]')
                current_item_count = len(video_items)

                for item in video_items:
                    try:
                        # Find the link within the current item
                        link_element = item.find_element(By.TAG_NAME, 'a')
                        item_url = link_element.get_attribute('href')
                        
                        # Extract the video_id from the item's URL
                        item_video_id = get_tiktok_video_id_from_url(item_url)

                        if item_video_id == video_id:
                            video_element_to_click = link_element # This is the clickable <a> tag
                            target_video_found_on_grid = True
                            logging.info(f"Found video {video_id} link on profile grid (via shortcode match).")
                            
                            # --- Scrape Views and Saves from Profile Grid Thumbnail (BEFORE CLICKING) ---
                            # Views and Saves are typically siblings or children of the content div within 'user-post-item'
                            app_instance.set_status_from_thread(f"Selenium: Scraping views/saves from thumbnail for {video_id}...")
                            try:
                                # Scrape Views
                                grid_views_element = None
                                try:
                                    grid_views_element = item.find_element(By.CSS_SELECTOR, 'strong[data-e2e="video-views"]')
                                    if not grid_views_element: # Fallback to video-play-count if video-views not found
                                        grid_views_element = item.find_element(By.CSS_SELECTOR, 'strong[data-e2e="video-play-count"]')
                                    logging.info("Selenium: Successfully used data-e2e for grid views within item.")
                                except NoSuchElementException:
                                    logging.warning(f"Selenium: data-e2e views not found in grid item for {video_id}. Trying class-based selectors.")
                                    grid_views_element = item.find_element(By.XPATH, ".//strong[contains(@class, 'video-count') or contains(@class, 'video-views') or contains(@class, 'post-views')]")
                                    logging.info("Selenium: Successfully used class-based XPath for grid views within item.")

                                if grid_views_element:
                                    grid_views_text = grid_views_element.text.strip()
                                    parsed_grid_views = parse_count_text(grid_views_text)
                                    if parsed_grid_views is not None:
                                        data["views"] = parsed_grid_views
                                        logging.info(f"Selenium: Successfully scraped views from profile grid thumbnail: {data['views']}")
                                    else:
                                        logging.warning(f"Selenium: Could not parse views from profile grid thumbnail text: '{grid_views_text}' for {video_id}.")
                                else:
                                    logging.warning(f"Selenium: Views element not found in grid item for {video_id} after all attempts.")

                                # Scrape Saves - using data-e2e="undefined-count"
                                grid_saves_element = None
                                try:
                                    grid_saves_element = item.find_element(By.CSS_SELECTOR, 'strong[data-e2e="undefined-count"]')
                                    logging.info("Selenium: Successfully used data-e2e=\"undefined-count\" for grid saves within item.")
                                except NoSuchElementException:
                                    logging.warning(f"Selenium: data-e2e=\"undefined-count\" not found for saves in grid item for {video_id}. This is the primary selector for saves on thumbnails.")
                                    pass # No reliable fallback for saves on thumbnail if this specific data-e2e is missing

                                if grid_saves_element:
                                    grid_saves_text = grid_saves_element.text.strip()
                                    parsed_grid_saves = parse_count_text(grid_saves_text)
                                    if parsed_grid_saves is not None:
                                        data["saves"] = parsed_grid_saves
                                        logging.info(f"Selenium: Successfully scraped saves from profile grid thumbnail: {data['saves']}")
                                    else:
                                        logging.warning(f"Selenium: Could not parse saves from profile grid thumbnail text: '{grid_saves_text}' for {video_id}.")
                                else:
                                    logging.warning(f"Selenium: Saves element not found in grid item for {video_id} after all attempts (using data-e2e='undefined-count').")

                            except Exception as e:
                                logging.error(f"Selenium: Error scraping views/saves from profile grid thumbnail for {video_id}: {e}", exc_info=True)
                            
                            break # Found the video and scraped views/saves, exit inner loop
                    except NoSuchElementException:
                        # This item might not have a direct <a> tag or other expected structure
                        logging.debug("Skipping a video item due to missing link element.")
                        continue
                
                if target_video_found_on_grid:
                    break # Exit outer scrolling loop if video was found

                # If not found yet, scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3) # Wait for content to load
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # Check if scroll height hasn't changed AND no new items are found after some scrolls, assume end
                if new_height == last_height and current_item_count == previous_item_count and scroll_attempts > 5: # Give it a few attempts before concluding no more content
                    logging.info("No new content loaded or no new items found after multiple scrolls. Reached end of profile or content limit.")
                    break 
                
                last_height = new_height
                previous_item_count = current_item_count # Update previous count for next iteration
                scroll_attempts += 1
            
            if not target_video_found_on_grid:
                logging.error(f"Video {video_id} not found on {data['owner']}'s profile after scrolling all content.")
                data["error"] = "Video not found on profile grid for detailed scrape."
                return data # Exit if video can't be found even on profile

            # --- Click the Video to Open Full Post Page ---
            app_instance.set_status_from_thread(f"Selenium: Clicking video {video_id} to open full post page...")
            try:
                driver.execute_script("arguments[0].click();", video_element_to_click)
                time.sleep(5) # Wait for the modal/new page to load
                logging.info(f"Selenium: Successfully clicked video {video_id}.")
            except ElementClickInterceptedException:
                logging.warning("Selenium: Click intercepted, trying JS click.")
                driver.execute_script("arguments[0].click();", video_element_to_click)
                time.sleep(5)
            except Exception as e:
                logging.error(f"Selenium: Error clicking video {video_id}: {e}", exc_info=True)
                data["error"] = f"Selenium Click Error during profile navigation: {e}"
                # If we can't click, we can't get post date from opened page, so return early
                _close_driver(driver)
                return data

            # --- Phase 2: Scrape from the opened post page/modal ---
            # This call will update existing data values (likes, comments, etc.)
            # and specifically aim to get post_date (which is likely visible only here).
            _scrape_data_from_loaded_page(driver, video_id, data)
        else:
            logging.info(f"Direct scrape for {video_id} was sufficient. Skipping profile navigation.")
            app_instance.set_status_from_thread(f"Direct scrape for {video_id} complete. No profile navigation needed.")


        # Final check if any data was actually extracted
        if any(data[key] == "N/A" for key in ["likes", "comments", "shares", "saves", "views", "owner", "post_date"]):
            data["error"] = "Selenium: No metric data extracted. Page structure might have changed or content not loaded due to blocking."
            logging.error(f"Selenium: Failed to extract any metrics for {video_id}. Final data: {data}")
        else:
            logging.info(f"Selenium: Successfully extracted all metrics for {video_id}.")
            data["error"] = None # Clear error if successful

    except BrowserPathError as e:
        data["error"] = f"Browser Configuration Error: {e}"
        logging.critical(data["error"])
    except WebDriverException as e:
        data["error"] = f"Selenium Driver Error: {e}"
        logging.critical(f"Top-level WebDriver Error for {video_id}: {e}", exc_info=True)
    except Exception as e:
        data["error"] = f"Unexpected Error: {e}"
        logging.critical(f"Unexpected top-level error for {video_id}: {e}", exc_info=True)
    finally:
        _close_driver(driver) # Ensure driver is closed in finally block


    # Ensure all values are integers for calculation, default to 0 for N/A
    likes_val = data.get("likes") if isinstance(data.get("likes"), int) else 0
    comments_val = data.get("comments") if isinstance(data.get("comments"), int) else 0
    shares_val = data.get("shares") if isinstance(data.get("shares"), int) else 0
    saves_val = data.get("saves") if isinstance(data.get("saves"), int) else 0
    views_val = data.get("views") if isinstance(data.get("views"), int) else 0 # Use 0 for views too if N/A

    # Calculate engagement rate using the extracted (or default 0) values
    data["engagement_rate"] = calculate_engagement_rate_post(likes_val, comments_val, views_val, shares_val, saves_val)

    now_str_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["last_record"] = now_str_local

    if app_instance:
        if data.get("error"):
            app_instance.set_status_from_thread(f"Scrape for {video_id} completed with errors: {data['error']}")
        else:
            app_instance.set_status_from_thread(f"Scrape complete for {video_id}.")

    logging.info(f"[scrape_post_data] Completed for {video_id}: {data}")
    return data


if __name__ == "__main__":
    """
    Usage (command line):
      python scraper.py <tiktok_video_url_or_id>

    Example:
      python scraper.py https://www.tiktok.com/@tiktok/video/7019777974345678901
      python scraper.py 7019777974345678901
    """
    import sys
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )


    if len(sys.argv) < 2:
        print("Usage: python scraper.py <tiktok_video_url_or_id>")
        sys.exit(1)

    input_val = sys.argv[1]

    class DummyApp:
        def set_status_from_thread(self, msg):
            print(f"[STATUS] {msg}")

    async def main():
        dummy = DummyApp()
        result = await scrape_post_data(input_val, app_instance=dummy)
        print(json.dumps(result, indent=4))

    asyncio.run(main())
