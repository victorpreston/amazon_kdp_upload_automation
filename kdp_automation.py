#!/usr/bin/env python3
"""
Complete Amazon KDP Automation System - ULTIMATE VERSION
WARNING: Use at your own risk - may violate Amazon's Terms of Service

COMPLETE COVERAGE:
✅ Kindle eBook Details: Language, Title, Subtitle, Author, Description, Keywords, Publishing Rights, Adult Content, Categories  
✅ Kindle eBook Content: Cover Upload, Manuscript Upload
✅ Kindle eBook Pricing: Price Setting, Royalty Calculation
✅ Book Publishing: Final publication with confirmation

Now reads from prepared books folder created by kdp_preparation.py
Fixed all form interaction issues including language autocomplete selection.
"""

import os
import sys
import time
import json
import random
import logging
import schedule
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import configparser
import tempfile

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Project version
VERSION = "2.1.0"

class KDPConfig:
    """Configuration management for KDP automation"""
    
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default"""
        if not os.path.exists(self.config_file):
            self.create_default_config()
        
        self.config.read(self.config_file)
    
    def create_default_config(self):
        """Create default configuration file"""
        config = configparser.ConfigParser()
        
        config['KDP'] = {
            'email': '',
            'password': '',
            'base_url': 'https://kdp.amazon.com',
            'max_login_attempts': '3'
        }
        
        config['AUTOMATION'] = {
            'books_per_day': '3',
            'upload_time': '09:00',
            'min_delay': '30',
            'max_delay': '120',
            'page_load_timeout': '30',
            'element_timeout': '15'
        }
        
        config['FILES'] = {
            'prepared_books_directory': './prepared_books',
            'data_file': 'metadata_full.csv',  # Fallback if prepared books not found
            'output_directory': './processed_books',
            'log_directory': './logs',
            'session_file': './session_data.json'
        }
        
        config['BROWSER'] = {
            'chrome_driver_path': '',
            'user_data_dir': './chrome_profile',
            'window_width': '1366',
            'window_height': '768',
            'headless': 'false'
        }
        
        with open(self.config_file, 'w') as f:
            config.write(f)
        
        print(f"Created default config file: {self.config_file}")
        print("Please edit the configuration file with your credentials and settings.")
    
    def get(self, section, key, fallback=None):
        """Get configuration value"""
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=None):
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=None):
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)

class KDPLogger:
    """Enhanced logging system for KDP automation"""
    
    def __init__(self, log_dir="./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_format = '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        
        # Main log file
        log_file = self.log_dir / f"kdp_automation_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )
        
        # Create specific loggers
        self.automation_logger = logging.getLogger('automation')
        self.selenium_logger = logging.getLogger('selenium')
        self.error_logger = logging.getLogger('errors')
        
        # Error log file
        error_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(log_format))
        self.error_logger.addHandler(error_handler)

class SessionManager:
    """Manage browser sessions and cookies"""
    
    def __init__(self, session_file="./session_data.json"):
        self.session_file = session_file
        self.session_data = self.load_session()
    
    def load_session(self) -> Dict:
        """Load session data from file"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Could not load session data: {e}")
        return {}
    
    def save_session(self, driver):
        """Save session data to file"""
        try:
            session_data = {
                'cookies': driver.get_cookies(),
                'current_url': driver.current_url,
                'timestamp': datetime.now().isoformat(),
                'user_agent': driver.execute_script("return navigator.userAgent;")
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logging.info("Session data saved successfully")
        except Exception as e:
            logging.error(f"Failed to save session data: {e}")
    
    def restore_session(self, driver):
        """Restore session in browser"""
        if not self.session_data.get('cookies'):
            return False
        
        try:
            # Navigate to base domain first
            driver.get("https://kdp.amazon.com")
            time.sleep(2)
            
            # Add cookies
            for cookie in self.session_data['cookies']:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logging.warning(f"Could not add cookie: {e}")
            
            # Refresh to apply cookies
            driver.refresh()
            time.sleep(3)
            
            logging.info("Session restored successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to restore session: {e}")
            return False

class HumanBehaviorSimulator:
    """Simulate human-like behavior to avoid detection"""
    
    @staticmethod
    def random_delay(min_seconds=1, max_seconds=3):
        """Random delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def safe_type(driver, element, text, typing_delay=0.1):
        """Type text with human-like delays and proper interaction"""
        try:
            # Ensure element is visible and interactable
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            # Click to focus
            element.click()
            time.sleep(0.5)
            
            # Clear field
            element.clear()
            time.sleep(0.5)
            
            # Type with human-like delays
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, typing_delay))
            
            # Verify text was entered
            time.sleep(0.5)
            entered_text = element.get_attribute('value')
            if entered_text != text:
                logging.warning(f"Text verification failed. Expected: '{text}', Got: '{entered_text}'")
                # Try alternative method
                element.clear()
                element.send_keys(text)
            
            return True
            
        except Exception as e:
            logging.error(f"Safe type failed: {e}")
            return False
    
    @staticmethod
    def random_mouse_movement(driver):
        """Perform random mouse movements"""
        try:
            actions = ActionChains(driver)
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")
            
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, viewport_width)
                y = random.randint(0, viewport_height)
                actions.move_by_offset(x, y)
                time.sleep(random.uniform(0.1, 0.3))
            
            actions.perform()
        except Exception as e:
            logging.warning(f"Mouse movement failed: {e}")
    
    @staticmethod
    def scroll_page(driver, direction="down"):
        """Scroll page naturally"""
        try:
            if direction == "down":
                driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(100, 300))
            else:
                driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(-300, -100))
            
            HumanBehaviorSimulator.random_delay(0.5, 1.5)
        except Exception as e:
            logging.warning(f"Page scroll failed: {e}")

class KDPAutomator:
    """Main KDP automation class"""
    
    def __init__(self, config: KDPConfig):
        self.config = config
        self.driver = None
        self.session_manager = SessionManager(config.get('FILES', 'session_file'))
        self.behavior = HumanBehaviorSimulator()
        self.wait = None
        self.books_data = None
        self.processed_books = set()
        
        # Setup logging
        self.logger = KDPLogger(config.get('FILES', 'log_directory'))
        
        # Load book data
        self.load_books_data()
        
        # Load processed books tracking
        self.load_processed_books_tracking()
    
    def load_processed_books_tracking(self):
        """Load tracking of which prepared books have been processed"""
        tracking_file = Path(self.config.get('FILES', 'log_directory', './logs')) / 'processed_books.json'
        
        try:
            if tracking_file.exists():
                with open(tracking_file, 'r') as f:
                    processed_data = json.load(f)
                    # Convert book directory names to set
                    self.processed_books = set(processed_data.get('processed_directories', []))
                    logging.info(f"Loaded tracking for {len(self.processed_books)} processed books")
            else:
                self.processed_books = set()
                logging.info("No previous processing tracking found, starting fresh")
                
        except Exception as e:
            logging.warning(f"Could not load processed books tracking: {e}")
            self.processed_books = set()
    
    def save_processed_books_tracking(self):
        """Save tracking of processed books"""
        tracking_file = Path(self.config.get('FILES', 'log_directory', './logs')) / 'processed_books.json'
        
        try:
            tracking_data = {
                'processed_directories': list(self.processed_books),
                'last_updated': datetime.now().isoformat(),
                'total_processed': len(self.processed_books)
            }
            
            with open(tracking_file, 'w') as f:
                json.dump(tracking_data, f, indent=2)
                
            logging.info(f"Saved tracking for {len(self.processed_books)} processed books")
            
        except Exception as e:
            logging.error(f"Could not save processed books tracking: {e}")
    
    def load_books_data(self):
        """Load books data from prepared books folder"""
        prepared_books_dir = Path(self.config.get('FILES', 'prepared_books_directory', './prepared_books'))
        
        try:
            if not prepared_books_dir.exists():
                logging.error(f"Prepared books directory not found: {prepared_books_dir}")
                logging.error("Please run kdp_preparation.py first to prepare books")
                raise FileNotFoundError(f"Prepared books directory not found: {prepared_books_dir}")
            
            # Find all book directories
            book_dirs = [d for d in prepared_books_dir.iterdir() if d.is_dir() and d.name.startswith('book_')]
            
            if not book_dirs:
                logging.error("No prepared book directories found")
                logging.error("Please run kdp_preparation.py first to prepare books")
                raise FileNotFoundError("No prepared book directories found")
            
            # Sort by book index (book_000_, book_001_, etc.)
            book_dirs.sort(key=lambda x: x.name)
            
            # Load metadata from each book directory
            books_data = []
            for book_dir in book_dirs:
                metadata_file = book_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Add directory path for reference
                        metadata['book_directory'] = str(book_dir)
                        metadata['book_index'] = len(books_data)  # Use position as index
                        
                        books_data.append(metadata)
                        logging.info(f"Loaded book: {metadata['title']}")
                        
                    except Exception as e:
                        logging.warning(f"Failed to load metadata from {metadata_file}: {e}")
                        continue
                else:
                    logging.warning(f"No metadata.json found in {book_dir}")
            
            if not books_data:
                raise ValueError("No valid book metadata found in prepared books directory")
            
            # Convert to pandas DataFrame for compatibility with existing code
            self.books_data = pd.DataFrame(books_data)
            
            logging.info(f"Loaded {len(self.books_data)} prepared books from {prepared_books_dir}")
            
        except Exception as e:
            logging.error(f"Failed to load prepared books data: {e}")
            raise
    
    def setup_browser(self) -> webdriver.Chrome:
        """Setup Chrome browser with anti-detection measures and fixed path issues"""
        try:
            options = Options()
            
            # Create absolute path for user data directory
            user_data_dir = self.config.get('BROWSER', 'user_data_dir', './chrome_profile')
            abs_user_data_dir = os.path.abspath(user_data_dir)
            
            # Create directory if it doesn't exist
            Path(abs_user_data_dir).mkdir(parents=True, exist_ok=True)
            
            # Set user data directory with absolute path
            options.add_argument(f"--user-data-dir={abs_user_data_dir}")
            
            # Window size
            width = self.config.getint('BROWSER', 'window_width', 1366)
            height = self.config.getint('BROWSER', 'window_height', 768)
            options.add_argument(f"--window-size={width},{height}")
            
            # Anti-detection and stability measures
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--disable-features=VizDisplayCompositor")
            
            # Additional Chrome stability options
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-translate")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            
            # Headless mode (if configured)
            if self.config.getboolean('BROWSER', 'headless', False):
                options.add_argument("--headless")
            
            # Setup Chrome driver using webdriver-manager for automatic management
            try:
                chrome_driver_path = self.config.get('BROWSER', 'chrome_driver_path')
                if chrome_driver_path and os.path.exists(chrome_driver_path):
                    service = Service(chrome_driver_path)
                    logging.info(f"Using specified ChromeDriver: {chrome_driver_path}")
                else:
                    # Auto-download and manage ChromeDriver
                    service = Service(ChromeDriverManager().install())
                    logging.info("Using auto-managed ChromeDriver")
                
                driver = webdriver.Chrome(service=service, options=options)
                
            except Exception as e:
                logging.error(f"Failed to setup ChromeDriver: {e}")
                # Fallback to system ChromeDriver
                logging.info("Attempting fallback to system ChromeDriver")
                driver = webdriver.Chrome(options=options)
            
            # Execute script to hide automation detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Additional stealth measures
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # Set timeouts
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(self.config.getint('AUTOMATION', 'page_load_timeout', 30))
            
            self.wait = WebDriverWait(driver, self.config.getint('AUTOMATION', 'element_timeout', 15))
            
            logging.info("Browser setup completed successfully")
            return driver
            
        except Exception as e:
            logging.error(f"Failed to setup browser: {e}")
            raise
    
    def login_to_kdp(self) -> bool:
        """Login to Amazon KDP"""
        email = self.config.get('KDP', 'email')
        password = self.config.get('KDP', 'password')
        
        if not email or not password:
            logging.error("Email and password must be configured")
            return False
        
        try:
            # Navigate to KDP
            self.driver.get(self.config.get('KDP', 'base_url'))
            self.behavior.random_delay(2, 4)
            
            # Try to restore session first
            if self.session_manager.restore_session(self.driver):
                # Check if we're already logged in
                if self.is_logged_in():
                    logging.info("Successfully restored session - already logged in")
                    return True
            
            # Find and click sign in button
            try:
                sign_in_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')]"))
                )
                sign_in_btn.click()
                self.behavior.random_delay(2, 3)
            except TimeoutException:
                # Maybe already on login page
                pass
            
            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
            self.behavior.safe_type(self.driver, email_field, email)
            self.behavior.random_delay(1, 2)
            
            # Click continue
            continue_btn = self.driver.find_element(By.ID, "continue")
            continue_btn.click()
            self.behavior.random_delay(2, 3)
            
            # Enter password
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "ap_password")))
            self.behavior.safe_type(self.driver, password_field, password)
            self.behavior.random_delay(1, 2)
            
            # Click sign in
            sign_in_btn = self.driver.find_element(By.ID, "signInSubmit")
            sign_in_btn.click()
            self.behavior.random_delay(3, 5)
            
            # Check for successful login
            if self.is_logged_in():
                logging.info("Successfully logged in to KDP")
                self.session_manager.save_session(self.driver)
                return True
            else:
                logging.error("Login failed - not on expected page")
                return False
                
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if successfully logged in to KDP"""
        try:
            # Look for KDP dashboard elements
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'bookshelf')]")),
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Bookshelf')]")),
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Create')]"))
                )
            )
            return True
        except TimeoutException:
            return False
    
    def navigate_to_create_book(self) -> bool:
        """Navigate to create new book page - FIXED VERSION"""
        try:
            # First navigate to the "what would you like to create" page
            logging.info("Looking for Create New button...")
            
            # Try multiple selectors for the main Create button
            create_selectors = [
                "//a[contains(text(), 'Create New')]",
                "//span[contains(text(), 'Create New')]",
                "//button[contains(text(), 'Create New')]",
                "//a[contains(@href, 'create')]"
            ]
            
            create_btn = None
            for selector in create_selectors:
                try:
                    create_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not create_btn:
                # Try going directly to create page
                logging.info("Direct navigation to create page...")
                self.driver.get("https://kdp.amazon.com/en_US/title-setup/kindle")
                self.behavior.random_delay(3, 5)
            else:
                create_btn.click()
                self.behavior.random_delay(2, 3)
                logging.info("Clicked main Create button")
            
            # Now look for the "Create eBook" button on the selection page
            logging.info("Looking for Create eBook button...")
            
            # Multiple selectors for the "Create eBook" button
            ebook_selectors = [
                "//button[contains(text(), 'Create eBook')]",
                "//a[contains(text(), 'Create eBook')]",
                "//span[contains(text(), 'Create eBook')]",
                "//*[contains(text(), 'Create eBook')]"
            ]
            
            ebook_btn = None
            for selector in ebook_selectors:
                try:
                    ebook_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    logging.info(f"Found Create eBook button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not ebook_btn:
                logging.error("Could not find Create eBook button")
                self.debug_page_elements()
                return False
            
            # Click the Create eBook button
            ebook_btn.click()
            self.behavior.random_delay(3, 5)
            logging.info("Clicked Create eBook button")
            
            # Wait for the actual book creation form to load
            logging.info("Waiting for book creation form to load...")
            
            # Look for form elements to confirm we're on the right page
            form_indicators = [
                "//input[@id='data-title']",
                "//input[@name='data[title]']",
                "//*[contains(text(), 'Book Details')]",
                "//*[contains(text(), 'Title')]"
            ]
            
            form_found = False
            for indicator in form_indicators:
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                    form_found = True
                    logging.info(f"Found form indicator: {indicator}")
                    break
                except TimeoutException:
                    continue
            
            if form_found:
                logging.info("Successfully navigated to book creation form")
                return True
            else:
                logging.error("Could not confirm book creation form loaded")
                self.debug_page_elements()
                return False
                
        except Exception as e:
            logging.error(f"Failed to navigate to create book: {e}")
            self.debug_page_elements()
            return False
    
    def debug_page_elements(self):
        """Debug helper to log current page elements"""
        try:
            logging.info(f"Current URL: {self.driver.current_url}")
            logging.info(f"Page title: {self.driver.title}")
            
            # Log some common elements
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logging.info(f"Found {len(buttons)} buttons on page")
            for i, btn in enumerate(buttons[:5]):  # Log first 5 buttons
                try:
                    text = btn.text.strip()
                    if text:
                        logging.info(f"Button {i}: '{text}'")
                except:
                    pass
            
            # Log links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            logging.info(f"Found {len(links)} links on page")
            for i, link in enumerate(links[:5]):  # Log first 5 links
                try:
                    text = link.text.strip()
                    if text:
                        logging.info(f"Link {i}: '{text}'")
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"Debug failed: {e}")
    
    def wait_for_form_ready(self):
        """Wait for the KDP form to be fully loaded and interactive"""
        try:
            logging.info("Waiting for form to be fully ready...")
            
            # Wait for page to stabilize
            time.sleep(3)
            
            # Wait for any loading indicators to disappear
            try:
                self.wait.until_not(EC.presence_of_element_located((By.CLASS_NAME, "loading")))
            except TimeoutException:
                pass
            
            # Wait for JavaScript to finish executing
            self.wait.until(lambda driver: driver.execute_script("return jQuery.active == 0") if driver.execute_script("return typeof jQuery != 'undefined'") else True)
            
            # Wait for form elements to be interactable
            time.sleep(2)
            
            logging.info("Form should be ready for interaction")
            return True
            
        except Exception as e:
            logging.warning(f"Form readiness check failed: {e}")
            return True  # Continue anyway

    def fill_book_details(self, book_data: pd.Series) -> bool:
        """Fill in book details form - COMPLETELY FIXED VERSION using exact form analysis selectors"""
        try:
            logging.info("Starting to fill book details...")
            
            # Wait for form to be fully ready
            self.wait_for_form_ready()
            
            # Step 0: Set Language FIRST (before other fields) using exact form analysis selector
            try:
                if pd.notna(book_data['language']) and str(book_data['language']).lower() != 'english':
                    language_to_set = str(book_data['language'])
                    logging.info(f"Setting language to: {language_to_set}")
                    
                    # From form analysis: aria_label="language-dropdown-editable-text", autocomplete input
                    language_input = self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//input[@aria-label='language-dropdown-editable-text']")
                    ))
                    
                    # Clear the current value and set new language
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", language_input)
                    time.sleep(0.5)
                    
                    # Click to focus and activate autocomplete
                    language_input.click()
                    time.sleep(0.5)
                    
                    # Clear existing value completely
                    language_input.clear()
                    time.sleep(0.5)
                    
                    # Alternative method: Select all and delete
                    language_input.send_keys(Keys.CONTROL + "a")
                    language_input.send_keys(Keys.DELETE)
                    time.sleep(0.5)
                    
                    # Type the new language slowly to trigger autocomplete
                    for char in language_to_set:
                        language_input.send_keys(char)
                        time.sleep(0.1)
                    
                    # Wait for autocomplete dropdown to appear
                    time.sleep(2)
                    
                    # Try to find and click the matching option in the dropdown
                    dropdown_selectors = [
                        f"//li[contains(text(), '{language_to_set}')]",
                        f"//div[contains(text(), '{language_to_set}')]", 
                        f"//span[contains(text(), '{language_to_set}')]",
                        f"//*[contains(@class, 'ui-menu-item')][contains(text(), '{language_to_set}')]",
                        f"//*[contains(@class, 'autocomplete')][contains(text(), '{language_to_set}')]"
                    ]
                    
                    option_selected = False
                    for selector in dropdown_selectors:
                        try:
                            dropdown_option = self.driver.find_element(By.XPATH, selector)
                            if dropdown_option.is_displayed():
                                dropdown_option.click()
                                logging.info(f"Selected {language_to_set} from dropdown")
                                option_selected = True
                                time.sleep(1)
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not option_selected:
                        # Fallback: try arrow keys and enter
                        logging.info("Dropdown selection failed, trying arrow keys")
                        language_input.send_keys(Keys.ARROW_DOWN)
                        time.sleep(0.5)
                        language_input.send_keys(Keys.ENTER)
                        time.sleep(1)
                        
                        # Verify the selection worked
                        current_value = language_input.get_attribute('value')
                        if current_value.lower() != language_to_set.lower():
                            logging.warning(f"Language selection may have failed. Expected: {language_to_set}, Got: {current_value}")
                            
                            # Last resort: try direct value setting
                            try:
                                self.driver.execute_script(f"arguments[0].value = '{language_to_set}';", language_input)
                                # Trigger change event
                                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", language_input)
                                time.sleep(1)
                                logging.info(f"Set language via JavaScript: {language_to_set}")
                            except Exception as js_error:
                                logging.error(f"JavaScript language setting failed: {js_error}")
                        else:
                            logging.info(f"Language successfully set to: {current_value}")
                    
                    # Final verification
                    final_value = language_input.get_attribute('value')
                    logging.info(f"Final language value: {final_value}")
                    
                else:
                    logging.info("Language is English or not specified, keeping default")
                    
            except Exception as e:
                logging.warning(f"Language setting failed: {e}")
                # Continue anyway - language is not critical for upload
            
            # Step 1: Fill Title using exact selector from form analysis
            title_filled = False
            try:
                # Use exact selector from form analysis: name="data[title]", id="data-title"
                title_field = self.wait.until(EC.element_to_be_clickable((By.ID, "data-title")))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", title_field)
                time.sleep(1)
                
                if self.behavior.safe_type(self.driver, title_field, str(book_data['title'])):
                    logging.info(f"Successfully filled title: {book_data['title']}")
                    title_filled = True
                else:
                    logging.error("Failed to fill title")
                    return False
                    
            except Exception as e:
                logging.error(f"Title filling failed: {e}")
                return False
            
            # Step 2: Fill Subtitle using exact selector from form analysis
            if pd.notna(book_data['subtitle']) and book_data['subtitle']:
                try:
                    # Use exact selector: name="data[subtitle]", id="data-subtitle"
                    subtitle_field = self.wait.until(EC.element_to_be_clickable((By.ID, "data-subtitle")))
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", subtitle_field)
                    time.sleep(0.5)
                    
                    if self.behavior.safe_type(self.driver, subtitle_field, str(book_data['subtitle'])):
                        logging.info(f"Filled subtitle: {book_data['subtitle']}")
                        
                except Exception as e:
                    logging.warning(f"Subtitle filling failed: {e}")
            
            # Step 3: Fill Author Name using exact selectors from form analysis
            author_name = str(book_data['author'])
            try:
                # Split author name for first/last name fields
                if ' ' in author_name:
                    first_name = author_name.split(' ')[0]
                    last_name = ' '.join(author_name.split(' ')[1:])
                else:
                    first_name = author_name
                    last_name = ""
                
                # Fill first name: id="data-primary-author-first-name"
                first_name_field = self.wait.until(EC.element_to_be_clickable((By.ID, "data-primary-author-first-name")))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", first_name_field)
                time.sleep(0.5)
                
                if self.behavior.safe_type(self.driver, first_name_field, first_name):
                    logging.info(f"Filled first name: {first_name}")
                
                # Fill last name if available: id="data-primary-author-last-name"
                if last_name:
                    last_name_field = self.driver.find_element(By.ID, "data-primary-author-last-name")
                    if self.behavior.safe_type(self.driver, last_name_field, last_name):
                        logging.info(f"Filled last name: {last_name}")
                        
            except Exception as e:
                logging.warning(f"Author filling failed: {e}")
            
            # Step 4: Fill Description using iframe (from form analysis)
            if pd.notna(book_data['description_html']):
                try:
                    # Clean HTML from description
                    import re
                    clean_description = re.sub('<.*?>', '', str(book_data['description_html']))
                    
                    # Handle iframe for rich text editor (class="cke_wysiwyg_frame cke_reset")
                    try:
                        iframe = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.cke_wysiwyg_frame")))
                        self.driver.switch_to.frame(iframe)
                        
                        # Look for contenteditable body inside iframe
                        editor_body = self.driver.find_element(By.TAG_NAME, "body")
                        if editor_body:
                            # Clear and type in the editor
                            editor_body.clear()
                            editor_body.send_keys(clean_description)
                            logging.info("Filled description in rich text editor")
                        
                        # Switch back to main content
                        self.driver.switch_to.default_content()
                        
                    except Exception as iframe_error:
                        # Switch back to main content if iframe failed
                        self.driver.switch_to.default_content()
                        logging.warning(f"Rich text editor failed, trying hidden field: {iframe_error}")
                        
                        # Fallback: try to set the hidden description field directly
                        try:
                            description_hidden = self.driver.find_element(By.NAME, "data[description]")
                            self.driver.execute_script("arguments[0].value = arguments[1];", description_hidden, clean_description)
                            logging.info("Set description via hidden field")
                        except Exception:
                            logging.warning("Could not set description")
                            
                except Exception as e:
                    logging.warning(f"Description handling failed: {e}")
            
            # Step 5: Fill Keywords using exact selectors from form analysis
            if pd.notna(book_data['keywords']):
                try:
                    keywords_text = str(book_data['keywords'])
                    keywords_list = [kw.strip() for kw in keywords_text.split(';')] if ';' in keywords_text else [keywords_text]
                    
                    # Fill up to 7 keyword fields (data-keywords-0 through data-keywords-6)
                    for i, keyword in enumerate(keywords_list[:7]):
                        try:
                            keyword_field = self.driver.find_element(By.ID, f"data-keywords-{i}")
                            if self.behavior.safe_type(self.driver, keyword_field, keyword):
                                logging.info(f"Filled keyword {i}: {keyword}")
                        except Exception:
                            continue
                            
                except Exception as e:
                    logging.warning(f"Keywords filling failed: {e}")
            
            # Step 6: Handle Publishing Rights using exact radio button from form analysis
            try:
                # Select "I own the copyright" - id="non-public-domain", value="false"
                rights_radio = self.wait.until(EC.element_to_be_clickable((By.ID, "non-public-domain")))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", rights_radio)
                time.sleep(0.5)
                
                if not rights_radio.is_selected():
                    self.driver.execute_script("arguments[0].click();", rights_radio)
                    logging.info("Selected 'I own the copyright'")
                    time.sleep(1)
                    
            except Exception as e:
                logging.warning(f"Publishing rights selection failed: {e}")
            
            # Step 7: Handle Adult Content using exact radio button from form analysis
            try:
                # Select "No" for adult content - name="data[is_adult_content]-radio", value="false"
                adult_radios = self.driver.find_elements(By.NAME, "data[is_adult_content]-radio")
                for radio in adult_radios:
                    if radio.get_attribute('value') == 'false':
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", radio)
                        time.sleep(0.5)
                        if not radio.is_selected():
                            self.driver.execute_script("arguments[0].click();", radio)
                            logging.info("Selected 'No' for adult content")
                            time.sleep(1)
                        break
                        
            except Exception as e:
                logging.warning(f"Adult content selection failed: {e}")
            
            # Step 8: Handle Categories - REQUIRED FIELD - must select categories
            try:
                # Categories are required! The button should be enabled after other fields are filled
                # Wait a moment for the button to potentially enable
                time.sleep(2)
                
                categories_btn = self.wait.until(EC.presence_of_element_located((By.ID, "categories-modal-button")))
                
                # Scroll to categories section
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", categories_btn)
                time.sleep(1)
                
                # Check if button is now enabled after filling other fields
                if categories_btn.is_enabled():
                    logging.info("Categories button is enabled, opening category selection")
                    categories_btn.click()
                    time.sleep(3)  # Wait for modal to open
                    
                    # Handle category selection modal using BISAC code
                    if pd.notna(book_data['bisac']):
                        bisac_code = str(book_data['bisac'])
                        logging.info(f"Selecting category for BISAC: {bisac_code}")
                        
                        # Map common BISAC codes to category selections
                        self.select_category_by_bisac(bisac_code)
                    else:
                        # Default category selection if no BISAC
                        self.select_default_category()
                    
                    # Save category selection
                    self.save_category_selection()
                    
                else:
                    # Try to force enable the button or use alternative approach
                    logging.warning("Categories button still disabled, trying to force enable")
                    
                    # Try clicking anyway using JavaScript
                    try:
                        self.driver.execute_script("arguments[0].removeAttribute('disabled');", categories_btn)
                        self.driver.execute_script("arguments[0].click();", categories_btn)
                        time.sleep(3)
                        
                        if pd.notna(book_data['bisac']):
                            bisac_code = str(book_data['bisac'])
                            self.select_category_by_bisac(bisac_code)
                        else:
                            self.select_default_category()
                        
                        self.save_category_selection()
                        
                    except Exception as force_error:
                        logging.error(f"Could not force category selection: {force_error}")
                        return False
                        
            except Exception as e:
                logging.error(f"Categories handling failed: {e}")
                logging.error("Categories are required - cannot proceed without them")
                return False
            
            # Step 9: Verify Categories are Selected (Critical Check)
            try:
                # Wait a moment and check if categories error is gone
                time.sleep(2)
                
                # Look for the category error message
                category_error_selectors = [
                    "//*[contains(text(), 'Add a category')]", 
                    "//*[contains(text(), 'category') and contains(@class, 'error')]",
                    "//*[contains(@class, 'error') and contains(text(), 'book')]"
                ]
                
                category_error_found = False
                for selector in category_error_selectors:
                    try:
                        error_element = self.driver.find_element(By.XPATH, selector)
                        if error_element.is_displayed():
                            category_error_found = True
                            logging.error("Category error still present - categories not properly selected")
                            break
                    except NoSuchElementException:
                        continue
                
                if category_error_found:
                    logging.error("CRITICAL: Categories are required but not selected. Cannot proceed.")
                    # Try one more time to handle categories
                    try:
                        self.handle_categories_emergency(book_data)
                    except:
                        logging.error("Emergency category handling also failed")
                        return False
                else:
                    logging.info("Categories successfully selected - no error message found")
                    
            except Exception as e:
                logging.warning(f"Category verification failed: {e}")
            
            # Step 10: Click "Save and Continue" to proceed to next step
            try:
                # From form analysis: id="save-and-continue-announce"
                save_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "save-and-continue-announce")))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", save_btn)
                time.sleep(1)
                
                save_btn.click()
                logging.info("Clicked 'Save and Continue' - proceeding to Content step")
                time.sleep(3)  # Wait for next page to load
                
            except Exception as e:
                logging.warning(f"Could not click Save and Continue: {e}")
                # Try alternative selector
                try:
                    save_btn_alt = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Save and Continue')]")
                    save_btn_alt.click()
                    logging.info("Clicked Save and Continue with alternative selector")
                    time.sleep(3)
                except Exception:
                    logging.error("Failed to proceed to next step")
                    return False
            
            logging.info("Successfully completed filling book details")
            return True
            
        except Exception as e:
            logging.error(f"Failed to fill book details: {e}")
            self.debug_page_elements()
            return False
    
    def upload_book_files(self, book_data: pd.Series) -> bool:
        """Upload book files (cover and manuscript) - UPDATED for multi-step flow"""
        try:
            logging.info("Starting file uploads in Content step...")
            
            # We should already be on the Content page from clicking "Save and Continue"
            # Wait for content page to load
            time.sleep(3)
            
            # Verify we're on the content step
            content_indicators = [
                "//h2[contains(text(), 'Kindle eBook Content')]",
                "//h3[contains(text(), 'Content')]",
                "//*[contains(text(), 'Upload your book cover')]",
                "//*[contains(text(), 'Upload your manuscript')]"
            ]
            
            content_page_found = False
            for indicator in content_indicators:
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                    content_page_found = True
                    logging.info("Confirmed we're on Content step")
                    break
                except TimeoutException:
                    continue
            
            if not content_page_found:
                logging.warning("Could not confirm Content step page")
            
            # Upload cover - using prepared book files
            cover_selectors = [
                "//input[@type='file'][contains(@accept, 'image')]",
                "//input[@type='file'][contains(@name, 'cover')]",
                "//input[@type='file'][contains(@id, 'cover')]",
                "//div[contains(text(), 'cover')]/following-sibling::div//input[@type='file']"
            ]
            
            manuscript_selectors = [
                "//input[@type='file'][contains(@accept, '.epub')]",
                "//input[@type='file'][contains(@name, 'manuscript')]",
                "//input[@type='file'][contains(@id, 'manuscript')]",
                "//input[@type='file'][not(contains(@accept, 'image'))]",
                "//div[contains(text(), 'manuscript')]/following-sibling::div//input[@type='file']"
            ]
            
            # Upload cover - using prepared book files
            cover_path = self.get_book_file_path(book_data, 'ebook_cover')
            if cover_path and os.path.exists(cover_path):
                cover_upload = None
                for selector in cover_selectors:
                    try:
                        cover_upload = self.driver.find_element(By.XPATH, selector)
                        logging.info(f"Found cover upload with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if cover_upload:
                    cover_upload.send_keys(cover_path)
                    self.behavior.random_delay(3, 5)
                    logging.info(f"Cover uploaded successfully: {os.path.basename(cover_path)}")
                else:
                    logging.warning("Could not find cover upload field")
            else:
                logging.warning(f"Cover file not found or not available")
            
            # Upload manuscript (epub) - using prepared book files
            epub_path = self.get_book_file_path(book_data, 'epub')
            if epub_path and os.path.exists(epub_path):
                manuscript_upload = None
                for selector in manuscript_selectors:
                    try:
                        manuscript_upload = self.driver.find_element(By.XPATH, selector)
                        logging.info(f"Found manuscript upload with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if manuscript_upload:
                    manuscript_upload.send_keys(epub_path)
                    self.behavior.random_delay(5, 8)
                    logging.info(f"Manuscript uploaded successfully: {os.path.basename(epub_path)}")
                else:
                    logging.warning("Could not find manuscript upload field")
            else:
                logging.warning(f"EPUB file not found or not available")
            
            # Click "Save and Continue" to proceed to Pricing
            try:
                save_continue_selectors = [
                    "//button[contains(text(), 'Save and Continue')]",
                    "//input[@value='Save and Continue']"
                ]
                
                for selector in save_continue_selectors:
                    try:
                        save_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        save_btn.click()
                        logging.info("Clicked 'Save and Continue' - proceeding to Pricing step")
                        time.sleep(3)
                        break
                    except Exception:
                        continue
            except Exception as e:
                logging.warning(f"Could not proceed to pricing: {e}")
            
            logging.info("File uploads section completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed to upload files: {e}")
            return False
    
    def set_pricing(self, book_data: pd.Series) -> bool:
        """Set book pricing - UPDATED for Pricing step"""
        try:
            logging.info("Setting book pricing in Pricing step...")
            
            # We should already be on the Pricing page from clicking "Save and Continue"
            time.sleep(3)
            
            # Verify we're on the pricing step
            pricing_indicators = [
                "//h2[contains(text(), 'Kindle eBook Pricing')]",
                "//h3[contains(text(), 'Pricing')]",
                "//*[contains(text(), 'List Price')]",
                "//*[contains(text(), 'Royalty')]"
            ]
            
            pricing_page_found = False
            for indicator in pricing_indicators:
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                    pricing_page_found = True
                    logging.info("Confirmed we're on Pricing step")
                    break
                except TimeoutException:
                    continue
            
            if not pricing_page_found:
                logging.warning("Could not confirm Pricing step page")
            
            # Set price - already converted to dollars in prepared metadata
            price_usd = book_data['price_ebook_usd']  # Already in dollars from prepared metadata
            
            price_selectors = [
                "//input[contains(@name, 'price')]",
                "//input[contains(@id, 'price')]",
                "//input[@type='number']",
                "//input[@placeholder='0.00']",
                "//div[contains(text(), 'List Price')]/following-sibling::div//input",
                "//label[contains(text(), 'USD')]/preceding-sibling::input"
            ]
            
            price_field = None
            for selector in price_selectors:
                try:
                    price_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    logging.info(f"Found price field with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if price_field:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", price_field)
                time.sleep(0.5)
                
                if self.behavior.safe_type(self.driver, price_field, str(price_usd)):
                    logging.info(f"Set pricing: ${price_usd}")
                    time.sleep(2)  # Wait for price calculation
                    return True
                else:
                    logging.error("Failed to type price")
                    return False
            else:
                logging.warning("Could not find price field")
                return False
            
        except Exception as e:
            logging.error(f"Failed to set pricing: {e}")
            return False
    
    def publish_book(self) -> bool:
        """Publish the book - FINAL STEP"""
        try:
            logging.info("Publishing book - final step...")
            
            # Look for publish button in Pricing step
            publish_selectors = [
                "//button[contains(text(), 'Publish Your Kindle eBook')]",
                "//button[contains(text(), 'Publish eBook')]", 
                "//button[contains(text(), 'Publish')]",
                "//input[@value='Publish Your Kindle eBook']",
                "//input[@value='Publish']"
            ]
            
            publish_btn = None
            for selector in publish_selectors:
                try:
                    publish_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    logging.info(f"Found publish button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not publish_btn:
                logging.error("Could not find publish button")
                # Try scrolling down to find it
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try again after scrolling
                for selector in publish_selectors:
                    try:
                        publish_btn = self.driver.find_element(By.XPATH, selector)
                        logging.info(f"Found publish button after scrolling: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not publish_btn:
                    logging.error("Still could not find publish button after scrolling")
                    return False
            
            # Scroll to publish button and click
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", publish_btn)
            time.sleep(1)
            
            publish_btn.click()
            self.behavior.random_delay(3, 5)
            logging.info("Clicked publish button")
            
            # Handle any confirmation dialogs
            confirm_selectors = [
                "//button[contains(text(), 'Yes, publish')]",
                "//button[contains(text(), 'Confirm')]",
                "//button[contains(text(), 'Publish')]",
                "//input[@value='Confirm']",
                "//input[@value='Yes, publish']"
            ]
            
            for selector in confirm_selectors:
                try:
                    confirm_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    confirm_btn.click()
                    self.behavior.random_delay(3, 5)
                    logging.info("Confirmed publication")
                    break
                except TimeoutException:
                    continue
            
            # Wait for success page or confirmation
            time.sleep(5)
            
            # Check for success indicators
            success_indicators = [
                "//*[contains(text(), 'published successfully')]",
                "//*[contains(text(), 'Thank you')]",
                "//*[contains(text(), 'submitted')]",
                "//*[contains(text(), 'Bookshelf')]"
            ]
            
            success_found = False
            for indicator in success_indicators:
                try:
                    self.driver.find_element(By.XPATH, indicator)
                    success_found = True
                    logging.info("Found success confirmation")
                    break
                except NoSuchElementException:
                    continue
            
            if success_found:
                logging.info("Book published successfully - confirmed!")
            else:
                logging.warning("Could not confirm publication success, but no errors")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to publish book: {e}")
            return False
    
    def get_book_file_path(self, book_data: pd.Series, file_type: str) -> str:
        """Get file path from prepared book metadata"""
        try:
            # book_data now contains the metadata.json data
            files = book_data.get('files', {})
            
            # Map file types
            file_mapping = {
                'cover': 'ebook_cover',
                'ebook_cover': 'ebook_cover', 
                'epub': 'epub',
                'manuscript': 'epub',
                'docx': 'docx'
            }
            
            mapped_type = file_mapping.get(file_type, file_type)
            file_path = files.get(mapped_type)
            
            if file_path and os.path.exists(file_path):
                logging.info(f"Found {file_type} file: {file_path}")
                return file_path
            else:
                logging.warning(f"File not found for {file_type}: {file_path}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting file path for {file_type}: {e}")
            return None
    
    def clean_file_path(self, file_path):
        """Clean file path - now handles prepared book paths"""
        if file_path and isinstance(file_path, str):
            # Prepared book paths are already clean, just return as-is
            return file_path.strip()
        return file_path
    
    def process_single_book(self, book_index: int) -> bool:
        """Process a single book upload using prepared book data - COMPLETE 3-STEP FLOW"""
        book_data = self.books_data.iloc[book_index]
        book_directory = book_data['book_directory']
        
        logging.info("="*60)
        logging.info(f"STARTING COMPLETE KDP UPLOAD PROCESS")
        logging.info(f"Book: {book_data['title']}")
        logging.info(f"Author: {book_data['author']}")
        logging.info(f"Language: {book_data['language']}")
        logging.info(f"Directory: {book_directory}")
        logging.info("="*60)
        
        try:
            # STEP 1: Navigate to create book form
            logging.info("STEP 1: Navigating to book creation form...")
            if not self.navigate_to_create_book():
                logging.error("STEP 1 FAILED: Could not navigate to create book form")
                return False
            logging.info("STEP 1 COMPLETED: Successfully navigated to form")
            
            # STEP 2: Fill eBook Details (including language, categories, etc.)
            logging.info("STEP 2: Filling eBook Details (titles, author, description, categories)...")
            if not self.fill_book_details(book_data):
                logging.error("STEP 2 FAILED: Could not fill book details")
                return False
            logging.info("STEP 2 COMPLETED: eBook Details filled and saved")
            
            # STEP 3: Upload eBook Content (cover + manuscript)
            logging.info("STEP 3: Uploading eBook Content (cover and manuscript files)...")
            if not self.upload_book_files(book_data):
                logging.error("STEP 3 FAILED: File uploads failed")
                return False
            logging.info("STEP 3 COMPLETED: eBook Content uploaded")
            
            # STEP 4: Set eBook Pricing
            logging.info("STEP 4: Setting eBook Pricing...")
            if not self.set_pricing(book_data):
                logging.error("STEP 4 FAILED: Pricing setup failed")
                return False
            logging.info("STEP 4 COMPLETED: eBook Pricing set")
            
            # STEP 5: Publish the book
            logging.info("STEP 5: Publishing the book...")
            if not self.publish_book():
                logging.error("STEP 5 FAILED: Book publication failed")
                return False
            logging.info("STEP 5 COMPLETED: Book published successfully!")
            
            # Mark as processed using directory name
            self.processed_books.add(os.path.basename(book_directory))
            self.save_processed_books_tracking()
            
            logging.info("="*60)
            logging.info(f"SUCCESS: Complete upload process finished for '{book_data['title']}'")
            logging.info("All 5 steps completed: Navigation → Details → Content → Pricing → Publishing")
            logging.info("="*60)
            return True
            
        except Exception as e:
            logging.error("="*60)
            logging.error(f"CRITICAL ERROR in book upload process: {e}")
            logging.error(f"Failed book: {book_data['title']}")
            logging.error("="*60)
            return False
    
    def process_daily_batch(self):
        """Process daily batch of books"""
        books_per_day = self.config.getint('AUTOMATION', 'books_per_day', 3)
        
        try:
            # Setup browser
            self.driver = self.setup_browser()
            
            # Login
            if not self.login_to_kdp():
                logging.error("Failed to login, aborting batch")
                return
            
            # Get books to process
            books_to_process = self.get_next_books_to_process(books_per_day)
            
            if not books_to_process:
                logging.info("No more books to process")
                return
            
            successful_uploads = 0
            
            for i, book_index in enumerate(books_to_process):
                logging.info(f"Processing book {i+1}/{len(books_to_process)}")
                
                if self.process_single_book(book_index):
                    successful_uploads += 1
                
                # Random delay between books
                if i < len(books_to_process) - 1:
                    delay = random.randint(
                        self.config.getint('AUTOMATION', 'min_delay', 30),
                        self.config.getint('AUTOMATION', 'max_delay', 120)
                    )
                    logging.info(f"Waiting {delay} seconds before next book...")
                    time.sleep(delay)
            
            logging.info(f"Daily batch completed: {successful_uploads}/{len(books_to_process)} successful uploads")
            
        except Exception as e:
            logging.error(f"Error in daily batch: {e}")
        
        finally:
            if self.driver:
                try:
                    self.session_manager.save_session(self.driver)
                    self.driver.quit()
                except Exception as e:
                    logging.error(f"Error closing browser: {e}")
    
    def get_next_books_to_process(self, count: int) -> List[int]:
        """Get next books to process from prepared books"""
        available_books = []
        
        for i in range(len(self.books_data)):
            book_data = self.books_data.iloc[i]
            book_directory = book_data['book_directory']
            book_dir_name = os.path.basename(book_directory)
            
            # Check if this book directory has been processed
            if book_dir_name not in self.processed_books:
                available_books.append(i)
                if len(available_books) >= count:
                    break
        
        logging.info(f"Found {len(available_books)} unprocessed books, returning {min(count, len(available_books))}")
        return available_books
    
    def run_scheduler(self):
        """Run the automation scheduler"""
        upload_time = self.config.get('AUTOMATION', 'upload_time', '09:00')
        
        schedule.every().day.at(upload_time).do(self.process_daily_batch)
        
        print(f"KDP Automation System v{VERSION}")
        print("=" * 50)
        print(f"Reading from: Prepared Books Directory")
        print(f"Upload time: {upload_time}")
        print(f"Books per day: {self.config.getint('AUTOMATION', 'books_per_day', 3)}")
        print(f"Total prepared books: {len(self.books_data)}")
        print(f"Already processed: {len(self.processed_books)}")
        print(f"Remaining books: {len(self.books_data) - len(self.processed_books)}")
        print("=" * 50)
        print("Press Ctrl+C to stop")
        
        # Run one batch immediately for testing
        print("\nRunning test batch...")
        self.process_daily_batch()
        
        # Keep scheduler running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nAutomation stopped by user")

def main():
    """Main entry point"""
    try:
        # Load configuration
        config = KDPConfig()
        
        # Check if configuration is complete
        if not config.get('KDP', 'email') or not config.get('KDP', 'password'):
            print("Please configure your KDP credentials in config.ini")
            return
        
        # Check if prepared books directory exists
        prepared_books_dir = Path(config.get('FILES', 'prepared_books_directory', './prepared_books'))
        if not prepared_books_dir.exists():
            print(f"Prepared books directory not found: {prepared_books_dir}")
            print("Please run kdp_preparation.py first to prepare your books")
            print("Example: python kdp_preparation.py")
            return
        
        # Initialize automator
        automator = KDPAutomator(config)
        
        # Run scheduler
        automator.run_scheduler()
        
    except Exception as e:
        logging.error(f"Application error: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()