"""Script to build tree-sitter language libraries."""

import os
from pathlib import Path
from tree_sitter import Language
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_languages():
    """Build tree-sitter language libraries."""
    try:
        # Get the current directory
        current_dir = Path(__file__).parent
        build_dir = current_dir / 'build'
        vendor_dir = current_dir.parent.parent / 'vendor'
        
        # Create build directory if it doesn't exist
        build_dir.mkdir(exist_ok=True)
        
        # Path to the JavaScript grammar
        js_repo_path = vendor_dir / 'tree-sitter-javascript'
        
        if not js_repo_path.exists():
            logger.error(f"JavaScript grammar not found at {js_repo_path}")
            return False
            
        # Build the language library
        logger.info(f"Building language library in {build_dir}")
        Language.build_library(
            str(build_dir / 'languages.so'),
            [str(js_repo_path)]
        )
        
        logger.info("Language library built successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error building language library: {e}")
        return False

if __name__ == '__main__':
    build_languages() 