"""
Base Scraper class for Dutch Subsidy Finder
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from .config import Config


class BaseScraper:
    """Base class for all scrapers with common functionality."""
    
    def __init__(self, source_config: Dict):
        self.config = source_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Override this method in subclasses."""
        raise NotImplementedError
        
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        try:
            await asyncio.sleep(Config.REQUEST_DELAY)
            
            # Try with SSL verification first, then without if it fails
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return BeautifulSoup(html, 'html.parser')
                    else:
                        self.logger.warning(f"HTTP {response.status} for {url}")
                        return None
            except Exception as ssl_error:
                if "ssl" in str(ssl_error).lower() or "certificate" in str(ssl_error).lower():
                    self.logger.info(f"SSL error for {url}, trying without SSL verification...")
                    # Create a new session without SSL verification for this request
                    connector = aiohttp.TCPConnector(verify_ssl=False)
                    async with aiohttp.ClientSession(connector=connector, headers=session.headers) as no_ssl_session:
                        async with no_ssl_session.get(url) as response:
                            if response.status == 200:
                                html = await response.text()
                                return BeautifulSoup(html, 'html.parser')
                            else:
                                self.logger.warning(f"HTTP {response.status} for {url} (no SSL)")
                                return None
                else:
                    raise ssl_error
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def extract_text(self, element, default: str = "") -> str:
        """Safely extract text from BeautifulSoup element."""
        if element:
            return element.get_text(strip=True)
        return default
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common unwanted characters
        text = re.sub(r'[^\w\s\-.,;:()\[\]€$]', '', text)
        
        return text
    
    def extract_amount(self, text: str) -> str:
        """Extract funding amount from text."""
        if not text:
            return ""
        
        # Look for common amount patterns
        amount_patterns = [
            r'€\s*[\d,.]+ (?:miljoen|million)',
            r'€\s*[\d,.]+',
            r'[\d,.]+ (?:miljoen|million) euro',
            r'tot (?:€\s*)?[\d,.]+ (?:miljoen|million)?',
            r'maximaal (?:€\s*)?[\d,.]+ (?:miljoen|million)?'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    def extract_deadline(self, text: str) -> str:
        """Extract deadline from text."""
        if not text:
            return ""
        
        # Look for date patterns
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{1,2} (?:januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december) \d{4}',
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2},? \d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    def create_subsidy_dict(self, **kwargs) -> Dict:
        """Create standardized subsidy dictionary."""
        return {
            'name': kwargs.get('name', ''),
            'funding_organization': kwargs.get('funding_organization', ''),
            'amount': kwargs.get('amount', ''),
            'deadline': kwargs.get('deadline', ''),
            'status': kwargs.get('status', ''),
            'eligibility': kwargs.get('eligibility', ''),
            'research_areas': kwargs.get('research_areas', ''),
            'description': kwargs.get('description', ''),
            'application_process': kwargs.get('application_process', ''),
            'contact_info': kwargs.get('contact_info', ''),
            'url': kwargs.get('url', ''),
            'raw_text': kwargs.get('raw_text', '')
        }
