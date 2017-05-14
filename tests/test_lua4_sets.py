# coding: utf-8

# Copyright 2015, 2017 Jonathan Goble
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

# Copied from the official Lua 5.3.2 test suite and converted to Python

import sys
sys.path.insert(0, r'src')

import luapatt


### SETS

### This class takes several minutes to run, so be patient. test_percent_z and
### test_dot are responsible for two-thirds of that time.

### Update 5/14/2017: changing tests from full range of Unicode to 8 bits,
### because Travis CI testing is taking almost three times as long now.

class TestSets:
    @classmethod
    def setup_class(cls):
        cls.abc = ''.join(map(chr, range(256)))
        assert len(cls.abc) == sys.maxunicode + 1

    def strset(self, p):
        result = set()
        def record(char):
            result.add(char)
        luapatt.gsub(self.abc, p, record)
        return result

    def test_hex_range_set(self):
        assert len(self.strset('[\xc0-\xd0]')) == 17
    def test_range_set(self):
        assert self.strset('[a-z]') == set("abcdefghijklmnopqrstuvwxyz")
    def test_range_and_class_set(self):
        assert self.strset('[a-z%d]') == self.strset('[%da-uu-z]')
    def test_dash_at_end_of_set(self):
        assert self.strset('[a-]') == set("-a")
    def test_negated_set(self):
        assert self.strset('[^%W]') == self.strset('[%w]')
    def test_right_bracket_percent_set(self):
        assert self.strset('[]%%]') == set('%]')
    def test_escaped_dash_in_set(self):
        assert self.strset('[a%-z]') == set('-az')
    def test_escapes_in_set(self):
        assert self.strset('[%^%[%-a%]%-b]') == set('-[]^ab')
    def test_percent_z(self):
        assert self.strset('%Z') == \
            self.strset('[\u0001-{}]'.format(chr(sys.maxunicode)))
    def test_dot(self):
        assert self.strset('.') == \
            self.strset('[\u0001-{}%z]'.format(chr(sys.maxunicode)))

    # Custom tests:
    def test_percent_u(self):
        assert self.strset('%u') == set(c for c in self.abc if c.isupper())

    @classmethod
    def teardown_class(cls):
        del cls.abc
