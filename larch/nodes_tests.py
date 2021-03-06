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

import larch


class FrozenNodeTests(unittest.TestCase):

    def test_node_id_is_in_error_message(self):
        node = larch.nodes.Node(123, [], [])
        e = larch.FrozenNode(node)
        self.assert_('123' in str(e))


class NodeTests(unittest.TestCase):

    def setUp(self):
        self.node_id = 12765
        self.pairs = [('key2', 'value2'), ('key1', 'value1')]
        self.pairs.sort()
        self.keys = [k for k, v in self.pairs]
        self.values = [v for k, v in self.pairs]
        self.node = larch.nodes.Node(self.node_id, self.keys, self.values)

    def test_has_id(self):
        self.assertEqual(self.node.id, self.node_id)

    def test_empty_node_is_still_true(self):
        empty = larch.nodes.Node(self.node_id, [], [])
        self.assert_(empty)

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

    def test_returns_keys_and_values(self):
        self.assertEqual(self.node.keys(), self.keys)
        self.assertEqual(self.node.values(), self.values)

    def test_adds_key_value_pair_to_empty_node(self):
        node = larch.nodes.Node(0, [], [])
        node.add('foo', 'bar')
        self.assertEqual(node.keys(), ['foo'])
        self.assertEqual(node.values(), ['bar'])
        self.assertEqual(node['foo'], 'bar')

    def test_adds_key_value_pair_to_end_of_node_of_one_element(self):
        node = larch.nodes.Node(0, ['foo'], ['bar'])
        node.add('foo2', 'bar2')
        self.assertEqual(node.keys(), ['foo', 'foo2'])
        self.assertEqual(node.values(), ['bar', 'bar2'])
        self.assertEqual(node['foo2'], 'bar2')

    def test_adds_key_value_pair_to_beginning_of_node_of_one_element(self):
        node = larch.nodes.Node(0, ['foo'], ['bar'])
        node.add('bar', 'bar')
        self.assertEqual(node.keys(), ['bar', 'foo'])
        self.assertEqual(node.values(), ['bar', 'bar'])
        self.assertEqual(node['bar'], 'bar')

    def test_adds_key_value_pair_to_middle_of_node_of_two_elements(self):
        node = larch.nodes.Node(0, ['bar', 'foo'], ['bar', 'bar'])
        node.add('duh', 'bar')
        self.assertEqual(node.keys(), ['bar', 'duh', 'foo'])
        self.assertEqual(node.values(), ['bar', 'bar', 'bar'])
        self.assertEqual(node['duh'], 'bar')

    def test_add_replaces_value_for_existing_key(self):
        node = larch.nodes.Node(0, ['bar', 'foo'], ['bar', 'bar'])
        node.add('bar', 'xxx')
        self.assertEqual(node.keys(), ['bar', 'foo'])
        self.assertEqual(node.values(), ['xxx', 'bar'])
        self.assertEqual(node['bar'], 'xxx')

    def test_add_resets_cached_size(self):
        node = larch.nodes.Node(0, [], [])
        node.size = 1234
        node.add('foo', 'bar')
        self.assertEqual(node.size, None)

    def test_removes_first_key(self):
        node = larch.nodes.Node(0, ['bar', 'duh', 'foo'], 
                                   ['bar', 'bar', 'bar'])
        node.remove('bar')
        self.assertEqual(node.keys(), ['duh', 'foo'])
        self.assertEqual(node.values(), ['bar', 'bar'])
        self.assertRaises(KeyError, node.__getitem__, 'bar')

    def test_removes_last_key(self):
        node = larch.nodes.Node(0, ['bar', 'duh', 'foo'], 
                                   ['bar', 'bar', 'bar'])
        node.remove('foo')
        self.assertEqual(node.keys(), ['bar', 'duh'])
        self.assertEqual(node.values(), ['bar', 'bar'])
        self.assertRaises(KeyError, node.__getitem__, 'foo')

    def test_removes_middle_key(self):
        node = larch.nodes.Node(0, ['bar', 'duh', 'foo'], 
                                   ['bar', 'bar', 'bar'])
        node.remove('duh')
        self.assertEqual(node.keys(), ['bar', 'foo'])
        self.assertEqual(node.values(), ['bar', 'bar'])
        self.assertRaises(KeyError, node.__getitem__, 'duh')

    def test_raises_exception_when_removing_unknown_key(self):
        node = larch.nodes.Node(0, ['bar', 'duh', 'foo'], 
                                   ['bar', 'bar', 'bar'])
        self.assertRaises(KeyError, node.remove, 'yo')

    def test_remove_resets_cached_size(self):
        node = larch.nodes.Node(0, ['foo'], ['bar'])
        node.size = 1234
        node.remove('foo')
        self.assertEqual(node.size, None)

    def test_removes_index_range(self):
        node = larch.nodes.Node(0, ['bar', 'duh', 'foo'], 
                                   ['bar', 'bar', 'bar'])
        node.size = 12375654
        node.remove_index_range(1, 5)
        self.assertEqual(node.keys(), ['bar'])
        self.assertEqual(node.values(), ['bar'])
        self.assertEqual(node.size, None)

    def test_finds_keys_in_range(self):
        # The children's keys are 'bar' and 'foo'. We need to test for
        # every combination of minkey and maxkey being less than, equal,
        # or greater than either child key (as long as minkey <= maxkey).
        
        node = larch.LeafNode(0, ['bar', 'foo'], ['bar', 'foo']) 
        find = node.find_keys_in_range

        self.assertEqual(find('aaa', 'aaa'), [])
        self.assertEqual(find('aaa', 'bar'), ['bar'])
        self.assertEqual(find('aaa', 'ccc'), ['bar'])
        self.assertEqual(find('aaa', 'foo'), ['bar', 'foo'])
        self.assertEqual(find('aaa', 'ggg'), ['bar', 'foo'])

        self.assertEqual(find('bar', 'bar'), ['bar'])
        self.assertEqual(find('bar', 'ccc'), ['bar'])
        self.assertEqual(find('bar', 'foo'), ['bar', 'foo'])
        self.assertEqual(find('bar', 'ggg'), ['bar', 'foo'])

        self.assertEqual(find('ccc', 'ccc'), [])
        self.assertEqual(find('ccc', 'foo'), ['foo'])
        self.assertEqual(find('ccc', 'ggg'), ['foo'])

        self.assertEqual(find('foo', 'foo'), ['foo'])
        self.assertEqual(find('foo', 'ggg'), ['foo'])

        self.assertEqual(find('ggg', 'ggg'), [])

    def test_finds_no_potential_range_in_empty_node(self):
        node = larch.LeafNode(0, [], [])
        self.assertEqual(node.find_potential_range('aaa', 'bbb'), (None, None))

    def test_finds_potential_ranges(self):
        # The children's keys are 'bar' and 'foo'. We need to test for
        # every combination of minkey and maxkey being less than, equal,
        # or greater than either child key (as long as minkey <= maxkey).
        
        node = larch.LeafNode(0, ['bar', 'foo'], ['bar', 'foo'])
        find = node.find_potential_range

        self.assertEqual(find('aaa', 'aaa'), (None, None))
        self.assertEqual(find('aaa', 'bar'), (0, 0))
        self.assertEqual(find('aaa', 'ccc'), (0, 0))
        self.assertEqual(find('aaa', 'foo'), (0, 1))
        self.assertEqual(find('aaa', 'ggg'), (0, 1))

        self.assertEqual(find('bar', 'bar'), (0, 0))
        self.assertEqual(find('bar', 'ccc'), (0, 0))
        self.assertEqual(find('bar', 'foo'), (0, 1))
        self.assertEqual(find('bar', 'ggg'), (0, 1))

        self.assertEqual(find('ccc', 'ccc'), (0, 0))
        self.assertEqual(find('ccc', 'foo'), (0, 1))
        self.assertEqual(find('ccc', 'ggg'), (0, 1))

        self.assertEqual(find('foo', 'foo'), (1, 1))
        self.assertEqual(find('foo', 'ggg'), (1, 1))

        # This one is a bit special. The last key may refer to a
        # child that is an index node, so it _might_ have keys
        # in the desired range.
        self.assertEqual(find('ggg', 'ggg'), (1, 1))

    def test_is_not_frozen(self):
        self.assertEqual(self.node.frozen, False)

    def test_freezing_makes_add_raise_error(self):
        self.node.frozen = True
        self.assertRaises(larch.FrozenNode, self.node.add, 'foo', 'bar')

    def test_freezing_makes_remove_raise_error(self):
        self.node.frozen = True
        self.assertRaises(larch.FrozenNode, self.node.remove, 'foo')

    def test_freezing_makes_remove_index_range_raise_error(self):
        self.node.frozen = True
        self.assertRaises(larch.FrozenNode, self.node.remove_index_range, 0, 1)


class IndexNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf1 = larch.LeafNode(0, ['bar'], ['bar'])
        self.leaf2 = larch.LeafNode(1, ['foo'], ['foo'])
        self.index_id = 1234
        self.index = larch.IndexNode(self.index_id, ['bar', 'foo'],
                                     [self.leaf1.id, self.leaf2.id])

    def test_find_key_for_child_containing(self):
        find = self.index.find_key_for_child_containing

        self.assertEqual(find('aaa'), None)
        self.assertEqual(find('bar'), 'bar')
        self.assertEqual(find('bar2'), 'bar')
        self.assertEqual(find('foo'), 'foo')
        self.assertEqual(find('foo2'), 'foo')

    def test_returns_none_when_no_child_contains_key(self):
        self.assertEqual(self.index.find_key_for_child_containing('a'), None)

    def test_finds_no_key_when_node_is_empty(self):
        empty = larch.IndexNode(0, [], [])
        self.assertEqual(empty.find_key_for_child_containing('f00'), None)

    def test_finds_no_children_in_range_when_empty(self):
        empty = larch.IndexNode(0, [], [])
        self.assertEqual(empty.find_children_in_range('bar', 'foo'), [])

    def test_finds_children_in_ranges(self):
        # The children's keys are 'bar' and 'foo'. We need to test for
        # every combination of minkey and maxkey being less than, equal,
        # or greater than either child key (as long as minkey <= maxkey).
        
        find = self.index.find_children_in_range
        bar = self.leaf1.id
        foo = self.leaf2.id

        self.assertEqual(find('aaa', 'aaa'), [])
        self.assertEqual(find('aaa', 'bar'), [bar])
        self.assertEqual(find('aaa', 'ccc'), [bar])
        self.assertEqual(find('aaa', 'foo'), [bar, foo])
        self.assertEqual(find('aaa', 'ggg'), [bar, foo])

        self.assertEqual(find('bar', 'bar'), [bar])
        self.assertEqual(find('bar', 'ccc'), [bar])
        self.assertEqual(find('bar', 'foo'), [bar, foo])
        self.assertEqual(find('bar', 'ggg'), [bar, foo])

        self.assertEqual(find('ccc', 'ccc'), [bar])
        self.assertEqual(find('ccc', 'foo'), [bar, foo])
        self.assertEqual(find('ccc', 'ggg'), [bar, foo])

        self.assertEqual(find('foo', 'foo'), [foo])
        self.assertEqual(find('foo', 'ggg'), [foo])

        self.assertEqual(find('ggg', 'ggg'), [foo])

