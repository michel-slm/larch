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
import tempfile

import btree


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
    
    '''

    nodedir = 'nodes'

    def __init__(self, dirname, node_size, codec, upload_max=1024, 
                 lru_size=100):
        btree.NodeStore.__init__(self, node_size, codec)
        self.dirname = dirname
        self.metadata_name = os.path.join(dirname, 'metadata')
        self.metadata = None
        self.rs = btree.RefcountStore(self)
        self.cache = lru.LRUCache(lru_size)
        self.upload_max = upload_max
        self.upload_queue = btree.UploadQueue(self._really_put_node, 
                                              self.upload_max)

    def mkdir(self, dirname):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    def read_file(self, filename):
        return file(filename).read()

    def write_file(self, filename, contents):
        dirname = os.path.dirname(filename)
        fd, tempname = tempfile.mkstemp(dir=dirname)
        os.write(fd, contents)
        os.close(fd)
        os.rename(tempname, filename)

    def file_exists(self, filename):
        return os.path.exists(filename)

    def rename_file(self, old, new):
        os.rename(old, new)

    def remove_file(self, filename):
        os.remove(filename)

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
        basename = '%x' % node_id
        subdir = '%d' % (node_id / (2**13))
        return os.path.join(self.dirname, self.nodedir, subdir, basename)
        
    def put_node(self, node):
        self.cache.add(node.id, node)
        self.upload_queue.put(node)

    def push_upload_queue(self):
        self.upload_queue.push()

    def _really_put_node(self, node):
        encoded_node = self.codec.encode(node)
        if len(encoded_node) > self.node_size:
            raise btree.NodeTooBig(node, len(encoded_node))
        name = self.pathname(node.id)
        if self.file_exists(name):
            self.remove_file(name)
        self.mkdir(os.path.dirname(name))
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
        got_it = self.upload_queue.remove(node_id)
        name = self.pathname(node_id)
        if self.file_exists(name):
            self.remove_file(name)
        elif not got_it:
            raise btree.NodeMissing(node_id)
        
    def list_nodes(self):
        queued = self.upload_queue.list_ids()

        nodedir = os.path.join(self.dirname, self.nodedir)
        uploaded = []
        if self.file_exists(nodedir):
            for dirname, subdirs, basenames in os.walk(nodedir):
                uploaded += [int(x, 16) for x in basenames]
        return queued + uploaded

    def get_refcount(self, node_id):
        return self.rs.get_refcount(node_id)

    def set_refcount(self, node_id, refcount):
        self.rs.set_refcount(node_id, refcount)

    def save_refcounts(self):
        self.rs.save_refcounts()
