# test_browser.py
import sys
import time
from utils.playwright_driver import PlaywrightDriver

def main():
    # Path to your Chrome profile
    profile_path = r"C:\Users\MA\AppData\Local\Google\Chrome\User Data\Profile 5"
    
    # URL to navigate to
    url = "https://www.linkedin.com/feed/"
    
    print(f"Opening Chrome with profile: {profile_path}")
    print(f"Navigating to: {url}")
    
    # Initialize the Playwright driver with your profile
    driver = PlaywrightDriver(
        mode="profile_mode",  # Use profile mode to load your existing Chrome profile
        profile_path=profile_path,
        headless=False,  # Set to False to see the browser window
        user_agent_type="default"  # Use default user agent
    )
    
    try:
        # Start the browser
        driver.start()
        
        # Navigate to LinkedIn
        print("Navigating to LinkedIn...")
        success = driver.navigate(url)
        
        if success:
            print("Successfully navigated to LinkedIn")
        else:
            print("Failed to navigate to LinkedIn")
        
        # Sleep for 20 seconds
        print("Waiting for 20 seconds...")
        time.sleep(20)
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close the browser
        print("Closing browser...")
        driver.close()
        print("Browser closed")

if __name__ == "__main__":
    main()