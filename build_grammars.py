0#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

def build_grammars():
    """Build tree-sitter grammars for supported languages."""
    # Create build directory if it doesn't exist
    build_dir = Path('build')
    build_dir.mkdir(exist_ok=True)
    
    # Clone tree-sitter-javascript if not exists
    js_grammar_dir = Path('vendor/tree-sitter-javascript')
    if not js_grammar_dir.exists():
        subprocess.run([
            'git', 'clone',
            'https://github.com/tree-sitter/tree-sitter-javascript.git',
            str(js_grammar_dir)
        ], check=True)
    
    # Build JavaScript grammar
    print("Building JavaScript grammar...")
    subprocess.run([
        'tree-sitter', 'generate',
        str(js_grammar_dir / 'grammar.js'),
        '--out-dir', str(build_dir)
    ], check=True)
    
    # Build shared library
    print("Building shared library...")
    if sys.platform == 'win32':
        subprocess.run([
            'gcc', '-shared', '-o', str(build_dir / 'my-languages.dll'),
            '-I', str(js_grammar_dir / 'src'),
            str(build_dir / 'javascript.c'),
            '-lstdc++', '-fPIC'
        ], check=True)
    else:
        subprocess.run([
            'gcc', '-shared', '-o', str(build_dir / 'my-languages.so'),
            '-I', str(js_grammar_dir / 'src'),
            str(build_dir / 'javascript.c'),
            '-lstdc++', '-fPIC'
        ], check=True)
    
    print("Grammar build complete!")

if __name__ == '__main__':
    build_grammars() 