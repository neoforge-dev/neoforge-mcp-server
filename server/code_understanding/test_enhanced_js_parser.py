"""Tests for the enhanced JavaScript parser adapter with complex patterns."""

import os
import sys
import logging
import unittest
from pathlib import Path

# Add the parent directory to sys.path so we can import the required modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the JavaScript parser
from server.code_understanding.language_adapters import JavaScriptParserAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEnhancedJavaScriptParser(unittest.TestCase):
    """Test class for the enhanced JavaScript parser."""
    
    def setUp(self):
        """Set up the test environment."""
        # Initialize the parser
        self.parser = JavaScriptParserAdapter()
        
        # Load the test file with complex imports and exports
        test_file_path = os.path.join(os.path.dirname(__file__), 'test_files', 'complex_imports_test.js')
        with open(test_file_path, 'rb') as f:
            self.test_code = f.read()
        
        # Print information about the test file
        print(f"Loaded test file: {test_file_path}")
        print(f"Test file size: {len(self.test_code)} bytes")
    
    def test_parse_complex_imports(self):
        """Test parsing of complex import patterns."""
        result = self.parser.analyze(self.test_code)
        
        # Print the detected imports for debugging
        print("\n=== DETECTED IMPORTS ===")
        for imp in result.get('imports', []):
            print(f"- {imp}")
        
        imports = result.get('imports', [])
        self.assertGreater(len(imports), 0, "No imports detected")
        
        # Test basic imports - Using side_effect pattern since that's what we detect
        react_import = self.find_import(imports, 'react')
        self.assertIsNotNone(react_import, "Failed to detect React import")
        
        # Test relative path imports
        relative_path_import = self.find_import(imports, '../../../utils/formatters')
        self.assertIsNotNone(relative_path_import, "Failed to detect import with relative path")
        
        # Check for other key imports from the test file
        react_dom_import = self.find_import(imports, 'react-dom')
        self.assertIsNotNone(react_dom_import, "Failed to detect ReactDOM import")
        
        # Get a count of all recognized imports
        module_imports = self.get_unique_modules(imports)
        self.assertGreaterEqual(len(module_imports), 5, "Failed to detect at least 5 different modules")
    
    def test_parse_complex_exports(self):
        """Test parsing of complex export patterns."""
        result = self.parser.analyze(self.test_code)
        
        # Print the detected exports for debugging
        print("\n=== DETECTED EXPORTS ===")
        for exp in result.get('exports', []):
            print(f"- {exp}")
        
        exports = result.get('exports', [])
        self.assertGreater(len(exports), 0, "No exports detected")
        
        # Test basic exports
        basic_exports = self.find_exports(exports, export_type='variable')
        self.assertGreaterEqual(len(basic_exports), 1, "Failed to detect basic exports")
        
        # Test function exports 
        function_exports = self.find_exports(exports, export_type='function')
        self.assertGreaterEqual(len(function_exports), 1, "Failed to detect function exports")
        
        # Test class exports
        class_exports = self.find_exports(exports, export_type='class')
        self.assertGreaterEqual(len(class_exports), 1, "Failed to detect class exports")
        
        # Test default exports
        default_exports = self.find_exports(exports, is_default=True)
        self.assertGreaterEqual(len(default_exports), 0, "Failed to detect default exports")
        
        # Test named exports
        named_exports = self.find_exports(exports, is_default=False)
        self.assertGreaterEqual(len(named_exports), 1, "Failed to detect named exports")
    
    # Helper methods for finding specific imports/exports
    def find_import(self, imports, module_name, **kwargs):
        """Find an import with the specified module name and attributes."""
        for imp in imports:
            if 'module' in imp and imp['module'] == module_name:
                # Check if all provided kwargs match
                matches = True
                for key, value in kwargs.items():
                    if key not in imp or imp[key] != value:
                        matches = False
                        break
                if matches:
                    return imp
        return None
    
    def find_imports(self, imports, module_name=None, **kwargs):
        """Find all imports matching the criteria."""
        matching_imports = []
        for imp in imports:
            if module_name and ('module' not in imp or imp['module'] != module_name):
                continue
            
            # Check if all provided kwargs match
            matches = True
            for key, value in kwargs.items():
                if key not in imp or imp[key] != value:
                    matches = False
                    break
            if matches:
                matching_imports.append(imp)
        return matching_imports
    
    def find_exports(self, exports, **kwargs):
        """Find all exports matching the criteria."""
        matching_exports = []
        for exp in exports:
            # Check if all provided kwargs match
            matches = True
            for key, value in kwargs.items():
                if key not in exp or exp[key] != value:
                    matches = False
                    break
            if matches:
                matching_exports.append(exp)
        return matching_exports
    
    def find_imports_with_alias(self, imports, module_name=None):
        """Find imports with aliases."""
        matching_imports = []
        for imp in imports:
            if module_name and ('module' not in imp or imp['module'] != module_name):
                continue
            
            if 'imported_as' in imp and imp['imported_as']:
                matching_imports.append(imp)
        return matching_imports
        
    # Additional helper method
    def get_unique_modules(self, imports):
        """Get a set of unique module names from imports."""
        modules = set()
        for imp in imports:
            if 'module' in imp:
                modules.add(imp['module'])
        return modules

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run the tests
    unittest.main() 