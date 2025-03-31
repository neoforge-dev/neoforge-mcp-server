import logging
import sys
import json

from server.code_understanding.analyzer import CodeAnalyzer
from server.code_understanding.language_adapters import JavaScriptParserAdapter
from server.code_understanding.parser import CodeParser

# Set up logging to see detailed debug information
logging.basicConfig(level=logging.DEBUG, 
                   format='%(levelname)s:%(name)s:%(message)s')

# Create a simple JavaScript code with a variable declaration
js_code = """
const fs = require('fs');
const instance = new MyClass(123);
let myVar = 'test';
const myConst = 456;
"""

def print_node_structure(node, indent=0):
    """Print the structure of an AST node for debugging."""
    if not node:
        print(f"{'  ' * indent}None")
        return
        
    print(f"{'  ' * indent}Type: {node.type}, Text: {node.text[:50] + '...' if len(node.text) > 50 else node.text}")
    print(f"{'  ' * indent}Fields: {node.fields}")
    print(f"{'  ' * indent}Children: {len(node.children)}")
    
    for i, child in enumerate(node.children):
        print(f"{'  ' * indent}Child {i}:")
        print_node_structure(child, indent + 1)

# Parse the JavaScript code
parser = CodeParser()
tree = parser.parse(js_code, language='javascript')

print("\n--- AST Structure ---")
print_node_structure(tree.root_node)

# Analyze the code with our analyzer
analyzer = CodeAnalyzer()
result = analyzer.analyze_code(js_code, language='javascript')

print("\n--- Analysis Result ---")
print(f"Imports: {json.dumps(result.get('imports', []), indent=2)}")
print(f"Variables: {json.dumps(result.get('variables', []), indent=2)}")
print(f"Functions: {json.dumps(result.get('functions', []), indent=2)}")
print(f"Classes: {json.dumps(result.get('classes', []), indent=2)}") 