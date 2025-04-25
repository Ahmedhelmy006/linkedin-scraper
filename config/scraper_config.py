"""
Enhanced configuration settings for the LinkedIn scraper system.

This configuration includes improved randomization settings and
human-like behavior patterns to avoid detection.
"""

import os
import random
from typing import Dict, List, Tuple, Any

# Basic paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROFILES_DIR = os.path.join(DATA_DIR, "linkedin_profiles")

# Queue and memory file paths
PROFILE_QUEUE_PATH = os.path.join(DATA_DIR, "profile_queue.json")
MEMORY_PATH = os.path.join(DATA_DIR, "memory.json")

# Session configuration
SESSION_TYPES = [
    {"name": "regular", "duration": (5, 7), "probability": 0.6, "max_profiles": 8},
    {"name": "short", "duration": (2, 6), "probability": 0.2, "max_profiles": 5},
    {"name": "long", "duration": (7, 13), "probability": 0.1, "max_profiles": 12},
    {"name": "quick", "duration": (2, 4), "probability": 0.1, "max_profiles": 3}
]

# Browsing behavior configuration
ACTIVE_HOURS = list(range(10, 21))  # 10 AM to 8 PM
SESSIONS_PER_HOUR = 2
MINIMUM_SESSION_SPACING = 15 * 60  # Minimum 15 minutes between sessions

# Enhanced Feed Browsing Duration with probability distribution
# Used in the _get_feed_browsing_duration method in HumanLikeBehavior
# 60%: 45-90 seconds
# 20%: 75.3-180.7 seconds
# 10%: 180.74-240.873 seconds
# 5%: 10-18.45 seconds
# 5%: 240.64-400 seconds
FEED_BROWSING_DURATION = (10, 24.87)  # Default fallback if probability method fails

# Profile navigation delay with millisecond precision
PROFILE_NAVIGATION_DELAY = (5, 12)  # seconds between profile navigation

# Scroll pause time ranges
SCROLL_PAUSE_TIME = (0.8, 3.0)  # seconds between scrolls

# List of random sites to visit for idle behavior
# These are safe, popular sites that won't trigger suspicion
RANDOM_SITES = [
    "https://www.wikipedia.org",
    "https://www.weather.com",
    "https://www.bbc.com/news",
    "https://www.nytimes.com",
    "https://www.theguardian.com",
    "https://www.reuters.com",
    "https://www.nationalgeographic.com",
    "https://www.forbes.com",
    "https://www.time.com",
    "https://www.wsj.com",
    "https://www.economist.com",
    "https://www.cnn.com",
    "https://www.bloomberg.com",
    "https://www.theatlantic.com",
    "https://www.espn.com",
    "https://www.nature.com",
    "https://www.scientificamerican.com",
    "https://www.smithsonianmag.com"
]

# Section reading times (seconds)
SECTION_READ_TIMES = {
    "experience": (6, 12),
    "education": (4, 8),
    "skills": (3, 7),
    "recommendations": (5, 10),
    "courses": (2, 5),
    "languages": (2, 4),
    "interests": (3, 6),
    "certifications": (3, 7),
    "projects": (4, 9),
    "publications": (5, 11),
    "patents": (4, 8),
    "volunteer": (3, 6),
    "default": (3, 8)  # Default for any other section
}

# Browser configuration
BROWSER_CONFIG = {
    "headless": False,  # Set to True for production
    "user_agent_type": "random",
    "viewport": {"width": 1920, "height": 1080},
    "viewport_variations": True,  # Whether to randomize viewport slightly
}

# LinkedIn specific URLs
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_BASE_URL = "https://www.linkedin.com/"

# System events
EVENTS = {
    "QUEUE_UPDATED": "queue_updated",
    "SESSION_PLANNED": "session_planned",
    "SESSION_STARTED": "session_started",  # This should match exactly
    "SESSION_ENDED": "session_ended",
    "PROFILE_SCRAPED": "profile_scraped",
    "PROFILE_FAILED": "profile_failed",
    "SYSTEM_STATE_CHANGED": "system_state_changed",
    "ERROR": "error"
}

# System States
STATES = {
    "INACTIVE": "inactive",
    "WAITING_FOR_ACTIVE_HOURS": "waiting_for_active_hours",
    "PLANNING_NEXT_SESSION": "planning_next_session",
    "SESSION_STARTING": "session_starting",
    "FEED_BROWSING": "feed_browsing",
    "PROFILE_SCRAPING": "profile_scraping",
    "SESSION_ENDING": "session_ending",
    "COOLDOWN_PERIOD": "cooldown_period",
    "ERROR": "error",
    "RATE_LIMITED": "rate_limited",  # New state for handling rate limiting
    "AUTHENTICATION_FAILURE": "authentication_failure"  # New state for auth issues
}

# Profile states
PROFILE_STATES = {
    "QUEUED": "queued",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed",
    "FAILED": "failed"
}

# Chance of visiting random sites between profiles
RANDOM_SITE_VISIT_CHANCE = 0.2  # 20% chance

# Idle behavior configuration
IDLE_BEHAVIOR_CONFIG = {
    "min_duration": 30,  # seconds
    "max_duration": 90,  # seconds
    "chance_between_profiles": 0.2,  # 20% chance after a profile
    "min_profiles_before_idle": 1,  # Minimum profiles to scrape before idle
    "max_profiles_before_idle": 4,  # Maximum profiles to scrape before idle
}

# Create necessary directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROFILES_DIR, exist_ok=True)