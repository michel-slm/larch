# Copyright 2011  Lars Wirzenius
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


import os


class IdPath(object):

    '''Convert a numeric id to a pathname.
    
    The ids are stored in a directory hierarchy, the depth of which
    can be adjusted by a parameter to the class. The ids are assumed
    to be non-negative integers.
    
    '''
    
    def __init__(self, dirname, depth, bits_per_level, skip_bits):
        self.dirname = dirname
        self.depth = depth
        self.bits_per_level = bits_per_level
        self.skip_bits = skip_bits
    
    def convert(self, identifier):
        def level_bits(level):
            level_mask = 2**self.bits_per_level - 1
            n = self.skip_bits + level * self.bits_per_level
            return (identifier >> n) & level_mask
            
        subdirs = ['%d' % level_bits(i) for i in range(self.depth)]
        parts = [self.dirname] + subdirs + ['%x' % identifier]
        return os.path.join(*parts)

