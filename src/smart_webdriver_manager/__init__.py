__version__ = "0.5.0"


import logging

logger = logging.getLogger(__name__)


# Avaialble managers
from smart_webdriver_manager.driver import ChromeDriverManager


__all__ = [
    "ChromeDriverManager",
]
