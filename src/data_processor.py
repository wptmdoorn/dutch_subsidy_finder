"""
Data Processor for Dutch Subsidy Finder
Handles filtering, relevance scoring, and data cleaning
"""

import logging
import re
from datetime import datetime
from typing import Dict, List

from .config import Config


class DataProcessor:
    """Processes and filters scraped subsidy data."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_subsidies(self, raw_subsidies: List[Dict]) -> List[Dict]:
        """Process and filter subsidies based on relevance."""
        processed_subsidies = []
        
        self.logger.info(f"Processing {len(raw_subsidies)} raw subsidies...")
        
        for subsidy in raw_subsidies:
            try:
                # Clean and standardize the subsidy data
                cleaned_subsidy = self._clean_subsidy_data(subsidy)
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(cleaned_subsidy)
                cleaned_subsidy['relevance_score'] = relevance_score
                
                # Add matched keywords
                matched_keywords = self._get_matched_keywords(cleaned_subsidy)
                cleaned_subsidy['keywords_matched'] = ', '.join(matched_keywords)
                
                # Only include subsidies that meet minimum relevance threshold
                if relevance_score >= Config.MIN_RELEVANCE_SCORE:
                    processed_subsidies.append(cleaned_subsidy)
                    
            except Exception as e:
                self.logger.warning(f"Failed to process subsidy: {e}")
        
        # Sort by relevance score (highest first)
        processed_subsidies.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        self.logger.info(f"Processed {len(processed_subsidies)} relevant subsidies")
        return processed_subsidies
    
    def _clean_subsidy_data(self, subsidy: Dict) -> Dict:
        """Clean and standardize subsidy data."""
        cleaned = {}
        
        # Clean text fields
        text_fields = ['name', 'description', 'eligibility', 'research_areas', 
                      'application_process', 'contact_info']
        
        for field in text_fields:
            value = subsidy.get(field, '')
            cleaned[field] = self._clean_text(value)
        
        # Clean and standardize other fields
        cleaned['funding_organization'] = subsidy.get('funding_organization', '')
        cleaned['amount'] = self._clean_amount(subsidy.get('amount', ''))
        cleaned['deadline'] = self._clean_deadline(subsidy.get('deadline', ''))
        cleaned['status'] = self._clean_status(subsidy.get('status', ''))
        cleaned['url'] = subsidy.get('url', '')
        cleaned['source'] = subsidy.get('source', '')
        cleaned['date_scraped'] = subsidy.get('date_scraped', datetime.now().isoformat())
        cleaned['raw_text'] = subsidy.get('raw_text', '')
        
        return cleaned
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove unwanted characters but keep essential punctuation
        text = re.sub(r'[^\w\s\-.,;:()\[\]€$%&/]', '', text)
        
        # Limit length to prevent extremely long descriptions
        if len(text) > 1000:
            text = text[:997] + "..."
        
        return text
    
    def _clean_amount(self, amount: str) -> str:
        """Clean and standardize funding amounts."""
        if not amount:
            return ""
        
        # Remove extra whitespace and normalize
        amount = re.sub(r'\s+', ' ', amount.strip())
        
        # Standardize common patterns
        amount = re.sub(r'euro?s?', '€', amount, flags=re.IGNORECASE)
        amount = re.sub(r'miljoen', 'million', amount, flags=re.IGNORECASE)
        
        return amount
    
    def _clean_deadline(self, deadline: str) -> str:
        """Clean and standardize deadlines."""
        if not deadline:
            return ""
        
        # Try to parse and standardize date format
        deadline = deadline.strip()
        
        # Convert Dutch month names to English
        dutch_months = {
            'januari': 'january', 'februari': 'february', 'maart': 'march',
            'april': 'april', 'mei': 'may', 'juni': 'june',
            'juli': 'july', 'augustus': 'august', 'september': 'september',
            'oktober': 'october', 'november': 'november', 'december': 'december'
        }
        
        for dutch, english in dutch_months.items():
            deadline = re.sub(dutch, english, deadline, flags=re.IGNORECASE)
        
        return deadline
    
    def _clean_status(self, status: str) -> str:
        """Clean and standardize status."""
        if not status:
            return "Unknown"
        
        status = status.strip().title()
        
        # Standardize common status values
        if any(word in status.lower() for word in ['open', 'geopend', 'available']):
            return 'Open'
        elif any(word in status.lower() for word in ['closed', 'gesloten', 'expired']):
            return 'Closed'
        else:
            return status
    
    def _calculate_relevance_score(self, subsidy: Dict) -> float:
        """Calculate relevance score based on keyword matches."""
        score = 0.0
        
        # Get text content for analysis
        title = subsidy.get('name', '').lower()
        description = subsidy.get('description', '').lower()
        research_areas = subsidy.get('research_areas', '').lower()
        eligibility = subsidy.get('eligibility', '').lower()
        raw_text = subsidy.get('raw_text', '').lower()
        
        # Count keyword matches in different sections
        title_matches = 0
        description_matches = 0
        research_matches = 0
        eligibility_matches = 0
        
        for keyword in Config.RESEARCH_KEYWORDS:
            keyword_lower = keyword.lower()
            
            if keyword_lower in title:
                title_matches += 1
            if keyword_lower in description:
                description_matches += 1
            if keyword_lower in research_areas:
                research_matches += 1
            if keyword_lower in eligibility:
                eligibility_matches += 1
        
        # Calculate weighted score
        score += title_matches * Config.SCORING_WEIGHTS['title_match']
        score += description_matches * Config.SCORING_WEIGHTS['description_match']
        score += research_matches * Config.SCORING_WEIGHTS['keywords_match']
        score += eligibility_matches * Config.SCORING_WEIGHTS['eligibility_match']
        
        # Bonus for upcoming deadlines
        deadline = subsidy.get('deadline', '')
        if deadline and self._has_upcoming_deadline(deadline):
            score += Config.SCORING_WEIGHTS['deadline_bonus']
        
        # Bonus for health/medical focus (relevant to clinical chemistry)
        health_keywords = ['health', 'medical', 'clinical', 'healthcare', 'gezondheid', 'medisch', 'klinisch']
        if any(keyword in raw_text for keyword in health_keywords):
            score += 1.0
        
        # Bonus for AI/technology focus
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'technology', 'digital']
        if any(keyword in raw_text for keyword in ai_keywords):
            score += 1.0
        
        return round(score, 2)
    
    def _get_matched_keywords(self, subsidy: Dict) -> List[str]:
        """Get list of matched keywords for the subsidy."""
        matched = []
        
        # Combine all text content
        all_text = ' '.join([
            subsidy.get('name', ''),
            subsidy.get('description', ''),
            subsidy.get('research_areas', ''),
            subsidy.get('eligibility', ''),
            subsidy.get('raw_text', '')
        ]).lower()
        
        # Find matching keywords
        for keyword in Config.RESEARCH_KEYWORDS:
            if keyword.lower() in all_text:
                matched.append(keyword)
        
        return matched[:10]  # Limit to top 10 matches
    
    def _has_upcoming_deadline(self, deadline: str) -> bool:
        """Check if deadline is within the next 90 days."""
        if not deadline:
            return False
        
        try:
            # Try to parse various date formats
            date_patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, deadline)
                if match:
                    try:
                        if len(match.group(1)) == 4:  # YYYY-MM-DD
                            year, month, day = match.groups()
                        else:  # DD-MM-YYYY or DD/MM/YYYY
                            day, month, year = match.groups()
                        
                        deadline_date = datetime(int(year), int(month), int(day))
                        days_until = (deadline_date - datetime.now()).days
                        
                        return 0 <= days_until <= 90
                    except ValueError:
                        continue
            
            return False
            
        except Exception:
            return False
