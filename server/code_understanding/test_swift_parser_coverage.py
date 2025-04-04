"""Comprehensive tests focused on improving coverage for SwiftParserAdapter."""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Add the required directories to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'server')))

# First try direct import from server module
try:
    from server.code_understanding.language_adapters import SwiftParserAdapter
    from server.code_understanding.common_types import MockTree, MockNode
# If that fails, try importing from copied module in tests directory
except ImportError:
    try:
        # Try importing from local directory
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server', 'code_understanding'))
        from language_adapters import SwiftParserAdapter
        from common_types import MockTree, MockNode
    except ImportError:
        print("ERROR: Could not import required modules. Make sure tree_sitter is installed.")
        sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.ERROR)

class TestSwiftParserCoverage(unittest.TestCase):
    """Test suite for Swift parser coverage."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = SwiftParserAdapter()
        # Ensure parser is properly mocked for testing
        self.parser._tree_sitter_available = False
        self.parser._version = "1.0.0"  # Set a mock version for testing
        
        # Create a temp directory for testing file operations
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temp directory
        shutil.rmtree(self.temp_dir)
    
    def test_parse_edge_cases(self):
        """Test parsing edge cases."""
        # Test empty code
        with self.assertRaises(ValueError):
            self.parser.parse("")
        
        # Test None input
        with self.assertRaises(ValueError):
            self.parser.parse(None)
        
        # Test whitespace-only code
        with self.assertRaises(ValueError):
            self.parser.parse("   \n   \t  ")
        
        # Test bytes input with valid UTF-8
        # Note: Our implementation actually handles bytes input now
        result = self.parser.parse(b"import Foundation")
        self.assertIsNotNone(result)
        
        # Test invalid syntax
        code = "invalid Swift syntax @#$%"
        result = self.parser.parse(code)
        self.assertIsNotNone(result)
    
    def test_analyze_basic_features(self):
        """Test analyze method with basic Swift features."""
        # Test basic Swift syntax
        code = """
        import Foundation
        
        func calculateSum(a: Int, b: Int) -> Int {
            return a + b
        }
        
        struct Point {
            var x: Double
            var y: Double
        }
        
        class Person {
            var name: String
            var age: Int
            
            init(name: String, age: Int) {
                self.name = name
                self.age = age
            }
        }
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        self.assertIn('imports', result, "Result should include imports key")
        self.assertIn('functions', result, "Result should include functions key")
        self.assertIn('classes', result, "Result should include classes key")
        
        # Check imports
        imports = result.get('imports', [])
        self.assertEqual(len(imports), 1, "Should have one import")
        self.assertEqual(imports[0].get('name'), 'Foundation', "Should import Foundation")
        
        # Check functions
        functions = result.get('functions', [])
        self.assertGreaterEqual(len(functions), 1, "Should have at least one function")
        self.assertTrue(any(f.get('name') == 'calculateSum' for f in functions), "Should have calculateSum function")
        
        # Check classes
        classes = result.get('classes', [])
        self.assertGreaterEqual(len(classes), 2, "Should have at least two classes/structs")
        self.assertTrue(any(c.get('name') == 'Point' for c in classes), "Should have Point struct")
        self.assertTrue(any(c.get('name') == 'Person' for c in classes), "Should have Person class")
    
    def test_analyze_swiftui_features(self):
        """Test analyze with SwiftUI-specific features."""
        # Test SwiftUI view with property wrappers
        code = r"""
        import SwiftUI
        
        struct ContentView: View {
            @State private var text = ""
            @Environment(\.colorScheme) var colorScheme
            
            var body: some View {
                VStack {
                    Text("Hello, world!")
                    TextField("Enter text", text: $text)
                }
            }
        }
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        
        # Check imports
        imports = result.get('imports', [])
        self.assertEqual(len(imports), 1, "Should have one import")
        self.assertEqual(imports[0].get('name'), 'SwiftUI', "Should import SwiftUI")
        
        # Check classes
        classes = result.get('classes', [])
        self.assertGreaterEqual(len(classes), 1, "Should have at least one class/struct")
        self.assertTrue(any(c.get('name') == 'ContentView' for c in classes), "Should have ContentView struct")
        
        # Check variables
        variables = result.get('variables', [])
        self.assertGreaterEqual(len(variables), 1, "Should have at least one variable")
    
    def test_analyze_property_wrappers(self):
        """Test analyze with various property wrappers."""
        code = r"""
        import SwiftUI
        
        class ViewModel: ObservableObject {
            @Published var count = 0
            @AppStorage("username") var username: String = ""
        }
        
        struct SettingsView: View {
            @Binding var isEnabled: Bool
            @State private var selectedTab = 0
            @SceneStorage("selectedItem") var selectedItem: String?
            @StateObject private var viewModel = ViewModel()
            
            var body: some View {
                TabView(selection: $selectedTab) {
                    Text("Tab 1").tag(0)
                    Text("Tab 2").tag(1)
                }
            }
        }
        """
        result = self.parser.analyze(code)
        self.assertIsInstance(result, dict, "Should return a dictionary result")
        
        # Check classes
        classes = result.get('classes', [])
        self.assertGreaterEqual(len(classes), 2, "Should have at least two classes/structs")
        self.assertTrue(any(c.get('name') == 'ViewModel' for c in classes), "Should have ViewModel class")
        self.assertTrue(any(c.get('name') == 'SettingsView' for c in classes), "Should have SettingsView struct")
        
        # Check variables with property wrappers
        variables = result.get('variables', [])
        self.assertGreaterEqual(len(variables), 1, "Should have at least one variable")
    
    def test_analyze_empty_string(self):
        """Test analyzing an empty string."""
        result = self.parser.analyze("")
        self.assertEqual(result, {"error": "Empty code provided"})
        
        # Test None input
        result = self.parser.analyze(None)
        self.assertEqual(result, {"error": "Empty code provided"})
    
    def test_convert_node(self):
        """Test converting a tree-sitter Node to MockNode."""
        # Create a mock tree-sitter node
        mock_node = MagicMock()
        mock_node.type = "source_file"
        mock_node.start_byte = 0
        mock_node.end_byte = 17
        mock_node.children = []
        
        source_code = "import Foundation"
        
        # Convert to MockNode
        mock_tree_node = self.parser._convert_node(mock_node, source_code)
        self.assertIsInstance(mock_tree_node, MockNode)
        self.assertEqual(mock_tree_node.type, "source_file")
        self.assertEqual(mock_tree_node.text, "import Foundation")
    
    def test_extract_code_features(self):
        """Test extracting code features from Swift code."""
        # Create a minimal mock tree
        root_node = MockNode(
            type="source_file",
            text="import Foundation",
            children=[
                MockNode(
                    type="import_declaration",
                    text="import Foundation",
                    children=[
                        MockNode(type="identifier", text="Foundation", children=[])
                    ]
                )
            ]
        )
        mock_tree = MockTree(root_node)
        
        # Extract features
        features = self.parser._extract_code_features("import Foundation", mock_tree)
        self.assertIsInstance(features, dict)
        self.assertIn('imports', features)
        self.assertEqual(len(features['imports']), 1)
        self.assertEqual(features['imports'][0]['name'], 'Foundation')
    
    def test_extract_swift_import(self):
        """Test extracting Swift import declarations."""
        # Create a mock import declaration node
        node = MockNode(
            type="import_declaration",
            text="import Foundation",
            children=[
                MockNode(type="identifier", text="Foundation", children=[])
            ]
        )
        
        # Extract imports
        imports = self.parser._extract_swift_imports(node, "import Foundation")
        self.assertIsInstance(imports, list)
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]['name'], 'Foundation')
    
    def test_extract_swift_function(self):
        """Test extracting Swift function declarations."""
        # Create a mock function declaration node
        param_node = MockNode(
            type="parameter",
            text="a: Int",
            children=[
                MockNode(type="identifier", text="a", children=[])
            ]
        )
        
        node = MockNode(
            type="function_declaration",
            text="func test(a: Int) -> Void { }",
            children=[
                MockNode(type="identifier", text="test", children=[]),
                MockNode(
                    type="parameter_list",
                    text="(a: Int)",
                    children=[param_node]
                )
            ]
        )
        
        # Extract functions
        functions = self.parser._extract_swift_functions(node, "func test(a: Int) -> Void { }")
        self.assertIsInstance(functions, list)
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions[0]['name'], 'test')
    
    def test_extract_swift_class(self):
        """Test extracting Swift class declarations."""
        # Create a mock class declaration node
        node = MockNode(
            type="class_declaration",
            text="class Person { }",
            children=[
                MockNode(type="identifier", text="Person", children=[]),
                MockNode(type="declaration_list", text="{ }", children=[])
            ]
        )
        
        # Extract classes
        classes = self.parser._extract_swift_classes(node, "class Person { }")
        self.assertIsInstance(classes, list)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]['name'], 'Person')
        self.assertEqual(classes[0]['kind'], 'class')
    
    def test_extract_swift_variable(self):
        """Test extracting Swift variable declarations."""
        # Create a mock variable declaration node
        node = MockNode(
            type="variable_declaration",
            text="var name: String",
            children=[
                MockNode(type="identifier", text="name", children=[])
            ]
        )
        
        # Extract variables
        variables = self.parser._extract_swift_variables(node, "var name: String")
        self.assertIsInstance(variables, list)
        self.assertEqual(len(variables), 1)
        self.assertEqual(variables[0]['name'], 'name')
    
    def test_extract_swift_export(self):
        """Test extracting Swift export statements."""
        # Create a mock export statement node with public modifier
        node = MockNode(
            type="function_declaration",
            text="public func test() {}",
            children=[
                MockNode(type="modifiers", text="public", children=[]),
                MockNode(type="identifier", text="test", children=[])
            ]
        )
        
        # Extract exports
        exports = self.parser._extract_swift_exports(node, "public func test() {}")
        self.assertIsInstance(exports, list)
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0]['name'], 'test')
    
    def test_version_property(self):
        """Test version property."""
        # Get the current version value
        version = self.parser.version
        
        # Any version value is acceptable for the test to pass
        # We're just testing that the property can be accessed without error
        self.assertIsInstance(version, (str, type(None)), "Version should be a string or None")
    
    def test_deduplicate_by_field(self):
        """Test deduplicating items by field."""
        items = [
            {'name': 'item1', 'value': 1},
            {'name': 'item2', 'value': 2},
            {'name': 'item1', 'value': 3}  # Duplicate name
        ]
        
        result = self.parser._deduplicate_by_field(items, 'name')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'item1')
        self.assertEqual(result[1]['name'], 'item2')
    
if __name__ == '__main__':
    unittest.main() 