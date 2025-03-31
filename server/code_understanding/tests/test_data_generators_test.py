"""
Tests for the test data generators.
"""

import pytest
from .test_data_generators import (
    TestDataGenerator,
    Language,
    CodeSample
)

def test_generate_simple_python():
    """Test generating simple Python code samples."""
    generator = TestDataGenerator()
    samples = generator.generate_samples(Language.PYTHON, "simple")
    
    assert len(samples) == 1
    sample = samples[0]
    
    assert sample.language == Language.PYTHON
    assert sample.complexity == "simple"
    assert "def" in sample.code
    assert len(sample.expected_symbols) >= 3
    assert len(sample.expected_relationships) >= 2

def test_generate_medium_javascript():
    """Test generating medium complexity JavaScript code samples."""
    generator = TestDataGenerator()
    samples = generator.generate_samples(Language.JAVASCRIPT, "medium")
    
    assert len(samples) == 1
    sample = samples[0]
    
    assert sample.language == Language.JAVASCRIPT
    assert sample.complexity == "medium"
    assert "class" in sample.code
    assert len(sample.expected_symbols) >= 5
    assert len(sample.expected_relationships) >= 3

def test_generate_complex_swift():
    """Test generating complex Swift code samples."""
    generator = TestDataGenerator()
    samples = generator.generate_samples(Language.SWIFT, "complex")
    
    assert len(samples) == 1
    sample = samples[0]
    
    assert sample.language == Language.SWIFT
    assert sample.complexity == "complex"
    assert "protocol" in sample.code
    assert "class" in sample.code
    assert len(sample.expected_symbols) >= 10
    assert len(sample.expected_relationships) >= 5

def test_generate_all_languages():
    """Test generating samples for all languages."""
    generator = TestDataGenerator()
    all_samples = generator.generate_all_samples()
    
    assert len(all_samples) == 3  # One for each language
    for language in Language:
        assert language in all_samples
        assert len(all_samples[language]) == 3  # One for each complexity level

def test_symbol_consistency():
    """Test that generated symbols match the code."""
    generator = TestDataGenerator()
    samples = generator.generate_all_samples()
    
    for language, language_samples in samples.items():
        for sample in language_samples:
            # Check that all expected symbols appear in the code
            for symbol in sample.expected_symbols:
                assert symbol["name"] in sample.code
            
            # Check that all expected relationships have valid sources and targets
            for rel in sample.expected_relationships:
                assert any(s["name"] == rel["source"] for s in sample.expected_symbols)
                assert any(s["name"] == rel["target"] for s in sample.expected_symbols)

def test_language_specific_features():
    """Test that each language's samples include language-specific features."""
    generator = TestDataGenerator()
    samples = generator.generate_all_samples()
    
    # Python-specific features
    python_samples = samples[Language.PYTHON]
    assert any("def" in s.code for s in python_samples)
    assert any("class" in s.code for s in python_samples)
    assert any("import" in s.code for s in python_samples)
    
    # JavaScript-specific features
    js_samples = samples[Language.JAVASCRIPT]
    assert any("function" in s.code for s in js_samples)
    assert any("class" in s.code for s in js_samples)
    assert any("import" in s.code for s in js_samples)
    
    # Swift-specific features
    swift_samples = samples[Language.SWIFT]
    assert any("func" in s.code for s in swift_samples)
    assert any("class" in s.code for s in swift_samples)
    assert any("protocol" in s.code for s in swift_samples)

def test_complexity_levels():
    """Test that complexity levels are properly reflected in the generated code."""
    generator = TestDataGenerator()
    samples = generator.generate_all_samples()
    
    for language, language_samples in samples.items():
        simple_samples = [s for s in language_samples if s.complexity == "simple"]
        medium_samples = [s for s in language_samples if s.complexity == "medium"]
        complex_samples = [s for s in language_samples if s.complexity == "complex"]
        
        # Simple samples should be basic functions
        assert all("def" in s.code or "function" in s.code or "func" in s.code 
                  for s in simple_samples)
        
        # Medium samples should include classes
        assert all("class" in s.code for s in medium_samples)
        
        # Complex samples should include multiple features
        assert all(any(feature in s.code for feature in ["import", "class", "def", "function", "protocol"])
                  for s in complex_samples)

def test_relationship_types():
    """Test that relationship types are appropriate for each language."""
    generator = TestDataGenerator()
    samples = generator.generate_all_samples()
    
    for language, language_samples in samples.items():
        for sample in language_samples:
            for rel in sample.expected_relationships:
                # All languages should have these basic relationships
                assert rel["type"] in ["defines", "calls", "imports"]
                
                # Language-specific relationships
                if language == Language.SWIFT:
                    assert any(rel["type"] == "conforms_to" for rel in sample.expected_relationships)
                elif language == Language.JAVASCRIPT:
                    assert any(rel["type"] == "exports" for rel in sample.expected_relationships)
                elif language == Language.PYTHON:
                    assert any(rel["type"] == "imports" for rel in sample.expected_relationships) 