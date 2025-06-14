# tiktok_post_analytics.py (Revised - Removed initial browser launch and messagebox)

import tkinter as tk
import logging
import os
import traceback
from datetime import datetime
# Removed: from tkinter import messagebox # No longer needed for startup messages

from ui import TikTokScraperApp
from database import setup_database, DB_FILE
from scraper import TIKTOK_SESSION_DATA_DIR, TIKTOK_BROWSER_USER_DATA_DIR # Corrected directory names


# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "app_run.log")

logging.basicConfig(
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler()
    ],
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s',
)
logging.info("TikTok Post Analyzer starting up (Selenium)...")

if not os.path.exists(TIKTOK_SESSION_DATA_DIR):
    try:
        os.makedirs(TIKTOK_SESSION_DATA_DIR)
        logging.info(f"Created TikTok session data directory: {TIKTOK_SESSION_DATA_DIR}")
    except Exception as e:
        logging.error(f"Failed to create TikTok session data directory on startup: {e}", exc_info=True)

if not os.path.exists(TIKTOK_BROWSER_USER_DATA_DIR):
    try:
        os.makedirs(TIKTOK_BROWSER_USER_DATA_DIR)
        logging.info(f"Created TikTok Browser user data directory: {TIKTOK_BROWSER_USER_DATA_DIR}")
    except Exception as e:
        logging.error(f"Failed to create TikTok Browser user data directory on startup: {e}", exc_info=True)


root_tk_window = None
app = None 

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Handles unhandled exceptions in the Tkinter application.
    Errors will now be logged to console and file.
    """
    try:
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical(f"Unhandled Tkinter exception:\n{tb_str}")
    except Exception as log_exc:
        print(f"Logging failed in global_exception_handler: {log_exc}")
        print(f"Original Unhandled Tkinter exception: {exc_type} - {exc_value}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        setup_database()

        root_tk_window = tk.Tk()
        root_tk_window.report_callback_exception = global_exception_handler

        app = TikTokScraperApp(root_tk_window) 

        app._load_data_from_db_into_ui()
        
        root_tk_window.mainloop()

    except SystemExit:
        logging.info("Application exited via SystemExit.")
    except Exception as e_startup:
        tb_str_startup = traceback.format_exc()
        logging.critical(f"CRITICAL STARTUP ERROR: {e_startup}\n{tb_str_startup}")
        error_report_file = os.path.join(SCRIPT_DIR, "__startup_error__.log")
        try:
            with open(error_report_file, "a") as f_err:
                f_err.write(f"{datetime.now()} - CRITICAL STARTUP ERROR: {e_startup}\n{tb_str_startup}\n")
            print(f"A critical startup error occurred. Details saved to {error_report_file}")
        except Exception as e_file_log:
            print(f"Failed to write to {error_report_file}: {e_file_log}")
            print(f"Original startup error: {e_startup}\n{tb_str_startup}")
        
        import sys
        sys.exit(1)