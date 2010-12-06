#!/usr/bin/python
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


import logging
import sys

import btree


class BtreeFsck(object):

    '''Verify that a B-tree is logically correct.'''
    
    def __init__(self, dirname, node_size, key_size):
        codec = btree.NodeCodec(key_size)
        self.ns = btree.NodeStoreDisk(dirname, node_size, codec)
        self.minkey = '\x00' * key_size
        self.maxkey = '\xff' * key_size

    def _assert(self, cond, msg1, msg2):
        if not cond:
            if msg1:
                logging.error(msg1)
            logging.error('not true: %s' % msg2)

    def assert_equal(self, a, b, msg=''):
        self._assert(a == b, msg, '%s == %s' % (repr(a), repr(b)))

    def assert_greater(self, a, b, msg=''):
        self._assert(a > b, msg, '%s > %s' % (repr(a), repr(b)))

    def assert_ge(self, a, b, msg=''):
        self._assert(a >= b, msg, '%s >= %s' % (repr(a), repr(b)))

    def assert_in_range(self, a, lo, hi, msg=''):
        self._assert(lo <= a <= hi, msg, 
                     '%s <= %s <= %s' % (repr(lo), repr(a), repr(hi)))
    
    def check_index_node(self, node_id, minkey, maxkey):
        logging.info('checking index node: %d' % node_id)
        node = self.ns.get_node(node_id)
        keys = node.keys()

        self.assert_greater(self.ns.get_refcount(node_id), 0, 
                            'node refcount must be > 0')
        self.assert_greater(len(keys), 0, 'index node must have children')
        self.assert_equal(sorted(keys), keys, 'node keys must be sorted')
        self.assert_equal(sorted(set(keys)), keys, 'node keys must be unique')
        self.assert_in_range(keys[0], minkey, maxkey,
                             'keys must be within range')
        if len(keys) > 1:
            self.assert_in_range(keys[-1], minkey, maxkey,
                                 'keys must be within range')

        for i, key in enumerate(keys):
            child_id = node[key]
            child = self.ns.get_node(child_id)
            next_key = (keys + [maxkey])[i]
            if type(child) == btree.IndexNode:
                self.check_index(child_id, key, next_key)
            
    def check_root_node(self, root_id):
        logging.info('checking root node: %d' % root_id)
        root = self.ns.get_node(root_id)
        self.assert_equal(self.ns.get_refcount(root_id), 1, 
                          'root refcount should be 1')
        
    def check_tree(self, root_id):
        logging.info('checking tree: %d' % root_id)
        self.check_root_node(root_id)
        self.check_index_node(root_id, self.minkey, self.maxkey)

    def forest_root_ids(self):
        string = self.ns.get_metadata('root_ids')
        return [int(x) for x in string.split(',')]

    def check_forest(self):
        for root_id in self.forest_root_ids():
            self.check_tree(root_id)


def main():
    dirname = sys.argv[1]
    node_size = int(sys.argv[2])
    key_size = int(sys.argv[3])
    
    logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', 
                        level=logging.DEBUG)
    logging.info('btree fsck')
    logging.info('forest: %s' % dirname)
    logging.info('node size: %d' % node_size)
    logging.info('key size: %d' % key_size)

    fsck = BtreeFsck(dirname, node_size, key_size)
    fsck.check_forest()


if __name__ == '__main__':
    main()
