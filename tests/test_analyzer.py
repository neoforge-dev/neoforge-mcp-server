"""Tests for code analysis."""

import pytest
from server.code_understanding.analyzer import CodeAnalyzer

@pytest.fixture
def analyzer():
    """Create a test analyzer."""
    return CodeAnalyzer()

@pytest.fixture
def sample_code():
    """Create sample Python code for testing."""
    return """
import os
from pathlib import Path
from typing import List, Optional

class BaseClass:
    def base_method(self) -> None:
        pass

class TestClass(BaseClass):
    def __init__(self, name: str):
        self.name = name
        
    def test_method(self, value: int) -> Optional[str]:
        result = f"Processing {value}"
        return result if value > 0 else None

def helper_function(items: List[int]) -> int:
    return sum(items)

test_variable = "Hello World"
numbers = [1, 2, 3]
result = helper_function(numbers)
"""

def test_analyze_code(analyzer, sample_code):
    """Test analyzing Python code."""
    result = analyzer.analyze_code(sample_code)
    
    # Check imports
    assert len(result['imports']) == 3
    assert result['imports'][0]['name'] == 'import os'
    assert result['imports'][1]['name'] == 'from pathlib import Path'
    assert result['imports'][2]['name'] == 'from typing import List, Optional'
    
    # Check classes
    assert len(result['classes']) == 2
    base_class = result['classes'][0]
    test_class = result['classes'][1]
    
    assert base_class['name'] == 'BaseClass'
    assert len(base_class['methods']) == 1
    assert base_class['methods'][0]['name'] == 'base_method'
    
    assert test_class['name'] == 'TestClass'
    assert len(test_class['methods']) == 2
    assert test_class['methods'][0]['name'] == '__init__'
    assert test_class['methods'][1]['name'] == 'test_method'
    assert test_class['bases'] == ['BaseClass']
    
    # Check functions
    assert len(result['functions']) == 1
    helper_func = result['functions'][0]
    assert helper_func['name'] == 'helper_function'
    assert len(helper_func['parameters']) == 1
    assert helper_func['parameters'][0]['name'] == 'items'
    
    # Check variables
    assert len(result['variables']) == 3
    var_names = {v['name'] for v in result['variables']}
    assert var_names == {'test_variable', 'numbers', 'result'}

def test_analyze_code_invalid(analyzer):
    """Test analyzing invalid Python code."""
    result = analyzer.analyze_code("invalid python code :")
    assert result == {
        'imports': [],
        'functions': [],
        'classes': [],
        'variables': []
    }

def test_analyze_code_empty(analyzer):
    """Test analyzing empty code."""
    result = analyzer.analyze_code("")
    assert result == {
        'imports': [],
        'functions': [],
        'classes': [],
        'variables': []
    }

def test_analyze_code_complex_imports(analyzer):
    """Test analyzing code with complex imports."""
    code = """
import os, sys
from pathlib import Path, PurePath
from typing import (
    List,
    Optional,
    Dict,
    Any
)
from .utils import helper1, helper2 as h2
"""
    result = analyzer.analyze_code(code)
    assert len(result['imports']) == 7
    import_names = {imp['name'] for imp in result['imports']}
    assert 'import os' in import_names
    assert 'import sys' in import_names
    assert 'from pathlib import Path' in import_names
    assert 'from pathlib import PurePath' in import_names
    assert 'from typing import List' in import_names
    assert 'from .utils import helper1' in import_names
    assert 'from .utils import h2' in import_names

def test_analyze_code_complex_functions(analyzer):
    """Test analyzing code with complex functions."""
    code = """
def simple_func():
    pass

def func_with_params(a: int, b: str, *args, **kwargs):
    return a, b

async def async_func(x, y):
    await something()

@decorator
def decorated_func(value):
    return value * 2
"""
    result = analyzer.analyze_code(code)
    assert len(result['functions']) == 4
    func_names = {func['name'] for func in result['functions']}
    assert func_names == {'simple_func', 'func_with_params', 'async_func', 'decorated_func'}
    
    # Check parameters
    for func in result['functions']:
        if func['name'] == 'func_with_params':
            assert len(func['parameters']) == 4
            param_names = {p['name'] for p in func['parameters']}
            assert param_names == {'a', 'b', 'args', 'kwargs'}

def test_analyze_code_complex_classes(analyzer):
    """Test analyzing code with complex classes."""
    code = """
class SimpleClass:
    pass

class MultipleInheritance(BaseClass1, BaseClass2, metaclass=Meta):
    class_var = 42
    
    def __init__(self):
        super().__init__()
    
    @property
    def prop(self):
        return self._prop
    
    @classmethod
    def factory(cls):
        return cls()
    
    @staticmethod
    def utility():
        return "util"
"""
    result = analyzer.analyze_code(code)
    assert len(result['classes']) == 2
    
    simple_class = result['classes'][0]
    assert simple_class['name'] == 'SimpleClass'
    assert len(simple_class['methods']) == 0
    
    complex_class = result['classes'][1]
    assert complex_class['name'] == 'MultipleInheritance'
    assert len(complex_class['bases']) == 2
    assert complex_class['bases'] == ['BaseClass1', 'BaseClass2']
    assert len(complex_class['methods']) == 4
    method_names = {m['name'] for m in complex_class['methods']}
    assert method_names == {'__init__', 'prop', 'factory', 'utility'}

def test_analyze_code_complex_variables(analyzer):
    """Test analyzing code with complex variable assignments."""
    code = """
x = 42
y = "string"
z = [1, 2, 3]
a, b = 1, 2
c = d = 3
e = (
    "multi"
    "line"
    "string"
)
f = {
    'key': 'value'
}
"""
    result = analyzer.analyze_code(code)
    assert len(result['variables']) == 8
    var_names = {v['name'] for v in result['variables']}
    assert var_names == {'x', 'y', 'z', 'a', 'b', 'c', 'd', 'e', 'f'}
    
    # Check types
    for var in result['variables']:
        if var['name'] == 'x':
            assert var['type'] == 'int'
        elif var['name'] == 'y':
            assert var['type'] == 'str'
        elif var['name'] == 'z':
            assert var['type'] == 'list'
        elif var['name'] == 'f':
            assert var['type'] == 'dict' 