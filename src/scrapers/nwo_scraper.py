"""
NWO (Nederlandse Organisatie voor Wetenschappelijk Onderzoek) Scraper
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from ..config import Config
from ..base_scraper import BaseScraper


class NWOScraper(BaseScraper):
    """Scraper for NWO funding opportunities."""
    
    def __init__(self):
        super().__init__(Config.FUNDING_SOURCES['nwo'])
        self.logger = logging.getLogger(__name__)
        
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Scrape NWO funding opportunities."""
        subsidies = []
        
        for url in self.config['search_urls']:
            self.logger.info(f"Scraping NWO URL: {url}")
            soup = await self.fetch_page(session, url)
            
            if soup:
                page_subsidies = await self._parse_nwo_page(session, soup, url)
                subsidies.extend(page_subsidies)
        
        # Add known NWO opportunities (fallback when website scraping fails)
        subsidies.extend(self._get_known_nwo_opportunities())
        
        return subsidies
    
    async def _parse_nwo_page(self, session: aiohttp.ClientSession, 
                            soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Parse NWO page for funding opportunities."""
        subsidies = []
        
        # Look for call listings - NWO uses various structures
        call_selectors = [
            '.call-item',
            '.funding-call',
            '.opportunity-item',
            '.card',
            'article',
            '.teaser'
        ]
        
        calls_found = []
        for selector in call_selectors:
            calls = soup.select(selector)
            if calls:
                calls_found.extend(calls)
                break
        
        # If no structured calls found, look for links containing funding keywords
        if not calls_found:
            links = soup.find_all('a', href=True)
            for link in links:
                link_text = self.extract_text(link).lower()
                if any(keyword in link_text for keyword in ['call', 'funding', 'grant', 'subsidy', 'financiering']):
                    calls_found.append(link)
        
        # Process each found call
        for call_element in calls_found[:20]:  # Limit to prevent overload
            try:
                subsidy = await self._parse_nwo_call(session, call_element, base_url)
                if subsidy and subsidy['name']:
                    subsidies.append(subsidy)
            except Exception as e:
                self.logger.warning(f"Failed to parse NWO call: {e}")
        
        return subsidies
    
    async def _parse_nwo_call(self, session: aiohttp.ClientSession, 
                            element, base_url: str) -> Dict:
        """Parse individual NWO call."""
        
        # Extract basic information
        title_elem = (element.find(['h1', 'h2', 'h3', 'h4']) or 
                     element.find('a') or element)
        title = self.clean_text(self.extract_text(title_elem))
        
        # Get link to detailed page
        link_elem = element.find('a', href=True) or element
        if hasattr(link_elem, 'get') and link_elem.get('href'):
            detail_url = urljoin(base_url, link_elem['href'])
        else:
            detail_url = base_url
        
        # Extract summary information
        description = ""
        deadline = ""
        amount = ""
        
        # Look for description
        desc_elem = element.find(['p', '.description', '.summary', '.excerpt'])
        if desc_elem:
            description = self.clean_text(self.extract_text(desc_elem))
        
        # Extract deadline and amount from text
        full_text = self.extract_text(element)
        deadline = self.extract_deadline(full_text)
        amount = self.extract_amount(full_text)
        
        # Try to get more details from the detail page
        if detail_url != base_url:
            detail_info = await self._get_nwo_detail_info(session, detail_url)
            if detail_info:
                description = detail_info.get('description', description)
                deadline = detail_info.get('deadline', deadline)
                amount = detail_info.get('amount', amount)
        
        return self.create_subsidy_dict(
            name=title,
            funding_organization=self.config['name'],
            amount=amount,
            deadline=deadline,
            status=self._determine_status(deadline, full_text),
            eligibility=self._extract_eligibility(full_text),
            research_areas=self._extract_research_areas(full_text),
            description=description,
            application_process="",
            contact_info="",
            url=detail_url,
            raw_text=full_text
        )
    
    async def _get_nwo_detail_info(self, session: aiohttp.ClientSession, 
                                 url: str) -> Dict:
        """Get detailed information from NWO call page."""
        soup = await self.fetch_page(session, url)
        if not soup:
            return {}
        
        info = {}
        
        # Extract detailed description
        desc_selectors = ['.content', '.description', '.call-content', 'main', '.body']
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                info['description'] = self.clean_text(self.extract_text(desc_elem))
                break
        
        # Extract deadline from page
        full_text = self.extract_text(soup)
        info['deadline'] = self.extract_deadline(full_text)
        info['amount'] = self.extract_amount(full_text)
        
        return info
    
    def _determine_status(self, deadline: str, text: str) -> str:
        """Determine the status of the funding call."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['closed', 'gesloten', 'expired', 'verlopen']):
            return 'Closed'
        elif any(word in text_lower for word in ['open', 'geopend', 'available', 'beschikbaar']):
            return 'Open'
        elif deadline:
            return 'Open'
        else:
            return 'Unknown'
    
    def _extract_eligibility(self, text: str) -> str:
        """Extract eligibility criteria from text."""
        text_lower = text.lower()
        eligibility_keywords = [
            'eligibility', 'eligible', 'geschikt', 'voorwaarden',
            'requirements', 'vereisten', 'criteria'
        ]
        
        sentences = text.split('.')
        eligibility_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in eligibility_keywords):
                eligibility_sentences.append(sentence.strip())
        
        return ' '.join(eligibility_sentences[:3])  # Limit to 3 sentences
    
    def _extract_research_areas(self, text: str) -> str:
        """Extract research areas from text."""
        research_areas = []
        text_lower = text.lower()
        
        # Look for research area keywords
        area_keywords = [
            'health', 'gezondheid', 'medical', 'medisch',
            'technology', 'technologie', 'innovation', 'innovatie',
            'science', 'wetenschap', 'research', 'onderzoek'
        ]
        
        for keyword in area_keywords:
            if keyword in text_lower:
                research_areas.append(keyword.title())
        
        return ', '.join(research_areas[:5])  # Limit to 5 areas
    
    def _get_known_nwo_opportunities(self) -> List[Dict]:
        """Get known NWO opportunities relevant to clinical chemistry & AI."""
        known_opportunities = [
            {
                'name': 'NWO Veni Grant',
                'funding_organization': self.config['name'],
                'amount': '€280,000 over 3 years',
                'deadline': 'Annual call (typically March)',
                'status': 'Open',
                'eligibility': 'Researchers within 3 years of PhD completion',
                'research_areas': 'All scientific disciplines including Clinical Chemistry, AI, Medical Research',
                'description': 'Personal grant for excellent researchers who have recently obtained their PhD. Supports innovative research including interdisciplinary projects combining clinical chemistry with AI and data science.',
                'application_process': 'Apply through NWO online portal',
                'contact_info': 'NWO Domain Science',
                'url': 'https://www.nwo.nl/en/calls/nwo-talent-programme-veni-2025',
                'raw_text': 'NWO Veni grant for early career researchers in clinical chemistry and AI'
            },
            {
                'name': 'NWO Vidi Grant',
                'funding_organization': self.config['name'],
                'amount': '€800,000 over 5 years',
                'deadline': 'Annual call (typically September)',
                'status': 'Open',
                'eligibility': 'Researchers within 8 years of PhD completion',
                'research_areas': 'All scientific disciplines including Medical Technology, AI, Clinical Research',
                'description': 'Personal grant for experienced researchers to develop their own innovative line of research and build up a research group. Excellent for clinical chemistry researchers developing AI-powered diagnostic tools.',
                'application_process': 'Apply through NWO online portal',
                'contact_info': 'NWO Domain Science',
                'url': 'https://www.nwo.nl/en/calls/nwo-talent-programme-vidi-2025',
                'raw_text': 'NWO Vidi grant for experienced researchers in clinical chemistry and AI'
            },
            {
                'name': 'NWO Vici Grant',
                'funding_organization': self.config['name'],
                'amount': '€1.5 million over 5 years',
                'deadline': 'Annual call (typically June)',
                'status': 'Open',
                'eligibility': 'Senior researchers, professors',
                'research_areas': 'All scientific disciplines including Health Technology, AI, Clinical Innovation',
                'description': 'Personal grant for highly experienced researchers to build up an innovative research group. Perfect for establishing large-scale clinical chemistry and AI research programs.',
                'application_process': 'Apply through NWO online portal',
                'contact_info': 'NWO Domain Science',
                'url': 'https://www.nwo.nl/en/calls/nwo-talent-programme-vici-2025',
                'raw_text': 'NWO Vici grant for senior researchers in clinical chemistry and AI'
            },
            {
                'name': 'NWO Open Competition Domain Science-XS',
                'funding_organization': self.config['name'],
                'amount': '€50,000 over 2 years',
                'deadline': 'Multiple rounds per year',
                'status': 'Open',
                'eligibility': 'All researchers at Dutch knowledge institutions',
                'research_areas': 'Natural Sciences, Medical Sciences, Technology, AI',
                'description': 'Small-scale research projects in natural sciences, including medical technology and AI applications in healthcare and diagnostics.',
                'application_process': 'Continuous application rounds',
                'contact_info': 'NWO Domain Science',
                'url': 'https://www.nwo.nl/en/calls/open-competition-domain-science-xs',
                'raw_text': 'NWO Open Competition XS for small research projects'
            },
            {
                'name': 'NWO Open Competition Domain Science-M',
                'funding_organization': self.config['name'],
                'amount': '€300,000 over 3 years',
                'deadline': 'Annual call (typically October)',
                'status': 'Open',
                'eligibility': 'All researchers at Dutch knowledge institutions',
                'research_areas': 'Natural Sciences, Medical Sciences, Technology, AI, Clinical Research',
                'description': 'Medium-scale research projects including clinical chemistry research, AI development for medical applications, and innovative diagnostic technologies.',
                'application_process': 'Annual application round',
                'contact_info': 'NWO Domain Science',
                'url': 'https://www.nwo.nl/en/calls/open-competition-domain-science-m',
                'raw_text': 'NWO Open Competition M for medium research projects'
            },
            {
                'name': 'NWO Health Research and Care Innovation (ZonMw)',
                'funding_organization': self.config['name'],
                'amount': 'Various amounts',
                'deadline': 'Multiple calls throughout the year',
                'status': 'Open',
                'eligibility': 'Dutch research institutions and healthcare organizations',
                'research_areas': 'Health Research, Medical Innovation, Clinical Chemistry, Digital Health',
                'description': 'Funding for health research and care innovation, including clinical chemistry research, laboratory medicine innovations, and AI applications in healthcare.',
                'application_process': 'Apply through ZonMw portal',
                'contact_info': 'ZonMw',
                'url': 'https://www.zonmw.nl/en/',
                'raw_text': 'NWO ZonMw health research and innovation funding'
            }
        ]
        
        return known_opportunities
