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

# Copied from the official Lua 5.3.2 test suite and converted to Python

import sys
sys.path.insert(0, r'src')

import luapatt

from helpers import checkerror, syntaxerror


### GMATCH

def test_gmatch_empty_matches():
    a = -1
    for i in luapatt.gmatch('abcde', '()'):
        assert i == a + 1
        a = i
    assert a == 5

def test_gmatch_basic():
    t = []
    for w in luapatt.gmatch("first second word", "%w+"):
        t.append(w)
    assert t == ["first", "second", "word"]

def test_gmatch_backreferences():
    t = [2, 5, 8]
    for i in luapatt.gmatch("xuxx uu ppar r", "()(.)%2"):
        assert i[0] == t.pop(0)
    assert len(t) == 0

def test_gmatch_multi_captures():
    t = {}
    for i, j in luapatt.gmatch("13 14 10 = 11, 15= 16, 22=23",
                                  "(%d+)%s*=%s*(%d+)"):
        t[int(i)] = int(j)
    for k, v in t.items():
        assert k + 1 == v + 0
    assert len(t) == 3


### FRONTIER PATTERNS

def test_frontier_class():
    assert luapatt.gsub("aaa aa a aaa a", "%f[%w]a", "x") == "xaa xa x xaa x"
def test_frontier_left_bracket():
    assert luapatt.gsub("[[]] [][] [[[[", "%f[[].", "x") == "x[]] x]x] x[[["
def test_frontier_class_nullmatch():
    assert luapatt.gsub("01abc45de3", "%f[%d]", ".") == ".01abc.45de.3"
def test_frontier_class_match():
    assert luapatt.gsub("01abc45 de3x", "%f[%D]%w", ".") == "01.bc45 de3."
def test_frontier_negated_nullchar():
    assert luapatt.gsub("function", "%f[^\0]%w", ".") == ".unction"
def test_frontier_nullchar():
    assert luapatt.gsub("function", "%f[\0]", ".") == "function."

def test_frontier_nullmatch_atstart():
    assert luapatt.find("a", "%f[a]") == (0, 0)
def test_frontier_nullmatch_negated_percent_z():
    assert luapatt.find("a", "%f[^%z]") == (0, 0)
def test_frontier_nullmatch_atend():
    assert luapatt.find("a", "%f[^%l]") == (1, 1)
def test_frontier_nullmatch_inmiddle():
    assert luapatt.find("aba", "%f[a%z]") == (2, 2)
def test_frontier_nullmatch_percent_z():
    assert luapatt.find("aba", "%f[%z]") == (3, 3)
def test_frontier_nomatch():
    assert luapatt.find("aba", "%f[%l%z]") is None
def test_frontier_nomatch_2():
    assert luapatt.find("aba", "%f[^%l%z]") is None

def test_multi_frontier():
    assert luapatt.find(" alo aalo allo", "%f[%S].-%f[%s].-%f[%S]") == \
        (1, 5)
def test_multi_frontier_2():
    assert luapatt.match(" alo aalo allo", "%f[%S](.-%f[%s].-%f[%S])") == \
        'alo '

def test_frontier_gmatch():
    a = [0, 4, 8, 13, 16]
    r = []
    for k in luapatt.gmatch("alo alo th02 is 1hat", "()%f[%w%d]"):
        r.append(k)
    assert a == r


### MALFORMED PATTERN ERRORS

def test_error_unfinished_capture():
    syntaxerror("(.", "unfinished capture")
def test_error_invalid_right_paren():
    syntaxerror(".)", "unmatched ')'")
def test_error_unfinished_set():
    syntaxerror("[a", "missing ']'")
def test_error_empty_set():
    syntaxerror("[]", "missing ']'")
def test_error_empty_negated_set():
    syntaxerror("[^]", "missing ']'")
def test_error_set_bare_percent():
    syntaxerror("[a%]", "missing ']'")
def test_error_end_with_bare_percent():
    syntaxerror("[a%", "missing ']'")
def test_error_balance_no_args():
    syntaxerror("%b", "missing arguments to '%b')")
def test_error_balance_one_arg():
    syntaxerror("%ba", "missing arguments to '%b')")
def test_error_lone_percent():
    syntaxerror('%', "pattern ends with bare '%'")
def test_error_frontier_no_arg():
    syntaxerror("%f", "missing '[' after '%f'")


### STACK OVERFLOW

def f2(size):
    s = "a" * size
    p = ".?" * size
    return luapatt.match(s, p)

def test_stack_no_overflow():
    assert len(f2(80)) == 80

def test_stack_overflow():
    checkerror(luapatt.PatternStackOverflow,
               'pattern too complex, exceeded recursion limit',
               f2, 200000)


### BIG STRINGS (these take a few seconds)

class TestBigStrings:
    @classmethod
    def setup_class(cls):
        cls.a = 'a' * 300000
    def test_big_string_backtrack_one(self):
        assert luapatt.find(self.a, '^a*.?$')
    def test_big_string_no_match(self):
        assert not luapatt.find(self.a, '^a*.?b$')
    def test_big_string_minus(self):
        assert luapatt.find(self.a, '^a-.?$')
    @classmethod
    def teardown_class(cls):
        del cls.a


