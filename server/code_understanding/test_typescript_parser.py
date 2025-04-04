"""Tests for essential TypeScript parsing support in the JavaScript parser adapter."""

import unittest
import os
from pathlib import Path
import sys
import subprocess
import pytest
import logging

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tree_sitter import Language, Parser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestTypeScriptParser(unittest.TestCase):
    """Test class for essential TypeScript parsing support."""
    
    @classmethod
    def setUpClass(cls):
        # Clone and build the TypeScript grammar
        ts_dir = Path(__file__).parent / "tree-sitter-typescript"
        if not ts_dir.exists():
            subprocess.run(["git", "clone", "https://github.com/tree-sitter/tree-sitter-typescript.git"], cwd=Path(__file__).parent)
        
        # Build the TypeScript language
        Language.build_library(
            str(Path(__file__).parent / "build/my-languages.so"),
            [str(ts_dir / "typescript")]
        )
        
        # Load the TypeScript language
        cls.TYPESCRIPT_LANGUAGE = Language(str(Path(__file__).parent / "build/my-languages.so"), "typescript")
    
    def setUp(self):
        """Set up the test environment."""
        self.parser = Parser()
        self.parser.set_language(self.TYPESCRIPT_LANGUAGE)
        self.test_file = os.path.join(os.path.dirname(__file__), 'test_files', 'typescript_features.ts')
        
    def test_parse_typescript_features(self):
        """Test parsing of essential TypeScript features."""
        with open(self.test_file, 'r') as f:
            source_code = f.read()
        
        tree = self.parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node
        
        # Test interface declarations
        interface_nodes = self._find_nodes_by_type(root_node, 'interface_declaration')
        self.assertEqual(len(interface_nodes), 1)
        interface_node = interface_nodes[0]
        self.assertEqual(interface_node.child_by_field_name('name').text.decode('utf8'), 'UserInterface')
        
        # Test type declarations
        type_nodes = self._find_nodes_by_type(root_node, 'type_alias_declaration')
        self.assertEqual(len(type_nodes), 1)
        type_node = type_nodes[0]
        self.assertEqual(type_node.child_by_field_name('name').text.decode('utf8'), 'UserType')
        
        # Test enum declarations
        enum_nodes = self._find_nodes_by_type(root_node, 'enum_declaration')
        self.assertEqual(len(enum_nodes), 1)
        enum_node = enum_nodes[0]
        self.assertEqual(enum_node.child_by_field_name('name').text.decode('utf8'), 'UserRole')
        
        # Test function declarations
        function_nodes = self._find_nodes_by_type(root_node, 'function_declaration')
        self.assertEqual(len(function_nodes), 1)
        function_node = function_nodes[0]
        self.assertEqual(function_node.child_by_field_name('name').text.decode('utf8'), 'processUser')
        
        # Test variable declarations
        variable_nodes = self._find_nodes_by_type(root_node, 'variable_declaration')
        self.assertEqual(len(variable_nodes), 1)
        variable_node = variable_nodes[0]
        declarator = variable_node.child_by_field_name('declarator')
        self.assertEqual(declarator.child_by_field_name('name').text.decode('utf8'), 'testUser')
    
    def _find_nodes_by_type(self, root_node, type_name):
        nodes = []
        cursor = root_node.walk()
        
        def visit(node):
            if node.type == type_name:
                nodes.append(node)
            return True
        
        cursor.reset(root_node)
        cursor.visit(visit)
        return nodes

if __name__ == '__main__':
    unittest.main() 