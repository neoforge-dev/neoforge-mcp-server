"""Advanced test cases for JavaScript parser."""

import pytest
from typing import Dict, Any, Optional
from server.code_understanding.language_adapters import JavaScriptParserAdapter, ParserError
from server.code_understanding.common_types import MockTree, MockNode

@pytest.fixture
def parser():
    """Create a JavaScript parser adapter for testing."""
    return JavaScriptParserAdapter()

def test_parser_initialization(parser):
    """Test parser initialization."""
    assert parser.parser is not None
    assert parser.language is not None
    assert parser._node_cache == {}
    assert parser._feature_cache == {}

def test_memory_management(parser):
    """Test memory management functionality."""
    # Test cache initialization
    assert parser._memory_threshold == 100 * 1024 * 1024  # 100MB
    assert parser._cleanup_interval == 300  # 5 minutes
    
    # Test cache operations
    test_node = MockNode(type="test_node", text="test")
    parser._cache_node("test", test_node)
    assert parser._get_cached_node("test") == test_node
    
    test_feature = ("test_type", {"key": "value"})
    parser._cache_feature("test_key", "test_type", {"key": "value"})
    assert parser._get_cached_feature("test_key") == test_feature
    
    # Test cache cleanup
    parser._cleanup_cache()
    assert parser._get_cached_node("test") is None
    assert parser._get_cached_feature("test_key") is None

def test_error_handling(parser):
    """Test error handling functionality."""
    # Test custom error creation
    error = ParserError("Test error", "test_error")
    assert str(error) == "Test error"
    assert error.error_type == "test_error"
    assert error.context == {}
    
    # Test error with context
    error = ParserError("Test error", "test_error", context={"key": "value"})
    assert error.context == {"key": "value"}
    
    # Test error recovery
    with pytest.raises(ParserError):
        parser.parse("invalid javascript code")
    
    # Test error context tracking
    assert len(parser._error_context) > 0
    assert "attempt_1" in parser._error_context

def test_feature_extraction(parser):
    """Test feature extraction functionality."""
    # Test import extraction
    code = """
    import { name } from 'module';
    import defaultExport from 'module';
    import * as namespace from 'module';
    """
    tree = parser.parse(code)
    assert tree is not None
    
    imports = [f for f in tree.features if f[0] == 'import']
    assert len(imports) == 3
    
    # Test export extraction
    code = """
    export const name = 'test';
    export default function() {}
    export { name1, name2 };
    """
    tree = parser.parse(code)
    assert tree is not None
    
    exports = [f for f in tree.features if f[0] == 'export']
    assert len(exports) == 3
    
    # Test function extraction
    code = """
    function test() {}
    async function asyncTest() {}
    function* generatorTest() {}
    """
    tree = parser.parse(code)
    assert tree is not None
    
    functions = [f for f in tree.features if f[0] == 'function']
    assert len(functions) == 3
    
    # Test class extraction
    code = """
    class Test {}
    class AsyncTest {}
    """
    tree = parser.parse(code)
    assert tree is not None
    
    classes = [f for f in tree.features if f[0] == 'class']
    assert len(classes) == 2

def test_node_manipulation(parser):
    """Test node manipulation utilities."""
    # Test node text extraction
    code = "const name = 'test';"
    tree = parser.parse(code)
    assert tree is not None
    
    # Test finding child by type
    node = tree.root_node
    const_node = parser._find_child_by_type(node, 'lexical_declaration')
    assert const_node is not None
    
    # Test finding children by type
    children = parser._find_children_by_type(node, 'lexical_declaration')
    assert len(children) > 0
    
    # Test getting field value
    name_node = parser._get_field_value(const_node, 'name')
    assert name_node == 'name'

def test_complex_parsing_scenarios(parser):
    """Test parsing of complex JavaScript code."""
    # Test nested structures
    code = """
    class Test {
        constructor() {
            this.name = 'test';
        }
        
        async method() {
            const result = await this.fetch();
            return result;
        }
    }
    
    export default Test;
    """
    tree = parser.parse(code)
    assert tree is not None
    
    # Test multiple features
    classes = [f for f in tree.features if f[0] == 'class']
    functions = [f for f in tree.features if f[0] == 'function']
    exports = [f for f in tree.features if f[0] == 'export']
    
    assert len(classes) == 1
    assert len(functions) == 2  # constructor and method
    assert len(exports) == 1

def test_edge_cases(parser):
    """Test handling of edge cases."""
    # Test empty code
    tree = parser.parse("")
    assert tree is not None
    assert len(tree.features) == 0
    
    # Test invalid code
    tree = parser.parse("invalid javascript code")
    assert tree is None
    
    # Test very large code
    large_code = "const name = 'test';\n" * 1000
    tree = parser.parse(large_code)
    assert tree is not None
    
    # Test special characters
    code = r"""
    const name = 'test\n';
    const path = 'C:\path\to\file';
    """
    tree = parser.parse(code)
    assert tree is not None

def test_performance(parser):
    """Test parser performance."""
    import time
    
    # Test parsing speed
    code = "const name = 'test';\n" * 100
    start_time = time.time()
    tree = parser.parse(code)
    end_time = time.time()
    
    assert tree is not None
    assert end_time - start_time < 1.0  # Should parse within 1 second
    
    # Test memory usage
    import psutil
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Parse large code
    large_code = "const name = 'test';\n" * 1000
    tree = parser.parse(large_code)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (less than 50MB)
    assert memory_increase < 50 * 1024 * 1024 