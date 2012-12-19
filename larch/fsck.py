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
import tracing
import ttystatus

import larch


class Error(larch.Error):

    def __init__(self, msg):
        self.msg = 'Assertion failed: %s' % msg


class WorkItem(object):

    '''A work item for fsck.
    
    Subclass can optionally set the ``name`` attribute; the class name
    is used by default.
    
    '''

    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return self.__class__.__name__
    
    def do(self):
        pass

    def warning(self, msg):
        self.fsck.warning('warning: %s: %s' % (self.name, msg))

    def error(self, msg):
        self.fsck.error('ERROR: %s: %s' % (self.name, msg))

    def get_node(self, node_id):
        tracing.trace('node_id=%s' % node_id)
        try:
            return self.fsck.forest.node_store.get_node(node_id)
        except larch.NodeMissing:
            self.error(
                'forest %s: node %s is missing' %
                    (self.fsck.forest_name, node_id))

    def start_modification(self, node):
        self.fsck.forest.node_store.start_modification(node)

    def put_node(self, node):
        tracing.trace('node.id=%s' % node.id)
        return self.fsck.forest.node_store.put_node(node)


class CheckIndexNode(WorkItem):

    def __init__(self, fsck, node):
        self.fsck = fsck
        self.node = node
        self.name = 'node %s in %s' % (self.node.id, self.fsck.forest_name)

    def do(self):
        tracing.trace('node.id=%s' % self.node.id)

        if type(self.node) != larch.IndexNode:
            self.error(
                'forest %s: node %s: '
                'Expected to get an index node, got %s instead' %
                    (self.fsck.forest_name, self.node.id, type(self.node)))
            return

        if len(self.node) == 0:
            self.error('forest %s: index node %s: No children' %
                (self.fsck.forest_name, self.node.id))
            return

        # Increase refcounts for all children, and check that the child
        # nodes exist. If the children are index nodes, create work
        # items to check those. Leaf nodes get no further checking.

        drop_keys = []
        for key in self.node:
            child_id = self.node[key]
            seen_already = child_id in self.fsck.refcounts
            self.fsck.count(child_id)
            if not seen_already:
                child = self.get_node(child_id)
                if child is None:
                    drop_keys.append(key)
                elif type(child) == larch.IndexNode:
                    yield CheckIndexNode(self.fsck, child)

        # Fix references to missing children by dropping them.
        if self.fsck.fix and drop_keys:
            self.start_modification(self.node)
            for key in drop_keys:
                self.node.remove(key)
            self.put_node(self.node)


class CheckForest(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.name = 'forest %s' % self.fsck.forest_name

    def do(self):
        for tree in self.fsck.forest.trees:
            self.fsck.count(tree.root.id)
            root_node = self.get_node(tree.root.id)
            tracing.trace('root_node.id=%s' % root_node.id)
            yield CheckIndexNode(self.fsck, root_node)


class CheckRefcounts(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.name = 'refcounts in %s' % self.fsck.forest_name

    def do(self):
        for node_id in self.fsck.refcounts:
            refcount = self.fsck.forest.node_store.get_refcount(node_id)
            if refcount != self.fsck.refcounts[node_id]:
                self.error(
                    'forest %s: node %s: refcount is %s but should be %s' %
                        (self.fsck.forest_name,
                         node_id,
                         refcount,
                         self.fsck.refcounts[node_id]))
                if self.fsck.fix:
                    self.fsck.forest.node_store.set_refcount(
                        node_id, self.fsck.refcounts[node_id])


class CommitForest(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.name = 'committing fixes to %s' % self.fsck.forest_name

    def do(self):
        tracing.trace('committing changes to %s' % self.fsck.forest_name)
        self.fsck.forest.commit()


class Fsck(object):

    '''Verify internal consistency of a larch.Forest.'''
    
    def __init__(self, forest, warning, error, fix):
        self.forest = forest
        self.forest_name = getattr(
            forest.node_store, 'dirname', 'in-memory forest')
        self.warning = warning
        self.error = error
        self.fix = fix
        self.refcounts = {}

    def find_work(self):
        yield CheckForest(self)
        yield CheckRefcounts(self)
        if self.fix:
            yield CommitForest(self)

    def count(self, node_id):
        self.refcounts[node_id] = self.refcounts.get(node_id, 0) + 1

