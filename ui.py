import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import asyncio
import csv
import logging
from datetime import datetime, timezone
import os
import time
import re
import json
import shutil
import sys
import random # Added for random delays

import customtkinter as ctk

# Corrected: Import TikTok-specific directories and functions
# No longer importing specific selenium classes directly here, as scraper handles driver init.
from scraper import scrape_post_data, get_tiktok_video_id_from_url, TIKTOK_SESSION_DATA_DIR, TIKTOK_BROWSER_USER_DATA_DIR
# Corrected: Import TikTok-specific DB functions and file
from database import setup_database, DB_FILE, load_data_from_db, save_to_database, delete_data_from_db


# --- CustomTkinter Comprehensive Theme Definition ---
custom_theme_dict = {
    "CTk": {
        "fg_color": ["white", "white"],
        "text_color": ["#333333", "#333333"],
    },
    "CTkFrame": {
        "fg_color": ["white", "white"],
        "top_fg_color": ["white", "white"],
        "border_color": ["#E0E0E0", "#E0E0E0"],
        "border_width": 0,
        "corner_radius": 10,
    },
    "CTkButton": {
        "fg_color": ["#C6E7FF", "#C6E7FF"],
        "hover_color": ["#B0D4FF", "#B0D4FF"],
        "text_color": ["#333333", "#333333"],
        "text_color_disabled": ["#999999", "#999999"],
        "border_width": 0,
        "border_color": ["transparent", "transparent"],
        "corner_radius": 5,
    },
    "CTkLabel": {
        "text_color": ["#333333", "##333333"],
        "fg_color": ["transparent", "transparent"],
        "corner_radius": 0,
    },
    "CTkEntry": {
        "fg_color": ["white", "white"],
        "border_color": ["#A0A0A0", "#A0A0A0"],
        "text_color": ["#333333", "#333333"],
        "placeholder_text_color": ["#666666", "#666666"],
        "border_width": 2,
        "corner_radius": 5,
    },
    "CTkProgressBar": {
        "fg_color": ["#C6E7FF", "#C6E7FF"],
        "progress_color": ["#B0D4FF", "#B0D4FF"],
        "border_color": ["#B0D4FF", "#B0D4FF"],
        "border_width": 0,
        "corner_radius": 0,
    },
    "CTkSlider": {
        "fg_color": ["#C6E7FF", "#C6E7FF"],
        "progress_color": ["#B0D4FF", "#B0D4FF"],
        "button_color": ["#333333", "#333333"],
        "button_hover_color": ["#666666", "#666666"],
        "border_color": ["#B0D4FF", "#B0D4FF"],
        "border_width": 0,
        "corner_radius": 1000,
        "button_corner_radius": 1000,
    },
    "CTkOptionMenu": {
        "fg_color": ["#F0F0F0", "#F0F0F0"],
        "button_color": ["#C6E7FF", "#C6E7FF"],
        "button_hover_color": ["#B0D4FF", "#B0D4FF"],
        "text_color": ["#333333", "#333333"],
        "text_color_disabled": ["#999999", "#999999"],
        "corner_radius": 5,
        "border_width": 1,
        "border_color": ["#C6E7FF", "#C6E7FF"],
    },
    "CTkComboBox": {
        "fg_color": ["white", "white"],
        "button_color": ["#C6E7FF", "#C6E7FF"],
        "button_hover_color": ["#B0D4FF", "#B0D4FF"],
        "text_color": ["#333333", "#333333"],
        "text_color_disabled": ["#999999", "#999999"],
        "corner_radius": 5,
        "border_width": 2,
        "border_color": ["#C6E7FF", "#C6E7FF"],
    },
    "CTkScrollbar": {
        "fg_color": ["#E0E0E0", "#E0E0E0"],
        "button_color": ["#999999", "#999999"],
        "button_hover_color": ["#666666", "#666666"],
        "corner_radius": 1000,
        "border_width": 0,
        "border_spacing": 0,
        "width": 3,
    },
    "CTkSwitch": {
        "fg_color": ["#C6E7FF", "#C6E7FF"],
        "progress_color": ["#B0D4FF", "#B0D4FF"],
        "button_color": ["#333333", "#333333"],
        "button_hover_color": ["#666666", "#666666"],
        "corner_radius": 1000,
        "button_corner_radius": 1000,
    },
    "CTkCheckBox": {
        "fg_color": ["#C6E7FF", "#C6E7FF"],
        "checkmark_color": ["#333333", "#333333"],
        "hover_color": ["#B0D4FF", "#B0D4FF"],
        "text_color": ["#333333", "#333333"],
        "text_color_disabled": ["#999999", "#999999"],
        "corner_radius": 5,
        "border_width": 1,
        "border_color": ["#C6E7FF", "#C6E7FF"],
    },
    "CTkRadiobutton": {
        "fg_color": ["#C6E7FF", "#C6E7FF"],
        "checkmark_color": ["#333333", "#333333"],
        "hover_color": ["#B0D4FF", "#B0D4FF"],
        "text_color": ["#333333", "#333333"],
        "text_color_disabled": ["#999999", "#999999"],
        "corner_radius": 1000,
        "border_width": 2,
        "border_color": ["#C6E7FF", "#C6E7FF"],
    },
    "CTkSegmentedButton": {
        "fg_color": ["white", "white"],
        "selected_color": ["#C6E7FF", "#C6E7FF"],
        "selected_hover_color": ["#B0D4FF", "#B0D4FF"],
        "unselected_color": ["#E0E0E0", "#E0E0E0"],
        "unselected_hover_color": ["#D0D0D0", "#D0D0D0"],
        "text_color": ["#333333", "#333333"],
        "text_color_disabled": ["#999999", "#999999"],
        "border_color": ["#C6E7FF", "#C6E7FF"],
        "border_width": 1,
        "corner_radius": 5,
    },
    "DropdownMenu": {
        "fg_color": ["#F0F0F0", "#F0F0F0"],
        "hover_color": ["#C6E7FF", "#C6E7FF"],
        "text_color": ["#333333", "#333333"],
        "corner_radius": 5,
        "border_width": 0,
        "border_color": ["transparent", "transparent"],
    },
    "CTkTextbox": {
        "fg_color": ["#F0F0F0", "#F0F0F0"],
        "border_color": ["#C6E7FF", "#C6E7FF"],
        "text_color": ["#333333", "#333333"],
        "placeholder_text_color": ["#666666", "#666666"],
        "border_width": 1,
        "corner_radius": 5,
        "scrollbar_button_color": ["#B0D4FF", "#B0D4FF"],
        "scrollbar_button_hover_color": ["#A0C0E0", "#A0C0E0"],
    },
    "CTkToolTip": {
        "fg_color": ["#333333", "#333333"],
        "text_color": ["white", "white"],
        "corner_radius": 5,
    },
    "CTkFont": {
        "macOS": {
            "family": "Helvetica Neue",
            "size": 13,
            "weight": "normal",
        },
        "Windows": {
            "family": "Segoe UI",
            "size": 13,
            "weight": "normal",
        },
        "Linux": {
            "family": "Ubuntu",
            "size": 13,
            "weight": "normal",
        }
    }
}


def resource_path(relative_path):
    """Get absolute path to a resource; works for both development and frozen executables."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

import sys

theme_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_theme.json")
try:
    with open(theme_file_path, "w") as f:
        json.dump(custom_theme_dict, f, indent=4)
    logging.info(f"Custom theme saved to: {theme_file_path}")
except Exception as e:
    logging.error(f"Error saving custom theme JSON file: {e}. Falling back to default 'blue' theme.", exc_info=True)
    theme_file_path = "blue"


class TikTokScraperApp: # Renamed class
    def __init__(self, root_window): # Removed logged_in_username from init as it's not managed explicitly by UI for TikTok
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme(theme_file_path)

        self.root = root_window
        self.root.title("TikTok Post Analyzer") # Updated title
        self.root.geometry("1000x650")
        
        # Set application icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "redblack.ico") # Changed icon file
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                logging.info(f"Application icon set to: {icon_path}")
            else:
                logging.warning(f"Icon file not found at: {icon_path}")
        except Exception as e:
            logging.error(f"Error setting application icon: {e}", exc_info=True)


        self.scraped_data_for_table = [] # Stores data as list of dicts
        
        # Initialize sorting state
        self.sort_column = None
        self.sort_reverse = False

        self._setup_ui()
        
        # Initial status for TikTok app (no explicit Instaloader login)
        self.set_status("Ready. TikTok scraping relies on persistent browser data (no explicit login needed).")
            
        self._load_data_from_db_into_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.is_batch_scraping = False
        
        # Initialize temporary notification label
        self._temp_notification_label = None
        self._temp_notification_after_id = None
        # Initialize overlay attribute
        self.overlay = None 


    def _on_closing(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?", parent=self.root):
            logging.info("Application exiting by user confirmation.")
            self.root.destroy()

    def _load_data_from_db_into_ui(self):
        self.set_status("Loading previous records from database...")
        try:
            # Clear in-memory data and treeview before loading from DB
            self.scraped_data_for_table.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)

            rows = load_data_from_db()
            # This db_columns list MUST match the SELECT statement order in database.py's load_data_from_db for TikTok
            db_columns_order = [
                "video_id", "link", "post_date", "last_record",
                "owner", "likes", "comments", "shares", "saves", "views", "engagement_rate", "error" # Added 'saves'
            ]

            for row_tuple in rows:
                row_dict = {}
                for j, col_name in enumerate(db_columns_order):
                    if j < len(row_tuple):
                        row_dict[col_name] = row_tuple[j]
                    else:
                        row_dict[col_name] = None 
                
                # Format dates to date-only strings
                if row_dict.get("post_date") and row_dict["post_date"] != "N/A":
                    try:
                        # Handle potential "YYYY-MM-DD HH:MM:SS (UTC)" format or just "YYYY-MM-DD"
                        if " " in str(row_dict["post_date"]): # Check for time part
                            dt_obj = datetime.strptime(str(row_dict["post_date"]).split(" ")[0], "%Y-%m-%d")
                        else:
                             dt_obj = datetime.strptime(str(row_dict["post_date"]), "%Y-%m-%d")
                        row_dict["post_date"] = dt_obj.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        logging.warning(f"Failed to parse post_date from DB: {row_dict.get('post_date')}")
                        row_dict["post_date"] = "N/A" # Set to N/A if cannot parse

                if row_dict.get("last_record") and row_dict["last_record"] != "N/A":
                    try:
                        # Ensure last_record is also parsed as date only for display
                        if " " in str(row_dict["last_record"]):
                            dt_obj = datetime.strptime(str(row_dict["last_record"]).split(" ")[0], "%Y-%m-%d")
                        else:
                            dt_obj = datetime.strptime(str(row_dict["last_record"]), "%Y-%m-%d")
                        row_dict["last_record"] = dt_obj.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        logging.warning(f"Failed to parse last_record from DB: {row_dict.get('last_record')}")
                        row_dict["last_record"] = "N/A" # Set to N/A if cannot parse


                # Explicitly map data to the display columns expected by self.columns
                post_data_gui = {
                    "link": row_dict.get("link", "N/A"),
                    "post_date": row_dict.get("post_date", "N/A"),
                    "last_record": row_dict.get("last_record", "N/A"),
                    "owner": row_dict.get("owner", "N/A"),
                    "likes": row_dict.get("likes", "N/A"),
                    "comments": row_dict.get("comments", "N/A"),
                    "shares": row_dict.get("shares", "N/A"),
                    "saves": row_dict.get("saves", "N/A"), # Added 'saves' here
                    "views": row_dict.get("views", "N/A"),
                    "engagement_rate": row_dict.get("engagement_rate", "N/A"),
                    "error": row_dict.get("error", None),
                    "video_id": row_dict.get("video_id", get_tiktok_video_id_from_url(row_dict.get("link", ""))) # Changed to video_id
                }
                
                self.scraped_data_for_table.append(post_data_gui)
            
            self._refresh_table_display()

            self.set_status(f"{len(rows)} records loaded. Ready.")
            logging.info(f"{len(rows)} records loaded from database.")
        except Exception as e:
            if "no such column" in str(e).lower() or "no such table" in str(e).lower(): # Handle "no such table" too
                msg = (
                    f"Database schema error: {e}. "
                    f"Please delete or rename the old '{DB_FILE}' file and restart the application to recreate the schema."
                )
                self.set_status(msg)
                logging.error(msg, exc_info=True)
            else:
                self.set_status(f"Error loading data from database: {e}. Ready.")
                logging.error(f"Error loading data from database: {e}", exc_info=True)

    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent") 
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10) 

        table_frame = ctk.CTkFrame(main_frame, fg_color="transparent") 
        table_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=(0, 5)) # Adjusted pady for compact layout
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_columnconfigure(1, weight=0)


        # Modified self.columns to include "saves" and removed "video_id"
        self.columns = (
            "link", "post_date", "last_record",
            "owner", "likes", "comments", "shares", "saves", "views", "engagement_rate" 
        )
        self.tree = ttk.Treeview(
            table_frame, columns=self.columns, show="headings", selectmode="extended" 
        )

        tree_style = ttk.Style()
        tree_style.theme_use('clam')
        tree_style.configure("Treeview",
            background="white",
            fieldbackground="white",
            foreground="#333333",
            font=("Segoe UI", 10),
            bordercolor="#E0E0E0",
            lightcolor="#E0E0E0",
            darkcolor="#E0E0E0",
            rowheight=25
        )
        tree_style.map("Treeview",
            background=[('selected', "#87aec9")],
            foreground=[('selected', "white")]
        )
        tree_style.configure("Treeview.Heading",
            background="#C6E7FF",
            foreground="#333333",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padding=(5, 5)
        )
        self.tree.tag_configure("failed", background="#FFCCCC", foreground="black")

        # Modified col_widths to include "saves" and adjusted other widths
        col_widths = {
            "link": 250, 
            "post_date": 100,
            "last_record": 100,
            "owner": 90,
            "likes": 60,
            "comments": 60,
            "shares": 60,
            "saves": 60, # New saves column width
            "views": 70,
            "engagement_rate": 100
        }
        col_align = {
            "likes": tk.CENTER, "comments": tk.CENTER, "shares": tk.CENTER, "saves": tk.CENTER, "views": tk.CENTER, "engagement_rate": tk.CENTER # Added saves alignment
        }
        for col in self.columns:
            heading_text = col.replace("_", " ").title()
            self.tree.heading(col, text=heading_text, command=lambda c=col: self._sort_treeview(c))
            self.tree.column(col, width=col_widths.get(col, 100), anchor=col_align.get(col, tk.W), minwidth=50)

        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ctk.CTkScrollbar(table_frame, command=self.tree.yview, orientation="vertical", width=8)
        vsb.grid(row=0, column=1, sticky="ns") 
        self.tree.configure(yscrollcommand=vsb.set)

        input_frame = ctk.CTkFrame(main_frame, fg_color="transparent") 
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5) 

        url_record_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        url_record_frame.pack(fill=tk.X, pady=(0, 5))
        
        ctk.CTkLabel(url_record_frame, text="TikTok Post URL:").pack(side=tk.LEFT, padx=(0, 5)) # Updated label
        self.url_entry = ctk.CTkEntry(url_record_frame, width=60) 
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.scrape_button = ctk.CTkButton( 
            url_record_frame, text="Record", command=self.on_record_button_press
        )
        self.scrape_button.pack(side=tk.LEFT, padx=5)

        other_buttons_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        other_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.batch_scrape_button = ctk.CTkButton( 
            other_buttons_frame, text="Import CSV", command=self.on_batch_scrape_button_press
        )
        self.batch_scrape_button.pack(side=tk.LEFT, padx=5)

        self.update_selected_button = ctk.CTkButton(
            other_buttons_frame, text="Update Data", command=self.on_update_selected
        )
        self.update_selected_button.pack(side=tk.LEFT, padx=5)

        self.delete_selected_button = ctk.CTkButton(
            other_buttons_frame, text="Delete", command=self.on_delete_selected
        )
        self.delete_selected_button.pack(side=tk.LEFT, padx=5)

        self.export_button = ctk.CTkButton( 
            other_buttons_frame, text="Export CSV", command=self.export_to_csv
        )
        self.export_button.pack(side=tk.LEFT, padx=5)

        # New button for clearing browser data
        self.clear_browser_data_button = ctk.CTkButton(
            other_buttons_frame, text="Clear Browser Data", command=self.clear_browser_data
        )
        self.clear_browser_data_button.pack(side=tk.LEFT, padx=5)


        self.tree.bind("<Button-3>", self._show_context_menu)


    def _update_username_display(self, username):
        """No longer applicable for TikTok, but kept as a placeholder."""
        pass


    def set_status(self, message):
        """
        Updates the status using a temporary, non-blocking overlay notification.
        """
        logging.info(f"STATUS_UPDATE: {message}")
        self.root.after(0, lambda: self._show_temp_notification(message))

    def set_status_from_thread(self, message):
        """
        Updates the status using a temporary, non-blocking overlay notification from a thread.
        """
        self.root.after(0, lambda: self._show_temp_notification(message))

    def _show_temp_notification(self, message, duration_ms=3000):
        """
        Displays a temporary, non-blocking notification label in the center top.
        """
        if self._temp_notification_label:
            self._temp_notification_label.destroy()
            if self._temp_notification_after_id:
                self.root.after_cancel(self._temp_notification_after_id)

        self._temp_notification_label = ctk.CTkLabel(
            self.root,
            text=message,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            fg_color="#333333",
            corner_radius=5,
            padx=15, pady=10
        )
        self._temp_notification_label.place(relx=0.5, rely=0.05, anchor="n")
        
        self._temp_notification_after_id = self.root.after(duration_ms, self._hide_temp_notification)

    def _hide_temp_notification(self):
        """Hides the temporary notification label."""
        if self._temp_notification_label:
            self._temp_notification_label.destroy()
            self._temp_notification_label = None
        if self._temp_notification_after_id:
            self._temp_notification_after_id = None

    def _show_blocking_overlay(self, text="Processing..."):
        """
        Displays a blocking overlay for long-running operations.
        """
        if self.overlay:
            return

        self.overlay = ctk.CTkFrame(self.root, fg_color=("gray80", "gray20"), bg_color=("gray80", "gray20"), corner_radius=0)
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.lift()

        container = ctk.CTkFrame(self.overlay, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(container, text=text, font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333").pack(pady=(0, 10))
        ctk.CTkLabel(container, text="Please wait...", font=ctk.CTkFont(size=14), text_color="#666666").pack()
        
        self.root.update_idletasks()

    def _hide_blocking_overlay(self):
        """Hides the blocking overlay."""
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

    def on_record_button_press(self):
        post_url = self.url_entry.get().strip()
        if not post_url:
            self.set_status("Input Error: Please enter a TikTok Post URL.")
            return

        self._set_buttons_state(tk.DISABLED) 
        self._show_blocking_overlay("Recording Single Post...")
        logging.info(f"Record button pressed for URL: {post_url}")

        thread = threading.Thread(
            target=self._run_tiktok_scrape_in_thread, args=(post_url, False)
        )
        thread.daemon = True
        thread.start()

    def on_batch_scrape_button_press(self):
        if self.is_batch_scraping:
            self.set_status("Batch scraping already in progress.")
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Select CSV file with TikTok URLs" # Updated title
        )
        if not filepath:
            self.set_status("Batch scrape cancelled. No CSV file selected.")
            return

        self.is_batch_scraping = True
        self._set_buttons_state(tk.DISABLED) 
        self._show_blocking_overlay(f"Starting Batch Scrape from CSV...")
        logging.info(f"Batch scrape initiated from CSV: {filepath}")

        thread = threading.Thread(
            target=self._run_batch_scrape_in_thread, args=(filepath,)
        )
        thread.daemon = True
        thread.start()

    def on_update_selected(self):
        selections = list(self.tree.selection())
        if not selections:
            self.set_status("Selection Error: Select one or more items to update.")
            return

        links_to_update = []
        for sel in selections:
            try:
                item_data = self._get_item_data_from_tree_selection(sel)
                if item_data and "link" in item_data:
                    links_to_update.append(item_data["link"])
            except Exception as ex:
                logging.error(f"Error retrieving tree item for update: {ex}", exc_info=True)
                self.set_status(f"Error preparing update: {ex}")

        if not links_to_update:
            self.set_status("Update Warning: No valid items selected for update.")
            return

        self.is_batch_scraping = True 
        self._set_buttons_state(tk.DISABLED)
        self._show_blocking_overlay(f"Updating {len(links_to_update)} Selected Posts...")
        logging.info(f"Update selected initiated for {len(links_to_update)} posts.")

        thread = threading.Thread(
            target=self._run_batch_scrape_in_thread, args=(None, links_to_update)
        )
        thread.daemon = True
        thread.start()

    def on_delete_selected(self):
        """Deletes selected items from the Treeview and the database."""
        selections = list(self.tree.selection())
        if not selections:
            messagebox.showerror("Selection Error", "Select one or more items to delete.", parent=self.root)
            return

        links_to_delete = []
        for sel in selections:
            try:
                item_data = self._get_item_data_from_tree_selection(sel)
                if item_data and "link" in item_data:
                    links_to_delete.append(item_data["link"])
            except Exception as ex:
                logging.error(f"Error retrieving tree item for deletion: {ex}", exc_info=True)
                self.set_status(f"Error preparing deletion: {ex}")

        if not links_to_delete:
            messagebox.showwarning("Delete Warning", "No valid items selected for deletion.", parent=self.root)
            return

        self.set_status(f"Deleting {len(links_to_delete)} selected posts...")
        logging.info(f"Deletion initiated for {len(links_to_delete)} posts.")

        def delete_task():
            try:
                for link in links_to_delete:
                    # Remove from in-memory list first
                    self.scraped_data_for_table = [item for item in self.scraped_data_for_table if item.get("link") != link]
                    delete_data_from_db(link) # Call the database function to delete
                self.root.after(0, self._refresh_table_display) # Refresh UI from updated in-memory list
                self.root.after(0, lambda: self.set_status(f"Deleted {len(links_to_delete)} items. Table refreshed."))
                logging.info(f"Successfully deleted {len(links_to_delete)} items.")
            except Exception as e:
                self.root.after(0, lambda: self.set_status(f"Error during deletion: {e}"))
                logging.error(f"Error during deletion: {e}", exc_info=True)
            finally:
                self.root.after(0, self._set_buttons_state, tk.NORMAL)
        
        self._set_buttons_state(tk.DISABLED)
        threading.Thread(target=delete_task, daemon=True).start()
    
    def _get_item_data_from_tree_selection(self, item_id):
        """Helper to get the full dictionary for a selected treeview item."""
        values = self.tree.item(item_id, 'values')
        if not values:
            return None
        
        # Map the values back to a dictionary based on self.columns order
        # Assuming that 'link' is always the first column in self.columns for this
        item_dict_from_display = {self.columns[i]: values[i] for i in range(len(self.columns))}
        
        # Now, find the full data entry in self.scraped_data_for_table using the link
        link_from_tree = item_dict_from_display.get("link")
        if link_from_tree:
            for data_entry in self.scraped_data_for_table:
                # Use get_tiktok_video_id_from_url for robust comparison
                if get_tiktok_video_id_from_url(data_entry.get("link", "")) == get_tiktok_video_id_from_url(link_from_tree):
                    return data_entry
        return None

    def clear_browser_data(self):
        """
        Clears the TikTok browser user data directory, effectively logging out and
        resetting the browser profile.
        """
        if messagebox.askyesno("Clear Browser Data", 
                               "This will clear all TikTok browser data (cookies, cache, login sessions).\n"
                               "If TikTok data requires login, you will need to re-establish a session manually by temporarily disabling headless mode in scraper.py and logging in.\n\n"
                               "Are you sure you want to proceed?", parent=self.root):
            try:
                if os.path.exists(TIKTOK_BROWSER_USER_DATA_DIR):
                    shutil.rmtree(TIKTOK_BROWSER_USER_DATA_DIR)
                    os.makedirs(TIKTOK_BROWSER_USER_DATA_DIR) # Recreate empty directory
                    self.set_status("TikTok browser data cleared. If login is required, re-establish manually.")
                    logging.info("TikTok browser user data cleared.")
                else:
                    self.set_status("TikTok browser data directory not found, nothing to clear.")
                    logging.warning("Attempted to clear non-existent TikTok browser data directory.")
            except Exception as e:
                self.set_status(f"Error clearing browser data: {e}")
                logging.error(f"Error clearing TikTok browser data: {e}", exc_info=True)


    def _run_batch_scrape_in_thread(self, filepath=None, urls_to_scrape_list=None):
        urls_to_scrape = []
        if urls_to_scrape_list:
            urls_to_scrape = urls_to_scrape_list
            source_desc = f"{len(urls_to_scrape)} selected URLs"
        elif filepath:
            try:
                with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    for i, row in enumerate(reader):
                        if i == 0 and len(row) > 0 and row[0].strip().lower() == 'url':
                            continue
                        if row:
                            url = row[0].strip()
                            if url:
                                urls_to_scrape.append(url)
                source_desc = f"CSV file: {filepath}"
            except FileNotFoundError:
                self.set_status_from_thread(f"Error: CSV file not found at {filepath}")
                logging.error(f"CSV file not found: {filepath}", exc_info=True)
                self.is_batch_scraping = False
                self._set_buttons_state(tk.NORMAL)
                self._hide_blocking_overlay()
                return
            except Exception as e:
                self.set_status_from_thread(f"Error reading CSV file: {e}")
                logging.error(f"Error reading CSV from {filepath}: {e}", exc_info=True)
                self.is_batch_scraping = False
                self._set_buttons_state(tk.NORMAL)
                self._hide_blocking_overlay()
                return
        else:
            self.set_status_from_thread("Error: No URLs provided for batch scrape.")
            self.is_batch_scraping = False
            self._set_buttons_state(tk.NORMAL)
            self._hide_blocking_overlay()
            return


        if not urls_to_scrape:
            self.set_status_from_thread(f"No URLs found to scrape from {source_desc}.")
            self.is_batch_scraping = False
            self._set_buttons_state(tk.NORMAL)
            self._hide_blocking_overlay()
            return

        self.set_status_from_thread(f"Starting batch scrape from {source_desc}. Found {len(urls_to_scrape)} URLs...")
        logging.info(f"Batch scrape initiated from {source_desc}. Found {len(urls_to_scrape)} URLs.")

        for i, url in enumerate(urls_to_scrape):
            self.set_status_from_thread(f"Batch: Scraping {i+1}/{len(urls_to_scrape)}: {url}...")
            logging.info(f"Batch: Processing URL {i+1}/{len(urls_to_scrape)}: {url}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            scraped_data_dict = loop.run_until_complete(scrape_post_data(url, self)) 
            loop.close()
            self._handle_scrape_result(scraped_data_dict, url) 
            # Introduce a random delay between scrapes to reduce bot detection
            time.sleep(random.uniform(3, 8)) # Sleep between 3 and 8 seconds

        self.set_status_from_thread(f"Batch scrape complete. Processed {len(urls_to_scrape)} URLs.")
        logging.info("Batch scrape successfully completed.")
        self.is_batch_scraping = False
        self._set_buttons_state(tk.NORMAL)
        self._hide_blocking_overlay()


    def _run_tiktok_scrape_in_thread(self, post_url, is_batch=True): # Renamed function
        scraped_data_dict = {"error": "Scraping failed unexpectedly.", "url": post_url}
        loop = None 
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            scraped_data_dict = loop.run_until_complete(scrape_post_data(post_url, self)) 
        except Exception as e:
            logging.error(f"Error in single scrape thread execution for {post_url}: {e}", exc_info=True)
            scraped_data_dict = {"error": str(e), "url": post_url}
        finally:
            if not is_batch: 
                self.root.after(
                    0, lambda data=scraped_data_dict: self._handle_scrape_result(data, post_url) # Renamed handler
                )
                self.root.after(0, self._set_buttons_state, tk.NORMAL)
                self.root.after(0, self._hide_blocking_overlay)
            if loop and not loop.is_closed():
                loop.close()

    def _handle_scrape_result(self, scraped_data_dict, post_url): # Renamed handler
        video_id = get_tiktok_video_id_from_url(post_url) or "unknown_post" # Changed to video_id
        current_timestamp_str = datetime.now().strftime("%Y-%m-%d") 

        has_error = scraped_data_dict.get("error") is not None and scraped_data_dict.get("error") != ""

        if has_error:
            error_message = scraped_data_dict.get("error", "Unknown error")
            self.set_status(f"Scrape: Failed for {video_id} - {error_message}")
            logging.error(f"Handling scrape failure for {video_id}: {error_message}")
        else:
            self.set_status(f"Scrape: Data for {video_id} recorded successfully.")
            logging.info(f"Scrape: Data for {video_id} successfully handled and recorded.")
            self.url_entry.delete(0, tk.END) # Clear input on successful scrape


        formatted_post_date = "N/A"
        if scraped_data_dict.get("post_date") and scraped_data_dict["post_date"] != "N/A":
            try:
                # Assuming post_date could be "YYYY-MM-DD HH:MM:SS (UTC)" or "YYYY-MM-DD" or relative text.
                # Only parse if it looks like a full datetime or date string
                if re.match(r"\d{4}-\d{2}-\d{2}", str(scraped_data_dict["post_date"])):
                    dt_part = str(scraped_data_dict["post_date"]).split(" ")[0]
                    dt_obj = datetime.strptime(dt_part, "%Y-%m-%d")
                    formatted_post_date = dt_obj.strftime("%Y-%m-%d")
                else:
                    formatted_post_date = scraped_data_dict["post_date"] # Keep relative text as is
            except (ValueError, TypeError):
                formatted_post_date = scraped_data_dict["post_date"] # Keep as is if unparseable

        # Prepare GUI data dictionary with all expected fields, including error status
        gui_data = {
            "link": scraped_data_dict.get("link", post_url),
            "video_id": video_id, # Changed to video_id
            "post_date": formatted_post_date,
            "last_record": current_timestamp_str, # This will always be today's date based on system time
            "owner": scraped_data_dict.get("owner", "N/A"),
            "likes": scraped_data_dict.get("likes", "N/A"),
            "comments": scraped_data_dict.get("comments", "N/A"),
            "shares": scraped_data_dict.get("shares", "N/A"),
            "saves": scraped_data_dict.get("saves", "N/A"), # Added 'saves' here
            "views": scraped_data_dict.get("views", "N/A"),
            "engagement_rate": scraped_data_dict.get("engagement_rate", "N/A"),
            "error": scraped_data_dict.get("error", None),
        }

        existing_index = -1
        for i, item in enumerate(self.scraped_data_for_table):
            if item.get("video_id") == video_id: # Changed to video_id
                existing_index = i
                break

        if existing_index != -1:
            self.scraped_data_for_table[existing_index].update({
                "link": gui_data["link"],
                "post_date": gui_data["post_date"],
                "last_record": gui_data["last_record"],
                "owner": gui_data["owner"],
                "likes": gui_data["likes"],
                "comments": gui_data["comments"],
                "shares": gui_data["shares"],
                "saves": gui_data["saves"], # Updated 'saves' here
                "views": gui_data["views"],
                "engagement_rate": gui_data["engagement_rate"],
                "error": gui_data["error"]
            })
            logging.info(f"Updated existing record for {video_id} in in-memory table.")
        else:
            self.scraped_data_for_table.append(gui_data)
            logging.info(f"Added new record for {video_id} to in-memory table.")

        save_to_database(gui_data, video_id) # Changed to video_id
        
        self.root.after(0, self._refresh_table_display)

    def _set_buttons_state(self, state):
        self.scrape_button.configure(state=state)
        self.batch_scrape_button.configure(state=state)
        self.update_selected_button.configure(state=state)
        self.delete_selected_button.configure(state=state)
        self.export_button.configure(state=state)
        self.clear_browser_data_button.configure(state=state) # Control new button

    def _refresh_table_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for post_data in self.scraped_data_for_table:
            values = []
            for col in self.columns: # self.columns now includes "saves"
                value = post_data.get(col, "N/A")
                if col == "engagement_rate":
                    if isinstance(value, (int, float)) and value != "N/A":
                        values.append(f"{value:.2f}%")
                    elif isinstance(value, str) and value.endswith('%'):
                        values.append(value)
                    else:
                        values.append("N/A")
                else:
                    values.append(value)

            tag = "failed" if (post_data.get("error") is not None and post_data.get("error") != "") else ""
            self.tree.insert("", tk.END, values=values, tags=(tag,) if tag else ())
        
        self.set_status("Table display refreshed.")


    def export_to_csv(self):
        if not self.scraped_data_for_table:
            messagebox.showinfo("No Data", "There is no data to export.", parent=self.root)
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Scraped Data As"
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                # Use the full internal columns for CSV export, including video_id and saves
                full_export_columns = [
                    "link", "video_id", "post_date", "last_record", # Include video_id for CSV export
                    "owner", "likes", "comments", "shares", "saves", "views", "engagement_rate", "error" # Added 'saves'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=full_export_columns)
                writer.writeheader()
                for row_data_dict in self.scraped_data_for_table:
                    export_data = {}
                    for k in full_export_columns: # Iterate through all columns for export
                        v = row_data_dict.get(k, "N/A") # Get value, default to "N/A"
                        if k == "engagement_rate" and isinstance(v, (int, float)) and v != "N/A":
                            export_data[k] = f"{v:.2f}%"
                        else:
                            export_data[k] = v
                    writer.writerow(export_data)
            self.set_status(f"Data exported to CSV: {filepath}")
            messagebox.showinfo("Export Successful", f"Data successfully exported to\n{filepath}", parent=self.root)
            logging.info(f"Data exported to CSV: {filepath}")
        except Exception as e:
            self.set_status(f"Error exporting data: {e}")
            messagebox.showerror("Export Error", f"Could not export data: {e}", parent=self.root)
            logging.error(f"Error exporting data to CSV: {e}", exc_info=True)

    def _show_context_menu(self, event):
        """Displays the right-click context menu for the Treeview."""
        menu = tk.Menu(self.tree, tearoff=0)
        menu.add_command(label="Select All", command=self._select_all_items)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _select_all_items(self):
        """Selects all items currently visible in the Treeview."""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def _sort_treeview(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False

        def _get_sort_value(item, col_name):
            value = item.get(col_name)
            if value is None or value == "N/A":
                if col_name in ["likes", "comments", "shares", "saves", "views", "engagement_rate"]: # Added saves
                    return float('-inf') if not self.sort_reverse else float('inf') 
                elif col_name in ["post_date", "last_record"]:
                    return datetime.min.replace(tzinfo=timezone.utc) if not self.sort_reverse else datetime.max.replace(tzinfo=timezone.utc)
                return ""
            
            if col_name in ["likes", "comments", "shares", "saves", "views"]: # Added saves
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return float('-inf') if not self.sort_reverse else float('inf')
            if col_name == "engagement_rate":
                try:
                    if isinstance(value, str) and value.endswith('%'):
                        return float(value.strip('%'))
                    return float(value)
                except (ValueError, TypeError):
                    return float('-inf') if not self.sort_reverse else float('inf')
            if col_name in ["post_date", "last_record"]:
                try:
                    if re.match(r"\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}", str(value)):
                        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    elif re.match(r"\d{4}-\d{2}-\d{2}", str(value)):
                        return datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    else:
                        return datetime.min.replace(tzinfo=timezone.utc) if not self.sort_reverse else datetime.max.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    return datetime.min.replace(tzinfo=timezone.utc) if not self.sort_reverse else datetime.max.replace(tzinfo=timezone.utc)
            return value

        self.scraped_data_for_table.sort(key=lambda item: _get_sort_value(item, col), reverse=self.sort_reverse)
        
        self._refresh_table_display()

        for c in self.columns:
            if c == col:
                arrow = " ↓" if self.sort_reverse else " ↑"
                self.tree.heading(c, text=c.replace("_", " ").title() + arrow)
            else:
                self.tree.heading(c, text=c.replace("_", " ").title())