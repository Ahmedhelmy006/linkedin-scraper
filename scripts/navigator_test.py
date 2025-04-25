# test_enhanced_scraper.py
"""
Test script for the enhanced LinkedIn scraper system.

This script tests the key enhancements:
1. Human-like behavior patterns
2. Multi-tab support
3. Profile-aware session management
4. Natural navigation patterns
"""

import os
import sys
import logging
import time
import random
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.playwright_driver import PlaywrightDriver
from services.linked_navigator.human_like_behavior import HumanLikeBehavior
from services.linked_navigator.linkedin_navigator import LinkedInNavigator
from services.linked_navigator.brain import Brain
from config.scraper_config import RANDOM_SITES

def test_multi_tab_support():
    """Test the multi-tab functionality in PlaywrightDriver."""
    logger.info("=== Testing Multi-Tab Support ===")
    
    driver = PlaywrightDriver(
        mode="profile_mode",
        headless=False,
        profile_path=r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5",
        user_agent_type="random"
    )
    
    try:
        # Start the browser
        logger.info("Starting browser...")
        driver.start()
        
        # Navigate to a site in the main tab
        logger.info("Navigating to LinkedIn in main tab...")
        driver.navigate("https://www.linkedin.com/feed/")
        time.sleep(3)
        
        # Create a new tab
        logger.info("Creating new tab...")
        success, new_tab_index = driver.new_page()
        
        if not success:
            logger.error("Failed to create new tab")
            return False
            
        logger.info(f"New tab created with index {new_tab_index}")
        
        # Navigate to a different site in the new tab
        random_site = random.choice(RANDOM_SITES)
        logger.info(f"Navigating to {random_site} in new tab...")
        driver.navigate(random_site, page_index=new_tab_index)
        time.sleep(5)
        
        # Switch back to the first tab
        logger.info("Switching back to first tab...")
        driver.switch_page(0)
        time.sleep(3)
        
        # Get current URL to verify we're on the right tab
        current_url = driver.get_current_url()
        logger.info(f"Current URL in first tab: {current_url}")
        
        # Close the second tab
        logger.info("Closing second tab...")
        driver.close_page(new_tab_index)
        
        # Verify tab count
        tab_count = driver.get_page_count()
        logger.info(f"Remaining tab count: {tab_count}")
        
        logger.info("Multi-tab test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in multi-tab test: {str(e)}")
        return False
        
    finally:
        # Close the browser
        driver.close()

def test_human_like_behavior():
    """Test the enhanced human-like behavior patterns."""
    logger.info("=== Testing Human-Like Behavior ===")
    
    driver = PlaywrightDriver(
        mode="profile_mode",
        headless=False,
        profile_path=r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5",
        user_agent_type="random"
    )
    
    try:
        # Start the browser
        logger.info("Starting browser...")
        driver.start()
        
        # Initialize behavior controller
        behavior = HumanLikeBehavior(driver)
        
        # Test feed browsing with probabilistic duration
        logger.info("Testing feed browsing with probabilistic duration...")
        start_time = time.time()
        behavior.browse_feed()
        duration = time.time() - start_time
        logger.info(f"Feed browsing completed in {duration:.2f} seconds")
        
        # Test random site visit
        logger.info("Testing random site visit...")
        behavior.visit_random_site(duration_range=(15, 30))
        
        # Test profile navigation
        logger.info("Testing profile navigation...")
        behavior.navigate_to_profile("https://www.linkedin.com/in/satyanadella/")
        
        # Test reading simulation
        logger.info("Testing reading simulation...")
        behavior.simulate_reading(min_duration=5.0, max_duration=10.0)
        
        # Test viewport adjustment
        logger.info("Testing viewport adjustment...")
        behavior.adjust_viewport()
        
        logger.info("Human-like behavior test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in human-like behavior test: {str(e)}")
        return False
        
    finally:
        # Close the browser
        driver.close()

def test_navigation_patterns():
    """Test natural navigation patterns in the LinkedIn Navigator."""
    logger.info("=== Testing Natural Navigation Patterns ===")
    
    driver = PlaywrightDriver(
        mode="profile_mode",
        headless=False,
        profile_path=r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5",
        user_agent_type="random"
    )
    
    try:
        # Start the browser
        logger.info("Starting browser...")
        driver.start()
        
        # Initialize navigator
        navigator = LinkedInNavigator(
            profile_url="https://www.linkedin.com/in/satyanadella/",
            driver=driver
        )
        
        # Navigate to main profile and extract section links
        logger.info("Navigating to profile and extracting section links...")
        if not navigator.navigate_profile():
            logger.error("Failed to navigate to profile")
            return False
            
        # Log available sections
        logger.info(f"Available sections: {navigator.available_sections}")
        logger.info(f"Section links found: {len(navigator.section_links)}")
        
        # Navigate to a couple of sections
        if 'experience' in navigator.available_sections:
            logger.info("Navigating to experience section...")
            navigator.navigate_section('experience')
            time.sleep(2)
        
        if 'education' in navigator.available_sections:
            logger.info("Navigating to education section...")
            navigator.navigate_section('education')
            time.sleep(2)
            
        logger.info("Navigation patterns test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in navigation patterns test: {str(e)}")
        return False
        
    finally:
        # Close the browser
        navigator.close()

def test_session_management():
    """Test profile-aware session management."""
    logger.info("=== Testing Session Management ===")
    
    # Initialize brain
    brain = Brain()
    
    try:
        # Create a mock session
        session_id = f"test_session_{int(time.time())}"
        brain.current_session = {
            "id": session_id,
            "type": "regular",
            "start_time": datetime.now().isoformat(),
            "planned_duration": 300,  # 5 minutes
            "profiles": [
                {"url": "https://www.linkedin.com/in/profile1/"},
                {"url": "https://www.linkedin.com/in/profile2/"}
            ]
        }
        
        # Test marking profile started
        logger.info("Testing profile started marking...")
        brain.mark_profile_started()
        
        # Test session duration check while profile is in progress
        logger.info("Testing session duration check during profile...")
        
        # Artificially set the session to have exceeded its duration
        brain.current_session["start_time"] = (
            datetime.now().replace(
                hour=datetime.now().hour - 1
            ).isoformat()
        )
        
        should_terminate = brain.check_session_duration()
        logger.info(f"Should terminate during profile: {should_terminate}")
        logger.info(f"Should terminate after profile: {brain.should_terminate_session}")
        
        # Test marking profile completed
        logger.info("Testing profile completed marking...")
        brain.mark_profile_completed()
        
        # Check if session should terminate now
        should_terminate = brain.check_session_duration()
        logger.info(f"Should terminate after profile completed: {should_terminate}")
        
        # End the session
        logger.info("Testing session ended...")
        brain.session_ended(session_id, {
            "profiles_completed": 1,
            "profiles_failed": 0
        })
        
        logger.info("Session management test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in session management test: {str(e)}")
        return False
        
    finally:
        # Stop the brain
        brain.stop()

def test_full_profile_scrape():
    """Test a complete profile scraping operation with all enhancements."""
    logger.info("=== Testing Full Profile Scrape ===")
    
    driver = PlaywrightDriver(
        mode="profile_mode",
        headless=False,
        profile_path=r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5",
        user_agent_type="random"
    )
    
    try:
        # Start the browser
        logger.info("Starting browser...")
        driver.start()
        
        # Initialize behavior controller
        behavior = HumanLikeBehavior(driver)
        
        # Initialize navigator with a test profile
        test_profile = "https://www.linkedin.com/in/satyanadella/"
        
        navigator = LinkedInNavigator(
            profile_url=test_profile,
            driver=driver,
            behavior=behavior
        )
        
        # Create a brain instance for session tracking
        brain = Brain()
        brain.current_session = {
            "id": f"test_session_{int(time.time())}",
            "start_time": datetime.now().isoformat(),
            "planned_duration": 600,  # 10 minutes
            "profiles": [{"url": test_profile}]
        }
        
        # Mark profile started
        brain.mark_profile_started()
        
        # Scrape all sections
        logger.info(f"Scraping all sections for profile: {test_profile}")
        if not navigator.scrape_all_sections():
            logger.error("Failed to scrape profile sections")
            return False
            
        # Save profile data
        profile_dir = navigator.save_profile_data()
        logger.info(f"Profile data saved to: {profile_dir}")
        
        # Check what sections were scraped
        logger.info(f"Sections scraped: {navigator.metadata['sections_scraped']}")
        
        # Mark profile completed
        brain.mark_profile_completed()
        
        logger.info("Full profile scrape test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in full profile scrape test: {str(e)}")
        return False
        
    finally:
        # Close resources
        navigator.close()
        brain.stop()

if __name__ == "__main__":
    # Run the tests
    print("\n" + "="*50)
    print("ENHANCED LINKEDIN SCRAPER SYSTEM TEST")
    print("="*50 + "\n")
    
    tests = [
        ("Multi-Tab Support", test_multi_tab_support),
        ("Human-Like Behavior", test_human_like_behavior),
        ("Navigation Patterns", test_navigation_patterns),
        ("Session Management", test_session_management),
        ("Full Profile Scrape", test_full_profile_scrape)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\nRunning test: {test_name}")
        print("-" * (len(test_name) + 14))
        
        try:
            start_time = time.time()
            success = test_func()
            duration = time.time() - start_time
            
            results[test_name] = {
                "success": success,
                "duration": duration
            }
            
            status = "PASSED" if success else "FAILED"
            print(f"Test {status} in {duration:.2f} seconds\n")
            
        except Exception as e:
            print(f"Test ERROR: {str(e)}\n")
            results[test_name] = {
                "success": False,
                "error": str(e)
            }
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for r in results.values() if r.get("success", False))
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result.get("success", False) else "✗ FAILED"
        if "duration" in result:
            print(f"{status} - {test_name} ({result['duration']:.2f}s)")
        else:
            print(f"{status} - {test_name} (ERROR: {result.get('error', 'Unknown error')})")
    
    print(f"\nOverall: {passed}/{total} tests passed")