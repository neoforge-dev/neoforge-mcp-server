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
from .language_adapters import JavaScriptParserAdapter, PythonMockParserAdapter
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
        self.imports = []
        self.functions = []
        self.classes = []
        self.variables = []
        self.exports = []
        self.error_details = []
        self.current_class = None
        self.language = language
        
        if not code or not code.strip():
            self.error_details.append({'message': 'Empty code'})
            return {
                'imports': self.imports,
                'functions': self.functions,
                'classes': self.classes,
                'variables': self.variables,
                'exports': self.exports,
                'error_details': self.error_details
            }
            
        # Detect language if not provided
        if not language:
            language = self._detect_language(code)
            logger.info(f"Detected language: {language}")
        
        try:
            adapter = None
            if language == 'javascript':
                adapter = JavaScriptParserAdapter()
            elif language == 'python':
                adapter = PythonMockParserAdapter()
            # Add elif for SwiftParserAdapter etc. here
            # elif language == 'swift':
            #     adapter = SwiftParserAdapter()
            else:
                # No adapter found for the detected/specified language
                 logger.warning(f"No specific adapter found for language: {language}. Analysis might be incomplete.")
                 # Return empty structure
                 return {
                     'language': language,
                     'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': [],
                     'has_errors': False, 'errors': []
                 }
            
            # --- Call adapter and return its result directly --- 
            if adapter:
                 analysis_result = adapter.analyze(code)
                 # Add language info to the result from adapter
                 analysis_result['language'] = language
                 return analysis_result
            # else:
            #    # This path should not be reachable if the logic above correctly handles
            #    # all supported languages and the final else block catches unsupported ones.
            #     logger.error(f"Adapter was None for language {language}, logic error in analyze_code.")
            #     return {
            #         'language': language,
            #         'imports': [], 'functions': [], 'classes': [], 'variables': [], 'exports': [],
            #         'has_errors': True, 'errors': [{'message': 'Internal error: Adapter became None unexpectedly'}]
            #     }
                 
            # --- OLD LOGIC REMOVED --- 

        except Exception as e:
            logger.exception(f"Error analyzing code for language {language}: {e}")
            return {
                'language': language,
                'imports': [],
                'functions': [],
                'classes': [],
                'variables': [],
                'exports': [],
                'has_errors': True,
                'error_details': [{'message': str(e)}], # Keep original key for now
                'errors': [{'message': str(e)}] # Add new key too
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
        """Extract import statements from a node.
        
        Args:
            root: Root node to extract imports from
            
        Returns:
            List of dictionaries containing import information
        """
        imports = []
        for node in root.children:
            if node.type == 'import':
                imports.append({
                    'type': 'import',
                    'name': node.text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                })
        return imports

    def _extract_classes(self, root):
        """Extract class definitions from a node.
        
        Args:
            root: Root node to extract classes from
            
        Returns:
            List of dictionaries containing class information
        """
        classes = []
        for node in root.children:
            if node.type == 'class_definition':
                classes.append({
                    'name': node.fields["name"].text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'methods': [],
                    'bases': []
                })
        return classes

    def _extract_variables(self, root):
        """Extract variable assignments from a node.
        
        Args:
            root: Root node to extract variables from
            
        Returns:
            List of dictionaries containing variable information
        """
        variables = []
        for node in root.children:
            if node.type == 'assignment':
                right_text = node.fields["right"].text
                inferred_type = "str" if ((right_text.startswith("'") and right_text.endswith("'")) or (right_text.startswith('"') and right_text.endswith('"'))) else "unknown"
                variables.append({
                    'name': node.fields["left"].text,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'type': inferred_type
                })
        return variables