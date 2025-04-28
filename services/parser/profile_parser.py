# services/parser/parser.py
"""
LinkedIn profile HTML parser.

This module provides functionalities to parse HTML content from
scraped LinkedIn profiles and extract structured data.
"""

import logging
import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime
import traceback


logger = logging.getLogger(__name__)

class LinkedInProfileParser:
    """
    Parses LinkedIn profile HTML content to extract structured data.
    
    This class processes HTML files for different sections of a LinkedIn profile
    and converts them to structured data suitable for analysis or storage.
    """
    
    def __init__(self, profile_dir: str):
        """
        Initialize the profile parser with the profile directory.
        
        Args:
            profile_dir: Path to the directory containing profile HTML files
        """
        self.profile_dir = profile_dir
        self.metadata = self._load_metadata()
        self.profile_data = {
            "basic_info": {},
            "experiences": [],
            "education": [],
            "skills": [],
            "recommendations": [],
            "courses": [],
            "languages": [],
            "interests": []
        }
        
        # Store raw HTML content
        self.html_content = {}
        
    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load profile metadata from the metadata JSON file.
        
        Returns:
            Dictionary containing profile metadata
        """
        try:
            # Find metadata file (it should follow the pattern: profile_name_metadata.json)
            metadata_files = [f for f in os.listdir(self.profile_dir) if f.endswith('_metadata.json')]
            
            if not metadata_files:
                logger.warning(f"No metadata file found in {self.profile_dir}")
                return {}
            
            metadata_path = os.path.join(self.profile_dir, metadata_files[0])
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            logger.info(f"Loaded metadata for profile: {metadata.get('profile_name', 'Unknown')}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error loading metadata: {str(e)}")
            return {}
    
    def _load_html_file(self, section_name: str) -> Optional[str]:
        """
        Load HTML content for a specific section.
        
        Args:
            section_name: Name of the section to load
            
        Returns:
            HTML content as string, or None if file doesn't exist
        """
        try:
            file_path = os.path.join(self.profile_dir, f"{section_name}.html")
            
            if not os.path.exists(file_path):
                logger.warning(f"HTML file for section '{section_name}' not found")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            self.html_content[section_name] = html_content
            return html_content
            
        except Exception as e:
            logger.error(f"Error loading HTML for section {section_name}: {str(e)}")
            return None
    
    def parse_all(self) -> Dict[str, Any]:
        """
        Parse all available sections of the profile.
        
        Returns:
            Dictionary containing structured data from all profile sections
        """
        # Basic profile info from main profile
        if self._load_html_file("main_profile"):
            self.parse_basic_info()
        
        # Parse other sections if HTML files are available
        sections = [
            ("experience", self.parse_experience),
            ("education", self.parse_education),
            ("skills", self.parse_skills),
            ("recommendations", self.parse_recommendations),
            ("courses", self.parse_courses),
            ("languages", self.parse_languages),
            ("interests", self.parse_interests)
        ]
        
        for section_name, parse_method in sections:
            if self._load_html_file(section_name):
                parse_method()
        
        # Add metadata to the result
        result = {
            "metadata": self.metadata,
            **self.profile_data
        }
        
        return result
    
    def parse_basic_info(self) -> Dict[str, Any]:
        """
        Parse basic profile information from the main profile HTML.
        
        Returns:
            Dictionary containing basic profile information
        """
        if "main_profile" not in self.html_content:
            logger.warning("Cannot parse basic info: main profile HTML not loaded")
            return {}
        
        html = self.html_content["main_profile"]
        soup = BeautifulSoup(html, 'html.parser')
        
        basic_info = {
            "name": self.metadata.get("profile_name", ""),
            "profile_url": self.metadata.get("profile_url", ""),
            "headline": "",
            "location": "",
            "about": "",
            "followers": "",
            "connections": ""
        }
        
        try:
            # Extract headline - use more specific selector
            headline_elem = soup.select_one('div.text-body-medium')
            if headline_elem:
                basic_info["headline"] = headline_elem.text.strip()
            
            # Extract location - specific to profile page
            location_elem = soup.select_one('span.text-body-small.inline.t-black--light.break-words')
            if location_elem:
                basic_info["location"] = location_elem.text.strip()
            
            # Extract connections
            connections_elem = soup.select_one('li.text-body-small span.t-black--light')
            if connections_elem:
                connections_text = connections_elem.text.strip()
                # Extract the connections count
                if "connections" in connections_text:
                    basic_info["connections"] = connections_text.replace("connections", "").strip()
            
            # Extract about section
            about_section = soup.select_one('section#about, div.pv-about-section')
            if about_section:
                about_text_elem = about_section.select_one('div.display-flex div.t-14.t-normal.t-black')
                if about_text_elem:
                    about_text = about_text_elem.get_text(separator=' ', strip=True)
                    basic_info["about"] = about_text
            
            # Extract followers count if available
            followers_elem = soup.select_one('span:contains("followers")')
            if followers_elem:
                followers_text = followers_elem.text.strip()
                followers_match = re.search(r'([\d,]+)\s+followers', followers_text)
                if followers_match:
                    basic_info["followers"] = followers_match.group(1).replace(',', '')
            
        except Exception as e:
            logger.error(f"Error parsing basic info: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Update profile data
        self.profile_data["basic_info"] = basic_info
        
        return basic_info
    
    def parse_experience(self) -> List[Dict[str, Any]]:
        """
        Parse work experience information with improved data field mapping.
        
        Returns:
            List of dictionaries containing work experience entries
        """
        if "experience" not in self.html_content:
            logger.warning("Cannot parse experience: experience HTML not loaded")
            return []
        
        html = self.html_content["experience"]
        soup = BeautifulSoup(html, 'html.parser')
        
        experiences = []
        
        try:
            # Look for top-level experience entries
            experience_items = soup.select('li.pvs-list__paged-list-item')
            
            for item in experience_items:
                # Skip if it's just a spacer or doesn't contain relevant info
                if not item.text.strip() or len(item.text.strip()) < 10:
                    continue
                
                # Check if this is a grouped experience (multiple positions at same company)
                grouped_section = item.select_one('div.pvs-list__container')
                is_grouped = grouped_section is not None
                
                if is_grouped:
                    # Handle grouped experience (multiple roles at same company)
                    company_elem = item.select_one('div.mr1.hoverable-link-text.t-bold span')
                    company_name = company_elem.text.strip() if company_elem else ""
                    
                    company_duration_elem = item.select_one('span.t-14.t-normal span')
                    company_duration = company_duration_elem.text.strip() if company_duration_elem else ""
                    
                    # Process each position within the company
                    position_items = grouped_section.select('li.pvs-list__paged-list-item')
                    for pos_item in position_items:
                        position = {
                            "title": "",
                            "company": company_name,
                            "location": "",
                            "description": "",
                            "date_range": "",
                            "duration": company_duration  # Store total duration at company
                        }
                        
                        # Extract position title
                        pos_title_elem = pos_item.select_one('div.mr1.hoverable-link-text.t-bold span')
                        if pos_title_elem:
                            position["title"] = pos_title_elem.text.strip()
                        
                        # Extract position date range
                        date_elements = pos_item.select('span.t-14.t-normal.t-black--light span')
                        for date_elem in date_elements:
                            text = date_elem.text.strip()
                            if "·" in text and any(month in text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                                position["date_range"] = text
                                break
                        
                        # Extract position location
                        for location_elem in date_elements:
                            text = location_elem.text.strip()
                            if text and "·" not in text and not any(month in text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                                position["location"] = text
                                break
                        
                        # Extract position description
                        desc_elem = pos_item.select_one('div.t-14.t-normal.t-black span')
                        if desc_elem:
                            position["description"] = desc_elem.get_text(separator=' ', strip=True)
                        
                        # Only add if we have a valid title
                        if position["title"]:
                            experiences.append(position)
                else:
                    # Handle single position
                    experience = {
                        "title": "",
                        "company": "",
                        "location": "",
                        "description": "",
                        "date_range": "",
                        "duration": ""
                    }
                    
                    # Extract title
                    title_elem = item.select_one('div.mr1.hoverable-link-text.t-bold span')
                    if title_elem:
                        experience["title"] = title_elem.text.strip()
                    
                    # Extract company name
                    company_elem = item.select_one('span.t-14.t-normal span')
                    if company_elem:
                        experience["company"] = company_elem.text.strip()
                    
                    # Extract date range and location
                    info_elements = item.select('span.t-14.t-normal.t-black--light span')
                    for info_elem in info_elements:
                        text = info_elem.text.strip()
                        if "·" in text and any(month in text for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                            experience["date_range"] = text
                        elif text and not text.startswith("·"):
                            experience["location"] = text
                    
                    # Extract description
                    desc_elem = item.select_one('div.t-14.t-normal.t-black span')
                    if desc_elem:
                        experience["description"] = desc_elem.get_text(separator=' ', strip=True)
                    
                    # Filter out connection entries and only add valid entries
                    if (experience["title"] or experience["company"]) and not (
                        "· 3rd" in experience.get("company", "") or 
                        "· 2nd" in experience.get("company", "") or
                        "· 1st" in experience.get("company", "")):
                        experiences.append(experience)
        
        except Exception as e:
            logger.error(f"Error parsing experience: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Update profile data
        self.profile_data["experiences"] = experiences
        
        return experiences
    def parse_education(self) -> List[Dict[str, Any]]:
        """
        Parse education information with improved selectors.
        
        Returns:
            List of dictionaries containing education entries
        """
        if "education" not in self.html_content:
            logger.warning("Cannot parse education: education HTML not loaded")
            return []
        
        html = self.html_content["education"]
        soup = BeautifulSoup(html, 'html.parser')
        
        education_entries = []
        
        try:
            # Find all education list items
            education_items = soup.select('li.pvs-list__paged-list-item')
            
            for item in education_items:
                # Skip if it's just a spacer or doesn't contain relevant info
                if not item.text.strip() or len(item.text.strip()) < 10:
                    continue
                
                education = {
                    "school": "",
                    "degree": "",
                    "field_of_study": "",
                    "date_range": "",
                    "activities": "",
                    "description": ""
                }
                
                # Extract school name - this is in the bold text
                school_elem = item.select_one('div.mr1.hoverable-link-text.t-bold span')
                if school_elem:
                    education["school"] = school_elem.text.strip()
                
                # Extract degree - this is in the normal t-14 text
                degree_elems = item.select('span.t-14.t-normal span')
                if degree_elems and len(degree_elems) > 0:
                    education["degree"] = degree_elems[0].text.strip()
                
                # Extract date range - look for the caption wrapper
                date_elem = item.select_one('span.pvs-entity__caption-wrapper')
                if date_elem:
                    education["date_range"] = date_elem.text.strip()
                
                # Look for additional information like activities or description
                # These may be in sub-components
                desc_elems = item.select('div.pvs-entity__sub-components li div.t-14.t-normal.t-black span')
                if desc_elems:
                    for desc_elem in desc_elems:
                        text = desc_elem.text.strip()
                        if text:
                            if 'activities' in text.lower() or 'club' in text.lower() or 'society' in text.lower():
                                education["activities"] = text
                            else:
                                education["description"] += text + " "
                    
                    # Trim any extra whitespace
                    education["description"] = education["description"].strip()
                
                # Extract field of study if it's separate from degree
                # Sometimes it appears as "Degree, Field of Study"
                if education["degree"] and "," in education["degree"]:
                    parts = education["degree"].split(",", 1)
                    education["degree"] = parts[0].strip()
                    education["field_of_study"] = parts[1].strip()
                
                # Only add if at least school is available
                if education["school"]:
                    education_entries.append(education)
            
        except Exception as e:
            logger.error(f"Error parsing education: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Update profile data
        self.profile_data["education"] = education_entries
        
        return education_entries
    
    def parse_skills(self) -> List[Dict[str, Any]]:
        """
        Parse skills information.
        
        Returns:
            List of dictionaries containing skills entries
        """
        if "skills" not in self.html_content:
            logger.warning("Cannot parse skills: skills HTML not loaded")
            return []
        
        html = self.html_content["skills"]
        soup = BeautifulSoup(html, 'html.parser')
        
        skills = []
        
        try:
            # Look for skills entries
            skill_sections = soup.select('.pvs-list__item--line-separated, .pv-skill-category-entity, .artdeco-list__item')
            
            for section in skill_sections:
                # Skip if it's just a spacer or doesn't contain relevant info
                if not section.text.strip() or len(section.text.strip()) < 3:
                    continue
                
                skill = {
                    "name": "",
                    "endorsements": 0,
                    "category": ""
                }
                
                # Extract skill name
                name_elem = section.select_one('.t-bold span, .pv-skill-category-entity__name-text')
                if name_elem:
                    skill["name"] = name_elem.text.strip()
                
                # Extract endorsements count
                endorsements_elem = section.select_one('.t-normal.t-black--light span, .pv-skill-category-entity__endorsement-count')
                if endorsements_elem:
                    endorsements_text = endorsements_elem.text.strip()
                    # Extract number from text
                    endorsements_match = re.search(r'(\d+)', endorsements_text)
                    if endorsements_match:
                        skill["endorsements"] = int(endorsements_match.group(1))
                
                # Try to determine skill category
                # Often grouped under headings in the skills section
                category_heading = section.find_previous('h3')
                if category_heading:
                    skill["category"] = category_heading.text.strip()
                
                # Only add if name is available
                if skill["name"]:
                    skills.append(skill)
        
        except Exception as e:
            logger.error(f"Error parsing skills: {str(e)}")
        
        # Update profile data
        self.profile_data["skills"] = skills
        
        return skills
    
    def parse_recommendations(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse recommendations information.
        
        Returns:
            Dictionary with 'received' and 'given' recommendations
        """
        if "recommendations" not in self.html_content:
            logger.warning("Cannot parse recommendations: recommendations HTML not loaded")
            return {"received": [], "given": []}
        
        html = self.html_content["recommendations"]
        soup = BeautifulSoup(html, 'html.parser')
        
        recommendations = {
            "received": [],
            "given": []
        }
        
        try:
            # Find recommendation sections
            received_section = soup.find('section', {'id': 'received-recommendations-section'}) or soup.find('div', {'id': 'recommendation-list'})
            given_section = soup.find('section', {'id': 'given-recommendations-section'})
            
            # Parse received recommendations
            if received_section:
                rec_items = received_section.select('.pvs-list__item--line-separated, .pv-recommendation-entity, .artdeco-list__item')
                
                for item in rec_items:
                    # Skip if it's just a spacer or doesn't contain relevant info
                    if not item.text.strip() or len(item.text.strip()) < 20:
                        continue
                    
                    recommendation = {
                        "recommender_name": "",
                        "recommender_title": "",
                        "relationship": "",
                        "text": ""
                    }
                    
                    # Extract recommender name
                    name_elem = item.select_one('.t-bold span, .pv-recommendation-entity__detail h3')
                    if name_elem:
                        recommendation["recommender_name"] = name_elem.text.strip()
                    
                    # Extract recommender title
                    title_elem = item.select_one('.t-normal span, .pv-recommendation-entity__detail p:nth-of-type(1)')
                    if title_elem:
                        recommendation["recommender_title"] = title_elem.text.strip()
                    
                    # Extract relationship
                    relation_elem = item.select_one('.t-normal span:contains("Working relationship"), .pv-recommendation-entity__relationship')
                    if relation_elem:
                        relation_text = relation_elem.text.strip()
                        relation_match = re.search(r'relationship: (.*)', relation_text)
                        if relation_match:
                            recommendation["relationship"] = relation_match.group(1).strip()
                    
                    # Extract recommendation text
                    text_elem = item.select_one('.t-normal span.visually-hidden, .pv-recommendation-entity__text')
                    if text_elem:
                        recommendation["text"] = text_elem.get_text(separator=' ', strip=True)
                    
                    # Only add if at least name and text are available
                    if recommendation["recommender_name"] and recommendation["text"]:
                        recommendations["received"].append(recommendation)
            
            # Parse given recommendations
            if given_section:
                rec_items = given_section.select('.pvs-list__item--line-separated, .pv-recommendation-entity, .artdeco-list__item')
                
                for item in rec_items:
                    # Skip if it's just a spacer or doesn't contain relevant info
                    if not item.text.strip() or len(item.text.strip()) < 20:
                        continue
                    
                    recommendation = {
                        "recipient_name": "",
                        "recipient_title": "",
                        "relationship": "",
                        "text": ""
                    }
                    
                    # Extract recipient name
                    name_elem = item.select_one('.t-bold span, .pv-recommendation-entity__detail h3')
                    if name_elem:
                        recommendation["recipient_name"] = name_elem.text.strip()
                    
                    # Extract recipient title
                    title_elem = item.select_one('.t-normal span, .pv-recommendation-entity__detail p:nth-of-type(1)')
                    if title_elem:
                        recommendation["recipient_title"] = title_elem.text.strip()
                    
                    # Extract relationship
                    relation_elem = item.select_one('.t-normal span:contains("Working relationship"), .pv-recommendation-entity__relationship')
                    if relation_elem:
                        relation_text = relation_elem.text.strip()
                        relation_match = re.search(r'relationship: (.*)', relation_text)
                        if relation_match:
                            recommendation["relationship"] = relation_match.group(1).strip()
                    
                    # Extract recommendation text
                    text_elem = item.select_one('.t-normal span.visually-hidden, .pv-recommendation-entity__text')
                    if text_elem:
                        recommendation["text"] = text_elem.get_text(separator=' ', strip=True)
                    
                    # Only add if at least name and text are available
                    if recommendation["recipient_name"] and recommendation["text"]:
                        recommendations["given"].append(recommendation)
        
        except Exception as e:
            logger.error(f"Error parsing recommendations: {str(e)}")
        
        # Update profile data
        self.profile_data["recommendations"] = recommendations
        
        return recommendations
    
    def parse_courses(self) -> List[Dict[str, Any]]:
        """
        Parse courses information.
        
        Returns:
            List of dictionaries containing course entries
        """
        if "courses" not in self.html_content:
            logger.warning("Cannot parse courses: courses HTML not loaded")
            return []
        
        html = self.html_content["courses"]
        soup = BeautifulSoup(html, 'html.parser')
        
        courses = []
        
        try:
            # Look for course entries
            course_items = soup.select('.pvs-list__item--line-separated, .pv-accomplishment-entity, .artdeco-list__item')
            
            for item in course_items:
                # Skip if it's just a spacer or doesn't contain relevant info
                if not item.text.strip() or len(item.text.strip()) < 3:
                    continue
                
                course = {
                    "name": "",
                    "number": "",
                    "provider": ""
                }
                
                # Extract course name
                name_elem = item.select_one('.t-bold span, .pv-accomplishment-entity__title')
                if name_elem:
                    course["name"] = name_elem.text.strip()
                
                # Try to extract course number and provider
                # These are often in the same element with different patterns
                details_elem = item.select_one('.t-normal span, .pv-accomplishment-entity__subtitle')
                if details_elem:
                    details_text = details_elem.text.strip()
                    
                    # Try to match patterns like "Course Number: ABC123" or "Provider: Coursera"
                    number_match = re.search(r'course (?:number|id|code):\s*([\w\d-]+)', details_text, re.IGNORECASE)
                    provider_match = re.search(r'provider:\s*([^,]+)', details_text, re.IGNORECASE)
                    
                    if number_match:
                        course["number"] = number_match.group(1).strip()
                    
                    if provider_match:
                        course["provider"] = provider_match.group(1).strip()
                    
                    # If no structured format, assume it's the provider
                    if not number_match and not provider_match and details_text:
                        course["provider"] = details_text
                
                # Only add if name is available
                if course["name"]:
                    courses.append(course)
        
        except Exception as e:
            logger.error(f"Error parsing courses: {str(e)}")
        
        # Update profile data
        self.profile_data["courses"] = courses
        
        return courses
    
    def parse_languages(self) -> List[Dict[str, Any]]:
        """
        Parse languages information.
        
        Returns:
            List of dictionaries containing language entries
        """
        if "languages" not in self.html_content:
            logger.warning("Cannot parse languages: languages HTML not loaded")
            return []
        
        html = self.html_content["languages"]
        soup = BeautifulSoup(html, 'html.parser')
        
        languages = []
        
        try:
            # Look for language entries
            language_items = soup.select('.pvs-list__item--line-separated, .pv-accomplishment-entity, .artdeco-list__item')
            
            for item in language_items:
                # Skip if it's just a spacer or doesn't contain relevant info
                if not item.text.strip() or len(item.text.strip()) < 3:
                    continue
                
                language = {
                    "language": "",
                    "proficiency": ""
                }
                
                # Extract language name
                name_elem = item.select_one('.t-bold span, .pv-accomplishment-entity__title')
                if name_elem:
                    language["language"] = name_elem.text.strip()
                
                # Extract proficiency level
                proficiency_elem = item.select_one('.t-normal span, .pv-accomplishment-entity__subtitle')
                if proficiency_elem:
                    language["proficiency"] = proficiency_elem.text.strip()
                
                # Only add if language name is available
                if language["language"]:
                    languages.append(language)
        
        except Exception as e:
            logger.error(f"Error parsing languages: {str(e)}")
        
        # Update profile data
        self.profile_data["languages"] = languages
        
        return languages
    
    def parse_interests(self) -> List[Dict[str, Any]]:
        """
        Parse interests information.
        
        Returns:
            List of dictionaries containing interest entries
        """
        if "interests" not in self.html_content:
            logger.warning("Cannot parse interests: interests HTML not loaded")
            return []
        
        html = self.html_content["interests"]
        soup = BeautifulSoup(html, 'html.parser')
        
        interests = []
        
        try:
            # Look for interest entries
            interest_items = soup.select('.pvs-list__item--line-separated, .pv-interest-entity, .artdeco-list__item')
            
            for item in interest_items:
                # Skip if it's just a spacer or doesn't contain relevant info
                if not item.text.strip() or len(item.text.strip()) < 3:
                    continue
                
                interest = {
                    "name": "",
                    "followers": ""
                }
                
                # Extract interest name
                name_elem = item.select_one('.t-bold span, .pv-entity__summary-title-text')
                if name_elem:
                    interest["name"] = name_elem.text.strip()
                
                # Extract followers count
                followers_elem = item.select_one('.t-normal span:contains("followers"), .pv-entity__follower-count')
                if followers_elem:
                    followers_text = followers_elem.text.strip()
                    # Extract number from text
                    followers_match = re.search(r'([\d,]+)\s+followers', followers_text)
                    if followers_match:
                        interest["followers"] = followers_match.group(1).replace(',', '')
                
                # Only add if name is available
                if interest["name"]:
                    interests.append(interest)
        
        except Exception as e:
            logger.error(f"Error parsing interests: {str(e)}")
        
        # Update profile data
        self.profile_data["interests"] = interests
        
        return interests
    
    def save_parsed_data(self, output_path: Optional[str] = None) -> str:
        """
        Save parsed profile data to a JSON file.
        
        Args:
            output_path: Path to save the output JSON file (if None, saves to profile directory)
            
        Returns:
            Path to the saved JSON file
        """
        if not output_path:
            # Generate filename based on profile name
            profile_name = self.metadata.get("profile_name", "unknown_profile")
            safe_name = re.sub(r'[\\/*?:"<>|]', "_", profile_name)
            output_path = os.path.join(self.profile_dir, f"{safe_name}_parsed_data.json")
        
        try:
            # Add parsing timestamp
            result = {
                "parsing_date": datetime.now().isoformat(),
                "metadata": self.metadata,
                **self.profile_data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Saved parsed data to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving parsed data: {str(e)}")
            return ""