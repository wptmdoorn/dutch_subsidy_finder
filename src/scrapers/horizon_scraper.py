"""
Horizon Europe Scraper (Dutch participation focus)
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from ..config import Config
from ..base_scraper import BaseScraper


class HorizonScraper(BaseScraper):
    """Scraper for Horizon Europe funding opportunities."""
    
    def __init__(self):
        super().__init__(Config.FUNDING_SOURCES['horizon_europe'])
        self.logger = logging.getLogger(__name__)
        
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Scrape Horizon Europe funding opportunities."""
        subsidies = []
        
        # Note: Horizon Europe portal is complex and may require API access
        # This is a simplified scraper that attempts to get basic information
        
        for url in self.config['search_urls']:
            self.logger.info(f"Scraping Horizon Europe URL: {url}")
            soup = await self.fetch_page(session, url)
            
            if soup:
                page_subsidies = await self._parse_horizon_page(session, soup, url)
                subsidies.extend(page_subsidies)
        
        # Add some known Horizon Europe opportunities for clinical chemistry & AI
        subsidies.extend(self._get_known_horizon_opportunities())
        
        return subsidies
    
    async def _parse_horizon_page(self, session: aiohttp.ClientSession, 
                                soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Parse Horizon Europe page for funding opportunities."""
        subsidies = []
        
        # Look for opportunity listings
        opportunity_selectors = [
            '.opportunity-item',
            '.call-item',
            '.topic-item',
            '.card',
            'article'
        ]
        
        opportunities_found = []
        for selector in opportunity_selectors:
            opportunities = soup.select(selector)
            if opportunities:
                opportunities_found.extend(opportunities)
                break
        
        # Process each found opportunity
        for opportunity in opportunities_found[:15]:  # Limit to prevent overload
            try:
                subsidy = await self._parse_horizon_opportunity(session, opportunity, base_url)
                if subsidy and subsidy['name']:
                    subsidies.append(subsidy)
            except Exception as e:
                self.logger.warning(f"Failed to parse Horizon opportunity: {e}")
        
        return subsidies
    
    async def _parse_horizon_opportunity(self, session: aiohttp.ClientSession, 
                                       element, base_url: str) -> Dict:
        """Parse individual Horizon Europe opportunity."""
        
        # Extract title
        title_elem = (element.find(['h1', 'h2', 'h3', 'h4']) or 
                     element.find('a') or element)
        title = self.clean_text(self.extract_text(title_elem))
        
        # Get detail URL
        link_elem = element.find('a', href=True) or element
        if hasattr(link_elem, 'get') and link_elem.get('href'):
            detail_url = urljoin(base_url, link_elem['href'])
        else:
            detail_url = base_url
        
        # Extract basic information
        full_text = self.extract_text(element)
        description = self.clean_text(full_text)
        deadline = self.extract_deadline(full_text)
        amount = self.extract_amount(full_text)
        
        return self.create_subsidy_dict(
            name=title,
            funding_organization=self.config['name'],
            amount=amount,
            deadline=deadline,
            status='Open',
            eligibility='EU organizations, including Dutch institutions',
            research_areas=self._extract_eu_research_areas(full_text),
            description=description,
            application_process='Apply through EU Funding & Tenders Portal',
            contact_info='',
            url=detail_url,
            raw_text=full_text
        )
    
    def _get_known_horizon_opportunities(self) -> List[Dict]:
        """Get known Horizon Europe opportunities relevant to clinical chemistry & AI."""
        known_opportunities = [
            {
                'name': 'Horizon Europe - Health Cluster',
                'funding_organization': self.config['name'],
                'amount': '€8.2 billion (2021-2027)',
                'deadline': 'Various deadlines throughout the year',
                'status': 'Open',
                'eligibility': 'EU organizations, including Dutch research institutions',
                'research_areas': 'Health, Medical Technology, Clinical Research',
                'description': 'Funding for health research and innovation, including digital health, medical technologies, and clinical studies.',
                'application_process': 'Apply through EU Funding & Tenders Portal',
                'contact_info': 'Contact Dutch National Contact Points',
                'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search',
                'raw_text': 'Horizon Europe Health Cluster funding opportunities'
            },
            {
                'name': 'Horizon Europe - Digital, Industry and Space',
                'funding_organization': self.config['name'],
                'amount': '€15.3 billion (2021-2027)',
                'deadline': 'Multiple calls per year',
                'status': 'Open',
                'eligibility': 'EU organizations, including Dutch companies and research institutes',
                'research_areas': 'AI, Digital Health, Medical Devices, Data Science',
                'description': 'Funding for digital technologies including AI applications in healthcare, medical device innovation, and digital transformation.',
                'application_process': 'Submit proposals through EU portal',
                'contact_info': 'Dutch Enterprise Agency (RVO) - EU desk',
                'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search',
                'raw_text': 'Horizon Europe Digital Industry Space cluster'
            },
            {
                'name': 'ERC (European Research Council) Grants',
                'funding_organization': self.config['name'],
                'amount': '€1.5-2.5 million per grant',
                'deadline': 'Annual calls (typically October)',
                'status': 'Open',
                'eligibility': 'Excellent researchers at any career stage',
                'research_areas': 'All fields including Clinical Chemistry, AI, Medical Research',
                'description': 'Prestigious grants for frontier research, including interdisciplinary projects combining clinical chemistry with AI.',
                'application_process': 'Apply through ERC portal',
                'contact_info': 'NWO (Dutch contact point for ERC)',
                'url': 'https://erc.europa.eu/',
                'raw_text': 'European Research Council grants for frontier research'
            }
        ]
        
        return known_opportunities
    
    def _extract_eu_research_areas(self, text: str) -> str:
        """Extract EU research areas from text."""
        research_areas = []
        text_lower = text.lower()
        
        # EU research priority areas
        eu_keywords = [
            'health', 'digital', 'green deal', 'climate',
            'artificial intelligence', 'ai', 'data',
            'medical', 'clinical', 'innovation',
            'technology', 'research', 'science'
        ]
        
        for keyword in eu_keywords:
            if keyword in text_lower:
                research_areas.append(keyword.title())
        
        return ', '.join(list(set(research_areas))[:5])
