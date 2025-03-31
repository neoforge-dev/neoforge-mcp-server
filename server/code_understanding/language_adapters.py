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
from .common_types import MockTree, MockNode

logger = logging.getLogger(__name__)

# Define paths to language libraries
JAVASCRIPT_LANGUAGE_PATH = os.path.join(os.path.dirname(__file__), 'build', 'languages.so')

# Define Tree-sitter query strings (or load from .scm files)
JS_IMPORT_QUERY = """
(import_statement) @import
"""

# Query for require() call - run on the call_expression node
JS_REQUIRE_QUERY = """
(call_expression
  function: (identifier) @require
  (#eq? @require "require"))
"""

# Query for async functions
JS_ASYNC_QUERY = """
(function_declaration
  "async") @function
(method_definition
  "async") @method
"""

# Query for export statements
JS_EXPORT_QUERY = """
(export_statement) @export
"""

# Query for destructuring patterns
JS_DESTRUCTURING_QUERY = """
(object_pattern) @object_pattern
"""

# Query for template literals
JS_TEMPLATE_QUERY = """
(template_string) @template
"""

# Query for class features
JS_CLASS_QUERY = """
(class_declaration) @class
"""

class JavaScriptParserAdapter:
    """JavaScript parser adapter using tree-sitter for robust parsing."""
    
    def __init__(self):
        """Initialize the JavaScript parser adapter."""
        self.logger = logging.getLogger(__name__)
        self.parser = Parser()
        self.language = None
        # Store compiled queries if needed for conversion
        self.import_query = None
        self.require_query = None
        self.async_query = None
        self.export_query = None
        self.destructuring_query = None
        self.template_query = None
        self.class_query = None
        # Add others like symbol_query if needed
        self._load_language_and_queries()
        
    def _load_language_and_queries(self):
        """Load JavaScript language and compile queries."""
        try:
            # Load the JavaScript language from the built library
            from tree_sitter import Language
            
            # Check if the language file exists
            if not os.path.exists(JAVASCRIPT_LANGUAGE_PATH):
                # Build the language file if it doesn't exist
                build_dir = os.path.join(os.path.dirname(__file__), 'build')
                os.makedirs(build_dir, exist_ok=True)
                
                # Clone the tree-sitter-javascript repository if needed
                vendor_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vendor')
                os.makedirs(vendor_dir, exist_ok=True)
                js_repo_path = os.path.join(vendor_dir, 'tree-sitter-javascript')
                
                if not os.path.exists(js_repo_path):
                    subprocess.run(['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-javascript.git', js_repo_path], check=True)
                
                # Build the language
                Language.build_library(
                    JAVASCRIPT_LANGUAGE_PATH,
                    [js_repo_path]
                )
            
            self.language = Language(JAVASCRIPT_LANGUAGE_PATH, 'javascript')
            self.parser.set_language(self.language)
            logger.info("JavaScript language loaded successfully.")

            # Define queries for JavaScript features
            query_strings = {
                'JS_IMPORT_QUERY': """
                    (import_statement
                        source: (string) @source
                        (import_clause
                            (identifier) @default_import)?
                        (named_imports
                            (import_specifier
                                name: (identifier) @named_import))?
                        (namespace_import
                            (identifier) @namespace)?
                    )
                """,
                'JS_REQUIRE_QUERY': """
                    (variable_declaration
                        (variable_declarator
                            name: (identifier) @name
                            value: (call_expression
                                function: (identifier) @require
                                arguments: (arguments
                                    (string) @source)
                                (#eq? @require "require"))))
                """,
                'JS_ASYNC_QUERY': """
                    (function_declaration
                        "async" @async
                        name: (identifier) @name)
                    (method_definition
                        "async" @async
                        name: (property_identifier) @name)
                    (arrow_function
                        "async" @async)
                """,
                'JS_EXPORT_QUERY': """
                    (export_statement
                        "default" @default?
                        declaration: [
                            (class_declaration
                                name: (identifier) @name)
                            (function_declaration
                                name: (identifier) @name)
                            (identifier) @name
                        ]?
                        (export_clause
                            (export_specifier
                                name: (identifier) @name))?
                    )
                """,
                'JS_CLASS_QUERY': """
                    (class_declaration
                        name: (identifier) @name
                        body: (class_body
                            (method_definition
                                "static" @static?
                                "async" @async?
                                name: (property_identifier) @method_name)?))
                """,
                'JS_VARIABLE_QUERY': """
                    (variable_declaration
                        (variable_declarator
                            name: (identifier) @name))
                """
            }

            # Compile queries
            self.queries = {}
            for name, query_string in query_strings.items():
                try:
                    # Remove any extra whitespace and newlines
                    query_string = query_string.strip()
                    self.queries[name] = self.language.query(query_string)
                    logger.debug(f"Compiled query {name}")
                except Exception as e:
                    logger.error(f"Error compiling query {name}: {e}")
                    raise

            logger.info("JavaScript queries compiled.")
        except Exception as e:
            logger.error(f"Error loading JavaScript language or queries: {e}")
            raise

    def parse(self, code: str) -> MockTree:
        """Parse JavaScript code using tree-sitter."""
        try:
            if not code.strip():
                return MockTree(
                    features={
                        'imports': [],
                        'functions': [],
                        'classes': [],
                        'variables': set(),  # Use a set to avoid duplicates
                        'exports': [],
                        'has_errors': False,
                        'error_details': []
                    }
                )

            logger.debug("Parsing code with tree-sitter")
            tree = self.parser.parse(bytes(code, 'utf-8'))
            root = tree.root_node
            logger.debug(f"Root node type: {root.type}")

            if root.type != 'program':
                raise ValueError(f"Expected program node, got {root.type}")

            # Initialize results
            results = {
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': set(),  # Use a set to avoid duplicates
                'exports': [],
                'has_errors': False,
                'error_details': []
            }

            def visit_node(node):
                try:
                    if node.type == 'import_statement':
                        # Handle ES6 imports
                        source_node = node.child_by_field_name('source')
                        if source_node:
                            source = source_node.text.decode('utf-8').strip("'\"")
                            
                            # Check for default import
                            import_clause = node.child_by_field_name('import_clause')
                            if import_clause:
                                # Handle default import
                                if import_clause.type == 'identifier':
                                    results['imports'].append({
                                        'name': import_clause.text.decode('utf-8'),
                                        'type': 'import',
                                        'module': source,
                                        'is_default': True
                                    })
                                else:
                                    # Handle named imports
                                    named_imports = import_clause.child_by_field_name('named_imports')
                                    if named_imports:
                                        for specifier in named_imports.named_children:
                                            if specifier.type == 'import_specifier':
                                                name = None
                                                for child in specifier.named_children:
                                                    if child.type == 'identifier':
                                                        name = child
                                                        break
                                                if name:
                                                    results['imports'].append({
                                                        'name': name.text.decode('utf-8'),
                                                        'type': 'import',
                                                        'module': source,
                                                        'is_default': False
                                                    })
                                    # Handle default import in named imports
                                    default_import = import_clause.child_by_field_name('name')
                                    if default_import:
                                        results['imports'].append({
                                            'name': default_import.text.decode('utf-8'),
                                            'type': 'import',
                                            'module': source,
                                            'is_default': True
                                        })

                    elif node.type == 'call_expression':
                        # Handle require() calls and dynamic imports
                        func = node.child_by_field_name('function')
                        if func:
                            func_text = func.text.decode('utf-8')
                            if func_text == 'require':
                                args = node.child_by_field_name('arguments')
                                if args and args.named_children:
                                    source = args.named_children[0].text.decode('utf-8').strip("'\"")
                                    # Get the variable name from the parent node
                                    parent = node.parent
                                    if parent and parent.type == 'variable_declarator':
                                        name_node = parent.child_by_field_name('name')
                                        if name_node:
                                            name = name_node.text.decode('utf-8')
                                            results['imports'].append({
                                                'name': name,
                                                'type': 'require',
                                                'module': source,
                                                'is_default': True
                                            })
                            elif func_text == 'import':
                                # Handle dynamic imports
                                args = node.child_by_field_name('arguments')
                                if args and args.named_children:
                                    source = args.named_children[0].text.decode('utf-8').strip("'\"")
                                    parent = node.parent
                                    if parent and parent.type == 'variable_declarator':
                                        name_node = parent.child_by_field_name('name')
                                        if name_node:
                                            name = name_node.text.decode('utf-8')
                                            results['imports'].append({
                                                'name': name,
                                                'type': 'dynamic_import',
                                                'module': source,
                                                'is_default': True
                                            })

                    elif node.type == 'function_declaration':
                        # Handle function declarations
                        name = node.child_by_field_name('name')
                        if name:
                            func_info = {
                                'name': name.text.decode('utf-8'),
                                'is_async': 'async' in node.text.decode('utf-8'),
                                'is_method': False,
                                'is_arrow': False
                            }
                            results['functions'].append(func_info)

                    elif node.type == 'arrow_function':
                        # Handle arrow functions
                        parent = node.parent
                        if parent and parent.type == 'variable_declarator':
                            name = parent.child_by_field_name('name')
                            if name:
                                func_info = {
                                    'name': name.text.decode('utf-8'),
                                    'is_async': 'async' in node.text.decode('utf-8'),
                                    'is_method': False,
                                    'is_arrow': True
                                }
                                results['functions'].append(func_info)

                    elif node.type == 'method_definition':
                        # Handle class methods
                        name = node.child_by_field_name('name')
                        if name:
                            method_info = {
                                'name': name.text.decode('utf-8'),
                                'is_async': 'async' in node.text.decode('utf-8'),
                                'is_method': True,
                                'is_static': 'static' in node.text.decode('utf-8'),
                                'is_private': name.text.decode('utf-8').startswith('#')
                            }
                            # Add to the current class's methods
                            if results['classes']:
                                results['classes'][-1]['methods'].append(method_info)

                    elif node.type == 'class_declaration':
                        # Handle class declarations
                        name = node.child_by_field_name('name')
                        if name:
                            class_info = {
                                'name': name.text.decode('utf-8'),
                                'methods': [],
                                'fields': [],
                                'decorators': []
                            }
                            # Check for decorators
                            if node.prev_sibling and node.prev_sibling.type == 'decorator':
                                class_info['decorators'].append({
                                    'name': node.prev_sibling.child_by_field_name('name').text.decode('utf-8')
                                })
                            results['classes'].append(class_info)

                    elif node.type == 'field_definition':
                        # Handle class fields
                        name = node.child_by_field_name('name')
                        if name:
                            field_info = {
                                'name': name.text.decode('utf-8'),
                                'is_static': 'static' in node.text.decode('utf-8'),
                                'is_private': name.text.decode('utf-8').startswith('#'),
                                'has_decorator': bool(node.prev_sibling and node.prev_sibling.type == 'decorator')
                            }
                            if results['classes']:
                                results['classes'][-1]['fields'].append(field_info)

                    elif node.type == 'lexical_declaration':
                        # Handle variable declarations (const/let)
                        kind = node.child_by_field_name('kind') or node.named_children[0]
                        is_const = kind and kind.text.decode('utf-8') == 'const'
                        
                        for declarator in node.named_children:
                            if declarator.type == 'variable_declarator':
                                name = declarator.child_by_field_name('name')
                                value = declarator.child_by_field_name('value')
                                
                                # Skip require() calls as they're handled as imports
                                if value and value.type == 'call_expression':
                                    func = value.child_by_field_name('function')
                                    if func and func.text.decode('utf-8') == 'require':
                                        continue
                                
                                if name:
                                    var_info = {
                                        'name': name.text.decode('utf-8'),
                                        'is_const': is_const,
                                        'has_decorator': bool(node.prev_sibling and node.prev_sibling.type == 'decorator')
                                    }
                                    results['variables'].add(json.dumps(var_info))  # Convert to JSON for set storage

                    elif node.type == 'export_statement':
                        # Handle export statements
                        decl = node.child_by_field_name('declaration')
                        if decl:
                            if decl.type == 'class_declaration':
                                name = decl.child_by_field_name('name')
                                if name:
                                    results['exports'].append({
                                        'name': name.text.decode('utf-8'),
                                        'is_default': 'default' in node.text.decode('utf-8')
                                    })
                            elif decl.type == 'lexical_declaration':
                                # Handle exported variables
                                kind = decl.child_by_field_name('kind') or decl.named_children[0]
                                is_const = kind and kind.text.decode('utf-8') == 'const'
                                
                                for declarator in decl.named_children:
                                    if declarator.type == 'variable_declarator':
                                        name = declarator.child_by_field_name('name')
                                        if name:
                                            var_name = name.text.decode('utf-8')
                                            # Add to exports
                                            results['exports'].append({
                                                'name': var_name,
                                                'is_default': False
                                            })
                                            # Add to variables
                                            var_info = {
                                                'name': var_name,
                                                'is_const': is_const
                                            }
                                            results['variables'].add(json.dumps(var_info))  # Convert to JSON for set storage
                        else:
                            # Handle named exports without declaration
                            export_clause = node.child_by_field_name('export_clause')
                            if export_clause:
                                for specifier in export_clause.named_children:
                                    if specifier.type == 'export_specifier':
                                        name = specifier.child_by_field_name('name')
                                        if name:
                                            results['exports'].append({
                                                'name': name.text.decode('utf-8'),
                                                'is_default': False
                                            })

                except Exception as e:
                    logger.error(f"Error processing node {node.type}: {e}")
                    results['has_errors'] = True
                    results['error_details'].append({
                        'message': f"Error processing node {node.type}: {str(e)}",
                        'node_type': node.type,
                        'node_text': node.text.decode('utf-8'),
                        'line': node.start_point[0] + 1,
                        'column': node.start_point[1] + 1
                    })

            # Visit all nodes in the tree using a proper tree traversal
            def traverse_tree(node):
                visit_node(node)
                for child in node.children:
                    traverse_tree(child)

            traverse_tree(root)

            # Convert variables set back to list
            results['variables'] = [json.loads(var_info) for var_info in results['variables']]

            # Create MockTree with features
            return MockTree(
                root_node=MockNode(type='program', text='program'),
                has_errors=results['has_errors'],
                error_details=results['error_details'],
                features=results
            )

        except Exception as e:
            logger.error(f"Error parsing JavaScript code: {e}")
            return MockTree(
                features={
                    'imports': [],
                    'functions': [],
                    'classes': [],
                    'variables': [],
                    'exports': [],
                    'has_errors': True,
                    'error_details': [{'message': str(e)}]
                }
            )

    def _tree_sitter_to_mock_node(self, node: Any) -> MockNode:
        """Convert a tree-sitter node to a MockNode."""
        try:
            if not node:
                return None

            # Get node type and text
            node_type = node.type
            node_text = node.text.decode('utf-8') if isinstance(node.text, bytes) else str(node.text)
            
            # Create fields dictionary
            fields = {}
            cursor = node.walk()
            
            # Get all fields
            if cursor.goto_first_child():
                while True:
                    field_name = cursor.field_name()
                    if field_name:
                        fields[field_name] = self._tree_sitter_to_mock_node(cursor.node())
                    if not cursor.goto_next_sibling():
                        break
                cursor.goto_parent()
            
            # Add feature-specific metadata
            metadata = {}
            
            # Handle async functions
            if node_type in ['async_function_declaration', 'async_method_definition', 'async_arrow_function']:
                metadata['is_async'] = True
            
            # Handle exports
            if node_type == 'export_statement':
                metadata['is_export'] = True
                if node.child_by_field_name('declaration'):
                    metadata['is_default'] = False
                elif node.child_by_field_name('specifiers'):
                    specifiers = node.child_by_field_name('specifiers')
                    if specifiers.type == 'namespace_export':
                        metadata['is_namespace'] = True
                        metadata['source_module'] = node.child_by_field_name('source').text.decode('utf-8')
                    else:
                        metadata['is_default'] = False
                        metadata['source_module'] = node.child_by_field_name('source').text.decode('utf-8') if node.child_by_field_name('source') else None
            
            # Handle destructuring
            if node_type in ['object_pattern', 'array_pattern']:
                metadata['is_destructured'] = True
            elif node_type == 'rest_pattern':
                metadata['is_rest'] = True
            
            # Handle template literals
            if node_type == 'template_literal':
                metadata['is_template_literal'] = True
            elif node_type == 'template_substitution':
                metadata['is_template_substitution'] = True
            
            # Handle class features
            if node_type == 'class_declaration':
                metadata['is_class'] = True
                name_node = node.child_by_field_name('name')
                if name_node:
                    metadata['class_name'] = name_node.text.decode('utf-8')
            elif node_type == 'method_definition':
                method_name = node.child_by_field_name('name').text.decode('utf-8')
                metadata['method_name'] = method_name
                if method_name.startswith('#'):
                    metadata['is_private'] = True
                elif method_name == 'constructor':
                    metadata['is_constructor'] = True
                elif method_name.startswith('get '):
                    metadata['is_getter'] = True
                elif method_name.startswith('set '):
                    metadata['is_setter'] = True
                elif node.parent and node.parent.type == 'class_body' and node.parent.parent and node.parent.parent.type == 'class_declaration':
                    metadata['is_static'] = node.child_by_field_name('static') is not None
            
            # Create MockNode with metadata
            mock_node = MockNode(
                type=node_type,
                text=node_text,
                fields=fields,
                metadata=metadata
            )
            
            return mock_node
            
        except Exception as e:
            self.logger.error(f"Error converting tree-sitter node: {e}")
            return None

    def _cleanup_temp_files(self, temp_dir: Path) -> None:
        """Clean up temporary files created during grammar building.
        
        Args:
            temp_dir: Path to the temporary directory to clean up.
        """
        try:
            if temp_dir.exists():
                for file in temp_dir.glob('**/*'):
                    if file.is_file():
                        file.unlink()
                for dir in reversed(list(temp_dir.glob('**/*'))):
                    if dir.is_dir():
                        dir.rmdir()
                temp_dir.rmdir()
                logger.info(f"Cleaned up temporary files in {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")

    @property
    def version(self) -> Optional[str]:
        """Get the version of the JavaScript grammar.
        
        Returns:
            str: Version string from package.json, or None if not available.
        """
        try:
            if self.language:
                vendor_path = Path(__file__).parent.parent.parent / 'vendor' / 'tree-sitter-javascript'
                package_json = vendor_path / 'package.json'
                if package_json.exists():
                    import json
                    with open(package_json) as f:
                        data = json.load(f)
                        return data.get('version')
            return None
        except Exception as e:
            logger.error(f"Error getting grammar version: {e}")
            return None

    def analyze(self, code: str) -> Dict[str, Any]:
        """Analyze JavaScript code and return extracted information."""
        try:
            mock_tree = self.parse(code)
            if not mock_tree:
                return {'error': 'Failed to parse JavaScript code'}

            return {
                'imports': mock_tree.imports,
                'exports': mock_tree.exports,
                'functions': mock_tree.functions,
                'classes': mock_tree.classes,
                'variables': mock_tree.variables
            }

        except Exception as e:
            logger.error(f"Error analyzing JavaScript code: {str(e)}")
            return {'error': str(e)}

class SwiftParserAdapter:
    def parse(self, code: str) -> Optional[MockTree]:
        if not code or code.strip() == '':
            raise ValueError("Input code cannot be empty or whitespace only.")
        # For now, bypass validation and return a mock tree with a 'source_file' root node
        logger.warning("Swift parsing not implemented, returning basic mock tree.")
        root = MockNode(type='source_file', text='source_file')
        return MockTree(root) 