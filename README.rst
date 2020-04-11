luapatt |travis-develop|
========================

A Python 3.5+ implementation of the `Lua language’s`_ pattern matching
functions. Lua’s pattern matching is simpler than regular expressions
and lacks several features that regexes have, such as ``|`` for
alternation, but also contains some features difficult or impossible to
duplicate in most regex flavors, such as the ability to easily match a
balanced pair of parentheses (or any two other characters).

Installation
------------

``pip install luapatt``

Documentation
-------------

For documentation on how pattern matching works, please read the `Lua
reference manual`_. This library contains the following differences from
stock Lua:

-  ``%c``, ``%g``, ``%p``, and their negated counterparts are not
   available; attempting to use them will raise the built-in
   ``NotImplementedError``.
-  Other character classes that rely on the meaning of a character call
   Python’s ``str.is*`` family of methods, and so use the Unicode
   definition of that meaning.
-  String positions are zero-based instead of one-based, reflecting the
   fact that Python is generally zero-based (as opposed to Lua, which
   has one-based indexes). This affects position captures and the
   indexes returned as the first two results from ``find()``.
-  Function return values are combined into a tuple, as is standard with
   Python. However, singleton tuples are not returned; the single value
   is returned directly instead.
-  ``gsub()`` does *not* return the number of substitutions by default,
   instead returning only the new string. To get the count, pass the
   named argument ``count=True`` to the call (which will result in a
   2-tuple of the new string and the count).
-  An extra function, ``set_escape_char()``, is provided to change the
   escape character. It takes one argument: the new escape character,
   which must be a ``str`` object of length 1. The escape character
   cannot be set to any of the other special characters. While it is
   possible to set it to a letter or number, this is not recommended as
   it may interfere with other aspects of pattern matching, and doing so
   may be disallowed in the future.

   -  **NOTE:** Because ``set_escape_char`` modifies global state, it is
      **not** thread-safe.

-  Unlike Lua, which has no notion of a Unicode string and assumes all
   characters are one byte in length, this library operates on full
   Unicode strings (i.e. ``str`` objects). If you pass bytes objects to
   this library, the behavior is undefined.

Licensing
---------

As with Lua itself, this library is released under the MIT License.

.. _Lua language’s: http://www.lua.org/home.html
.. _Lua reference manual: http://www.lua.org/manual/5.3/manual.html#6.4.1
.. |travis-develop| image:: https://travis-ci.org/jcgoble3/luapatt.svg?branch=develop
   :target: https://travis-ci.org/jcgoble3/luapatt
