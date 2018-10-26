from __future__ import division, absolute_import, print_function

import sys

import numpy as np
from numpy.testing import (
    assert_, assert_equal, assert_raises, assert_raises_regex)
from numpy.core.overrides import (
    get_overloaded_types_and_args, array_function_dispatch,
    verify_matching_signatures)
from numpy.core.numeric import pickle


def _get_overloaded_args(relevant_args):
    types, args = get_overloaded_types_and_args(relevant_args)
    return args


def _return_not_implemented(self, *args, **kwargs):
    return NotImplemented


class TestGetOverloadedTypesAndArgs(object):

    def test_ndarray(self):
        array = np.array(1)

        types, args = get_overloaded_types_and_args([array])
        assert_equal(set(types), {np.ndarray})
        assert_equal(list(args), [])

        types, args = get_overloaded_types_and_args([array, array])
        assert_equal(len(types), 1)
        assert_equal(set(types), {np.ndarray})
        assert_equal(list(args), [])

        types, args = get_overloaded_types_and_args([array, 1])
        assert_equal(set(types), {np.ndarray})
        assert_equal(list(args), [])

        types, args = get_overloaded_types_and_args([1, array])
        assert_equal(set(types), {np.ndarray})
        assert_equal(list(args), [])

    def test_ndarray_subclasses(self):

        class OverrideSub(np.ndarray):
            __array_function__ = _return_not_implemented

        class NoOverrideSub(np.ndarray):
            pass

        array = np.array(1).view(np.ndarray)
        override_sub = np.array(1).view(OverrideSub)
        no_override_sub = np.array(1).view(NoOverrideSub)

        types, args = get_overloaded_types_and_args([array, override_sub])
        assert_equal(set(types), {np.ndarray, OverrideSub})
        assert_equal(list(args), [override_sub])

        types, args = get_overloaded_types_and_args([array, no_override_sub])
        assert_equal(set(types), {np.ndarray, NoOverrideSub})
        assert_equal(list(args), [])

        types, args = get_overloaded_types_and_args(
            [override_sub, no_override_sub])
        assert_equal(set(types), {OverrideSub, NoOverrideSub})
        assert_equal(list(args), [override_sub])

    def test_ndarray_and_duck_array(self):

        class Other(object):
            __array_function__ = _return_not_implemented

        array = np.array(1)
        other = Other()

        types, args = get_overloaded_types_and_args([other, array])
        assert_equal(set(types), {np.ndarray, Other})
        assert_equal(list(args), [other])

        types, args = get_overloaded_types_and_args([array, other])
        assert_equal(set(types), {np.ndarray, Other})
        assert_equal(list(args), [other])

    def test_ndarray_subclass_and_duck_array(self):

        class OverrideSub(np.ndarray):
            __array_function__ = _return_not_implemented

        class Other(object):
            __array_function__ = _return_not_implemented

        array = np.array(1)
        subarray = np.array(1).view(OverrideSub)
        other = Other()

        assert_equal(_get_overloaded_args([array, subarray, other]),
                     [subarray, other])
        assert_equal(_get_overloaded_args([array, other, subarray]),
                     [subarray, other])

    def test_many_duck_arrays(self):

        class A(object):
            __array_function__ = _return_not_implemented

        class B(A):
            __array_function__ = _return_not_implemented

        class C(A):
            __array_function__ = _return_not_implemented

        class D(object):
            __array_function__ = _return_not_implemented

        a = A()
        b = B()
        c = C()
        d = D()

        assert_equal(_get_overloaded_args([1]), [])
        assert_equal(_get_overloaded_args([a]), [a])
        assert_equal(_get_overloaded_args([a, 1]), [a])
        assert_equal(_get_overloaded_args([a, a, a]), [a])
        assert_equal(_get_overloaded_args([a, d, a]), [a, d])
        assert_equal(_get_overloaded_args([a, b]), [b, a])
        assert_equal(_get_overloaded_args([b, a]), [b, a])
        assert_equal(_get_overloaded_args([a, b, c]), [b, c, a])
        assert_equal(_get_overloaded_args([a, c, b]), [c, b, a])


class TestNDArrayArrayFunction(object):

    def test_method(self):

        class SubOverride(np.ndarray):
            __array_function__ = _return_not_implemented

        class NoOverrideSub(np.ndarray):
            pass

        array = np.array(1)

        def func():
            return 'original'

        result = array.__array_function__(
            func=func, types=(np.ndarray,), args=(), kwargs={})
        assert_equal(result, 'original')

        result = array.__array_function__(
            func=func, types=(np.ndarray, SubOverride), args=(), kwargs={})
        assert_(result is NotImplemented)

        result = array.__array_function__(
            func=func, types=(np.ndarray, NoOverrideSub), args=(), kwargs={})
        assert_equal(result, 'original')


# need to define this at the top level to test pickling
@array_function_dispatch(lambda array: (array,))
def dispatched_one_arg(array):
    """Docstring."""
    return 'original'


class TestArrayFunctionDispatch(object):

    def test_pickle(self):
        for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
            roundtripped = pickle.loads(
                    pickle.dumps(dispatched_one_arg, protocol=proto))
            assert_(roundtripped is dispatched_one_arg)

    def test_name_and_docstring(self):
        assert_equal(dispatched_one_arg.__name__, 'dispatched_one_arg')
        if sys.flags.optimize < 2:
            assert_equal(dispatched_one_arg.__doc__, 'Docstring.')

    def test_interface(self):

        class MyArray(object):
            def __array_function__(self, func, types, args, kwargs):
                return (self, func, types, args, kwargs)

        original = MyArray()
        (obj, func, types, args, kwargs) = dispatched_one_arg(original)
        assert_(obj is original)
        assert_(func is dispatched_one_arg)
        assert_equal(set(types), {MyArray})
        # assert_equal uses the overloaded np.iscomplexobj() internally
        assert_(args == (original,))
        assert_equal(kwargs, {})

    def test_not_implemented(self):

        class MyArray(object):
            def __array_function__(self, func, types, args, kwargs):
                return NotImplemented

        array = MyArray()
        with assert_raises_regex(TypeError, 'no implementation found'):
            dispatched_one_arg(array)


class TestVerifyMatchingSignatures(object):

    def test_verify_matching_signatures(self):

        verify_matching_signatures(lambda x: 0, lambda x: 0)
        verify_matching_signatures(lambda x=None: 0, lambda x=None: 0)
        verify_matching_signatures(lambda x=1: 0, lambda x=None: 0)

        with assert_raises(RuntimeError):
            verify_matching_signatures(lambda a: 0, lambda b: 0)
        with assert_raises(RuntimeError):
            verify_matching_signatures(lambda x: 0, lambda x=None: 0)
        with assert_raises(RuntimeError):
            verify_matching_signatures(lambda x=None: 0, lambda y=None: 0)
        with assert_raises(RuntimeError):
            verify_matching_signatures(lambda x=1: 0, lambda y=1: 0)

    def test_array_function_dispatch(self):

        with assert_raises(RuntimeError):
            @array_function_dispatch(lambda x: (x,))
            def f(y):
                pass

        # should not raise
        @array_function_dispatch(lambda x: (x,), verify=False)
        def f(y):
            pass


def _new_duck_type_and_implements():
    """Create a duck array type and implements functions."""
    HANDLED_FUNCTIONS = {}

    class MyArray(object):
        def __array_function__(self, func, types, args, kwargs):
            if func not in HANDLED_FUNCTIONS:
                return NotImplemented
            if not all(issubclass(t, MyArray) for t in types):
                return NotImplemented
            return HANDLED_FUNCTIONS[func](*args, **kwargs)

    def implements(numpy_function):
        """Register an __array_function__ implementations."""
        def decorator(func):
            HANDLED_FUNCTIONS[numpy_function] = func
            return func
        return decorator

    return (MyArray, implements)


class TestArrayFunctionImplementation(object):

    def test_one_arg(self):
        MyArray, implements = _new_duck_type_and_implements()

        @implements(dispatched_one_arg)
        def _(array):
            return 'myarray'

        assert_equal(dispatched_one_arg(1), 'original')
        assert_equal(dispatched_one_arg(MyArray()), 'myarray')

    def test_optional_args(self):
        MyArray, implements = _new_duck_type_and_implements()

        @array_function_dispatch(lambda array, option=None: (array,))
        def func_with_option(array, option='default'):
            return option

        @implements(func_with_option)
        def my_array_func_with_option(array, new_option='myarray'):
            return new_option

        # we don't need to implement every option on __array_function__
        # implementations
        assert_equal(func_with_option(1), 'default')
        assert_equal(func_with_option(1, option='extra'), 'extra')
        assert_equal(func_with_option(MyArray()), 'myarray')
        with assert_raises(TypeError):
            func_with_option(MyArray(), option='extra')

        # but new options on implementations can't be used
        result = my_array_func_with_option(MyArray(), new_option='yes')
        assert_equal(result, 'yes')
        with assert_raises(TypeError):
            func_with_option(MyArray(), new_option='no')

    def test_not_implemented(self):
        MyArray, implements = _new_duck_type_and_implements()

        @array_function_dispatch(lambda array: (array,), module='my')
        def func(array):
            return array

        array = np.array(1)
        assert_(func(array) is array)

        with assert_raises_regex(
                TypeError, "no implementation found for 'my.func'"):
            func(MyArray())


class TestNDArrayMethods(object):

    def test_repr(self):
        # gh-12162: should still be defined even if __array_function__ doesn't
        # implement np.array_repr()

        class MyArray(np.ndarray):
            def __array_function__(*args, **kwargs):
                return NotImplemented

        array = np.array(1).view(MyArray)
        assert_equal(repr(array), 'MyArray(1)')
        assert_equal(str(array), '1')

        
class TestNumPyFunctions(object):

    def test_module(self):
        assert_equal(np.sum.__module__, 'numpy')
        assert_equal(np.char.equal.__module__, 'numpy.char')
        assert_equal(np.fft.fft.__module__, 'numpy.fft')
        assert_equal(np.linalg.solve.__module__, 'numpy.linalg')

    def test_override_sum(self):
        MyArray, implements = _new_duck_type_and_implements()

        @implements(np.sum)
        def _(array):
            return 'yes'

        assert_equal(np.sum(MyArray()), 'yes')
