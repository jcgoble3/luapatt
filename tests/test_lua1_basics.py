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


### BASIC FIND TESTS

# empty patterns are tricky
def test_empty_empty():
    assert luapatt.find('', '') == (0, 0)
def test_plain_empty():
    assert luapatt.find('alo', '') == (0, 0)
# first position
def test_first_char():
    assert luapatt.find('a\0o a\0o a\0o', 'a', 0) == (0, 1)
# starts in the middle
def test_substr_expinit_1():
    assert luapatt.find('a\0o a\0o a\0o', 'a\0o', 1) == (4, 7)
# starts in the middle
def test_substr_expinit_2():
    assert luapatt.find('a\0o a\0o a\0o', 'a\0o', 8) == (8, 11)
# finds at the end
def test_substr_atend():
    assert luapatt.find('a\0a\0a\0a\0\0ab', '\0ab', 1) == (8, 11)
# last position
def test_last_char():
    assert luapatt.find('a\0a\0a\0a\0\0ab', 'b') == (10, 11)
# check ending
def test_nomatch_pastend():
    assert luapatt.find('a\0a\0a\0a\0\0ab', 'b\0') is None
def test_nomatch_pastend_nullsrc():
    assert luapatt.find('', '\0') is None
def test_substr():
    assert luapatt.find('alo123alo', '12') == (3, 5)


### QUANTIFIERS AND ANCHORS

def test_nomatch_startanchor():
    assert luapatt.find('alo^123alo', '^12') is None

def test_dot_asterisk_basic():
    assert luapatt.match("aaab", ".*b") == "aaab"
def test_dot_asterisk_backtrack1():
    assert luapatt.match("aaa", ".*a") == "aaa"
def test_dot_asterisk_matchzero():
    assert luapatt.match("b", ".*b") == "b"

def test_dot_plus_basic():
    assert luapatt.match("aaab", ".+b") == "aaab"
def test_dot_plus_backtrack1():
    assert luapatt.match("aaa", ".+a") == "aaa"
def test_dot_plus_failzero():
    assert luapatt.match("b", ".+b") is None

def test_dot_question_basic_1():
    assert luapatt.match("aaab", ".?b") == "ab"
def test_dot_question_basic_2():
    assert luapatt.match("aaa", ".?a") == "aa"
def test_dot_question_matchzero():
    assert luapatt.match("b", ".?b") == "b"

def test_percent_l():
    assert luapatt.match('aloALO', '%l*') == 'alo'
def test_percent_a():
    assert luapatt.match('aLo_ALO', '%a*') == 'aLo'

def test_plain_asterisk():
    assert luapatt.match('aaab', 'a*') == 'aaa'
def test_full_match_asterisk():
    assert luapatt.match('aaa', '^.*$') == 'aaa'
def test_asterisk_null_match():
    assert luapatt.match('aaa', 'b*') == ''
def test_asterisk_null_match_2():
    assert luapatt.match('aaa', 'ab*a') == 'aa'
def test_asterisk_match_one():
    assert luapatt.match('aba', 'ab*a') == 'aba'
def test_plain_plus():
    assert luapatt.match('aaab', 'a+') == 'aaa'
def test_full_match_plus():
    assert luapatt.match('aaa', '^.+$') == 'aaa'
def test_plain_plus_failzero():
    assert luapatt.match('aaa', 'b+') is None
def test_plain_plus_failzero_2():
    assert luapatt.match('aaa', 'ab+a') is None
def test_plus_match_one():
    assert luapatt.match('aba', 'ab+a') == 'aba'
def test_end_anchor():
    assert luapatt.match('a$a', '.$') == 'a'
def test_escaped_end_anchor():
    assert luapatt.match('a$a', '.%$') == 'a$'
def test_dollarsign_inmiddle():
    assert luapatt.match('a$a', '.$.') == 'a$a'
def test_double_dollarsign():
    assert luapatt.match('a$a', '$$') is None
def test_end_anchor_nomatch():
    assert luapatt.match('a$b', 'a$') is None
def test_end_anchor_matchnull():
    assert luapatt.match('a$a', '$') == ''
def test_asterisk_match_nullstring():
    assert luapatt.match('', 'b*') == ''
def test_plain_nomatch():
    assert luapatt.match('aaa', 'bb*') is None
def test_minus_match_zero():
    assert luapatt.match('aaab', 'a-') == ''
def test_full_match_minus():
    assert luapatt.match('aaa', '^.-$') == 'aaa'
def test_asterisk_maxexpand():
    assert luapatt.match('aabaaabaaabaaaba', 'b.*b') == 'baaabaaabaaab'
def test_minus_minexpand():
    assert luapatt.match('aabaaabaaabaaaba', 'b.-b') == 'baaab'
def test_dot_plain_endanchor():
    assert luapatt.match('alo xo', '.o$') == 'xo'
def test_class_x2_asterisk():
    assert luapatt.match(' \n isto é assim', '%S%S*') == 'isto'
def test_class_asterisk_endanchor():
    assert luapatt.match(' \n isto é assim', '%S*$') == 'assim'
def test_set_asterisk_endanchor():
    assert luapatt.match(' \n isto é assim', '[a-z]*$') == 'assim'
def test_negatedset_with_class():
    assert luapatt.match('um caracter ? extra', '[^%sa-z]') == '?'
def test_question_match_zero():
    assert luapatt.match('', 'a?') == ''
def test_question_match_one():
    assert luapatt.match('á', 'á?') == 'á'
def test_multi_question():
    assert luapatt.match('ábl', 'á?b?l?') == 'ábl'
def test_question_match_zero_2():
    assert luapatt.match('  ábl', 'á?b?l?') == ''
def test_question_backtracking():
    assert luapatt.match('aa', '^aa?a?a') == 'aa'


### OTHERS

def test_right_bracket_in_set():
    assert luapatt.match(']]]áb', '[^]]') == 'á'
def test_percent_x():
    assert luapatt.match("0alo alo", "%x*") == "0a"
def test_match_control_characters():
    assert luapatt.match('alo alo', '%C+') == 'alo alo'
def test_match_printable():
    assert luapatt.match('  \n\r*&\n\r   xuxu  \n\n', '%g%g%g+') == 'xuxu'
def test_match_punctuation():
    assert luapatt.match('Hello World!', '%p+') == '!'
