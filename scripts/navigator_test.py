# test_linkedin_navigator.py
"""
Test script for the LinkedInNavigator class.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.linked_navigator.linkedin_navigator import LinkedInNavigator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def test_navigator():
    """Test the LinkedInNavigator with a sample profile."""
    # Set up test parameters
    profile_url = "https://www.linkedin.com/in/ashraf-elzoheri/"
    
    # Use the provided Chrome profile path
    profile_path = r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5"
    
    # Create navigator instance
    navigator = LinkedInNavigator(
        profile_url=profile_url,
        headless=False,  # Set to True for production
        cookies_file=None,
        profile_path=profile_path
    )
    
    try:
        # Start the navigator
        if not navigator.start():
            logger.error(f"Failed to start navigator: {navigator.last_error}")
            return
        
        # Navigate to main profile
        if not navigator.navigate_profile():
            logger.error(f"Failed to navigate profile: {navigator.last_error}")
            return
        
        # Navigate to experience section
        if not navigator.navigate_experience():
            logger.error(f"Failed to navigate experience section: {navigator.last_error}")
            return
        
        # Save HTML to files for inspection
        with open("profile_html.html", "w", encoding="utf-8") as f:
            f.write(navigator.main_profile_html)
        
        with open("experience_html.html", "w", encoding="utf-8") as f:
            f.write(navigator.experience_html)
        
        logger.info("Successfully saved HTML files")
        
    except Exception as e:
        logger.error(f"Error during navigation: {str(e)}")
    finally:
        # Always close the navigator to clean up resources
        navigator.close()

if __name__ == "__main__":
    test_navigator()