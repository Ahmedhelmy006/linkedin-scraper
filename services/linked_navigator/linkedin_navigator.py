# services/linkedin_navigator.py
"""
LinkedIn Navigator module for scraping LinkedIn profiles.

This module handles LinkedIn navigation and content extraction,
working with the human-like behavior module to ensure natural interaction.
"""

import logging
import re
import time
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from config.scraper_config import PROFILES_DIR
from utils.playwright_driver import PlaywrightDriver
from services.linked_navigator.human_like_behavior import HumanLikeBehavior

logger = logging.getLogger(__name__)

class LinkedInNavigator:
    """
    LinkedIn Profile Navigator.
    
    This class handles navigation to LinkedIn profiles and extraction
    of profile data, following human-like behavior patterns.
    """
    
    def __init__(
        self, 
        profile_url: str,
        driver: Optional[PlaywrightDriver] = None,
        behavior: Optional[HumanLikeBehavior] = None,
        headless: bool = False,
        cookies_file: Optional[str] = None,
        profile_path: Optional[str] = None
    ):
        """
        Initialize the LinkedIn Navigator.
        
        Args:
            profile_url: URL of the LinkedIn profile to navigate
            driver: Optional shared PlaywrightDriver instance
            behavior: Optional HumanLikeBehavior instance
            headless: Whether to run the browser in headless mode
            cookies_file: Path to cookies file for authentication
            profile_path: Path to browser profile for persistent sessions
        """
        self.profile_url = self._normalize_profile_url(profile_url)
        self.headless = headless
        self.cookies_file = cookies_file
        self.profile_path = profile_path
        
        # Use provided driver or create a new one later
        self.driver = driver
        self.driver_mode = "shared" if driver else "profile_mode" if profile_path else "cookies_mode" if cookies_file else "basic"
        
        # Use provided behavior or create a new one
        self.behavior = behavior
        if not self.behavior:
            self.behavior = HumanLikeBehavior()
        
        # Initialize storage for the extracted HTML
        self.main_profile_html = ""
        self.experience_html = ""
        self.education_html = ""
        self.skills_html = ""
        self.recommendations_html = ""
        self.courses_html = ""
        self.languages_html = ""
        self.interests_html = ""
        
        # Initialize metadata
        self.profile_name = ""
        self.metadata = {
            "profile_url": self.profile_url,
            "scrape_date": datetime.now().isoformat(),
            "sections_scraped": []
        }
        
        # Initialize other state properties
        self.is_authenticated = False
        self.last_error = None
        self.own_driver = False  # Whether we created our own driver
    
    def _normalize_profile_url(self, url: str) -> str:
        """
        Normalize the LinkedIn profile URL format.
        
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
            # Only initialize driver if we don't already have one
            if not self.driver:
                logger.info(f"Initializing LinkedIn Navigator for profile: {self.profile_url}")
                
                # Import here to avoid circular imports
                from utils.playwright_driver import PlaywrightDriver
                
                # Initialize the driver with appropriate configuration
                self.driver = PlaywrightDriver(
                    mode=self.driver_mode,
                    headless=self.headless,
                    cookies_file=self.cookies_file,
                    profile_path=self.profile_path,
                    user_agent_type="random"
                )
                
                # Start the browser
                self.driver.start()
                self.own_driver = True
                
            # Set the driver in the behavior controller
            self.behavior.set_driver(self.driver)
            
            return True
        except Exception as e:
            # Check if the error is related to the profile being in use
            if "is already in use" in str(e):
                self.last_error = "Chrome profile is already in use. Please close all Chrome instances and try again."
            else:
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
            # First browse the feed using human-like behavior
            if not self.behavior.browse_feed():
                logger.warning("Feed browsing failed or was skipped")
            
            # Navigate to the profile using human-like behavior
            if not self.behavior.navigate_to_profile(self.profile_url):
                self.last_error = f"Failed to navigate to {self.profile_url}"
                logger.error(self.last_error)
                return False
            
            # Check for authentication
            self._check_authentication()
            
            if not self.is_authenticated:
                self.last_error = "Not authenticated on LinkedIn. Please provide valid cookies or profile."
                logger.error(self.last_error)
                return False
            
            # Extract the profile name for folder naming
            self._extract_profile_name()
            
            # Extract the HTML
            self.main_profile_html = self.driver.get_content()
            
            if not self.main_profile_html:
                self.last_error = "Failed to extract profile HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("main_profile")
            
            # Read profile content with human-like behavior
            self.behavior.simulate_reading(min_duration=5.0, max_duration=15.0)
            
            logger.info("Successfully extracted main profile HTML")
            logger.info(f"Main profile HTML length: {len(self.main_profile_html)}")
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
            # Navigate to the experience section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "experience"):
                self.last_error = "Failed to navigate to experience section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.experience_html = self.driver.get_content()
            
            if not self.experience_html:
                self.last_error = "Failed to extract experience HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("experience")
            
            logger.info("Successfully extracted experience section HTML")
            logger.info(f"Experience HTML length: {len(self.experience_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating experience section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_education(self) -> bool:
        """
        Navigate to the education section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the education section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "education"):
                self.last_error = "Failed to navigate to education section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.education_html = self.driver.get_content()
            
            if not self.education_html:
                self.last_error = "Failed to extract education HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("education")
            
            logger.info("Successfully extracted education section HTML")
            logger.info(f"Education HTML length: {len(self.education_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating education section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_skills(self) -> bool:
        """
        Navigate to the skills section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the skills section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "skills"):
                self.last_error = "Failed to navigate to skills section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.skills_html = self.driver.get_content()
            
            if not self.skills_html:
                self.last_error = "Failed to extract skills HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("skills")
            
            logger.info("Successfully extracted skills section HTML")
            logger.info(f"Skills HTML length: {len(self.skills_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating skills section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_recommendations(self) -> bool:
        """
        Navigate to the recommendations section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the recommendations section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "recommendations"):
                self.last_error = "Failed to navigate to recommendations section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.recommendations_html = self.driver.get_content()
            
            if not self.recommendations_html:
                self.last_error = "Failed to extract recommendations HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("recommendations")
            
            logger.info("Successfully extracted recommendations section HTML")
            logger.info(f"Recommendations HTML length: {len(self.recommendations_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating recommendations section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_courses(self) -> bool:
        """
        Navigate to the courses section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the courses section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "courses"):
                self.last_error = "Failed to navigate to courses section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.courses_html = self.driver.get_content()
            
            if not self.courses_html:
                self.last_error = "Failed to extract courses HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("courses")
            
            logger.info("Successfully extracted courses section HTML")
            logger.info(f"Courses HTML length: {len(self.courses_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating courses section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_languages(self) -> bool:
        """
        Navigate to the languages section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the languages section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "languages"):
                self.last_error = "Failed to navigate to languages section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.languages_html = self.driver.get_content()
            
            if not self.languages_html:
                self.last_error = "Failed to extract languages HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("languages")
            
            logger.info("Successfully extracted languages section HTML")
            logger.info(f"Languages HTML length: {len(self.languages_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating languages section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_interests(self) -> bool:
        """
        Navigate to the interests section and extract its HTML.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = "Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Navigate to the interests section using human-like behavior
            if not self.behavior.navigate_to_profile_section(self.profile_url, "interests"):
                self.last_error = "Failed to navigate to interests section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML
            self.interests_html = self.driver.get_content()
            
            if not self.interests_html:
                self.last_error = "Failed to extract interests HTML"
                logger.error(self.last_error)
                return False
            
            # Update metadata
            self.metadata["sections_scraped"].append("interests")
            
            logger.info("Successfully extracted interests section HTML")
            logger.info(f"Interests HTML length: {len(self.interests_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating interests section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def _extract_profile_name(self) -> None:
        """Extract the profile name from the current page."""
        try:
            # Use JavaScript to extract the name
            name = self.driver.evaluate("""
                () => {
                    // Try different selectors for the name
                    const nameSelectors = [
                        'h1.text-heading-xlarge',
                        'h1.pv-text-details__title',
                        'h1.top-card-layout__title',
                        'h1.inline'
                    ];
                    
                    for (const selector of nameSelectors) {
                        const nameElement = document.querySelector(selector);
                        if (nameElement && nameElement.textContent.trim()) {
                            return nameElement.textContent.trim();
                        }
                    }
                    
                    // Fallback to any h1 that seems like a name
                    const allH1s = Array.from(document.querySelectorAll('h1'));
                    for (const h1 of allH1s) {
                        const text = h1.textContent.trim();
                        if (text && text.length < 50 && !text.includes('LinkedIn')) {
                            return text;
                        }
                    }
                    
                    return '';
                }
            """)
            
            if name:
                self.profile_name = name
                # Update metadata
                self.metadata["profile_name"] = name
                logger.info(f"Extracted profile name: {name}")
            else:
                # Use the username from URL as fallback
                username = self.profile_url.split("/in/")[1].rstrip("/")
                self.profile_name = username
                self.metadata["profile_name"] = f"Unknown ({username})"
                logger.warning(f"Could not extract name, using username from URL: {username}")
                
        except Exception as e:
            logger.error(f"Error extracting profile name: {str(e)}")
            # Use the username from URL as fallback
            username = self.profile_url.split("/in/")[1].rstrip("/")
            self.profile_name = username
            self.metadata["profile_name"] = f"Unknown ({username})"
    
    def _check_authentication(self) -> None:
        """
        Check if we are authenticated on LinkedIn.
        
        This updates the is_authenticated flag based on page content.
        """
        try:
            # Look for elements that indicate we're logged in or logged out
            is_logged_in = self.driver.evaluate("""
                () => {
                    // Elements that indicate logged in state
                    const profileNav = document.querySelector('.global-nav__me');
                    const navBar = document.querySelector('nav.global-nav');
                    const profileSection = document.querySelector('.pv-top-card');
                    
                    // Elements that indicate logged out state
                    const loginForm = document.querySelector('form.login__form');
                    const joinNowButton = document.querySelector('a[data-tracking-control-name="guest_homepage-basic_join-now"]');
                    const signInButton = document.querySelector('a[data-tracking-control-name="guest_homepage-basic_sign-in"]');
                    
                    return !!(profileNav || navBar || profileSection) && !(loginForm || joinNowButton || signInButton);
                }
            """)
            
            self.is_authenticated = bool(is_logged_in)
            logger.info(f"Authentication check: {'Authenticated' if self.is_authenticated else 'Not authenticated'}")
            
        except Exception as e:
            logger.error(f"Error checking authentication: {str(e)}")
            self.is_authenticated = False
    
    def scrape_all_sections(self) -> bool:
        """
        Scrape all available profile sections.
        
        Returns:
            True if at least some sections were successfully scraped, False otherwise
        """
        success = False
        
        # Navigate to main profile first
        if self.navigate_profile():
            success = True
            
            # Navigate to other sections
            sections = [
                ("experience", self.navigate_experience),
                ("education", self.navigate_education),
                ("skills", self.navigate_skills),
                ("recommendations", self.navigate_recommendations),
                ("courses", self.navigate_courses),
                ("languages", self.navigate_languages),
                ("interests", self.navigate_interests)
            ]
            
            for section_name, section_method in sections:
                try:
                    logger.info(f"Scraping {section_name} section...")
                    section_method()
                    # Short pause between sections to avoid rate limiting
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error scraping {section_name} section: {str(e)}")
        
        return success
    
    def save_profile_data(self, base_dir: str = PROFILES_DIR) -> str:
        """
        Save all scraped profile data to files.
        
        Args:
            base_dir: Base directory for saving profile data
            
        Returns:
            Path to the profile directory where data was saved
        """
        # Sanitize profile name for file system use
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", self.profile_name)
        
        # Create profile directory
        profile_dir = os.path.join(base_dir, safe_name)
        os.makedirs(profile_dir, exist_ok=True)
        
        # Update metadata
        self.metadata["save_time"] = datetime.now().isoformat()
        
        # Save metadata
        metadata_file = os.path.join(profile_dir, f"{safe_name}_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
        
        # Save HTML files
        html_files = [
            ("main_profile", self.main_profile_html),
            ("experience", self.experience_html),
            ("education", self.education_html),
            ("skills", self.skills_html),
            ("recommendations", self.recommendations_html),
            ("courses", self.courses_html),
            ("languages", self.languages_html),
            ("interests", self.interests_html)
        ]
        
        for section_name, html_content in html_files:
            if html_content:
                html_file = os.path.join(profile_dir, f"{section_name}.html")
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
        
        logger.info(f"Saved profile data to {profile_dir}")
        return profile_dir
    
    def close(self) -> None:
        """Close the browser and clean up resources."""
        if self.driver and self.own_driver:
            try:
                self.driver.close()
                logger.info("Navigator closed successfully")
            except Exception as e:
                logger.error(f"Error closing navigator: {str(e)}")