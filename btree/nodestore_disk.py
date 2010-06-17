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


import ConfigParser
import logging
import lru
import os
import StringIO
import struct

import btree


class RefcountStore(object):

    '''Store node reference counts.'''

    per_group = 2**15
    refcountdir = 'refcounts'

    def __init__(self, node_store):
        self.node_store = node_store
        self.refcounts = dict()
        self.dirty = set()

    def get_refcount(self, node_id):
        if node_id not in self.refcounts:
            group = self.load_refcount_group(self.group(node_id))
            if group is None:
                self.refcounts[node_id] = 0
            else:
                for x, count in group:
                    if x not in self.dirty:
                        self.refcounts[x] = count
        return self.refcounts[node_id]

    def set_refcount(self, node_id, refcount):
        if refcount == 0 and refcount in self.refcounts:
            del self.refcounts[node_id]
        else:
            self.refcounts[node_id] = refcount
        self.dirty.add(node_id)

    def save_refcounts(self):
        if self.dirty:
            level = logging.getLogger().getEffectiveLevel()
            if level <= logging.DEBUG: # pragma: no cover
                logging.debug('btree.NodeStoreDisk.RefcountStore: '
                              '%d refcounts in memory (%d zero), %d dirty' %
                              (len(self.refcounts), 
                               sum(1 
                                   for x in self.refcounts 
                                   if self.refcounts[x] == 0),
                               len(self.dirty)))
            self.node_store.mkdir(os.path.join(self.node_store.dirname,
                                               self.refcountdir))
            ids = sorted(self.dirty)
            for start_id in range(self.group(ids[0]), self.group(ids[-1]) + 1, 
                                  self.per_group):
                encoded = self.encode_refcounts(start_id, self.per_group)
                filename = self.group_filename(start_id)
                self.node_store.write_file(filename, encoded)
            self.dirty.clear()

    def load_refcount_group(self, start_id):
        filename = self.group_filename(start_id)
        if self.node_store.file_exists(filename):
            encoded = self.node_store.read_file(filename)
            return self.decode_refcounts(encoded)

    def group_filename(self, start_id):
        return os.path.join(self.node_store.dirname, self.refcountdir,
                            'refcounts-%d' % start_id)

    def group(self, node_id):
        return (node_id / self.per_group) * self.per_group

    def encode_refcounts(self, start_id, how_many):
        fmt = '!QH' + 'H' * how_many
        args = ([start_id, how_many] +
                [self.refcounts.get(i, 0)
                 for i in range(start_id, start_id + how_many)])
        return struct.pack(fmt, *args)

    def decode_refcounts(self, encoded):
        n = struct.calcsize('!QH')
        start_id, how_many = struct.unpack('!QH', encoded[:n])
        counts = struct.unpack('!' + 'H' * how_many, encoded[n:])
        return [(start_id + i, counts[i]) for i in range(how_many)]


class UploadQueue(object):

    def __init__(self, really_put, max_length):
        self.really_put = really_put
        self.max = max_length
        # Together, node_before and node_after form a random access
        # double-linked sequence. None used as the sentinel on both ends.
        self.node_before = dict()
        self.node_after = dict()
        self.node_before[None] = None
        self.node_after[None] = None
        self.ids = dict()  # maps node.id to node
        
    def put(self, node):
        before = self.node_before[None]
        self.node_before[None] = node
        self.node_before[node] = before
        self.node_after[before] = node
        self.node_after[node] = None
        self.ids[node.id] = node
        while len(self.ids) > self.max:
            self._push_oldest()

    def _push_oldest(self):
        node = self.node_after[None]
        self.remove(node.id)
        self.really_put(node)

    def push(self):
        while self.ids:
            self._push_oldest()
    
    def remove(self, node_id):
        if node_id in self.ids:
            node = self.ids[node_id]
            before = self.node_before[node]
            after = self.node_after[node]
            self.node_before[after] = before
            self.node_after[before] = after
            del self.node_before[node]
            del self.node_after[node]
            del self.ids[node_id]
            return True
        else:
            return False
        
    def list_ids(self):
        return self.ids.keys()
        
    def get(self, node_id):
        return self.ids.get(node_id)

class NodeStoreDisk(btree.NodeStore):

    '''An implementation of btree.NodeStore API for on-disk storage.
    
    The caller will specify a directory in which the nodes will be stored.
    Each node is stored in its own file, named after the node identifier.

    This class can be subclassed to allow filesystem operations be
    overridden. The subclass needs to override the following methods:

    * read_file
    * write_file
    * file_exists
    * rename_file
    * remove_file
    * listdir
    
    '''

    refcounts_per_group = 2**15
    nodedir = 'nodes'

    def __init__(self, dirname, node_size, codec, upload_max=64):
        btree.NodeStore.__init__(self, node_size, codec)
        self.dirname = dirname
        self.metadata_name = os.path.join(dirname, 'metadata')
        self.metadata = None
        self.rs = RefcountStore(self)
        self.cache = lru.LRUCache(100)
        self.upload_max = upload_max
        self.upload_queue = UploadQueue(self._really_put_node, self.upload_max)

    def mkdir(self, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    def read_file(self, filename):
        return file(filename).read()

    def write_file(self, filename, contents):
        file(filename, 'w').write(contents)

    def file_exists(self, filename):
        return os.path.exists(filename)

    def rename_file(self, old, new):
        os.rename(old, new)

    def remove_file(self, filename):
        os.remove(filename)

    def listdir(self, dirname):
        return os.listdir(dirname)

    def _load_metadata(self):
        if self.metadata is None:
            self.metadata = ConfigParser.ConfigParser()
            self.metadata.add_section('metadata')
            if self.file_exists(self.metadata_name):
                data = self.read_file(self.metadata_name)
                f = StringIO.StringIO(data)
                self.metadata.readfp(f)

    def get_metadata_keys(self):
        self._load_metadata()
        return self.metadata.options('metadata')
        
    def get_metadata(self, key):
        self._load_metadata()
        if self.metadata.has_option('metadata', key):
            return self.metadata.get('metadata', key)
        else:
            raise KeyError(key)
        
    def set_metadata(self, key, value):
        self._load_metadata()
        self.metadata.set('metadata', key, value)

    def remove_metadata(self, key):
        self._load_metadata()
        if self.metadata.has_option('metadata', key):
            self.metadata.remove_option('metadata', key)
        else:
            raise KeyError(key)

    def save_metadata(self):
        self._load_metadata()
        f = StringIO.StringIO()
        self.metadata.write(f)
        self.write_file(self.metadata_name + '_new', f.getvalue())
        self.rename_file(self.metadata_name + '_new', self.metadata_name)

    def pathname(self, node_id):
        return os.path.join(self.dirname, self.nodedir, '%d.node' % node_id)
        
    def put_node(self, node):
        self.cache.add(node.id, node)
        self.upload_queue.put(node)

    def push_upload_queue(self):
        self.upload_queue.push()

    def _really_put_node(self, node):
        encoded_node = self.codec.encode(node)
        if len(encoded_node) > self.node_size:
            raise btree.NodeTooBig(node.id, len(encoded_node))
        name = self.pathname(node.id)
        if self.file_exists(name):
            raise btree.NodeExists(node.id)
        self.mkdir(os.path.join(self.dirname, self.nodedir))
        self.write_file(name, encoded_node)
        
    def get_node(self, node_id):
        node = self.cache.get(node_id)
        if node is not None:
            return node

        node = self.upload_queue.get(node_id)
        if node is not None:
            return node

        name = self.pathname(node_id)
        if self.file_exists(name):
            encoded = self.read_file(name)
            node = self.codec.decode(encoded)
            self.cache.add(node.id, node)
            return node
        else:
            raise btree.NodeMissing(node_id)
    
    def remove_node(self, node_id):
        self.cache.remove(node_id)
        if self.upload_queue.remove(node_id):
            return

        name = self.pathname(node_id)
        if self.file_exists(name):
            self.remove_file(name)
        else:
            raise btree.NodeMissing(node_id)
        
    def list_nodes(self):
        queued = self.upload_queue.list_ids()
        try:
            basenames = self.listdir(os.path.join(self.dirname, self.nodedir))
        except OSError:
            basenames = []
        nodenames = [x for x in basenames if x.endswith('.node')]
        uploaded = [int(x[:-len('.node')]) for x in nodenames]
        return queued + uploaded

    def get_refcount(self, node_id):
        return self.rs.get_refcount(node_id)

    def set_refcount(self, node_id, refcount):
        self.rs.set_refcount(node_id, refcount)

    def save_refcounts(self):
        self.rs.save_refcounts()
