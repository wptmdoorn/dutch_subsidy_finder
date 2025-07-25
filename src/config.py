"""
Configuration settings for Dutch Subsidy Finder
"""

from datetime import datetime
from pathlib import Path


class Config:
    """Application configuration settings."""
    
    # Research keywords for clinical chemistry & AI
    RESEARCH_KEYWORDS = [
        # Clinical Chemistry
        'clinical chemistry', 'klinische chemie', 'laboratory medicine', 
        'laboratoriumgeneeskunde', 'diagnostics', 'diagnostiek', 'biomarkers',
        'laboratory diagnostics', 'medical laboratory', 'clinical laboratory',
        'point-of-care', 'POCT', 'molecular diagnostics', 'immunoassays',
        'mass spectrometry', 'chromatography', 'spectroscopy',
        
        # AI & Technology
        'artificial intelligence', 'AI', 'machine learning', 'ML',
        'deep learning', 'neural networks', 'data science',
        'predictive analytics', 'algorithm', 'automation',
        'digital health', 'digitale zorg', 'e-health', 'telemedicine',
        'medical AI', 'healthcare AI', 'clinical AI',
        
        # Healthcare & Medical
        'healthcare', 'gezondheidszorg', 'medical', 'medisch',
        'clinical', 'klinisch', 'patient care', 'patiëntenzorg',
        'precision medicine', 'personalized medicine', 'gepersonaliseerde geneeskunde',
        'medical technology', 'medische technologie', 'health technology',
        'biomedical', 'biomedisch', 'life sciences', 'levenswetenschappen',
        
        # Innovation & Research
        'innovation', 'innovatie', 'research', 'onderzoek',
        'development', 'ontwikkeling', 'technology', 'technologie',
        'digital transformation', 'digitale transformatie'
    ]
    
    # Funding sources to scrape
    FUNDING_SOURCES = {
        'nwo': {
            'name': 'Nederlandse Organisatie voor Wetenschappelijk Onderzoek',
            'base_url': 'https://www.nwo.nl',
            'search_urls': [
                'https://www.nwo.nl/calls',
                'https://www.nwo.nl/en/calls'
            ]
        },
        'zonmw': {
            'name': 'ZonMw',
            'base_url': 'https://www.zonmw.nl',
            'search_urls': [
                'https://www.zonmw.nl/nl/financieringswijzer/',
                'https://www.zonmw.nl/en/funding-opportunities/'
            ]
        },
        'rvo': {
            'name': 'Rijksdienst voor Ondernemend Nederland',
            'base_url': 'https://www.rvo.nl',
            'search_urls': [
                'https://www.rvo.nl/subsidies-financiering',
                'https://www.rvo.nl/subsidies-financiering/innovatie'
            ]
        },
        'horizon_europe': {
            'name': 'Horizon Europe (Dutch participation)',
            'base_url': 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home',
            'search_urls': [
                'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search'
            ]
        },
        'health_holland': {
            'name': 'Health~Holland',
            'base_url': 'https://www.health-holland.com',
            'search_urls': [
                'https://www.health-holland.com/funding'
            ]
        },
        # Temporarily disabled due to SSL certificate issues
        # 'google_search': {
        #     'name': 'Google Search Results',
        #     'base_url': 'https://www.google.com',
        #     'search_urls': []  # Generated dynamically
        # }
    }
    
    # Scraping settings
    REQUEST_DELAY = 2  # seconds between requests
    MAX_RETRIES = 3
    TIMEOUT = 30  # seconds
    
    # User agent for web scraping
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    # Output settings
    OUTPUT_DIR = Path('output')
    OUTPUT_FILENAME = f'dutch_subsidies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    # Excel column configuration
    EXCEL_COLUMNS = [
        'Subsidy Name',
        'Funding Organization', 
        'Amount/Budget',
        'Application Deadline',
        'Status',
        'Eligibility Criteria',
        'Research Areas',
        'Description',
        'Application Process',
        'Contact Information',
        'Website URL',
        'Relevance Score',
        'Keywords Matched',
        'Date Scraped'
    ]
    
    # Relevance scoring weights
    SCORING_WEIGHTS = {
        'title_match': 3.0,
        'description_match': 2.0,
        'keywords_match': 1.5,
        'eligibility_match': 1.0,
        'deadline_bonus': 0.5  # bonus for upcoming deadlines
    }
    
    # Minimum relevance score to include in results
    MIN_RELEVANCE_SCORE = 3.0
    
    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'subsidy_finder.log'
