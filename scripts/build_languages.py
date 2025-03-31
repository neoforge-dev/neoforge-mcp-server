"""Script to build tree-sitter language libraries."""

import os
import subprocess
from pathlib import Path

def build_languages():
    """Build tree-sitter language libraries."""
    # Get project root directory
    root_dir = Path(__file__).parent.parent
    
    # Create vendor directory if it doesn't exist
    vendor_dir = root_dir / 'vendor'
    vendor_dir.mkdir(exist_ok=True)
    
    # Clone tree-sitter-javascript if it doesn't exist
    js_dir = vendor_dir / 'tree-sitter-javascript'
    if not js_dir.exists():
        subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-javascript.git', str(js_dir)], check=True)
        
    # Build the language
    build_dir = js_dir / 'src'
    build_dir.mkdir(exist_ok=True)
    
    # Build the language library
    os.chdir(str(js_dir))
    subprocess.run(['cc', '-c', '-I.', '-o', 'src/parser.o', 'src/parser.c'], check=True)
    subprocess.run(['cc', '-c', '-I.', '-o', 'src/scanner.o', 'src/scanner.c'], check=True)
    subprocess.run(['cc', '-shared', '-o', 'src/tree-sitter-javascript.so', 'src/parser.o', 'src/scanner.o'], check=True)
    
if __name__ == '__main__':
    build_languages() 