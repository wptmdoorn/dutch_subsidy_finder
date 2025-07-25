"""
Scraper Manager for Dutch Subsidy Finder
Coordinates all scrapers and manages data collection
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import aiohttp

from .config import Config
from .scrapers.nwo_scraper import NWOScraper
from .scrapers.zonmw_scraper import ZonMwScraper
from .scrapers.rvo_scraper import RVOScraper
from .scrapers.horizon_scraper import HorizonScraper
from .scrapers.health_holland_scraper import HealthHollandScraper
# from .scrapers.google_scraper import GoogleScraper  # Disabled due to SSL issues


class ScraperManager:
    """Manages all subsidy scrapers and coordinates data collection."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scrapers = {
            'nwo': NWOScraper(),
            'zonmw': ZonMwScraper(),
            'rvo': RVOScraper(),
            'horizon_europe': HorizonScraper(),
            'health_holland': HealthHollandScraper(),
            # 'google_search': GoogleScraper()  # Disabled due to SSL issues
        }
        
    async def scrape_all_sources(self) -> List[Dict]:
        """Scrape all configured funding sources."""
        all_subsidies = []
        
        # Create aiohttp session with proper headers and no SSL verification
        connector = aiohttp.TCPConnector(limit=10, verify_ssl=False)
        timeout = aiohttp.ClientTimeout(total=Config.TIMEOUT)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': Config.USER_AGENT}
        ) as session:
            
            # Run all scrapers concurrently
            tasks = []
            for source_name, scraper in self.scrapers.items():
                task = self._scrape_source_with_retry(session, source_name, scraper)
                tasks.append(task)
            
            # Wait for all scrapers to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for source_name, result in zip(self.scrapers.keys(), results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to scrape {source_name}: {result}")
                else:
                    self.logger.info(f"Scraped {len(result)} subsidies from {source_name}")
                    all_subsidies.extend(result)
        
        return all_subsidies
    
    async def _scrape_source_with_retry(self, session: aiohttp.ClientSession, 
                                      source_name: str, scraper) -> List[Dict]:
        """Scrape a single source with retry logic."""
        for attempt in range(Config.MAX_RETRIES):
            try:
                self.logger.info(f"Scraping {source_name} (attempt {attempt + 1})")
                subsidies = await scraper.scrape(session)
                
                # Add source metadata to each subsidy
                for subsidy in subsidies:
                    subsidy['source'] = source_name
                    subsidy['date_scraped'] = datetime.now().isoformat()
                
                return subsidies
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {source_name}: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(Config.REQUEST_DELAY * (attempt + 1))
                else:
                    self.logger.error(f"All attempts failed for {source_name}")
                    return []
        
        return []
