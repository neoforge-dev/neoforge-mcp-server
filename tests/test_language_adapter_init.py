"""Tests for language adapter initialization and grammar building."""

import pytest
import logging
import subprocess
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

def test_initialization(adapter):
    """Test basic initialization of the adapter."""
    assert adapter.parser is not None, "Parser should be initialized"
    assert adapter.language is not None, "Language should be loaded"
    assert adapter.import_query is not None, "Import query should be compiled"
    assert adapter.require_query is not None, "Require query should be compiled"

def test_grammar_directory_structure(adapter):
    """Test that grammar directory structure is correct."""
    vendor_path = Path(__file__).parent.parent.parent / 'vendor' / 'tree-sitter-javascript'
    assert vendor_path.exists(), "Vendor directory should exist"
    assert (vendor_path / 'src').exists(), "Source directory should exist"
    assert (vendor_path / 'src' / 'parser.c').exists(), "Parser source should exist"
    assert (vendor_path / 'src' / 'scanner.c').exists(), "Scanner source should exist"

def test_grammar_building(tmp_path, adapter):
    """Test grammar building process."""
    # Create a temporary directory for testing
    test_dir = tmp_path / "test_grammar"
    test_dir.mkdir()
    (test_dir / "src").mkdir()
    
    # Create minimal valid grammar files
    (test_dir / "src" / "parser.c").write_text("""
#include "tree_sitter/parser.h"
#include <string.h>
#include <wctype.h>

enum {
  ERROR,
  END,
  TOKEN_END,
  TOKEN_ERROR,
};

static bool scan(TSLexer *lexer, const bool *valid_symbols) {
  return false;
}

void *tree_sitter_javascript_external_scanner_create() {
  return NULL;
}

void tree_sitter_javascript_external_scanner_destroy(void *payload) {
}

unsigned tree_sitter_javascript_external_scanner_serialize(void *payload, char *buffer) {
  return 0;
}

void tree_sitter_javascript_external_scanner_deserialize(void *payload, const char *buffer, unsigned length) {
}

bool tree_sitter_javascript_external_scanner_scan(void *payload, TSLexer *lexer, const bool *valid_symbols) {
  return scan(lexer, valid_symbols);
}
""")
    
    # Test building with minimal grammar
    try:
        from tree_sitter import Language
        Language.build_library(
            str(test_dir / "javascript.so"),
            [str(test_dir)]
        )
    except Exception as e:
        pytest.fail(f"Failed to build minimal grammar: {e}")

def test_grammar_source_updates(tmp_path, adapter):
    """Test that grammar is rebuilt when source files change."""
    vendor_path = Path(__file__).parent.parent.parent / 'vendor' / 'tree-sitter-javascript'
    build_dir = Path(__file__).parent.parent / 'code_understanding' / 'build'
    language_lib = build_dir / 'javascript.so'
    
    # Get initial modification time
    initial_mtime = language_lib.stat().st_mtime if language_lib.exists() else 0
    
    # Touch a source file
    parser_c = vendor_path / 'src' / 'parser.c'
    if parser_c.exists():
        subprocess.run(['touch', str(parser_c)], check=True)
    
    # Rebuild
    adapter._load_language_and_queries()
    
    # Verify rebuild
    if language_lib.exists():
        new_mtime = language_lib.stat().st_mtime
        assert new_mtime > initial_mtime, "Grammar should be rebuilt when source changes"

def test_query_compilation(adapter):
    """Test that queries are properly compiled."""
    # Test import query
    captures = adapter.import_query.captures(adapter.parser.parse(b"import { name } from './module';").root_node)
    assert len(captures) > 0, "Import query should capture nodes"
    
    # Test require query
    captures = adapter.require_query.captures(adapter.parser.parse(b"const fs = require('fs');").root_node)
    assert len(captures) > 0, "Require query should capture nodes"

def test_language_features(adapter):
    """Test that language features are properly loaded."""
    # Test basic parsing
    tree = adapter.parser.parse(b"console.log('test');")
    assert tree is not None, "Should parse basic code"
    assert not tree.root_node.has_error, "Should parse without errors"
    
    # Test error recovery
    tree = adapter.parser.parse(b"function test() {")
    assert tree is not None, "Should parse incomplete code"
    assert tree.root_node.has_error, "Should detect syntax errors"

def test_grammar_cleanup(tmp_path, adapter):
    """Test cleanup of temporary files during grammar building."""
    # Create temporary directory with some files
    temp_dir = tmp_path / "temp_grammar"
    temp_dir.mkdir()
    (temp_dir / "temp.c").write_text("// temporary file")
    
    # Force cleanup
    adapter._cleanup_temp_files(temp_dir)
    
    # Verify cleanup
    assert not (temp_dir / "temp.c").exists(), "Temporary files should be cleaned up"

def test_grammar_building_errors(tmp_path, adapter):
    """Test handling of grammar building errors."""
    # Create invalid grammar directory
    invalid_dir = tmp_path / "invalid_grammar"
    invalid_dir.mkdir()
    (invalid_dir / "src").mkdir()
    (invalid_dir / "src" / "parser.c").write_text("invalid C code")
    
    # Attempt to build
    with pytest.raises(Exception):
        from tree_sitter import Language
        Language.build_library(
            str(invalid_dir / "javascript.so"),
            [str(invalid_dir)]
        )

def test_grammar_version_compatibility(adapter):
    """Test grammar version compatibility."""
    # Get grammar version
    version = adapter.language.version if adapter.language else None
    assert version is not None, "Should have grammar version"
    
    # Test parsing with different versions
    code = "const test = 'version test';"
    tree = adapter.parser.parse(code.encode())
    assert tree is not None, "Should parse with current grammar version"

def test_grammar_performance(adapter):
    """Test grammar parsing performance."""
    import time
    
    # Create large test file
    large_code = "const test = 'performance test';\n" * 1000
    
    # Measure parsing time
    start_time = time.time()
    tree = adapter.parser.parse(large_code.encode())
    end_time = time.time()
    
    assert tree is not None, "Should parse large file"
    assert end_time - start_time < 1.0, "Should parse within reasonable time" 