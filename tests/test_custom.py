# coding: utf-8

# Copyright 2015 Jonathan Goble
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

import sys
sys.path.insert(0, r'src')

import luapatt

from helpers import checkerror


### SET_ESCAPE_CHAR

class TestSetEscapeChar:
    def setup_method(self, _):
        luapatt.set_escape_char('%')

    def test_valid_escape(self):
        luapatt.set_escape_char('@')
        assert luapatt.ESCAPE == '@'
    def test_invalid_escape(self):
        checkerror(ValueError, 'cannot be any of',
                   luapatt.set_escape_char, '+')
        assert luapatt.ESCAPE == '%'
    def test_long_escape(self):
        checkerror(ValueError, 'must be a single character',
                   luapatt.set_escape_char, '<>')
        assert luapatt.ESCAPE == '%'
    def test_null_escape(self):
        checkerror(ValueError, 'must be a single character',
                   luapatt.set_escape_char, '')
        assert luapatt.ESCAPE == '%'
    def test_bytes_escape(self):
        checkerror(TypeError, 'must be a unicode character',
                   luapatt.set_escape_char, b'@')
        assert luapatt.ESCAPE == '%'
    def test_non_string_escape(self):
        checkerror(TypeError, 'must be a unicode character',
                   luapatt.set_escape_char, 42)
        assert luapatt.ESCAPE == '%'

    def teardown_method(self, _):
        luapatt.set_escape_char('%')


### ADDITIONAL TESTS FOR COMPLETE CODE COVERAGE

def test_find_negative_init():
    assert luapatt.find('test', 't', -1) == (0, 1)

def test_find_captures():
    assert luapatt.find('  test  ', '([^ ]+)') == (2, 6, 'test')

def test_error_gsub_repl_bare_percent():
    checkerror(luapatt.PatternSyntaxError,
               "replacement string ends with bare '%'",
               luapatt.gsub, 'test', 'te', 'fail%')

def test_error_gsub_repl_escaped_escape():
    assert luapatt.gsub('4', '4', '%%') == '%'

def test_too_many_captures():
    checkerror(luapatt.PatternTooManyCaptures, 'too many captures',
               luapatt.find, 'test', '()' * (luapatt.MAXCAPTURES * 2))

def test_minexpand_fail():
    assert luapatt.find('test', 'te-x') is None
