"""
ZonMw (Nederlandse organisatie voor gezondheidsonderzoek en zorginnovatie) Scraper
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from ..config import Config
from ..base_scraper import BaseScraper


class ZonMwScraper(BaseScraper):
    """Scraper for ZonMw funding opportunities."""
    
    def __init__(self):
        super().__init__(Config.FUNDING_SOURCES['zonmw'])
        self.logger = logging.getLogger(__name__)
        
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Scrape ZonMw funding opportunities."""
        subsidies = []
        
        for url in self.config['search_urls']:
            self.logger.info(f"Scraping ZonMw URL: {url}")
            soup = await self.fetch_page(session, url)
            
            if soup:
                page_subsidies = await self._parse_zonmw_page(session, soup, url)
                subsidies.extend(page_subsidies)
        
        return subsidies
    
    async def _parse_zonmw_page(self, session: aiohttp.ClientSession, 
                              soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Parse ZonMw page for funding opportunities."""
        subsidies = []
        
        # Look for funding opportunity listings - ZonMw specific selectors
        funding_selectors = [
            '.funding-opportunity',
            '.call-item',
            '.subsidy-item',
            '.financiering-item',
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
                    'subsidie', 'financiering', 'call', 'oproep', 'tender',
                    'funding', 'grant', 'beurs'
                ]):
                    opportunities_found.append(link)
        
        # Process each found opportunity
        for opportunity in opportunities_found[:25]:  # Limit to prevent overload
            try:
                subsidy = await self._parse_zonmw_opportunity(session, opportunity, base_url)
                if subsidy and subsidy['name']:
                    subsidies.append(subsidy)
            except Exception as e:
                self.logger.warning(f"Failed to parse ZonMw opportunity: {e}")
        
        return subsidies
    
    async def _parse_zonmw_opportunity(self, session: aiohttp.ClientSession, 
                                     element, base_url: str) -> Dict:
        """Parse individual ZonMw funding opportunity."""
        
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
        description = ""
        deadline = ""
        amount = ""
        
        # Look for description in common ZonMw structures
        desc_selectors = ['.description', '.summary', '.excerpt', 'p', '.content']
        for selector in desc_selectors:
            desc_elem = element.find(selector)
            if desc_elem:
                description = self.clean_text(self.extract_text(desc_elem))
                break
        
        # Extract information from element text
        full_text = self.extract_text(element)
        deadline = self.extract_deadline(full_text)
        amount = self.extract_amount(full_text)
        
        # Get detailed information if available
        if detail_url != base_url:
            detail_info = await self._get_zonmw_detail_info(session, detail_url)
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
            research_areas=self._extract_health_research_areas(full_text),
            description=description,
            application_process=self._extract_application_process(full_text),
            contact_info="",
            url=detail_url,
            raw_text=full_text
        )
    
    async def _get_zonmw_detail_info(self, session: aiohttp.ClientSession, 
                                   url: str) -> Dict:
        """Get detailed information from ZonMw opportunity page."""
        soup = await self.fetch_page(session, url)
        if not soup:
            return {}
        
        info = {}
        
        # Extract detailed description
        desc_selectors = [
            '.call-description',
            '.content',
            '.description', 
            'main',
            '.body-content',
            '.page-content'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                desc_text = self.extract_text(desc_elem)
                if len(desc_text) > 100:  # Only use substantial descriptions
                    info['description'] = self.clean_text(desc_text)
                    break
        
        # Extract deadline and amount from full page
        full_text = self.extract_text(soup)
        info['deadline'] = self.extract_deadline(full_text)
        info['amount'] = self.extract_amount(full_text)
        
        return info
    
    def _determine_status(self, deadline: str, text: str) -> str:
        """Determine the status of the funding opportunity."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in [
            'gesloten', 'closed', 'afgelopen', 'expired', 'verlopen'
        ]):
            return 'Closed'
        elif any(word in text_lower for word in [
            'open', 'geopend', 'beschikbaar', 'available', 'actief'
        ]):
            return 'Open'
        elif deadline:
            return 'Open'
        else:
            return 'Unknown'
    
    def _extract_eligibility(self, text: str) -> str:
        """Extract eligibility criteria from text."""
        eligibility_keywords = [
            'wie kan aanvragen', 'eligibility', 'eligible', 'geschikt',
            'voorwaarden', 'requirements', 'vereisten', 'criteria',
            'doelgroep', 'target group'
        ]
        
        sentences = text.split('.')
        eligibility_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in eligibility_keywords):
                eligibility_sentences.append(sentence.strip())
        
        return ' '.join(eligibility_sentences[:3])
    
    def _extract_health_research_areas(self, text: str) -> str:
        """Extract health and medical research areas from text."""
        research_areas = []
        text_lower = text.lower()
        
        # Health-specific research areas
        health_keywords = [
            'gezondheid', 'health', 'medisch', 'medical', 'klinisch', 'clinical',
            'zorg', 'care', 'patient', 'patiënt', 'behandeling', 'treatment',
            'diagnose', 'diagnosis', 'therapie', 'therapy', 'preventie', 'prevention',
            'public health', 'volksgezondheid', 'epidemiologie', 'epidemiology',
            'farmacologie', 'pharmacology', 'biomedisch', 'biomedical'
        ]
        
        for keyword in health_keywords:
            if keyword in text_lower:
                research_areas.append(keyword.title())
        
        return ', '.join(list(set(research_areas))[:6])  # Remove duplicates, limit to 6
    
    def _extract_application_process(self, text: str) -> str:
        """Extract application process information."""
        process_keywords = [
            'hoe aanvragen', 'how to apply', 'application process',
            'aanvraagprocedure', 'indienen', 'submit', 'deadline'
        ]
        
        sentences = text.split('.')
        process_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in process_keywords):
                process_sentences.append(sentence.strip())
        
        return ' '.join(process_sentences[:2])  # Limit to 2 sentences
