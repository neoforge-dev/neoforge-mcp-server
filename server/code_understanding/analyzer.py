"""Module for analyzing Python code."""

import ast
import logging
from typing import Dict, List, Optional, Set, Any, Union
import os
import re

from tree_sitter import Tree
from .parser import CodeParser
# Import common types
from .common_types import MockNode, MockTree
# Import language adapters
from .language_adapters import JavaScriptParserAdapter, SwiftParserAdapter
from .graph import Node

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzer for Python code."""

    def __init__(self):
        """Initialize the analyzer."""
        self.parser = CodeParser()
        self.imports = []
        self.functions = []
        self.classes = []
        self.variables = []
        self.exports = []
        self.error_details = []
        self.current_class = []
        self.language = None

    def reset_state(self):
        """Reset the analyzer state for a new analysis."""
        self.imports = []
        self.functions = []
        self.classes = []
        self.variables = []
        self.exports = []
        self.error_details = []
        self.current_class = []  # Stack of classes being processed

    def _detect_language(self, code: str) -> Optional[str]:
        """Detect the programming language of the code.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Detected language identifier or None if unknown
        """
        # Look for language-specific patterns
        if 'import' in code and ('def ' in code or 'class ' in code):
            return 'python'
        elif ('function' in code or 'class' in code) and ('{' in code and '}' in code):
            return 'javascript'
        return None

    def analyze_code(self, code: str, language: str = None) -> Dict[str, Any]:
        """Analyze code and extract features based on language.
        
        Args:
            code: Source code to analyze
            language: Optional language identifier. If None, will try to detect.
            
        Returns:
            Dict with extracted code features
        """
        logger.info(f"Analyzing code with language {language}")
        
        # Reset state
        self.reset_state()
        
        if not code or not code.strip():
            self.error_details.append({'message': 'Empty code'})
            return {
                'language': language,
                'imports': self.imports,
                'functions': self.functions,
                'classes': self.classes,
                'variables': self.variables,
                'exports': self.exports,
                'has_errors': True,
                'error_details': self.error_details,
                'errors': self.error_details
            }
            
        # Detect language if not provided
        if not language:
            language = self._detect_language(code)
            logger.info(f"Detected language: {language}")
            # Handle case where language detection fails
            if not language:
                logger.warning("Could not detect language. Analysis cannot proceed.")
                self.error_details.append({'message': 'Could not detect language'})
                return {
                    'language': None,
                    'imports': self.imports,
                    'functions': self.functions,
                    'classes': self.classes,
                    'variables': self.variables,
                    'exports': self.exports,
                    'has_errors': True,
                    'error_details': self.error_details,
                    'errors': self.error_details
                }

        self.language = language # Store the determined language

        try:
            if language == 'javascript':
                adapter = JavaScriptParserAdapter()
                analysis_result = adapter.analyze(code)
            elif language == 'swift':
                adapter = SwiftParserAdapter()
                analysis_result = adapter.analyze(code)
            elif language == 'python':
                # Handle Python using the internal parser and extraction methods
                tree = self.parser.parse(code, language='python')
                if tree and tree.root_node:
                    # Assuming _extract_ methods work with the parser's output tree
                    self.imports = self._extract_imports(tree.root_node)
                    self.functions = self._extract_functions(tree.root_node)
                    self.classes = self._extract_classes(tree.root_node)
                    self.variables = self._extract_variables(tree.root_node)
                    # Exports are generally not a Python concept in the same way
                    self.exports = [] 
                    # Check for errors on the tree if the parser provides this
                    has_errors = getattr(tree, 'has_errors', False) 
                    if has_errors:
                         # Attempt to get detailed errors if available
                         self.error_details.extend(getattr(tree, 'errors', [{'message': 'Syntax error detected by parser'}]))
                else:
                    has_errors = True
                    self.error_details.append({'message': 'Python parsing failed or returned empty tree'})

                analysis_result = {
                    'imports': self.imports,
                    'functions': self.functions,
                    'classes': self.classes,
                    'variables': self.variables,
                    'exports': self.exports,
                    'has_errors': has_errors,
                    'error_details': self.error_details, # Keep for compatibility if needed
                    'errors': self.error_details # Standardized errors key
                }
            else:
                # No adapter or handler found for the language
                logger.warning(f"No specific handler found for language: {language}. Analysis might be incomplete.")
                self.error_details.append({'message': f'Unsupported language: {language}'})
                analysis_result = {
                    'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': [],
                    'has_errors': True, 'error_details': self.error_details, 'errors': self.error_details
                }
            
            # Add language info to the final result
            analysis_result['language'] = language
            return analysis_result

        except Exception as e:
            logger.exception(f"Error analyzing code for language {language}: {e}")
            self.error_details.append({'message': str(e), 'type': type(e).__name__})
            return {
                'language': language,
                'imports': self.imports, # Return partially gathered data if any
                'functions': self.functions,
                'classes': self.classes,
                'variables': self.variables,
                'exports': self.exports,
                'has_errors': True,
                'error_details': self.error_details, # Keep original key for now
                'errors': self.error_details # Add new key too
            }

    def analyze_file(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a source code file.
        
        Args:
            file_path: Path to the source code file.
            language: Optional language override. If not provided, inferred from file extension.
            
        Returns:
            Dict containing analysis results with the following structure:
            {
                'has_errors': bool,
                'error_details': List[Dict[str, str]],
                'imports': List[Dict],
                'functions': List[Dict],
                'classes': List[Dict],
                'variables': List[Dict],
                'exports': List[Dict]
            }
        """
        # Input validation
        if not file_path:
            return {
                'has_errors': True,
                'error_details': [{"message": "File path cannot be empty"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        
        # Check file existence
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Infer language from file extension if not provided
        if not language:
            ext = os.path.splitext(file_path)[1].lower()
            language = {
                '.py': 'python',
                '.js': 'javascript',
                '.swift': 'swift'
            }.get(ext)
            if not language:
                return {
                    'has_errors': True,
                    'error_details': [{"message": f"Could not determine language for file: {file_path}"}],
                    'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
                }
        
        # Read and analyze file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.analyze_code(code, language)
        except UnicodeDecodeError:
            return {
                'has_errors': True,
                'error_details': [{"message": f"File {file_path} is not valid UTF-8"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        except IOError as e:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Error reading file {file_path}: {str(e)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }
        except Exception as e:
            return {
                'has_errors': True,
                'error_details': [{"message": f"Unexpected error analyzing file {file_path}: {str(e)}"}],
                'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': []
            }

    def analyze_directory(self, directory_path):
        """Analyze all Python files in a directory.

        Args:
            directory_path (str): Path to the directory to analyze.

        Returns:
            list: A list of dictionaries, each containing analysis results for a file:
                - file (str): The file path
                - imports (list): List of import information
                - functions (list): List of function information
                - classes (list): List of class information
                - variables (list): List of variable information

        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")

        results = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        analysis = self.analyze_file(file_path)
                        analysis['file'] = file_path
                        results.append(analysis)
                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {str(e)}")

        return results

    def _extract_imports(self, root):
        """Extract import statements from the MockTree root node."""
        imports = []
        logger.debug(f"[_extract_imports] Starting. Root children count: {len(root.children) if root and hasattr(root, 'children') else 'N/A'}")
        if not root or not hasattr(root, 'children'):
            logger.debug("[_extract_imports] Root is None or has no children.")
            return imports

        for i, node in enumerate(root.children):
            logger.debug(f"[_extract_imports] Processing root child {i}: type='{node.type}'")
            
            # Handle Swift-style import nodes (from our MockParser)
            if node.type == 'import_declaration':
                logger.debug(f"  Found 'import_declaration' node from MockParser")
                # Extract module name from import_path_component child
                for child in node.children:
                    if child.type == 'import_path_component':
                        # This is the module name
                        module_name = getattr(child, 'text', '')
                        if module_name:
                            imports.append({
                                'type': 'import',
                                'module': module_name,
                                'alias': None,  # No alias in this format
                                'start_line': node.start_point[0] + 1,
                                'end_line': node.end_point[0] + 1
                            })
                            logger.debug(f"    Found import: module='{module_name}'")
            
            # Handle our MockParser 'import' type added for Python
            elif node.type == 'import': # Handles 'import module' or 'import module as alias'
                logger.debug(f"  Found 'import' node. Children count: {len(node.children)}")
                # Children are 'alias' nodes
                for j, alias_node in enumerate(node.children):
                    logger.debug(f"    Processing alias child {j}: type='{alias_node.type}', fields: {hasattr(alias_node, 'fields')}")
                    if alias_node.type == 'alias' and hasattr(alias_node, 'fields') and alias_node.fields:
                        name_node = alias_node.fields.get('name')
                        asname_node = alias_node.fields.get('asname')
                        name_text = getattr(name_node, 'text', '[N/A]')
                        asname_text = getattr(asname_node, 'text', '[N/A]') if asname_node else None
                        logger.debug(f"      Extracted name='{name_text}', asname='{asname_text}'")
                        if name_node: # Check if name_node itself exists
                            imports.append({
                                'type': 'import',
                                'module': getattr(name_node, 'text', ''),
                                'alias': getattr(asname_node, 'text', None) if asname_node else None,
                                'start_line': node.start_point[0] + 1,
                                'end_line': node.end_point[0] + 1
                            })
                        else:
                            logger.warning(f"      Skipped alias node {j} due to missing 'name' field.")
                    else:
                        logger.warning(f"    Skipped alias child {j}: type mismatch or no fields.")
            
            # Handle 'from module import' type that uses 'module' node type
            elif node.type == 'module': # Handles 'from module import name' or 'from module import name as alias'
                logger.debug(f"  Found 'module' node (represents ImportFrom). Fields: {hasattr(node, 'fields')}")
                # 'module' type node represents the 'from' part in MockParser
                module_field = node.fields.get('module') if hasattr(node, 'fields') else None
                names_field = node.fields.get('names') if hasattr(node, 'fields') else None
                
                source_module = getattr(module_field, 'text', '[N/A]') if module_field else ''
                logger.debug(f"    Source module: '{source_module}'")
                
                if names_field and isinstance(names_field, list):
                    logger.debug(f"    Found 'names' field (list). Count: {len(names_field)}")
                    # Names are a list of 'alias' nodes
                    for k, alias_node in enumerate(names_field):
                        logger.debug(f"      Processing name alias {k}: type='{alias_node.type}', fields: {hasattr(alias_node, 'fields')}")
                        if alias_node.type == 'alias' and hasattr(alias_node, 'fields') and alias_node.fields:
                            name_node = alias_node.fields.get('name')
                            asname_node = alias_node.fields.get('asname')
                            name_text = getattr(name_node, 'text', '[N/A]')
                            asname_text = getattr(asname_node, 'text', '[N/A]') if asname_node else None
                            logger.debug(f"        Extracted name='{name_text}', asname='{asname_text}'")
                            if name_node:
                                imports.append({
                                    'type': 'from_import',
                                    'module': source_module,
                                    'name': getattr(name_node, 'text', ''),
                                    'alias': getattr(asname_node, 'text', None) if asname_node else None,
                                    'start_line': node.start_point[0] + 1,
                                    'end_line': node.end_point[0] + 1
                                })
                            else:
                                logger.warning(f"        Skipped name alias {k} due to missing 'name' field.")
                        else:
                            logger.warning(f"      Skipped name alias {k}: type mismatch or no fields.")
                else:
                     logger.debug(f"    'names' field not found or not a list.")
                                
        logger.debug(f"[_extract_imports] Finished. Found {len(imports)} imports.")
        return imports

    def _extract_classes(self, root):
        """Extract class definitions from the MockTree root node."""
        classes = []
        logger.debug(f"[_extract_classes] Starting for {root.type if hasattr(root, 'type') else 'unknown'} node")
        
        if not root or not hasattr(root, 'children'):
            return classes
            
        for i, node in enumerate(root.children):
            if not hasattr(node, 'type'):
                continue
            
            logger.debug(f"[_extract_classes] Processing child {i}: type='{node.type}'")
            
            if node.type == 'class_definition':
                logger.debug(f"  Found class_definition node")
                
                # Get class name from fields or children
                class_name = ""
                
                # Try getting name from fields
                if hasattr(node, 'fields') and node.fields and 'name' in node.fields:
                    name_node = node.fields.get('name')
                    if name_node and hasattr(name_node, 'text'):
                        class_name = name_node.text
                        logger.debug(f"    Got class name from fields.name.text: {class_name}")
                
                # Try getting name from first child with type 'identifier'
                if not class_name:
                    for child in node.children:
                        if hasattr(child, 'type') and child.type == 'identifier':
                            if hasattr(child, 'text') and child.text:
                                class_name = child.text
                                logger.debug(f"    Got class name from identifier child: {class_name}")
                                break
                
                # Skip if we couldn't find a name
                if not class_name:
                    logger.warning(f"    Skipped class definition node {i} due to missing 'name'.")
                    continue
                
                # Extract base classes
                bases = []
                
                # Look for inheritance clause in children
                for child in node.children:
                    if hasattr(child, 'type') and child.type == 'inheritance_clause':
                        logger.debug(f"    Found inheritance_clause node")
                        for base_node in child.children:
                            if hasattr(base_node, 'type') and base_node.type == 'type_identifier':
                                if hasattr(base_node, 'text') and base_node.text:
                                    bases.append(base_node.text)
                
                # Create class info
                class_info = {
                    'name': class_name,
                    'bases': bases,
                    'start_line': node.start_point[0] + 1 if hasattr(node, 'start_point') else 0,
                    'end_line': node.end_point[0] + 1 if hasattr(node, 'end_point') else 0,
                    'methods': []
                }
                
                # Extract methods from class body
                class_body = None
                for child in node.children:
                    if hasattr(child, 'type') and child.type == 'class_body':
                        class_body = child
                        break
                
                if class_body and hasattr(class_body, 'children'):
                    logger.debug(f"    Found class_body node with {len(class_body.children)} children")
                    for method_node in class_body.children:
                        if hasattr(method_node, 'type') and method_node.type == 'function_definition':
                            method_name = ""
                            
                            # Try getting name from fields
                            if hasattr(method_node, 'fields') and method_node.fields and 'name' in method_node.fields:
                                name_node = method_node.fields.get('name')
                                if name_node and hasattr(name_node, 'text'):
                                    method_name = name_node.text
                            
                            # Try getting name from text attribute
                            if not method_name and hasattr(method_node, 'text') and method_node.text:
                                method_name = method_node.text
                            
                            # Try getting name from first child with type 'identifier'
                            if not method_name:
                                for c in method_node.children:
                                    if hasattr(c, 'type') and c.type == 'identifier':
                                        if hasattr(c, 'text') and c.text:
                                            method_name = c.text
                                            break
                            
                            if method_name:
                                # Extract parameters
                                parameters = []
                                
                                # Check for parameters in fields
                                if hasattr(method_node, 'fields') and method_node.fields and 'parameters' in method_node.fields:
                                    param_node = method_node.fields.get('parameters')
                                    if param_node and hasattr(param_node, 'children'):
                                        for p in param_node.children:
                                            if hasattr(p, 'text'):
                                                parameters.append({
                                                    'name': p.text,
                                                    'type': 'parameter',  # Default type
                                                })
                                
                                # Create method info
                                method_info = {
                                    'name': method_name,
                                    'parameters': parameters,
                                    'start_line': method_node.start_point[0] + 1 if hasattr(method_node, 'start_point') else 0,
                                    'end_line': method_node.end_point[0] + 1 if hasattr(method_node, 'end_point') else 0,
                                }
                                
                                class_info['methods'].append(method_info)
                                logger.debug(f"    Added method: {method_name}")
                            else:
                                logger.warning(f"    Skipped method node due to missing 'name'.")
                
                # Add class to results
                classes.append(class_info)
                logger.debug(f"  Added class: {class_name} with {len(class_info['methods'])} methods")
                
            # Process nested nodes (but not for functions)
            elif node.type not in ('function_definition'):
                for child in node.children:
                    child_classes = self._extract_classes(child)
                    classes.extend(child_classes)
        
        logger.debug(f"[_extract_classes] Finished. Found {len(classes)} classes")
        return classes

    def _extract_variables(self, root):
        """Extract variable assignments from a node."""
        variables = []
        logger.debug(f"[_extract_variables] Starting. Root children count: {len(root.children) if root and hasattr(root, 'children') else 'N/A'}")
        if not root or not hasattr(root, 'children'):
            logger.debug("[_extract_variables] Root is None or has no children.")
            return variables
            
        for i, node in enumerate(root.children):
            logger.debug(f"[_extract_variables] Processing root child {i}: type='{node.type}'")
            if node.type == 'assignment':
                logger.debug(f"  Found 'assignment' node. Fields: {hasattr(node, 'fields')}")
                left_node = node.fields.get("left") if hasattr(node, 'fields') else None
                right_node = node.fields.get("right") if hasattr(node, 'fields') else None
                left_text = getattr(left_node, 'text', '[N/A]') if left_node else '[N/A]'
                right_text = getattr(right_node, 'text', '[N/A]') if right_node else '[N/A]'
                logger.debug(f"    Left='{left_text}', Right='{right_text}'")
                
                if left_node and right_node:
                    # Safely get text for type inference
                    value_text = getattr(right_node, 'text', '')
                    inferred_type = "unknown"
                    if isinstance(value_text, str):
                        if (value_text.startswith("'") and value_text.endswith("'")) or \
                           (value_text.startswith('"') and value_text.endswith('"')):
                            inferred_type = "str"
                        elif value_text.isdigit():
                             inferred_type = "int"
                        elif '.' in value_text and all(c.isdigit() or c == '.' for c in value_text):
                             try:
                                  float(value_text)
                                  inferred_type = "float"
                             except ValueError:
                                  pass
                    logger.debug(f"    Inferred type: {inferred_type}")
                                 
                    variables.append({
                        'name': getattr(left_node, 'text', ''),
                        'start_line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'type': inferred_type
                    })
                else:
                    logger.warning(f"    Skipped assignment node {i} due to missing 'left' or 'right' field.")
        logger.debug(f"[_extract_variables] Finished. Found {len(variables)} variables.")
        return variables

    def _extract_functions(self, root):
        """Extract function definitions from the MockTree root node."""
        functions = []
        logger.debug(f"[_extract_functions] Starting for {root.type if hasattr(root, 'type') else 'unknown'} node")
        
        if not root or not hasattr(root, 'children'):
            return functions
            
        for i, node in enumerate(root.children):
            if not hasattr(node, 'type'):
                continue
                
            logger.debug(f"[_extract_functions] Processing child {i}: type='{node.type}'")
            
            # Handle function definition nodes
            if node.type == 'function_definition':
                logger.debug(f"  Found function_definition node")
                
                # Attempt to get function name from fields dictionary
                name = None
                
                # Try getting name from fields
                if hasattr(node, 'fields') and node.fields and 'name' in node.fields:
                    name_node = node.fields.get('name')
                    if name_node and hasattr(name_node, 'text'):
                        name = name_node.text
                        logger.debug(f"    Got name from fields.name.text: {name}")
                
                # Try getting name from text attribute directly
                if not name and hasattr(node, 'text') and node.text:
                    name = node.text
                    logger.debug(f"    Got name from text attribute: {name}")
                
                # Try getting name from first child with type 'identifier'
                if not name:
                    for child in node.children:
                        if hasattr(child, 'type') and child.type == 'identifier':
                            if hasattr(child, 'text') and child.text:
                                name = child.text
                                logger.debug(f"    Got name from identifier child: {name}")
                                break
                
                # Skip if we couldn't find a name
                if not name:
                    logger.warning(f"    Skipped function definition node {i} due to missing 'name' child node.")
                    continue
                    
                # Create function info
                function_info = {
                    'name': name,
                    'start_line': node.start_point[0] + 1 if hasattr(node, 'start_point') else 0,
                    'end_line': node.end_point[0] + 1 if hasattr(node, 'end_point') else 0,
                    'is_method': False,  # Methods are determined by context in a class
                }
                
                # Add parameters if available
                parameters = []
                if hasattr(node, 'fields') and node.fields and 'parameters' in node.fields:
                    param_node = node.fields.get('parameters')
                    if param_node and hasattr(param_node, 'children'):
                        for p in param_node.children:
                            if hasattr(p, 'text'):
                                parameters.append({
                                    'name': p.text,
                                    'type': 'parameter',  # Default type
                                })
                
                function_info['parameters'] = parameters
                functions.append(function_info)
                logger.debug(f"  Added function: {name} with {len(parameters)} parameters")
            
            # Process classes to extract methods
            elif node.type == 'class_definition':
                logger.debug(f"  Found class_definition node (methods belong to classes)")
                
                # Get class name - useful for debugging but not directly needed here
                class_name = ""
                if hasattr(node, 'fields') and node.fields and 'name' in node.fields:
                    name_node = node.fields.get('name')
                    if name_node and hasattr(name_node, 'text'):
                        class_name = name_node.text
                
                # Look for methods in class body
                # Class methods are not included in top-level functions
                for child in node.children:
                    if hasattr(child, 'type') and child.type == 'class_body':
                        logger.debug(f"    Found class_body node. Methods in this body are NOT top-level functions.")
                        # We intentionally don't process functions in class body for top-level functions
            
            # Recursively process all other node types (except classes)
            elif node.type not in ('class_definition'):
                for child in node.children:
                    child_functions = self._extract_functions(child)
                    functions.extend(child_functions)
        
        logger.debug(f"[_extract_functions] Finished. Found {len(functions)} functions")
        return functions