"""Tests for advanced JavaScript features and edge cases."""

import pytest
import logging
from pathlib import Path
from server.code_understanding.analyzer import CodeAnalyzer
from server.code_understanding.common_types import MockNode, MockTree

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('server.code_understanding').setLevel(logging.DEBUG)

@pytest.fixture
def analyzer():
    """Fixture to provide a CodeAnalyzer instance."""
    return CodeAnalyzer()

def test_async_await_support(analyzer):
    """Test parsing of async/await syntax."""
    code = """
async function fetchData() {
    const response = await fetch('https://api.example.com/data');
    return await response.json();
}

class AsyncClass {
    async method() {
        const result = await this.someAsyncOperation();
        return result;
    }
}

const asyncArrow = async () => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    return 'done';
};
"""
    result = analyzer.analyze_code(code, language='javascript')
    
    # Verify async functions
    functions = result.get('functions', [])
    assert len(functions) == 3, "Should find 3 functions (fetchData, method, asyncArrow)"
    assert any(f['name'] == 'fetchData' and f.get('is_async', False) for f in functions), "fetchData should be marked as async"
    
    # Verify async class method
    classes = result.get('classes', [])
    assert len(classes) == 1, "Should find AsyncClass"
    methods = classes[0].get('methods', [])
    assert any(m['name'] == 'method' and m.get('is_async', False) for m in methods), "method should be marked as async"
    
    # Verify async arrow function
    assert any(f['name'] == 'asyncArrow' and f.get('is_async', False) for f in functions), "asyncArrow should be marked as async"

def test_export_variants(analyzer):
    """Test different types of export statements."""
    code = """
// Named exports
export const name = 'test';
export function helper() {}
export class Helper {}

// Default export
export default class MainClass {
    constructor() {}
}

// Re-export
export { name as renamed, helper as helperFn } from './module';

// Default re-export
export { default } from './module';

// Namespace export
export * from './module';
"""
    result = analyzer.analyze_code(code, language='javascript')
    
    # Verify exports
    exports = result.get('exports', [])
    assert len(exports) >= 8, "Should find all export statements"
    
    # Check named exports
    assert any(e['name'] == 'name' and not e['is_default'] for e in exports), "Should find named export 'name'"
    assert any(e['name'] == 'helper' and not e['is_default'] for e in exports), "Should find named export 'helper'"
    assert any(e['name'] == 'Helper' and not e['is_default'] for e in exports), "Should find named export 'Helper'"
    
    # Check default export
    assert any(e['name'] == 'MainClass' and e['is_default'] for e in exports), "Should find default export 'MainClass'"
    
    # Check re-exports
    assert any(e['name'] == 'renamed' and e.get('source_module') == './module' for e in exports), "Should find re-export 'renamed'"
    assert any(e['name'] == 'helperFn' and e.get('source_module') == './module' for e in exports), "Should find re-export 'helperFn'"
    
    # Check namespace export
    assert any(e.get('is_namespace', False) and e.get('source_module') == './module' for e in exports), "Should find namespace export"

def test_destructuring_and_spread(analyzer):
    """Test parsing of destructuring and spread operators."""
    code = """
// Object destructuring
const { name, age, ...rest } = person;

// Array destructuring
const [first, second, ...others] = array;

// Parameter destructuring
function processUser({ id, name, settings: { theme } }) {
    return { id, name, theme };
}

// Spread in function calls
const max = Math.max(...numbers);

// Spread in object literals
const combined = { ...obj1, ...obj2 };
"""
    result = analyzer.analyze_code(code, language='javascript')
    
    # Verify variables
    variables = result.get('variables', [])
    assert len(variables) >= 5, "Should find all destructured variables"
    
    # Check object destructuring
    assert any(v['name'] == 'name' and v.get('is_destructured', False) for v in variables), "Should find destructured 'name'"
    assert any(v['name'] == 'rest' and v.get('is_rest', False) for v in variables), "Should find rest parameter 'rest'"
    
    # Check array destructuring
    assert any(v['name'] == 'first' and v.get('is_destructured', False) for v in variables), "Should find destructured 'first'"
    assert any(v['name'] == 'others' and v.get('is_rest', False) for v in variables), "Should find rest parameter 'others'"
    
    # Check function with destructured parameters
    functions = result.get('functions', [])
    assert any(f['name'] == 'processUser' and f.get('has_destructured_params', False) for f in functions), "Should find function with destructured parameters"

def test_template_literals(analyzer):
    """Test parsing of template literals and tagged templates."""
    code = """
const name = 'World';
const greeting = `Hello, ${name}!`;
const multiline = `
    This is a
    multiline string
    with ${name} interpolation
`;

function tag(strings, ...values) {
    return strings.reduce((result, str, i) => 
        result + str + (values[i] || ''), '');
}

const tagged = tag`Hello ${name}!`;
"""
    result = analyzer.analyze_code(code, language='javascript')
    
    # Verify template literals
    variables = result.get('variables', [])
    assert len(variables) >= 4, "Should find all variables"
    
    # Check template literal variables
    assert any(v['name'] == 'greeting' and v.get('is_template_literal', False) for v in variables), "Should find template literal 'greeting'"
    assert any(v['name'] == 'multiline' and v.get('is_template_literal', False) for v in variables), "Should find multiline template literal"
    
    # Check tagged template
    assert any(v['name'] == 'tagged' and v.get('is_tagged_template', False) for v in variables), "Should find tagged template"

def test_class_features(analyzer):
    """Test parsing of advanced class features."""
    code = """
class Base {
    constructor() {}
    static staticMethod() {}
    get computed() { return this._value; }
    set computed(value) { this._value = value; }
}

class Derived extends Base {
    constructor() {
        super();
    }
    
    #privateField = 'private';
    static #privateStatic = 'private static';
    
    #privateMethod() {}
    static #privateStaticMethod() {}
}
"""
    result = analyzer.analyze_code(code, language='javascript')
    
    # Verify classes
    classes = result.get('classes', [])
    assert len(classes) == 2, "Should find both classes"
    
    # Check Base class features
    base_class = next(c for c in classes if c['name'] == 'Base')
    methods = base_class.get('methods', [])
    assert any(m['name'] == 'staticMethod' and m.get('is_static', False) for m in methods), "Should find static method"
    assert any(m['name'] == 'computed' and m.get('is_getter', False) for m in methods), "Should find getter"
    assert any(m['name'] == 'computed' and m.get('is_setter', False) for m in methods), "Should find setter"
    
    # Check Derived class features
    derived_class = next(c for c in classes if c['name'] == 'Derived')
    assert derived_class.get('extends') == 'Base', "Should find extends clause"
    assert any(m['name'] == 'constructor' and m.get('calls_super', False) for m in derived_class.get('methods', [])), "Should find super call"
    
    # Check private members
    assert any(m['name'] == '#privateField' and m.get('is_private', False) for m in derived_class.get('fields', [])), "Should find private field"
    assert any(m['name'] == '#privateMethod' and m.get('is_private', False) for m in derived_class.get('methods', [])), "Should find private method"

def test_error_handling(analyzer):
    """Test parsing of error handling constructs."""
    code = """
try {
    throw new Error('test');
} catch (error) {
    console.error(error);
} finally {
    cleanup();
}

async function handleError() {
    try {
        await riskyOperation();
    } catch {
        // Ignore error
    }
}
"""
    result = analyzer.analyze_code(code, language='javascript')
    
    # Verify error handling
    functions = result.get('functions', [])
    assert len(functions) >= 1, "Should find handleError function"
    
    # Check try-catch blocks
    assert any(f['name'] == 'handleError' and f.get('has_try_catch', False) for f in functions), "Should find function with try-catch"
    
    # Check error variable in catch
    variables = result.get('variables', [])
    assert any(v['name'] == 'error' and v.get('is_catch_variable', False) for v in variables), "Should find catch variable"

def test_syntax_errors(analyzer):
    """Test handling of syntax errors."""
    invalid_codes = [
        # Missing closing brace
        """
        function test() {
            console.log('test');
        """,
        
        # Invalid export
        """
        export from './module';
        """,
        
        # Invalid class syntax
        """
        class {
            constructor() {}
        }
        """,
        
        # Invalid template literal
        """
        const str = `unclosed template literal;
        """
    ]
    
    for code in invalid_codes:
        try:
            result = analyzer.analyze_code(code, language='javascript')
            assert result is not None, "Should handle syntax errors gracefully"
            assert result.get('has_errors', False), "Should mark result as having errors"
        except Exception as e:
            pytest.fail(f"Failed to handle syntax error: {e}")

def test_file_based_analysis(analyzer, tmp_path):
    """Test analyzing JavaScript files."""
    # Create a test JavaScript file
    js_file = tmp_path / "test.js"
    js_file.write_text("""
export const name = 'test';
export function helper() {}
export default class MainClass {}
    """)
    
    # Analyze the file
    result = analyzer.analyze_file(str(js_file))
    
    # Verify results
    assert result is not None, "Should analyze file successfully"
    exports = result.get('exports', [])
    assert len(exports) == 3, "Should find all exports"
    assert any(e['name'] == 'name' and not e['is_default'] for e in exports), "Should find named export"
    assert any(e['name'] == 'MainClass' and e['is_default'] for e in exports), "Should find default export" 