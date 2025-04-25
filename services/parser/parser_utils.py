# services/parser/parser_utils.py
"""
Utility functions for batch processing of LinkedIn profile data.

This module provides helper functions to identify, process, and organize
parsed LinkedIn profile data across multiple profiles.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import concurrent.futures
from datetime import datetime
import time
import traceback
import shutil

from services.parser.profile_parser import LinkedInProfileParser

logger = logging.getLogger(__name__)

def find_profile_directories(base_dir: str) -> List[str]:
    """
    Find all profile directories under the base directory.
    
    Args:
        base_dir: Base directory containing profile subdirectories
        
    Returns:
        List of profile directory paths
    """
    profile_dirs = []
    
    try:
        # Check if base directory exists
        if not os.path.exists(base_dir):
            logger.error(f"Base directory {base_dir} does not exist")
            return []
        
        # Look for directories that contain a metadata file
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            
            # Check if it's a directory
            if os.path.isdir(item_path):
                # Check if it contains a metadata file
                has_metadata = any(f.endswith('_metadata.json') for f in os.listdir(item_path))
                
                if has_metadata:
                    profile_dirs.append(item_path)
                    logger.debug(f"Found profile directory: {item_path}")
                else:
                    logger.debug(f"Skipping directory without metadata: {item_path}")
        
        logger.info(f"Found {len(profile_dirs)} profile directories in {base_dir}")
        return profile_dirs
        
    except Exception as e:
        logger.error(f"Error finding profile directories: {str(e)}")
        return []

def parse_profile(profile_dir: str, output_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parse a single LinkedIn profile.
    
    Args:
        profile_dir: Path to the profile directory
        output_dir: Directory to save parsed data (if None, saves in profile directory)
        
    Returns:
        Parsed profile data as a dictionary, or None if parsing failed
    """
    try:
        logger.info(f"Parsing profile in directory: {profile_dir}")
        
        # Initialize the parser
        parser = LinkedInProfileParser(profile_dir)
        
        # Parse all available sections
        profile_data = parser.parse_all()
        
        # Save parsed data
        if output_dir:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Get profile name for filename
            profile_name = profile_data.get("metadata", {}).get("profile_name", "unknown_profile")
            safe_name = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in profile_name).strip()
            
            output_path = os.path.join(output_dir, f"{safe_name}_parsed_data.json")
            
            # Save to specified output directory
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
                
            logger.info(f"Saved parsed data to {output_path}")
        else:
            # Save in the profile directory
            parser.save_parsed_data()
        
        return profile_data
        
    except Exception as e:
        logger.error(f"Error parsing profile in {profile_dir}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def batch_parse_profiles(
    base_dir: str, 
    output_dir: Optional[str] = None, 
    max_workers: int = 4,
    include_raw_html: bool = False
) -> Dict[str, Any]:
    """
    Parse multiple LinkedIn profiles in parallel.
    
    Args:
        base_dir: Base directory containing profile subdirectories
        output_dir: Directory to save individual parsed data files
        max_workers: Maximum number of parallel workers
        include_raw_html: Whether to include the raw HTML in the result
        
    Returns:
        Dictionary with parsing statistics and results
    """
    start_time = time.time()
    
    # Find all profile directories
    profile_dirs = find_profile_directories(base_dir)
    
    if not profile_dirs:
        logger.warning(f"No profile directories found in {base_dir}")
        return {
            "status": "completed",
            "profiles_found": 0,
            "profiles_parsed": 0,
            "profiles_failed": 0,
            "elapsed_time": 0,
            "data": []
        }
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Parse profiles in parallel
    parsed_data = []
    failed_profiles = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit parsing tasks
        future_to_profile = {
            executor.submit(parse_profile, profile_dir, output_dir): profile_dir
            for profile_dir in profile_dirs
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_profile):
            profile_dir = future_to_profile[future]
            
            try:
                profile_data = future.result()
                
                if profile_data:
                    # Remove HTML content if not requested
                    if not include_raw_html and 'html_content' in profile_data:
                        del profile_data['html_content']
                    
                    parsed_data.append(profile_data)
                    logger.info(f"Successfully parsed profile: {profile_data.get('metadata', {}).get('profile_name', 'Unknown')}")
                else:
                    failed_profiles.append(profile_dir)
                    logger.warning(f"Failed to parse profile in {profile_dir}")
                    
            except Exception as e:
                failed_profiles.append(profile_dir)
                logger.error(f"Exception while parsing {profile_dir}: {str(e)}")
    
    # Calculate statistics
    elapsed_time = time.time() - start_time
    
    results = {
        "status": "completed",
        "profiles_found": len(profile_dirs),
        "profiles_parsed": len(parsed_data),
        "profiles_failed": len(failed_profiles),
        "failed_directories": failed_profiles,
        "elapsed_time": elapsed_time,
        "timestamp": datetime.now().isoformat(),
        "data": parsed_data
    }
    
    logger.info(f"Batch parsing completed: {len(parsed_data)} succeeded, {len(failed_profiles)} failed, took {elapsed_time:.2f} seconds")
    
    return results

def save_batch_results(results: Dict[str, Any], output_path: str) -> bool:
    """
    Save batch parsing results to a JSON file.
    
    Args:
        results: Batch parsing results to save
        output_path: Path to save the results to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Saved batch results to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving batch results: {str(e)}")
        return False

def extract_field_statistics(batch_results: Dict[str, Any], fields: List[str]) -> Dict[str, Dict[str, int]]:
    """
    Extract statistics for specific fields from batch results.
    
    Args:
        batch_results: Results from batch_parse_profiles
        fields: List of fields to get statistics for (e.g., ['education.school', 'skills.name'])
        
    Returns:
        Dictionary with field value frequencies
    """
    statistics = {}
    
    try:
        profiles = batch_results.get("data", [])
        
        for field_path in fields:
            field_parts = field_path.split('.')
            field_stats = {}
            
            # Process each profile
            for profile in profiles:
                # Navigate through the field path
                current = profile
                valid_path = True
                
                for part in field_parts:
                    if part in current:
                        current = current[part]
                    else:
                        valid_path = False
                        break
                
                if not valid_path:
                    continue
                
                # Handle different data types
                if isinstance(current, list):
                    # For lists, extract values from each item
                    if len(field_parts) > 1 and field_parts[-2] in profile:
                        # Handle nested lists of objects
                        for item in current:
                            value = item.get(field_parts[-1], "")
                            if value:
                                field_stats[value] = field_stats.get(value, 0) + 1
                else:
                    # For scalar values
                    if current:
                        field_stats[str(current)] = field_stats.get(str(current), 0) + 1
            
            # Sort by frequency (highest first)
            field_stats = {k: v for k, v in sorted(field_stats.items(), key=lambda item: item[1], reverse=True)}
            statistics[field_path] = field_stats
    
    except Exception as e:
        logger.error(f"Error extracting field statistics: {str(e)}")
    
    return statistics

def build_profile_index(parsed_data_dir: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Build an index of all parsed LinkedIn profiles.
    
    Args:
        parsed_data_dir: Directory containing parsed profile JSON files
        output_path: Path to save the index (if None, doesn't save)
        
    Returns:
        Dictionary containing profile index
    """
    index = {
        "total_profiles": 0,
        "last_updated": datetime.now().isoformat(),
        "profiles": []
    }
    
    try:
        # Find all parsed data JSON files
        if not os.path.exists(parsed_data_dir):
            logger.error(f"Directory {parsed_data_dir} does not exist")
            return index
        
        json_files = [f for f in os.listdir(parsed_data_dir) if f.endswith('_parsed_data.json')]
        
        for json_file in json_files:
            file_path = os.path.join(parsed_data_dir, json_file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                # Extract key information for the index
                metadata = profile_data.get("metadata", {})
                basic_info = profile_data.get("basic_info", {})
                
                profile_summary = {
                    "name": metadata.get("profile_name", "Unknown"),
                    "profile_url": metadata.get("profile_url", ""),
                    "headline": basic_info.get("headline", ""),
                    "location": basic_info.get("location", ""),
                    "file_path": file_path,
                    "scrape_date": metadata.get("scrape_date", ""),
                    "parsing_date": profile_data.get("parsing_date", ""),
                    "num_experiences": len(profile_data.get("experiences", [])),
                    "num_education": len(profile_data.get("education", [])),
                    "num_skills": len(profile_data.get("skills", []))
                }
                
                index["profiles"].append(profile_summary)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        
        # Update total count
        index["total_profiles"] = len(index["profiles"])
        
        # Sort profiles by name
        index["profiles"].sort(key=lambda p: p["name"])
        
        # Save index if output path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
            logger.info(f"Saved profile index to {output_path}")
        
        logger.info(f"Built index with {index['total_profiles']} profiles")
        return index
        
    except Exception as e:
        logger.error(f"Error building profile index: {str(e)}")
        return index

def merge_profiles_by_company(
    parsed_data_dir: str, 
    company_name: str, 
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find all profiles that mention a specific company and merge their data.
    
    Args:
        parsed_data_dir: Directory containing parsed profile JSON files
        company_name: Company name to search for
        output_path: Path to save the merged data (if None, doesn't save)
        
    Returns:
        Dictionary containing merged profile data for the company
    """
    company_data = {
        "company_name": company_name,
        "profiles_found": 0,
        "current_employees": [],
        "past_employees": [],
        "all_employees": []
    }
    
    try:
        # Find all parsed data JSON files
        if not os.path.exists(parsed_data_dir):
            logger.error(f"Directory {parsed_data_dir} does not exist")
            return company_data
        
        json_files = [f for f in os.listdir(parsed_data_dir) if f.endswith('_parsed_data.json')]
        
        for json_file in json_files:
            file_path = os.path.join(parsed_data_dir, json_file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                # Check experiences for the company
                experiences = profile_data.get("experiences", [])
                company_experiences = []
                is_current = False
                
                for exp in experiences:
                    company = exp.get("company", "").lower()
                    
                    # Check if the company name matches
                    if company_name.lower() in company:
                        company_experiences.append(exp)
                        
                        # Check if this is a current experience
                        date_range = exp.get("date_range", "").lower()
                        if "present" in date_range:
                            is_current = True
                
                # If company was found in experiences, add to results
                if company_experiences:
                    # Extract relevant profile information
                    metadata = profile_data.get("metadata", {})
                    basic_info = profile_data.get("basic_info", {})
                    
                    employee_data = {
                        "name": metadata.get("profile_name", "Unknown"),
                        "profile_url": metadata.get("profile_url", ""),
                        "headline": basic_info.get("headline", ""),
                        "location": basic_info.get("location", ""),
                        "company_experiences": company_experiences,
                        "is_current": is_current,
                        "education": profile_data.get("education", []),
                        "skills": profile_data.get("skills", [])
                    }
                    
                    # Add to appropriate lists
                    company_data["all_employees"].append(employee_data)
                    
                    if is_current:
                        company_data["current_employees"].append(employee_data)
                    else:
                        company_data["past_employees"].append(employee_data)
            
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        
        # Update counts
        company_data["profiles_found"] = len(company_data["all_employees"])
        company_data["current_count"] = len(company_data["current_employees"])
        company_data["past_count"] = len(company_data["past_employees"])
        
        # Sort employees by name
        company_data["all_employees"].sort(key=lambda p: p["name"])
        company_data["current_employees"].sort(key=lambda p: p["name"])
        company_data["past_employees"].sort(key=lambda p: p["name"])
        
        # Save merged data if output path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(company_data, f, indent=2)
            logger.info(f"Saved company data to {output_path}")
        
        logger.info(f"Found {company_data['profiles_found']} profiles related to {company_name}")
        return company_data
        
    except Exception as e:
        logger.error(f"Error merging profiles by company: {str(e)}")
        return company_data