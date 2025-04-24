"""
Simplified Playwright driver with built-in initialization and navigation.

This module provides a streamlined browser automation utility that handles
context creation, page management, and navigation in a single class.
"""

from playwright.sync_api import sync_playwright, BrowserContext, Page
import json
import logging
import random
import os
import time
from typing import Optional, Dict, Any, List, Tuple, Literal, Union

logger = logging.getLogger(__name__)

class PlaywrightDriver:
    """
    A streamlined utility class to manage Playwright browser automation.
    
    This class handles the entire lifecycle of browser automation including
    initialization, page creation, navigation, and cleanup.
    
    Supports multiple operation modes:
    - basic: No cookies or profile (default)
    - cookies_mode: Load cookies for authentication
    - profile_mode: Use a persistent Chrome profile
    """
    
    def __init__(
        self, 
        mode: Literal["basic", "cookies_mode", "profile_mode"] = "basic",
        cookies_file: Optional[str] = None,
        profile_path: Optional[str] = None,
        headless: bool = True,
        user_agent_type: str = "default"
    ):
        """
        Initialize the PlaywrightDriver with the specified mode.
        
        Args:
            mode: Operation mode ("basic", "cookies_mode", or "profile_mode")
            cookies_file: Path to a JSON file containing cookies for authentication (for cookies_mode)
            profile_path: Path to Chrome profile directory (for profile_mode)
            headless: Whether to run browser in headless mode (True) or with visible UI (False)
            user_agent_type: Type of user agent to use ("default", "random", or "mobile")
        """
        self.mode = mode
        self.cookies_file = cookies_file
        self.profile_path = profile_path
        self.headless = headless
        self.user_agent_type = user_agent_type
        
        # Initialize internal state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Validate configuration based on mode
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the configuration based on the selected mode."""
        if self.mode == "cookies_mode" and not self.cookies_file:
            logger.warning("cookies_mode selected but no cookies_file provided")
            
        if self.mode == "profile_mode" and not self.profile_path:
            logger.warning("profile_mode selected but no profile_path provided")
            
        if self.mode == "basic" and (self.cookies_file or self.profile_path):
            logger.warning("basic mode selected but cookies_file or profile_path was provided (these will be ignored)")

    def start(self) -> 'PlaywrightDriver':
        """
        Start the browser, initialize context, and create a page.
        
        Returns:
            Self (for method chaining)
        """
        try:
            # Start playwright
            self.playwright = sync_playwright().start()
            
            # Configure browser launch options based on mode
            launch_options = self._get_launch_options()
            
            # Select a user agent
            user_agent = self._get_user_agent(self.user_agent_type)
            
            # Configure context options
            context_options = {
                "user_agent": user_agent,
                "viewport": {'width': 1200, 'height': 900},
                "locale": "en-US"
            }
            
            # Launch browser differently based on mode
            if self.mode == "profile_mode" and self.profile_path:
                # For profile mode, we need to separate the user data dir from the profile name
                if "Profile " in self.profile_path:
                    # Path contains a specific profile directory
                    user_data_dir = self.profile_path.split("Profile ")[0].rstrip('\\/')
                    profile_name = "Profile " + self.profile_path.split("Profile ")[1]
                else:
                    # Using the main user data dir
                    user_data_dir = self.profile_path
                    profile_name = "Default"
                
                logger.info(f"Using Chrome user data dir: {user_data_dir}, profile: {profile_name}")
                
                # Launch with persistent context correctly
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    channel="chrome",  # Specifically use Chrome
                    headless=self.headless,
                    args=[
                        f'--profile-directory={profile_name}',  # This is crucial
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-infobars',
                        '--disable-dev-shm-usage',
                        '--disable-extensions',
                        '--disable-gpu',
                    ],
                    **context_options
                )
                
                # Create a page
                self.page = self.context.new_page()
            else:
                # For basic and cookies_mode, use regular launch
                self.browser = self.playwright.chromium.launch(**launch_options)
                
                # Create context with appropriate options
                self.context = self.browser.new_context(**context_options)
                
                # Handle cookies in cookies_mode
                if self.mode == "cookies_mode" and self.cookies_file:
                    self._load_cookies(self.context)
                
                # Create a page
                self.page = self.context.new_page()
            
            # Additional context settings
            self.context.set_default_timeout(60000)  # 60 seconds default timeout
            
            logger.info(f"Browser initialized in {self.mode} mode (headless: {self.headless})")
            return self
            
        except Exception as e:
            logger.error(f"Failed to initialize Playwright driver: {str(e)}")
            # Clean up partially initialized resources
            self.close()
            raise

    def navigate(self, url: str, wait_until: str = "load") -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
            wait_until: Navigation wait condition ('load', 'domcontentloaded', 'networkidle', 'commit')
            
        Returns:
            True if navigation succeeded, False otherwise
        """
        if not self.page:
            logger.error("Cannot navigate: No page available. Call start() first.")
            return False
            
        try:
            response = self.page.goto(url, wait_until=wait_until)
            if response:
                logger.info(f"Navigated to {url} (status: {response.status})")
                return True
            else:
                logger.warning(f"Navigation to {url} did not return a response")
                return False
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {str(e)}")
            return False
    
    def get_content(self) -> Optional[str]:
        """
        Get the HTML content of the current page.
        
        Returns:
            HTML content as string, or None if not available
        """
        if not self.page:
            logger.error("Cannot get content: No page available. Call start() first.")
            return None
            
        try:
            return self.page.content()
        except Exception as e:
            logger.error(f"Failed to get page content: {str(e)}")
            return None
    
    def screenshot(self, path: str) -> bool:
        """
        Take a screenshot of the current page.
        
        Args:
            path: File path to save the screenshot
            
        Returns:
            True if successful, False otherwise
        """
        if not self.page:
            logger.error("Cannot take screenshot: No page available. Call start() first.")
            return False
            
        try:
            self.page.screenshot(path=path)
            logger.info(f"Screenshot saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return False
    
    def click(self, selector: str, timeout: int = 30000) -> bool:
        """
        Click on an element.
        
        Args:
            selector: CSS selector of the element to click
            timeout: Maximum time to wait for the selector to be visible
            
        Returns:
            True if successful, False otherwise
        """
        if not self.page:
            logger.error("Cannot click: No page available. Call start() first.")
            return False
            
        try:
            self.page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to click on {selector}: {str(e)}")
            return False
    
    def type_text(self, selector: str, text: str, delay: int = 20) -> bool:
        """
        Type text into an element.
        
        Args:
            selector: CSS selector of the input element
            text: Text to type
            delay: Delay between keypresses in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.page:
            logger.error("Cannot type text: No page available. Call start() first.")
            return False
            
        try:
            self.page.fill(selector, text)
            return True
        except Exception as e:
            logger.error(f"Failed to type text into {selector}: {str(e)}")
            return False
    
    def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """
        Wait for an element to be visible.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if element appeared, False if timed out
        """
        if not self.page:
            logger.error("Cannot wait for selector: No page available. Call start() first.")
            return False
            
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Timed out waiting for selector {selector}: {str(e)}")
            return False
    
    def wait(self, seconds: float) -> None:
        """
        Wait for a specified number of seconds.
        
        Args:
            seconds: Number of seconds to wait
        """
        time.sleep(seconds)
    
    def save_cookies(self, cookies_file: Optional[str] = None) -> bool:
        """
        Save cookies from the current context to a file.
        
        Args:
            cookies_file: Path to save cookies to (uses self.cookies_file if None)
            
        Returns:
            True if cookies were saved successfully, False otherwise
        """
        if not self.context:
            logger.error("Cannot save cookies: No context available. Call start() first.")
            return False
            
        save_path = cookies_file or self.cookies_file
        
        if not save_path:
            logger.error("No cookies file path specified")
            return False
            
        try:
            cookies = self.context.cookies()
            with open(save_path, 'w') as file:
                json.dump(cookies, file, indent=2)
            logger.info(f"Saved cookies to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {str(e)}")
            return False
    
    def evaluate(self, javascript: str) -> Any:
        """
        Evaluate JavaScript code in the browser context.
        
        Args:
            javascript: JavaScript code to evaluate
            
        Returns:
            Result of the JavaScript evaluation
        """
        if not self.page:
            logger.error("Cannot evaluate: No page available. Call start() first.")
            return None
            
        try:
            return self.page.evaluate(javascript)
        except Exception as e:
            logger.error(f"Failed to evaluate JavaScript: {str(e)}")
            return None
    
    def _get_launch_options(self) -> Dict[str, Any]:
        """Get browser launch options based on the selected mode."""
        options = {
            "headless": self.headless,
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-gpu',
            ]
        }
        
        # We don't add user_data_dir here anymore, since profile mode uses launch_persistent_context
        
        return options

    def _load_cookies(self, context: BrowserContext) -> None:
        """Load cookies from file to the browser context."""
        try:
            with open(self.cookies_file, 'r') as file:
                cookies = json.load(file)
                context.add_cookies(cookies)
                logger.info(f"Loaded cookies from {self.cookies_file}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load cookies from {self.cookies_file}: {str(e)}")
            # Continue without cookies rather than failing completely

    def _get_user_agent(self, user_agent_type: str) -> str:
        """
        Get a user agent string based on the specified type.
        
        Args:
            user_agent_type: Type of user agent to use ("default", "random", or "mobile")
            
        Returns:
            A user agent string
        """
        # Default Chrome user agent
        default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        
        # Collection of desktop user agents
        desktop_uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
        ]
        
        # Collection of mobile user agents
        mobile_uas = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.90 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.90 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.89 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.90 Mobile Safari/537.36",
        ]
        
        if user_agent_type == "default":
            return default_ua
        elif user_agent_type == "random":
            # Pick a random desktop user agent
            return random.choice(desktop_uas)
        elif user_agent_type == "mobile":
            # Pick a random mobile user agent
            return random.choice(mobile_uas)
        else:
            logger.warning(f"Unknown user agent type: {user_agent_type}, using default")
            return default_ua
    
    def close(self) -> None:
        """Close browser and clean up all resources."""
        try:
            # These checks prevent errors when closing partially initialized resources
            if self.page:
                self.page = None
                
            if self.context:
                self.context.close()
                self.context = None
                
            if self.browser:
                self.browser.close()
                self.browser = None
                
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
                
            logger.info("Playwright driver closed successfully")
        except Exception as e:
            logger.error(f"Error when closing Playwright driver: {str(e)}")