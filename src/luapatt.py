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

from array import array
from collections.abc import Mapping
import unicodedata

__version__ = '0.9.0b5'

_ARRAYTYPECODES = {}
for code in 'bhilq':
    try:
        size = 1 << ((array(code).itemsize << 3) - 1)
    except ValueError:  # 'q' might not be available
        pass
    else:
        if size not in _ARRAYTYPECODES:
            _ARRAYTYPECODES[size] = code
_ARRAYSIZES = list(_ARRAYTYPECODES.keys())
_ARRAYSIZES.sort()
del size, code

MAXCAPTURES = 100
MAXRECURSION = 200
ESCAPE = '%'
SPECIALS = '^$*+?.([-'
UNFINISHEDCAPTURE = -1
POSITIONCAPTURE = -2
PLACEHOLDER = -3


class PatternError(Exception):
    '''Base class for all pattern-related errors in this module.'''


class PatternSyntaxError(PatternError):
    '''All syntax errors; argument is description of problem.'''


class PatternLongSourceError(PatternError):
    def __str__(self):
        return 'source string too long'


class PatternTooComplex(PatternError):
    '''Base class for when the pattern exceeds complexity limits.'''


class PatternStackOverflow(PatternTooComplex):
    def __str__(self):
        return 'pattern too complex, exceeded recursion limit'


class PatternTooManyCaptures(PatternTooComplex):
    def __str__(self):
        return 'too many captures'


class _MatchState:
    def __init__(self, source, pattern, noanchor=False):
        self.matchdepth = MAXRECURSION
        self.source = source
        self.srcstart = 0
        self.capturenum = 0
        sourcelen = len(source)
        for size in _ARRAYSIZES:
            if sourcelen < size:
                typecode = _ARRAYTYPECODES[size]
                break
        else:
            raise PatternLongSourceError
        self.capturestarts = array(
            typecode, (PLACEHOLDER for _ in range(MAXCAPTURES))
        )
        self.captureends = array(
            typecode, (PLACEHOLDER for _ in range(MAXCAPTURES))
        )

    def reset(self, init):
        self.capturenum = 0
        self.srcstart = init
        self.matchdepth = MAXRECURSION

    def getsinglecapture(self, num):
        start = self.capturestarts[num]
        end = self.captureends[num]
        if end == POSITIONCAPTURE:
            return start
        else:
            return self.source[start:end]

    def getcaptures(self, sp):
        if self.capturenum == 0:
            return [self.source[self.srcstart:sp]]
        else:
            return [self.getsinglecapture(n) for n
                    in range(self.capturenum)]


class _PatternMatcher:
    def __init__(self, source, pattern, noanchor=False):
        self.source = source
        self.srclen = len(source)
        self.pattern = pattern
        self.pattlen = len(pattern)
        self.anchor = False if noanchor else (self.pattlen > 0 and
                                              pattern[0] == '^')

    @property
    def nospecials(self):
        return not any(c in self.pattern for c in SPECIALS + ESCAPE)

    def find_aux(self, type, init=0, plain=False):
        if init < 0:
            init = 0
        if init > len(self.source):  # start after source's end?
            return None  # no chance of finding anything
        if type == 'find' and (plain or self.nospecials):
            start = self.source.find(self.pattern, init)  # built-in str.find()
            if start > -1:
                return (start, start + len(self.pattern))
        else:
            init -= 1
            self.state = _MatchState(self.source, self.pattern)
            first = True
            pp = 1 if self.anchor else 0
            while first or ((self.state.srcstart < self.srclen) and
                            not self.anchor):
                first = False
                init += 1
                self.state.reset(init)
                sp = self.match(init, pp)
                if sp is not None:
                    if type == 'find':
                        ret = [init, sp]
                        if self.state.capturenum != 0:
                            ret.extend(self.state.getcaptures(sp))
                        return tuple(ret)
                    elif type == 'match':
                        result = tuple(self.state.getcaptures(sp))
                        if len(result) == 1:
                            return result[0]
                        else:
                            return result
                    elif type == 'gmatch':
                        captures = tuple(self.state.getcaptures(sp))
                        if len(captures) == 1:
                            return (init, sp), captures[0]
                        else:
                            return (init, sp), captures
                    elif type == 'gsub':
                        return (init, sp), tuple(self.state.getcaptures(sp))
        return None

    def _subst_str(self, captures, repl, matchstart, matchend):
        char = 0
        rlen = len(repl)
        accum = []
        while char < rlen:
            c = repl[char]
            if c != ESCAPE:
                accum.append(c)
            else:
                char += 1
                if char == rlen:
                    raise PatternSyntaxError(
                        "replacement string ends with bare '{}'".format(ESCAPE)
                    )
                c = repl[char]
                if c == ESCAPE:
                    accum.append(ESCAPE)
                elif c in '123456789':
                    if c == '1':
                        c = 0
                    else:
                        c = self.checkcapture(int(c))
                    accum.append(str(captures[c]))
                elif c == '0':
                    accum.append(
                        str(self.source[matchstart:matchend])
                    )
                else:
                    raise PatternSyntaxError(
                        "invalid '{}{}' in replacement "
                        "string".format(ESCAPE, c)
                    )
            char += 1
        return ''.join(accum)

    def subst(self, captures, repl, matchstart, matchend):
        if callable(repl):
            value = repl(*captures)
        elif isinstance(repl, Mapping):
            value = repl.get(captures[0])
        else:
            value = self._subst_str(captures, str(repl), matchstart, matchend)
        if value is None or value is False:
            value = self.source[matchstart:matchend]
        return str(value)

    def match(self, sp, pp):
        if self.state.matchdepth == 0:
            raise PatternStackOverflow
        self.state.matchdepth -= 1
        while pp < self.pattlen:
            pc = self.pattern[pp]
            try:
                pc1 = self.pattern[pp + 1]
            except IndexError:
                pc1 = None
            if pc == '(':
                if pc1 == ')':
                    sp = self.startcapture(sp, pp + 2, POSITIONCAPTURE)
                else:
                    sp = self.startcapture(sp, pp + 1, UNFINISHEDCAPTURE)
                break
            elif pc == ')':
                sp = self.endcapture(sp, pp + 1)
                break
            elif pc == '$' and pp + 1 == self.pattlen:
                if sp != self.srclen:
                    sp = None
                break
            elif pc == ESCAPE:
                if pc1 is None:
                    raise PatternSyntaxError(
                        "pattern ends with bare '{}'".format(ESCAPE)
                    )
                elif pc1 == 'b':
                    sp = self.matchbalance(sp, pp + 2)
                    if sp is None:
                        break
                    pp += 4
                    continue
                elif pc1 == 'f':
                    pp += 2
                    if pp >= self.pattlen or self.pattern[pp] != '[':
                        raise PatternSyntaxError(
                            "missing '[' after '{}f'".format(ESCAPE)
                        )
                    ep = self.classend(pp)
                    set = self.pattern[pp + 1:ep - 1]
                    prev = '\0' if sp == 0 else self.source[sp - 1]
                    next = '\0' if sp >= self.srclen else self.source[sp]
                    if (not self.matchbracketclass(prev, set) and
                            self.matchbracketclass(next, set)):
                        pp = ep
                        continue
                    sp = None
                    break
                elif pc1 in '0123456789':
                    sp = self.matchcapture(sp, int(pc1))
                    if sp is None:
                        break
                    pp += 2
                    continue
            # This point can only be reached if all conditions above test
            # false. Any true condition above is guaranteed to result in
            # either a break, a continue, or raising an error.
            ep = self.classend(pp)  # ep points to the optional quantifier
            try:
                qc = self.pattern[ep]
            except IndexError:
                qc = None
            if not self.singlematch(sp, pp, ep):
                if qc and qc in '*?-':  # allow zero matches?
                    pp = ep + 1
                    continue
                sp = None
                break
            else:  # matched once
                if qc == '?':
                    result = self.match(sp + 1, ep + 1)
                    if result is None:
                        pp = ep + 1
                        continue
                    else:
                        sp = result
                        break
                elif qc == '+':
                    sp = self.maxexpand(sp + 1, pp, ep)
                    break
                elif qc == '*':
                    sp = self.maxexpand(sp, pp, ep)
                    break
                elif qc == '-':
                    sp = self.minexpand(sp, pp, ep)
                    break
                else:  # no quantifier
                    sp += 1
                    pp = ep
                    continue
        self.state.matchdepth += 1
        return sp

    def matchcapture(self, sp, num):
        index = self.checkcapture(num)
        cs = self.state.capturestarts[index]
        ce = self.state.captureends[index]
        cl = ce - cs
        if (cl <= self.srclen - sp and
                self.source[sp:sp + cl] == self.state.getsinglecapture(index)):
            return sp + cl
        else:
            return None

    def startcapture(self, sp, pp, what):
        cnum = self.state.capturenum
        if cnum >= MAXCAPTURES:
            raise PatternTooManyCaptures
        self.state.capturestarts[cnum] = sp
        self.state.captureends[cnum] = what
        self.state.capturenum += 1
        result = self.match(sp, pp)
        if result is None:
            self.state.capturenum -= 1
        elif self.state.captureends[cnum] == UNFINISHEDCAPTURE:
            raise PatternSyntaxError('unfinished capture')
        return result

    def endcapture(self, sp, pp):
        index = self.capturetoclose()
        self.state.captureends[index] = sp
        result = self.match(sp, pp)
        if result is None:
            self.state.captureends[index] = UNFINISHEDCAPTURE
        return result

    def minexpand(self, sp, pp, ep):
        while True:
            result = self.match(sp, ep + 1)
            if result is not None:
                return result
            elif self.singlematch(sp, pp, ep):
                sp += 1
            else:
                return None

    def maxexpand(self, sp, pp, ep):
        count = 0
        while self.singlematch(sp + count, pp, ep):
            count += 1
        while count >= 0:
            result = self.match(sp + count, ep + 1)
            if result is not None:
                return result
            count -= 1
        return None

    def matchbalance(self, sp, pp):
        if pp > self.pattlen - 2:
            raise PatternSyntaxError(
                "missing arguments to '{}b')".format(ESCAPE)
            )
        b = self.pattern[pp]
        if sp == self.srclen or self.source[sp] != b:
            return None
        e = self.pattern[pp + 1]
        level = 1
        sp += 1
        while sp < self.srclen:
            sc = self.source[sp]
            if sc == e:
                level -= 1
                if level == 0:
                    return sp + 1
            elif sc == b:
                level += 1
            sp += 1
        return None

    def singlematch(self, sp, pp, ep):
        if sp >= self.srclen:
            return False
        sc = self.source[sp]
        pc = self.pattern[pp]
        if pc == '.':
            return True
        elif pc == ESCAPE:
            return self.matchclass(sc, self.pattern[pp + 1])
        elif pc == '[':
            return self.matchbracketclass(sc, self.pattern[pp + 1:ep - 1])
        else:
            return sc == pc

    def matchbracketclass(self, sc, set):
        if set[0] == '^':
            signal = False
            pos = 1
        else:
            signal = True
            pos = 0
        sl = len(set)
        while pos < sl:
            pc = set[pos]
            try:
                pc1 = set[pos + 1]
            except IndexError:
                pc1 = None
            if pc == ESCAPE:
                pos += 1
                if self.matchclass(sc, pc1):
                    return signal
            elif pc1 == '-' and pos + 2 < sl:
                pos += 2
                if pc <= sc <= set[pos]:
                    return signal
            elif pc == sc:
                return signal
            pos += 1
        return not signal

    def matchclass(self, sc, pc):
        pcl = pc.lower()
        if pcl == 'a':
            match = sc.isalpha()
        elif pcl == 'd':
            match = sc.isdigit()
        elif pcl == 'l':
            match = sc.islower()
        elif pcl == 's':
            match = sc.isspace()
        elif pcl == 'u':
            match = sc.isupper()
        elif pcl == 'w':
            match = sc.isalpha() or sc.isdigit()
        elif pcl == 'x':
            match = sc.isdigit() or sc in 'abcdefABCDEF'
        elif pcl == 'z':
            match = sc == '\0'
        elif pcl == 'c':
            match = unicodedata.category(sc)[0] == 'C'
        elif pcl == 'g':
            match = unicodedata.category(sc)[0] not in 'CZ'
        elif pcl == 'p':
            match = unicodedata.category(sc)[0] == 'P'
        else:
            return sc == pc
        return match if pc.islower() else not match

    def checkcapture(self, n):
        n -= 1
        if (n < 0 or n >= self.state.capturenum or
                self.state.captureends[n] == UNFINISHEDCAPTURE):
            raise PatternSyntaxError(
                'invalid capture index {}{}'.format(ESCAPE, n + 1)
            )
        return n

    def capturetoclose(self):
        for index in range(self.state.capturenum - 1, -1, -1):
            if self.state.captureends[index] == UNFINISHEDCAPTURE:
                return index
        raise PatternSyntaxError("unmatched ')'")

    def classend(self, pp):
        pc = self.pattern[pp]
        pp += 1
        if pc == ESCAPE:
            # The error case of a pattern ending with a bare ESCAPE is handled
            # in self.match() before this is ever called.
            return pp + 1
        elif pc == '[':
            try:
                if self.pattern[pp] == '^':
                    pp += 1
                if self.pattern[pp] == ']':
                    pp += 1
                while self.pattern[pp] != ']':
                    if (self.pattern[pp] == ESCAPE and
                            pp + 1 < self.pattlen):
                        pp += 2
                    else:
                        pp += 1
                return pp + 1
            except IndexError:
                raise PatternSyntaxError("missing ']'") from None
        else:
            return pp


####################
# Public functions #
####################


def set_escape_char(char):
    global ESCAPE
    if not isinstance(char, str):
        raise TypeError('"char" must be a unicode character')
    if len(char) != 1:
        raise ValueError('"char" must be a single character')
    invalidescapes = SPECIALS + ')]'
    if char in invalidescapes:
        raise ValueError('"char" cannot be any of "{}"'.format(invalidescapes))
    ESCAPE = char


def find(source, pattern, init=0, plain=False):
    matcher = _PatternMatcher(source, pattern)
    return matcher.find_aux(type='find', init=init, plain=plain)


def match(source, pattern, init=0):
    matcher = _PatternMatcher(source, pattern)
    return matcher.find_aux(type='match', init=init, plain=False)


def gmatch(source, pattern):
    matcher = _PatternMatcher(source, pattern, noanchor=True)
    init = 0
    result = True
    while result:
        result = matcher.find_aux(type='gmatch', init=init, plain=False)
        if result:
            newstart = result[0][1]
            if newstart == result[0][0]:  # empty match at starting position?
                newstart += 1  # go forward at least one character
            init = newstart
            yield result[1]


def gsub(source, pattern, repl, limit=None, count=False):
    matcher = _PatternMatcher(source, pattern)
    accum = []
    init = 0
    replcount = 0
    if matcher.anchor:
        limit = 1  # not possible to match more than one if anchored at start
    elif limit is None:
        # Maximum possible substitutions is one more than len(source)
        # e.g. luapatt.gsub('test', '.-', '=') returns '=t=e=s=t='
        limit = len(source) + 1
    while replcount < limit:
        result = matcher.find_aux(type='gsub', init=init, plain=False)
        if not result:
            break
        replcount += 1
        matchstart, matchend = result[0]
        accum.append(source[init:matchstart])
        accum.append(matcher.subst(result[1], repl, matchstart, matchend))
        init = matchend
        if matchstart == matchend:  # empty match?
            if matchend < matcher.srclen:
                accum.append(source[matchend])  # skip a character
            init += 1
    accum.append(source[init:])  # collect the rest of the source string
    finalstring = ''.join(accum)
    if count:
        return finalstring, replcount
    else:
        return finalstring
