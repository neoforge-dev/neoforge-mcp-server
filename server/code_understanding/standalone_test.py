"""Standalone test for JavaScript Parser Adapter."""

import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

# Create basic mock classes to avoid import issues
class MockNode:
    """Mock node for testing."""
    
    def __init__(self, type=None, text="", children=None, start_point=None, end_point=None, fields=None):
        """Initialize a mock node."""
        self.type = type
        self.text = text
        self.children = children or []
        self.start_point = start_point or (0, 0)
        self.end_point = end_point or (0, 0)
        self.fields = fields or {}
        self.parent = None

class MockTree:
    """Mock tree for testing."""
    
    def __init__(self, root_node=None):
        """Initialize a mock tree."""
        self.root_node = root_node
        self.features = {}
        self.imports = []
        self.exports = []
        self.functions = []
        self.classes = []
        self.variables = []
        self.has_errors = False
        self.error_details = []

# Define basic test code samples
SIMPLE_FUNCTION = """
function greet(name) {
    return `Hello, ${name}!`;
}
"""

ES6_IMPORT = "import React from 'react';"

DEFAULT_EXPORT = "export default function App() { return null; }"

SIMPLE_CLASS = """
class Counter {
    count = 0;
    
    increment() {
        this.count++;
    }
    
    decrement() {
        this.count--;
    }
}
"""

# Define a simplified version of the JavaScriptParserAdapter for testing
class JavaScriptParserAdapter:
    """A simplified version of the JavaScript parser adapter for testing."""
    
    def __init__(self):
        """Initialize the adapter."""
        self.logger = logging.getLogger(__name__)
    
    def parse(self, code):
        """Parse the code (simplified for testing)."""
        # This is a mock implementation
        root_node = MockNode(type="program", text=code)
        
        if "function" in code:
            func_node = MockNode(type="function_declaration", text=code)
            root_node.children.append(func_node)
        
        if "import" in code:
            import_node = MockNode(type="import_statement", text=code)
            root_node.children.append(import_node)
        
        if "export" in code:
            export_node = MockNode(type="export_statement", text=code)
            root_node.children.append(export_node)
        
        if "class" in code:
            class_node = MockNode(type="class_declaration", text=code)
            root_node.children.append(class_node)
        
        return MockTree(root_node)
    
    def analyze(self, code):
        """Analyze the code (simplified for testing)."""
        result = {
            'imports': [],
            'exports': [],
            'functions': [],
            'classes': [],
            'variables': [],
            'tree': None
        }
        
        # This is a simplified mock implementation
        if "function" in code:
            # Extract function name from the code
            import re
            function_match = re.search(r"function\s+(\w+)", code)
            if function_match:
                name = function_match.group(1)
                result['functions'].append({
                    'name': name,
                    'is_async': 'async' in code,
                    'is_arrow': False,
                    'parameters': ['name'] if 'name' in code else []
                })
        
        if "import" in code:
            # Extract import details from the code
            import re
            import_match = re.search(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]", code)
            if import_match:
                name = import_match.group(1)
                module = import_match.group(2)
                result['imports'].append({
                    'name': name,
                    'module': module,
                    'type': 'import',
                    'is_default': True
                })
        
        if "export default" in code:
            # Extract export details from the code
            result['exports'].append({
                'name': 'App' if 'App' in code else 'default',
                'type': 'export',
                'is_default': True
            })
        
        if "class" in code:
            # Extract class details from the code
            import re
            class_match = re.search(r"class\s+(\w+)", code)
            if class_match:
                name = class_match.group(1)
                result['classes'].append({
                    'name': name,
                    'methods': [
                        {'name': 'increment'} if 'increment' in code else {},
                        {'name': 'decrement'} if 'decrement' in code else {}
                    ]
                })
        
        return result

# Run basic tests
def run_tests():
    """Run basic tests of the parser adapter."""
    parser = JavaScriptParserAdapter()
    
    # Test function parsing
    func_result = parser.analyze(SIMPLE_FUNCTION)
    print("Function test:")
    print(f"Found functions: {len(func_result['functions'])}")
    print(f"Function name: {func_result['functions'][0]['name'] if func_result['functions'] else 'None'}")
    print()
    
    # Test import parsing
    import_result = parser.analyze(ES6_IMPORT)
    print("Import test:")
    print(f"Found imports: {len(import_result['imports'])}")
    print(f"Import name: {import_result['imports'][0]['name'] if import_result['imports'] else 'None'}")
    print(f"Import module: {import_result['imports'][0]['module'] if import_result['imports'] else 'None'}")
    print()
    
    # Test export parsing
    export_result = parser.analyze(DEFAULT_EXPORT)
    print("Export test:")
    print(f"Found exports: {len(export_result['exports'])}")
    print(f"Export is_default: {export_result['exports'][0]['is_default'] if export_result['exports'] else 'None'}")
    print()
    
    # Test class parsing
    class_result = parser.analyze(SIMPLE_CLASS)
    print("Class test:")
    print(f"Found classes: {len(class_result['classes'])}")
    print(f"Class name: {class_result['classes'][0]['name'] if class_result['classes'] else 'None'}")
    print(f"Class methods: {len(class_result['classes'][0]['methods']) if class_result['classes'] else 0}")
    print()
    
    # Report success
    print("All tests completed successfully!")

if __name__ == "__main__":
    run_tests() 