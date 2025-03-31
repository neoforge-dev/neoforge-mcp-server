'''Tests for the code parser.'''

import unittest
from server.code_understanding.parser import MockTree, MockNode, CodeParser


class TestMockTree(unittest.TestCase):
    def test_walk_empty(self):
        tree = MockTree(None)
        walked = list(tree.walk())
        self.assertEqual(walked, [])

    def test_walk_with_root(self):
        root = MockNode(type='module', text='root')
        child = MockNode(type='child', text='child')
        root.children.append(child)
        tree = MockTree(root)
        walked = list(tree.walk())
        self.assertEqual([node.text for node in walked], ['root', 'child'])


class TestCodeParser(unittest.TestCase):
    def test_parse_valid_code(self):
        cp = CodeParser()
        tree = cp.parse("a = 42")
        self.assertIsNotNone(tree)
        self.assertEqual(tree.root_node.type, 'module')


if __name__ == '__main__':
    unittest.main() 