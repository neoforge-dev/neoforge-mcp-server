"""Code understanding module for analyzing source code."""

import os
import logging
from .parser import CodeParser
from .analyzer import CodeAnalyzer
from .extractor import SymbolExtractor
from .build_languages import build_languages

logger = logging.getLogger(__name__)

# Build language library on import
try:
    LANGUAGE_LIB_PATH = build_languages()
    logger.info(f"Language library built at {LANGUAGE_LIB_PATH}")
except Exception as e:
    logger.error(f"Failed to build language library: {e}")
    LANGUAGE_LIB_PATH = None

__all__ = ['CodeParser', 'CodeAnalyzer', 'SymbolExtractor'] 