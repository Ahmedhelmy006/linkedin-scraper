# test_linkedin_scraper.py
"""
Test script for the LinkedIn scraper system.
"""

import os
import sys
import logging
import time
import threading
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.scraper_config import PROFILE_QUEUE_PATH, MEMORY_PATH
from utils.event_bus import EventBus
from utils.state_machine import StateMachine
from services.linked_navigator.queue_manager import QueueManager
from services.linked_navigator.brain import Brain
from services.linked_navigator.batch_processor import BatchProcessor
from services.linked_navigator.human_like_behavior import HumanLikeBehavior
from services.linked_navigator.linkedin_navigator import LinkedInNavigator
from utils.playwright_driver import PlaywrightDriver

def session_callback(session_data):
    """
    Callback function to handle a scraping session.
    
    Args:
        session_data: Session data from the Brain
        
    Returns:
        Dictionary with session results
    """
    logger.info(f"Executing session: {session_data['id']}")
    session_id = session_data['id']
    
    # Session statistics
    stats = {
        "profiles_started": 0,
        "profiles_completed": 0,
        "profiles_failed": 0
    }
    
    try:
        # Initialize shared browser
        logger.info("Initializing browser for session...")
        driver = PlaywrightDriver(
            mode="profile_mode",
            headless=False,
            profile_path=r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5",
            user_agent_type="random"
        )
        
        # Start the browser with enough time
        logger.info("Starting browser...")
        start_success = driver.start()
        
        if not start_success:
            logger.error("Failed to start browser")
            stats["error"] = "Failed to start browser"
            return stats
        
        logger.info("Browser started successfully")
        
        # Initialize behavior controller
        behavior = HumanLikeBehavior(driver)
                
        # Process each profile in the session
        profiles = session_data.get("profiles", [])
        for profile in profiles:
            profile_url = profile["url"]
            logger.info(f"Processing profile: {profile_url}")
            
            try:
                stats["profiles_started"] += 1
                
                # Create navigator with shared driver and behavior
                navigator = LinkedInNavigator(
                    profile_url=profile_url,
                    driver=driver,
                    behavior=behavior
                )
                
                # Scrape the profile
                if navigator.scrape_all_sections():
                    # Save the profile data
                    profile_dir = navigator.save_profile_data()
                    
                    # Update profile status in queue
                    queue_manager.mark_profile_status(
                        profile_url, 
                        "completed", 
                        {"saved_to": profile_dir}
                    )
                    
                    stats["profiles_completed"] += 1
                    logger.info(f"Successfully scraped profile: {profile_url}")
                else:
                    # Update profile status in queue
                    queue_manager.mark_profile_status(
                        profile_url, 
                        "failed", 
                        {"error": navigator.last_error}
                    )
                    
                    stats["profiles_failed"] += 1
                    logger.error(f"Failed to scrape profile: {profile_url}")
            
            except Exception as e:
                logger.error(f"Error processing profile {profile_url}: {str(e)}")
                queue_manager.mark_profile_status(profile_url, "failed", {"error": str(e)})
                stats["profiles_failed"] += 1
        
        # Close the shared browser
        driver.close()
        
    except Exception as e:
        logger.error(f"Error executing session: {str(e)}")
        stats["error"] = str(e)
    
    return stats

def test_scraper():
    """Test the LinkedIn scraper system."""
    global queue_manager
    
    try:
        # Initialize components
        event_bus = EventBus.get_instance()
        state_machine = StateMachine()
        queue_manager = QueueManager()
        brain = Brain()
        batch_processor = BatchProcessor(brain, queue_manager)
        
        # Register session callback
        batch_processor.register_session_callback(session_callback)
        
        # Start the brain
        brain.start()
        
        # Add some test profiles
        profiles = [
            "https://www.linkedin.com/in/anithabala",
            "https://www.linkedin.com/in/annakourula/",
            "https://www.linkedin.com/in/anna-yugova/",
            "https://www.linkedin.com/in/antoineduchene/",
            "https://www.linkedin.com/in/architrao/",
            "https://www.linkedin.com/in/armitarostamian/",
            "https://www.linkedin.com/in/arthurmichel/",
            "https://www.linkedin.com/in/zhivkaatanasovanedyalkova/",
            "https://www.linkedin.com/in/aylin-schaer/",
            "https://www.linkedin.com/in/bradford-sliva-cma-csca",
            "https://www.linkedin.com/in/benrmurray/",
            "https://www.linkedin.com/in/bencohens/",
            "https://www.linkedin.com/in/benjamin-mills-b4902520",
            "https://www.linkedin.com/in/brianmarszowski/",
            "https://www.linkedin.com/in/boryanarb",
            "https://www.linkedin.com/in/brookereid",
            "https://www.linkedin.com/in/bennovanginkel/?originalSubdomain=nl",
            "https://www.linkedin.com/in/carla-manso-108a531/",
            "https://www.linkedin.com/in/cÃ©dric-ringelstein-49296828",
            "https://www.linkedin.com/in/chrisraman/?originalSubdomain=be",
            "https://www.linkedin.com/in/christian-wattig/",
            "https://www.linkedin.com/in/christophvanderkelen",
            "https://www.linkedin.com/in/angelikajarski/",
            "https://www.linkedin.com/in/christy-page-ab34b0b/",
            "https://www.linkedin.com/in/camilo-ramirez-cpa-7b90b027/",
            "https://www.linkedin.com/in/damobird365/",
            "https://www.linkedin.com/in/dan-maclachlan-61712348/",
            "https://www.linkedin.com/in/dstoner/",
            "https://www.linkedin.com/in/daniel-schorege-589232a2/",
            "https://www.linkedin.com/in/david-harpur-778771151/",
            "https://www.linkedin.com/in/david-fortin-cpa-816b20b5",
            "https://www.linkedin.com/in/talwardeepak/",
            "https://www.linkedin.com/in/delia-lazarean-34801590/",
            "https://www.linkedin.com/in/diegosaenz2010/",
            "https://www.linkedin.com/in/davidandrejohnsondaj/",
            "https://www.linkedin.com/in/donnieschell/",
            "https://www.linkedin.com/in/douglaspilot/",
            "https://www.linkedin.com/in/deepakkamaraj",
            "https://www.linkedin.com/in/andy-fleetham-555b4628",
            "https://www.linkedin.com/in/dudley-h-peacock/",
            "https://www.linkedin.com/in/eduardopadraomartins/"
        ]
        
        # Add profiles to queue
        result = batch_processor.add_profiles(profiles, initiator="test_script")
        logger.info(f"Added profiles result: {result}")
        
        # Wait for processing to complete
        logger.info("Waiting for profiles to be processed...")
        
        # Monitor until all profiles are processed or timeout
        start_time = time.time()
        timeout = 3600  # 1 hour timeout
        
        while time.time() - start_time < timeout:
            # Get queue stats
            queue_stats = queue_manager.get_queue_stats()
            brain_status = brain.get_status()
            
            logger.info(f"Queue stats: {queue_stats}")
            logger.info(f"Brain state: {brain_status['state']}")
            
            # Check if all profiles are done
            if queue_stats["pending"] == 0 and queue_stats["completed"] == len(profiles):
                logger.info("All profiles processed!")
                break
            
            # Wait before checking again
            time.sleep(30)
        
        # Stop the brain
        brain.stop()
        
        logger.info("Test completed")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        # Try to stop the brain
        if 'brain' in locals():
            brain.stop()

if __name__ == "__main__":
    # Clean up old queue and memory for testing
    if os.path.exists(PROFILE_QUEUE_PATH):
        os.remove(PROFILE_QUEUE_PATH)
    
    if os.path.exists(MEMORY_PATH):
        os.remove(MEMORY_PATH)
    
    # Run the test
    test_scraper()