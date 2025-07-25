#!/usr/bin/env python3
"""
Dutch Subsidy Finder for Clinical Chemistry & AI Research
=========================================================

This application scrapes major Dutch funding sources for research and innovation
subsidies, with a focus on clinical chemistry and AI research opportunities.

Author: Clinical Chemistry & AI Research Tool
Date: 2025
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.scraper_manager import ScraperManager
from src.data_processor import DataProcessor
from src.excel_exporter import ExcelExporter
from src.utils import setup_logging


async def main():
    """Main application entry point."""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Dutch Subsidy Finder...")
    logger.info(f"Target research areas: {', '.join(Config.RESEARCH_KEYWORDS)}")
    
    try:
        # Initialize components
        scraper_manager = ScraperManager()
        data_processor = DataProcessor()
        excel_exporter = ExcelExporter()
        
        # Step 1: Scrape all funding sources
        logger.info("Step 1: Scraping funding sources...")
        raw_subsidies = await scraper_manager.scrape_all_sources()
        logger.info(f"Found {len(raw_subsidies)} total subsidies")
        
        # Step 2: Process and filter data
        logger.info("Step 2: Processing and filtering data...")
        processed_subsidies = data_processor.process_subsidies(raw_subsidies)
        logger.info(f"Processed {len(processed_subsidies)} relevant subsidies")
        
        # Step 3: Export to Excel
        logger.info("Step 3: Exporting to Excel...")
        output_file = excel_exporter.export_subsidies(processed_subsidies)
        
        logger.info(f"✅ Successfully exported subsidies to: {output_file}")
        logger.info(f"📊 Total subsidies found: {len(processed_subsidies)}")
        
        # Print summary statistics
        print_summary(processed_subsidies)
        
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        sys.exit(1)


def print_summary(subsidies):
    """Print summary statistics of found subsidies."""
    print("\n" + "="*60)
    print("🎯 DUTCH SUBSIDY FINDER - SUMMARY REPORT")
    print("="*60)
    
    total = len(subsidies)
    print(f"📈 Total Subsidies Found: {total}")
    
    if total > 0:
        # Count by funding organization
        orgs = {}
        high_relevance = 0
        upcoming_deadlines = 0
        
        for subsidy in subsidies:
            org = subsidy.get('funding_organization', 'Unknown')
            orgs[org] = orgs.get(org, 0) + 1
            
            if subsidy.get('relevance_score', 0) >= 8:
                high_relevance += 1
                
            # Check for upcoming deadlines (within 60 days)
            deadline = subsidy.get('deadline')
            if deadline and isinstance(deadline, str):
                try:
                    deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
                    days_until = (deadline_date - datetime.now()).days
                    if 0 <= days_until <= 60:
                        upcoming_deadlines += 1
                except:
                    pass
        
        print(f"🎯 High Relevance (Score ≥8): {high_relevance}")
        print(f"⏰ Upcoming Deadlines (≤60 days): {upcoming_deadlines}")
        
        print("\n📊 By Funding Organization:")
        for org, count in sorted(orgs.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {org}: {count}")
    
    print("\n🔬 Focused on: Clinical Chemistry & AI Research")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
