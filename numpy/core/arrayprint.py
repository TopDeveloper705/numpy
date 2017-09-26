"""Array printing function

$Id: arrayprint.py,v 1.9 2005/09/13 13:58:44 teoliphant Exp $

"""
from __future__ import division, absolute_import, print_function

__all__ = ["array2string", "array_str", "array_repr", "set_string_function",
           "set_printoptions", "get_printoptions"]
__docformat__ = 'restructuredtext'

#
# Written by Konrad Hinsen <hinsenk@ere.umontreal.ca>
# last revision: 1996-3-13
# modified by Jim Hugunin 1997-3-3 for repr's and str's (and other details)
# and by Perry Greenfield 2000-4-1 for numarray
# and by Travis Oliphant  2005-8-22 for numpy


# Note: Both scalartypes.c.src and arrayprint.py implement strs for numpy
# scalars but for different purposes. scalartypes.c.src has str/reprs for when
# the scalar is printed on its own, while arrayprint.py has strs for when
# scalars are printed inside an ndarray. Only the latter strs are currently
# user-customizable.

import sys
import functools
if sys.version_info[0] >= 3:
    try:
        from _thread import get_ident
    except ImportError:
        from _dummy_thread import get_ident
else:
    try:
        from thread import get_ident
    except ImportError:
        from dummy_thread import get_ident

import numpy as np
from . import numerictypes as _nt
from .umath import absolute, not_equal, isnan, isinf
from . import multiarray
from .multiarray import (array, format_longfloat, datetime_as_string,
                         datetime_data, dtype, ndarray)
from .fromnumeric import ravel, any
from .numeric import concatenate, asarray, errstate
from .numerictypes import (longlong, intc, int_, float_, complex_, bool_,
                           flexible)
import warnings

if sys.version_info[0] >= 3:
    _MAXINT = sys.maxsize
    _MININT = -sys.maxsize - 1
else:
    _MAXINT = sys.maxint
    _MININT = -sys.maxint - 1

_format_options = {
    'edgeitems': 3,  # repr N leading and trailing items of each dimension
    'threshold': 1000,  # total items > triggers array summarization
    'precision': 8,  # precision of floating point representations
    'suppress': False,  # suppress printing small floating values in exp format
    'linewidth': 75,
    'nanstr': 'nan',
    'infstr': 'inf',
    'sign': '-',
    'formatter': None }

def _make_options_dict(precision=None, threshold=None, edgeitems=None,
                       linewidth=None, suppress=None, nanstr=None, infstr=None,
                       sign=None, formatter=None):
    """ make a dictionary out of the non-None arguments, plus sanity checks """

    options = {k: v for k, v in locals().items() if v is not None}

    if suppress is not None:
        options['suppress'] = bool(suppress)

    if sign not in [None, '-', '+', ' ', 'legacy']:
        raise ValueError("sign option must be one of "
                         "' ', '+', '-', or 'legacy'")

    return options

def set_printoptions(precision=None, threshold=None, edgeitems=None,
                     linewidth=None, suppress=None, nanstr=None, infstr=None,
                     formatter=None, sign=None):
    """
    Set printing options.

    These options determine the way floating point numbers, arrays and
    other NumPy objects are displayed.

    Parameters
    ----------
    precision : int, optional
        Number of digits of precision for floating point output (default 8).
    threshold : int, optional
        Total number of array elements which trigger summarization
        rather than full repr (default 1000).
    edgeitems : int, optional
        Number of array items in summary at beginning and end of
        each dimension (default 3).
    linewidth : int, optional
        The number of characters per line for the purpose of inserting
        line breaks (default 75).
    suppress : bool, optional
        If True, always print floating point numbers using fixed point
        notation, in which case numbers equal to zero in the current precision
        will print as zero.  If False, then scientific notation is used when
        absolute value of the smallest number is < 1e-4 or the ratio of the
        maximum absolute value to the minimum is > 1e3. The default is False.
    nanstr : str, optional
        String representation of floating point not-a-number (default nan).
    infstr : str, optional
        String representation of floating point infinity (default inf).
    sign : string, either '-', '+', ' ' or 'legacy', optional
        Controls printing of the sign of floating-point types. If '+', always
        print the sign of positive values. If ' ', always prints a space
        (whitespace character) in the sign position of positive values.  If
        '-', omit the sign character of positive values. If 'legacy', print a
        space for positive values except in 0d arrays, and also add a space for
        'True' values in size-1 bool arrays. (default '-')
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are::

            - 'bool'
            - 'int'
            - 'timedelta' : a `numpy.timedelta64`
            - 'datetime' : a `numpy.datetime64`
            - 'float'
            - 'longfloat' : 128-bit floats
            - 'complexfloat'
            - 'longcomplexfloat' : composed of two 128-bit floats
            - 'numpystr' : types `numpy.string_` and `numpy.unicode_`
            - 'object' : `np.object_` arrays
            - 'str' : all other strings

        Other keys that can be used to set a group of types at once are::

            - 'all' : sets all types
            - 'int_kind' : sets 'int'
            - 'float_kind' : sets 'float' and 'longfloat'
            - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
            - 'str_kind' : sets 'str' and 'numpystr'

    See Also
    --------
    get_printoptions, set_string_function, array2string

    Notes
    -----
    `formatter` is always reset with a call to `set_printoptions`.

    Examples
    --------
    Floating point precision can be set:

    >>> np.set_printoptions(precision=4)
    >>> print(np.array([1.123456789]))
    [ 1.1235]

    Long arrays can be summarised:

    >>> np.set_printoptions(threshold=5)
    >>> print(np.arange(10))
    [0 1 2 ..., 7 8 9]

    Small results can be suppressed:

    >>> eps = np.finfo(float).eps
    >>> x = np.arange(4.)
    >>> x**2 - (x + eps)**2
    array([ -4.9304e-32,  -4.4409e-16,   0.0000e+00,   0.0000e+00])
    >>> np.set_printoptions(suppress=True)
    >>> x**2 - (x + eps)**2
    array([-0., -0.,  0.,  0.])

    A custom formatter can be used to display array elements as desired:

    >>> np.set_printoptions(formatter={'all':lambda x: 'int: '+str(-x)})
    >>> x = np.arange(3)
    >>> x
    array([int: 0, int: -1, int: -2])
    >>> np.set_printoptions()  # formatter gets reset
    >>> x
    array([0, 1, 2])

    To put back the default options, you can use:

    >>> np.set_printoptions(edgeitems=3,infstr='inf',
    ... linewidth=75, nanstr='nan', precision=8,
    ... suppress=False, threshold=1000, formatter=None)
    """
    opt = _make_options_dict(precision, threshold, edgeitems, linewidth,
                             suppress, nanstr, infstr, sign, formatter)
    # formatter is always reset
    opt['formatter'] = formatter
    _format_options.update(opt)


def get_printoptions():
    """
    Return the current print options.

    Returns
    -------
    print_opts : dict
        Dictionary of current print options with keys

          - precision : int
          - threshold : int
          - edgeitems : int
          - linewidth : int
          - suppress : bool
          - nanstr : str
          - infstr : str
          - formatter : dict of callables
          - sign : str

        For a full description of these options, see `set_printoptions`.

    See Also
    --------
    set_printoptions, set_string_function

    """
    return _format_options.copy()

def _leading_trailing(a):
    edgeitems =  _format_options['edgeitems']
    if a.ndim == 1:
        if len(a) > 2*edgeitems:
            b = concatenate((a[:edgeitems], a[-edgeitems:]))
        else:
            b = a
    else:
        if len(a) > 2*edgeitems:
            l = [_leading_trailing(a[i]) for i in range(min(len(a), edgeitems))]
            l.extend([_leading_trailing(a[-i]) for i in range(
                min(len(a), edgeitems), 0, -1)])
        else:
            l = [_leading_trailing(a[i]) for i in range(0, len(a))]
        b = concatenate(tuple(l))
    return b

def _object_format(o):
    """ Object arrays containing lists should be printed unambiguously """
    if type(o) is list:
        fmt = 'list({!r})'
    else:
        fmt = '{!r}'
    return fmt.format(o)

def repr_format(x):
    return repr(x)

def _get_formatdict(data, **opt):
    prec, supp, sign = opt['precision'], opt['suppress'], opt['sign']

    # wrapped in lambdas to avoid taking a code path with the wrong type of data
    formatdict = {'bool': lambda: BoolFormat(data, legacy=(sign == 'legacy')),
                  'int': lambda: IntegerFormat(data),
                  'float': lambda: FloatFormat(data, prec, supp, sign),
                  'longfloat': lambda: LongFloatFormat(prec),
                  'complexfloat': lambda: ComplexFormat(data, prec, supp, sign),
                  'longcomplexfloat': lambda: LongComplexFormat(prec),
                  'datetime': lambda: DatetimeFormat(data),
                  'timedelta': lambda: TimedeltaFormat(data),
                  'object': lambda: _object_format,
                  'numpystr': lambda: repr_format,
                  'str': lambda: str}

    # we need to wrap values in `formatter` in a lambda, so that the interface
    # is the same as the above values.
    def indirect(x):
        return lambda: x

    formatter = opt['formatter']
    if formatter is not None:
        fkeys = [k for k in formatter.keys() if formatter[k] is not None]
        if 'all' in fkeys:
            for key in formatdict.keys():
                formatdict[key] = indirect(formatter['all'])
        if 'int_kind' in fkeys:
            for key in ['int']:
                formatdict[key] = indirect(formatter['int_kind'])
        if 'float_kind' in fkeys:
            for key in ['float', 'longfloat']:
                formatdict[key] = indirect(formatter['float_kind'])
        if 'complex_kind' in fkeys:
            for key in ['complexfloat', 'longcomplexfloat']:
                formatdict[key] = indirect(formatter['complex_kind'])
        if 'str_kind' in fkeys:
            for key in ['numpystr', 'str']:
                formatdict[key] = indirect(formatter['str_kind'])
        for key in formatdict.keys():
            if key in fkeys:
                formatdict[key] = indirect(formatter[key])

    return formatdict

def _get_format_function(data, **options):
    """
    find the right formatting function for the dtype_
    """
    dtype_ = data.dtype
    if dtype_.fields is not None:
        format_functions = []
        for field_name in dtype_.names:
            format_function = _get_format_function(data[field_name], **options)
            if dtype_[field_name].shape != ():
                format_function = SubArrayFormat(format_function)
            format_functions.append(format_function)
        return StructureFormat(format_functions)

    dtypeobj = dtype_.type
    formatdict = _get_formatdict(data, **options)
    if issubclass(dtypeobj, _nt.bool_):
        return formatdict['bool']()
    elif issubclass(dtypeobj, _nt.integer):
        if issubclass(dtypeobj, _nt.timedelta64):
            return formatdict['timedelta']()
        else:
            return formatdict['int']()
    elif issubclass(dtypeobj, _nt.floating):
        if issubclass(dtypeobj, _nt.longfloat):
            return formatdict['longfloat']()
        else:
            return formatdict['float']()
    elif issubclass(dtypeobj, _nt.complexfloating):
        if issubclass(dtypeobj, _nt.clongfloat):
            return formatdict['longcomplexfloat']()
        else:
            return formatdict['complexfloat']()
    elif issubclass(dtypeobj, (_nt.unicode_, _nt.string_)):
        return formatdict['numpystr']()
    elif issubclass(dtypeobj, _nt.datetime64):
        return formatdict['datetime']()
    elif issubclass(dtypeobj, _nt.object_):
        return formatdict['object']()
    else:
        return formatdict['numpystr']()


def _recursive_guard(fillvalue='...'):
    """
    Like the python 3.2 reprlib.recursive_repr, but forwards *args and **kwargs

    Decorates a function such that if it calls itself with the same first
    argument, it returns `fillvalue` instead of recursing.

    Largely copied from reprlib.recursive_repr
    """

    def decorating_function(f):
        repr_running = set()

        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            key = id(self), get_ident()
            if key in repr_running:
                return fillvalue
            repr_running.add(key)
            try:
                return f(self, *args, **kwargs)
            finally:
                repr_running.discard(key)

        return wrapper

    return decorating_function


# gracefully handle recursive calls, when object arrays contain themselves
@_recursive_guard()
def _array2string(a, options, separator=' ', prefix=""):

    if a.size > options['threshold']:
        summary_insert = "..., "
        data = _leading_trailing(a)
    else:
        summary_insert = ""
        data = asarray(a)

    # find the right formatting function for the array
    format_function = _get_format_function(data, **options)

    # skip over "["
    next_line_prefix = " "
    # skip over array(
    next_line_prefix += " "*len(prefix)

    lst = _formatArray(a, format_function, a.ndim, options['linewidth'],
                       next_line_prefix, separator,
                       options['edgeitems'], summary_insert)[:-1]
    return lst



def array2string(a, max_line_width=None, precision=None,
                 suppress_small=None, separator=' ', prefix="",
                 style=np._NoValue, formatter=None, threshold=None,
                 edgeitems=None, sign=None):
    """
    Return a string representation of an array.

    Parameters
    ----------
    a : ndarray
        Input array.
    max_line_width : int, optional
        The maximum number of columns the string should span. Newline
        characters splits the string appropriately after array elements.
    precision : int, optional
        Floating point precision. Default is the current printing
        precision (usually 8), which can be altered using `set_printoptions`.
    suppress_small : bool, optional
        Represent very small numbers as zero. A number is "very small" if it
        is smaller than the current printing precision.
    separator : str, optional
        Inserted between elements.
    prefix : str, optional
        An array is typically printed as::

          'prefix(' + array2string(a) + ')'

        The length of the prefix string is used to align the
        output correctly.
    style : _NoValue, optional
        Has no effect, do not use.

        .. deprecated:: 1.14.0
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are::

            - 'bool'
            - 'int'
            - 'timedelta' : a `numpy.timedelta64`
            - 'datetime' : a `numpy.datetime64`
            - 'float'
            - 'longfloat' : 128-bit floats
            - 'complexfloat'
            - 'longcomplexfloat' : composed of two 128-bit floats
            - 'numpystr' : types `numpy.string_` and `numpy.unicode_`
            - 'str' : all other strings

        Other keys that can be used to set a group of types at once are::

            - 'all' : sets all types
            - 'int_kind' : sets 'int'
            - 'float_kind' : sets 'float' and 'longfloat'
            - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
            - 'str_kind' : sets 'str' and 'numpystr'
    threshold : int, optional
        Total number of array elements which trigger summarization
        rather than full repr.
    edgeitems : int, optional
        Number of array items in summary at beginning and end of
        each dimension.
    sign : string, either '-', '+', ' ' or 'legacy', optional
        Controls printing of the sign of floating-point types. If '+', always
        print the sign of positive values. If ' ', always prints a space
        (whitespace character) in the sign position of positive values.  If
        '-', omit the sign character of positive values. If 'legacy', print a
        space for positive values except in 0d arrays, and also add a space for
        'True' values in size-1 bool arrays.

    Returns
    -------
    array_str : str
        String representation of the array.

    Raises
    ------
    TypeError
        if a callable in `formatter` does not return a string.

    See Also
    --------
    array_str, array_repr, set_printoptions, get_printoptions

    Notes
    -----
    If a formatter is specified for a certain type, the `precision` keyword is
    ignored for that type.

    This is a very flexible function; `array_repr` and `array_str` are using
    `array2string` internally so keywords with the same name should work
    identically in all three functions.

    Examples
    --------
    >>> x = np.array([1e-16,1,2,3])
    >>> print(np.array2string(x, precision=2, separator=',',
    ...                       suppress_small=True))
    [ 0., 1., 2., 3.]

    >>> x  = np.arange(3.)
    >>> np.array2string(x, formatter={'float_kind':lambda x: "%.2f" % x})
    '[0.00 1.00 2.00]'

    >>> x  = np.arange(3)
    >>> np.array2string(x, formatter={'int':lambda x: hex(x)})
    '[0x0L 0x1L 0x2L]'

    """
    # Deprecation 05-16-2017  v1.14
    if style is not np._NoValue:
        warnings.warn("'style' argument is deprecated and no longer functional",
                      DeprecationWarning, stacklevel=3)

    overrides = _make_options_dict(precision, threshold, edgeitems,
                                   max_line_width, suppress_small, None, None,
                                   sign, formatter)
    options = _format_options.copy()
    options.update(overrides)

    if a.size == 0:
        # treat as a null array if any of shape elements == 0
        lst = "[]"
    else:
        lst = _array2string(a, options, separator, prefix)
    return lst


def _extendLine(s, line, word, max_line_len, next_line_prefix):
    if len(line.rstrip()) + len(word.rstrip()) >= max_line_len:
        s += line.rstrip() + "\n"
        line = next_line_prefix
    line += word
    return s, line


def _formatArray(a, format_function, rank, max_line_len,
                 next_line_prefix, separator, edge_items, summary_insert):
    """formatArray is designed for two modes of operation:

    1. Full output

    2. Summarized output

    """
    if rank == 0:
        return format_function(a[()]) + '\n'

    if summary_insert and 2*edge_items < len(a):
        leading_items = edge_items
        trailing_items = edge_items
        summary_insert1 = summary_insert
    else:
        leading_items = 0
        trailing_items = len(a)
        summary_insert1 = ""

    if rank == 1:
        s = ""
        line = next_line_prefix
        for i in range(leading_items):
            word = format_function(a[i]) + separator
            s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)

        if summary_insert1:
            s, line = _extendLine(s, line, summary_insert1, max_line_len, next_line_prefix)

        for i in range(trailing_items, 1, -1):
            word = format_function(a[-i]) + separator
            s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)

        word = format_function(a[-1])
        s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)
        s += line + "]\n"
        s = '[' + s[len(next_line_prefix):]
    else:
        s = '['
        sep = separator.rstrip()
        for i in range(leading_items):
            if i > 0:
                s += next_line_prefix
            s += _formatArray(a[i], format_function, rank-1, max_line_len,
                              " " + next_line_prefix, separator, edge_items,
                              summary_insert)
            s = s.rstrip() + sep.rstrip() + '\n'*max(rank-1, 1)

        if summary_insert1:
            s += next_line_prefix + summary_insert1 + "\n"

        for i in range(trailing_items, 1, -1):
            if leading_items or i != trailing_items:
                s += next_line_prefix
            s += _formatArray(a[-i], format_function, rank-1, max_line_len,
                              " " + next_line_prefix, separator, edge_items,
                              summary_insert)
            s = s.rstrip() + sep.rstrip() + '\n'*max(rank-1, 1)
        if leading_items or trailing_items > 1:
            s += next_line_prefix
        s += _formatArray(a[-1], format_function, rank-1, max_line_len,
                          " " + next_line_prefix, separator, edge_items,
                          summary_insert).rstrip()+']\n'
    return s

class FloatFormat(object):
    def __init__(self, data, precision, suppress_small, sign=False):
        # for backcompatibility, accept bools
        if isinstance(sign, bool):
            sign = '+' if sign else '-'

        if sign == 'legacy':
            sign = '-' if data.shape == () else ' '

        self.precision = precision
        self.suppress_small = suppress_small
        self.sign = sign
        self.exp_format = False
        self.large_exponent = False
        try:
            self.fillFormat(data)
        except (NotImplementedError):
            # if reduce(data) fails, this instance will not be called, just
            # instantiated in formatdict.
            pass

    def fillFormat(self, data):
        with errstate(all='ignore'):
            hasinf = isinf(data)
            special = isnan(data) | hasinf
            valid = not_equal(data, 0) & ~special
            non_zero = data[valid]
            abs_non_zero = absolute(non_zero)
            if len(non_zero) == 0:
                max_val = 0.
                min_val = 0.
                min_val_sgn = 0.
            else:
                max_val = np.max(abs_non_zero)
                min_val = np.min(abs_non_zero)
                min_val_sgn = np.min(non_zero)
                if max_val >= 1.e8:
                    self.exp_format = True
                if not self.suppress_small and (min_val < 0.0001
                                           or max_val/min_val > 1000.):
                    self.exp_format = True

        if self.exp_format:
            self.large_exponent = 0 < min_val < 1e-99 or max_val >= 1e100

            signpos = self.sign != '-' or any(non_zero < 0)
            # for back-compatibility with np 1.13, add extra space if padded
            signpos = signpos if self.sign != ' ' else 2
            max_str_len = signpos + 6 + self.precision + self.large_exponent

            conversion = '' if self.sign == '-' else self.sign
            format = '%' + conversion + '%d.%de' % (max_str_len, self.precision)
        else:
            if len(non_zero) and self.precision > 0:
                precision = self.precision
                trim_zero = lambda s: precision - (len(s) - len(s.rstrip('0')))
                fmt = '%%.%df' % (precision,)
                precision = max(trim_zero(fmt % x) for x in abs_non_zero)
            else:
                precision = 0

            int_len = len(str(int(max_val)))
            signpos = self.sign != '-' or (len(str(int(min_val_sgn))) > int_len)
            max_str_len = signpos + int_len + 1 + precision

            if any(special):
                neginf = self.sign != '-' or any(data[hasinf] < 0)
                nanlen = len(_format_options['nanstr'])
                inflen = len(_format_options['infstr']) + neginf
                max_str_len = max(max_str_len, nanlen, inflen)

            conversion = '' if self.sign == '-' else self.sign
            format = '%#' + conversion + '%d.%df' % (max_str_len, precision)

        self.special_fmt = '%%%ds' % (max_str_len,)
        self.format = format

    def __call__(self, x, strip_zeros=True):
        with errstate(invalid='ignore'):
            if isnan(x):
                nan_str = _format_options['nanstr']
                if self.sign == '+':
                    return self.special_fmt % ('+' + nan_str,)
                else:
                    return self.special_fmt % (nan_str,)
            elif isinf(x):
                inf_str = _format_options['infstr']
                if x > 0:
                    if self.sign == '+':
                        return self.special_fmt % ('+' + inf_str,)
                    else:
                        return self.special_fmt % (inf_str,)
                else:
                    return self.special_fmt % ('-' + inf_str,)

        s = self.format % x
        if self.large_exponent:
            # 3-digit exponent
            expsign = s[-3]
            if expsign == '+' or expsign == '-':
                s = s[1:-2] + '0' + s[-2:]
        elif self.exp_format:
            # 2-digit exponent
            if s[-3] == '0':
                s = ' ' + s[:-3] + s[-2:]
        elif strip_zeros:
            z = s.rstrip('0')
            s = z + ' '*(len(s)-len(z))
        return s

class IntegerFormat(object):
    def __init__(self, data):
        try:
            max_str_len = max(len(str(np.max(data))),
                              len(str(np.min(data))))
            self.format = '%' + str(max_str_len) + 'd'
        except (TypeError, NotImplementedError):
            # if reduce(data) fails, this instance will not be called, just
            # instantiated in formatdict.
            pass
        except ValueError:
            # this occurs when everything is NA
            pass

    def __call__(self, x):
        if _MININT < x < _MAXINT:
            return self.format % x
        else:
            return "%s" % x

class BoolFormat(object):
    def __init__(self, data, **kwargs):
        # in legacy printing style, include a space before True except in 0d
        if kwargs.get('legacy', False):
            self.truestr = ' True' if data.shape != () else 'True'
            return

        # add an extra space so " True" and "False" have the same length and
        # array elements align nicely when printed, but only for arrays with
        # more than one element (0d and nd)
        self.truestr = ' True' if data.size > 1 else 'True'

    def __call__(self, x):
        return self.truestr if x else "False"


class LongFloatFormat(object):
    # XXX Have to add something to determine the width to use a la FloatFormat
    # Right now, things won't line up properly
    def __init__(self, precision, sign=False):
        # for backcompatibility, accept bools
        if isinstance(sign, bool):
            sign = '+' if sign else '-'

        self.precision = precision
        self.sign = sign

    def __call__(self, x):
        if isnan(x):
            nan_str = _format_options['nanstr']
            if self.sign == '+':
                return '+' + nan_str
            else:
                return ' ' + nan_str
        elif isinf(x):
            inf_str = _format_options['infstr']
            if x > 0:
                if self.sign == '+':
                    return '+' + inf_str
                else:
                    return ' ' + inf_str
            else:
                return '-' + inf_str
        elif x >= 0:
            if self.sign == '+':
                return '+' + format_longfloat(x, self.precision)
            else:
                return ' ' + format_longfloat(x, self.precision)
        else:
            return format_longfloat(x, self.precision)


class LongComplexFormat(object):
    def __init__(self, precision):
        self.real_format = LongFloatFormat(precision)
        self.imag_format = LongFloatFormat(precision, sign='+')

    def __call__(self, x):
        r = self.real_format(x.real)
        i = self.imag_format(x.imag)
        return r + i + 'j'


class ComplexFormat(object):
    def __init__(self, x, precision, suppress_small, sign=False):
        # for backcompatibility, accept bools
        if isinstance(sign, bool):
            sign = '+' if sign else '-'

        self.real_format = FloatFormat(x.real, precision, suppress_small,
                                       sign=sign)
        self.imag_format = FloatFormat(x.imag, precision, suppress_small,
                                       sign='+')

    def __call__(self, x):
        r = self.real_format(x.real, strip_zeros=False)
        i = self.imag_format(x.imag, strip_zeros=False)
        if not self.imag_format.exp_format:
            z = i.rstrip('0')
            i = z + 'j' + ' '*(len(i)-len(z))
        else:
            i = i + 'j'
        return r + i


class DatetimeFormat(object):
    def __init__(self, x, unit=None, timezone=None, casting='same_kind'):
        # Get the unit from the dtype
        if unit is None:
            if x.dtype.kind == 'M':
                unit = datetime_data(x.dtype)[0]
            else:
                unit = 's'

        if timezone is None:
            timezone = 'naive'
        self.timezone = timezone
        self.unit = unit
        self.casting = casting

    def __call__(self, x):
        return "'%s'" % datetime_as_string(x,
                                    unit=self.unit,
                                    timezone=self.timezone,
                                    casting=self.casting)

class TimedeltaFormat(object):
    def __init__(self, data):
        nat_value = array(['NaT'], dtype=data.dtype)[0]
        int_dtype = dtype(data.dtype.byteorder + 'i8')
        int_view = data.view(int_dtype)
        v = int_view[not_equal(int_view, nat_value.view(int_dtype))]
        if len(v) > 0:
            # Max str length of non-NaT elements
            max_str_len = max(len(str(np.max(v))),
                              len(str(np.min(v))))
        else:
            max_str_len = 0
        if len(v) < len(data):
            # data contains a NaT
            max_str_len = max(max_str_len, 5)
        self.format = '%' + str(max_str_len) + 'd'
        self._nat = "'NaT'".rjust(max_str_len)

    def __call__(self, x):
        # TODO: After NAT == NAT deprecation should be simplified:
        if (x + 1).view('i8') == x.view('i8'):
            return self._nat
        else:
            return self.format % x.astype('i8')


class SubArrayFormat(object):
    def __init__(self, format_function):
        self.format_function = format_function

    def __call__(self, arr):
        if arr.ndim <= 1:
            return "[" + ", ".join(self.format_function(a) for a in arr) + "]"
        return "[" + ", ".join(self.__call__(a) for a in arr) + "]"


class StructureFormat(object):
    def __init__(self, format_functions):
        self.format_functions = format_functions
        self.num_fields = len(format_functions)

    def __call__(self, x):
        s = "("
        for field, format_function in zip(x, self.format_functions):
            s += format_function(field) + ", "
        return (s[:-2] if 1 < self.num_fields else s[:-1]) + ")"


_typelessdata = [int_, float_, complex_]
if issubclass(intc, int):
    _typelessdata.append(intc)
if issubclass(longlong, int):
    _typelessdata.append(longlong)

def array_repr(arr, max_line_width=None, precision=None, suppress_small=None):
    """
    Return the string representation of an array.

    Parameters
    ----------
    arr : ndarray
        Input array.
    max_line_width : int, optional
        The maximum number of columns the string should span. Newline
        characters split the string appropriately after array elements.
    precision : int, optional
        Floating point precision. Default is the current printing precision
        (usually 8), which can be altered using `set_printoptions`.
    suppress_small : bool, optional
        Represent very small numbers as zero, default is False. Very small
        is defined by `precision`, if the precision is 8 then
        numbers smaller than 5e-9 are represented as zero.

    Returns
    -------
    string : str
      The string representation of an array.

    See Also
    --------
    array_str, array2string, set_printoptions

    Examples
    --------
    >>> np.array_repr(np.array([1,2]))
    'array([1, 2])'
    >>> np.array_repr(np.ma.array([0.]))
    'MaskedArray([ 0.])'
    >>> np.array_repr(np.array([], np.int32))
    'array([], dtype=int32)'

    >>> x = np.array([1e-6, 4e-7, 2, 3])
    >>> np.array_repr(x, precision=6, suppress_small=True)
    'array([ 0.000001,  0.      ,  2.      ,  3.      ])'

    """
    if type(arr) is not ndarray:
        class_name = type(arr).__name__
    else:
        class_name = "array"

    if arr.size > 0 or arr.shape == (0,):
        lst = array2string(arr, max_line_width, precision, suppress_small,
                           ', ', class_name + "(")
    else:  # show zero-length shape unless it is (0,)
        lst = "[], shape=%s" % (repr(arr.shape),)

    skipdtype = (arr.dtype.type in _typelessdata) and arr.size > 0

    if skipdtype:
        return "%s(%s)" % (class_name, lst)
    else:
        typename = arr.dtype.name
        # Quote typename in the output if it is "complex".
        if typename and not (typename[0].isalpha() and typename.isalnum()):
            typename = "'%s'" % typename

        lf = ' '
        if issubclass(arr.dtype.type, flexible):
            if arr.dtype.names:
                typename = "%s" % str(arr.dtype)
            else:
                typename = "'%s'" % str(arr.dtype)
            lf = '\n'+' '*len(class_name + "(")
        return "%s(%s,%sdtype=%s)" % (class_name, lst, lf, typename)

def array_str(a, max_line_width=None, precision=None, suppress_small=None):
    """
    Return a string representation of the data in an array.

    The data in the array is returned as a single string.  This function is
    similar to `array_repr`, the difference being that `array_repr` also
    returns information on the kind of array and its data type.

    Parameters
    ----------
    a : ndarray
        Input array.
    max_line_width : int, optional
        Inserts newlines if text is longer than `max_line_width`.  The
        default is, indirectly, 75.
    precision : int, optional
        Floating point precision.  Default is the current printing precision
        (usually 8), which can be altered using `set_printoptions`.
    suppress_small : bool, optional
        Represent numbers "very close" to zero as zero; default is False.
        Very close is defined by precision: if the precision is 8, e.g.,
        numbers smaller (in absolute value) than 5e-9 are represented as
        zero.

    See Also
    --------
    array2string, array_repr, set_printoptions

    Examples
    --------
    >>> np.array_str(np.arange(3))
    '[0 1 2]'

    """
    return array2string(a, max_line_width, precision, suppress_small, ' ', "")

def set_string_function(f, repr=True):
    """
    Set a Python function to be used when pretty printing arrays.

    Parameters
    ----------
    f : function or None
        Function to be used to pretty print arrays. The function should expect
        a single array argument and return a string of the representation of
        the array. If None, the function is reset to the default NumPy function
        to print arrays.
    repr : bool, optional
        If True (default), the function for pretty printing (``__repr__``)
        is set, if False the function that returns the default string
        representation (``__str__``) is set.

    See Also
    --------
    set_printoptions, get_printoptions

    Examples
    --------
    >>> def pprint(arr):
    ...     return 'HA! - What are you going to do now?'
    ...
    >>> np.set_string_function(pprint)
    >>> a = np.arange(10)
    >>> a
    HA! - What are you going to do now?
    >>> print(a)
    [0 1 2 3 4 5 6 7 8 9]

    We can reset the function to the default:

    >>> np.set_string_function(None)
    >>> a
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    `repr` affects either pretty printing or normal string representation.
    Note that ``__repr__`` is still affected by setting ``__str__``
    because the width of each array element in the returned string becomes
    equal to the length of the result of ``__str__()``.

    >>> x = np.arange(4)
    >>> np.set_string_function(lambda x:'random', repr=False)
    >>> x.__str__()
    'random'
    >>> x.__repr__()
    'array([     0,      1,      2,      3])'

    """
    if f is None:
        if repr:
            return multiarray.set_string_function(array_repr, 1)
        else:
            return multiarray.set_string_function(array_str, 0)
    else:
        return multiarray.set_string_function(f, repr)

set_string_function(array_str, 0)
set_string_function(array_repr, 1)
