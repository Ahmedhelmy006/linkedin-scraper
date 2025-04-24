def safe_call(func, *args, **kwargs):
    """
    Safely call a function and handle any exceptions.
    
    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call, or None if an exception occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Error calling {func.__name__}: {e}")
        return None
    
    # Add to utils/helper.py

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def save_linkedin_profile_data(
    profile_name: str,
    profile_url: str,
    sections_data: Dict[str, str],
    base_dir: str = "linkedin_profiles",
    additional_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Save LinkedIn profile data to organized directory structure.
    
    Args:
        profile_name: Name of the profile owner
        profile_url: URL of the LinkedIn profile
        sections_data: Dictionary mapping section names to HTML content
        base_dir: Base directory for saving profile data
        additional_metadata: Any additional metadata to include
        
    Returns:
        Path to the profile directory where data was saved
    """
    try:
        # Sanitize profile name for file system use
        safe_name = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in profile_name)
        safe_name = safe_name.strip()
        
        # Create profile directory
        profile_dir = os.path.join(base_dir, safe_name)
        os.makedirs(profile_dir, exist_ok=True)
        
        # Prepare metadata
        metadata = {
            "profile_name": profile_name,
            "profile_url": profile_url,
            "scrape_date": datetime.now().isoformat(),
            "sections_scraped": [section for section, content in sections_data.items() if content]
        }
        
        # Add additional metadata if provided
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Save metadata
        metadata_file = os.path.join(profile_dir, f"{safe_name}_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Save HTML files
        for section_name, html_content in sections_data.items():
            if html_content:
                html_file = os.path.join(profile_dir, f"{section_name}.html")
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
        
        logger.info(f"Saved profile data to {profile_dir}")
        return profile_dir
        
    except Exception as e:
        logger.error(f"Error saving profile data: {str(e)}", exc_info=True)
        return ""