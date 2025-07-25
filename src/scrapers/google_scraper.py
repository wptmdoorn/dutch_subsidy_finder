"""
Google Search Scraper for Dutch Subsidies
Searches Google for relevant subsidy opportunities
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import quote_plus, urljoin
import re

import aiohttp
from bs4 import BeautifulSoup

from ..config import Config
from ..base_scraper import BaseScraper


class GoogleScraper(BaseScraper):
    """Scraper that uses Google search to find subsidy opportunities."""
    
    def __init__(self):
        # Create a config for Google scraper
        google_config = {
            'name': 'Google Search Results',
            'search_urls': []  # Will be generated dynamically
        }
        super().__init__(google_config)
        self.logger = logging.getLogger(__name__)
        
        # Search queries for Dutch subsidies
        self.search_queries = [
            "subsidie klinische chemie Nederland 2024 2025",
            "financiering AI gezondheidszorg Nederland",
            "onderzoeksbeurs laboratoriumgeneeskunde Nederland",
            "NWO subsidie medische technologie",
            "ZonMw financiering diagnostiek",
            "RVO innovatie subsidie healthcare",
            "Nederlandse subsidies medical AI",
            "funding clinical chemistry Netherlands",
            "grant laboratory medicine Netherlands",
            "Dutch healthcare innovation funding",
            "subsidie digitale zorg Nederland",
            "financiering biomedisch onderzoek Nederland"
        ]
    
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Search Google for subsidy opportunities."""
        subsidies = []
        
        for query in self.search_queries:
            self.logger.info(f"Searching Google for: {query}")
            try:
                search_results = await self._google_search(session, query)
                subsidies.extend(search_results)
                
                # Add delay between searches to be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.warning(f"Failed to search Google for '{query}': {e}")
        
        # Remove duplicates based on URL
        unique_subsidies = []
        seen_urls = set()
        
        for subsidy in subsidies:
            url = subsidy.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_subsidies.append(subsidy)
        
        return unique_subsidies[:15]  # Limit to top 15 results
    
    async def _google_search(self, session: aiohttp.ClientSession, query: str) -> List[Dict]:
        """Try multiple search approaches to find subsidies."""
        subsidies = []
        
        # Try different search engines and approaches - using HTTP where possible
        search_attempts = [
            # Try HTTP versions first (no SSL needed)
            ("simple_search", f"http://www.google.com/search?q={quote_plus(query + ' site:nwo.nl OR site:zonmw.nl OR site:rvo.nl')}"),
            # Alternative search engines that might work better
            ("bing", f"https://www.bing.com/search?q={quote_plus(query)}"),
            # Direct site search (fallback)
            ("direct_search", f"https://www.nwo.nl/en/calls"),
        ]
        
        for search_name, search_url in search_attempts:
            try:
                self.logger.info(f"Trying {search_name} search: {query}")
                
                # Simple headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SubsidyBot/1.0)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                
                # Disable SSL verification completely
                connector = aiohttp.TCPConnector(verify_ssl=False)
                
                async with aiohttp.ClientSession(connector=connector) as search_session:
                    async with search_session.get(search_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Parse results based on search engine
                            if search_name == "startpage":
                                results = await self._parse_startpage_results(search_session, soup, query)
                            elif search_name == "searx":
                                results = await self._parse_searx_results(search_session, soup, query)
                            elif search_name == "direct_nwo":
                                results = await self._parse_direct_site_results(search_session, soup, query, "NWO")
                            else:
                                results = []
                            
                            subsidies.extend(results)
                            
                            if results:
                                self.logger.info(f"Found {len(results)} results from {search_name}")
                                break  # If we found results, don't try other search engines
                        else:
                            self.logger.warning(f"{search_name} search failed with status {response.status}")
                            
                await asyncio.sleep(1)  # Rate limiting between attempts
                
            except Exception as e:
                self.logger.warning(f"Failed {search_name} search for '{query}': {e}")
                continue
        
        return subsidies
    
    async def _parse_duckduckgo_results(self, session: aiohttp.ClientSession, 
                                      soup: BeautifulSoup, query: str) -> List[Dict]:
        """Parse DuckDuckGo search results page."""
        subsidies = []
        
        # Debug: Check if we got any HTML content
        if not soup or not soup.get_text(strip=True):
            self.logger.warning(f"No HTML content received for DuckDuckGo query: {query}")
            return subsidies
        
        # DuckDuckGo search result selectors
        result_selectors = [
            '.result',  # Standard DuckDuckGo result
            '.web-result',  # Web result container
            '.result__body',  # Result body
            'div[data-testid="result"]'  # New DuckDuckGo format
        ]
        
        results_found = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                self.logger.info(f"Found {len(results)} DuckDuckGo results with selector: {selector}")
                results_found = results
                break
        
        if not results_found:
            self.logger.warning(f"No DuckDuckGo search results found for query: {query}")
            return subsidies
        
        for i, result in enumerate(results_found[:8]):  # Limit to top 8 results per query
            try:
                self.logger.info(f"Processing DuckDuckGo result {i+1}")
                subsidy = await self._parse_duckduckgo_result(session, result, query)
                if subsidy and self._is_relevant_result(subsidy):
                    subsidies.append(subsidy)
                    self.logger.info(f"Added relevant subsidy: {subsidy.get('name', 'Unknown')}")
                elif subsidy:
                    self.logger.info(f"Filtered out irrelevant result: {subsidy.get('name', 'Unknown')}")
            except Exception as e:
                self.logger.warning(f"Failed to parse DuckDuckGo result {i+1}: {e}")
        
        return subsidies
    
    async def _parse_duckduckgo_result(self, session: aiohttp.ClientSession, 
                                     result_element, query: str) -> Dict:
        """Parse individual DuckDuckGo search result."""
        
        # Extract title
        title_selectors = ['.result__title a', '.result__a', 'h2 a', 'h3 a', 'a[data-testid="result-title-a"]']
        title = ""
        url = ""
        
        for selector in title_selectors:
            title_elem = result_element.select_one(selector)
            if title_elem:
                title = self.clean_text(self.extract_text(title_elem))
                url = title_elem.get('href', '')
                break
        
        # Extract snippet/description
        snippet_selectors = ['.result__snippet', '.result__body', 'span[data-testid="result-snippet"]']
        description = ""
        
        for selector in snippet_selectors:
            snippet_elem = result_element.select_one(selector)
            if snippet_elem:
                description = self.clean_text(self.extract_text(snippet_elem))
                break
        
        # Extract additional information from the snippet
        full_text = f"{title} {description}"
        deadline = self.extract_deadline(full_text)
        amount = self.extract_amount(full_text)
        
        # Determine funding organization from URL
        funding_org = self._determine_funding_org(url)
        
        return self.create_subsidy_dict(
            name=title,
            funding_organization=funding_org,
            amount=amount,
            deadline=deadline,
            status=self._determine_status_from_text(full_text),
            eligibility=self._extract_eligibility_from_snippet(description),
            research_areas=self._extract_research_areas_from_text(full_text),
            description=description,
            application_process="",
            contact_info="",
            url=url,
            raw_text=full_text
        )
    
    async def _parse_google_results(self, session: aiohttp.ClientSession,
                                  soup: BeautifulSoup, query: str) -> List[Dict]:
        """Parse Google search results page."""
        subsidies = []
        
        # Debug: Check if we got any HTML content
        if not soup or not soup.get_text(strip=True):
            self.logger.warning(f"No HTML content received for query: {query}")
            return subsidies
        
        # Debug: Log some of the HTML to see what we're getting
        page_text = soup.get_text()[:500]  # First 500 characters
        self.logger.info(f"Google page content preview: {page_text[:200]}...")
        
        # Check if Google is blocking us
        if "unusual traffic" in page_text.lower() or "captcha" in page_text.lower():
            self.logger.warning("Google is blocking requests - unusual traffic detected")
            return subsidies
        
        # Google search result selectors (these may change over time)
        result_selectors = [
            'div.g',  # Standard Google result
            '.rc',    # Result container
            '[data-ved]',  # Results with data-ved attribute
            'div[data-ved]',  # More specific data-ved
            '.g',     # Simple g class
            'div.tF2Cxc'  # New Google result container
        ]
        
        results_found = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                self.logger.info(f"Found {len(results)} results with selector: {selector}")
                results_found = results
                break
        
        if not results_found:
            self.logger.warning(f"No search results found with any selector for query: {query}")
            # Debug: Save HTML to see structure
            with open(f"debug_google_{query.replace(' ', '_')[:20]}.html", "w") as f:
                f.write(str(soup))
            return subsidies
        
        for i, result in enumerate(results_found[:8]):  # Limit to top 8 results per query
            try:
                self.logger.info(f"Processing result {i+1}")
                subsidy = await self._parse_google_result(session, result, query)
                if subsidy and self._is_relevant_result(subsidy):
                    subsidies.append(subsidy)
                    self.logger.info(f"Added relevant subsidy: {subsidy.get('name', 'Unknown')}")
                elif subsidy:
                    self.logger.info(f"Filtered out irrelevant result: {subsidy.get('name', 'Unknown')}")
            except Exception as e:
                self.logger.warning(f"Failed to parse Google result {i+1}: {e}")
        
        return subsidies
    
    async def _parse_google_result(self, session: aiohttp.ClientSession, 
                                 result_element, query: str) -> Dict:
        """Parse individual Google search result."""
        
        # Extract title
        title_elem = result_element.find(['h3', 'h2', 'h1'])
        title = self.clean_text(self.extract_text(title_elem)) if title_elem else ""
        
        # Extract URL
        link_elem = result_element.find('a', href=True)
        url = link_elem['href'] if link_elem else ""
        
        # Clean Google redirect URLs
        if url.startswith('/url?q='):
            url = url.split('/url?q=')[1].split('&')[0]
        
        # Extract snippet/description
        snippet_selectors = ['.VwiC3b', '.s', '.st', 'span']
        description = ""
        
        for selector in snippet_selectors:
            snippet_elem = result_element.select_one(selector)
            if snippet_elem:
                snippet_text = self.extract_text(snippet_elem)
                if len(snippet_text) > 50:  # Only use substantial snippets
                    description = self.clean_text(snippet_text)
                    break
        
        # Extract additional information from the snippet
        full_text = f"{title} {description}"
        deadline = self.extract_deadline(full_text)
        amount = self.extract_amount(full_text)
        
        # Determine funding organization from URL
        funding_org = self._determine_funding_org(url)
        
        return self.create_subsidy_dict(
            name=title,
            funding_organization=funding_org,
            amount=amount,
            deadline=deadline,
            status=self._determine_status_from_text(full_text),
            eligibility=self._extract_eligibility_from_snippet(description),
            research_areas=self._extract_research_areas_from_text(full_text),
            description=description,
            application_process="",
            contact_info="",
            url=url,
            raw_text=full_text
        )
    
    def _is_relevant_result(self, subsidy: Dict) -> bool:
        """Check if the search result is relevant to subsidies."""
        title = subsidy.get('name', '').lower()
        description = subsidy.get('description', '').lower()
        url = subsidy.get('url', '').lower()
        
        # Must contain subsidy-related keywords
        subsidy_keywords = [
            'subsidie', 'subsidy', 'financiering', 'funding', 'grant',
            'beurs', 'steun', 'support', 'call', 'oproep'
        ]
        
        # Must contain research/health keywords
        research_keywords = [
            'onderzoek', 'research', 'innovatie', 'innovation',
            'gezondheid', 'health', 'medisch', 'medical',
            'klinisch', 'clinical', 'ai', 'artificial intelligence'
        ]
        
        # Check if result contains relevant keywords
        text_to_check = f"{title} {description}"
        
        has_subsidy_keyword = any(keyword in text_to_check for keyword in subsidy_keywords)
        has_research_keyword = any(keyword in text_to_check for keyword in research_keywords)
        
        # Filter out irrelevant domains
        irrelevant_domains = [
            'youtube.com', 'facebook.com', 'twitter.com', 'linkedin.com',
            'wikipedia.org', 'google.com', 'bing.com'
        ]
        
        is_relevant_domain = not any(domain in url for domain in irrelevant_domains)
        
        return has_subsidy_keyword and has_research_keyword and is_relevant_domain
    
    def _determine_funding_org(self, url: str) -> str:
        """Determine funding organization from URL."""
        url_lower = url.lower()
        
        if 'nwo.nl' in url_lower:
            return 'NWO (Nederlandse Organisatie voor Wetenschappelijk Onderzoek)'
        elif 'zonmw.nl' in url_lower:
            return 'ZonMw'
        elif 'rvo.nl' in url_lower:
            return 'RVO (Rijksdienst voor Ondernemend Nederland)'
        elif 'health-holland.com' in url_lower:
            return 'Health~Holland'
        elif 'europa.eu' in url_lower or 'ec.europa.eu' in url_lower:
            return 'European Commission / Horizon Europe'
        elif 'government.nl' in url_lower or 'rijksoverheid.nl' in url_lower:
            return 'Dutch Government'
        else:
            return 'Various (Google Search Result)'
    
    def _determine_status_from_text(self, text: str) -> str:
        """Determine status from text content."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in [
            'gesloten', 'closed', 'expired', 'verlopen', 'afgelopen'
        ]):
            return 'Closed'
        elif any(word in text_lower for word in [
            'open', 'geopend', 'available', 'beschikbaar', 'actief'
        ]):
            return 'Open'
        else:
            return 'Unknown'
    
    def _extract_eligibility_from_snippet(self, text: str) -> str:
        """Extract eligibility information from snippet."""
        if not text:
            return ""
        
        eligibility_keywords = [
            'voor', 'eligible', 'geschikt', 'doelgroep',
            'researchers', 'onderzoekers', 'companies', 'bedrijven'
        ]
        
        sentences = text.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in eligibility_keywords):
                return sentence.strip()
        
        return ""
    
    def _extract_research_areas_from_text(self, text: str) -> str:
        """Extract research areas from text."""
        research_areas = []
        text_lower = text.lower()
        
        # Research area keywords
        area_keywords = [
            'klinische chemie', 'clinical chemistry', 'laboratoriumgeneeskunde',
            'laboratory medicine', 'diagnostiek', 'diagnostics', 'ai',
            'artificial intelligence', 'machine learning', 'gezondheid',
            'health', 'medisch', 'medical', 'innovatie', 'innovation'
        ]
        
        for keyword in area_keywords:
            if keyword in text_lower:
                research_areas.append(keyword.title())
        
        return ', '.join(list(set(research_areas))[:5])  # Remove duplicates, limit to 5
    
    async def _parse_startpage_results(self, session: aiohttp.ClientSession, 
                                     soup: BeautifulSoup, query: str) -> List[Dict]:
        """Parse Startpage search results."""
        subsidies = []
        
        # Startpage result selectors
        result_selectors = ['.w-gl__result', '.result', 'div.result']
        
        results_found = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                self.logger.info(f"Found {len(results)} Startpage results")
                results_found = results
                break
        
        for i, result in enumerate(results_found[:5]):
            try:
                # Extract title and URL
                title_elem = result.select_one('h3 a, .result-title a, a')
                if not title_elem:
                    continue
                    
                title = self.clean_text(self.extract_text(title_elem))
                url = title_elem.get('href', '')
                
                # Extract description
                desc_elem = result.select_one('.result-desc, .w-gl__description')
                description = self.clean_text(self.extract_text(desc_elem)) if desc_elem else ""
                
                if self._is_relevant_result({'name': title, 'description': description, 'url': url}):
                    subsidy = self.create_subsidy_dict(
                        name=title,
                        funding_organization=self._determine_funding_org(url),
                        amount="",
                        deadline="",
                        status="Unknown",
                        eligibility="",
                        research_areas=self._extract_research_areas_from_text(f"{title} {description}"),
                        description=description,
                        application_process="",
                        contact_info="",
                        url=url,
                        raw_text=f"{title} {description}"
                    )
                    subsidies.append(subsidy)
                    
            except Exception as e:
                self.logger.warning(f"Failed to parse Startpage result {i+1}: {e}")
        
        return subsidies
    
    async def _parse_searx_results(self, session: aiohttp.ClientSession, 
                                 soup: BeautifulSoup, query: str) -> List[Dict]:
        """Parse Searx search results."""
        subsidies = []
        
        # Searx result selectors
        result_selectors = ['.result', 'article.result']
        
        results_found = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                self.logger.info(f"Found {len(results)} Searx results")
                results_found = results
                break
        
        for i, result in enumerate(results_found[:5]):
            try:
                # Extract title and URL
                title_elem = result.select_one('h3 a, .result-title a')
                if not title_elem:
                    continue
                    
                title = self.clean_text(self.extract_text(title_elem))
                url = title_elem.get('href', '')
                
                # Extract description
                desc_elem = result.select_one('.result-content, .content')
                description = self.clean_text(self.extract_text(desc_elem)) if desc_elem else ""
                
                if self._is_relevant_result({'name': title, 'description': description, 'url': url}):
                    subsidy = self.create_subsidy_dict(
                        name=title,
                        funding_organization=self._determine_funding_org(url),
                        amount="",
                        deadline="",
                        status="Unknown",
                        eligibility="",
                        research_areas=self._extract_research_areas_from_text(f"{title} {description}"),
                        description=description,
                        application_process="",
                        contact_info="",
                        url=url,
                        raw_text=f"{title} {description}"
                    )
                    subsidies.append(subsidy)
                    
            except Exception as e:
                self.logger.warning(f"Failed to parse Searx result {i+1}: {e}")
        
        return subsidies
    
    async def _parse_direct_site_results(self, session: aiohttp.ClientSession, 
                                       soup: BeautifulSoup, query: str, site_name: str) -> List[Dict]:
        """Parse direct site search results."""
        subsidies = []
        
        # Generic selectors for direct site results
        result_selectors = [
            '.call-item', '.funding-item', '.grant-item',
            '.result', 'article', '.post', '.item'
        ]
        
        results_found = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                self.logger.info(f"Found {len(results)} direct site results from {site_name}")
                results_found = results
                break
        
        for i, result in enumerate(results_found[:5]):
            try:
                # Extract title
                title_elem = result.select_one('h1, h2, h3, h4, .title, a')
                if not title_elem:
                    continue
                    
                title = self.clean_text(self.extract_text(title_elem))
                
                # Try to find URL
                link_elem = result.select_one('a')
                url = link_elem.get('href', '') if link_elem else ""
                if url and not url.startswith('http'):
                    url = f"https://www.nwo.nl{url}" if site_name == "NWO" else url
                
                # Extract description from text content
                description = self.clean_text(self.extract_text(result))[:500]
                
                if title and len(title) > 10:  # Basic validation
                    subsidy = self.create_subsidy_dict(
                        name=title,
                        funding_organization=site_name,
                        amount="",
                        deadline="",
                        status="Unknown",
                        eligibility="",
                        research_areas=self._extract_research_areas_from_text(f"{title} {description}"),
                        description=description,
                        application_process="",
                        contact_info="",
                        url=url,
                        raw_text=f"{title} {description}"
                    )
                    subsidies.append(subsidy)
                    
            except Exception as e:
                self.logger.warning(f"Failed to parse direct site result {i+1}: {e}")
        
        return subsidies
