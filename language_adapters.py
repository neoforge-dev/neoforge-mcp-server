'''Language-specific parser adapters for JavaScript and Swift.'''

import ast
import re
from typing import Optional, Dict, Any, List, Union
from tree_sitter import Language, Parser, Tree, Node
import logging # Add logging
import subprocess # For building grammar
import os # For path checks
from pathlib import Path # For path handling
import json

# Import common Mock structure
try:
    from .common_types import MockTree, MockNode
except ImportError:
    # Handle both relative and absolute imports for flexibility
    try:
        from server.code_understanding.common_types import MockTree, MockNode
    except ImportError:
        from common_types import MockTree, MockNode

logger = logging.getLogger(__name__) 

def analyze(self, code):
    """
    Analyze JavaScript code to extract functions, classes, imports and exports.
    """
    try:
        tree = self.parse(code)
        if not tree:
            return {
                'has_errors': True,
                'error_details': ['Failed to parse JavaScript code']
            }
        
        result = {
            'has_errors': False,
            'error_details': [],
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': [],
            'variables': [],
            'tree': tree  # Add the tree to the result dictionary
        }
        
        self._extract_functions(tree, result)
        self._extract_classes(tree, result)
        self._extract_imports(tree, result)
        self._extract_exports(tree, result)
        
        return result
    except Exception as e:
        self.logger.error(f"Failed to analyze JavaScript code: {str(e)}")
        return {
            'has_errors': True,
            'error_details': [str(e)]
        } 