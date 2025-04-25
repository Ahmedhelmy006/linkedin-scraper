"""
Enhanced Playwright driver with built-in initialization, navigation, and multi-tab support.

This module provides a streamlined browser automation utility that handles
context creation, page management, multiple tabs, and navigation in a single class.
"""

from playwright.sync_api import sync_playwright, BrowserContext, Page, Browser
import json
import logging
import random
import os
import time
from typing import Optional, Dict, Any, List, Tuple, Literal, Union, Callable

from config.scraper_config import RANDOM_SITES, STATES, EVENTS, LINKEDIN_FEED_URL, SCROLL_PAUSE_TIME

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
        self.pages = []  # Track all pages/tabs
        
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
                
                # Create a page if none exists
                if len(self.context.pages) == 0:
                    self.page = self.context.new_page()
                else:
                    self.page = self.context.pages[0]
                
                # Track pages
                self.pages = list(self.context.pages)
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
                self.pages = [self.page]
            
            # Additional context settings
            self.context.set_default_timeout(60000)  # 60 seconds default timeout
            
            # Listen for new page events to track tabs
            self.context.on("page", lambda page: self._handle_new_page(page))
            
            # Apply random viewport variation (10% chance)
            if random.random() < 0.1:
                self._apply_random_viewport()
            
            logger.info(f"Browser initialized in {self.mode} mode (headless: {self.headless})")
            return self
            
        except Exception as e:
            logger.error(f"Failed to initialize Playwright driver: {str(e)}")
            # Clean up partially initialized resources
            self.close()
            raise
    
    def _handle_new_page(self, page: Page) -> None:
        """
        Handle a new page/tab being created.
        
        Args:
            page: The new Page object
        """
        logger.debug(f"New page/tab detected: {page}")
        if page not in self.pages:
            self.pages.append(page)
    
    def _apply_random_viewport(self) -> None:
        """Apply a random variation to the viewport size."""
        try:
            # Get current viewport
            current_viewport = self.context.viewport_size or {'width': 1200, 'height': 900}
            
            # Apply random variations
            width_delta = random.randint(-150, 150)
            height_delta = random.randint(-80, 80)
            
            new_width = max(800, current_viewport['width'] + width_delta)
            new_height = max(600, current_viewport['height'] + height_delta)
            
            # Set new viewport
            self.context.set_viewport_size({'width': new_width, 'height': new_height})
            logger.info(f"Applied random viewport: {new_width}x{new_height}")
            
        except Exception as e:
            logger.error(f"Failed to apply random viewport: {str(e)}")

    def navigate(self, url: str, wait_until: str = "load", page_index: int = None) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: The URL to navigate to
            wait_until: Navigation wait condition ('load', 'domcontentloaded', 'networkidle', 'commit')
            page_index: Optional index of the page/tab to use (None for current active page)
            
        Returns:
            True if navigation succeeded, False otherwise
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot navigate: No page available at index {page_index}.")
            return False
            
        try:
            # Add a small random delay before navigation (makes it look more natural)
            time.sleep(random.uniform(0.1, 0.5))
            
            # Perform navigation with variable timeout
            timeout = random.randint(30000, 60000)  # 30-60 seconds
            response = target_page.goto(url, wait_until=wait_until, timeout=timeout)
            
            if response:
                logger.info(f"Navigated to {url} (status: {response.status})")
                return True
            else:
                logger.warning(f"Navigation to {url} did not return a response")
                return False
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {str(e)}")
            return False
    
    def _get_page(self, page_index: Optional[int] = None) -> Optional[Page]:
        """
        Get a page by index or the currently active page.
        
        Args:
            page_index: Index of the page to get, or None for current active page
            
        Returns:
            The requested Page object, or None if not available
        """
        # Return the current page if no index is specified
        if page_index is None:
            return self.page
            
        # Return the page at the specified index if it exists
        if 0 <= page_index < len(self.pages):
            return self.pages[page_index]
            
        return None
    

    def new_page(self) -> Tuple[bool, int]:
        """
        Create a new page/tab and properly track it.
        
        Returns:
            Tuple of (success, page_index)
        """
        if not self.context:
            logger.error("Cannot create new page: No context available. Call start() first.")
            return False, -1
            
        try:
            # Store current page index as main page
            main_page_index = self.pages.index(self.page) if self.page in self.pages else 0
            
            # Create a new page
            new_page = self.context.new_page()
            
            # Add to pages list and get its index
            self.pages.append(new_page)
            new_index = len(self.pages) - 1
            
            # Do NOT switch context yet - keep the reference to the original page
            logger.info(f"Created new page at index {new_index} (current active page remains at index {main_page_index})")
            
            return True, new_index
        except Exception as e:
            logger.error(f"Failed to create new page: {str(e)}")
            return False, -1

    # Also update the visit_random_site method in HumanLikeBehavior class
    def visit_random_site(self, duration_range: Tuple[float, float] = (30, 90)) -> bool:
        """
        Visit a random website for a period of time.
        
        Args:
            duration_range: Min and max duration in seconds
            
        Returns:
            True if successfully visited a random site, False otherwise
        """
        if not self.driver:
            logger.error("Driver not set. Cannot visit random site.")
            return False
            
        try:
            # Store information about the current page
            main_page_index = 0
            current_url = self.driver.get_current_url()
            
            if not current_url:
                logger.warning("Could not determine current URL before random site visit")
                current_url = "https://www.linkedin.com/feed/"
            
            logger.info(f"Starting random site visit, current page URL: {current_url}")
            
            # Try to open a new tab
            logger.info("Creating new tab for random site visit...")
            success, new_tab_index = self.driver.new_page()
            
            if not success:
                logger.warning("Could not open new tab, will use current tab")
                new_tab_created = False
            else:
                new_tab_created = True
                logger.info(f"New tab created with index {new_tab_index}")
                
                # Switch to the new tab explicitly
                self.driver.switch_page(new_tab_index)
                logger.info(f"Switched to new tab (index {new_tab_index})")
            
            # Get a list of random, safe sites
            random_sites = getattr(RANDOM_SITES, "sites", [
                "https://www.wikipedia.org",
                "https://www.weather.com",
                "https://www.bbc.com",
                "https://www.nytimes.com",
                "https://www.reuters.com",
                "https://www.nationalgeographic.com",
                "https://www.forbes.com",
                "https://www.time.com"
            ])
            
            # Select a random site
            random_site = random.choice(random_sites)
            logger.info(f"Visiting random site: {random_site}")
            
            # Navigate to random site in the current tab (which should be the new tab if created)
            result = self.driver.navigate(random_site)
            
            if not result:
                logger.error(f"Failed to navigate to {random_site}")
                # If we're in a new tab but navigation failed, close it and return to original
                if new_tab_created:
                    self.driver.close_page(new_tab_index)
                    self.driver.switch_page(main_page_index)
                return False
                
            # Stay on site for random duration
            duration = self.random_range(*duration_range)
            logger.info(f"Staying on {random_site} for {duration:.2f} seconds")
            
            # Interact with the random site naturally
            time.sleep(self.random_range(2, 5))  # Initial load time
            
            # Scroll through the page
            self._scroll_with_human_behavior(duration=duration * 0.7)  # Use 70% of time for scrolling
            
            # Finish with a pause at the end
            time.sleep(duration * 0.3)  # Remaining 30% of time
            
            # Return to the original tab/URL
            if new_tab_created:
                # Close the current tab
                logger.info(f"Closing random site tab (index {new_tab_index})")
                self.driver.close_page(new_tab_index)
                
                # Switch back to the original tab
                logger.info(f"Switching back to original tab (index {main_page_index})")
                self.driver.switch_page(main_page_index)
                
                # Verify we're back on the original page
                current_url_after = self.driver.get_current_url()
                if current_url_after and current_url_after != current_url:
                    logger.warning(f"After tab switch, URL is {current_url_after} (expected: {current_url})")
                    # Try to navigate back to original URL if different
                    self.driver.navigate(current_url)
            else:
                # Navigate back to original URL in the same tab
                logger.info(f"Navigating back to {current_url} in same tab")
                self.driver.navigate(current_url)
            
            logger.info(f"Returned from random site visit to {random_site}")
            return True
            
        except Exception as e:
            logger.error(f"Error visiting random site: {str(e)}")
            return False
    
    def close_page(self, page_index: int) -> bool:
        """
        Close a specific page/tab.
        
        Args:
            page_index: Index of the page to close
            
        Returns:
            True if successful, False otherwise
        """
        if not self.context or page_index >= len(self.pages) or page_index < 0:
            logger.error(f"Cannot close page {page_index}: Invalid index or no context")
            return False
            
        try:
            target_page = self.pages[page_index]
            target_page.close()
            self.pages.pop(page_index)
            
            # If we closed the current active page, update the reference
            if self.page == target_page:
                if self.pages:
                    self.page = self.pages[0]
                else:
                    self.page = None
                    
            logger.info(f"Closed page at index {page_index}")
            return True
        except Exception as e:
            logger.error(f"Failed to close page {page_index}: {str(e)}")
            return False
    
    def switch_page(self, page_index: int) -> bool:
        """
        Switch the active page.
        
        Args:
            page_index: Index of the page to switch to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.context or page_index >= len(self.pages) or page_index < 0:
            logger.error(f"Cannot switch to page {page_index}: Invalid index or no context")
            return False
            
        try:
            self.page = self.pages[page_index]
            logger.info(f"Switched to page at index {page_index}")
            
            # Bring the page to focus
            self.page.bring_to_front()
            return True
        except Exception as e:
            logger.error(f"Failed to switch to page {page_index}: {str(e)}")
            return False
    
    def get_content(self, page_index: Optional[int] = None) -> Optional[str]:
        """
        Get the HTML content of a page.
        
        Args:
            page_index: Optional index of the page to get content from
            
        Returns:
            HTML content as string, or None if not available
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot get content: No page available at index {page_index}.")
            return None
            
        try:
            return target_page.content()
        except Exception as e:
            logger.error(f"Failed to get page content: {str(e)}")
            return None
    
    def screenshot(self, path: str, page_index: Optional[int] = None) -> bool:
        """
        Take a screenshot of a page.
        
        Args:
            path: File path to save the screenshot
            page_index: Optional index of the page to screenshot
            
        Returns:
            True if successful, False otherwise
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot take screenshot: No page available at index {page_index}.")
            return False
            
        try:
            target_page.screenshot(path=path)
            logger.info(f"Screenshot saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return False
    
    def click(self, selector: str, timeout: Optional[int] = None, page_index: Optional[int] = None) -> bool:
        """
        Click on an element.
        
        Args:
            selector: CSS selector of the element to click
            timeout: Maximum time to wait for the selector to be visible
            page_index: Optional index of the page on which to click
            
        Returns:
            True if successful, False otherwise
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot click: No page available at index {page_index}.")
            return False
            
        try:
            # Use variable timeout if not specified
            if timeout is None:
                timeout = random.randint(15000, 30000)  # 15-30 seconds
                
            target_page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to click on {selector}: {str(e)}")
            return False
    
    def type_text(self, selector: str, text: str, delay: Optional[int] = None, page_index: Optional[int] = None) -> bool:
        """
        Type text into an element.
        
        Args:
            selector: CSS selector of the input element
            text: Text to type
            delay: Delay between keypresses in milliseconds
            page_index: Optional index of the page on which to type
            
        Returns:
            True if successful, False otherwise
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot type text: No page available at index {page_index}.")
            return False
            
        try:
            # Use variable delay if not specified
            if delay is None:
                delay = random.randint(10, 30)  # 10-30ms between keypresses
                
            target_page.fill(selector, text, timeout=30000)
            return True
        except Exception as e:
            logger.error(f"Failed to type text into {selector}: {str(e)}")
            return False
    
    def wait_for_selector(self, selector: str, timeout: Optional[int] = None, page_index: Optional[int] = None) -> bool:
        """
        Wait for an element to be visible.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait in milliseconds (None for random timeout)
            page_index: Optional index of the page on which to wait
            
        Returns:
            True if element appeared, False if timed out
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot wait for selector: No page available at index {page_index}.")
            return False
            
        try:
            # Use variable timeout if not specified
            if timeout is None:
                timeout = random.randint(5000, 15000)  # 5-15 seconds random timeout
                
            target_page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Timed out waiting for selector {selector} after {timeout}ms: {str(e)}")
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
    
    def evaluate(self, javascript: str, page_index: Optional[int] = None) -> Any:
        """
        Evaluate JavaScript code in the browser context.
        
        Args:
            javascript: JavaScript code to evaluate
            page_index: Optional index of the page on which to evaluate
            
        Returns:
            Result of the JavaScript evaluation
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot evaluate: No page available at index {page_index}.")
            return None
            
        try:
            return target_page.evaluate(javascript)
        except Exception as e:
            logger.error(f"Failed to evaluate JavaScript: {str(e)}")
            return None
    
    def get_current_url(self, page_index: Optional[int] = None) -> Optional[str]:
        """
        Get the current URL of a page.
        
        Args:
            page_index: Optional index of the page
            
        Returns:
            Current URL as string or None if error
        """
        target_page = self._get_page(page_index)
        
        if not target_page:
            logger.error(f"Cannot get URL: No page available at index {page_index}.")
            return None
            
        try:
            return target_page.url
        except Exception as e:
            logger.error(f"Failed to get current URL: {str(e)}")
            return None
    
    def get_page_count(self) -> int:
        """
        Get the number of open pages/tabs.
        
        Returns:
            Number of open pages/tabs
        """
        return len(self.pages)
    
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
    
    def execute_on_all_pages(self, fn: Callable[[Page], Any]) -> List[Any]:
        """
        Execute a function on all open pages.
        
        Args:
            fn: Function that takes a Page object and returns anything
            
        Returns:
            List of return values from each page
        """
        results = []
        for page in self.pages:
            try:
                results.append(fn(page))
            except Exception as e:
                logger.error(f"Error executing function on page: {str(e)}")
                results.append(None)
        return results
    
    def close(self) -> None:
        """Close browser and clean up all resources."""
        try:
            # Clear pages list first
            self.pages = []
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