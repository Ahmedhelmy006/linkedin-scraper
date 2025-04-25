# scripts/parse_profiles.py
"""
Command-line interface for LinkedIn profile parsing.

This script provides a command-line interface to parse LinkedIn profiles
that have been scraped using the LinkedIn Navigator.
"""

import argparse
import logging
import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.parser.profile_parser import LinkedInProfileParser
from services.parser.parser_utils import (
    find_profile_directories,
    batch_parse_profiles,
    save_batch_results,
    extract_field_statistics,
    build_profile_index,
    merge_profiles_by_company
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"linkedin_parser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the LinkedIn parser CLI."""
    parser = argparse.ArgumentParser(description="LinkedIn Profile Parser")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Parse a single profile
    single_parser = subparsers.add_parser("parse", help="Parse a single LinkedIn profile")
    single_parser.add_argument("profile_dir", help="Directory containing the profile HTML files")
    single_parser.add_argument("--output", "-o", help="Output JSON file path")
    
    # Batch parse multiple profiles
    batch_parser = subparsers.add_parser("batch", help="Batch parse multiple LinkedIn profiles")
    batch_parser.add_argument("base_dir", help="Base directory containing profile subdirectories")
    batch_parser.add_argument("--output", "-o", help="Output directory for parsed JSON files")
    batch_parser.add_argument("--results", "-r", help="Path to save batch results summary")
    batch_parser.add_argument("--workers", "-w", type=int, default=4, help="Maximum number of worker threads")
    
    # List profile directories
    list_parser = subparsers.add_parser("list", help="List all profile directories in a base directory")
    list_parser.add_argument("base_dir", help="Base directory containing profile subdirectories")
    
    # Build profile index
    index_parser = subparsers.add_parser("index", help="Build an index of parsed profiles")
    index_parser.add_argument("parsed_dir", help="Directory containing parsed JSON files")
    index_parser.add_argument("--output", "-o", help="Output JSON file path for the index")
    
    # Merge profiles by company
    company_parser = subparsers.add_parser("company", help="Find and merge profiles related to a company")
    company_parser.add_argument("parsed_dir", help="Directory containing parsed JSON files")
    company_parser.add_argument("company_name", help="Company name to search for")
    company_parser.add_argument("--output", "-o", help="Output JSON file path for the merged data")
    
    # Field statistics
    stats_parser = subparsers.add_parser("stats", help="Extract statistics for specific fields")
    stats_parser.add_argument("batch_results", help="Path to batch results JSON file")
    stats_parser.add_argument("fields", nargs="+", help="Fields to extract statistics for (e.g., 'education.school')")
    stats_parser.add_argument("--output", "-o", help="Output JSON file path for the statistics")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Execute the appropriate command
        if args.command == "parse":
            # Parse a single profile
            logger.info(f"Parsing profile in directory: {args.profile_dir}")
            
            profile_parser = LinkedInProfileParser(args.profile_dir)
            profile_data = profile_parser.parse_all()
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, indent=2)
                logger.info(f"Saved parsed data to {args.output}")
            else:
                output_path = profile_parser.save_parsed_data()
                logger.info(f"Saved parsed data to {output_path}")
                
            print(f"Successfully parsed profile: {profile_data.get('metadata', {}).get('profile_name', 'Unknown')}")
            
        elif args.command == "batch":
            # Batch parse multiple profiles
            logger.info(f"Batch parsing profiles in directory: {args.base_dir}")
            
            results = batch_parse_profiles(
                args.base_dir, 
                args.output, 
                args.workers
            )
            
            # Save batch results if requested
            if args.results:
                save_batch_results(results, args.results)
                
            print(f"Batch parsing completed: {results['profiles_parsed']} succeeded, {results['profiles_failed']} failed")
            print(f"Elapsed time: {results['elapsed_time']:.2f} seconds")
            
        elif args.command == "list":
            # List profile directories
            profiles = find_profile_directories(args.base_dir)
            print(f"Found {len(profiles)} profile directories:")
            for profile_dir in profiles:
                print(f"  - {profile_dir}")
                
        elif args.command == "index":
            # Build profile index
            index = build_profile_index(args.parsed_dir, args.output)
            print(f"Built index with {index['total_profiles']} profiles")
            
            if not args.output:
                # Print sample if not saving to file
                print("\nSample profiles:")
                for profile in index['profiles'][:5]:
                    print(f"  - {profile['name']} ({profile['headline']})")
                
                if len(index['profiles']) > 5:
                    print(f"  ... and {len(index['profiles']) - 5} more")
            
        elif args.command == "company":
            # Merge profiles by company
            company_data = merge_profiles_by_company(args.parsed_dir, args.company_name, args.output)
            print(f"Found {company_data['profiles_found']} profiles related to '{args.company_name}'")
            print(f"  - Current employees: {len(company_data['current_employees'])}")
            print(f"  - Past employees: {len(company_data['past_employees'])}")
            
            if not args.output:
                # Print sample if not saving to file
                print("\nCurrent employees:")
                for employee in company_data['current_employees'][:5]:
                    print(f"  - {employee['name']} ({employee['headline']})")
                
                if len(company_data['current_employees']) > 5:
                    print(f"  ... and {len(company_data['current_employees']) - 5} more")
            
        elif args.command == "stats":
            # Extract field statistics
            with open(args.batch_results, 'r', encoding='utf-8') as f:
                batch_results = json.load(f)
            
            stats = extract_field_statistics(batch_results, args.fields)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2)
                print(f"Saved field statistics to {args.output}")
            else:
                # Print statistics
                for field, values in stats.items():
                    print(f"\nStatistics for {field}:")
                    
                    # Print top 10 values
                    for i, (value, count) in enumerate(list(values.items())[:10]):
                        print(f"  {i+1}. {value}: {count}")
                    
                    if len(values) > 10:
                        print(f"  ... and {len(values) - 10} more values")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()