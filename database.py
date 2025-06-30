import sqlite3
import os
import logging
from datetime import datetime
import re

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Corrected DB_FILE name for TikTok
DB_FILE = os.path.join(SCRIPT_DIR, "tiktok_analytics.db")

def setup_database():
    """Sets up the SQLite database and creates the tiktok_posts table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Corrected: Table name to tiktok_posts, and added 'saves' column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tiktok_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                link TEXT,
                post_date TEXT,
                last_record TEXT,
                owner TEXT,
                likes TEXT,
                comments TEXT,
                shares TEXT,
                saves TEXT, -- New column for Saves
                views TEXT,
                engagement_rate TEXT,
                error TEXT
            )
        """)
        conn.commit()
        logging.info("Database setup/check complete for TikTok analytics.")
    except Exception as e:
        logging.error(f"Failed to setup database: {e}", exc_info=True)
    finally:
        conn.close()

def save_to_database(post_data_dict, video_id):
    """Saves or updates a scraped TikTok post's data in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        engagement_rate_value = post_data_dict.get("engagement_rate", "N/A")
        if isinstance(engagement_rate_value, (int, float)) and engagement_rate_value != "N/A":
            formatted_engagement_rate = f"{engagement_rate_value:.2f}%"
        else:
            formatted_engagement_rate = str(engagement_rate_value)

        db_row = {
            "video_id": video_id,
            "link": post_data_dict.get("link", "N/A"),
            "post_date": post_data_dict.get("post_date", "N/A"),
            "last_record": post_data_dict.get("last_record", datetime.now().strftime("%Y-%m-%d")),
            "owner": post_data_dict.get("owner", "N/A"),
            "likes": str(post_data_dict.get("likes", "N/A")),
            "comments": str(post_data_dict.get("comments", "N/A")),
            "shares": str(post_data_dict.get("shares", "N/A")),
            "saves": str(post_data_dict.get("saves", "N/A")), # Added saves here
            "views": str(post_data_dict.get("views", "N/A")),
            "engagement_rate": formatted_engagement_rate,
            "error": post_data_dict.get("error", None)
        }
        cursor.execute("""
            INSERT OR REPLACE INTO tiktok_posts
            (video_id, link, post_date, last_record, owner, likes, comments, shares, saves, views, engagement_rate, error)
            VALUES (:video_id, :link, :post_date, :last_record, :owner, :likes, :comments, :shares, :saves, :views, :engagement_rate, :error)
        """, db_row)
        conn.commit()
        logging.info(f"Data for {video_id} saved to database.")
    except sqlite3.Error as e:
        log_msg = f"Database error for {video_id}: {e}"
        logging.error(log_msg, exc_info=True)
    finally:
        conn.close()

def load_data_from_db():
    """Loads all scraped TikTok post data from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Corrected: Added 'saves' to columns selected
    db_columns = [
        "video_id", "link", "post_date", "last_record",
        "owner", "likes", "comments", "shares", "saves", "views", "engagement_rate", "error"
    ]
    select_query = f"SELECT {', '.join(db_columns)} FROM tiktok_posts ORDER BY last_record DESC"
    try:
        cursor.execute(select_query)
        rows = cursor.fetchall()
        logging.info(f"Loaded {len(rows)} rows from database.")
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error loading data: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def delete_data_from_db(link):
    """Deletes a record from the database based on its link (extracting video_id)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Corrected: Use TikTok specific video ID extraction
        match = re.search(r'(?:tiktok\.com/@[\w.]+/video/|vm\.tiktok\.com/|tiktok\.com/t/)([0-9]+)', link)
        if match:
            video_id = match.group(1)
            cursor.execute("DELETE FROM tiktok_posts WHERE video_id = ?", (video_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logging.info(f"Successfully deleted record for video_id: {video_id}")
            else:
                logging.warning(f"No record found for video_id: {video_id} (link: {link})")
        else:
            logging.warning(f"Could not extract video ID from link: {link}. Cannot delete.")
    except sqlite3.Error as e:
        logging.error(f"Database error deleting data for link {link}: {e}", exc_info=True)
    finally:
        conn.close()
