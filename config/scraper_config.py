"""
Configuration settings for the LinkedIn scraper system.
"""

import os
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
PROFILE_NAVIGATION_DELAY = (5, 12)  # seconds between profile navigation
SCROLL_PAUSE_TIME = (0.8, 3.0)  # seconds between scrolls
FEED_BROWSING_DURATION = (45, 90)  # seconds to browse feed before profile

# Browser configuration
BROWSER_CONFIG = {
    "headless": False,  # Set to True for production
    "user_agent_type": "random",
    "viewport": {"width": 1920, "height": 1080}
}

# LinkedIn specific URLs
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_BASE_URL = "https://www.linkedin.com/"

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
    "ERROR": "error"
}

# Profile states
PROFILE_STATES = {
    "QUEUED": "queued",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed",
    "FAILED": "failed"
}

# Create necessary directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROFILES_DIR, exist_ok=True)