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
            if node.type == 'import': # Handles 'import module' or 'import module as alias'
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
        """Extract class definitions from a node."""
        classes = []
        logger.debug(f"[_extract_classes] Starting. Root children count: {len(root.children) if root and hasattr(root, 'children') else 'N/A'}")
        if not root or not hasattr(root, 'children'):
            logger.debug("[_extract_classes] Root is None or has no children.")
            return classes

        for i, node in enumerate(root.children):
            logger.debug(f"[_extract_classes] Processing root child {i}: type='{node.type}'")
            if node.type == 'class_definition':
                logger.debug(f"  Found 'class_definition' node. Fields: {hasattr(node, 'fields')}, Children: {len(node.children)}")
                name_node = None
                body_nodes = []
                base_nodes = []
                
                # Extract name, body, and bases from fields (MockParser structure)
                if hasattr(node, 'fields') and node.fields:
                    name_node = node.fields.get("name")
                    body_nodes = node.fields.get("body", []) # Expecting a list of method nodes
                    base_nodes = node.fields.get("bases", []) # Expecting a list of identifier nodes
                    
                class_name = getattr(name_node, 'text', '[N/A]') if name_node else '[N/A]'
                logger.debug(f"    Extracted class name='{class_name}' (from fields)")
                logger.debug(f"    Found {len(body_nodes)} nodes in body field, {len(base_nodes)} nodes in bases field.")

                if name_node:
                    methods = []
                    bases = []
                    
                    # Extract method names from body_nodes
                    if isinstance(body_nodes, list):
                        for body_item in body_nodes:
                             # MockParser creates function_definition for methods
                             if body_item and body_item.type == 'function_definition': 
                                  # Find the method name within the function_definition's children
                                  method_name_node = None
                                  for child in body_item.children:
                                      if child.type == 'name':
                                          method_name_node = child
                                          break
                                  method_name = getattr(method_name_node, 'text', '[Unknown Method]')
                                  logger.debug(f"      Found method: '{method_name}' (type: {body_item.type})")
                                  if method_name_node:
                                       methods.append({'name': method_name})
                                  else:
                                       logger.warning(f"      Could not find name child for method node: {body_item}")
                             else:
                                 logger.debug(f"      Skipping non-method node in body: {body_item.type if body_item else 'None'}")
                                       
                    # Extract base class names from base_nodes
                    if isinstance(base_nodes, list):
                         for base_node in base_nodes:
                              # Assuming base_node is an identifier node with text
                              if base_node and hasattr(base_node, 'text'):
                                   base_name = base_node.text
                                   logger.debug(f"      Found base class: '{base_name}'")
                                   bases.append(base_name)
                              else:
                                  logger.warning(f"      Skipping invalid base node: {base_node}")
                              
                    classes.append({
                        'name': getattr(name_node, 'text', ''),
                        'start_line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1,
                        'methods': methods,
                        'bases': bases
                    })
                    logger.debug(f"    Appended class '{class_name}' with {len(methods)} methods and {len(bases)} bases.")
                else:
                     logger.warning(f"    Skipped class definition node {i} due to missing 'name' field.")
                     
        logger.debug(f"[_extract_classes] Finished. Found {len(classes)} classes.")
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
        """Extract function definitions from a node."""
        functions = []
        logger.debug(f"[_extract_functions] Starting. Root children count: {len(root.children) if root and hasattr(root, 'children') else 'N/A'}")
        if not root or not hasattr(root, 'children'):
            logger.debug("[_extract_functions] Root is None or has no children.")
            return functions
            
        for i, node in enumerate(root.children):
            logger.debug(f"[_extract_functions] Processing root child {i}: type='{node.type}'")
            if node.type == 'function_definition':
                logger.debug(f"  Found 'function_definition' node. Fields: {hasattr(node, 'fields')}, Children: {len(node.children)}")
                # Find the name node within the children (MockParser puts it here)
                name_node = None
                for child in node.children:
                    if child.type == 'name':
                        name_node = child
                        break 
                
                func_name = getattr(name_node, 'text', '[N/A]') if name_node else '[N/A]'
                logger.debug(f"    Extracted function name='{func_name}' (from children)")
                if name_node:
                     # TODO: Extract parameters, return type etc.
                     functions.append({
                          'name': getattr(name_node, 'text', ''),
                          'start_line': node.start_point[0] + 1,
                          'end_line': node.end_point[0] + 1,
                     })
                else:
                     logger.warning(f"    Skipped function definition node {i} due to missing 'name' child node.")
                     
        logger.debug(f"[_extract_functions] Finished. Found {len(functions)} functions.")
        return functions