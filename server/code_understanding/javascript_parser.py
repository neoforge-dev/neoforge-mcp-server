"""JavaScript parser using tree-sitter."""

from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from tree_sitter import Language, Parser, Node
import subprocess
import os

class JavaScriptParser:
    """Parser for JavaScript code using tree-sitter."""
    
    def __init__(self):
        """Initialize the JavaScript parser."""
        # Initialize parser
        self.parser = Parser()
        
        try:
            # Load the language from the vendor directory
            vendor_path = Path(__file__).parent.parent.parent / 'vendor' / 'tree-sitter-javascript'
            language_lib = str(vendor_path / 'src' / 'tree-sitter-javascript.so')
            
            # Clone the repository if it doesn't exist
            if not os.path.exists(vendor_path):
                subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-javascript.git', str(vendor_path)], check=True)
            
            # Build the language library if it doesn't exist
            if not os.path.exists(language_lib):
                os.makedirs(os.path.dirname(language_lib), exist_ok=True)
                subprocess.run(['cc', '-fPIC', '-c', str(vendor_path / 'src' / 'parser.c'), '-o', str(vendor_path / 'src' / 'parser.o')], check=True)
                subprocess.run(['cc', '-fPIC', '-c', str(vendor_path / 'src' / 'scanner.c'), '-o', str(vendor_path / 'src' / 'scanner.o')], check=True)
                subprocess.run(['cc', '-shared', str(vendor_path / 'src' / 'parser.o'), str(vendor_path / 'src' / 'scanner.o'), '-o', language_lib], check=True)
            
            # Load the language
            self.language = Language(language_lib, 'javascript')
            self.parser.set_language(self.language)
            
            # Initialize queries
            self.import_query = """
            (import_statement
              (string) @source
              (import_clause
                (named_imports
                  (import_specifier
                    (identifier) @specifier))))
            """
            
            self.export_query = """
            (export_statement
              (variable_declaration
                (variable_declarator
                  (identifier) @export_name)))
            (export_statement
              (function_declaration
                (identifier) @export_name))
            (export_statement
              (class_declaration
                (identifier) @export_name))
            (export_statement
              (export_clause
                (export_specifier
                  (identifier) @export_name)))
            """
            
            self.require_query = """
            (call_expression
              (identifier) @require
              (arguments (string) @source))
            """
            
            self.symbol_query = """
            (function_declaration
              (identifier) @function)
            (class_declaration
              (identifier) @class)
            (variable_declaration
              (variable_declarator
                (identifier) @variable))
            (method_definition
              (property_identifier) @method)
            (arrow_function
              (identifier) @function)
            (pair
              (property_identifier) @property)
            """
            
        except Exception as e:
            print(f"Error loading JavaScript language: {e}")
            raise
    
    def parse(self, code: str) -> Optional[Node]:
        """Parse JavaScript code and return the syntax tree."""
        try:
            if not code.strip():
                return None
                
            tree = self.parser.parse(bytes(code, 'utf8'))
            root = tree.root_node
            
            # Check if the tree has any errors
            if root.has_error:
                return None
                
            return root
        except Exception as e:
            print(f"Error parsing code: {e}")
            return None
    
    def get_imports(self, node: Node) -> List[Dict[str, Any]]:
        """Extract import statements from the syntax tree."""
        imports = []
        query = self.language.query(self.import_query)
        captures = query.captures(node)
        
        current_import = {}
        for capture in captures:
            node, capture_name = capture
            if capture_name == 'source':
                source = node.text.decode('utf8').strip('"\'')
                if current_import:
                    current_import['source'] = source
                    imports.append(current_import)
                    current_import = {}
                else:
                    current_import = {'source': source}
            elif capture_name == 'specifier':
                current_import['specifier'] = node.text.decode('utf8')
        
        if current_import:
            imports.append(current_import)
        
        return imports
    
    def get_exports(self, node: Node) -> List[Dict[str, Any]]:
        """Extract export statements from the syntax tree."""
        exports = []
        query = self.language.query(self.export_query)
        captures = query.captures(node)
        
        for capture in captures:
            node, capture_name = capture
            if capture_name == 'export_name':
                exports.append({
                    'name': node.text.decode('utf8'),
                    'type': node.parent.parent.type
                })
        
        return exports
    
    def get_requires(self, node: Node) -> List[Dict[str, Any]]:
        """Extract require statements from the syntax tree."""
        requires = []
        query = self.language.query(self.require_query)
        captures = query.captures(node)
        
        current_require = {}
        for capture in captures:
            node, capture_name = capture
            if capture_name == 'require':
                current_require = {}
            elif capture_name == 'source':
                source = node.text.decode('utf8').strip('"\'')
                current_require['source'] = source
                requires.append(current_require)
                current_require = {}
        
        return requires
    
    def get_symbols(self, node: Node) -> List[Dict[str, Any]]:
        """Extract symbol declarations from the syntax tree."""
        symbols = []
        query = self.language.query(self.symbol_query)
        captures = query.captures(node)
        
        for capture in captures:
            node, capture_name = capture
            symbols.append({
                'name': node.text.decode('utf8'),
                'type': capture_name,
                'start': node.start_point,
                'end': node.end_point
            })
        
        return symbols 