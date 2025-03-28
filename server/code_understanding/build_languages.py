"""Script to build tree-sitter language libraries."""

import os
import logging
from tree_sitter import Language

logger = logging.getLogger(__name__)

def build_languages():
    """Build tree-sitter language libraries."""
    try:
        # Get the absolute path to the vendor directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        vendor_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'vendor')
        
        # Python language path
        python_path = os.path.join(vendor_dir, 'tree-sitter-python')
        
        # Create build directory if it doesn't exist
        build_dir = os.path.join(current_dir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        
        # Build language library
        library_path = os.path.join(build_dir, 'languages.so')
        Language.build_library(
            library_path,
            [python_path]
        )
        
        logger.info(f"Successfully built language library at {library_path}")
        return library_path
        
    except Exception as e:
        logger.error(f"Failed to build language library: {e}")
        raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    build_languages() 