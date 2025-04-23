# test_lookup_csv.py
import csv
import logging
import time
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.lookup import LinkedInProfileLookup
from utils.email_validator import EmailValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def ensure_directory_exists(directory_path):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        logger.info(f"Created directory: {directory_path}")

def process_csv(input_csv_path, results_dir):
    """
    Process a CSV file to find and update missing LinkedIn URLs.
    
    Args:
        input_csv_path: Path to the input CSV file
        results_dir: Directory to store results
    """
    # Ensure results directory exists
    ensure_directory_exists(results_dir)
    
    # Create timestamped copy of the original CSV in results directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_csv_path = os.path.join(results_dir, f"linkedin_results_{timestamp}.csv")
    
    # Copy the original file to results directory as a starting point
    shutil.copy2(input_csv_path, result_csv_path)
    logger.info(f"Created initial results file: {result_csv_path}")
    
    # Initialize the LinkedIn profile lookup service
    lookup_service = LinkedInProfileLookup()
    
    # Read CSV and identify rows needing LinkedIn URLs
    rows_to_process = []
    
    with open(input_csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Check if required columns exist
        fieldnames = reader.fieldnames
        if 'Email' not in fieldnames or 'Linkedin URL' not in fieldnames:
            logger.error("CSV must contain 'Email' and 'Linkedin URL' columns")
            return
        
        # Collect rows that need processing
        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is headers
            email = row.get('Email', '').strip()
            linkedin_url = row.get('Linkedin URL', '').strip()
            
            # Skip if already has LinkedIn URL or no email
            if linkedin_url or not email:
                continue
                
            # Validate email format
            if not EmailValidator.is_valid(email):
                logger.warning(f"Row {i}: Invalid email format: {email}")
                continue
                
            # Add to processing queue
            rows_to_process.append((i, row))
    
    logger.info(f"Found {len(rows_to_process)} rows with missing LinkedIn URLs")
    
    # Process each row that needs a LinkedIn URL
    for row_index, row in rows_to_process:
        email = row['Email'].strip()
        
        logger.info(f"Processing row {row_index}: {email}")
        
        try:
            # Look up the LinkedIn profile
            linkedin_url = lookup_service.lookup_by_email(email)
            
            if linkedin_url:
                logger.info(f"Found LinkedIn URL for {email}: {linkedin_url}")
                
                # Update the result CSV with the found URL
                update_csv_row(result_csv_path, row_index, 'Linkedin URL', linkedin_url)
                
                # Add a small delay to avoid overwhelming the service
                time.sleep(1)
            else:
                logger.warning(f"No LinkedIn URL found for {email}")
        except Exception as e:
            logger.error(f"Error processing {email}: {str(e)}")
            
            # If we hit rate limits, wait a bit longer
            if "rate limit" in str(e).lower():
                logger.info("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)
    
    logger.info(f"CSV processing complete. Results saved to {result_csv_path}")

def update_csv_row(csv_path, row_index, column_name, new_value):
    """
    Update a specific cell in a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        row_index: The row index (1-based, header is row 1)
        column_name: The column name to update
        new_value: The new value to set
    """
    # Read entire CSV into memory
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        
        # Add each row to our list
        current_row = 2  # Start at row 2 (after header)
        for row in reader:
            if current_row == row_index:
                # This is the row we want to update
                row[column_name] = new_value
            rows.append(row)
            current_row += 1
    
    # Write the updated data back to the CSV
    with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"Updated row {row_index}, column '{column_name}' with value: {new_value}")

def main():
    """Main entry point for the script."""
    # Input CSV path
    input_csv_path = r"C:\Users\MA\Downloads\AI Finance Club Reports - Circle.csv"
    
    # Results directory
    results_dir = "results"
    
    # Process the CSV
    logger.info(f"Starting to process {input_csv_path}")
    process_csv(input_csv_path, results_dir)

if __name__ == "__main__":
    main()