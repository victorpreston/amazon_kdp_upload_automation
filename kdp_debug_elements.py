#!/usr/bin/env python3
"""
Complete KDP Debug Script with Automatic Login and Navigation
This mimics the exact automation flow and dumps all form elements
"""

import os
import sys
import time
import json
import random
import logging
from datetime import datetime
from pathlib import Path
import configparser

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

class KDPDebugger:
    """Debug KDP form by following exact automation path"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.config = self.load_config()
        self.setup_logging()
        
    def load_config(self):
        """Load config from automation script"""
        config = configparser.ConfigParser()
        if os.path.exists('config.ini'):
            config.read('config.ini')
            return config
        else:
            print("ERROR: config.ini not found!")
            print("Make sure you have the config.ini file with your KDP credentials")
            sys.exit(1)
    
    def setup_logging(self):
        """Setup basic logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def setup_browser(self):
        """Setup browser exactly like automation script"""
        options = Options()
        
        # Same browser settings as automation
        user_data_dir = './chrome_profile'
        abs_user_data_dir = os.path.abspath(user_data_dir)
        Path(abs_user_data_dir).mkdir(parents=True, exist_ok=True)
        
        options.add_argument(f"--user-data-dir={abs_user_data_dir}")
        options.add_argument("--window-size=1366,768")
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
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            self.driver = webdriver.Chrome(options=options)
        
        # Hide automation
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver.implicitly_wait(10)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 15)
        
        print("Browser setup completed")
    
    def login_to_kdp(self):
        """Login using same logic as automation"""
        email = self.config.get('KDP', 'email')
        password = self.config.get('KDP', 'password')
        
        if not email or not password:
            print("ERROR: Email and password must be configured in config.ini")
            return False
        
        print(f"Logging in with email: {email}")
        
        try:
            # Navigate to KDP
            self.driver.get("https://kdp.amazon.com")
            time.sleep(random.uniform(2, 4))
            
            # Try to restore session (same as automation)
            try:
                if os.path.exists('./session_data.json'):
                    with open('./session_data.json', 'r') as f:
                        session_data = json.load(f)
                    
                    if session_data.get('cookies'):
                        self.driver.get("https://kdp.amazon.com")
                        time.sleep(2)
                        
                        for cookie in session_data['cookies']:
                            try:
                                self.driver.add_cookie(cookie)
                            except Exception:
                                pass
                        
                        self.driver.refresh()
                        time.sleep(3)
                        
                        # Check if already logged in
                        if self.is_logged_in():
                            print("Successfully restored session - already logged in")
                            return True
            except Exception:
                pass
            
            # Find and click sign in button
            try:
                sign_in_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')]"))
                )
                sign_in_btn.click()
                time.sleep(random.uniform(2, 3))
            except TimeoutException:
                pass
            
            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
            email_field.clear()
            for char in email:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            time.sleep(random.uniform(1, 2))
            
            # Click continue
            continue_btn = self.driver.find_element(By.ID, "continue")
            continue_btn.click()
            time.sleep(random.uniform(2, 3))
            
            # Enter password
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "ap_password")))
            password_field.clear()
            for char in password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            time.sleep(random.uniform(1, 2))
            
            # Click sign in
            sign_in_btn = self.driver.find_element(By.ID, "signInSubmit")
            sign_in_btn.click()
            time.sleep(random.uniform(3, 5))
            
            # Check for successful login
            if self.is_logged_in():
                print("Successfully logged in to KDP")
                return True
            else:
                print("Login failed - not on expected page")
                return False
                
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def is_logged_in(self):
        """Check if logged in using same logic as automation"""
        try:
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
    
    def navigate_to_create_book(self):
        """Navigate to book creation form using same logic as automation"""
        try:
            print("Navigating to create book form...")
            
            # Try to find Create New button
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
                print("Could not find Create button, trying direct navigation...")
                self.driver.get("https://kdp.amazon.com/en_US/title-setup/kindle")
                time.sleep(random.uniform(3, 5))
            else:
                create_btn.click()
                time.sleep(random.uniform(2, 3))
                print("Clicked Create button")
            
            # Look for Create eBook button
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
                    print(f"Found Create eBook button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not ebook_btn:
                print("Could not find Create eBook button")
                return False
            
            # Click Create eBook button
            ebook_btn.click()
            time.sleep(random.uniform(3, 5))
            print("Clicked Create eBook button")
            
            # Wait for form to load
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
                    print(f"Found form indicator: {indicator}")
                    break
                except TimeoutException:
                    continue
            
            if form_found:
                print("Successfully navigated to book creation form!")
                return True
            else:
                print("Could not confirm form loaded")
                return False
                
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False
    
    def analyze_form_elements(self):
        """Analyze all form elements and save to file"""
        print("\n" + "="*80)
        print("ANALYZING ALL FORM ELEMENTS")
        print("="*80)
        
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'url': self.driver.current_url,
            'page_title': self.driver.title,
            'inputs': [],
            'textareas': [],
            'selects': [],
            'buttons': [],
            'iframes': [],
            'radio_buttons': [],
            'checkboxes': []
        }
        
        # Analyze all input fields
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        print(f"\nFOUND {len(inputs)} INPUT FIELDS:")
        print("-" * 50)
        
        for i, inp in enumerate(inputs):
            try:
                input_info = {
                    'index': i,
                    'type': inp.get_attribute('type'),
                    'name': inp.get_attribute('name'),
                    'id': inp.get_attribute('id'),
                    'placeholder': inp.get_attribute('placeholder'),
                    'class': inp.get_attribute('class'),
                    'value': inp.get_attribute('value'),
                    'visible': inp.is_displayed(),
                    'enabled': inp.is_enabled(),
                    'aria_label': inp.get_attribute('aria-label'),
                    'xpath': f"//input[@type='{inp.get_attribute('type')}']" if inp.get_attribute('type') else None
                }
                
                # Add to appropriate category
                if input_info['type'] == 'radio':
                    analysis_results['radio_buttons'].append(input_info)
                elif input_info['type'] == 'checkbox':
                    analysis_results['checkboxes'].append(input_info)
                else:
                    analysis_results['inputs'].append(input_info)
                
                # Print visible, relevant inputs
                if (input_info['visible'] and 
                    input_info['type'] in ['text', 'email', 'number', 'file', 'radio', 'checkbox']):
                    
                    print(f"INPUT {i} ({input_info['type']}):")
                    for key, value in input_info.items():
                        if value and key != 'index':
                            print(f"  {key}: {value}")
                    print()
                    
            except Exception as e:
                print(f"Error analyzing input {i}: {e}")
        
        # Analyze textareas
        textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
        print(f"\nFOUND {len(textareas)} TEXTAREA FIELDS:")
        print("-" * 50)
        
        for i, ta in enumerate(textareas):
            try:
                textarea_info = {
                    'index': i,
                    'name': ta.get_attribute('name'),
                    'id': ta.get_attribute('id'),
                    'placeholder': ta.get_attribute('placeholder'),
                    'class': ta.get_attribute('class'),
                    'visible': ta.is_displayed(),
                    'enabled': ta.is_enabled(),
                    'aria_label': ta.get_attribute('aria-label')
                }
                
                analysis_results['textareas'].append(textarea_info)
                
                if textarea_info['visible']:
                    print(f"TEXTAREA {i}:")
                    for key, value in textarea_info.items():
                        if value and key != 'index':
                            print(f"  {key}: {value}")
                    print()
            except Exception as e:
                print(f"Error analyzing textarea {i}: {e}")
        
        # Analyze select dropdowns
        selects = self.driver.find_elements(By.TAG_NAME, "select")
        print(f"\nFOUND {len(selects)} SELECT DROPDOWNS:")
        print("-" * 50)
        
        for i, sel in enumerate(selects):
            try:
                select_info = {
                    'index': i,
                    'name': sel.get_attribute('name'),
                    'id': sel.get_attribute('id'),
                    'class': sel.get_attribute('class'),
                    'visible': sel.is_displayed(),
                    'enabled': sel.is_enabled()
                }
                
                analysis_results['selects'].append(select_info)
                
                if select_info['visible']:
                    print(f"SELECT {i}:")
                    for key, value in select_info.items():
                        if value and key != 'index':
                            print(f"  {key}: {value}")
                    print()
            except Exception as e:
                print(f"Error analyzing select {i}: {e}")
        
        # Analyze buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        print(f"\nFOUND {len(buttons)} BUTTONS:")
        print("-" * 50)
        
        for i, btn in enumerate(buttons):
            try:
                button_info = {
                    'index': i,
                    'text': btn.text.strip(),
                    'type': btn.get_attribute('type'),
                    'class': btn.get_attribute('class'),
                    'id': btn.get_attribute('id'),
                    'visible': btn.is_displayed(),
                    'enabled': btn.is_enabled()
                }
                
                analysis_results['buttons'].append(button_info)
                
                if button_info['visible'] and button_info['text']:
                    print(f"BUTTON {i}: '{button_info['text']}'")
                    for key, value in button_info.items():
                        if value and key not in ['index', 'text']:
                            print(f"  {key}: {value}")
                    print()
            except Exception as e:
                print(f"Error analyzing button {i}: {e}")
        
        # Analyze iframes
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        print(f"\nFOUND {len(iframes)} IFRAMES:")
        print("-" * 50)
        
        for i, iframe in enumerate(iframes):
            try:
                iframe_info = {
                    'index': i,
                    'src': iframe.get_attribute('src'),
                    'id': iframe.get_attribute('id'),
                    'class': iframe.get_attribute('class'),
                    'visible': iframe.is_displayed()
                }
                
                analysis_results['iframes'].append(iframe_info)
                
                if iframe_info['visible']:
                    print(f"IFRAME {i}:")
                    for key, value in iframe_info.items():
                        if value and key != 'index':
                            print(f"  {key}: {value}")
                    print()
            except Exception as e:
                print(f"Error analyzing iframe {i}: {e}")
        
        # Save results to file
        output_file = f"kdp_form_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        
        print("="*80)
        print(f"ANALYSIS COMPLETE!")
        print(f"Results saved to: {output_file}")
        print("="*80)
        
        # Also save a summary text file
        summary_file = f"kdp_form_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("KDP FORM ELEMENT ANALYSIS\n")
            f.write("="*50 + "\n\n")
            f.write(f"URL: {self.driver.current_url}\n")
            f.write(f"Page Title: {self.driver.title}\n")
            f.write(f"Analysis Time: {datetime.now()}\n\n")
            
            # Key fields summary
            f.write("KEY FORM FIELDS FOUND:\n")
            f.write("-" * 30 + "\n")
            
            for inp in analysis_results['inputs']:
                if inp['visible'] and inp['type'] in ['text', 'email', 'number']:
                    f.write(f"INPUT: type={inp['type']}, name={inp['name']}, id={inp['id']}, placeholder={inp['placeholder']}\n")
            
            for ta in analysis_results['textareas']:
                if ta['visible']:
                    f.write(f"TEXTAREA: name={ta['name']}, id={ta['id']}, placeholder={ta['placeholder']}\n")
            
            for sel in analysis_results['selects']:
                if sel['visible']:
                    f.write(f"SELECT: name={sel['name']}, id={sel['id']}\n")
            
            f.write("\nRADIO BUTTONS:\n")
            for radio in analysis_results['radio_buttons']:
                if radio['visible']:
                    f.write(f"RADIO: name={radio['name']}, id={radio['id']}, value={radio['value']}\n")
            
            f.write("\nBUTTONS:\n")
            for btn in analysis_results['buttons']:
                if btn['visible'] and btn['text']:
                    f.write(f"BUTTON: '{btn['text']}', class={btn['class']}\n")
        
        print(f"Summary saved to: {summary_file}")
        return output_file, summary_file
    
    def run_debug(self):
        """Run complete debug process"""
        try:
            print("Starting KDP Form Debug Process...")
            print("This will login and navigate to the form exactly like the automation")
            
            # Setup browser
            self.setup_browser()
            
            # Login
            if not self.login_to_kdp():
                print("Failed to login, cannot continue")
                return
            
            # Navigate to form
            if not self.navigate_to_create_book():
                print("Failed to navigate to form, cannot continue")
                return
            
            # Give form time to fully load
            print("Waiting for form to fully load...")
            time.sleep(5)
            
            # Analyze all elements
            json_file, text_file = self.analyze_form_elements()
            
            print(f"\nDEBUG COMPLETE!")
            print(f"Share these files:")
            print(f"1. {json_file}")
            print(f"2. {text_file}")
            
            # Keep browser open for manual inspection if needed
            input("\nPress ENTER to close browser...")
            
        except Exception as e:
            print(f"Debug process failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()

def main():
    debugger = KDPDebugger()
    debugger.run_debug()

if __name__ == "__main__":
    main()