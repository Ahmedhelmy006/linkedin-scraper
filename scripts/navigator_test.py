# test_batch.py
"""
Test batch script for the LinkedIn scraper system.
This script demonstrates how to batch process a list of LinkedIn profiles.
"""

import os
import sys
import logging
import time
import random  # Ensure random is imported at the top level
import threading
from datetime import datetime
import json
import argparse
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('linkedin_batch.log')
    ]
)

logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.scraper_config import PROFILE_QUEUE_PATH, MEMORY_PATH, PROFILES_DIR
from utils.event_bus import EventBus
from utils.state_machine import StateMachine
from services.linked_navigator.queue_manager import QueueManager
from services.linked_navigator.brain import Brain
from services.linked_navigator.batch_processor import BatchProcessor
from services.linked_navigator.human_like_behavior import HumanLikeBehavior
from services.linked_navigator.linkedin_navigator import LinkedInNavigator
from utils.playwright_driver import PlaywrightDriver

def session_callback(session_data: Dict[str, Any]) -> Dict[str, Any]:
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
        "profiles_failed": 0,
        "session_id": session_id,
        "start_time": datetime.now().isoformat()
    }
    
    try:
        # Initialize shared browser
        logger.info("Initializing browser for session...")
        
        # Check if a profile path was provided in the session data
        profile_path = session_data.get('profile_path', None)
        if not profile_path:
            # Default profile path (modify as needed)
            profile_path = r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5"
            logger.info(f"Using default profile path: {profile_path}")
        
        headless = session_data.get('headless', False)
        
        driver = PlaywrightDriver(
            mode="profile_mode",
            headless=headless,
            profile_path=profile_path,
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
        total_profiles = len(profiles)
        logger.info(f"Processing {total_profiles} profiles in this session")
        
        for i, profile in enumerate(profiles, 1):
            profile_url = profile["url"]
            logger.info(f"Processing profile {i}/{total_profiles}: {profile_url}")
            
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
                
            # Add a randomized delay between profiles for a more human-like pattern
            if i < total_profiles:  # Don't delay after the last profile
                # More natural randomization with millisecond precision (4.7 to 17.3 seconds)
                delay = 4.7 + random.random() * 12.6
                logger.info(f"Waiting {delay:.2f} seconds before next profile...")
                time.sleep(delay)
        
        # Close the shared browser
        logger.info("Closing browser...")
        driver.close()
        logger.info("Browser closed")
        
    except Exception as e:
        logger.error(f"Error executing session: {str(e)}")
        stats["error"] = str(e)
    
    # Record end time
    stats["end_time"] = datetime.now().isoformat()
    return stats

def process_profiles(profile_list: List[str], headless: bool = False, clean_queue: bool = False) -> Dict[str, Any]:
    """
    Process a list of LinkedIn profiles.
    
    Args:
        profile_list: List of LinkedIn profile URLs
        headless: Whether to run the browser in headless mode
        clean_queue: Whether to clean the queue before starting
        
    Returns:
        Dictionary with processing results
    """
    global queue_manager
    
    results = {
        "total_profiles": len(profile_list),
        "profiles_added": 0,
        "profiles_failed": 0,
        "start_time": datetime.now().isoformat()
    }
    
    try:
        # Initialize components
        logger.info("Initializing system components...")
        event_bus = EventBus.get_instance()
        state_machine = StateMachine()
        queue_manager = QueueManager()
        brain = Brain()
        batch_processor = BatchProcessor(brain, queue_manager)
        
        # Register session callback
        batch_processor.register_session_callback(session_callback)
        
        # Clean queue if requested
        if clean_queue:
            logger.info("Cleaning existing queue...")
            queue_manager.clear_queue()
        
        # Start the brain
        logger.info("Starting brain...")
        brain.start()
        
        # Add profiles to queue
        logger.info(f"Adding {len(profile_list)} profiles to queue...")
        result = batch_processor.add_profiles(profile_list, initiator="test_batch")
        
        # Update results
        results["profiles_added"] = len(result.get("added", []))
        results["profiles_failed"] = len(result.get("failed", []))
        results["already_queued"] = len(result.get("already_queued", []))
        
        logger.info(f"Added profiles result: {result}")
        
        # Wait for processing to complete
        logger.info("Waiting for profiles to be processed...")
        
        # Monitor until all profiles are processed or timeout
        start_time = time.time()
        timeout = 7200  # 2 hour timeout
        
        # Randomized check interval between 25-35 seconds
        while time.time() - start_time < timeout:
            # Get queue stats
            queue_stats = queue_manager.get_queue_stats()
            brain_status = brain.get_status()
            
            logger.info(f"Queue stats: {queue_stats}")
            logger.info(f"Brain state: {brain_status['state']}")
            
            # Check if all profiles are done
            if queue_stats["pending"] == 0 and queue_stats["completed"] > 0:
                logger.info("All profiles processed!")
                break
            
            # Randomized wait before checking again (25-35 seconds with millisecond precision)
            check_interval = 25 + random.random() * 10
            time.sleep(check_interval)
        
        # Get final stats
        final_queue_stats = queue_manager.get_queue_stats()
        results["completed"] = final_queue_stats.get("completed", 0)
        results["failed"] = final_queue_stats.get("status_counts", {}).get("failed", 0)
        results["end_time"] = datetime.now().isoformat()
        
        # Stop the brain
        logger.info("Stopping brain...")
        brain.stop()
        
        logger.info("Batch processing completed")
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        results["error"] = str(e)
        
        # Try to stop the brain
        if 'brain' in locals():
            brain.stop()
    
    return results

def save_results(results: Dict[str, Any], filename: str = "batch_results.json") -> None:
    """
    Save batch processing results to a file.
    
    Args:
        results: Results dictionary
        filename: Output filename
    """
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

def main():
    """Main function to process LinkedIn profiles."""
    parser = argparse.ArgumentParser(description="Batch process LinkedIn profiles")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--clean", action="store_true", help="Clean existing queue before starting")
    parser.add_argument("--profiles", type=str, help="Path to JSON file with profile URLs")
    args = parser.parse_args()
    
    # Get profiles from command line argument or use defaults
    if args.profiles and os.path.exists(args.profiles):
        try:
            with open(args.profiles, 'r') as f:
                profiles = json.load(f)
            logger.info(f"Loaded {len(profiles)} profiles from {args.profiles}")
        except Exception as e:
            logger.error(f"Error loading profiles from {args.profiles}: {str(e)}")
            return
    else:
        # Default profiles list
        profiles = [
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
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(PROFILE_QUEUE_PATH), exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)
    
    # Process profiles
    results = process_profiles(profiles, headless=args.headless, clean_queue=args.clean)
    
    # Save results
    save_results(results)

if __name__ == "__main__":
    # No need to import random here since it's already imported at the top level
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)