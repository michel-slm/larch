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


import btree


class Forest(object):

    '''A collection of BTrees in the same node store.'''

    def __init__(self, node_store):
        self.node_store = node_store
        self.trees = []
        self.last_id = 0
        self.read_metadata()

    def read_metadata(self):
        keys = self.node_store.get_metadata_keys()
        if 'last_id' in keys:
            self.last_id = int(self.node_store.get_metadata('last_id'))
        if 'root_ids' in keys:
            s = self.node_store.get_metadata('root_ids')
            root_ids = [int(x) for x in s.split(',')]
            self.trees = [btree.BTree(self, self.node_store, root_id)
                          for root_id in root_ids]
    
    def new_id(self):
        '''Generate next node id for this forest.'''
        self.last_id += 1
        return self.last_id

    def new_tree(self, old=None):
        '''Create a new tree.

        If old is None, a completely new tree is created. Otherwise,
        a clone of an existing one is created.

        '''

        if old:
            t = btree.BTree(self, self.node_store, old.root_id)
            t.increment(t.root_id)
        else:
            t = btree.BTree(self, self.node_store, None)
        self.trees.append(t)
        return t

    def remove_tree(self, tree):
        '''Remove a tree from the forest.'''
        self.trees.remove(tree)

    def commit(self):
        '''Make sure all changes are stored into the node store.'''
        self.node_store.set_metadata('last_id', self.last_id)
        root_ids = ','.join('%d'% t.root_id for t in self.trees)
        self.node_store.set_metadata('root_ids', root_ids)
        self.node_store.save_metadata()
        self.node_store.save_refcounts()
