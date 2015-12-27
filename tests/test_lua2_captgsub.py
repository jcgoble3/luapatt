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

from helpers import checkerror


### CAPTURES AND BACKREFERENCES

def f1(s, p):
    p = luapatt.gsub(p, "%%([0-9])", lambda s: "%" + str(int(s)+1))
    p = luapatt.gsub(p, "^(^?)", "%1()", 1)
    p = luapatt.gsub(p, "($?)$", "()%1", 1)
    t = luapatt.match(s, p)
    print(t)
    return s[t[0]:t[-1]]
def test_backreference():
    assert f1('alo alx 123 b\0o b\0o', '(..*) %1') == "b\0o b\0o"
def test_two_backreferences():
    assert f1('axz123= 4= 4 34', '(.+)=(.*)=%2 %1') == '3= 4= 4 3'
def test_asterisk_backreference():
    assert f1('=======', '^(=*)=%1$') == '======='

def test_backreference_nomatch():
    assert luapatt.match('==========', '^([=]*)=%1$') is None

def test_capture():
    assert luapatt.match("alo xyzK", "(%w+)K") == "xyz"
def test_capture_null():
    assert luapatt.match("254 K", "(%d*)K") == ""
def test_capture_null_end_anchor():
    assert luapatt.match("alo ", "(%w*)$") == ""
def test_capture_no_match():
    assert luapatt.match("alo ", "(%w+)$") is None
def test_escaped_paren():
    assert luapatt.find("(álo)", "%(á") == (0, 2)
def test_nested_captures():
    assert luapatt.match("âlo alo", "^(((.).).* (%w*))$") == \
        ('âlo alo', 'âl', 'â', 'alo')
def test_nested_captures_and_position_capture():
    assert luapatt.match('0123456789', '(.+(.?)())') == \
        ('0123456789', '', 10)


### GSUB

def test_gsub_basic():
    assert luapatt.gsub('ülo ülo', 'ü', 'x') == 'xlo xlo'
# trim
def test_gsub_end_anchor():
    assert luapatt.gsub('alo úlo  ', ' +$', '') == 'alo úlo'
# double trim
def test_gsub_double_anchor():
    assert luapatt.gsub('  alo alo  ', '^%s*(.-)%s*$', '%1') == 'alo alo'
def test_gsub_plus():
    assert luapatt.gsub('alo  alo  \n 123\n ', '%s+', ' ') == 'alo alo 123 '
def test_gsub_count():
    t = "abç d"
    result = luapatt.gsub(t, '(.)', '%1@', count=True)
    assert ('@' + result[0], result[1]) == (luapatt.gsub(t, '', '@'), 5)
def test_gsub_init_and_limit():
    assert luapatt.gsub('abçd', '(.)', '%0@', 2, count=True) == \
        ('a@b@çd', 2)
def test_gsub_position():
    assert luapatt.gsub('alo alo', '()[al]', '%1') == '01o 45o'
def test_gsub_captures():
    assert luapatt.gsub("abc=xyz", "(%w*)(=)(%w+)", "%3%2%1-%0") == \
        "xyz=abc-abc=xyz"
def test_gsub_captures_2():
    assert luapatt.gsub("abc", "%w", "%1%0") == "aabbcc"
def test_gsub_captures_3():
    assert luapatt.gsub("abc", "%w+", "%0%1") == "abcabc"
def test_gsub_append():
    assert luapatt.gsub('áéí', '$', '\0óú') == 'áéí\0óú'
def test_gsub_start_anchor_nullstring():
    assert luapatt.gsub('', '^', 'r') == 'r'
def test_gsub_end_anchor_nullstring():
    assert luapatt.gsub('', '$', 'r') == 'r'

def test_gsub_function():
    assert luapatt.gsub("um (dois) tres (quatro)", "(%(%w+%))", str.upper) \
        == "um (DOIS) tres (QUATRO)"

def test_gsub_function_sideeffect():
    dic = {}
    def setkey(k, v):
        dic[k] = v
    luapatt.gsub("a=roberto,roberto=a", "(%w+)=(%w%w*)", setkey)
    assert dic == {'a': "roberto", 'roberto': "a"}

def test_gsub_custom_function():
    def f(a, b):
        return luapatt.gsub(a, '.', b)
    assert luapatt.gsub(
        "trocar tudo em |teste|b| é |beleza|al|", "|([^|]*)|([^|]*)|", f
    ) == "trocar tudo em bbbbb é alalalalalal"

def test_gsub_func_accumulator():
    t = {}
    s = 'a alo jose  joao'
    def f(a, w, b):
        assert len(w) == b - a
        t[a] = b - a
    r = luapatt.gsub(s, '()(%w+)()', f)
    assert (s, t) == (r, {0: 1, 2: 3, 6: 4, 12: 4})


### BALANCING

def isbalanced(s):
    return luapatt.find(luapatt.gsub(s, "%b()", ""), "[()]") is None

def test_balancing_1():
    assert isbalanced("(9 ((8))(\0) 7) \0\0 a b ()(c)() a")
def test_balancing_2():
    assert not isbalanced("(9 ((8) 7) a b (\0 c) a")
def test_balancing_dupe_args():
    assert luapatt.gsub("alo 'oi' alo", "%b''", '"') == 'alo " alo'


### MORE GSUB

def test_gsub_function_readfromlist():
    t = ["apple", "orange", "lime"]
    assert luapatt.gsub("x and x and x", "x", lambda _: t.pop(0)) == \
        "apple and orange and lime"

def test_gsub_asterisk_function():
    t = []
    luapatt.gsub("first second word", "%w%w*", lambda w: t.append(w))
    assert t == ['first', 'second', 'word']

def test_gsub_limit_function():
    t = []
    assert luapatt.gsub("first second word", "%w+", lambda w: t.append(w),
        2) == "first second word"
    assert t == ['first', 'second']

def test_gsub_error_bad_capture_index():
    checkerror(luapatt.PatternSyntaxError, "invalid capture index %2",
               luapatt.gsub, "alo", ".", "%2")
def test_gsub_error_percent0_in_pattern():
    checkerror(luapatt.PatternSyntaxError, "invalid capture index %0",
               luapatt.gsub, "alo", "(%0)", "a")
def test_gsub_error_backreference_incomplete():
    checkerror(luapatt.PatternSyntaxError, "invalid capture index %1",
               luapatt.gsub, "alo", "(%1)", "a")
def test_gsub_bad_percent_in_replacement():
    checkerror(luapatt.PatternSyntaxError,
               "invalid '%x' in replacement string",
               luapatt.gsub, "alo", ".", "%x")

# recursive nest of gsubs
def test_gsub_recursion():
    def rev(s):
        return luapatt.gsub(s, "(.)(.+)", lambda c, s1: rev(s1) + c)
    x = "abcdef"
    assert rev(rev(x)) == x

# gsub with dicts
def test_gsub_empty_dict():
    assert luapatt.gsub("alo alo", ".", {}) == "alo alo"
def test_gsub_dict():
    assert luapatt.gsub("alo alo", "(.)", {'a': "AA", 'l': ""}) == "AAo AAo"
def test_gsub_dict_partial_capture():
    assert luapatt.gsub("alo alo", "(.).", {'a': "AA", 'l': "K"}) == \
        "AAo AAo"
def test_gsub_dict_multi_captures_False():
    assert luapatt.gsub("alo alo", "((.)(.?))", {'al': "AA", 'o': False}) \
        == "AAo AAo"

def test_gsub_dict_position_captures():
    assert luapatt.gsub("alo alo", "().", {0: 'x', 1: 'yy', 2: 'zzz'}) == \
        "xyyzzz alo"
