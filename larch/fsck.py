# Copyright 2010, 2011  Lars Wirzenius
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


import logging
import sys
import ttystatus

import larch


class Fsck(object):

    '''Verify that a B-tree is logically correct.'''
    
    def __init__(self, status, forest):
        self.status = status
        self.forest = forest
        self.ns = self.forest.node_store
        self.minkey = '\x00' * self.ns.codec.key_bytes
        self.maxkey = '\xff' * self.ns.codec.key_bytes

    def error(self, msg):
        self.status.notify('ERROR: %s' % msg)

    def info(self, msg):
        self.status.notify(msg)
        
    def _assert(self, cond, msg1, msg2):
        if not cond:
            if msg1:
                self.error(msg1)
            self.error('not true: %s' % msg2)

    def assert_equal(self, a, b, msg=''):
        self._assert(a == b, msg, '%s == %s' % (repr(a), repr(b)))

    def assert_greater(self, a, b, msg=''):
        self._assert(a > b, msg, '%s > %s' % (repr(a), repr(b)))

    def assert_ge(self, a, b, msg=''):
        self._assert(a >= b, msg, '%s >= %s' % (repr(a), repr(b)))

    def assert_in_keyrange(self, a, lo, hi, msg=''):
        '''half-open range: lo <= a < hi'''
        self._assert(lo <= a < hi, msg, 
                     '%s <= %s < %s' % (repr(lo), repr(a), repr(hi)))

    def assert_in(self, value, collection, msg=''):
        self._assert(value in collection, msg, 
                     '%s in %s' % (repr(value), repr(collection)))

    def check_node(self, node, minkey, maxkey):
        keys = node.keys()
        self.assert_greater(self.ns.get_refcount(node.id), 0, 
                            'node refcount must be > 0')
        self.assert_greater(len(keys), 0, 'node must have children')
        self.assert_equal(sorted(keys), keys, 'node keys must be sorted')
        self.assert_equal(sorted(set(keys)), keys, 'node keys must be unique')
        self.assert_in_keyrange(keys[0], minkey, maxkey,
                                'node keys must be within range')
        if len(keys) > 1:
            self.assert_in_keyrange(keys[-1], minkey, maxkey,
                                    'keys must be within range')
    
    def check_leaf_node(self, node, minkey, maxkey):
        pass
    
    def check_index_node(self, node, minkey, maxkey):
        keys = node.keys()
        child0_id = node[keys[0]]
        try:
            child0 = self.ns.get_node(child0_id)
        except larch.NodeMissing:
            self.error('child missing: %d' % child0_id)
            self.error('index node not checked: %d' % node.id)
            return
        child_type = type(child0)

        for key in keys:
            child = self.ns.get_node(node[key])
            
            self.assert_in(type(child), [larch.IndexNode, larch.LeafNode],
                           'type must be index or leaf')
            self.assert_equal(type(child), child_type,
                              'all children must have same type')
            
    def check_root_node(self, root):
        self.assert_equal(self.ns.get_refcount(root.id), 1, 
                          'root refcount should be 1')
        self.assert_equal(type(root), larch.IndexNode, 'root must be an index')
        
    def walk(self, node, minkey, maxkey):
        if node.id in self.checked:
            return
        self.checked.add(node.id)
        yield node, minkey, maxkey
        if type(node) is larch.IndexNode:
            keys = node.keys()
            next_keys = keys[1:] + [maxkey]
            for i in range(len(keys)):
                child_id = node[keys[i]]
                try:
                    child = self.ns.get_node(child_id)
                except larch.NodeMissing:
                    self.error('node missing: %d' % child_id)
                else:
                    for t in self.walk(child, keys[i], next_keys[i]):
                        yield t
        
    def check_tree(self, root_id):
        try:
            root = self.ns.get_node(root_id)
        except larch.NodeMissing:
            self.error('root node missing: %d' % root_id)
        else:
            self.check_root_node(root)
            for node, min2, max2 in self.walk(root, self.minkey, self.maxkey):
                self.status['node_id'] = str(node.id)
                self.status['nodes_done'] += 1
                self.check_node(node, min2, max2)
                if type(node) is larch.IndexNode:
                    self.check_index_node(node, min2, max2)
                else:
                    self.check_leaf_node(node, min2, max2)

    def forest_root_ids(self):
        string = self.ns.get_metadata('root_ids')
        return [int(x) for x in string.split(',')]

    def check_forest(self):
        self.info('larch fsck')

        nodes = self.ns.list_nodes()
        self.info('nodes: %d' % len(nodes))
        
        self.status['node_id'] = '---'
        self.status['nodes_done'] = 0
        self.status['nodes_total'] = len(nodes)

        self.checked = set()
        for root_id in self.forest_root_ids():
            self.check_tree(root_id)
        
        self.status.finish()

