import struct

import btree


class NodeCodec(object):

    '''Encode and decode nodes from their binary format.
    
    Node identifiers are assumed to fit into 64 bits.
    
    Leaf node values are assumed to fit into 65535 bytes.
    
    '''
    
    def __init__(self, key_bytes):
        self.key_bytes = key_bytes
        
    def leaf_size(self, pairs):
        '''Return size of a leaf node with the given pairs.'''
        fmt = self.leaf_format(pairs)
        return struct.calcsize(fmt)

    def leaf_format(self, pairs):
        return ('!cQI' + ('%ds' % self.key_bytes) * len(pairs) + 
                'I' * len(pairs) +
                ''.join('%ds' % len(value) for key, value in pairs))

    def encode_leaf(self, node):
        '''Encode a leaf node as a byte string.'''

        pairs = node.pairs()
        fmt = self.leaf_format(pairs)
        return struct.pack(fmt, *(['L', node.id, len(pairs)] +
                                    [key for key, value in pairs] +
                                    [len(value) for key, value in pairs] +
                                    [value for key, value in pairs]))

    def decode_leaf(self, encoded):
        '''Decode a leaf node from its encoded byte string.'''

        buf = buffer(encoded)
        el, node_id, num_pairs = struct.unpack_from('!cQI', buf)
        fmt = ('!cQI' + ('%ds' % self.key_bytes) * num_pairs + 
                'I' * num_pairs)
        items = struct.unpack_from(fmt, buf)
        keys = items[3:3+num_pairs]
        lengths = items[3+num_pairs:3+num_pairs*2]
        offsets = [0]
        for i in range(1, len(lengths)):
            offsets.append(offsets[-1] + lengths[i-1])

        values = buffer(encoded, struct.calcsize(fmt))
        pairs = [(keys[i], values[offsets[i]:offsets[i] + lengths[i]]) 
                    for i in range(len(keys))]

        return btree.LeafNode(node_id, pairs)

    def max_index_pairs(self, node_size): # pragma: no cover
        '''Return number of index pairs that fit in a node of a given size.'''
        index_header_size = struct.calcsize('!cQI')
        index_pair_size = struct.calcsize('%dsQ' % self.key_bytes)
        return (node_size - index_header_size) / index_pair_size

    def index_format(self, pairs):
        return ('!cQI' + ('%ds' % self.key_bytes) * len(pairs) + 
                'Q' * len(pairs))
        
    def encode_index(self, node):
        '''Encode an index node as a byte string.'''

        pairs = node.pairs()
        fmt = self.index_format(pairs)
        return struct.pack(fmt, *(['I', node.id, len(pairs)] +
                                  [key for key, child_id in pairs] +
                                  [child_id for key, child_id in pairs]))

    def decode_index(self, encoded):
        '''Decode an index node from its encoded byte string.'''

        buf = buffer(encoded)
        eye, node_id, num_pairs = struct.unpack_from('!cQI', buf)
        fmt = ('!cQI' + ('%ds' % self.key_bytes) * num_pairs + 'Q' * num_pairs)
        items = struct.unpack(fmt, encoded)
        keys = items[3:3+num_pairs]
        child_ids = items[3+num_pairs:]
        assert len(keys) == len(child_ids)
        for x in child_ids:
            assert type(x) == int
        return btree.IndexNode(node_id, zip(keys, child_ids))

    def encode(self, node):
        if isinstance(node, btree.LeafNode):
            return self.encode_leaf(node)
        else:
            return self.encode_index(node)

    def decode(self, encoded):
        if encoded.startswith('L'):
            return self.decode_leaf(encoded)
        else:
            return self.decode_index(encoded)

