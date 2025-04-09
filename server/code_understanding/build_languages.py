"""Script to build tree-sitter language libraries."""

import os
from pathlib import Path
import logging
import subprocess
import shutil
import platform

# Constants
BUILD_DIR = os.path.join(os.path.dirname(__file__), 'build')
# Determine the correct file extension based on OS
LIB_EXTENSION = '.dylib' if platform.system() == 'Darwin' else '.so'
# Define paths using the correct extension
JAVASCRIPT_LANGUAGE_FILENAME = 'javascript' + LIB_EXTENSION # e.g., javascript.dylib or javascript.so
JAVASCRIPT_LANGUAGE_PATH = os.path.join(BUILD_DIR, JAVASCRIPT_LANGUAGE_FILENAME)

TYPESCRIPT_LANGUAGE_FILENAME = 'typescript' + LIB_EXTENSION # e.g., typescript.dylib or typescript.so
TYPESCRIPT_LANGUAGE_PATH = os.path.join(BUILD_DIR, TYPESCRIPT_LANGUAGE_FILENAME)

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
            
        # Build using tree-sitter CLI
        try:
            subprocess.run(['tree-sitter', '--version'], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("tree-sitter CLI not found. Please install it with: npm install -g tree-sitter-cli")
            return False
            
        # Build the grammar
        os.chdir(str(js_repo_path))
        subprocess.run(['tree-sitter', 'generate'], check=True)
        subprocess.run(['tree-sitter', 'build'], check=True)
        
        # Determine expected library file based on OS
        built_lib_path = None
        lib_name = None # Variable to store the actual library name found

        so_path = js_repo_path / 'parser.so'
        dylib_path = js_repo_path / 'javascript.dylib' # Standard name on macOS

        if so_path.exists():
            built_lib_path = so_path
            lib_name = 'parser.so' # Use the actual name
        elif platform.system() == "Darwin" and dylib_path.exists():
            built_lib_path = dylib_path
            lib_name = 'javascript.dylib' # Use the actual name

        # Copy the built files using the correct name
        if built_lib_path and lib_name:
             # Ensure the target directory exists
            target_dir = build_dir
            target_dir.mkdir(exist_ok=True)
            
            target_path = build_dir / lib_name # Use the original name
            shutil.copy2(built_lib_path, target_path)
            logger.info(f"Successfully copied {lib_name} as JavaScript grammar to {target_path}")
            return True
        else:
            logger.error(f"Failed to find built parser library (.so or .dylib) in {js_repo_path}")
            return False
        
    except Exception as e:
        logger.error(f"Error building language library: {e}")
        return False

def build_javascript_grammar():
    """Build the JavaScript grammar."""
    try:
        # Create build directory if it doesn't exist
        build_dir = Path(__file__).parent / 'build'
        build_dir.mkdir(exist_ok=True)
        
        # Clone tree-sitter-javascript if not present
        js_repo = build_dir / 'tree-sitter-javascript'
        if not js_repo.exists():
            subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-javascript.git', str(js_repo)], check=True)
        
        # Change to the JavaScript repo directory
        os.chdir(str(js_repo))
        
        # Generate and build the grammar
        subprocess.run(['tree-sitter', 'generate'], check=True)
        subprocess.run(['tree-sitter', 'build'], check=True)
        
        # Determine expected library file based on OS
        built_lib_path = None
        lib_name = None # Variable to store the actual library name found

        so_path = js_repo / 'parser.so'
        dylib_path = js_repo / 'javascript.dylib' # Standard name on macOS

        if so_path.exists():
            built_lib_path = so_path
            lib_name = 'parser.so' # Use the actual name
        elif platform.system() == "Darwin" and dylib_path.exists():
            built_lib_path = dylib_path
            lib_name = 'javascript.dylib' # Use the actual name

        # Copy the built parser to the build directory with its original name
        if built_lib_path and lib_name:
            # Ensure the target directory exists
            target_dir = build_dir
            target_dir.mkdir(exist_ok=True)

            target_path = build_dir / lib_name # Use the original name
            shutil.copy2(built_lib_path, target_path)
            logger.info(f"Successfully copied {lib_name} as JavaScript grammar to {target_path}")
        else:
            raise Exception(f"Parser library (.so or .dylib) not found in {js_repo}")

        logger.info("Successfully built JavaScript grammar")
        return True
    except Exception as e:
        logger.error(f"Error building JavaScript grammar: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    build_languages()
    build_javascript_grammar() 