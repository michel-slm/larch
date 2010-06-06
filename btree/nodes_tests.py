# Copyright 2010  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import unittest

import btree


class NodeTests(unittest.TestCase):

    def setUp(self):
        self.node_id = 12765
        self.pairs = [('key2', 'value2'), ('key1', 'value1')]
        self.pairs.sort()
        self.node = btree.nodes.Node(self.node_id, self.pairs)

    def test_has_id(self):
        self.assertEqual(self.node.id, self.node_id)

    def test_has_no_size(self):
        self.assertEqual(self.node.size, None)

    def test_has_each_pair(self):
        for key, value in self.pairs:
            self.assertEqual(self.node[key], value)

    def test_raises_keyerror_for_missing_key(self):
        self.assertRaises(KeyError, self.node.__getitem__, 'notexist')

    def test_contains_each_key(self):
        for key, value in self.pairs:
            self.assert_(key in self.node)

    def test_does_not_contain_wrong_key(self):
        self.assertFalse('notexist' in self.node)

    def test_is_equal_to_itself(self):
        self.assert_(self.node == self.node)

    def test_iterates_over_all_keys(self):
        self.assertEqual([k for k in self.node], 
                         sorted(k for k, v in self.pairs))

    def test_has_correct_length(self):
        self.assertEqual(len(self.node), len(self.pairs))

    def test_has_keys(self):
        self.assertEqual(self.node.keys(), sorted(k for k, v in self.pairs))

    def test_sorts_keys(self):
        self.assertEqual(self.node.keys(), sorted(k for k, v in self.pairs))

    def test_has_values(self):
        self.assertEqual(self.node.values(), 
                         [v for k, v in sorted(self.pairs)])

    def test_returns_correct_first_key(self):
        self.assertEqual(self.node.first_key(), 'key1')

    def test_returns_pairs(self):
        self.assertEqual(self.node.pairs(), sorted(self.pairs))

    def test_does_not_return_excluded_pairs(self):
        self.assertEqual(self.node.pairs(exclude=['key1']), 
                         [('key2', 'value2')])


class IndexNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf1 = btree.LeafNode(0, [('bar', 'bar')])
        self.leaf2 = btree.LeafNode(1, [('foo', 'foo')])
        self.index_id = 1234
        self.index = btree.IndexNode(self.index_id,
                                     [('bar', self.leaf1.id), 
                                      ('foo', self.leaf2.id)])

    def test_finds_child_containing_key(self):
        self.assertEqual(self.index.find_key_for_child_containing('barbar'),
                         'bar')

    def test_returns_none_when_no_child_contains_key(self):
        self.assertEqual(self.index.find_key_for_child_containing('a'), None)

