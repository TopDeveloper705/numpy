from __future__ import division, absolute_import, print_function

__all__ = ['atleast_1d', 'atleast_2d', 'atleast_3d', 'block', 'hstack',
           'stack', 'vstack']


from . import numeric as _nx
from .numeric import array, asanyarray, newaxis
from .multiarray import normalize_axis_index

def atleast_1d(*arys):
    """
    Convert inputs to arrays with at least one dimension.

    Scalar inputs are converted to 1-dimensional arrays, whilst
    higher-dimensional inputs are preserved.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more input arrays.

    Returns
    -------
    ret : ndarray
        An array, or list of arrays, each with ``a.ndim >= 1``.
        Copies are made only if necessary.

    See Also
    --------
    atleast_2d, atleast_3d

    Examples
    --------
    >>> np.atleast_1d(1.0)
    array([ 1.])

    >>> x = np.arange(9.0).reshape(3,3)
    >>> np.atleast_1d(x)
    array([[ 0.,  1.,  2.],
           [ 3.,  4.,  5.],
           [ 6.,  7.,  8.]])
    >>> np.atleast_1d(x) is x
    True

    >>> np.atleast_1d(1, [3, 4])
    [array([1]), array([3, 4])]

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if ary.ndim == 0:
            result = ary.reshape(1)
        else:
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return res

def atleast_2d(*arys):
    """
    View inputs as arrays with at least two dimensions.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more array-like sequences.  Non-array inputs are converted
        to arrays.  Arrays that already have two or more dimensions are
        preserved.

    Returns
    -------
    res, res2, ... : ndarray
        An array, or list of arrays, each with ``a.ndim >= 2``.
        Copies are avoided where possible, and views with two or more
        dimensions are returned.

    See Also
    --------
    atleast_1d, atleast_3d

    Examples
    --------
    >>> np.atleast_2d(3.0)
    array([[ 3.]])

    >>> x = np.arange(3.0)
    >>> np.atleast_2d(x)
    array([[ 0.,  1.,  2.]])
    >>> np.atleast_2d(x).base is x
    True

    >>> np.atleast_2d(1, [1, 2], [[1, 2]])
    [array([[1]]), array([[1, 2]]), array([[1, 2]])]

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if ary.ndim == 0:
            result = ary.reshape(1, 1)
        elif ary.ndim == 1:
            result = ary[newaxis,:]
        else:
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return res

def atleast_3d(*arys):
    """
    View inputs as arrays with at least three dimensions.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more array-like sequences.  Non-array inputs are converted to
        arrays.  Arrays that already have three or more dimensions are
        preserved.

    Returns
    -------
    res1, res2, ... : ndarray
        An array, or list of arrays, each with ``a.ndim >= 3``.  Copies are
        avoided where possible, and views with three or more dimensions are
        returned.  For example, a 1-D array of shape ``(N,)`` becomes a view
        of shape ``(1, N, 1)``, and a 2-D array of shape ``(M, N)`` becomes a
        view of shape ``(M, N, 1)``.

    See Also
    --------
    atleast_1d, atleast_2d

    Examples
    --------
    >>> np.atleast_3d(3.0)
    array([[[ 3.]]])

    >>> x = np.arange(3.0)
    >>> np.atleast_3d(x).shape
    (1, 3, 1)

    >>> x = np.arange(12.0).reshape(4,3)
    >>> np.atleast_3d(x).shape
    (4, 3, 1)
    >>> np.atleast_3d(x).base is x.base  # x is a reshape, so not base itself
    True

    >>> for arr in np.atleast_3d([1, 2], [[1, 2]], [[[1, 2]]]):
    ...     print(arr, arr.shape)
    ...
    [[[1]
      [2]]] (1, 2, 1)
    [[[1]
      [2]]] (1, 2, 1)
    [[[1 2]]] (1, 1, 2)

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if ary.ndim == 0:
            result = ary.reshape(1, 1, 1)
        elif ary.ndim == 1:
            result = ary[newaxis,:, newaxis]
        elif ary.ndim == 2:
            result = ary[:,:, newaxis]
        else:
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return res


def vstack(tup):
    """
    Stack arrays in sequence vertically (row wise).

    Take a sequence of arrays and stack them vertically to make a single
    array. Rebuild arrays divided by `vsplit`.

    This function continues to be supported for backward compatibility, but
    you should prefer ``np.concatenate`` or ``np.stack``. The ``np.stack``
    function was added in NumPy 1.10.

    Parameters
    ----------
    tup : sequence of ndarrays
        Tuple containing arrays to be stacked. The arrays must have the same
        shape along all but the first axis.

    Returns
    -------
    stacked : ndarray
        The array formed by stacking the given arrays.

    See Also
    --------
    stack : Join a sequence of arrays along a new axis.
    hstack : Stack arrays in sequence horizontally (column wise).
    dstack : Stack arrays in sequence depth wise (along third dimension).
    concatenate : Join a sequence of arrays along an existing axis.
    vsplit : Split array into a list of multiple sub-arrays vertically.
    block : Assemble arrays from blocks.

    Notes
    -----
    Equivalent to ``np.concatenate(tup, axis=0)`` if `tup` contains arrays that
    are at least 2-dimensional.

    Examples
    --------
    >>> a = np.array([1, 2, 3])
    >>> b = np.array([2, 3, 4])
    >>> np.vstack((a,b))
    array([[1, 2, 3],
           [2, 3, 4]])

    >>> a = np.array([[1], [2], [3]])
    >>> b = np.array([[2], [3], [4]])
    >>> np.vstack((a,b))
    array([[1],
           [2],
           [3],
           [2],
           [3],
           [4]])

    """
    return _nx.concatenate([atleast_2d(_m) for _m in tup], 0)

def hstack(tup):
    """
    Stack arrays in sequence horizontally (column wise).

    Take a sequence of arrays and stack them horizontally to make
    a single array. Rebuild arrays divided by `hsplit`.

    This function continues to be supported for backward compatibility, but
    you should prefer ``np.concatenate`` or ``np.stack``. The ``np.stack``
    function was added in NumPy 1.10.

    Parameters
    ----------
    tup : sequence of ndarrays
        All arrays must have the same shape along all but the second axis.

    Returns
    -------
    stacked : ndarray
        The array formed by stacking the given arrays.

    See Also
    --------
    stack : Join a sequence of arrays along a new axis.
    vstack : Stack arrays in sequence vertically (row wise).
    dstack : Stack arrays in sequence depth wise (along third axis).
    concatenate : Join a sequence of arrays along an existing axis.
    hsplit : Split array along second axis.
    block : Assemble arrays from blocks.

    Notes
    -----
    Equivalent to ``np.concatenate(tup, axis=1)`` if `tup` contains arrays that
    are at least 2-dimensional.

    Examples
    --------
    >>> a = np.array((1,2,3))
    >>> b = np.array((2,3,4))
    >>> np.hstack((a,b))
    array([1, 2, 3, 2, 3, 4])
    >>> a = np.array([[1],[2],[3]])
    >>> b = np.array([[2],[3],[4]])
    >>> np.hstack((a,b))
    array([[1, 2],
           [2, 3],
           [3, 4]])

    """
    arrs = [atleast_1d(_m) for _m in tup]
    # As a special case, dimension 0 of 1-dimensional arrays is "horizontal"
    if arrs and arrs[0].ndim == 1:
        return _nx.concatenate(arrs, 0)
    else:
        return _nx.concatenate(arrs, 1)


def stack(arrays, axis=0):
    """
    Join a sequence of arrays along a new axis.

    The `axis` parameter specifies the index of the new axis in the dimensions
    of the result. For example, if ``axis=0`` it will be the first dimension
    and if ``axis=-1`` it will be the last dimension.

    .. versionadded:: 1.10.0

    Parameters
    ----------
    arrays : sequence of array_like
        Each array must have the same shape.
    axis : int, optional
        The axis in the result array along which the input arrays are stacked.

    Returns
    -------
    stacked : ndarray
        The stacked array has one more dimension than the input arrays.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    split : Split array into a list of multiple sub-arrays of equal size.
    block : Assemble arrays from blocks.

    Examples
    --------
    >>> arrays = [np.random.randn(3, 4) for _ in range(10)]
    >>> np.stack(arrays, axis=0).shape
    (10, 3, 4)

    >>> np.stack(arrays, axis=1).shape
    (3, 10, 4)

    >>> np.stack(arrays, axis=2).shape
    (3, 4, 10)

    >>> a = np.array([1, 2, 3])
    >>> b = np.array([2, 3, 4])
    >>> np.stack((a, b))
    array([[1, 2, 3],
           [2, 3, 4]])

    >>> np.stack((a, b), axis=-1)
    array([[1, 2],
           [2, 3],
           [3, 4]])

    """
    arrays = [asanyarray(arr) for arr in arrays]
    if not arrays:
        raise ValueError('need at least one array to stack')

    shapes = set(arr.shape for arr in arrays)
    if len(shapes) != 1:
        raise ValueError('all input arrays must have the same shape')

    result_ndim = arrays[0].ndim + 1
    axis = normalize_axis_index(axis, result_ndim)

    sl = (slice(None),) * axis + (_nx.newaxis,)
    expanded_arrays = [arr[sl] for arr in arrays]
    return _nx.concatenate(expanded_arrays, axis=axis)


def block(arrays):
    """
    Assemble an array from nested lists of blocks.

    You can create a 2-D blocked array with the same notation you use for
    `np.array`.

    Parameters
    ----------
    arrays : nested list/tuple of ndarrays or scalars
        lists and tuples are treated as sequence, everything else is treated
        as an element to concatenate.

        Inputs are normalized to have uniform depth by wrapping elements in
        extra layers of lists - for instance:
        * ``[[[a, b], c], d]`` is normalized to ``[[[a, b], [c]], [[d]]]``
        * ``[[[a]], b]`` is normalized to ``[[[a]], [[b]]]``

        After the above normalization, the innermost lists are `concatenate`d
        along the last dimension, the second-innermost along the second-last
        dimensions, etc.

    Returns
    -------
    blocked : ndarray
        The array assembled from the given blocks.
        The dimensionality of the output is determined by the dimensionality of
        all the inputs, and the degree to which the input list is nested -
        whichever is greatest.

    See Also
    --------
    concatenate : Join a sequence of arrays together.
    stack : Stack arrays in sequence along a new dimension.
    hstack : Stack arrays in sequence horizontally (column wise).
    vstack : Stack arrays in sequence vertically (row wise).
    dstack : Stack arrays in sequence depth wise (along third dimension).
    vsplit : Split array into a list of multiple sub-arrays vertically.

    Notes
    -----
    ``block`` is similar to Matlab's "square bracket stacking": ``[A A; B B]``

    Examples
    --------
    Stacking scalars in a row:
    >>> block([1, 2, 3])
    array([1, 2, 3])

    Stacking scalars with 1d arrays:
    >>> a = np.array([2, 3])
    >>> block([1, a])
    np.array([1, 2, 3])

    Stacking 1d arrays in a row:
    >>> A = np.array([1, 2, 3])
    >>> B = np.array([2, 3, 4])
    >>> block([A, B])
    array([1, 2, 3, 2, 3, 4])

    Stacking 2d row-vectors in a row:
    >>> A = np.array([[1, 2, 3]])
    >>> B = np.array([[2, 3, 4]])
    >>> block([A, B])
    array([[1, 2, 3, 2, 3, 4]])

    Stacking 1d arrays in a column:
    >>> a = np.array([1, 1])
    >>> b = np.array([2, 2])
    >>> block([[a], [b]])
    array([[1, 1],
           [2, 2]])

    Stacking 2d row-vectors in a column:
    >>> A = np.array([[1, 2, 3]])
    >>> B = np.array([[2, 3, 4]])
    >>> block([[A], [B]])
    array([[1, 2, 3],
           [2, 3, 4]])

    The tuple notation also works:
    >>> A = np.ones((2, 2))
    >>> B = 2 * A
    >>> block((A, B))
    array([[1, 1, 2, 2],
           [1, 1, 2, 2]])

    Block array with arbitrary shaped elements
    >>> one = np.array([[1, 1, 1]])
    >>> two = np.array([[2, 2, 2]])
    >>> three = np.array([[3, 3, 3, 3, 3, 3]])
    >>> four = np.array([4, 4, 4, 4, 4, 4])
    >>> six = np.array([6, 6, 6, 6, 6])
    >>> zeros = np.zeros((2, 6), dtype=int)
    >>> block([[one,  two],
    ...        [three    ],
    ...        [four     ],
    ...        [5,    six],
    ...        [zeros    ])
    array([[1, 1, 1, 2, 2, 2],
           [3, 3, 3, 3, 3, 3],
           [4, 4, 4, 4, 4, 4],
           [5, 6, 6, 6, 6, 6],
           [0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0]])

    """

    def is_element(x):
        return not isinstance(x, (list, tuple))

    def recursive_map(x, base, aggregate=list):
        """
        Iterate over the nested list, applying `base` to items, and `aggregate`
        to iterables of mapped items
        """
        def f(x):
            if is_element(x):
                return base(x)
            else:
                return aggregate(f(xi) for xi in x)
        return f(x)

    def exactly_nd(x, ndim):
        x = asanyarray(x)
        shape = [1] * ndim
        shape[ndim-x.ndim:] = x.shape
        return x.reshape(shape)

    def max_or_0(xs):
        """ Like max, but returns 0 on an empty iterable """
        xs = list(xs)
        return max(xs) if xs else 0

    # convert all the arrays to ndarrays
    arrays = recursive_map(arrays, base=asanyarray)

    # determine the final number of dimensions
    list_ndim = recursive_map(arrays, base=lambda x: 0,
                                 aggregate=lambda xs: max_or_0(xs) + 1)
    elem_ndim = recursive_map(arrays, base=lambda x: x.ndim, aggregate=max_or_0)
    ndim = max(list_ndim, elem_ndim)

    # Make all the elements the same dimension
    arrays = recursive_map(arrays, base=lambda x: exactly_nd(x, ndim))

    # concate
    def _concatenate_recursive(x, axis):
        if is_element(x):
            return x
        else:
            return _nx.concatenate([
                _concatenate_recursive(xi, axis=axis+1)
                for xi in x
            ], axis=axis)

    return _concatenate_recursive(arrays, -list_ndim)