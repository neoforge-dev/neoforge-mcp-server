import os
import sys
import json
import logging

# Add the project root to Python path
sys.path.append(os.path.abspath('.'))

from server.code_understanding.analyzer import CodeAnalyzer

# Set up logging to see detailed debug information
logging.basicConfig(level=logging.DEBUG, 
                   format='%(levelname)s:%(name)s:%(message)s')

def print_node_structure(node, indent=0):
    """Recursively print the structure of a node."""
    if not node:
        return
    
    indent_str = '  ' * indent
    node_type = getattr(node, 'type', 'Unknown')
    node_text = getattr(node, 'text', '')[:50]  # Truncate text for readability
    
    print(f"{indent_str}Node: {node_type}")
    print(f"{indent_str}Text: {node_text}")
    
    if hasattr(node, 'fields') and node.fields:
        print(f"{indent_str}Fields: {node.fields}")
    
    if hasattr(node, 'children'):
        for i, child in enumerate(node.children):
            print(f"{indent_str}Child {i}:")
            print_node_structure(child, indent + 1)

# Create a simple JavaScript code with different statements
js_code = """
const fs = require('fs');
import path from 'path';
import { readFileSync } from 'fs';

function greet(name) {
  return `Hello, ${name}!`;
}

const farewell = (name) => {
  return `Goodbye, ${name}!`;
};

class MyClass {
  constructor(value) {
    this.value = value;
  }
  
  getValue() {
    return this.value;
  }
}

const instance = new MyClass(123);
let myVar = 'test';
const myConst = 456;
"""

# Parse the code to get the AST tree directly
from server.code_understanding.parser import CodeParser
parser = CodeParser()
tree = parser.parse(js_code, language='javascript')

print("\n--- AST Structure ---")
print_node_structure(tree.root_node)

# Analyze the code with our analyzer
print("\n--- Running Analysis ---")
analyzer = CodeAnalyzer()
result = analyzer.analyze_code(js_code, language='javascript')

print("\n--- Analysis Result ---")
print(f"Imports: {json.dumps(result.get('imports', []), indent=2)}")
print(f"Variables: {json.dumps(result.get('variables', []), indent=2)}")
print(f"Functions: {json.dumps(result.get('functions', []), indent=2)}")
print(f"Classes: {json.dumps(result.get('classes', []), indent=2)}") 