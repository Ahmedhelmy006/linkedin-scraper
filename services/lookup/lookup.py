# services/lookup.py
import time
import logging
from datetime import datetime, timedelta
import random
from typing import Dict, List, Optional, Tuple

# Import the existing functions from rocketreach_requests
from config.rocketreach_requests import (
    get_lkd_profile_devloper_nbo,
    get_lkd_profile_muhammad_helmey_006,
    get_lkd_profile_ahmed_helmey_006,
    get_lkd_profile_ahmed_modelwiz,
    get_lkd_profile_ahmed_helmey_009,
    get_lkd_profile_ichbin
)

# Import utility functions
from utils.email_validator import EmailValidator
from utils.helper import safe_call

logger = logging.getLogger(__name__)

class LinkedInProfileLookup:
    """
    Service for looking up LinkedIn profiles based on email addresses.
    This is a minimal implementation that can be expanded later.
    """
    
    def __init__(self):
        # Track API calls for rate limiting
        self.call_history = {
            "get_lkd_profile_devloper_nbo": [],
            "get_lkd_profile_muhammad_helmey_006": [],
            "get_lkd_profile_ahmed_helmey_006": [],
            "get_lkd_profile_ahmed_modelwiz": [],
            "get_lkd_profile_ahmed_helmey_009": [],
            "get_lkd_profile_ichbin": []

        }
        
        # Define rate limits
        self.cooldown_seconds = 10  # No function should be called twice in 10 seconds
        self.max_calls_per_hour = 70  # Maximum 70 calls per hour per function
        
        # Map function names to actual functions
        self.lookup_functions = {
            "get_lkd_profile_devloper_nbo": get_lkd_profile_devloper_nbo,
            "get_lkd_profile_muhammad_helmey_006": get_lkd_profile_muhammad_helmey_006,
            "get_lkd_profile_ahmed_helmey_006": get_lkd_profile_ahmed_helmey_006,
            "get_lkd_profile_ahmed_modelwiz": get_lkd_profile_ahmed_modelwiz,
            "get_lkd_profile_ahmed_helmey_009": get_lkd_profile_ahmed_helmey_009,
            "get_lkd_profile_ichbin": get_lkd_profile_ichbin,
    }
    
    def lookup_by_email(self, email: str) -> Optional[str]:
        """
        Look up a LinkedIn profile using an email address
        
        Args:
            email: Email address to look up
            
        Returns:
            LinkedIn profile URL or None if not found
        """
        # Validate email
        if not EmailValidator.is_valid(email):
            logger.error(f"Invalid email format: {email}")
            raise ValueError(f"Invalid email format: {email}")
        
        # Select the appropriate function to call
        function_name = self._select_available_function()
        if not function_name:
            logger.error("No available lookup functions due to rate limiting")
            raise RuntimeError("Rate limit exceeded for all available lookup functions")
        
        # Record this call
        self._record_call(function_name)
        
        # Call the selected function using safe_call
        logger.info(f"Looking up LinkedIn profile for {email} using {function_name}")
        lookup_function = self.lookup_functions[function_name]
        linkedin_url = safe_call(lookup_function, email)
        
        return linkedin_url
    
    def _select_available_function(self) -> Optional[str]:
        """
        Select a function that isn't currently rate-limited
        
        Returns:
            Name of an available function or None if all are rate-limited
        """
        available_functions = []
        
        for func_name in self.lookup_functions.keys():
            if self._can_call_function(func_name):
                available_functions.append(func_name)
        
        if not available_functions:
            return None
        
        # Return a random available function to distribute load
        return random.choice(available_functions)
    
    def _can_call_function(self, function_name: str) -> bool:
        """
        Check if a function can be called based on rate limits
        
        Args:
            function_name: Name of the function to check
            
        Returns:
            True if the function can be called, False otherwise
        """
        calls = self.call_history.get(function_name, [])
        
        # Check cooldown period (last 10 seconds)
        now = datetime.now()
        if calls and (now - calls[-1]).total_seconds() < self.cooldown_seconds:
            return False
        
        # Check hourly limit
        one_hour_ago = now - timedelta(hours=1)
        recent_calls = [call for call in calls if call > one_hour_ago]
        if len(recent_calls) >= self.max_calls_per_hour:
            return False
        
        return True
    
    def _record_call(self, function_name: str) -> None:
        """
        Record that a function was called for rate limiting purposes
        
        Args:
            function_name: Name of the called function
        """
        now = datetime.now()
        self.call_history.setdefault(function_name, []).append(now)
        
        # Clean up old call history to prevent memory leaks
        one_day_ago = now - timedelta(days=1)
        self.call_history[function_name] = [
            call for call in self.call_history[function_name] 
            if call > one_day_ago
        ]