#!/usr/bin/env python3
"""
Complete Amazon KDP Automation System - FINAL WORKING VERSION
WARNING: Use at your own risk - may violate Amazon's Terms of Service

Fixed all navigation and form interaction issues for real KDP interface.
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
VERSION = "1.0.2"

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
            'data_file': 'metadata_full.csv',
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
    
    def load_books_data(self):
        """Load books data from CSV/Excel"""
        data_file = self.config.get('FILES', 'data_file')
        
        try:
            if data_file.endswith('.xlsx'):
                self.books_data = pd.read_excel(data_file)
            else:
                self.books_data = pd.read_csv(data_file, sep=';')
            
            logging.info(f"Loaded {len(self.books_data)} books from {data_file}")
            
        except Exception as e:
            logging.error(f"Failed to load books data: {e}")
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
                "//input[contains(@name, 'title') or contains(@id, 'title')]",
                "//textarea[contains(@name, 'description') or contains(@id, 'description')]",
                "//input[contains(@name, 'author') or contains(@id, 'author')]",
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
        """Fill in book details form - ULTIMATE FIXED VERSION"""
        try:
            logging.info("Starting to fill book details...")
            
            # Wait for form to be fully ready
            self.wait_for_form_ready()
            
            # Step 1: Set Language (if not already English)
            try:
                if book_data['language'] != 'English':
                    language_selectors = [
                        "//select[contains(@name, 'language')]",
                        "//select[contains(@id, 'language')]",
                        "//select[contains(@aria-label, 'language')]"
                    ]
                    
                    for selector in language_selectors:
                        try:
                            language_dropdown = Select(self.driver.find_element(By.XPATH, selector))
                            language_dropdown.select_by_visible_text(book_data['language'])
                            self.behavior.random_delay(1, 2)
                            logging.info(f"Selected language: {book_data['language']}")
                            break
                        except (NoSuchElementException, Exception):
                            continue
            except Exception as e:
                logging.warning(f"Could not set language: {e}")
            
            # Step 2: Fill Title - Based on actual form structure
            title_filled = False
            title_selectors = [
                "//h3[contains(text(), 'Book Title')]/following-sibling::div//input",
                "//div[contains(@class, 'book-title')]//input",
                "//label[text()='Book Title']/following-sibling::input",
                "//input[contains(@name, 'title')]",
                "//input[contains(@id, 'title')]"
            ]
            
            for attempt in range(3):  # Try up to 3 times
                for selector in title_selectors:
                    try:
                        logging.info(f"Attempt {attempt + 1}: Trying title selector: {selector}")
                        
                        # Wait for element to be clickable
                        title_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        
                        # Scroll to element
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", title_field)
                        time.sleep(1)
                        
                        # Check if element is enabled
                        if not title_field.is_enabled():
                            logging.warning("Title field is not enabled, waiting...")
                            time.sleep(2)
                            continue
                        
                        # Use safe_type method
                        if self.behavior.safe_type(self.driver, title_field, book_data['title']):
                            logging.info(f"Successfully filled title: {book_data['title']}")
                            title_filled = True
                            break
                        
                    except TimeoutException:
                        logging.warning(f"Title selector timeout: {selector}")
                        continue
                    except ElementNotInteractableException:
                        logging.warning(f"Title element not interactable: {selector}")
                        time.sleep(1)
                        continue
                    except Exception as e:
                        logging.warning(f"Title filling error with {selector}: {e}")
                        continue
                
                if title_filled:
                    break
                    
                # Wait between attempts
                time.sleep(2)
            
            if not title_filled:
                logging.error("Failed to fill title after all attempts")
                return False
            
            # Step 3: Fill Subtitle (optional) - Based on screenshots
            if pd.notna(book_data['subtitle']) and book_data['subtitle']:
                subtitle_selectors = [
                    "//h3[contains(text(), 'Book Title')]/following-sibling::div//input[contains(@placeholder, 'Subtitle') or position()=2]",
                    "//div[contains(text(), 'Subtitle')]/following-sibling::div//input",
                    "//input[contains(@name, 'subtitle')]",
                    "//input[contains(@id, 'subtitle')]"
                ]
                
                for selector in subtitle_selectors:
                    try:
                        subtitle_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", subtitle_field)
                        time.sleep(0.5)
                        
                        if self.behavior.safe_type(self.driver, subtitle_field, book_data['subtitle']):
                            logging.info(f"Filled subtitle: {book_data['subtitle']}")
                            break
                            
                    except (TimeoutException, ElementNotInteractableException):
                        continue
                    except Exception as e:
                        logging.warning(f"Subtitle error with {selector}: {e}")
                        continue
            
            # Step 4: Fill Author Name - Split into First/Last name based on screenshots
            author_filled = False
            
            # Try to fill First name field
            first_name_selectors = [
                "//input[@placeholder='First name']",
                "//h3[contains(text(), 'Author')]/following-sibling::div//input[@placeholder='First name']",
                "//div[contains(text(), 'Primary Author')]/following-sibling::div//input[@placeholder='First name']",
                "//input[contains(@name, 'firstName')]",
                "//input[contains(@id, 'firstName')]"
            ]
            
            for selector in first_name_selectors:
                try:
                    first_name_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", first_name_field)
                    time.sleep(0.5)
                    
                    # For first name, use full author name or split if contains space
                    author_name = str(book_data['author'])
                    if ' ' in author_name:
                        first_name = author_name.split(' ')[0]
                    else:
                        first_name = author_name
                    
                    if self.behavior.safe_type(self.driver, first_name_field, first_name):
                        logging.info(f"Filled first name: {first_name}")
                        
                        # Try to fill Last name field if author has multiple parts
                        if ' ' in author_name:
                            last_name = ' '.join(author_name.split(' ')[1:])
                            last_name_selectors = [
                                "//input[@placeholder='Last name']",
                                "//h3[contains(text(), 'Author')]/following-sibling::div//input[@placeholder='Last name']",
                                "//input[contains(@name, 'lastName')]",
                                "//input[contains(@id, 'lastName')]"
                            ]
                            
                            for last_selector in last_name_selectors:
                                try:
                                    last_name_field = self.driver.find_element(By.XPATH, last_selector)
                                    if self.behavior.safe_type(self.driver, last_name_field, last_name):
                                        logging.info(f"Filled last name: {last_name}")
                                        break
                                except Exception:
                                    continue
                        
                        author_filled = True
                        break
                        
                except (TimeoutException, ElementNotInteractableException):
                    continue
                except Exception as e:
                    logging.warning(f"Author error with {selector}: {e}")
                    continue
            
            if not author_filled:
                logging.warning("Could not fill author field")
            
            # Step 5: Fill Description - Rich text editor based on screenshots
            description_selectors = [
                "//h3[contains(text(), 'Description')]/following-sibling::div//iframe",  # Rich text editor iframe
                "//div[contains(@class, 'description')]//iframe",
                "//h3[contains(text(), 'Description')]/following-sibling::div//div[contains(@class, 'editor')]",  # Direct editor div
                "//textarea[contains(@name, 'description')]",  # Fallback to textarea
                "//div[contains(@contenteditable, 'true')]"  # Contenteditable div
            ]
            
            if pd.notna(book_data['description_html']):
                # Clean HTML from description
                import re
                clean_description = re.sub('<.*?>', '', book_data['description_html'])
                
                for selector in description_selectors:
                    try:
                        if 'iframe' in selector:
                            # Handle rich text editor in iframe
                            iframe = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                            self.driver.switch_to.frame(iframe)
                            
                            # Look for body or contenteditable element inside iframe
                            editor_selectors = [
                                "//body[@contenteditable='true']",
                                "//div[@contenteditable='true']",
                                "//body"
                            ]
                            
                            for editor_sel in editor_selectors:
                                try:
                                    editor_element = self.driver.find_element(By.XPATH, editor_sel)
                                    if self.behavior.safe_type(self.driver, editor_element, clean_description):
                                        logging.info("Filled description in rich text editor")
                                        self.driver.switch_to.default_content()
                                        break
                                except Exception:
                                    continue
                            else:
                                self.driver.switch_to.default_content()
                                continue
                            break
                        else:
                            # Handle regular text area or contenteditable div
                            description_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", description_field)
                            time.sleep(0.5)
                            
                            if self.behavior.safe_type(self.driver, description_field, clean_description):
                                logging.info("Filled description")
                                break
                            
                    except (TimeoutException, ElementNotInteractableException):
                        continue
                    except Exception as e:
                        logging.warning(f"Description error with {selector}: {e}")
                        continue
            
            # Step 6: Fill Keywords - Based on screenshots showing two input fields
            keywords_selectors = [
                "//h3[contains(text(), 'Keywords')]/following-sibling::div//input[1]",  # First keyword field
                "//div[contains(text(), 'Your Keywords')]/following-sibling::div//input[1]",
                "//input[contains(@name, 'keywords')]",
                "//input[contains(@id, 'keywords')]"
            ]
            
            if pd.notna(book_data['keywords']):
                # Split keywords if multiple, use first one for first field
                keywords_text = str(book_data['keywords'])
                if ';' in keywords_text:
                    first_keyword = keywords_text.split(';')[0].strip()
                else:
                    first_keyword = keywords_text
                
                for selector in keywords_selectors:
                    try:
                        keywords_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", keywords_field)
                        time.sleep(0.5)
                        
                        if self.behavior.safe_type(self.driver, keywords_field, first_keyword):
                            logging.info(f"Filled keywords: {first_keyword}")
                            break
                            
                    except (TimeoutException, ElementNotInteractableException):
                        continue
                    except Exception as e:
                        logging.warning(f"Keywords error with {selector}: {e}")
                        continue
            
            # Step 7: Handle Publishing Rights - Required selection based on screenshots
            try:
                rights_selectors = [
                    "//input[@type='radio'][following-sibling::text()[contains(., 'I own the copyright')]]",
                    "//label[contains(text(), 'I own the copyright')]//input[@type='radio']",
                    "//label[contains(text(), 'I own the copyright')]/preceding-sibling::input[@type='radio']",
                    "//h3[contains(text(), 'Publishing Rights')]/following-sibling::div//input[@type='radio'][1]"
                ]
                
                for selector in rights_selectors:
                    try:
                        rights_radio = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", rights_radio)
                        time.sleep(0.5)
                        
                        if not rights_radio.is_selected():
                            self.driver.execute_script("arguments[0].click();", rights_radio)
                            logging.info("Selected 'I own the copyright'")
                            time.sleep(1)
                            break
                    except Exception:
                        continue
            except Exception as e:
                logging.warning(f"Could not set publishing rights: {e}")
            
            # Step 8: Handle Adult Content - Required selection based on screenshots  
            try:
                adult_no_selectors = [
                    "//input[@type='radio'][following-sibling::text()[contains(., 'No')]]",
                    "//label[contains(text(), 'No')]//input[@type='radio']",
                    "//label[text()='No']/preceding-sibling::input[@type='radio']",
                    "//h3[contains(text(), 'Primary Audience')]/following-sibling::div//input[@type='radio'][2]"  # Usually "No" is second option
                ]
                
                for selector in adult_no_selectors:
                    try:
                        adult_radio = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", adult_radio)
                        time.sleep(0.5)
                        
                        if not adult_radio.is_selected():
                            self.driver.execute_script("arguments[0].click();", adult_radio)
                            logging.info("Selected 'No' for adult content")
                            time.sleep(1)
                            break
                    except Exception:
                        continue
            except Exception as e:
                logging.warning(f"Could not set adult content option: {e}")
            
            # Step 9: Click "Save and Continue" to proceed to next step
            try:
                save_continue_selectors = [
                    "//button[contains(text(), 'Save and Continue')]",
                    "//input[@value='Save and Continue']",
                    "//button[contains(@class, 'save-continue')]"
                ]
                
                for selector in save_continue_selectors:
                    try:
                        save_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", save_btn)
                        time.sleep(1)
                        
                        save_btn.click()
                        logging.info("Clicked 'Save and Continue' - proceeding to Content step")
                        time.sleep(3)  # Wait for next page to load
                        break
                    except Exception:
                        continue
            except Exception as e:
                logging.warning(f"Could not click Save and Continue: {e}")
            
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
            
            # Upload cover - try multiple selectors
            cover_selectors = [
                "//input[@type='file'][contains(@accept, 'image')]",
                "//input[@type='file'][contains(@name, 'cover')]",
                "//input[@type='file'][contains(@id, 'cover')]",
                "//div[contains(text(), 'cover')]/following-sibling::div//input[@type='file']"
            ]
            
            cover_path = self.clean_file_path(book_data['eBook-Cover'])
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
                    logging.info("Cover uploaded successfully")
                else:
                    logging.warning("Could not find cover upload field")
            else:
                logging.warning(f"Cover file not found: {cover_path}")
            
            # Upload manuscript (epub) - try multiple selectors
            manuscript_selectors = [
                "//input[@type='file'][contains(@accept, '.epub')]",
                "//input[@type='file'][contains(@name, 'manuscript')]",
                "//input[@type='file'][contains(@id, 'manuscript')]",
                "//input[@type='file'][not(contains(@accept, 'image'))]",
                "//div[contains(text(), 'manuscript')]/following-sibling::div//input[@type='file']"
            ]
            
            epub_path = self.clean_file_path(book_data['epub'])
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
                    logging.info("Manuscript uploaded successfully")
                else:
                    logging.warning("Could not find manuscript upload field")
            else:
                logging.warning(f"EPUB file not found: {epub_path}")
            
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
            
            # Set price (convert from cents to dollars)
            price_usd = book_data['price_ebook_usd'] / 100
            
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
    
    def clean_file_path(self, file_path):
        """Clean file path by removing extra quotes"""
        if file_path and isinstance(file_path, str):
            return file_path.strip().strip('"""').strip('"')
        return file_path
    
    def process_single_book(self, book_index: int) -> bool:
        """Process a single book upload"""
        book_data = self.books_data.iloc[book_index]
        
        logging.info(f"Starting upload for book: {book_data['title']}")
        
        try:
            # Navigate to create book
            if not self.navigate_to_create_book():
                logging.error("Failed to navigate to create book form")
                return False
            
            # Fill book details
            if not self.fill_book_details(book_data):
                logging.error("Failed to fill book details")
                return False
            
            # Upload files
            if not self.upload_book_files(book_data):
                logging.warning("File uploads had issues but continuing...")
            
            # Set pricing
            if not self.set_pricing(book_data):
                logging.warning("Pricing setup had issues but continuing...")
            
            # Publish book
            if not self.publish_book():
                logging.error("Failed to publish book")
                return False
            
            # Mark as processed
            self.processed_books.add(book_index)
            
            logging.info(f"Successfully uploaded book: {book_data['title']}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to process book {book_data['title']}: {e}")
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
        """Get next books to process"""
        available_books = []
        for i in range(len(self.books_data)):
            if i not in self.processed_books:
                available_books.append(i)
                if len(available_books) >= count:
                    break
        return available_books
    
    def run_scheduler(self):
        """Run the automation scheduler"""
        upload_time = self.config.get('AUTOMATION', 'upload_time', '09:00')
        
        schedule.every().day.at(upload_time).do(self.process_daily_batch)
        
        print(f"KDP Automation System v{VERSION}")
        print("=" * 50)
        print(f"Upload time: {upload_time}")
        print(f"Books per day: {self.config.getint('AUTOMATION', 'books_per_day', 3)}")
        print(f"Total books loaded: {len(self.books_data)}")
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
        
        # Initialize automator
        automator = KDPAutomator(config)
        
        # Run scheduler
        automator.run_scheduler()
        
    except Exception as e:
        logging.error(f"Application error: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()