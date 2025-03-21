# app/utils/helpers.py (updated)
import logging
import logging.handlers
import os
import re
from typing import Optional, Dict, Any
from app.config.settings import settings

def setup_logging():
    """
    Configure application logging with rotating file handler and console output.
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def normalize_arabic_text(text: str) -> str:
    """
    Normalize Arabic text by removing diacritics and standardizing characters.
    
    Args:
        text: Arabic text to normalize
        
    Returns:
        Normalized text
    """
    if not settings.NORMALIZE_ARABIC:
        return text
        
    # Remove diacritics (tashkeel)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    
    # Normalize alef variations to plain alef
    text = re.sub(r'[إأآا]', 'ا', text)
    
    # Normalize yaa variations
    text = re.sub(r'[يى]', 'ي', text)
    
    # Normalize taa marbuta
    text = re.sub(r'ة', 'ه', text)
    
    return text

def get_document_url_info(url: str) -> Dict[str, Any]:
    """
    Extract information from a Shamela library URL.
    
    Args:
        url: Document URL
        
    Returns:
        Dictionary with book ID, page number, etc.
    """
    # Example URL: https://shamela.ws/book/12345/page/67
    match = re.search(r'/book/(\d+)(?:/page/(\d+))?', url)
    if match:
        book_id = match.group(1)
        page = match.group(2) or "1"
        return {
            "book_id": book_id,
            "page": page,
            "is_shamela_url": True
        }
    return {"is_shamela_url": False}