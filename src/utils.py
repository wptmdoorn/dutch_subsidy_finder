"""
Utility functions for Dutch Subsidy Finder
"""

import logging
from pathlib import Path

from .config import Config


def setup_logging():
    """Setup logging configuration."""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(logs_dir / Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers to reduce noise
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


def format_currency(amount_str: str) -> str:
    """Format currency amounts consistently."""
    if not amount_str:
        return ""
    
    # Basic formatting - could be expanded
    return amount_str.replace('euro', '€').replace('EUR', '€')


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def clean_url(url: str) -> str:
    """Clean and validate URL."""
    if not url:
        return ""
    
    url = url.strip()
    
    # Add protocol if missing
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return False
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    if not text:
        return ""
    
    import re
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def safe_get(dictionary: dict, key: str, default="") -> str:
    """Safely get value from dictionary with default."""
    value = dictionary.get(key, default)
    return str(value) if value is not None else default
