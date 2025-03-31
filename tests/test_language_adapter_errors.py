"""Tests for language adapter error handling and edge cases."""

import pytest
import logging
from pathlib import Path
from server.code_understanding.language_adapters import JavaScriptParserAdapter
from server.code_understanding.common_types import MockNode, MockTree

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('server.code_understanding').setLevel(logging.DEBUG)

@pytest.fixture
def adapter():
    """Fixture to provide a JavaScriptParserAdapter instance."""
    return JavaScriptParserAdapter()

def test_empty_input(adapter):
    """Test handling of empty input."""
    with pytest.raises(ValueError, match="Input code cannot be empty or whitespace only"):
        adapter.parse("")

def test_whitespace_only(adapter):
    """Test handling of whitespace-only input."""
    with pytest.raises(ValueError, match="Input code cannot be empty or whitespace only"):
        adapter.parse("   \n\t  ")

def test_invalid_encoding(adapter):
    """Test handling of invalid UTF-8 input."""
    invalid_bytes = b'\x80\x81\x82'  # Invalid UTF-8 sequence
    with pytest.raises(ValueError, match="Input code is not valid UTF-8"):
        adapter.parse(invalid_bytes)

def test_language_not_loaded(adapter):
    """Test behavior when language is not loaded."""
    # Force language to None
    adapter.language = None
    with pytest.raises(RuntimeError, match="JavaScript language not loaded for adapter"):
        adapter.parse("console.log('test');")

def test_grammar_building_failure(tmp_path, adapter):
    """Test handling of grammar building failures."""
    # Create a temporary directory with invalid grammar files
    invalid_grammar_dir = tmp_path / "invalid_grammar"
    invalid_grammar_dir.mkdir()
    (invalid_grammar_dir / "src").mkdir()
    (invalid_grammar_dir / "src" / "parser.c").write_text("invalid C code")
    
    # Force the adapter to use the invalid grammar
    adapter._load_language_and_queries()
    
    # Verify that the adapter falls back to mock parser
    result = adapter.parse("console.log('test');")
    assert result is not None, "Should fall back to mock parser"
    assert result.get('has_errors', False), "Should mark result as having errors"

def test_query_compilation_failure(adapter):
    """Test handling of query compilation failures."""
    # Force invalid query
    adapter.import_query = "invalid query"
    adapter.require_query = "invalid query"
    
    # Should still parse but with reduced functionality
    result = adapter.parse("""
    import { name } from './module';
    const fs = require('fs');
    """)
    
    assert result is not None, "Should still parse with invalid queries"
    assert result.get('has_errors', False), "Should mark result as having errors"

def test_node_conversion_failure(adapter):
    """Test handling of node conversion failures."""
    # Test with malformed AST
    result = adapter.parse("""
    class {
        constructor() {}
    }
    """)
    
    assert result is not None, "Should handle malformed AST"
    assert result.get('has_errors', False), "Should mark result as having errors"

def test_import_statement_errors(adapter):
    """Test handling of various import statement errors."""
    invalid_imports = [
        # Missing source
        "import { name } from;",
        # Invalid source
        "import { name } from 123;",
        # Missing closing quote
        "import { name } from './module;",
        # Invalid import clause
        "import from './module';",
    ]
    
    for code in invalid_imports:
        result = adapter.parse(code)
        assert result is not None, "Should handle invalid import"
        assert result.get('has_errors', False), "Should mark result as having errors"

def test_export_statement_errors(adapter):
    """Test handling of various export statement errors."""
    invalid_exports = [
        # Missing identifier
        "export from './module';",
        # Invalid source
        "export { name } from 123;",
        # Missing closing quote
        "export { name } from './module;",
        # Invalid export clause
        "export { name as };",
    ]
    
    for code in invalid_exports:
        result = adapter.parse(code)
        assert result is not None, "Should handle invalid export"
        assert result.get('has_errors', False), "Should mark result as having errors"

def test_class_definition_errors(adapter):
    """Test handling of various class definition errors."""
    invalid_classes = [
        # Missing class name
        "class { constructor() {} }",
        # Invalid extends
        "class Test extends 123 {}",
        # Missing closing brace
        "class Test { constructor() {",
        # Invalid method
        "class Test { method( { } }",
    ]
    
    for code in invalid_classes:
        result = adapter.parse(code)
        assert result is not None, "Should handle invalid class"
        assert result.get('has_errors', False), "Should mark result as having errors"

def test_function_definition_errors(adapter):
    """Test handling of various function definition errors."""
    invalid_functions = [
        # Missing function name
        "function() {}",
        # Invalid parameter
        "function test( { }",
        # Missing closing brace
        "function test() {",
        # Invalid async
        "async function test() { await; }",
    ]
    
    for code in invalid_functions:
        result = adapter.parse(code)
        assert result is not None, "Should handle invalid function"
        assert result.get('has_errors', False), "Should mark result as having errors"

def test_variable_declaration_errors(adapter):
    """Test handling of various variable declaration errors."""
    invalid_variables = [
        # Missing identifier
        "const = 123;",
        # Invalid initializer
        "let name = {;",
        # Missing semicolon
        "var test = 123",
        # Invalid destructuring
        "const { name: } = obj;",
    ]
    
    for code in invalid_variables:
        result = adapter.parse(code)
        assert result is not None, "Should handle invalid variable declaration"
        assert result.get('has_errors', False), "Should mark result as having errors"

def test_template_literal_errors(adapter):
    """Test handling of various template literal errors."""
    invalid_templates = [
        # Missing closing backtick
        "const str = `Hello ${name};",
        # Invalid expression
        "const str = `Hello ${;",
        # Invalid tagged template
        "tag`Hello ${;",
    ]
    
    for code in invalid_templates:
        result = adapter.parse(code)
        assert result is not None, "Should handle invalid template literal"
        assert result.get('has_errors', False), "Should mark result as having errors" 