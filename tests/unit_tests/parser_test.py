# test_parser.py
"""
Test script for the LinkedIn profile parser.
"""

import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the parser modules
from services.parser.profile_parser import LinkedInProfileParser


def test_single_profile(profile_dir):
    """Test parsing a single profile directory."""
    logger.info(f"Testing parser on profile directory: {profile_dir}")
    
    # Verify the directory exists
    if not os.path.exists(profile_dir):
        logger.error(f"Profile directory not found: {profile_dir}")
        return
    
    # Check for metadata file
    metadata_files = [f for f in os.listdir(profile_dir) if f.endswith('_metadata.json')]
    if not metadata_files:
        logger.warning(f"No metadata file found in {profile_dir}")
    else:
        logger.info(f"Found metadata file: {metadata_files[0]}")
    
    # List HTML files
    html_files = [f for f in os.listdir(profile_dir) if f.endswith('.html')]
    logger.info(f"Found {len(html_files)} HTML files: {', '.join(html_files)}")
    
    # Initialize the parser
    try:
        parser = LinkedInProfileParser(profile_dir)
        
        # Parse all sections
        logger.info("Parsing profile sections...")
        profile_data = parser.parse_all()
        
        # Display basic information
        metadata = profile_data.get("metadata", {})
        basic_info = profile_data.get("basic_info", {})
        
        print("\n" + "="*50)
        print(f"Profile: {metadata.get('profile_name', 'Unknown')}")
        print(f"URL: {metadata.get('profile_url', 'Unknown')}")
        print(f"Headline: {basic_info.get('headline', 'Unknown')}")
        print(f"Location: {basic_info.get('location', 'Unknown')}")
        print("="*50)
        
        # Display section counts
        print("\nSection Information:")
        print(f"- Experiences: {len(profile_data.get('experiences', []))}")
        print(f"- Education entries: {len(profile_data.get('education', []))}")
        print(f"- Skills: {len(profile_data.get('skills', []))}")
        print(f"- Languages: {len(profile_data.get('languages', []))}")
        
        # Save the parsed data
        output_path = os.path.join(profile_dir, "parsed_profile.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2)
        
        logger.info(f"Saved parsed data to {output_path}")
        print(f"\nParsed data saved to: {output_path}")
        
        return profile_data
        
    except Exception as e:
        logger.error(f"Error parsing profile: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Main entry point for the test script."""
    # Use provided directory or default
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
    else:
        profile_dir = r"D:\aifc_members_lookup\data\linkedin_profiles\Anna Kourula"
    
    test_single_profile(profile_dir)

if __name__ == "__main__":
    main()