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
from typing import Optional, Dict, Any, List, Tuple
import random

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
            
            # Allow a randomized time for page to stabilize (between 1.0 and 3.4 seconds with millisecond precision)
            time.sleep(1.0 + random.random() * 2.4)
            
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
            
            # Allow a very short time for page to stabilize
            time.sleep(1)
            
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
            
            # Allow a very short time for page to stabilize
            time.sleep(1)
            
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
            
            # Allow a very short time for page to stabilize
            time.sleep(1)
            
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
            
            # Allow a very short time for page to stabilize
            time.sleep(1)
            
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
            
            # Allow a very short time for page to stabilize
            time.sleep(1)
            
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
            
            # Allow a very short time for page to stabilize
            time.sleep(1)
            
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
            # We'll check for authentication by examining the HTML content
            current_html = self.driver.get_content()
            
            # Simple content-based checks rather than waiting for selectors
            if current_html:
                # If HTML contains elements typically only visible when logged in
                logged_in_indicators = [
                    'global-nav__me',
                    'feed-identity-module',
                    'artdeco-entity-lockup',
                    'profile-picture'
                ]
                
                logged_out_indicators = [
                    'login__form',
                    'join-now',
                    'sign-in',
                    'guest_homepage'
                ]
                
                has_logged_in = any(indicator in current_html for indicator in logged_in_indicators)
                has_logged_out = any(indicator in current_html for indicator in logged_out_indicators)
                
                self.is_authenticated = has_logged_in and not has_logged_out
            else:
                self.is_authenticated = False
            
            logger.info(f"Authentication check: {'Authenticated' if self.is_authenticated else 'Not authenticated'}")
            
        except Exception as e:
            logger.error(f"Error checking authentication: {str(e)}")
            self.is_authenticated = False
    
    def scrape_all_sections(self) -> bool:
        """
        Scrape all available profile sections intelligently by extracting section URLs from HTML.
        
        Returns:
            True if at least some sections were successfully scraped, False otherwise
        """
        success = False
        
        # Navigate to main profile first
        if self.navigate_profile():
            success = True
            
            # Extract section URLs from the main profile HTML
            section_urls = self._extract_section_urls()
            logger.info(f"Extracted section URLs: {section_urls}")
            
            # Skip languages and interests sections as requested
            if "languages" in section_urls:
                del section_urls["languages"]
            if "interests" in section_urls:
                del section_urls["interests"]
                
            # Process each section with its direct URL
            for section_name, section_url in section_urls.items():
                try:
                    logger.info(f"Processing section: {section_name} with URL: {section_url}")
                    
                    # Navigate to the section using the extracted URL
                    if self._navigate_to_section_url(section_url):
                        # Store the HTML based on section name
                        self._store_section_html(section_name)
                        
                        # Return to main profile using the back button
                        self._click_back_button()
                        
                        # Randomized pause between section navigations
                        time.sleep(1.5 + random.random() * 2.8)
                    else:
                        logger.warning(f"Failed to navigate to section: {section_name}")
                except Exception as e:
                    logger.error(f"Error processing {section_name} section: {str(e)}")
        
        return success

    def _extract_section_urls(self) -> Dict[str, str]:
        """
        Extract section URLs directly from the profile HTML.
        
        Looks for URLs containing the profileUrn parameter.
        
        Returns:
            Dictionary mapping section names to their full URLs
        """
        section_urls = {}
        
        # Define regex pattern to find section URLs with profileUrn
        import re
        
        # Look for links to different sections
        section_types = ["experience", "education", "skills", "recommendations", "courses"]
        
        for section in section_types:
            # Pattern to match section URLs with profileUrn
            pattern = rf'href="(https://www\.linkedin\.com/in/[^/]+/details/{section}\?profileUrn=urn[^"]+)"'
            matches = re.findall(pattern, self.main_profile_html)
            
            if matches:
                # Use the first match for each section type
                section_urls[section] = matches[0]
        
        return section_urls

    def _navigate_to_section_url(self, url: str) -> bool:
        """
        Navigate directly to a section URL.
        
        Args:
            url: Complete section URL including profileUrn
            
        Returns:
            True if navigation was successful, False otherwise
        """
        if not self.driver:
            logger.error("Driver not initialized. Cannot navigate to section URL.")
            return False
        
        try:
            # Add randomized delay before navigation (1.0 to 3.4 seconds with millisecond precision)
            delay = 1.0 + random.random() * 2.4
            logger.info(f"Waiting {delay:.2f} seconds before navigation...")
            time.sleep(delay)
            
            # Navigate to the URL
            logger.info(f"Navigating to section URL: {url}")
            if not self.driver.navigate(url, wait_until="domcontentloaded"):
                logger.error("Failed to navigate to section URL")
                return False
            
            # Allow a randomized time for page to stabilize (between 1.0 and 3.4 seconds with millisecond precision)
            time.sleep(1.0 + random.random() * 2.4)
            
            return True
        except Exception as e:
            logger.error(f"Error navigating to section URL: {str(e)}")
            return False

    def _store_section_html(self, section_name: str) -> None:
        """
        Store the HTML content for a specific section.
        
        Args:
            section_name: Name of the section (experience, education, etc.)
        """
        try:
            html_content = self.driver.get_content()
            
            if not html_content:
                logger.warning(f"No HTML content retrieved for {section_name} section")
                return
                
            # Store the HTML based on section type
            if section_name == "experience":
                self.experience_html = html_content
            elif section_name == "education":
                self.education_html = html_content
            elif section_name == "skills":
                self.skills_html = html_content
            elif section_name == "recommendations":
                self.recommendations_html = html_content
            elif section_name == "courses":
                self.courses_html = html_content
            elif section_name == "languages":
                self.languages_html = html_content
            elif section_name == "interests":
                self.interests_html = html_content
            
            # Update metadata
            if section_name not in self.metadata["sections_scraped"]:
                self.metadata["sections_scraped"].append(section_name)
                
            logger.info(f"Successfully stored HTML for {section_name} section")
            logger.info(f"{section_name.capitalize()} HTML length: {len(html_content)}")
        except Exception as e:
            logger.error(f"Error storing HTML for {section_name} section: {str(e)}")

    def _click_back_button(self) -> bool:
        """
        Click the back button to return to the main profile.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            logger.error("Driver not initialized. Cannot click back button.")
            return False
        
        try:
            # Use JavaScript to find and click the back button
            clicked = self.driver.evaluate("""
                () => {
                    // Look for the back button using various attributes
                    const backButton = document.querySelector('button[aria-label="Back to the main profile page"]') || 
                                    document.querySelector('button[aria-label*="Back"]') || 
                                    document.querySelector('button.artdeco-button--circle svg[data-test-icon="arrow-left-medium"]').closest('button');
                    
                    if (backButton) {
                        // Add a small delay before clicking to appear more human-like
                        setTimeout(() => {
                            backButton.click();
                        }, Math.random() * 500 + 300);
                        return true;
                    }
                    return false;
                }
            """)
            
            if clicked:
                logger.info("Successfully clicked back button")
                # Allow a randomized time for main profile to reload (between 1.0 and 3.4 seconds with millisecond precision)
                time.sleep(1.0 + random.random() * 2.4)
                
                # Update the main profile HTML after returning
                updated_html = self.driver.get_content()
                if updated_html:
                    self.main_profile_html = updated_html
                
                return True
            else:
                logger.warning("Back button not found, will try direct navigation to profile")
                # Fall back to direct navigation
                return self.behavior.navigate_to_profile(self.profile_url)
        except Exception as e:
            logger.error(f"Error clicking back button: {str(e)}")
            return False
    
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