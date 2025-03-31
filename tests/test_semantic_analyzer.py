"""Tests for the JavaScript semantic analyzer."""

import unittest
import tempfile
import os
from pathlib import Path
from server.code_understanding.semantic_analyzer import SemanticAnalyzer

class TestSemanticAnalyzer(unittest.TestCase):
    """Test cases for the SemanticAnalyzer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.analyzer = SemanticAnalyzer()
        
    def test_basic_type_inference(self):
        """Test basic type inference for literals and variables."""
        code = """
        const number = 42;
        const string = "hello";
        const boolean = true;
        const array = [1, 2, 3];
        const object = { key: "value" };
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check types
        self.assertEqual(str(result['types']['number']), 'number')
        self.assertEqual(str(result['types']['string']), 'string')
        self.assertEqual(str(result['types']['boolean']), 'boolean')
        self.assertEqual(str(result['types']['array']), 'number[]')
        self.assertEqual(str(result['types']['object']), 'object')
        
    def test_function_type_inference(self):
        """Test type inference for functions."""
        code = """
        function add(a, b) {
            return a + b;
        }
        
        const multiply = (x, y) => x * y;
        
        class Calculator {
            divide(a, b) {
                return a / b;
            }
        }
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check function types
        self.assertEqual(str(result['types']['add']), 'function')
        self.assertEqual(str(result['types']['multiply']), 'function')
        self.assertEqual(str(result['types']['Calculator']), 'Calculator')
        
        # Check function contexts
        self.assertEqual(result['contexts']['add']['type'], 'function')
        self.assertEqual(len(result['contexts']['add']['parameters']), 2)
        
        # Check class method context
        self.assertEqual(result['contexts']['Calculator']['type'], 'class')
        self.assertIn('divide', result['contexts']['Calculator']['methods'])
        
    def test_class_analysis(self):
        """Test analysis of classes and their members."""
        code = """
        class Person {
            constructor(name, age) {
                this.name = name;
                this.age = age;
            }
            
            getName() {
                return this.name;
            }
            
            getAge() {
                return this.age;
            }
        }
        
        const person = new Person("John", 30);
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check class type
        self.assertEqual(str(result['types']['Person']), 'Person')
        self.assertEqual(str(result['types']['person']), 'Person')
        
        # Check class context
        person_context = result['contexts']['Person']
        self.assertEqual(person_context['type'], 'class')
        self.assertIn('constructor', person_context['methods'])
        self.assertIn('getName', person_context['methods'])
        self.assertIn('getAge', person_context['methods'])
        
    def test_scope_analysis(self):
        """Test scope analysis and variable lookup."""
        code = """
        const global = "global";
        
        function outer() {
            const outer_var = "outer";
            
            function inner() {
                const inner_var = "inner";
                console.log(global, outer_var, inner_var);
            }
            
            inner();
        }
        
        outer();
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check variable types
        self.assertEqual(str(result['types']['global']), 'string')
        self.assertEqual(str(result['types']['outer']), 'function')
        
        # Check function contexts
        outer_context = result['contexts']['outer']
        self.assertEqual(outer_context['type'], 'function')
        self.assertIn('outer_var', outer_context['scope']['variables'])
        
    def test_array_type_inference(self):
        """Test type inference for arrays and array operations."""
        code = """
        const numbers = [1, 2, 3];
        const strings = ["a", "b", "c"];
        const mixed = [1, "two", true];
        
        function processArray(arr) {
            return arr.map(x => x);
        }
        
        const result = processArray(numbers);
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check array types
        self.assertEqual(str(result['types']['numbers']), 'number[]')
        self.assertEqual(str(result['types']['strings']), 'string[]')
        self.assertEqual(str(result['types']['mixed']), 'any[]')
        self.assertEqual(str(result['types']['result']), 'number[]')
        
    def test_object_type_inference(self):
        """Test type inference for objects and object operations."""
        code = """
        const person = {
            name: "John",
            age: 30,
            address: {
                street: "123 Main St",
                city: "New York"
            }
        };
        
        function updatePerson(p) {
            p.age += 1;
            return p;
        }
        
        const updated = updatePerson(person);
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check object types
        self.assertEqual(str(result['types']['person']), 'object')
        self.assertEqual(str(result['types']['updated']), 'object')
        
        # Check function context
        update_context = result['contexts']['updatePerson']
        self.assertEqual(update_context['type'], 'function')
        self.assertEqual(len(update_context['parameters']), 1)
        
    def test_error_handling(self):
        """Test handling of invalid code."""
        # Test invalid JavaScript
        invalid_code = "invalid javascript code"
        result = self.analyzer.analyze_file('test.js', invalid_code)
        self.assertIn('error', result)
        self.assertEqual(result['types'], {})
        self.assertEqual(result['contexts'], {})
        
        # Test empty file
        empty_code = ""
        result = self.analyzer.analyze_file('test.js', empty_code)
        self.assertEqual(result['types'], {})
        self.assertEqual(result['contexts'], {})
        
    def test_builtin_types(self):
        """Test handling of built-in JavaScript types."""
        code = """
        const date = new Date();
        const regex = /test/;
        const promise = new Promise((resolve) => resolve());
        const map = new Map();
        const set = new Set();
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check built-in type inference
        self.assertEqual(str(result['types']['date']), 'Date')
        self.assertEqual(str(result['types']['regex']), 'RegExp')
        self.assertEqual(str(result['types']['promise']), 'Promise')
        self.assertEqual(str(result['types']['map']), 'Map')
        self.assertEqual(str(result['types']['set']), 'Set')
        
    def test_type_inheritance(self):
        """Test type inheritance and class relationships."""
        code = """
        class Animal {
            constructor(name) {
                this.name = name;
            }
            
            speak() {
                return "Some sound";
            }
        }
        
        class Dog extends Animal {
            constructor(name, breed) {
                super(name);
                this.breed = breed;
            }
            
            speak() {
                return "Woof!";
            }
        }
        
        const dog = new Dog("Rex", "German Shepherd");
        """
        
        result = self.analyzer.analyze_file('test.js', code)
        
        # Check class types
        self.assertEqual(str(result['types']['Animal']), 'Animal')
        self.assertEqual(str(result['types']['Dog']), 'Dog')
        self.assertEqual(str(result['types']['dog']), 'Dog')
        
        # Check class contexts
        dog_context = result['contexts']['Dog']
        self.assertEqual(dog_context['type'], 'class')
        self.assertIn('speak', dog_context['methods'])
        self.assertIn('breed', dog_context['properties'])

if __name__ == '__main__':
    unittest.main() 