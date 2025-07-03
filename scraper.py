import os
import re
import sys
import json
import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from dateutil.parser import parse as parse_date


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCRIPT_DIR = Path(__file__).parent.absolute()
TIKTOK_SESSION_DATA_DIR = "session_data"
TIKTOK_BROWSER_USER_DATA_DIR = "browser_user_data"
COOKIE_FILE = Path(SCRIPT_DIR) / "tiktok_cookies.json"

__all__ = [
    'TIKTOK_SESSION_DATA_DIR',
    'TIKTOK_BROWSER_USER_DATA_DIR',
    'get_tiktok_video_id_from_url'
]

def sanitize_url(url: str) -> str:
    """Cleans up a URL string by removing extra spaces and stripping."""
    if not isinstance(url, str):
        return ""
    return re.sub(r'\s+@\s+', "@", url).strip()

def get_tiktok_video_id_from_url(url: str) -> str | None:
    """Extracts the video ID from various TikTok URL formats."""
    clean_url = sanitize_url(url)
    match = re.search(r'/video/(\d+)', clean_url)
    if not match:
        match = re.search(r'(?:tiktok\.com/@[\w.]+/video/|vm\.tiktok\.com/|tiktok\.com/t/)(\d+)', clean_url)
    return match.group(1) if match else None

def build_profile_url(username: str) -> str:
    """Constructs a TikTok profile URL from a username."""
    if not username.startswith("@"):
        username = f"@{username}"
    return f"https://www.tiktok.com/{username.replace(' ', '')}"

def parse_count(text: str) -> int | None:
    """Parses a string count (e.g., '10K', '2.5M') into an integer."""
    if not isinstance(text, str):
        return None
    text = text.upper().replace(',', '').strip()
    multiplier = 1
    if text.endswith('K'):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith('M'):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith('B'):
        multiplier = 1_000_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        logging.debug(f"Could not parse count: '{text}'")
        return None

def parse_relative_time(relative_time_str: str) -> datetime | None:
    """Parses relative time strings (e.g., '2 hours ago', '3 days ago') to datetime."""
    now = datetime.now(timezone.utc)
    if "now" in relative_time_str.lower():
        return now
    match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago', relative_time_str, re.IGNORECASE)
    if match:
        num, unit = match.groups()
        num = int(num)
        if "second" in unit:
            return now - timedelta(seconds=num)
        elif "minute" in unit:
            return now - timedelta(minutes=num)
        elif "hour" in unit:
            return now - timedelta(hours=num)
        elif "day" in unit:
            return now - timedelta(days=num)
        elif "week" in unit:
            return now - timedelta(weeks=num)
        elif "month" in unit:
            return now - timedelta(days=num*30)
        elif "year" in unit:
            return now - timedelta(days=num*365)
    return None

async def save_cookies(context):
    """Saves browser cookies to a JSON file."""
    try:
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        logging.info(f"Cookies saved to {COOKIE_FILE}")
    except Exception as e:
        logging.warning(f"Failed to save cookies: {e}")

async def load_cookies(context):
    """Loads browser cookies from a JSON file."""
    if not COOKIE_FILE.exists():
        logging.info("Cookie file not found. Starting with fresh session.")
        return False
    try:
        with open(COOKIE_FILE, 'r') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        logging.info(f"Cookies loaded from {COOKIE_FILE}")
        return True
    except Exception as e:
        logging.warning(f"Failed to load cookies: {e}. Session will start fresh.")
        return False

async def apply_stealth(context):
    """Applies Playwright stealth techniques to avoid bot detection."""
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : navigator.permissions.query(parameters)
        );
    """)
    logging.info("Stealth applied to browser context.")

async def is_captcha_present(page):
    """Checks if a CAPTCHA challenge is present on the page."""
    captcha_selectors = [
        '[data-e2e="captcha-input"]',
        '.tiktok-captcha',
        '#verifyContainer',
        'iframe[src*="captcha"]',
        '.captcha_verify_bar_block',
    ]
    for selector in captcha_selectors:
        try:
            if await page.query_selector(selector):
                logging.warning(f"CAPTCHA detected using selector: {selector}")
                return True
        except PlaywrightTimeoutError:
            pass
        except Exception as e:
            logging.error(f"Error checking for CAPTCHA with selector {selector}: {e}")
            continue
    return False

class GridTimeoutError(Exception):
    """Custom exception for when grid scraping times out."""
    pass

async def scrape_views_and_date_from_grid(page, video_id, max_retries=3):
    """
    Scrapes ONLY video views from the user's profile grid.
    This is used as a fallback if direct scraping from the video page fails.
    Raises GridTimeoutError if all retries time out.
    """
    async def simulate_human_behavior_on_profile():
        """Simulates human-like scrolling and mouse movements on a profile page."""
        await page.mouse.move(random.randint(100, 600), random.randint(100, 400), steps=random.randint(5, 25))
        await asyncio.sleep(random.uniform(0.5, 1.2))
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(200, 600))
            await asyncio.sleep(random.uniform(1.0, 2.0))
        await page.set_viewport_size({
            "width": random.randint(1100, 1500),
            "height": random.randint(700, 900)
        })
        await asyncio.sleep(random.uniform(1.0, 2.0))

    for attempt in range(max_retries):
        try:
            logging.info(f"Grid scrape attempt {attempt+1}/{max_retries} for video ID {video_id}")
            await simulate_human_behavior_on_profile()

            grid_selector = f'a[href*="/video/{video_id}"]'
            await page.wait_for_selector(grid_selector, timeout=25000)
            grid_item = await page.query_selector(grid_selector)

            if not grid_item:
                logging.warning(f"Grid item for video ID {video_id} not found on attempt {attempt+1}. Scrolling and retrying.")
                await page.mouse.wheel(0, random.randint(800, 1500))
                await asyncio.sleep(random.uniform(3, 5))
                continue

            # --- Extract Views ---
            views_elem = await grid_item.query_selector('strong[data-e2e="video-views"]') or \
                         await grid_item.query_selector('strong[data-e2e="video-play-count"]') or \
                         await grid_item.query_selector('.tiktok-grid-item-views')
            views_text = await views_elem.inner_text() if views_elem else None
            views = parse_count(views_text)

            logging.debug(f"DEBUG: Views found in grid scrape attempt {attempt+1}: {views}")

            if views is not None:
                logging.info(f"Extracted via grid: views={views}")
                return views, None # Always return None for date, as it's not scraped here
            else:
                logging.warning(f"Could not extract views from grid on attempt {attempt+1}. Views: {views}. Retrying.")
                await asyncio.sleep(2 ** attempt)
                continue

        except PlaywrightTimeoutError:
            logging.warning(f"Grid scrape timeout (attempt {attempt+1}) for video ID {video_id}.")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise GridTimeoutError(f"Grid scrape timed out after {max_retries} attempts for video ID {video_id}")
        except Exception as e:
            logging.error(f"Grid scrape failed unexpectedly on attempt {attempt+1}: {e}", exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            continue

    logging.error(f"Failed to scrape views from grid after {max_retries} attempts for video ID {video_id}.")
    return None, None # If all retries fail, return None for views and None for date


async def _launch_browser_session(p, headless_mode: bool, url: str):
    """
    Helper function to launch a browser session, apply stealth, load cookies,
    and navigate to a URL. Returns (browser, context, page).
    """
    browser_args = ["--disable-blink-features=AutomationControlled"]

    browser = await p.chromium.launch(headless=headless_mode, args=browser_args)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    await apply_stealth(context)
    await load_cookies(context)
    page = await context.new_page()

    logging.info(f"Navigating to URL: {url} (Headed: {not headless_mode})")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(random.uniform(3, 6))
    
    return browser, context, page


async def scrape_post_data(url: str, app_instance=None):
    """
    Scrapes detailed data for a given TikTok video URL, including views, likes, comments, shares, saves,
    post date, and engagement rate. It handles direct page scraping and falls back to profile grid scraping.
    The app_instance parameter is optional and can be used for UI updates if provided.
    """
    data = {
        "url": url,
        "video_id": None,
        "views": None,
        "likes": None,
        "comments": None,
        "shares": None,
        "saves": None,
        "post_date": None, # post_date will ONLY be set by direct scrape
        "owner": None,
        "engagement_rate": None,
        "error": None
    }
    
    clean_url = sanitize_url(url)
    data["url"] = clean_url

    video_id = get_tiktok_video_id_from_url(clean_url)
    if not video_id:
        data["error"] = "Invalid TikTok video URL format. Could not extract video ID."
        logging.error(data["error"])
        return data
    data["video_id"] = video_id

    owner_match = re.search(r'/@([^/]+)/video/\d+', clean_url)
    if owner_match:
        data["owner"] = owner_match.group(1).replace(' ', '')
    
    logging.info(f"Attempting to scrape data for URL: {clean_url}")
    logging.info(f"Detected Video ID: {video_id}")
    if data["owner"]:
        logging.info(f"Detected Owner from URL: {data['owner']}")

    browser = None
    context = None
    page = None
    p_instance = None

    try:
        p_instance = await async_playwright().start()

        # --- Initial Launch in HEADLESS mode ---
        browser, context, page = await _launch_browser_session(p_instance, headless_mode=True, url=clean_url)

        # --- CAPTCHA Check (and potential headed relaunch) ---
        if await is_captcha_present(page):
            logging.warning("CAPTCHA detected in headless mode. Relaunching in HEADED mode for manual solving.")
            data["error"] = "CAPTCHA detected. Please solve manually in the popped-out browser."
            
            # Close the current headless session
            if context: await context.close()
            if browser: await browser.close()
            
            # Launch new browser in HEADED mode for CAPTCHA
            browser, context, page = await _launch_browser_session(p_instance, headless_mode=False, url=clean_url)

            logging.info("Browser is visible. Please solve any CAPTCHA manually. Script will wait for 120 seconds.")
            if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                 app_instance.set_status("CAPTCHA detected! Please solve in browser. Waiting 120s...")
            await asyncio.sleep(120)
            logging.info("Continuing after CAPTCHA wait...")

            if await is_captcha_present(page):
                data["error"] += " CAPTCHA still present after manual intervention time."
                logging.error(data["error"])
                if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                     app_instance.set_status("CAPTCHA still present. Scraping failed.")
                return data

            logging.info("CAPTCHA appears to be solved. Resuming scraping.")
            if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                 app_instance.set_status("CAPTCHA solved. Resuming scraping.")
        
        # --- Direct scraping logic (after initial launch or after CAPTCHA handling) ---
        
        # Wait for specific elements to ensure page is loaded, or networkidle
        try:
            await page.wait_for_selector('[data-e2e="like-count"]', timeout=20000)
            await page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            logging.warning("Main video page interaction elements did not load quickly. Proceeding with available content.")

        try:
            # Views: More robust selectors for direct scrape
            views_elem = await page.query_selector('strong[data-e2e="feed-video-play-count"]') or \
                         await page.query_selector('strong[data-e2e="video-play-count"]') or \
                         await page.query_selector('.video-details-container .view-count') or \
                         await page.query_selector('span.tiktok-share-counter-text[data-e2e="undefined-count"]')
            if views_elem:
                views_text = await views_elem.inner_text()
                data["views"] = parse_count(views_text)
            logging.info(f"Direct scrape - Views: {data['views']}")


            # Likes
            likes_elem = await page.query_selector('strong[data-e2e="like-count"]')
            data["likes"] = parse_count(await likes_elem.inner_text()) if likes_elem else None
            logging.info(f"Direct scrape - Likes: {data['likes']}")


            # Comments
            comments_elem = await page.query_selector('strong[data-e2e="comment-count"]')
            data["comments"] = parse_count(await comments_elem.inner_text()) if comments_elem else None
            logging.info(f"Direct scrape - Comments: {data['comments']}")


            # Shares
            shares_elem = await page.query_selector('strong[data-e2e="share-count"]')
            data["shares"] = parse_count(await shares_elem.inner_text()) if shares_elem else None
            logging.info(f"Direct scrape - Shares: {data['shares']}")


            # Saves
            saves_elem = await page.query_selector('strong[data-e2e="undefined-count"]') or \
                         await page.query_selector('strong[data-e2e="collect-count"]') or \
                         await page.query_selector('strong[data-e2e="favourite-count"]')
            data["saves"] = parse_count(await saves_elem.inner_text()) if saves_elem else None
            logging.info(f"Direct scrape - Saves: {data['saves']}")

            # Post Date: ONLY direct page elements (removed og:video:release_date)
            post_date_found_direct_scrape = False
            logging.info("Attempting to get post date from direct page elements (excluding meta tag).")
            # Combined selectors for post date as per your provided script and previous discussions
            date_span_elem = await page.query_selector('p[data-e2e="video-desc"] + div span:last-child') or \
                             await page.query_selector('span.video-info-source-text-date') or \
                             await page.query_selector('span.tiktok-video-publish-date') or \
                             await page.query_selector('span.tiktok-share-desc-text span:last-child') or \
                             await page.query_selector('xpath=/html/body/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[1]/div/a[2]/span[2]/span[3]')
            
            if date_span_elem:
                raw_text = await date_span_elem.inner_text()
                raw_text = raw_text.strip()
                post_date_dt = None
                try:
                    # Attempt to parse as a full date first (e.g., "2023-03-18")
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_text):
                        post_date_dt = parse_date(raw_text)
                    # Then try relative dates (e.g., "2 hours ago")
                    elif 'ago' in raw_text.lower():
                        post_date_dt = parse_relative_time(raw_text)
                    # Then try month-day format (e.g., "3-18")
                    elif re.match(r'^\d{1,2}-\d{1,2}$', raw_text):
                        year = datetime.now().year
                        post_date_dt = parse_date(f"{year}-{raw_text}", fuzzy=True)
                    else: # Fallback to general parsing
                        post_date_dt = parse_date(raw_text, fuzzy=True)
                    
                    if post_date_dt:
                        data["post_date"] = post_date_dt.strftime('%Y-%m-%d %H:%M:%S (UTC)')
                        logging.info(f"Extracted post_date from page element: {data['post_date']}")
                        post_date_found_direct_scrape = True
                except Exception as e:
                    logging.warning(f"Direct scrape date parsing failed for '{raw_text}': {e}")
            else:
                logging.warning("No direct page element found for post date.")
            
        except Exception as e:
            logging.warning(f"Error during direct scraping of elements: {e}")

        # --- Fallback to profile grid scraping for VIEWS ONLY if views is still missing ---
        if data["views"] is None:
            logging.info("Views missing from direct scrape. Attempting grid fallback for views.")
            if not data["owner"]:
                 logging.warning("Owner not found, cannot perform grid fallback scrape for views.")
                 data["error"] = data["error"] or ""
                 data["error"] += " Owner not found, failed grid fallback for views."
            else:
                profile_url = build_profile_url(data["owner"])
                
                try:
                    logging.info(f"Navigating to profile URL for grid fallback: {profile_url}")
                    await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(random.uniform(3, 6))

                    grid_views_only, _ = await scrape_views_and_date_from_grid(page, video_id)
                    
                    if grid_views_only is not None:
                        data["views"] = grid_views_only
                        logging.info(f"Views obtained from grid fallback: {data['views']}")

                except GridTimeoutError as gte:
                    logging.warning(f"Grid scrape for views timed out in current mode: {gte}. Relaunching in HEADED mode for re-attempt.")
                    data["error"] = data["error"] or "" # Initialize error if not already set
                    data["error"] += " Grid scrape for views timed out. Browser popped up for observation."

                    # Close the current browser session
                    if context: await context.close()
                    if browser: await browser.close()

                    # Launch new browser in HEADED mode for re-attempting grid scrape
                    browser, context, page = await _launch_browser_session(p_instance, headless_mode=False, url=profile_url)
                    logging.info("Browser is visible to re-attempt grid scrape (for views) after timeout.")
                    if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                         app_instance.set_status("Grid scrape for views timed out! Browser visible. Re-attempting grid scrape...")
                    
                    # --- Second attempt at grid scrape in HEADED mode ---
                    try:
                        grid_views_headed_only, _ = await scrape_views_and_date_from_grid(page, video_id)
                        
                        if grid_views_headed_only is not None:
                            data["views"] = grid_views_headed_only
                            logging.info(f"Views obtained from headed grid re-attempt: {data['views']}")
                            if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                                app_instance.set_status("Grid scrape for views successful in headed mode.")
                            # CRITICAL FIX: Clear the error if the re-scrape was successful
                            data["error"] = None # Clear any previous grid timeout error
                        else:
                            logging.warning("Grid scrape for views in headed mode still failed to get data.")
                            data["error"] += " Headed grid scrape for views did not retrieve data."
                            if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                                app_instance.set_status("Headed grid scrape for views incomplete. Browser visible for 30s observation.")
                            await asyncio.sleep(30)
                            return data

                    except GridTimeoutError as final_gte:
                        logging.warning(f"Grid scrape for views timed out again in headed mode: {final_gte}. Observing for 30 seconds.")
                        data["error"] += f" Headed grid scrape for views also timed out: {final_gte}. Observing."
                        if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                             app_instance.set_status("Headed grid scrape for views timed out! Browser visible for 30s observation.")
                        await asyncio.sleep(30)
                        return data

                    except Exception as e_headed:
                        logging.error(f"Unexpected error during headed grid re-attempt (for views): {e_headed}", exc_info=True)
                        data["error"] += f" Unexpected error during headed grid re-attempt (for views): {e_headed}"
                        if app_instance and hasattr(app_instance, 'set_status'): # Changed to set_status
                             app_instance.set_status("Error during headed grid scrape (for views). Browser visible for 30s observation.")
                        await asyncio.sleep(30)
                        return data

                except Exception as e:
                    logging.warning(f"Error during grid fallback navigation or scrape (before headed relaunch check, for views): {e}", exc_info=True)
                    data["error"] = data["error"] or ""
                    data["error"] += f" Error during grid fallback (for views): {e}"

        # --- Calculate Engagement Rate ---
        if all(v is not None for v in [data["likes"], data["comments"]]) and data["views"] is not None and data["views"] > 0:
            total_interactions = data["likes"] + data["comments"]
            data["engagement_rate"] = round((total_interactions / data["views"]) * 100, 2)
            logging.info(f"Calculated engagement rate: {data['engagement_rate']}%")
        else:
            logging.info("Cannot calculate engagement rate due to missing data (likes, comments, or views) or zero views.")

        # --- Final check for missing data and set error message if needed ---
        missing_fields = [k for k in ["views", "likes", "comments", "shares", "saves", "post_date"] if data[k] is None]
        if missing_fields:
            data["error"] = data["error"] or ""
            data["error"] += f" Missing data points: {', '.join(missing_fields)}."
            logging.warning(f"Final data check: {data['error']}")

        # Convert None values to "N/A" for the final output as requested by original structure
        for key, value in data.items():
            if value is None and key not in ["error", "engagement_rate"]:
                data[key] = "N/A"
            elif key == "engagement_rate" and value is None:
                data[key] = "N/A"

        await save_cookies(context)

    except PlaywrightTimeoutError as e:
        data["error"] = f"A page operation timed out: {str(e)}. This often means elements did not load in time or network issues. Try increasing timeouts or running non-headless."
        logging.critical(f"Playwright timeout: {e}", exc_info=True)
    except Exception as e:
        data["error"] = f"An unexpected error occurred during scraping: {str(e)}. See logs for details. This might be due to website changes or network issues."
        logging.critical(f"Unexpected error during scraping: {e}", exc_info=True)
    finally:
        if context:
            await context.close()
            logging.info("Browser context closed.")
        if browser:
            await browser.close()
            logging.info("Browser closed.")
        if p_instance:
            await p_instance.stop()
            logging.info("Playwright instance stopped.")
    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <tiktok_video_url>")
        print("Example: python scraper.py https://www.tiktok.com/@charlidamelio/video/7036660167099712773")
        sys.exit(1)
    
    url_to_scrape = sys.argv[1]
    
    if not url_to_scrape.startswith("http") or "tiktok.com" not in url_to_scrape:
        print(f"Error: Provided argument is not a valid TikTok URL: {url_to_scrape}")
        sys.exit(1)

    try:
        result = asyncio.run(scrape_post_data(url_to_scrape))
        print(json.dumps(result, indent=2))
    except Exception as main_e:
        logging.critical(f"An error occurred in the main execution block: {main_e}", exc_info=True)
        print(json.dumps({"error": f"Application failed to run: {main_e}"}, indent=2))
