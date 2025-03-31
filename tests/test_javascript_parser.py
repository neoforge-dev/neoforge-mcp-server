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
    # exports = result.get('exports', [])
    # assert len(exports) == 3, "Expected 3 exports"
    # assert any(exp['name'] == 'MyClass' for exp in exports)
    # assert any(exp['name'] == 'greet' for exp in exports)
    # assert any(exp['is_default'] for exp in exports)

# TODO: Add test_analyze_javascript_file using tmp_path fixture
# TODO: Add tests for syntax errors
# TODO: Add tests for different JS features (async/await, exports variants, etc.) 