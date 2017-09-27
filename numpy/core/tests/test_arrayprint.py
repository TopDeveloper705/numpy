# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function

import sys

import numpy as np
from numpy.testing import (
     run_module_suite, assert_, assert_equal, assert_raises, assert_warns
)

class TestArrayRepr(object):
    def test_nan_inf(self):
        x = np.array([np.nan, np.inf])
        assert_equal(repr(x), 'array([nan, inf])')

    def test_subclass(self):
        class sub(np.ndarray): pass

        # one dimensional
        x1d = np.array([1, 2]).view(sub)
        assert_equal(repr(x1d), 'sub([1, 2])')

        # two dimensional
        x2d = np.array([[1, 2], [3, 4]]).view(sub)
        assert_equal(repr(x2d),
            'sub([[1, 2],\n'
            '     [3, 4]])')

        # two dimensional with flexible dtype
        xstruct = np.ones((2,2), dtype=[('a', 'i4')]).view(sub)
        assert_equal(repr(xstruct),
            "sub([[(1,), (1,)],\n"
            "     [(1,), (1,)]],\n"
            "    dtype=[('a', '<i4')])"
        )

    def test_self_containing(self):
        arr0d = np.array(None)
        arr0d[()] = arr0d
        assert_equal(repr(arr0d),
            'array(array(..., dtype=object), dtype=object)')

        arr1d = np.array([None, None])
        arr1d[1] = arr1d
        assert_equal(repr(arr1d),
            'array([None, array(..., dtype=object)], dtype=object)')

        first = np.array(None)
        second = np.array(None)
        first[()] = second
        second[()] = first
        assert_equal(repr(first),
            'array(array(array(..., dtype=object), dtype=object), dtype=object)')

    def test_containing_list(self):
        # printing square brackets directly would be ambiguuous
        arr1d = np.array([None, None])
        arr1d[0] = [1, 2]
        arr1d[1] = [3]
        assert_equal(repr(arr1d),
            'array([list([1, 2]), list([3])], dtype=object)')

    def test_void_scalar_recursion(self):
        # gh-9345
        repr(np.void(b'test'))  # RecursionError ?


class TestComplexArray(object):
    def test_str(self):
        rvals = [0, 1, -1, np.inf, -np.inf, np.nan]
        cvals = [complex(rp, ip) for rp in rvals for ip in rvals]
        dtypes = [np.complex64, np.cdouble, np.clongdouble]
        actual = [str(np.array([c], dt)) for c in cvals for dt in dtypes]
        wanted = [
            '[0.+0.j]',    '[0.+0.j]',    '[0.+0.j]',
            '[0.+1.j]',    '[0.+1.j]',    '[0.+1.j]',
            '[0.-1.j]',    '[0.-1.j]',    '[0.-1.j]',
            '[0.+infj]',   '[0.+infj]',   '[0.+infj]',
            '[0.-infj]',   '[0.-infj]',   '[0.-infj]',
            '[0.+nanj]',   '[0.+nanj]',   '[0.+nanj]',
            '[1.+0.j]',    '[1.+0.j]',    '[1.+0.j]',
            '[1.+1.j]',    '[1.+1.j]',    '[1.+1.j]',
            '[1.-1.j]',    '[1.-1.j]',    '[1.-1.j]',
            '[1.+infj]',   '[1.+infj]',   '[1.+infj]',
            '[1.-infj]',   '[1.-infj]',   '[1.-infj]',
            '[1.+nanj]',   '[1.+nanj]',   '[1.+nanj]',
            '[-1.+0.j]',   '[-1.+0.j]',   '[-1.+0.j]',
            '[-1.+1.j]',   '[-1.+1.j]',   '[-1.+1.j]',
            '[-1.-1.j]',   '[-1.-1.j]',   '[-1.-1.j]',
            '[-1.+infj]',  '[-1.+infj]',  '[-1.+infj]',
            '[-1.-infj]',  '[-1.-infj]',  '[-1.-infj]',
            '[-1.+nanj]',  '[-1.+nanj]',  '[-1.+nanj]',
            '[inf+0.j]',   '[inf+0.j]',   '[inf+0.j]',
            '[inf+1.j]',   '[inf+1.j]',   '[inf+1.j]',
            '[inf-1.j]',   '[inf-1.j]',   '[inf-1.j]',
            '[inf+infj]',  '[inf+infj]',  '[inf+infj]',
            '[inf-infj]',  '[inf-infj]',  '[inf-infj]',
            '[inf+nanj]',  '[inf+nanj]',  '[inf+nanj]',
            '[-inf+0.j]',  '[-inf+0.j]',  '[-inf+0.j]',
            '[-inf+1.j]',  '[-inf+1.j]',  '[-inf+1.j]',
            '[-inf-1.j]',  '[-inf-1.j]',  '[-inf-1.j]',
            '[-inf+infj]', '[-inf+infj]', '[-inf+infj]',
            '[-inf-infj]', '[-inf-infj]', '[-inf-infj]',
            '[-inf+nanj]', '[-inf+nanj]', '[-inf+nanj]',
            '[nan+0.j]',   '[nan+0.j]',   '[nan+0.j]',
            '[nan+1.j]',   '[nan+1.j]',   '[nan+1.j]',
            '[nan-1.j]',   '[nan-1.j]',   '[nan-1.j]',
            '[nan+infj]',  '[nan+infj]',  '[nan+infj]',
            '[nan-infj]',  '[nan-infj]',  '[nan-infj]',
            '[nan+nanj]',  '[nan+nanj]',  '[nan+nanj]']

        for res, val in zip(actual, wanted):
            assert_equal(res, val)

class TestArray2String(object):
    def test_basic(self):
        """Basic test of array2string."""
        a = np.arange(3)
        assert_(np.array2string(a) == '[0 1 2]')
        assert_(np.array2string(a, max_line_width=4) == '[0 1\n 2]')

    def test_format_function(self):
        """Test custom format function for each element in array."""
        def _format_function(x):
            if np.abs(x) < 1:
                return '.'
            elif np.abs(x) < 2:
                return 'o'
            else:
                return 'O'

        x = np.arange(3)
        if sys.version_info[0] >= 3:
            x_hex = "[0x0 0x1 0x2]"
            x_oct = "[0o0 0o1 0o2]"
        else:
            x_hex = "[0x0L 0x1L 0x2L]"
            x_oct = "[0L 01L 02L]"
        assert_(np.array2string(x, formatter={'all':_format_function}) ==
                "[. o O]")
        assert_(np.array2string(x, formatter={'int_kind':_format_function}) ==
                "[. o O]")
        assert_(np.array2string(x, formatter={'all':lambda x: "%.4f" % x}) ==
                "[0.0000 1.0000 2.0000]")
        assert_equal(np.array2string(x, formatter={'int':lambda x: hex(x)}),
                x_hex)
        assert_equal(np.array2string(x, formatter={'int':lambda x: oct(x)}),
                x_oct)

        x = np.arange(3.)
        assert_(np.array2string(x, formatter={'float_kind':lambda x: "%.2f" % x}) ==
                "[0.00 1.00 2.00]")
        assert_(np.array2string(x, formatter={'float':lambda x: "%.2f" % x}) ==
                "[0.00 1.00 2.00]")

        s = np.array(['abc', 'def'])
        assert_(np.array2string(s, formatter={'numpystr':lambda s: s*2}) ==
                '[abcabc defdef]')

    def test_structure_format(self):
        dt = np.dtype([('name', np.str_, 16), ('grades', np.float64, (2,))])
        x = np.array([('Sarah', (8.0, 7.0)), ('John', (6.0, 7.0))], dtype=dt)
        assert_equal(np.array2string(x),
                "[('Sarah', [8., 7.]) ('John', [6., 7.])]")

        # for issue #5692
        A = np.zeros(shape=10, dtype=[("A", "M8[s]")])
        A[5:].fill(np.datetime64('NaT'))
        assert_equal(np.array2string(A),
                "[('1970-01-01T00:00:00',) ('1970-01-01T00:00:00',) " +
                "('1970-01-01T00:00:00',)\n ('1970-01-01T00:00:00',) " +
                "('1970-01-01T00:00:00',) ('NaT',) ('NaT',)\n " +
                "('NaT',) ('NaT',) ('NaT',)]")

        # See #8160
        struct_int = np.array([([1, -1],), ([123, 1],)], dtype=[('B', 'i4', 2)])
        assert_equal(np.array2string(struct_int),
                "[([  1,  -1],) ([123,   1],)]")
        struct_2dint = np.array([([[0, 1], [2, 3]],), ([[12, 0], [0, 0]],)],
                dtype=[('B', 'i4', (2, 2))])
        assert_equal(np.array2string(struct_2dint),
                "[([[ 0,  1], [ 2,  3]],) ([[12,  0], [ 0,  0]],)]")

        # See #8172
        array_scalar = np.array(
                (1., 2.1234567890123456789, 3.), dtype=('f8,f8,f8'))
        assert_equal(np.array2string(array_scalar), "(1., 2.12345679, 3.)")

    def test_unstructured_void_repr(self):
        a = np.array([27, 91, 50, 75,  7, 65, 10,  8,
                      27, 91, 51, 49,109, 82,101,100], dtype='u1').view('V8')
        assert_equal(repr(a[0]), r"void(b'\x1B\x5B\x32\x4B\x07\x41\x0A\x08')")
        assert_equal(str(a[0]), r"b'\x1B\x5B\x32\x4B\x07\x41\x0A\x08'")
        assert_equal(repr(a),
            r"array([b'\x1B\x5B\x32\x4B\x07\x41\x0A\x08'," "\n"
            r"       b'\x1B\x5B\x33\x31\x6D\x52\x65\x64']," "\n"
            r"      dtype='|V8')")

        assert_equal(eval(repr(a), vars(np)), a)
        assert_equal(eval(repr(a[0]), vars(np)), a[0])


class TestPrintOptions(object):
    """Test getting and setting global print options."""

    def setup(self):
        self.oldopts = np.get_printoptions()

    def teardown(self):
        np.set_printoptions(**self.oldopts)

    def test_basic(self):
        x = np.array([1.5, 0, 1.234567890])
        assert_equal(repr(x), "array([1.5       , 0.        , 1.23456789])")
        np.set_printoptions(precision=4)
        assert_equal(repr(x), "array([1.5   , 0.    , 1.2346])")

    def test_precision_zero(self):
        np.set_printoptions(precision=0)
        for values, string in (
                ([0.], "0."), ([.3], "0."), ([-.3], "-0."), ([.7], "1."),
                ([1.5], "2."), ([-1.5], "-2."), ([-15.34], "-15."),
                ([100.], "100."), ([.2, -1, 122.51], "  0.,  -1., 123."),
                ([0], "0"), ([-12], "-12"), ([complex(.3, -.7)], "0.-1.j")):
            x = np.array(values)
            assert_equal(repr(x), "array([%s])" % string)

    def test_formatter(self):
        x = np.arange(3)
        np.set_printoptions(formatter={'all':lambda x: str(x-1)})
        assert_equal(repr(x), "array([-1, 0, 1])")

    def test_formatter_reset(self):
        x = np.arange(3)
        np.set_printoptions(formatter={'all':lambda x: str(x-1)})
        assert_equal(repr(x), "array([-1, 0, 1])")
        np.set_printoptions(formatter={'int':None})
        assert_equal(repr(x), "array([0, 1, 2])")

        np.set_printoptions(formatter={'all':lambda x: str(x-1)})
        assert_equal(repr(x), "array([-1, 0, 1])")
        np.set_printoptions(formatter={'all':None})
        assert_equal(repr(x), "array([0, 1, 2])")

        np.set_printoptions(formatter={'int':lambda x: str(x-1)})
        assert_equal(repr(x), "array([-1, 0, 1])")
        np.set_printoptions(formatter={'int_kind':None})
        assert_equal(repr(x), "array([0, 1, 2])")

        x = np.arange(3.)
        np.set_printoptions(formatter={'float':lambda x: str(x-1)})
        assert_equal(repr(x), "array([-1.0, 0.0, 1.0])")
        np.set_printoptions(formatter={'float_kind':None})
        assert_equal(repr(x), "array([0., 1., 2.])")

    def test_0d_arrays(self):
        unicode = type(u'')
        assert_equal(unicode(np.array(u'café', np.unicode_)), u'café')

        if sys.version_info[0] >= 3:
            assert_equal(repr(np.array('café', np.unicode_)),
                         "array('café',\n      dtype='<U4')")
        else:
            assert_equal(repr(np.array(u'café', np.unicode_)),
                         "array(u'caf\\xe9',\n      dtype='<U4')")
        assert_equal(str(np.array('test', np.str_)), 'test')

        a = np.zeros(1, dtype=[('a', '<i4', (3,))])
        assert_equal(str(a[0]), '([0, 0, 0],)')

        assert_equal(repr(np.datetime64('2005-02-25')[...]),
                     "array('2005-02-25', dtype='datetime64[D]')")

        # repr of 0d arrays is affected by printoptions
        x = np.array(1)
        np.set_printoptions(formatter={'all':lambda x: "test"})
        assert_equal(repr(x), "array(test)")
        # str is unaffected
        assert_equal(str(x), "1")

        # check `style` arg raises
        assert_warns(DeprecationWarning, np.array2string,
                                         np.array(1.), style=repr)
        # but not in legacy mode
        np.set_printoptions(legacy=True)
        np.array2string(np.array(1.), style=repr)

    def test_float_spacing(self):
        x = np.array([1., 2., 3.])
        y = np.array([1., 2., -10.])
        z = np.array([100., 2., -1.])
        w = np.array([-100., 2., 1.])

        assert_equal(repr(x), 'array([1., 2., 3.])')
        assert_equal(repr(y), 'array([  1.,   2., -10.])')
        assert_equal(repr(np.array(y[0])), 'array(1.)')
        assert_equal(repr(np.array(y[-1])), 'array(-10.)')
        assert_equal(repr(z), 'array([100.,   2.,  -1.])')
        assert_equal(repr(w), 'array([-100.,    2.,    1.])')

        assert_equal(repr(np.array([np.nan, np.inf])), 'array([nan, inf])')
        assert_equal(repr(np.array([np.nan, -np.inf])), 'array([ nan, -inf])')

        x = np.array([np.inf, 100000, 1.1234])
        y = np.array([np.inf, 100000, -1.1234])
        z = np.array([np.inf, 1.1234, -1e120])
        np.set_printoptions(precision=2)
        assert_equal(repr(x), 'array([     inf, 1.00e+05, 1.12e+00])')
        assert_equal(repr(y), 'array([      inf,  1.00e+05, -1.12e+00])')
        assert_equal(repr(z), 'array([       inf,  1.12e+000, -1.00e+120])')

    def test_bool_spacing(self):
        assert_equal(repr(np.array([True,  True])),
                     'array([ True,  True], dtype=bool)')
        assert_equal(repr(np.array([True, False])),
                     'array([ True, False], dtype=bool)')
        assert_equal(repr(np.array([True])),
                     'array([ True], dtype=bool)')
        assert_equal(repr(np.array(True)),
                     'array(True, dtype=bool)')
        assert_equal(repr(np.array(False)),
                     'array(False, dtype=bool)')

    def test_sign_spacing(self):
        a = np.arange(4.)
        b = np.array([1.234e9])

        assert_equal(repr(a), 'array([0., 1., 2., 3.])')
        assert_equal(repr(np.array(1.)), 'array(1.)')
        assert_equal(repr(b), 'array([1.234e+09])')

        np.set_printoptions(sign=' ')
        assert_equal(repr(a), 'array([ 0.,  1.,  2.,  3.])')
        assert_equal(repr(np.array(1.)), 'array( 1.)')
        assert_equal(repr(b), 'array([ 1.234e+09])')

        np.set_printoptions(sign='+')
        assert_equal(repr(a), 'array([+0., +1., +2., +3.])')
        assert_equal(repr(np.array(1.)), 'array(+1.)')
        assert_equal(repr(b), 'array([+1.234e+09])')

        np.set_printoptions(legacy=True)
        assert_equal(repr(a), 'array([ 0.,  1.,  2.,  3.])')
        assert_equal(repr(b),  'array([  1.23400000e+09])')
        assert_equal(repr(-b), 'array([ -1.23400000e+09])')
        assert_equal(repr(np.array(1.)), 'array(1.0)')

        assert_raises(TypeError, np.set_printoptions, wrongarg=True)

    def test_sign_spacing_structured(self):
        a = np.ones(2, dtype='f,f')
        assert_equal(repr(a), "array([(1., 1.), (1., 1.)],\n"
                              "      dtype=[('f0', '<f4'), ('f1', '<f4')])")
        assert_equal(repr(a[0]), "(1., 1.)")

    def test_floatmode(self):
        x = np.array([0.6104, 0.922, 0.457, 0.0906, 0.3733, 0.007244,
                      0.5933, 0.947, 0.2383, 0.4226], dtype=np.float16)
        y = np.array([0.2918820979355541, 0.5064172631089138,
                      0.2848750619642916, 0.4342965294660567,
                      0.7326538397312751, 0.3459503329096204,
                      0.0862072768214508, 0.39112753029631175],
                      dtype=np.float64)
        z = np.arange(6, dtype=np.float16)/10

        # also make sure 1e23 is right (is between two fp numbers)
        w = np.array(['1e{}'.format(i) for i in range(25)], dtype=np.float64)
        # note: we construct w from the strings `1eXX` instead of doing
        # `10.**arange(24)` because it turns out the two are not equivalent in
        # python. On some architectures `1e23 != 10.**23`.
        wp = np.array([1.234e1, 1e2, 1e123])

        # unique mode
        np.set_printoptions(floatmode='unique')
        assert_equal(repr(x),
            "array([0.6104  , 0.922   , 0.457   , 0.0906  , 0.3733  , 0.007244,\n"
            "       0.5933  , 0.947   , 0.2383  , 0.4226  ], dtype=float16)")
        assert_equal(repr(y),
            "array([0.2918820979355541 , 0.5064172631089138 , 0.2848750619642916 ,\n"
            "       0.4342965294660567 , 0.7326538397312751 , 0.3459503329096204 ,\n"
            "       0.0862072768214508 , 0.39112753029631175])")
        assert_equal(repr(z),
            "array([0. , 0.1, 0.2, 0.3, 0.4, 0.5], dtype=float16)")
        assert_equal(repr(w),
            "array([1.e+00, 1.e+01, 1.e+02, 1.e+03, 1.e+04, 1.e+05, 1.e+06, 1.e+07,\n"
            "       1.e+08, 1.e+09, 1.e+10, 1.e+11, 1.e+12, 1.e+13, 1.e+14, 1.e+15,\n"
            "       1.e+16, 1.e+17, 1.e+18, 1.e+19, 1.e+20, 1.e+21, 1.e+22, 1.e+23,\n"
            "       1.e+24])")
        assert_equal(repr(wp), "array([1.234e+001, 1.000e+002, 1.000e+123])")

        # maxprec mode, precision=8
        np.set_printoptions(floatmode='maxprec', precision=8)
        assert_equal(repr(x),
            "array([0.6104  , 0.922   , 0.457   , 0.0906  , 0.3733  , 0.007244,\n"
            "       0.5933  , 0.947   , 0.2383  , 0.4226  ], dtype=float16)")
        assert_equal(repr(y),
            "array([0.2918821 , 0.50641726, 0.28487506, 0.43429653, 0.73265384,\n"
            "       0.34595033, 0.08620728, 0.39112753])")
        assert_equal(repr(z),
            "array([0. , 0.1, 0.2, 0.3, 0.4, 0.5], dtype=float16)")
        assert_equal(repr(w[::5]),
            "array([1.e+00, 1.e+05, 1.e+10, 1.e+15, 1.e+20])")
        assert_equal(repr(wp), "array([1.234e+001, 1.000e+002, 1.000e+123])")

        # fixed mode, precision=4
        np.set_printoptions(floatmode='fixed', precision=4)
        assert_equal(repr(x),
            "array([0.6104, 0.9219, 0.4570, 0.0906, 0.3733, 0.0072, 0.5933, 0.9468,\n"
            "       0.2383, 0.4226], dtype=float16)")
        assert_equal(repr(y),
            "array([0.2919, 0.5064, 0.2849, 0.4343, 0.7327, 0.3460, 0.0862, 0.3911])")
        assert_equal(repr(z),
            "array([0.0000, 0.1000, 0.2000, 0.3000, 0.3999, 0.5000], dtype=float16)")
        assert_equal(repr(w[::5]),
            "array([1.0000e+00, 1.0000e+05, 1.0000e+10, 1.0000e+15, 1.0000e+20])")
        assert_equal(repr(wp), "array([1.2340e+001, 1.0000e+002, 1.0000e+123])")
        # for larger precision, representation error becomes more apparent:
        np.set_printoptions(floatmode='fixed', precision=8)
        assert_equal(repr(z),
            "array([0.00000000, 0.09997559, 0.19995117, 0.30004883, 0.39990234,\n"
            "       0.50000000], dtype=float16)")

        # maxprec_equal  mode, precision=8
        np.set_printoptions(floatmode='maxprec_equal', precision=8)
        assert_equal(repr(x),
            "array([0.610352, 0.921875, 0.457031, 0.090576, 0.373291, 0.007244,\n"
            "       0.593262, 0.946777, 0.238281, 0.422607], dtype=float16)")
        assert_equal(repr(y),
            "array([0.29188210, 0.50641726, 0.28487506, 0.43429653, 0.73265384,\n"
            "       0.34595033, 0.08620728, 0.39112753])")
        assert_equal(repr(z),
            "array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=float16)")
        assert_equal(repr(w[::5]),
            "array([1.e+00, 1.e+05, 1.e+10, 1.e+15, 1.e+20])")
        assert_equal(repr(wp), "array([1.234e+001, 1.000e+002, 1.000e+123])")

def test_unicode_object_array():
    import sys
    if sys.version_info[0] >= 3:
        expected = "array(['é'], dtype=object)"
    else:
        expected = "array([u'\\xe9'], dtype=object)"
    x = np.array([u'\xe9'], dtype=object)
    assert_equal(repr(x), expected)


if __name__ == "__main__":
    run_module_suite()
