/*
** $Id: lstrlib.c,v 1.253 2016/12/20 18:37:00 roberto Exp roberto $
** Standard library for string operations and pattern-matching
** See Copyright Notice in lua.h
*/

/*
** Lua-isms remaining:
** 8-bit strings
** ASCII meanings in match_class()
** raise_error() (renamed from luaL_error)
** return NULL for no match (possibly indicates error in Python?)
** use of char* in MatchState (store string as PyObject* instead?)
** lmemfind()?
** push_onecapture()
** push_captures()
** nospecials()?
** all public functions
*/

#include "Python.h"

#include <ctype.h>
#include <string.h>

/*
** maximum number of captures that a pattern can do during
** pattern-matching. This limit is arbitrary, but must fit in
** an unsigned char.
*/
#if !defined(MAXCAPTURES)
#define MAXCAPTURES 32
#endif

/* macro to 'unsign' a character */
#define uchar(c) ((unsigned char)(c))

/* translate a relative string position: negative means back from end */
static int
posrelat(int pos, size_t len)
{
  if (pos >= 0)
    return pos;
  else if (0u - (size_t)pos > len)
    return 0;
  else
    return (int)len + pos + 1;
}

/*
** {======================================================
** PATTERN MATCHING
** =======================================================
*/

#define CAP_UNFINISHED (-1)
#define CAP_POSITION (-2)

typedef struct MatchState
{
  const char* src_init; /* init of source string */
  const char* src_end;  /* end ('\0') of source string */
  const char* p_end;    /* end ('\0') of pattern */
  int matchdepth; /* control for recursive depth (to avoid C stack overflow) */
  unsigned char level; /* total number of captures (finished or unfinished) */
  struct
  {
    const char* init;
    ptrdiff_t len;
  } capture[MAXCAPTURES];
} MatchState;

/* recursive function */
static const char* match(MatchState* ms, const char* s, const char* p);

/* maximum recursion depth for 'match' */
#if !defined(MAXCCALLS)
#define MAXCCALLS 200
#endif

#define ESC '%'
#define SPECIALS "^$*+?.([%-"

static int
check_capture(MatchState* ms, int l)
{
  l -= '1';
  if (l < 0 || l >= ms->level || ms->capture[l].len == CAP_UNFINISHED)
    return raise_error("invalid capture index %%%d", l + 1);
  return l;
}

static int
capture_to_close(MatchState* ms)
{
  int level = ms->level;
  for (level--; level >= 0; level--)
    if (ms->capture[level].len == CAP_UNFINISHED)
      return level;
  return raise_error("invalid pattern capture");
}

static const char*
classend(MatchState* ms, const char* p)
{
  switch (*p++) {
    case ESC: {
      if (p == ms->p_end)
        raise_error("malformed pattern (ends with '%%')");
      return p + 1;
    }
    case '[': {
      if (*p == '^')
        p++;
      do { /* look for a ']' */
        if (p == ms->p_end)
          raise_error("malformed pattern (missing ']')");
        if (*(p++) == ESC && p < ms->p_end)
          p++; /* skip escapes (e.g. '%]') */
      } while (*p != ']');
      return p + 1;
    }
    default: {
      return p;
    }
  }
}

static int
match_class(int c, int cl)
{
  int res;
  switch (tolower(cl)) {
    case 'a':
      res = isalpha(c);
      break;
    case 'c':
      res = iscntrl(c);
      break;
    case 'd':
      res = isdigit(c);
      break;
    case 'g':
      res = isgraph(c);
      break;
    case 'l':
      res = islower(c);
      break;
    case 'p':
      res = ispunct(c);
      break;
    case 's':
      res = isspace(c);
      break;
    case 'u':
      res = isupper(c);
      break;
    case 'w':
      res = isalnum(c);
      break;
    case 'x':
      res = isxdigit(c);
      break;
    case 'z':
      res = (c == 0);
      break; /* deprecated option */
    default:
      return (cl == c);
  }
  return (islower(cl) ? res : !res);
}

static int
matchbracketclass(int c, const char* p, const char* ec)
{
  int sig = 1;
  if (*(p + 1) == '^') {
    sig = 0;
    p++; /* skip the '^' */
  }
  while (++p < ec) {
    if (*p == ESC) {
      p++;
      if (match_class(c, uchar(*p)))
        return sig;
    } else if ((*(p + 1) == '-') && (p + 2 < ec)) {
      p += 2;
      if (uchar(*(p - 2)) <= c && c <= uchar(*p))
        return sig;
    } else if (uchar(*p) == c)
      return sig;
  }
  return !sig;
}

static int
singlematch(MatchState* ms, const char* s, const char* p, const char* ep)
{
  if (s >= ms->src_end)
    return 0;
  else {
    int c = uchar(*s);
    switch (*p) {
      case '.':
        return 1; /* matches any char */
      case ESC:
        return match_class(c, uchar(*(p + 1)));
      case '[':
        return matchbracketclass(c, p, ep - 1);
      default:
        return (uchar(*p) == c);
    }
  }
}

static const char*
matchbalance(MatchState* ms, const char* s, const char* p)
{
  if (p >= ms->p_end - 1)
    raise_error("malformed pattern (missing arguments to '%%b')");
  if (*s != *p)
    return NULL;
  else {
    int b = *p;
    int e = *(p + 1);
    int cont = 1;
    while (++s < ms->src_end) {
      if (*s == e) {
        if (--cont == 0)
          return s + 1;
      } else if (*s == b)
        cont++;
    }
  }
  return NULL; /* string ends out of balance */
}

static const char*
max_expand(MatchState* ms, const char* s, const char* p, const char* ep)
{
  ptrdiff_t i = 0; /* counts maximum expand for item */
  while (singlematch(ms, s + i, p, ep))
    i++;
  /* keeps trying to match with the maximum repetitions */
  while (i >= 0) {
    const char* res = match(ms, (s + i), ep + 1);
    if (res)
      return res;
    i--; /* else didn't match; reduce 1 repetition to try again */
  }
  return NULL;
}

static const char*
min_expand(MatchState* ms, const char* s, const char* p, const char* ep)
{
  for (;;) {
    const char* res = match(ms, s, ep + 1);
    if (res != NULL)
      return res;
    else if (singlematch(ms, s, p, ep))
      s++; /* try with one more repetition */
    else
      return NULL;
  }
}

static const char*
start_capture(MatchState* ms, const char* s, const char* p, int what)
{
  const char* res;
  int level = ms->level;
  if (level >= MAXCAPTURES)
    raise_error("too many captures");
  ms->capture[level].init = s;
  ms->capture[level].len = what;
  ms->level = level + 1;
  if ((res = match(ms, s, p)) == NULL) /* match failed? */
    ms->level--;                       /* undo capture */
  return res;
}

static const char*
end_capture(MatchState* ms, const char* s, const char* p)
{
  int l = capture_to_close(ms);
  const char* res;
  ms->capture[l].len = s - ms->capture[l].init; /* close capture */
  if ((res = match(ms, s, p)) == NULL)          /* match failed? */
    ms->capture[l].len = CAP_UNFINISHED;        /* undo capture */
  return res;
}

static const char*
match_capture(MatchState* ms, const char* s, int l)
{
  size_t len;
  l = check_capture(ms, l);
  len = ms->capture[l].len;
  if ((size_t)(ms->src_end - s) >= len &&
      memcmp(ms->capture[l].init, s, len) == 0)
    return s + len;
  else
    return NULL;
}

static const char*
match(MatchState* ms, const char* s, const char* p)
{
  if (ms->matchdepth-- == 0)
    raise_error("pattern too complex");
init:                   /* using goto's to optimize tail recursion */
  if (p != ms->p_end) { /* end of pattern? */
    switch (*p) {
      case '(': {            /* start capture */
        if (*(p + 1) == ')') /* position capture? */
          s = start_capture(ms, s, p + 2, CAP_POSITION);
        else
          s = start_capture(ms, s, p + 1, CAP_UNFINISHED);
        break;
      }
      case ')': { /* end capture */
        s = end_capture(ms, s, p + 1);
        break;
      }
      case '$': {
        if ((p + 1) != ms->p_end) /* is the '$' the last char in pattern? */
          goto dflt;              /* no; go to default */
        s = (s == ms->src_end) ? s : NULL; /* check end of string */
        break;
      }
      case ESC: { /* escaped sequences not in the format class[*+?-]? */
        switch (*(p + 1)) {
          case 'b': { /* balanced string? */
            s = matchbalance(ms, s, p + 2);
            if (s != NULL) {
              p += 4;
              goto init; /* return match(ms, s, p + 4); */
            }            /* else fail (s == NULL) */
            break;
          }
          case 'f': { /* frontier? */
            const char* ep;
            char previous;
            p += 2;
            if (*p != '[')
              raise_error("missing '[' after '%%f' in pattern");
            ep = classend(ms, p); /* points to what is next */
            previous = (s == ms->src_init) ? '\0' : *(s - 1);
            if (!matchbracketclass(uchar(previous), p, ep - 1) &&
                matchbracketclass(uchar(*s), p, ep - 1)) {
              p = ep;
              goto init; /* return match(ms, s, ep); */
            }
            s = NULL; /* match failed */
            break;
          }
          case '0':
          case '1':
          case '2':
          case '3':
          case '4':
          case '5':
          case '6':
          case '7':
          case '8':
          case '9': { /* capture results (%0-%9)? */
            s = match_capture(ms, s, uchar(*(p + 1)));
            if (s != NULL) {
              p += 2;
              goto init; /* return match(ms, s, p + 2) */
            }
            break;
          }
          default:
            goto dflt;
        }
        break;
      }
      default:
      dflt : { /* pattern class plus optional suffix */
        const char* ep = classend(ms, p); /* points to optional suffix */
        /* does not match at least once? */
        if (!singlematch(ms, s, p, ep)) {
          if (*ep == '*' || *ep == '?' || *ep == '-') { /* accept empty? */
            p = ep + 1;
            goto init;   /* return match(ms, s, ep + 1); */
          } else {        /* '+' or no suffix */
                s = NULL;
          }    /* fail */
        } else {         /* matched once */
          switch (*ep) { /* handle optional suffix */
            case '?': {  /* optional */
              const char* res;
              if ((res = match(ms, s + 1, ep + 1)) != NULL)
                s = res;
              else {
                p = ep + 1;
                goto init; /* else return match(ms, s, ep + 1); */
              }
              break;
            }
            case '+': /* 1 or more repetitions */
              s++;    /* 1 match already done */
            /* FALLTHROUGH */
            case '*': /* 0 or more repetitions */
              s = max_expand(ms, s, p, ep);
              break;
            case '-': /* 0 or more repetitions (minimum) */
              s = min_expand(ms, s, p, ep);
              break;
            default: /* no suffix */
              s++;
              p = ep;
              goto init; /* return match(ms, s + 1, ep); */
          }
        }
        break;
      }
    }
  }
  ms->matchdepth++;
  return s;
}

static const char*
lmemfind(const char* s1, size_t l1, const char* s2, size_t l2)
{
  if (l2 == 0)
    return s1; /* empty strings are everywhere */
  else if (l2 > l1)
    return NULL; /* avoids a negative 'l1' */
  else {
    const char* init; /* to search for a '*s2' inside 's1' */
    l2--;             /* 1st char will be checked by 'memchr' */
    l1 = l1 - l2;     /* 's2' cannot be found after that */
    while (l1 > 0 && (init = (const char*)memchr(s1, *s2, l1)) != NULL) {
      init++; /* 1st char is already checked */
      if (memcmp(init, s2 + 1, l2) == 0)
        return init - 1;
      else { /* correct 'l1' and 's1' to try again */
        l1 -= init - s1;
        s1 = init;
      }
    }
    return NULL; /* not found */
  }
}

static void
push_onecapture(MatchState* ms, int i, const char* s, const char* e)
{
  if (i >= ms->level) {
    if (i == 0)                         /* ms->level == 0, too */
      lua_pushlstring(ms->L, s, e - s); /* add whole match */
    else
      raise_error("invalid capture index %%%d", i + 1);
  } else {
    ptrdiff_t l = ms->capture[i].len;
    if (l == CAP_UNFINISHED)
      raise_error("unfinished capture");
    if (l == CAP_POSITION)
      lua_pushinteger(ms->L, (ms->capture[i].init - ms->src_init) + 1);
    else
      lua_pushlstring(ms->L, ms->capture[i].init, l);
  }
}

static int
push_captures(MatchState* ms, const char* s, const char* e)
{
  int i;
  int nlevels = (ms->level == 0 && s) ? 1 : ms->level;
  luaL_checkstack(ms->L, nlevels, "too many captures");
  for (i = 0; i < nlevels; i++)
    push_onecapture(ms, i, s, e);
  return nlevels; /* number of strings pushed */
}

/* check whether pattern has no special characters */
static int
nospecials(const char* p, size_t l)
{
  size_t upto = 0;
  do {
    if (strpbrk(p + upto, SPECIALS))
      return 0;                   /* pattern has a special character */
    upto += strlen(p + upto) + 1; /* may have more after \0 */
  } while (upto <= l);
  return 1; /* no special chars found */
}

static void
prepstate(MatchState* ms, const char* s, size_t ls,
          const char* p, size_t lp)
{
  ms->matchdepth = MAXCCALLS;
  ms->src_init = s;
  ms->src_end = s + ls;
  ms->p_end = p + lp;
}

static void
reprepstate(MatchState* ms)
{
  ms->level = 0;
  assert(ms->matchdepth == MAXCCALLS);
}

static int
str_find_aux(int find)
{
  size_t ls, lp;
  const char* s = luaL_checklstring(L, 1, &ls);
  const char* p = luaL_checklstring(L, 2, &lp);
  int init = posrelat(luaL_optinteger(L, 3, 1), ls);
  if (init < 1)
    init = 1;
  else if (init > (int)ls + 1) { /* start after string's end? */
    lua_pushnil(L);                      /* cannot find anything */
    return 1;
  }
  /* explicit request or no special characters? */
  if (find && (lua_toboolean(L, 4) || nospecials(p, lp))) {
    /* do a plain search */
    const char* s2 = lmemfind(s + init - 1, ls - (size_t)init + 1, p, lp);
    if (s2) {
      lua_pushinteger(L, (s2 - s) + 1);
      lua_pushinteger(L, (s2 - s) + lp);
      return 2;
    }
  } else {
    MatchState ms;
    const char* s1 = s + init - 1;
    int anchor = (*p == '^');
    if (anchor) {
      p++;
      lp--; /* skip anchor character */
    }
    prepstate(&ms, s, ls, p, lp);
    do {
      const char* res;
      reprepstate(&ms);
      if ((res = match(&ms, s1, p)) != NULL) {
        if (find) {
          lua_pushinteger(L, (s1 - s) + 1); /* start */
          lua_pushinteger(L, res - s);      /* end */
          return push_captures(&ms, NULL, 0) + 2;
        } else
          return push_captures(&ms, s1, res);
      }
    } while (s1++ < ms.src_end && !anchor);
  }
  lua_pushnil(L); /* not found */
  return 1;
}

static int
str_find()
{
  return str_find_aux(1);
}

static int
str_match()
{
  return str_find_aux(0);
}

/* state for 'gmatch' */
typedef struct GMatchState
{
  const char* src;       /* current position */
  const char* p;         /* pattern */
  const char* lastmatch; /* end of last match */
  MatchState ms;         /* match state */
} GMatchState;

static int
gmatch_aux()
{
  GMatchState* gm = (GMatchState*)lua_touserdata(L, lua_upvalueindex(3));
  const char* src;
  for (src = gm->src; src <= gm->ms.src_end; src++) {
    const char* e;
    reprepstate(&gm->ms);
    if ((e = match(&gm->ms, src, gm->p)) != NULL && e != gm->lastmatch) {
      gm->src = gm->lastmatch = e;
      return push_captures(&gm->ms, src, e);
    }
  }
  return 0; /* not found */
}

static int
gmatch()
{
  size_t ls, lp;
  const char* s = luaL_checklstring(L, 1, &ls);
  const char* p = luaL_checklstring(L, 2, &lp);
  GMatchState* gm;
  lua_settop(L, 2); /* keep them on closure to avoid being collected */
  gm = (GMatchState*)lua_newuserdata(L, sizeof(GMatchState));
  prepstate(&gm->ms, s, ls, p, lp);
  gm->src = s;
  gm->p = p;
  gm->lastmatch = NULL;
  lua_pushcclosure(L, gmatch_aux, 3);
  return 1;
}

static void
add_s(MatchState* ms, luaL_Buffer* b, const char* s, const char* e)
{
  size_t l, i;
  const char* news = lua_tolstring(L, 3, &l);
  for (i = 0; i < l; i++) {
    if (news[i] != ESC)
      luaL_addchar(b, news[i]);
    else {
      i++; /* skip ESC */
      if (!isdigit(uchar(news[i]))) {
        if (news[i] != ESC)
          raise_error("invalid use of '%c' in replacement string", ESC);
        luaL_addchar(b, news[i]);
      } else if (news[i] == '0')
        luaL_addlstring(b, s, e - s);
      else {
        push_onecapture(ms, news[i] - '1', s, e);
        luaL_tolstring(L, -1, NULL); /* if number, convert it to string */
        lua_remove(L, -2);           /* remove original value */
        luaL_addvalue(b);            /* add capture to accumulated result */
      }
    }
  }
}

static void
add_value(MatchState* ms, luaL_Buffer* b, const char* s, const char* e, int tr)
{
  switch (tr) {
    case LUA_TFUNCTION: {
      int n;
      lua_pushvalue(L, 3);
      n = push_captures(ms, s, e);
      lua_call(L, n, 1);
      break;
    }
    case LUA_TTABLE: {
      push_onecapture(ms, 0, s, e);
      lua_gettable(L, 3);
      break;
    }
    default: { /* LUA_TNUMBER or LUA_TSTRING */
      add_s(ms, b, s, e);
      return;
    }
  }
  if (!lua_toboolean(L, -1)) { /* nil or false? */
    lua_pop(L, 1);
    lua_pushlstring(L, s, e - s); /* keep original text */
  } else if (!lua_isstring(L, -1))
    raise_error("invalid replacement value (a %s)", luaL_typename(L, -1));
  luaL_addvalue(b); /* add result to accumulator */
}

static int
str_gsub()
{
  size_t srcl, lp;
  const char* src = luaL_checklstring(L, 1, &srcl);    /* subject */
  const char* p = luaL_checklstring(L, 2, &lp);        /* pattern */
  const char* lastmatch = NULL;                        /* end of last match */
  int tr = lua_type(L, 3);                             /* replacement type */
  int max_s = luaL_optinteger(L, 4, srcl + 1); /* max replacements */
  int anchor = (*p == '^');
  int n = 0; /* replacement count */
  MatchState ms;
  luaL_Buffer b;
  luaL_argcheck(tr == LUA_TNUMBER || tr == LUA_TSTRING ||
                tr == LUA_TFUNCTION || tr == LUA_TTABLE,
                3, "string/function/table expected");
  luaL_buffinit(L, &b);
  if (anchor) {
    p++;
    lp--; /* skip anchor character */
  }
  prepstate(&ms, src, srcl, p, lp);
  while (n < max_s) {
    const char* e;
    reprepstate(&ms); /* (re)prepare state for new match */
    if ((e = match(&ms, src, p)) != NULL && e != lastmatch) { /* match? */
      n++;
      add_value(&ms, &b, src, e, tr); /* add replacement to buffer */
      src = lastmatch = e;
    } else if (src < ms.src_end) /* otherwise, skip one character */
      luaL_addchar(&b, *src++);
    else
      break; /* end of subject */
    if (anchor)
      break;
  }
  luaL_addlstring(&b, src, ms.src_end - src);
  luaL_pushresult(&b);
  lua_pushinteger(L, n); /* number of substitutions */
  return 2;
}
