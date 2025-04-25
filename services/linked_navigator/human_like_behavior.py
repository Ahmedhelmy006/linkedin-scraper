# services/linked_navigator/human_like_behavior.py
"""
Human-like behavior implementation for LinkedIn navigation.

This module provides behaviors that mimic human interaction patterns
for browsing LinkedIn, including natural scrolling, mouse movements,
timing variations, and session behavior.
"""

import logging
import random
import time
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Callable, Union
import threading
import webbrowser

from config.scraper_config import (
    LINKEDIN_FEED_URL, FEED_BROWSING_DURATION, SCROLL_PAUSE_TIME,
    PROFILE_NAVIGATION_DELAY, EVENTS, STATES, RANDOM_SITES
)
from utils.event_bus import EventBus
from utils.state_machine import StateMachine
from utils.playwright_driver import PlaywrightDriver

logger = logging.getLogger(__name__)

class HumanLikeBehavior:
    """
    Implements human-like browsing behaviors for LinkedIn interaction.
    
    This class enhances the LinkedIn Navigator with natural human-like
    behaviors such as feed browsing, natural scrolling, and realistic timing.
    """
    
    def __init__(self, driver: Optional[PlaywrightDriver] = None):
        """
        Initialize the human-like behavior controller.
        
        Args:
            driver: Optional PlaywrightDriver instance
        """
        self.driver = driver
        self.event_bus = EventBus.get_instance()
        self.state_machine = StateMachine()  # Using shared state machine
        
        # Last interaction tracking
        self.last_scroll_time = None
        self.last_click_time = None
        self.last_mouse_move_time = None
        
        # Session behavior tracking
        self.session_start_time = None
        self.is_morning = False
        self.is_evening = False
        self.is_late_evening = False
        
        # Random range generator with millisecond precision
        self.random_range = lambda min_val, max_val: random.uniform(min_val, max_val)
    
    def set_driver(self, driver: PlaywrightDriver) -> None:
        """
        Set the PlaywrightDriver instance.
        
        Args:
            driver: PlaywrightDriver instance
        """
        self.driver = driver
        self.session_start_time = datetime.now()
        self._determine_time_of_day()

    def check_notifications(self) -> bool:
        """
        Visit and check the LinkedIn notifications page like a human would.
        
        Returns:
            True if notifications check completed successfully, False otherwise
        """
        if not self.driver:
            logger.error("Driver not set. Cannot check notifications.")
            return False
        
        try:
            logger.info("Checking LinkedIn notifications...")
            
            # Navigate to the notifications page
            notifications_url = "https://www.linkedin.com/notifications/?filter=all"
            if not self.driver.navigate(notifications_url, wait_until="domcontentloaded"):
                logger.error("Failed to navigate to notifications page")
                return False
            
            # Wait for notifications to load with variable timeout
            random_timeout = int(self.random_range(5000, 10000))  # 5-10 seconds
            notifications_loaded = self.driver.wait_for_selector(
                ".notification-container, .artdeco-empty-state, .notification-list", 
                timeout=random_timeout
            )
            
            if not notifications_loaded:
                logger.warning(f"Notification elements not detected after {random_timeout/1000}s, proceeding anyway")
                # Variable wait instead of fixed time
                time.sleep(self.random_range(2.145, 4.862))
            
            # Read notifications for a random duration
            read_duration = self.random_range(5, 15)
            logger.info(f"Reading notifications for {read_duration:.2f} seconds")
            
            # Scroll slowly through the notifications
            self._scroll_with_human_behavior(duration=read_duration, scroll_range=(100, 300))
            
            # Sometimes click on a notification (30% chance)
            if random.random() < 0.3:
                logger.info("Attempting to click on a random notification")
                notification_clicked = self.driver.evaluate("""
                    () => {
                        // Find all notification items
                        const notifications = document.querySelectorAll('.notification-item, .artdeco-card, .nt-card');
                        if (notifications.length === 0) return false;
                        
                        // Select a random notification
                        const randomIndex = Math.floor(Math.random() * Math.min(notifications.length, 5));
                        const randomNotification = notifications[randomIndex];
                        
                        // Attempt to click it
                        if (randomNotification) {
                            // Find a clickable element within the notification
                            const clickable = randomNotification.querySelector('a, button') || randomNotification;
                            clickable.click();
                            return true;
                        }
                        return false;
                    }
                """)
                
                if notification_clicked:
                    logger.info("Clicked on a notification")
                    # Wait a bit to view the notification content
                    time.sleep(self.random_range(4.5, 12.3))
                    
                    # Go back to notifications
                    self.driver.navigate(notifications_url)
                    time.sleep(self.random_range(1.5, 3.2))
            
            logger.info("Notifications check completed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking notifications: {str(e)}")
            return False
    
    def _determine_time_of_day(self) -> None:
        """Determine the time of day to adjust behavior accordingly."""
        current_hour = datetime.now().hour
        
        self.is_morning = 8 <= current_hour < 11
        self.is_evening = 16 <= current_hour < 20
        self.is_late_evening = 20 <= current_hour < 23
        
        logger.info(f"Session time period: {'Morning' if self.is_morning else 'Evening' if self.is_evening else 'Late evening' if self.is_late_evening else 'Afternoon'}")
    
    def browse_feed(self, min_duration: Optional[float] = None, max_duration: Optional[float] = None) -> bool:
        """
        Browse the LinkedIn feed like a human would.
        
        Args:
            min_duration: Minimum browsing duration in seconds
            max_duration: Maximum browsing duration in seconds
            
        Returns:
            True if feed browsing completed successfully, False otherwise
        """
        if not self.driver:
            logger.error("Driver not set. Cannot browse feed.")
            return False
        
        # Apply probabilistic duration selection
        duration = self._get_feed_browsing_duration()
        
        try:
            # Transition state
            self.state_machine.transition(STATES["FEED_BROWSING"], "Starting feed browsing")
            
            # Navigate to feed
            logger.info(f"Navigating to LinkedIn feed for {duration:.3f} seconds browsing")
            if not self.driver.navigate(LINKEDIN_FEED_URL, wait_until="domcontentloaded"):
                logger.error("Failed to navigate to LinkedIn feed")
                return False
            
            # Wait for feed to load - but with variable timeout
            random_timeout = int(self.random_range(5000, 12000))  # 5-12 seconds
            feed_loaded = self.driver.wait_for_selector(
                ".feed-shared-update-v2, .scaffold-layout", 
                timeout=random_timeout
            )
            
            if not feed_loaded:
                logger.warning(f"Feed elements not detected after {random_timeout/1000}s, proceeding anyway")
                # Variable wait instead of fixed 5 seconds
                time.sleep(self.random_range(3.145, 7.862))
            
            # First check notifications (80% chance)
            if random.random() < 0.8:
                self.check_notifications()
                
                # Return to feed after checking notifications
                if not self.driver.navigate(LINKEDIN_FEED_URL, wait_until="domcontentloaded"):
                    logger.error("Failed to return to LinkedIn feed after checking notifications")
                    return False
                    
                # Short delay after returning to feed
                time.sleep(self.random_range(1.2, 3.7))
            
            # Scroll feed for specified duration
            self._scroll_with_human_behavior(duration=duration)
            
            # Occasionally engage with content (like/comment visibility)
            if random.random() < 0.4:  # 40% chance
                self._simulate_content_engagement()
            
            logger.info(f"Feed browsing completed after {duration:.3f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error browsing feed: {str(e)}")
            return False
    
    def _get_feed_browsing_duration(self) -> float:
        """
        Get feed browsing duration based on probability distribution.
        
        Returns:
            Duration in seconds
        """
        rand = random.random()
        
        if rand < 0.6:  # 60% probability
            return self.random_range(45, 90)
        elif rand < 0.8:  # 20% probability
            return self.random_range(75.3, 180.7)
        elif rand < 0.9:  # 10% probability
            return self.random_range(180.74, 240.873)
        elif rand < 0.95:  # 5% probability
            return self.random_range(10, 18.45)
        else:  # 5% probability
            return self.random_range(240.64, 400)
    
    def navigate_to_profile(self, profile_url: str) -> bool:
        """
        Navigate to a LinkedIn profile with human-like delays.
        
        Args:
            profile_url: Profile URL to navigate to
            
        Returns:
            True if navigation was successful, False otherwise
        """
        if not self.driver:
            logger.error("Driver not set. Cannot navigate to profile.")
            return False
        
        try:
            # Add natural delay before navigating with millisecond precision
            delay = self.random_range(PROFILE_NAVIGATION_DELAY[0], PROFILE_NAVIGATION_DELAY[1])
            logger.info(f"Waiting {delay:.3f} seconds before navigating to profile")
            time.sleep(delay)
            
            # Transition state
            self.state_machine.transition(
                STATES["PROFILE_SCRAPING"],
                f"Navigating to profile {profile_url}"
            )
            
            # Navigate to profile
            logger.info(f"Navigating to profile: {profile_url}")
            if not self.driver.navigate(profile_url, wait_until="domcontentloaded"):
                logger.error(f"Failed to navigate to profile: {profile_url}")
                return False
            
            # Wait for profile to load with variable timeout
            random_timeout = int(self.random_range(8000, 15000))  # 8-15 seconds
            profile_loaded = self.driver.wait_for_selector(
                "h1.text-heading-xlarge, h1.pv-text-details__title, .pv-top-card",
                timeout=random_timeout
            )
            
            if not profile_loaded:
                logger.warning(f"Profile elements not detected after {random_timeout/1000}s, proceeding anyway")
                time.sleep(self.random_range(3.421, 6.937))
            
            # Verify we're on the right profile page
            current_url = self.driver.evaluate("() => window.location.href")
            if profile_url not in current_url:
                logger.warning(f"Expected to be on {profile_url} but current URL is {current_url}")
            
            # Variable chance of scrolling
            if random.random() < 0.8:  # 80% chance
                scroll_duration = self.random_range(5, 15)
                self._scroll_with_human_behavior(duration=scroll_duration)
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to profile: {str(e)}")
            return False

    def navigate_to_profile_section(self, profile_url: str, section: str) -> bool:
        """
        Navigate to a specific section of a LinkedIn profile.
        
        Args:
            profile_url: Base profile URL
            section: Section name (e.g., 'experience', 'education')
            
        Returns:
            True if navigation was successful, False otherwise
        """
        if not self.driver:
            logger.error("Driver not set. Cannot navigate to profile section.")
            return False
        
        try:
            # Extract section link from the main profile page instead of building URL
            section_url = self._extract_section_link(section)
            
            if not section_url:
                logger.warning(f"Could not find link for {section} section in profile page")
                # Fallback to standard URL building
                section_url = f"{profile_url}/details/{section}/"
                logger.info(f"Using fallback URL: {section_url}")
            
            # Add natural delay before navigating
            delay = self.random_range(2, 5)
            logger.info(f"Waiting {delay:.3f} seconds before navigating to {section} section")
            time.sleep(delay)
            
            # Navigate to section
            logger.info(f"Navigating to {section} section: {section_url}")
            if not self.driver.navigate(section_url, wait_until="domcontentloaded"):
                logger.error(f"Failed to navigate to {section} section")
                return False
            
            # Wait for section to load with variable timeout
            random_timeout = int(self.random_range(5000, 10000))  # 5-10 seconds
            section_loaded = self.driver.wait_for_selector(
                f".{section}-section, section#{section}-section, .pvs-list",
                timeout=random_timeout
            )
            
            if not section_loaded:
                logger.warning(f"{section.capitalize()} section elements not detected after {random_timeout/1000}s, proceeding anyway")
                time.sleep(self.random_range(2.173, 4.864))
            
            # Verify we're on the right section page
            current_url = self.driver.evaluate("() => window.location.href")
            if section not in current_url:
                logger.warning(f"Expected to be on {section} section but current URL is {current_url}")
            
            # Sometimes scroll section with pauses
            if random.random() < 0.7:  # 70% chance
                scroll_duration = self.random_range(3, 10)
                logger.info(f"Scrolling {section} section for {scroll_duration:.3f} seconds")
                self._scroll_with_human_behavior(duration=scroll_duration)
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to profile section: {str(e)}")
            return False
    
    def _extract_section_link(self, section: str) -> Optional[str]:
        """
        Extract section link from the main profile page.
        
        Args:
            section: Section name to find
            
        Returns:
            Section URL if found, None otherwise
        """
        if not self.driver:
            return None
        
        try:
            # Try to find the link on the page with different strategies
            link = self.driver.evaluate(f"""
                () => {{
                    // Strategy 1: Look for section-specific links
                    const sectionLinkSelectors = [
                        'a[href*="/details/{section}"]',
                        'a[data-control-name="{section}_tab"]',
                        'a[href*="#{section}"]'
                    ];
                    
                    for (const selector of sectionLinkSelectors) {{
                        const links = Array.from(document.querySelectorAll(selector));
                        for (const link of links) {{
                            if (link.href) return link.href;
                        }}
                    }}
                    
                    // Strategy 2: Look through all links with specific text content
                    const allLinks = Array.from(document.querySelectorAll('a'));
                    const sectionTerms = ['{section}', '{section.capitalize()}'];
                    
                    for (const link of allLinks) {{
                        const linkText = link.textContent.toLowerCase().trim();
                        if (sectionTerms.some(term => linkText.includes(term.toLowerCase())) && link.href) {{
                            return link.href;
                        }}
                    }}
                    
                    return null;
                }}
            """)
            
            return link
            
        except Exception as e:
            logger.error(f"Error extracting section link for {section}: {str(e)}")
            return None
    
    def navigate_back_to_profile(self) -> bool:
        """
        Navigate back to the main profile from a section.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            return False
            
        try:
            # Look for back button
            back_button_found = self.driver.evaluate("""
                () => {
                    // Try different selectors for back button
                    const backSelectors = [
                        'button[aria-label="Back to the main profile page"]',
                        'a[data-control-name="back_to_profile"]',
                        'a.profile-section-card__back-to-profile'
                    ];
                    
                    for (const selector of backSelectors) {
                        const backButton = document.querySelector(selector);
                        if (backButton) {
                            backButton.click();
                            return true;
                        }
                    }
                    
                    // Try looking for elements with text about going back to profile
                    const allButtons = Array.from(document.querySelectorAll('button, a'));
                    for (const button of allButtons) {
                        const text = button.textContent.toLowerCase();
                        if (text.includes('back to profile') || text.includes('return to profile')) {
                            button.click();
                            return true;
                        }
                    }
                    
                    return false;
                }
            """)
            
            if back_button_found:
                logger.info("Clicked back button to return to main profile")
                # Wait for navigation with variable timeout
                time.sleep(self.random_range(1.5, 4.2))
                return True
            else:
                logger.warning("Back button not found, using browser history")
                return self.driver.evaluate("() => { window.history.back(); return true; }")
                
        except Exception as e:
            logger.error(f"Error navigating back to profile: {str(e)}")
            return False
    
    def _scroll_with_human_behavior(self, duration: float = 30.0) -> None:
        """
        Scroll the page with human-like behavior, primarily downward.
        
        Args:
            duration: Duration to scroll in seconds
        """
        if not self.driver:
            logger.error("Driver not set. Cannot perform scrolling.")
            return
        
        try:
            # Apply time-of-day adjustments to scroll behavior
            scroll_speed_factor = self._get_time_adjusted_scroll_speed()
            pause_duration_factor = self._get_time_adjusted_pause_duration()
            
            end_time = time.time() + duration
            total_scrolled = 0
            consecutive_scrolls = 0
            
            # Calculate page height for relative scrolling
            page_height = self.driver.evaluate("() => document.body.scrollHeight") or 5000
            
            while time.time() < end_time:
                # Determine scroll speed based on probability
                scroll_speed = self._get_probabilistic_scroll_speed() * scroll_speed_factor
                
                # Determine scroll direction - overwhelmingly downward
                # Only 5% chance of scrolling up, and only after at least 3 downward scrolls
                scroll_up = False
                if consecutive_scrolls >= 3 and random.random() < 0.05:  # 5% chance after 3+ downward scrolls
                    scroll_up = True
                    consecutive_scrolls = 0
                else:
                    consecutive_scrolls += 1
                
                # Determine scroll distance based on speed and a random factor
                base_distance = scroll_speed * self.random_range(0.3, 0.7)
                
                # If scrolling up, use a much smaller distance (10-30% of downward scroll)
                if scroll_up:
                    reverse_amount = base_distance * self.random_range(0.1, 0.3)
                    self._perform_smooth_scroll(-reverse_amount)
                    total_scrolled -= reverse_amount
                    logger.debug(f"Scrolling UP {reverse_amount:.0f}px")
                    # Shorter pause after scrolling up
                    time.sleep(self.random_range(0.3, 0.8))
                    continue
                
                # Perform the scroll with bezier curve motion
                self._perform_smooth_scroll(base_distance)
                total_scrolled += base_distance
                logger.debug(f"Scrolling DOWN {base_distance:.0f}px")
                
                # Record last scroll time
                self.last_scroll_time = time.time()
                
                # Sometimes move the mouse while scrolling
                if random.random() < 0.3:  # 30% chance
                    self._simulate_mouse_movement()
                
                # Determine pause behavior
                if total_scrolled > self.random_range(1000, 2000) and random.random() < 0.7:
                    # 70% chance for a 1-3 second pause, adjusted by time of day
                    pause_time = self.random_range(1, 3) * pause_duration_factor
                    logger.debug(f"Pausing scroll for {pause_time:.3f}s after scrolling {total_scrolled:.0f}px")
                    time.sleep(pause_time)
                    total_scrolled = 0  # Reset scroll counter
                elif random.random() < 0.2:
                    # 20% chance for a 3-7 second pause (reading interesting content)
                    pause_time = self.random_range(3, 7) * pause_duration_factor
                    logger.debug(f"Reading pause for {pause_time:.3f}s")
                    time.sleep(pause_time)
                elif random.random() < 0.1:
                    # 10% chance for a micro-pause
                    pause_time = self.random_range(0.3, 0.8)
                    time.sleep(pause_time)
                else:
                    # Normal pause between scrolls
                    pause_time = self.random_range(SCROLL_PAUSE_TIME[0], SCROLL_PAUSE_TIME[1])
                    time.sleep(pause_time)
                    
                # Check if we're near the bottom of the page
                current_position = self.driver.evaluate("() => window.scrollY")
                if current_position and page_height and current_position > page_height * 0.85:
                    logger.debug("Near bottom of page, recalculating page height")
                    page_height = self.driver.evaluate("() => document.body.scrollHeight") or page_height
                    
                    # Sometimes longer pause at bottom of page
                    if random.random() < 0.4:  # 40% chance
                        time.sleep(self.random_range(1.5, 4.5))
                    
                    # If we're really at the bottom, break
                    if current_position > page_height * 0.95:
                        logger.debug("Reached bottom of page, ending scroll")
                        break
                    
        except Exception as e:
            logger.error(f"Error during human-like scrolling: {str(e)}")
    
    def _get_probabilistic_scroll_speed(self) -> float:
        """
        Get scroll speed based on probability distribution.
        
        Returns:
            Scroll speed in pixels per second
        """
        rand = random.random()
        
        if rand < 0.5:  # 50% probability - medium speed
            return self.random_range(300, 600)
        elif rand < 0.8:  # 30% probability - slow, careful reading
            return self.random_range(150, 300)
        elif rand < 0.95:  # 15% probability - skimming content
            return self.random_range(600, 900)
        else:  # 5% probability - fast scrolling
            return self.random_range(900, 1200)
    
    def _get_time_adjusted_scroll_speed(self) -> float:
        """
        Get time-of-day adjusted scroll speed factor.
        
        Returns:
            Multiplier for scroll speed
        """
        if self.is_morning:
            return 0.85  # 15% slower in the morning
        elif self.is_evening:
            return 1.10  # 10% faster in the evening
        elif self.is_late_evening:
            return 1.20  # 20% faster in late evening
        else:
            return 1.0  # Normal speed in the afternoon
    
    def _get_time_adjusted_pause_duration(self) -> float:
        """
        Get time-of-day adjusted pause duration factor.
        
        Returns:
            Multiplier for pause duration
        """
        if self.is_morning:
            return 1.20  # 20% longer pauses in the morning
        elif self.is_evening:
            return 0.85  # 15% shorter pauses in the evening
        elif self.is_late_evening:
            return 0.75  # 25% shorter pauses in late evening
        else:
            return 1.0  # Normal pauses in the afternoon
    
    def _perform_smooth_scroll(self, distance: float) -> None:
        """
        Perform a smooth scroll with acceleration and deceleration.
        
        Args:
            distance: Scroll distance in pixels (positive for down, negative for up)
        """
        if not self.driver:
            return
            
        # Convert to integer for JavaScript
        distance = int(distance)
        
        # Adjust number of steps based on distance - more steps for larger distances
        min_steps = 10
        max_steps = 25
        steps_factor = abs(distance) / 500  # Scale based on distance
        steps_range = (
            min(max(int(min_steps * steps_factor), min_steps), max_steps),
            min(max(int(max_steps * steps_factor), min_steps), max_steps * 2)
        )
        
        self.driver.evaluate(f"""
            () => {{
                // Calculate steps for smooth scrolling with bezier ease
                const distance = {distance};
                const steps = Math.floor({self.random_range(steps_range[0], steps_range[1])});
                const delay = Math.floor({self.random_range(5, 15)});
                
                // Function to scroll smoothly with natural acceleration
                const smoothScroll = async (steps, distance) => {{
                    // Create an acceleration curve
                    const easingFactor = t => {{
                        // Use bezier curve for more natural movement
                        // Start slow, accelerate in middle, decelerate at end
                        return t < 0.3
                            ? 3 * t * t
                            : t > 0.7
                                ? 3 * (1-t) * (1-t)
                                : 1;
                    }};
                    
                    let totalScrolled = 0;
                    
                    for (let i = 0; i < steps; i++) {{
                        const progress = i / (steps - 1);
                        const easing = easingFactor(progress);
                        
                        // Calculate how much to scroll in this step
                        const targetScrolled = distance * progress;
                        const stepScroll = Math.round(targetScrolled - totalScrolled);
                        
                        if (stepScroll !== 0) {{
                            window.scrollBy(0, stepScroll);
                            totalScrolled += stepScroll;
                        }}
                        
                        await new Promise(r => setTimeout(r, delay));
                    }}
                }};
                
                // Execute the smooth scroll
                smoothScroll(steps, distance);
            }}
        """)
    
    def _simulate_mouse_movement(self) -> None:
        """Simulate human-like mouse movements with Bézier curves, hesitations, and variable speeds."""
        if not self.driver:
            logger.error("Driver not set. Cannot simulate mouse movement.")
            return
        
        try:
            # Get page dimensions
            dimensions = self.driver.evaluate("""
                () => {
                    return {
                        width: document.documentElement.clientWidth,
                        height: document.documentElement.clientHeight
                    };
                }
            """)
            
            if not dimensions:
                logger.warning("Could not get page dimensions, using defaults")
                dimensions = {"width": 1366, "height": 768}
            
            # Generate random target coordinates
            x = random.randint(100, dimensions["width"] - 100)
            y = random.randint(100, dimensions["height"] - 100)
            
            # Generate a random speed between 400-1200px/second
            speed = self.random_range(400, 1200)
            
            # Determine if we'll have hesitations (10% chance)
            has_hesitation = random.random() < 0.1
            
            # Determine if we'll have overshooting (5% chance)
            has_overshooting = random.random() < 0.05
            
            if has_overshooting:
                overshoot_x = x + random.randint(5, 15) * (1 if random.random() < 0.5 else -1)
                overshoot_y = y + random.randint(5, 15) * (1 if random.random() < 0.5 else -1)
            else:
                overshoot_x = x
                overshoot_y = y
            
            # Move mouse with human-like motion
            self.driver.evaluate(f"""
                () => {{
                    // Create a custom mouse event
                    const moveMouse = (x, y) => {{
                        const event = new MouseEvent('mousemove', {{
                            'view': window,
                            'bubbles': true,
                            'cancelable': true,
                            'clientX': x,
                            'clientY': y
                        }});
                        document.dispatchEvent(event);
                    }};
                    
                    // Get current mouse position from a mouse event listener
                    let currentX = {dimensions["width"]/2}; // Start roughly in the center
                    let currentY = {dimensions["height"]/2};
                    
                    // Generate bezier curve points for natural movement
                    const points = Math.floor(20 + Math.random() * 10); // 20-30 points
                    const bezierPoints = [];
                    
                    // Add control points for the bezier curve - more variable
                    const cp1x = currentX + (Math.random() * 150) - 75;
                    const cp1y = currentY + (Math.random() * 150) - 75;
                    const cp2x = {overshoot_x} - (Math.random() * 150) - 75;
                    const cp2y = {overshoot_y} - (Math.random() * 150) - 75;
                    
                    // Generate points along the bezier curve
                    for (let i = 0; i <= points; i++) {{
                        const t = i / points;
                        const u = 1 - t;
                        
                        // Cubic bezier formula
                        const x = (u*u*u * currentX) + (3 * u*u * t * cp1x) + (3 * u * t*t * cp2x) + (t*t*t * {overshoot_x});
                        const y = (u*u*u * currentY) + (3 * u*u * t * cp1y) + (3 * u * t*t * cp2y) + (t*t*t * {overshoot_y});
                        
                        bezierPoints.push({{ x, y }});
                    }}
                    
                    // If overshooting, add final correction to target
                    if ({1 if has_overshooting else 0}) {{
                        bezierPoints.push({{ x: {x}, y: {y} }});
                    }}
                    
                    // Move the mouse along the curve with varying speed
                    const moveMouseAlongPath = async () => {{
                        for (let i = 0; i < bezierPoints.length; i++) {{
                            const point = bezierPoints[i];
                            
                            // Vary the delay between movements based on speed
                            const distance = i > 0 
                                ? Math.sqrt(Math.pow(point.x - bezierPoints[i-1].x, 2) + 
                                           Math.pow(point.y - bezierPoints[i-1].y, 2))
                                : 0;
                                
                            // Convert distance/speed to milliseconds with some randomness
                            const baseDelay = distance / {speed} * 1000;
                            const jitter = baseDelay * 0.2 * (Math.random() - 0.5);
                            let delay = Math.max(5, baseDelay + jitter);
                            
                            // Add hesitation randomly
                            if ({1 if has_hesitation else 0} && Math.random() < 0.2 && i > 0 && i < bezierPoints.length - 1) {{
                                delay += Math.random() * 300 + 100; // 100-400ms pause
                            }}
                            
                            moveMouse(point.x, point.y);
                            await new Promise(r => setTimeout(r, delay));
                        }}
                    }};
                    
                    // Execute the movement
                    moveMouseAlongPath();
                }}
            """)
            
            # Record last mouse move time
            self.last_mouse_move_time = time.time()
            
        except Exception as e:
            logger.error(f"Error simulating mouse movement: {str(e)}")
    
    def _simulate_content_engagement(self) -> None:
        """Simulate engaging with content without actually clicking."""
        if not self.driver:
            return
            
        try:
            # Find elements that look like engagement buttons
            self.driver.evaluate("""
                () => {
                    // Find like buttons or other engagement elements
                    const engagementSelectors = [
                        'button.react-button__trigger',
                        'button.social-actions__button',
                        'button[aria-label*="like"]',
                        'button[aria-label*="Like"]',
                        'button[data-control-name="like_toggle"]'
                    ];
                    
                    // Get all potential engagement elements
                    let engagementElements = [];
                    for (const selector of engagementSelectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length) {
                            engagementElements = [...engagementElements, ...Array.from(elements)];
                        }
                    }
                    
                    // If we found any, hover over some of them
                    if (engagementElements.length) {
                        // Select 1-3 random elements to hover over
                        const numToHover = Math.floor(Math.random() * 3) + 1;
                        const shuffled = engagementElements.sort(() => 0.5 - Math.random());
                        const selected = shuffled.slice(0, numToHover);
                        
                        // Simulate hovering over each element
                        selected.forEach(element => {
                            const rect = element.getBoundingClientRect();
                            const x = rect.left + rect.width / 2;
                            const y = rect.top + rect.height / 2;
                            
                            // Create and dispatch mouseenter/mouseover events
                            const mouseenterEvent = new MouseEvent('mouseenter', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: x,
                                clientY: y
                            });
                            
                            const mouseoverEvent = new MouseEvent('mouseover', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: x,
                                clientY: y
                            });
                            
                            element.dispatchEvent(mouseenterEvent);
                            element.dispatchEvent(mouseoverEvent);
                            
                            // We don't actually click, just hover
                        });
                    }
                }
            """)
            
            # Add a brief pause to simulate looking at engagement options
            time.sleep(self.random_range(1.2, 3.7))
            
        except Exception as e:
            logger.error(f"Error simulating content engagement: {str(e)}")
    
    def click_element(self, selector: str) -> bool:
        """
        Click an element with human-like timing.
        
        Args:
            selector: CSS selector for the element to click
            
        Returns:
            True if click was successful, False otherwise
        """
        if not self.driver:
            logger.error("Driver not set. Cannot click element.")
            return False
        
        try:
            # First check if element exists with variable timeout
            random_timeout = int(self.random_range(3000, 7000))  # 3-7 seconds
            element_exists = self.driver.wait_for_selector(selector, timeout=random_timeout)
            if not element_exists:
                logger.error(f"Element not found after {random_timeout/1000}s: {selector}")
                return False
            
            # Get element position
            element_position = self.driver.evaluate(f"""
                () => {{
                    const el = document.querySelector('{selector}');
                    if (!el) return null;
                    
                    const rect = el.getBoundingClientRect();
                    return {{
                        x: rect.left + rect.width / 2,
                        y: rect.top + rect.height / 2,
                        width: rect.width,
                        height: rect.height
                    }};
                }}
            """)
            
            if not element_position:
                logger.error(f"Could not get position for element: {selector}")
                return False
            
            # Move mouse to element with bezier curve motion
            self.driver.evaluate(f"""
                () => {{
                    // Create a custom mouse event for movement
                    const moveMouse = (x, y) => {{
                        const event = new MouseEvent('mousemove', {{
                            'view': window,
                            'bubbles': true,
                            'cancelable': true,
                            'clientX': x,
                            'clientY': y
                        }});
                        document.dispatchEvent(event);
                    }};
                    
                    // Current mouse position (estimate middle of viewport)
                    const viewportWidth = window.innerWidth;
                    const viewportHeight = window.innerHeight;
                    let currentX = viewportWidth / 2;
                    let currentY = viewportHeight / 2;
                    
                    // Target position (element center)
                    const targetX = {element_position['x']};
                    const targetY = {element_position['y']};
                    
                    // Generate bezier curve points for mouse movement
                    const points = Math.floor(15 + Math.random() * 10); // 15-25 points
                    
                    // Control points for bezier curve
                    const cp1x = currentX + (Math.random() * 100 - 50);
                    const cp1y = currentY + (Math.random() * 100 - 50);
                    const cp2x = targetX + (Math.random() * 100 - 50);
                    const cp2y = targetY + (Math.random() * 100 - 50);
                    
                    // Calculate points along bezier curve
                    const bezierPoints = [];
                    for (let i = 0; i <= points; i++) {{
                        const t = i / points;
                        const u = 1 - t;
                        
                        // Cubic bezier formula
                        const x = (u*u*u * currentX) + (3 * u*u * t * cp1x) + (3 * u * t*t * cp2x) + (t*t*t * targetX);
                        const y = (u*u*u * currentY) + (3 * u*u * t * cp1y) + (3 * u * t*t * cp2y) + (t*t*t * targetY);
                        
                        bezierPoints.push({{ x, y }});
                    }}
                    
                    // Move mouse along path
                    const moveAlongPath = async () => {{
                        for (const point of bezierPoints) {{
                            const delay = 5 + Math.random() * 15; // 5-20ms between movements
                            moveMouse(point.x, point.y);
                            await new Promise(r => setTimeout(r, delay));
                        }}
                        
                        // Add mouseenter and mouseover events on the element
                        const el = document.querySelector('{selector}');
                        if (el) {{
                            const mouseenterEvent = new MouseEvent('mouseenter', {{
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: targetX,
                                clientY: targetY
                            }});
                            
                            const mouseoverEvent = new MouseEvent('mouseover', {{
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: targetX,
                                clientY: targetY
                            }});
                            
                            el.dispatchEvent(mouseenterEvent);
                            el.dispatchEvent(mouseoverEvent);
                        }}
                    }};
                    
                    // Execute mouse movement
                    moveAlongPath();
                }}
            """)
            
            # Slight delay before clicking
            time.sleep(self.random_range(0.3, 1.2))
            
            # Click with the native Playwright click
            self.driver.click(selector)
            
            # Record last click time
            self.last_click_time = time.time()
            
            # Wait a bit after clicking
            time.sleep(self.random_range(0.5, 2.0))
            
            return True
            
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {str(e)}")
            return False

    def simulate_reading(self, min_duration: float = 3.0, max_duration: float = 15.0) -> None:
        """
        Simulate reading behavior with natural pauses.
        
        Args:
            min_duration: Minimum reading duration in seconds
            max_duration: Maximum reading duration in seconds
        """
        # Apply time-of-day adjustments
        if self.is_morning:
            min_duration *= 1.2
            max_duration *= 1.2
        elif self.is_evening:
            min_duration *= 0.85
            max_duration *= 0.85
        elif self.is_late_evening:
            min_duration *= 0.75
            max_duration *= 0.75
        
        duration = self.random_range(min_duration, max_duration)
        logger.info(f"Simulating reading for {duration:.3f} seconds")
        
        # Divide the reading time into segments with occasional scrolls
        time_spent = 0
        while time_spent < duration:
            # Read for a while
            read_segment = self.random_range(2.0, 5.0)
            actual_segment = min(read_segment, duration - time_spent)
            time.sleep(actual_segment)
            time_spent += actual_segment
            
            # Occasionally scroll a little
            if random.random() < 0.6 and time_spent < duration:  # 60% chance
                self.driver.evaluate(f"""
                    () => {{
                        // Small scroll with variable distance
                        const distance = Math.floor({self.random_range(50, 150)});
                        
                        // Smooth scroll implementation
                        const steps = Math.floor({self.random_range(8, 15)});
                        const delay = Math.floor({self.random_range(5, 10)});
                        
                        const smoothScroll = async () => {{
                            for (let i = 1; i <= steps; i++) {{
                                const step = distance * (i / steps) - distance * ((i - 1) / steps);
                                window.scrollBy(0, step);
                                await new Promise(r => setTimeout(r, delay));
                            }}
                        }};
                        
                        smoothScroll();
                    }}
                """)
                
                # Record last scroll time
                self.last_scroll_time = time.time()
                
                # Brief pause after scrolling
                time.sleep(self.random_range(0.5, 1.5))
                time_spent += 1.0
            
            # Sometimes move the mouse
            if random.random() < 0.3 and time_spent < duration:  # 30% chance
                self._simulate_mouse_movement()
                time_spent += 0.5
    
    def adjust_viewport(self) -> bool:
        """
        Occasionally adjust the viewport size slightly.
        
        Returns:
            True if adjustment was made, False otherwise
        """
        if not self.driver or random.random() > 0.1:  # Only 10% chance
            return False
            
        try:
            # Get current viewport size
            viewport = self.driver.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                }
            """)
            
            if not viewport:
                return False
                
            # Calculate new dimensions with small variations
            width_delta = random.randint(-150, 150)  # ±150px
            height_delta = random.randint(-80, 80)   # ±80px
            
            new_width = max(800, viewport["width"] + width_delta)  # Never below 800px
            new_height = max(600, viewport["height"] + height_delta)  # Never below 600px
            
            # Set new viewport size
            result = self.driver.evaluate(f"""
                () => {{
                    try {{
                        window.resizeTo({new_width}, {new_height});
                        return true;
                    }} catch (e) {{
                        console.error('Failed to resize window:', e);
                        return false;
                    }}
                }}
            """)
            
            logger.info(f"Adjusted viewport from {viewport['width']}x{viewport['height']} to {new_width}x{new_height}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error adjusting viewport: {str(e)}")
            return False
    
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
            # Try to open a new tab first
            new_tab_opened = self.driver.evaluate("""
                () => {
                    try {
                        window.open('about:blank', '_blank');
                        return true;
                    } catch (e) {
                        console.error('Failed to open new tab:', e);
                        return false;
                    }
                }
            """)
            
            if not new_tab_opened:
                logger.warning("Could not open new tab, will navigate in current tab")
                # Store current URL to return to later
                current_url = self.driver.evaluate("() => window.location.href")
            
            # Get a list of random, safe sites from imported config or use defaults
            random_sites = getattr(RANDOM_SITES, "sites", [
                "https://www.wikipedia.org",
                "https://www.weather.com",
                "https://www.cnn.com",
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
            
            # If we opened a new tab, navigate in that tab
            if new_tab_opened:
                # Switch to the new tab (should be the last one)
                self.driver.evaluate("""
                    () => {
                        // Get all window handles
                        const windows = window.open('', '_self').opener.parent.frames;
                        
                        // Focus the last window/tab
                        if (windows.length > 0) {
                            windows[windows.length - 1].focus();
                        }
                    }
                """)
                
                # Navigate to random site in new tab
                result = self.driver.navigate(random_site)
            else:
                # Navigate in current tab
                result = self.driver.navigate(random_site)
            
            if not result:
                logger.error(f"Failed to navigate to {random_site}")
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
            
            # Return to the original window/tab or URL
            if new_tab_opened:
                # Close the current tab
                self.driver.evaluate("() => window.close()")
                
                # Switch back to the original tab
                self.driver.evaluate("""
                    () => {
                        // Get original window/tab
                        const originalWindow = window.open('', '_self').opener;
                        if (originalWindow) {
                            originalWindow.focus();
                        }
                    }
                """)
            else:
                # Navigate back to original URL
                self.driver.navigate(current_url)
            
            logger.info(f"Returned from random site visit to {random_site}")
            return True
            
        except Exception as e:
            logger.error(f"Error visiting random site: {str(e)}")
            return False