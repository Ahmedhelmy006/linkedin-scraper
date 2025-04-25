# services/linkedin_navigator.py
"""
Enhanced LinkedIn Navigator module for scraping LinkedIn profiles.

This module handles LinkedIn navigation and content extraction,
working with the human-like behavior module to ensure natural interaction
while avoiding detection patterns.
"""

import logging
import re
import time
import os
import json
import random
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Set

from config.scraper_config import PROFILES_DIR
from utils.playwright_driver import PlaywrightDriver
from services.linked_navigator.human_like_behavior import HumanLikeBehavior

logger = logging.getLogger(__name__)

class LinkedInNavigator:
    """
    LinkedIn Profile Navigator.
    
    This class handles navigation to LinkedIn profiles and extraction
    of profile data, following human-like behavior patterns and avoiding
    detection through natural timing and navigation patterns.
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
        self.section_html = {}  # Store all section HTML by section name
        
        # Initialize metadata
        self.profile_name = ""
        self.metadata = {
            "profile_url": self.profile_url,
            "scrape_date": datetime.now().isoformat(),
            "sections_scraped": []
        }
        
        # Track sections available in the profile
        self.available_sections = set()
        self.section_links = {}  # Store actual URLs for sections
        
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
            
            # Occasionally visit a random site before navigating to the profile
            if random.random() < 0.3:  # 30% chance
                self.behavior.visit_random_site(duration_range=(30, 90))
            
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
            
            # Extract available section links from the main profile
            self._extract_section_links()
            
            # Read profile content with human-like behavior
            self.behavior.simulate_reading(min_duration=5.0, max_duration=15.0)
            
            logger.info("Successfully extracted main profile HTML")
            logger.info(f"Main profile HTML length: {len(self.main_profile_html)}")
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating profile: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def _extract_section_links(self) -> None:
        """Extract all available section links from the main profile HTML."""
        if not self.driver or not self.main_profile_html:
            return
            
        try:
            # Use JavaScript to extract section links
            section_links = self.driver.evaluate("""
                () => {
                    const sectionLinks = {};
                    const commonSections = [
                        'experience', 'education', 'skills', 'recommendations', 
                        'courses', 'languages', 'interests', 'certifications', 
                        'projects', 'publications', 'patents', 'volunteer'
                    ];
                    
                    // Look for explicit section links
                    document.querySelectorAll('a[href*="/details/"]').forEach(link => {
                        const href = link.href;
                        for (const section of commonSections) {
                            if (href.includes(`/details/${section}`)) {
                                sectionLinks[section] = href;
                                break;
                            }
                        }
                    });
                    
                    return sectionLinks;
                }
            """)
            
            if section_links and isinstance(section_links, dict):
                self.section_links = section_links
                self.available_sections = set(section_links.keys())
                logger.info(f"Extracted {len(self.available_sections)} section links: {', '.join(self.available_sections)}")
            else:
                logger.warning("No section links found in profile")
                
        except Exception as e:
            logger.error(f"Error extracting section links: {str(e)}")
    
    def navigate_section(self, section: str) -> bool:
        """
        Navigate to a specific profile section using extracted links or by name.
        
        Args:
            section: Section name (e.g., 'experience', 'education')
            
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.last_error = f"Driver not initialized. Call start() first."
            logger.error(self.last_error)
            return False
            
        if not self.main_profile_html:
            self.last_error = f"Main profile not loaded. Call navigate_profile() first."
            logger.error(self.last_error)
            return False
        
        try:
            # Check if section is available
            if section not in self.available_sections and section not in self.section_links:
                # Section not found in extracted links, check if we should try anyway
                # For the most common sections, try even if not found in links
                common_sections = {'experience', 'education', 'skills'}
                if section not in common_sections:
                    logger.info(f"Section '{section}' not available in profile, skipping")
                    return False
                    
                logger.warning(f"Section '{section}' not found in extracted links but is common, trying anyway")
            
            # Get section URL (either from extracted links or build it)
            section_url = None
            if section in self.section_links:
                section_url = self.section_links[section]
                logger.info(f"Using extracted section URL: {section_url}")
            
            # Navigate to the section
            success = False
            if section_url:
                # Use the exact extracted URL which includes query parameters
                success = self.behavior.navigate_to_profile_section(self.profile_url, section)
            else:
                # Fallback to standard navigation
                success = self.behavior.navigate_to_profile_section(self.profile_url, section)
            
            if not success:
                self.last_error = f"Failed to navigate to {section} section"
                logger.error(self.last_error)
                return False
            
            # Extract the HTML with variable timeout for randomization
            random_pause = random.uniform(0.5, 2.0)
            time.sleep(random_pause)
            html_content = self.driver.get_content()
            
            if not html_content:
                self.last_error = f"Failed to extract {section} HTML"
                logger.error(self.last_error)
                return False
            
            # Store the section HTML
            self.section_html[section] = html_content
            
            # Update metadata
            if section not in self.metadata["sections_scraped"]:
                self.metadata["sections_scraped"].append(section)
            
            # Read section content with human-like behavior
            reading_duration = random.uniform(3.0, 10.0)
            self.behavior.simulate_reading(min_duration=reading_duration, max_duration=reading_duration * 1.5)
            
            logger.info(f"Successfully extracted {section} section HTML")
            logger.info(f"{section.capitalize()} HTML length: {len(html_content)}")
            
            # Navigate back to main profile using back button
            self.behavior.navigate_back_to_profile()
            
            # Variable pause after returning to main profile
            time.sleep(random.uniform(1.0, 3.5))
            
            return True
            
        except Exception as e:
            self.last_error = f"Error navigating {section} section: {str(e)}"
            logger.error(self.last_error, exc_info=True)
            return False
    
    def navigate_experience(self) -> bool:
        """Navigate to the experience section."""
        return self.navigate_section('experience')
    
    def navigate_education(self) -> bool:
        """Navigate to the education section."""
        return self.navigate_section('education')
    
    def navigate_skills(self) -> bool:
        """Navigate to the skills section."""
        return self.navigate_section('skills')
    
    def navigate_recommendations(self) -> bool:
        """Navigate to the recommendations section."""
        return self.navigate_section('recommendations')
    
    def navigate_courses(self) -> bool:
        """Navigate to the courses section."""
        return self.navigate_section('courses')
    
    def navigate_languages(self) -> bool:
        """Navigate to the languages section."""
        return self.navigate_section('languages')
    
    def navigate_interests(self) -> bool:
        """Navigate to the interests section."""
        return self.navigate_section('interests')
    
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
        Scrape all available profile sections based on detected links.
        
        Returns:
            True if at least some sections were successfully scraped, False otherwise
        """
        success = False
        
        # Navigate to main profile first
        if self.navigate_profile():
            success = True
            
            # Get the available sections from the profile
            available_sections = list(self.available_sections)
            
            # If no sections were detected, try common ones
            if not available_sections:
                logger.warning("No sections detected in profile, trying common sections")
                available_sections = ['experience', 'education', 'skills']
            
            # Shuffle the sections to make the scraping pattern less predictable
            random.shuffle(available_sections)
            
            # Keep track of sections processed
            sections_processed = 0
            
            # Process each section
            for section in available_sections:
                try:
                    # Occasionally visit a random site between sections (20% chance)
                    if random.random() < 0.2 and sections_processed > 0:
                        logger.info("Taking a break by visiting a random site")
                        self.behavior.visit_random_site(duration_range=(30, 90))
                        
                        # Return to profile
                        if not self.behavior.navigate_to_profile(self.profile_url):
                            logger.warning("Failed to return to profile after random site visit")
                            time.sleep(random.uniform(1.5, 3.0))
                    
                    logger.info(f"Scraping {section} section...")
                    
                    # Add a variable pause between sections
                    if sections_processed > 0:
                        time.sleep(random.uniform(1.5, 4.5))
                    
                    # Navigate to the section
                    self.navigate_section(section)
                    sections_processed += 1
                    
                    # Decide if we should continue or stop (to make it more natural)
                    # As we process more sections, increase the chance of stopping
                    stop_chance = 0.1 * sections_processed
                    if random.random() < stop_chance and sections_processed >= 3:
                        logger.info(f"Naturally stopping after {sections_processed} sections")
                        break
                    
                except Exception as e:
                    logger.error(f"Error scraping {section} section: {str(e)}")
                    # Continue with next section
            
            # Final reading of the profile
            if sections_processed > 0:
                # Return to main profile if we processed any sections
                if not self.behavior.navigate_to_profile(self.profile_url):
                    logger.warning("Failed to return to main profile after scraping sections")
                
                # Final reading of the profile
                self.behavior.simulate_reading(min_duration=3.0, max_duration=8.0)
        
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
        
        # Update metadata with final information
        self.metadata["save_time"] = datetime.now().isoformat()
        self.metadata["available_sections"] = list(self.available_sections)
        self.metadata["sections_scraped"] = self.metadata["sections_scraped"]
        
        # Add device and browser information to metadata
        try:
            device_info = self.driver.evaluate("""
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        screenWidth: window.screen.width,
                        screenHeight: window.screen.height,
                        devicePixelRatio: window.devicePixelRatio,
                        language: navigator.language,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    };
                }
            """)
            
            if device_info:
                self.metadata["device_info"] = device_info
        except Exception as e:
            logger.error(f"Error getting device info: {str(e)}")
        
        # Save metadata
        metadata_file = os.path.join(profile_dir, f"{safe_name}_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
        
        # Save main profile HTML
        if self.main_profile_html:
            main_profile_file = os.path.join(profile_dir, "main_profile.html")
            with open(main_profile_file, 'w', encoding='utf-8') as f:
                f.write(self.main_profile_html)
        
        # Save section HTML files
        for section_name, html_content in self.section_html.items():
            if html_content:
                section_file = os.path.join(profile_dir, f"{section_name}.html")
                with open(section_file, 'w', encoding='utf-8') as f:
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
                
    def __del__(self):
        """Destructor to ensure browser is closed."""
        self.close()