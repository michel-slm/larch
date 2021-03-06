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
import os
import StringIO
import struct
import tempfile
import tracing

import larch


def encode_refcounts(refcounts, start_id, how_many, keys):
    fmt = '!QH' + 'H' * how_many
    args = [start_id, how_many] + ([0] * how_many)
    for key in keys:
        args[2 + key - start_id] = refcounts[key]
    return struct.pack(fmt, *args)
    
def decode_refcounts(encoded):
    n = struct.calcsize('!QH')
    start_id, how_many = struct.unpack('!QH', encoded[:n])
    counts = struct.unpack('!' + 'H' * how_many, encoded[n:])
    return zip(range(start_id, start_id + how_many), counts)


class RefcountStore(object):

    '''Store node reference counts.
    
    Each node has a reference count, which gets stored on disk.
    Reference counts are grouped into blocks of ``self.per_group`` counts,
    and each group is stored in its own file. This balances the
    per-file overhead with the overhead of keeping a lot of unneeded
    reference counts in memory.
    
    Only those blocks that are used get loaded into memory. Blocks
    that are full of zeroes are not stored in files, to save disk space.
    
    '''

    per_group = 2**15
    refcountdir = 'refcounts'

    def __init__(self, node_store):
        self.node_store = node_store
        self.refcounts = dict()
        self.dirty = set()

    def get_refcount(self, node_id):
        '''Return reference count for a given node.'''
        if node_id not in self.refcounts:
            group = self._load_refcount_group(self._start_id(node_id))
            if group is None:
                self.refcounts[node_id] = 0
            else:
                for x, count in group:
                    if x not in self.dirty:
                        self.refcounts[x] = count
        return self.refcounts[node_id]

    def set_refcount(self, node_id, refcount):
        '''Set the reference count for a given node.'''
        tracing.trace('setting refcount for %s to %s' % (node_id, refcount))
        self.refcounts[node_id] = refcount
        self.dirty.add(node_id)

    def save_refcounts(self):
        '''Save all modified refcounts.'''
        tracing.trace('saving refcounts (len(dirty) = %s)' % 
                            (len(self.dirty)))
        if self.dirty:
            dirname = os.path.join(self.node_store.dirname, self.refcountdir)
            if not self.node_store.journal.exists(dirname):
                self.node_store.journal.makedirs(dirname)
            ids = sorted(self.dirty)
            all_ids_in_memory = set(self.refcounts.keys())
            for start_id in range(self._start_id(ids[0]), 
                                  self._start_id(ids[-1]) + 1, 
                                  self.per_group):

                all_ids_in_group = set(
                    range(start_id, start_id + self.per_group))
                keys = all_ids_in_group.intersection(all_ids_in_memory)
                if keys:
                    encoded = encode_refcounts(
                        self.refcounts, start_id, self.per_group, keys)
                    filename = self._group_filename(start_id)
                    self.node_store.journal.overwrite_file(filename, encoded)

        # We re-initialize these so that they don't grow indefinitely.
        self.refcounts = dict()
        self.dirty = set()

    def _load_refcount_group(self, start_id):
        filename = self._group_filename(start_id)
        if self.node_store.journal.exists(filename):
            encoded = self.node_store.journal.cat(filename)
            return decode_refcounts(encoded)

    def _group_filename(self, start_id):
        return os.path.join(self.node_store.dirname, self.refcountdir,
                            'refcounts-%d' % start_id)

    def _start_id(self, node_id):
        return (node_id / self.per_group) * self.per_group
