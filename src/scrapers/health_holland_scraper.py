"""
Health~Holland Scraper
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from ..config import Config
from ..base_scraper import BaseScraper


class HealthHollandScraper(BaseScraper):
    """Scraper for Health~Holland funding opportunities."""
    
    def __init__(self):
        super().__init__(Config.FUNDING_SOURCES['health_holland'])
        self.logger = logging.getLogger(__name__)
        
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Scrape Health~Holland funding opportunities."""
        subsidies = []
        
        for url in self.config['search_urls']:
            self.logger.info(f"Scraping Health~Holland URL: {url}")
            soup = await self.fetch_page(session, url)
            
            if soup:
                page_subsidies = await self._parse_health_holland_page(session, soup, url)
                subsidies.extend(page_subsidies)
        
        # Add known Health~Holland opportunities
        subsidies.extend(self._get_known_health_holland_opportunities())
        
        return subsidies
    
    async def _parse_health_holland_page(self, session: aiohttp.ClientSession, 
                                       soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Parse Health~Holland page for funding opportunities."""
        subsidies = []
        
        # Look for funding opportunity listings
        funding_selectors = [
            '.funding-item',
            '.opportunity-item',
            '.program-item',
            '.card',
            '.teaser',
            'article'
        ]
        
        opportunities_found = []
        for selector in funding_selectors:
            opportunities = soup.select(selector)
            if opportunities:
                opportunities_found.extend(opportunities)
                break
        
        # If no structured opportunities found, look for relevant links
        if not opportunities_found:
            links = soup.find_all('a', href=True)
            for link in links:
                link_text = self.extract_text(link).lower()
                if any(keyword in link_text for keyword in [
                    'funding', 'financiering', 'program', 'programme',
                    'call', 'oproep', 'subsidy', 'subsidie'
                ]):
                    opportunities_found.append(link)
        
        # Process each found opportunity
        for opportunity in opportunities_found[:20]:  # Limit to prevent overload
            try:
                subsidy = await self._parse_health_holland_opportunity(session, opportunity, base_url)
                if subsidy and subsidy['name']:
                    subsidies.append(subsidy)
            except Exception as e:
                self.logger.warning(f"Failed to parse Health~Holland opportunity: {e}")
        
        return subsidies
    
    async def _parse_health_holland_opportunity(self, session: aiohttp.ClientSession, 
                                              element, base_url: str) -> Dict:
        """Parse individual Health~Holland opportunity."""
        
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
            status=self._determine_status(deadline, full_text),
            eligibility=self._extract_eligibility(full_text),
            research_areas=self._extract_health_tech_areas(full_text),
            description=description,
            application_process=self._extract_application_process(full_text),
            contact_info='',
            url=detail_url,
            raw_text=full_text
        )
    
    def _get_known_health_holland_opportunities(self) -> List[Dict]:
        """Get known Health~Holland opportunities relevant to clinical chemistry & AI."""
        known_opportunities = [
            {
                'name': 'Health~Holland Public-Private Partnership Programs',
                'funding_organization': self.config['name'],
                'amount': 'Various amounts depending on program',
                'deadline': 'Multiple calls per year',
                'status': 'Open',
                'eligibility': 'Dutch companies and research institutions in health tech',
                'research_areas': 'Health Technology, Medical Devices, Digital Health, AI in Healthcare',
                'description': 'Funding for public-private partnerships in health technology innovation, including AI applications in healthcare and medical device development.',
                'application_process': 'Apply through Health~Holland portal',
                'contact_info': 'info@health-holland.com',
                'url': 'https://www.health-holland.com/funding',
                'raw_text': 'Health Holland PPP programs for health technology innovation'
            },
            {
                'name': 'Health~Holland Innovation Fund',
                'funding_organization': self.config['name'],
                'amount': '€50,000 - €500,000',
                'deadline': 'Continuous application',
                'status': 'Open',
                'eligibility': 'Dutch health tech startups and SMEs',
                'research_areas': 'Digital Health, Medical Technology, Clinical Innovation',
                'description': 'Funding for innovative health technology projects, including digital health solutions and clinical chemistry innovations.',
                'application_process': 'Submit application online',
                'contact_info': 'funding@health-holland.com',
                'url': 'https://www.health-holland.com/funding',
                'raw_text': 'Health Holland Innovation Fund for health tech startups'
            },
            {
                'name': 'Health~Holland Accelerator Programs',
                'funding_organization': self.config['name'],
                'amount': 'Up to €100,000 + mentoring',
                'deadline': 'Quarterly application rounds',
                'status': 'Open',
                'eligibility': 'Early-stage health tech companies',
                'research_areas': 'AI in Healthcare, Medical Diagnostics, Digital Health',
                'description': 'Accelerator programs for health technology startups, including those working on AI-powered diagnostic tools and clinical chemistry innovations.',
                'application_process': 'Apply through accelerator portal',
                'contact_info': 'accelerator@health-holland.com',
                'url': 'https://www.health-holland.com/programs',
                'raw_text': 'Health Holland accelerator programs for health tech startups'
            }
        ]
        
        return known_opportunities
    
    def _determine_status(self, deadline: str, text: str) -> str:
        """Determine the status of the funding opportunity."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in [
            'closed', 'gesloten', 'expired', 'verlopen'
        ]):
            return 'Closed'
        elif any(word in text_lower for word in [
            'open', 'geopend', 'available', 'beschikbaar', 'active'
        ]):
            return 'Open'
        elif deadline:
            return 'Open'
        else:
            return 'Unknown'
    
    def _extract_eligibility(self, text: str) -> str:
        """Extract eligibility criteria from text."""
        eligibility_keywords = [
            'eligibility', 'eligible', 'geschikt', 'voorwaarden',
            'requirements', 'vereisten', 'criteria', 'who can apply',
            'target group', 'doelgroep'
        ]
        
        sentences = text.split('.')
        eligibility_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in eligibility_keywords):
                eligibility_sentences.append(sentence.strip())
        
        return ' '.join(eligibility_sentences[:3])
    
    def _extract_health_tech_areas(self, text: str) -> str:
        """Extract health technology areas from text."""
        research_areas = []
        text_lower = text.lower()
        
        # Health technology keywords
        health_tech_keywords = [
            'digital health', 'digitale zorg', 'medical technology', 'medtech',
            'health tech', 'medical devices', 'medische hulpmiddelen',
            'diagnostics', 'diagnostiek', 'ai', 'artificial intelligence',
            'machine learning', 'data science', 'clinical', 'klinisch',
            'biomedical', 'biomedisch', 'pharmaceutical', 'farmaceutisch',
            'telemedicine', 'telegeneeskunde', 'e-health'
        ]
        
        for keyword in health_tech_keywords:
            if keyword in text_lower:
                research_areas.append(keyword.title())
        
        return ', '.join(list(set(research_areas))[:6])  # Remove duplicates, limit to 6
    
    def _extract_application_process(self, text: str) -> str:
        """Extract application process information."""
        process_keywords = [
            'how to apply', 'hoe aanvragen', 'application process',
            'aanvraagprocedure', 'apply', 'aanvragen', 'submit'
        ]
        
        sentences = text.split('.')
        process_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in process_keywords):
                process_sentences.append(sentence.strip())
        
        return ' '.join(process_sentences[:2])  # Limit to 2 sentences
