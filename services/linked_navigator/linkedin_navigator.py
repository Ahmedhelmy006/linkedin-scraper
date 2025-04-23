"""
LinkedIn Navigator

This module provides functionality to navigate LinkedIn profiles and extract HTML content
from various sections for further processing.
"""

import logging
import re
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from utils.playwright_driver import PlaywrightDriver

logger = logging.getLogger(__name__)

class LinkedInNavigator:
    """
    LinkedIn Profile Navigator.
    
    This class uses Playwright to navigate and extract HTML content from LinkedIn profiles.
    It can navigate to different sections of a profile and store their HTML for later use.
    """
    
    def __init__(
        self, 
        profile_url: str,
        headless: bool = False,
        cookies_file: Optional[str] = None,
        profile_path: Optional[str] = None
    ):
        """
        Initialize the LinkedIn Navigator.
        
        Args:
            profile_url: URL of the LinkedIn profile to navigate
            headless: Whether to run the browser in headless mode
            cookies_file: Path to cookies file for authentication
            profile_path: Path to browser profile for persistent sessions
        """
        self.profile_url = self._normalize_profile_url(profile_url)
        self.headless = headless
        self.cookies_file = cookies_file
        self.profile_path = profile_path
        
        # Initialize driver mode based on provided parameters
        if profile_path:
            self.driver_mode = "profile_mode"
        elif cookies_file:
            self.driver_mode = "cookies_mode"
        else:
            self.driver_mode = "basic"
        
        # Initialize storage for the extracted HTML
        self.main_profile_html = ""
        self.experience_html = ""
        
        # Initialize other storage properties as needed
        self.education_html = ""
        self.skills_html = ""
        self.is_authenticated = False
        
        # Initialize driver
        self.driver = None
        self.last_error = None

    def _normalize_profile_url(self, url: str) -> str:
        """
        Normalize the LinkedIn profile URL format.
        
        This ensures the URL is in the standard format without any query parameters
        or trailing sections.
        
        Args:
            url: The LinkedIn profile URL
            
        Returns:
            Normalized profile URL
        """
        # Extract the base profile URL
        match = re.match(r'(https?://(?:www\.)?linkedin\.com/in/[^/]+).*', url)
        if match:
            return match.group(1)
        return url
    
    def _build_section_url(self, section: str) -> str:
        """
        Build a URL for a specific profile section.
        
        Args:
            section: The section name (e.g., 'experience', 'education')
            
        Returns:
            Full URL for the specified section
        """
        return f"{self.profile_url}/details/{section}/"
    
    def start(self) -> bool:
        """
        Start the navigator by initializing and configuring the PlaywrightDriver.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Initializing LinkedIn Navigator for profile: {self.profile_url}")
            
            # Initialize the driver with appropriate configuration
            self.driver = PlaywrightDriver(
                mode=self.driver_mode,
                headless=self.headless,
                cookies_file=self.cookies_file,
                profile_path=self.profile_path
            )
            
            # Start the browser
            self.driver.start()
            
            return True
        except Exception as e:
            self.last_error = f"Failed to start navigator: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_profile(self) -> bool:
        """
        Navigate to the main profile page and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the profile URL
            logger.info(f"Navigating to profile: {self.profile_url}")
            if not self.driver.navigate(self.profile_url, wait_until="networkidle"):
                self.last_error = f"Failed to navigate to {self.profile_url}"
                logger.error(self.last_error)
                return False
            
            # Wait for the page to fully load
            logger.info("Waiting for profile page to fully load...")
            time.sleep(3)  # Allow additional time for dynamic content
            
            # Check for authentication
            self._check_authentication()
            
            if not self.is_authenticated:
                self.last_error = "Not authenticated on LinkedIn. Please provide valid cookies or profile."
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.main_profile_html = self.driver.get_content()
            
            if not self.main_profile_html:
                self.last_error = "Failed to extract profile HTML"
                logger.error(self.last_error)
                return False
            
            logger.info("Successfully extracted main profile HTML")
            print(f"Main profile HTML length: {len(self.main_profile_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating profile: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_experience(self) -> bool:
        """
        Navigate to the experience section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Build the experience section URL
            experience_url = self._build_section_url("experience")
            
            logger.info(f"Navigating to experience section: {experience_url}")
            if not self.driver.navigate(experience_url, wait_until="networkidle"):
                self.last_error = f"Failed to navigate to {experience_url}"
                logger.error(self.last_error)
                return False
            
            # Wait for the page to fully load
            logger.info("Waiting for experience page to fully load...")
            time.sleep(3)  # Allow additional time for dynamic content
            
            # Extract the HTML
            self.experience_html = self.driver.get_content()
            
            if not self.experience_html:
                self.last_error = "Failed to extract experience HTML"
                logger.error(self.last_error)
                return False
            
            logger.info("Successfully extracted experience section HTML")
            print(f"Experience HTML length: {len(self.experience_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating experience section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def _check_authentication(self) -> None:
        """
        Check if we are authenticated on LinkedIn.
        
        This updates the is_authenticated flag based on page content.
        """
        try:
            # Look for elements that indicate we're logged in
            is_logged_in = self.driver.evaluate("""
                () => {
                    // Check for nav bar elements that appear when logged in
                    const navItems = document.querySelectorAll('nav.global-nav');
                    const profileImg = document.querySelector('img.global-nav__me-photo');
                    
                    // Check for login form which appears when not logged in
                    const loginForm = document.querySelector('form.login__form');
                    
                    return !!(navItems.length > 0 || profileImg) && !loginForm;
                }
            """)
            
            self.is_authenticated = bool(is_logged_in)
            logger.info(f"Authentication check: {'Authenticated' if self.is_authenticated else 'Not authenticated'}")
            
        except Exception as e:
            logger.error(f"Error checking authentication: {str(e)}")
            self.is_authenticated = False
    
    def close(self) -> None:
        """Close the browser and clean up resources."""
        if self.driver:
            try:
                self.driver.close()
                logger.info("Navigator closed successfully")
            except Exception as e:
                logger.error(f"Error closing navigator: {str(e)}")