# services/human_like_behavior.py
"""
Human-like behavior implementation for LinkedIn navigation.

This module provides behaviors that mimic human interaction patterns
for browsing LinkedIn, including natural scrolling, mouse movements,
timing variations, and session behavior.
"""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Callable
import threading

from config.scraper_config import (
    LINKEDIN_FEED_URL, FEED_BROWSING_DURATION, SCROLL_PAUSE_TIME,
    PROFILE_NAVIGATION_DELAY, EVENTS, STATES
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
    
    def set_driver(self, driver: PlaywrightDriver) -> None:
        """
        Set the PlaywrightDriver instance.
        
        Args:
            driver: PlaywrightDriver instance
        """
        self.driver = driver
    
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
        
        if not min_duration or not max_duration:
            min_duration, max_duration = FEED_BROWSING_DURATION
        
        duration = random.uniform(min_duration, max_duration)
        
        try:
            # Transition state
            self.state_machine.transition(STATES["FEED_BROWSING"], "Starting feed browsing")
            
            # Navigate to feed
            logger.info(f"Navigating to LinkedIn feed for {duration:.1f} seconds browsing")
            if not self.driver.navigate(LINKEDIN_FEED_URL, wait_until="domcontentloaded"):
                logger.error("Failed to navigate to LinkedIn feed")
                return False
            
            # Randomized delay for page to render basic content (1.0 to 3.4 seconds with millisecond precision)
            time.sleep(1.0 + random.random() * 2.4)
            
            # Scroll feed for specified duration
            self._scroll_with_human_behavior(duration=duration)
            
            logger.info("Feed browsing completed")
            return True
            
        except Exception as e:
            logger.error(f"Error browsing feed: {str(e)}")
            return False
    
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
            # Add natural delay before navigating
            delay = random.uniform(*PROFILE_NAVIGATION_DELAY)
            logger.info(f"Waiting {delay:.1f} seconds before navigating to profile")
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
            
            # Short delay to ensure at least some content has loaded
            time.sleep(2)
            
            # Verify we're on the right profile page
            current_url = self.driver.evaluate("() => window.location.href")
            if profile_url not in current_url:
                logger.warning(f"Expected to be on {profile_url} but current URL is {current_url}")
            
            # Sometimes scroll profile with pauses
            if random.random() < 0.8:  # 80% chance
                self._scroll_with_human_behavior(duration=random.uniform(5, 15))
            
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
            # Build section URL
            section_url = f"{profile_url}/details/{section}/"
            
            # Add natural delay before navigating
            delay = random.uniform(2, 5)
            logger.info(f"Waiting {delay:.1f} seconds before navigating to {section} section")
            time.sleep(delay)
            
            # Navigate to section
            logger.info(f"Navigating to {section} section: {section_url}")
            if not self.driver.navigate(section_url, wait_until="domcontentloaded"):
                logger.error(f"Failed to navigate to {section} section")
                return False
            
            # Randomized delay to allow page to render some content (1.0 to 3.4 seconds with millisecond precision)
            time.sleep(1.0 + random.random() * 2.4)
            
            # Verify we're on the right section page
            current_url = self.driver.evaluate("() => window.location.href")
            if section not in current_url:
                logger.warning(f"Expected to be on {section} section but current URL is {current_url}")
            
            # Sometimes scroll section with pauses
            if random.random() < 0.7:  # 70% chance
                scroll_duration = random.uniform(3, 10)
                logger.info(f"Scrolling {section} section for {scroll_duration:.1f} seconds")
                self._scroll_with_human_behavior(duration=scroll_duration)
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to profile section: {str(e)}")
            return False

    def _scroll_with_human_behavior(self, duration: float = 30.0, scroll_range: Tuple[int, int] = (300, 800)) -> None:
        """
        Scroll the page with human-like behavior.
        
        Args:
            duration: Duration to scroll in seconds
            scroll_range: Range of scroll distances (min, max)
        """
        if not self.driver:
            logger.error("Driver not set. Cannot perform scrolling.")
            return
        
        try:
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Random scroll distance
                scroll_distance = random.randint(*scroll_range)
                
                # Scroll with a smooth motion
                self.driver.evaluate(f"""
                    () => {{
                        // Calculate steps for smooth scrolling
                        const distance = {scroll_distance};
                        const steps = Math.floor(10 + Math.random() * 15); // 10-25 steps
                        const delay = Math.floor(5 + Math.random() * 10); // 5-15ms between steps
                        
                        // Function to scroll smoothly
                        const smoothScroll = async (steps, distance) => {{
                            const stepSize = distance / steps;
                            for (let i = 0; i < steps; i++) {{
                                window.scrollBy(0, stepSize);
                                await new Promise(r => setTimeout(r, delay));
                            }}
                        }};
                        
                        // Execute the smooth scroll
                        smoothScroll(steps, distance);
                    }}
                """)
                
                # Record last scroll time
                self.last_scroll_time = time.time()
                
                # Sometimes move the mouse while scrolling
                if random.random() < 0.3:  # 30% chance
                    self._simulate_mouse_movement()
                
                # Pause between scrolls like a human would
                pause_time = random.uniform(*SCROLL_PAUSE_TIME)
                time.sleep(pause_time)
                
                # Occasionally longer pause as if reading content
                if random.random() < 0.2:  # 20% chance
                    read_time = random.uniform(2.0, 6.0)  # 2-6 seconds reading
                    time.sleep(read_time)
                    
        except Exception as e:
            logger.error(f"Error during human-like scrolling: {str(e)}")

    def _simulate_mouse_movement(self) -> None:
        """Simulate human-like mouse movements."""
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
                    let currentX = {x/2}; // Start roughly in the center
                    let currentY = {y/2};
                    
                    // Generate bezier curve points for natural movement
                    const points = 20;
                    const bezierPoints = [];
                    
                    // Add control points for the bezier curve
                    const cp1x = currentX + (Math.random() * 100) - 50;
                    const cp1y = currentY + (Math.random() * 100) - 50;
                    const cp2x = {x} - (Math.random() * 100) - 50;
                    const cp2y = {y} - (Math.random() * 100) - 50;
                    
                    // Generate points along the bezier curve
                    for (let i = 0; i <= points; i++) {{
                        const t = i / points;
                        const u = 1 - t;
                        
                        // Cubic bezier formula
                        const x = (u*u*u * currentX) + (3 * u*u * t * cp1x) + (3 * u * t*t * cp2x) + (t*t*t * {x});
                        const y = (u*u*u * currentY) + (3 * u*u * t * cp1y) + (3 * u * t*t * cp2y) + (t*t*t * {y});
                        
                        bezierPoints.push({{ x, y }});
                    }}
                    
                    // Move the mouse along the curve with varying speed
                    const moveMouseAlongPath = async () => {{
                        for (const point of bezierPoints) {{
                            // Vary the delay between movements
                            const delay = 10 + Math.random() * 30;
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
            # First check if element exists
            element_exists = self.driver.wait_for_selector(selector, timeout=5000)
            if not element_exists:
                logger.error(f"Element not found: {selector}")
                return False
            
            # Sometimes move mouse to element before clicking
            if random.random() < 0.7:  # 70% chance
                # Get element position
                element_position = self.driver.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        if (!el) return null;
                        
                        const rect = el.getBoundingClientRect();
                        return {{
                            x: rect.left + rect.width / 2,
                            y: rect.top + rect.height / 2
                        }};
                    }}
                """)
                
                if element_position:
                    # Move mouse to element
                    self.driver.evaluate(f"""
                        () => {{
                            const point = {element_position};
                            
                            // Create a custom mouse event
                            const event = new MouseEvent('mousemove', {{
                                'view': window,
                                'bubbles': true,
                                'cancelable': true,
                                'clientX': point.x,
                                'clientY': point.y
                            }});
                            
                            document.dispatchEvent(event);
                        }}
                    """)
                    
                    # Slight delay before clicking
                    time.sleep(random.uniform(0.3, 1.2))
            
            # Click with a slight delay to simulate human click
            self.driver.click(selector)
            
            # Record last click time
            self.last_click_time = time.time()
            
            # Wait a bit after clicking
            time.sleep(random.uniform(0.5, 2.0))
            
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
        duration = random.uniform(min_duration, max_duration)
        logger.info(f"Simulating reading for {duration:.1f} seconds")
        
        # Divide the reading time into segments with occasional scrolls
        time_spent = 0
        while time_spent < duration:
            # Read for a while
            read_segment = random.uniform(2.0, 5.0)
            actual_segment = min(read_segment, duration - time_spent)
            time.sleep(actual_segment)
            time_spent += actual_segment
            
            # Occasionally scroll a little
            if random.random() < 0.6 and time_spent < duration:  # 60% chance
                self.driver.evaluate("""
                    () => {
                        // Small scroll
                        const distance = Math.floor(50 + Math.random() * 150);
                        window.scrollBy(0, distance);
                    }
                """)
                
                # Record last scroll time
                self.last_scroll_time = time.time()
                
                # Brief pause after scrolling
                time.sleep(random.uniform(0.5, 1.5))
                time_spent += 1.0
            
            # Sometimes move the mouse
            if random.random() < 0.3 and time_spent < duration:  # 30% chance
                self._simulate_mouse_movement()
                time_spent += 0.5