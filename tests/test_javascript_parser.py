"""Tests for JavaScript code analysis via CodeAnalyzer and JS Adapter."""

import pytest
import logging
from pathlib import Path

# Import the main analyzer entry point
from server.code_understanding.analyzer import CodeAnalyzer 
# Import the JS Adapter to potentially force its loading if needed for testing
# No longer need direct import if CodeParser handles loading
# from server.code_understanding.javascript_parser import JavaScriptParserAdapter 
# Import common types if needed for constructing expected results
from server.code_understanding.common_types import MockNode, MockTree

logger = logging.getLogger(__name__)
# Configure logging - Set level to DEBUG to see detailed parser/adapter logs
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('server.code_understanding').setLevel(logging.DEBUG)

def analyzer_fixture():
    """Fixture to provide a CodeAnalyzer instance."""
    # Ensure JS adapter tries to load if not already
    # We don't need to explicitly load it here anymore, 
    # CodeParser __init__ handles adapter loading.
    # try:
    #     JavaScriptParserAdapter() 
    # except Exception as e:
    #     logger.warning(f"Could not pre-initialize JS Adapter (might be ok if CodeParser handles it): {e}")
    return CodeAnalyzer()

@pytest.fixture
def analyzer():
    """Fixture to provide a CodeAnalyzer instance."""
    # We don't need to explicitly load it here anymore, 
    # CodeParser __init__ handles adapter loading.
    return CodeAnalyzer()

@pytest.fixture
def sample_js_code():
    """Sample JavaScript code for testing."""
    return """
const fs = require('fs'); // CommonJS require
import path from 'path'; // ES6 import default
import { readFileSync } from 'fs'; // ES6 named import

function greet(name) {
  console.log(`Hello, ${name}!`);
  return `Hello, ${name}!`;
}

// Arrow function assignment
const farewell = (name) => {
    console.log(`Goodbye, ${name}!`);
    return `Goodbye, ${name}!`;
};

class MyClass {
  constructor(value) {
    this.value = value;
  }

  getValue() {
    return this.value;
  }

  static staticMethod() {
    return 'Static method called';
  }
}

const instance = new MyClass(123);
greet('World');
farewell('Moon');
console.log(instance.getValue());
console.log(MyClass.staticMethod());
console.log(readFileSync); // Reference imported symbol

let myVar = 'test';
const myConst = 456;
export { MyClass, greet }; // Named export
export default farewell; // Default export
"""

# Mark test as potentially failing if JS support isn't fully wired
# @pytest.mark.xfail(reason="JavaScript parser adapter implementation or integration might be incomplete.")
def test_analyze_javascript_code(analyzer, sample_js_code):
    """Test analyzing a string of JavaScript code using CodeAnalyzer."""
    # analyzer = analyzer_fixture # No need to reassign
    # Assuming CodeParser will detect JS or we modify it to accept a hint
    # Let's add a language hint for clarity in testing
    result = analyzer.analyze_code(sample_js_code, language='javascript') 
    
    assert result is not None, "Analysis should return a result dictionary"

    # --- Assertions based on expected MockTree structure --- 

    # Verify imports/requires
    imports = result.get('imports', [])
    assert len(imports) == 3, f"Expected 3 imports/requires, found {len(imports)}"
    # Note: Adjust 'type' based on how the adapter differentiates them
    # Example expected types: 'require', 'import' (default), 'import' (named)
    require_fs = next((imp for imp in imports if imp.get('name') == 'fs' and imp.get('type') == 'require'), None)
    import_path = next((imp for imp in imports if imp.get('name') == 'path' and imp.get('type') == 'import'), None)
    import_readfilesync = next((imp for imp in imports if imp.get('name') == 'readFileSync' and imp.get('type') == 'import'), None)
    
    assert require_fs is not None, "Did not find require('fs')"
    assert import_path is not None, "Did not find import path"
    assert import_readfilesync is not None, "Did not find import readFileSync"
    assert import_readfilesync.get('module') == 'fs', "Named import readFileSync should have module 'fs'"
    # TODO: Add check for default import if adapter adds that info (e.g., import_path.get('is_default') == True)

    # Verify functions (top-level)
    functions = result.get('functions', [])
    assert len(functions) == 2, f"Expected 2 top-level functions (greet, farewell), found {len(functions)}"
    assert any(f['name'] == 'greet' for f in functions), "Did not find function 'greet'"
    # Assuming arrow functions assigned to const/let are treated as functions
    assert any(f['name'] == 'farewell' for f in functions), "Did not find arrow function 'farewell'"

    # Verify classes
    classes = result.get('classes', [])
    assert len(classes) == 1, "Should find one class"
    my_class = classes[0]
    assert my_class['name'] == 'MyClass', "Class name mismatch"
    
    # Verify methods within the class
    methods = my_class.get('methods', [])
    assert len(methods) == 3, f"Expected 3 methods, found {len(methods)}"
    assert any(meth['name'] == 'constructor' for meth in methods), "Did not find constructor"
    assert any(meth['name'] == 'getValue' for meth in methods), "Did not find getValue"
    assert any(meth['name'] == 'staticMethod' for meth in methods), "Did not find staticMethod"
    # TODO: Check for static flag on staticMethod if adapter adds it

    # Verify variables (top-level const/let/var)
    variables = result.get('variables', [])
    # Expecting: instance, myVar, myConst. 
    # NOTE: The analyzer currently extracts names from `variable_declarator` children
    # It might not distinguish between `instance` and the functions `greet`/`farewell` if they are under `variable_declaration`.
    # Let's refine the assertion based on actual output later.
    # For now, check that the expected *variable* names are present.
    var_names = {v['name'] for v in variables}
    assert 'instance' in var_names, "Did not find 'instance' variable"
    assert 'myVar' in var_names, "Did not find 'myVar' variable"
    assert 'myConst' in var_names, "Did not find 'myConst' variable"
    # Check that functions declared with `function` keyword are NOT in variables
    assert 'greet' not in var_names, "Function 'greet' should not be in variables list"
    # Check if arrow function is treated as variable or function
    # assert 'farewell' not in var_names, "Arrow function 'farewell' should not be in variables list if treated as function"
    assert len(variables) >= 3, f"Expected at least 3 top-level variables, found {len(variables)}"
    
    # Verify exports (Need CodeAnalyzer to extract this, maybe from 'export_statement' nodes)
    exports = result.get('exports', [])
    assert len(exports) == 3, f"Expected 3 exports, found {len(exports)}"
    assert any(exp['name'] == 'MyClass' and not exp['is_default'] for exp in exports), "Did not find named export 'MyClass'"
    assert any(exp['name'] == 'greet' and not exp['is_default'] for exp in exports), "Did not find named export 'greet'"
    assert any(exp['name'] == 'farewell' and exp['is_default'] for exp in exports), "Did not find default export 'farewell'"

def test_analyze_javascript_file(analyzer, sample_js_code, tmp_path):
    """Test analyzing a JavaScript file using CodeAnalyzer."""
    # Create a temporary JavaScript file
    js_file = tmp_path / "test.js"
    js_file.write_text(sample_js_code)
    
    # Analyze the file
    result = analyzer.analyze_file(str(js_file), language='javascript')
    
    assert result is not None, "Analysis should return a result dictionary"
    
    # Verify imports/requires
    imports = result.get('imports', [])
    assert len(imports) == 3, f"Expected 3 imports/requires, found {len(imports)}"
    
    # Verify functions
    functions = result.get('functions', [])
    assert len(functions) == 2, f"Expected 2 top-level functions, found {len(functions)}"
    
    # Verify classes
    classes = result.get('classes', [])
    assert len(classes) == 1, "Should find one class"
    
    # Verify variables
    variables = result.get('variables', [])
    assert len(variables) >= 3, f"Expected at least 3 top-level variables, found {len(variables)}"
    
    # Verify exports
    exports = result.get('exports', [])
    assert len(exports) == 3, f"Expected 3 exports, found {len(exports)}"

def test_syntax_errors(analyzer):
    """Test handling of JavaScript syntax errors."""
    # Test with invalid syntax
    invalid_code = """
    function test() {
        if (true) {
            console.log("Missing closing brace"
    }
    """
    
    result = analyzer.analyze_code(invalid_code, language='javascript')
    assert result is not None, "Analysis should return a result even with syntax errors"
    assert result.get('has_errors', False), "Result should indicate syntax errors"
    assert len(result.get('error_details', [])) > 0, "Should have error details"
    
    # Test with empty file
    empty_code = ""
    result = analyzer.analyze_code(empty_code, language='javascript')
    assert result is not None, "Analysis should return a result for empty input"
    assert result.get('has_errors', False), "Result should indicate empty input error"
    
    # Test with invalid UTF-8
    invalid_utf8 = b'\x80invalid utf-8'
    result = analyzer.analyze_code(invalid_utf8, language='javascript')
    assert result is not None, "Analysis should return a result for invalid UTF-8"
    assert result.get('has_errors', False), "Result should indicate UTF-8 error"

def test_js_features(analyzer):
    """Test parsing of various JavaScript features."""
    # Test async/await
    async_code = """
    async function fetchData() {
        const response = await fetch('https://api.example.com/data');
        return await response.json();
    }
    
    class AsyncClass {
        async method() {
            await this.doSomething();
        }
    }
    """
    
    result = analyzer.analyze_code(async_code, language='javascript')
    assert result is not None, "Analysis should return a result for async code"
    
    # Verify async functions
    functions = result.get('functions', [])
    async_functions = [f for f in functions if f.get('is_async', False)]
    assert len(async_functions) == 1, "Should find one async function"
    
    # Verify async methods
    classes = result.get('classes', [])
    async_methods = [m for c in classes for m in c.get('methods', []) if m.get('is_async', False)]
    assert len(async_methods) == 1, "Should find one async method"
    
    # Test different export variants
    export_code = """
    // Named exports
    export const name = 'test';
    export function helper() {}
    
    // Default export
    export default class MainClass {}
    
    // Re-export
    export { name as renamed } from './module';
    
    // Namespace export
    export * from './module';
    """
    
    result = analyzer.analyze_code(export_code, language='javascript')
    assert result is not None, "Analysis should return a result for export code"
    
    # Verify exports
    exports = result.get('exports', [])
    assert len(exports) >= 4, "Should find all export variants"
    
    # Test template literals and destructuring
    modern_code = """
    const { name, age, ...rest } = user;
    const [first, second, ...others] = array;
    
    const greeting = `Hello ${name}, you are ${age} years old!`;
    const multiline = `
        This is a
        multiline string
    `;
    """
    
    result = analyzer.analyze_code(modern_code, language='javascript')
    assert result is not None, "Analysis should return a result for modern JS features"
    
    # Verify variables with destructuring
    variables = result.get('variables', [])
    destructured = [v for v in variables if v.get('is_destructured', False)]
    assert len(destructured) >= 2, "Should find destructured variables"
    
    # Verify template literals
    template_vars = [v for v in variables if v.get('is_template_literal', False)]
    assert len(template_vars) >= 2, "Should find template literal variables"

def test_error_handling(analyzer):
    """Test error handling in the JavaScript parser adapter."""
    # Test with None input
    result = analyzer.analyze_code(None, language='javascript')
    assert result is not None, "Analysis should return a result for None input"
    assert result.get('has_errors', False), "Result should indicate error"
    
    # Test with invalid language
    result = analyzer.analyze_code("console.log('test');", language='invalid')
    assert result is not None, "Analysis should return a result for invalid language"
    assert result.get('has_errors', False), "Result should indicate error"
    
    # Test with very large input
    large_code = "console.log('test');" * 10000
    result = analyzer.analyze_code(large_code, language='javascript')
    assert result is not None, "Analysis should return a result for large input"
    
    # Test with non-existent file
    result = analyzer.analyze_file("nonexistent.js", language='javascript')
    assert result is not None, "Analysis should return a result for non-existent file"
    assert result.get('has_errors', False), "Result should indicate file not found error"
    
    # Test with file permission issues
    # Note: This test might need to be skipped on some systems
    import os
    try:
        with open("readonly.js", "w") as f:
            f.write("console.log('test');")
        os.chmod("readonly.js", 0o000)  # Remove all permissions
        
        result = analyzer.analyze_file("readonly.js", language='javascript')
        assert result is not None, "Analysis should return a result for permission error"
        assert result.get('has_errors', False), "Result should indicate permission error"
    finally:
        # Clean up
        try:
            os.chmod("readonly.js", 0o644)  # Restore permissions
            os.remove("readonly.js")
        except:
            pass

def test_modern_js_features(analyzer):
    """Test parsing of modern JavaScript features."""
    # Test class fields and private methods
    class_code = """
    class ModernClass {
        #privateField = 42;
        static #privateStaticField = 'private';
        readonly #readonlyField = 'readonly';
        
        #privateMethod() {
            return this.#privateField;
        }
        
        static #privateStaticMethod() {
            return ModernClass.#privateStaticField;
        }
        
        async #privateAsyncMethod() {
            await this.doSomething();
        }
    }
    """
    
    result = analyzer.analyze_code(class_code, language='javascript')
    assert result is not None, "Analysis should return a result for modern class features"
    
    # Verify class fields
    classes = result.get('classes', [])
    assert len(classes) == 1, "Should find one class"
    modern_class = classes[0]
    
    # Check private fields
    private_fields = [f for f in modern_class['fields'] if f['is_private']]
    assert len(private_fields) == 3, "Should find 3 private fields"
    
    # Check static fields
    static_fields = [f for f in modern_class['fields'] if f['is_static']]
    assert len(static_fields) == 1, "Should find 1 static field"
    
    # Check readonly fields
    readonly_fields = [f for f in modern_class['fields'] if f['is_readonly']]
    assert len(readonly_fields) == 1, "Should find 1 readonly field"
    
    # Check private methods
    private_methods = [m for m in modern_class['methods'] if m['is_private']]
    assert len(private_methods) == 3, "Should find 3 private methods"
    
    # Check async methods
    async_methods = [m for m in modern_class['methods'] if m['is_async']]
    assert len(async_methods) == 1, "Should find 1 async method"

def test_export_variants(analyzer):
    """Test parsing of different export types."""
    export_code = """
    // Named exports
    export const name = 'test';
    export function helper() {}
    
    // Default export
    export default class MainClass {}
    
    // Re-export
    export { name as renamed } from './module';
    
    // Namespace export
    export * from './module';
    
    // Export list
    export { a, b, c };
    
    // Export with assertions
    export const data = await import('./data.json', { assert: { type: 'json' } });
    """
    
    result = analyzer.analyze_code(export_code, language='javascript')
    assert result is not None, "Analysis should return a result for export variants"
    
    # Verify exports
    exports = result.get('exports', [])
    assert len(exports) >= 6, "Should find all export variants"
    
    # Check named exports
    named_exports = [e for e in exports if not e['is_default'] and not e.get('is_namespace')]
    assert len(named_exports) >= 2, "Should find named exports"
    
    # Check default export
    default_exports = [e for e in exports if e['is_default']]
    assert len(default_exports) == 1, "Should find default export"
    
    # Check namespace export
    namespace_exports = [e for e in exports if e.get('is_namespace')]
    assert len(namespace_exports) == 1, "Should find namespace export"
    
    # Check re-exports - this needs to check for type 're-export', not is_re_export property
    re_exports = [e for e in exports if e.get('type') == 're-export']
    assert len(re_exports) == 1, "Should find re-export"

def test_import_variants(analyzer):
    """Test parsing of different import types."""
    import_code = """
    // Default import
    import name from './module';
    
    // Named imports
    import { a, b, c } from './module';
    
    // Namespace import
    import * as ns from './module';
    
    // Dynamic import
    const module = await import('./module');
    
    // Import with assertions
    import json from './data.json' assert { type: 'json' };
    
    // Mixed imports
    import defaultExport, { named1, named2 } from './module';
    """
    
    result = analyzer.analyze_code(import_code, language='javascript')
    assert result is not None, "Analysis should return a result for import variants"
    
    # Verify imports
    imports = result.get('imports', [])
    assert len(imports) >= 6, "Should find all import variants"
    
    # Check default imports
    default_imports = [i for i in imports if i['is_default'] and not i.get('names')]
    assert len(default_imports) >= 2, "Should find default imports"
    
    # Check named imports
    named_imports = [i for i in imports if i.get('names')]
    assert len(named_imports) >= 2, "Should find named imports"
    
    # Check namespace imports
    namespace_imports = [i for i in imports if i.get('is_namespace')]
    assert len(namespace_imports) == 1, "Should find namespace import"
    
    # Check dynamic imports
    dynamic_imports = [i for i in imports if i.get('is_dynamic')]
    assert len(dynamic_imports) == 1, "Should find dynamic import"
    
    # Check imports with assertions
    asserted_imports = [i for i in imports if i.get('assertions')]
    assert len(asserted_imports) == 1, "Should find import with assertions"

def test_edge_cases(analyzer):
    """Test handling of edge cases and error conditions."""
    # Test empty file
    empty_code = ""
    result = analyzer.analyze_code(empty_code, language='javascript')
    assert result is not None, "Analysis should return a result for empty input"
    assert not result.get('has_errors', False), "Empty input should not be treated as error"
    
    # Test file with only comments
    comment_code = """
    // This is a comment
    /* This is a block comment */
    """
    result = analyzer.analyze_code(comment_code, language='javascript')
    assert result is not None, "Analysis should return a result for comment-only input"
    assert not result.get('has_errors', False), "Comment-only input should not be treated as error"
    
    # Test invalid UTF-8
    invalid_utf8 = b'\x80invalid utf-8'
    result = analyzer.analyze_code(invalid_utf8, language='javascript')
    assert result is not None, "Analysis should return a result for invalid UTF-8"
    assert result.get('has_errors', False), "Invalid UTF-8 should be treated as error"
    
    # Test very large input
    large_code = "console.log('test');" * 10000
    result = analyzer.analyze_code(large_code, language='javascript')
    assert result is not None, "Analysis should return a result for large input"
    
    # Test non-existent file
    result = analyzer.analyze_file("nonexistent.js", language='javascript')
    assert result is not None, "Analysis should return a result for non-existent file"
    assert result.get('has_errors', False), "Non-existent file should be treated as error"
    
    # Test file permission issues
    import os
    try:
        with open("readonly.js", "w") as f:
            f.write("console.log('test');")
        os.chmod("readonly.js", 0o000)  # Remove all permissions
        
        result = analyzer.analyze_file("readonly.js", language='javascript')
        assert result is not None, "Analysis should return a result for permission error"
        assert result.get('has_errors', False), "Permission error should be treated as error"
    finally:
        # Clean up
        try:
            os.chmod("readonly.js", 0o644)  # Restore permissions
            os.remove("readonly.js")
        except:
            pass

# TODO: Add tests for syntax errors
# TODO: Add tests for different JS features (async/await, exports variants, etc.) 