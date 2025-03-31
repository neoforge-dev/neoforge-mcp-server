'''python
import pytest
from code_understanding.semantic_analysis import perform_type_inference, build_cfg


def test_perform_type_inference():
    dummy_code = 'x = 1'
    result = perform_type_inference(dummy_code)
    assert isinstance(result, dict)
    assert 'types' in result


def test_build_cfg():
    dummy_code = 'if True:\n    pass'
    result = build_cfg(dummy_code)
    assert isinstance(result, dict)
    assert 'cfg' in result
''' 