__version__ = '0.7.0'


import logging

logger = logging.getLogger(__name__)


# Available managers
from smart_webdriver_manager.driver import ChromeDriverManager

__all__ = [
    'ChromeDriverManager',
]
