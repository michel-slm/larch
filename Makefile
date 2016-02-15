# Makefile for B-tree implementation
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


all: fsck-larch.1
	$(MAKE) -C doc html

fsck-larch.1: fsck-larch.1.in fsck-larch
	./fsck-larch --generate-manpage=fsck-larch.1.in > fsck-larch.1

check:
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm -f .coverage
	./insert-remove-test tempdir 100
	rm -r tempdir larch.log
	cmdtest tests
	./codec-speed -n1000
	./idpath-speed 1 t.idspeed-test 10 5 1 && rm -r t.idspeed-test
	./refcount-speed --refs=1000
	./speed-test --location t.speed-test --keys 1000
	
clean:
	rm -f .coverage *.py[co] larch/*.py[co] insert.prof lookup.prof
	rm -rf build tempdir larch.log example.tree t.idspeed-test t.speed-test
	rm -f fsck-larch.1
	$(MAKE) -C doc clean
