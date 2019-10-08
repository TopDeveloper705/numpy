============================================================
NEP 31 — Context-local and global overrides of the NumPy API
============================================================

:Author: Hameer Abbasi <habbasi@quansight.com>
:Author: Ralf Gommers <rgommers@quansight.com>
:Author: Peter Bell <pbell@quansight.com>
:Status: Draft
:Type: Standards Track
:Created: 2019-08-22


Abstract
--------

This NEP proposes to make all of NumPy's public API overridable via an
extensible backend mechanism.

Acceptance of this NEP means NumPy would provide global and context-local
overrides, as well as a dispatch mechanism similar to NEP-18 [2]_. First
experiences with ``__array_function__`` show that it is necessary to be able
to override NumPy functions that *do not take an array-like argument*, and
hence aren't overridable via ``__array_function__``. The most pressing need is
array creation and coercion functions, such as ``numpy.zeros`` or
``numpy.asarray``; see e.g. NEP-30 [9]_.

This NEP proposes to allow, in an opt-in fashion, overriding any part of the
NumPy API. It is intended as a comprehensive resolution to NEP-22 [3]_, and
obviates the need to add an ever-growing list of new protocols for each new
type of function or object that needs to become overridable.

Motivation and Scope
--------------------

The motivation behind ``uarray`` is manyfold: First, there have been several
attempts to allow dispatch of parts of the NumPy API, including (most
prominently), the ``__array_ufunc__`` protocol in NEP-13 [4]_, and the
``__array_function__`` protocol in NEP-18 [2]_, but this has shown the need
for further protocols to be developed, including a protocol for coercion (see
[5]_, [9]_). The reasons these overrides are needed have been extensively
discussed in the references, and this NEP will not attempt to go into the
details of why these are needed; but in short: It is necessary for library
authors to be able to coerce arbitrary objects into arrays of their own types,
such as CuPy needing to coerce to a CuPy array, for example, instead of
a NumPy array.

These kinds of overrides are useful for both the end-user as well as library
authors. End-users may have written or wish to write code that they then later
speed up or move to a different implementation, say PyData/Sparse. They can do
this simply by setting a backend. Library authors may also wish to write code
that is portable across array implementations, for example ``sklearn`` may wish
to write code for a machine learning algorithm that is portable across array
implementations while also using array creation functions.

This NEP takes a holistic approach: It assumes that there are parts of
the API that need to be overridable, and that these will grow over time. It
provides a general framework and a mechanism to avoid a design of a new
protocol each time this is required. This was the goal of ``uarray``: to
allow for overrides in an API without needing the design of a new protocol.

This NEP proposes the following: That ``unumpy`` [8]_  becomes the
recommended override mechanism for the parts of the NumPy API not yet covered
by ``__array_function__`` or ``__array_ufunc__``, and that ``uarray`` is
vendored into a new namespace within NumPy to give users and downstream
dependencies access to these overrides.  This vendoring mechanism is similar
to what SciPy decided to do for making ``scipy.fft`` overridable (see [10]_).


Detailed description
--------------------

Using overrides
~~~~~~~~~~~~~~~

The way we propose the overrides will be used by end users is::

    # On the library side
    import numpy.overridable as unp

    def library_function(array):
        array = unp.asarray(array)
        # Code using unumpy as usual
        return array

    # On the user side:
    import numpy.overridable as unp
    import uarray as ua
    import dask.array as da

    ua.register_backend(da)

    library_function(dask_array)  # works and returns dask_array

    with unp.set_backend(da):
        library_function([1, 2, 3, 4])  # actually returns a Dask array.


Here, ``backend`` can be any compatible object defined either by NumPy or an
external library, such as Dask or CuPy. Ideally, it should be the module
``dask.array`` or ``cupy`` itself.

Composing backends
~~~~~~~~~~~~~~~~~~

There are some backends which may depend on other backends, for example xarray
depending on `numpy.fft`, and transforming a time axis into a frequency axis,
or Dask/xarray holding an array other than a NumPy array inside it. This would
be handled in the following manner inside code::

    with ua.set_backend(cupy), ua.set_backend(dask.array):
        # Code that has distributed GPU arrays here

Proposals
~~~~~~~~~

The only change this NEP proposes at its acceptance, is to make ``unumpy`` the
officially recommended way to override NumPy. ``unumpy`` will remain a separate
repository/package (which we propose to vendor to avoid a hard dependency, and
use the separate ``unumpy`` package only if it is installed, rather than depend
on for the time being). In concrete terms, ``numpy.overridable`` becomes an
alias for ``unumpy``, if available with a fallback to the a vendored version if
not. ``uarray`` and ``unumpy`` and will be developed primarily with the input
of duck-array authors and secondarily, custom dtype authors, via the usual
GitHub workflow. There are a few reasons for this:

* Faster iteration in the case of bugs or issues.
* Faster design changes, in the case of needed functionality.
* ``unumpy`` will work with older versions of NumPy as well.
* The user and library author opt-in to the override process,
  rather than breakages happening when it is least expected.
  In simple terms, bugs in ``unumpy`` mean that ``numpy`` remains
  unaffected.
* For ``numpy.fft``, ``numpy.linalg`` and ``numpy.random``, the functions in
  the main namespace will mirror those in the ``numpy.overridable`` namespace.
  The reason for this is that there may exist functions in the in these
  submodules that need backends, even for ``numpy.ndarray`` inputs.

Advantanges of ``unumpy`` over other solutions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``unumpy`` offers a number of advantanges over the approach of defining a new
protocol for every problem encountered: Whenever there is something requiring
an override, ``unumpy`` will be able to offer a unified API with very minor
changes. For example:

* ``ufunc`` objects can be overridden via their ``__call__``, ``reduce`` and
  other methods.
* Other functions can be overridden in a similar fashion.
* ``np.asduckarray`` goes away, and becomes ``np.overridable.asarray`` with a
  backend set.
* The same holds for array creation functions such as ``np.zeros``,
  ``np.empty`` and so on.

This also holds for the future: Making something overridable would require only
minor changes to ``unumpy``.

Another promise ``unumpy`` holds is one of default implementations. Default
implementations can be provided for any multimethod, in terms of others. This
allows one to override a large part of the NumPy API by defining only a small
part of it. This is to ease the creation of new duck-arrays, by providing
default implementations of many functions that can be easily expressed in
terms of others, as well as a repository of utility functions that help in the
implementation of duck-arrays that most duck-arrays would require. This would
allow us to avoid designing entire protocols, e.g., a protocol for stacking
and concatenating would be replaced by simply implementing ``stack`` and/or
``concatenate`` and then providing default implementations for everything else
in that class. The same applies for transposing, and many other functions
which cannot even be concretely covered by protocols.

It also allows one to override functions in a manner which
``__array_function__`` simply cannot, such as overriding ``np.einsum`` with the
version from the ``opt_einsum`` package, or Intel MKL overriding FFT, BLAS
or ``ufunc`` objects. They would define a backend with the appropriate
multimethods, and the user would select them via a ``with`` statement, or
registering them as a backend.

The last benefit is a clear way to coerce to a given backend (via the
``coerce`` keyword in ``ua.set_backend``), and a protocol
for coercing not only arrays, but also ``dtype`` objects and ``ufunc`` objects
with similar ones from other libraries. This is due to the existence of actual,
third party dtype packages, and their desire to blend into the NumPy ecosystem
(see [6]_). This is a separate issue compared to the C-level dtype redesign
proposed in [7]_, it's about allowing third-party dtype implementations to
work with NumPy, much like third-party array implementations. These can provide
features such as, for example, units, jagged arrays or other such features that
are outside the scope of NumPy.

Mixing NumPy and ``unumpy`` in the same file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Normally, one would only want to import only one of ``unumpy`` or ``numpy``,
you would import it as ``np`` for familiarity. However, there may be situations
where one wishes to mix NumPy and the overrides, and there are a few ways to do
this, depending on the user's style::

    from numpy import overridable as unp
    import numpy as np

or::

    import numpy as np

    # Use unumpy via np.overridable

Duck-array coercion
~~~~~~~~~~~~~~~~~~~

There are inherent problems about returning objects that are not NumPy arrays
from ``numpy.array`` or ``numpy.asarray``, particularly in the context of C/C++
or Cython code that may get an object with a different memory layout than the
one it expects. However, we believe this problem may apply not only to these
two functions but all functions that return NumPy arrays. For this reason,
overrides are opt-in for the user, by using the submodule ``numpy.overridable``
rather than ``numpy``. NumPy will continue to work unaffected by anything in
``numpy.overridable``.

If the user wishes to obtain a NumPy array, there are two ways of doing it:

1. Use ``numpy.asarray`` (the non-overridable version).
2. Use ``numpy.overridable.asarray`` with the NumPy backend set and coercion
   enabled

Aliases outside of the ``numpy.overridable`` namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All functionality in ``numpy.random``, ``numpy.linalg`` and ``numpy.fft``
will be aliased to their respective overridable versions inside
``numpy.overridable``. The reason for this is that there are alternative
implementations of RNGs (``mkl-random``), linear algebra routines (``eigen``,
``blis``) and FFT routines (``mkl-fft``, ``pyFFTW``) that need to operate on
``numpy.ndarray`` inputs, but still need the ability to switch behaviour.

This is different from monkeypatching in a few different ways:

* The caller-facing signature of the function is always the same,
  so there is at least the loose sense of an API contract. Monkeypatching
  does not provide this ability.
* There is the ability of locally switching the backend.
* It has been `suggested <http://numpy-discussion.10968.n7.nabble.com/NEP-31-Context-local-and-global-overrides-of-the-NumPy-API-tp47452p47472.html>`_
  that the reason that 1.17 hasn't landed in the Anaconda defaults channel is
  due to the incompatibility between monkeypatching and `__array_function__`.

All this isn't possible at all with ``__array_function__`` or
``__array_ufunc__``.

It has been formally realised (at least in part) that a backend system is
needed for this, in the `NumPy roadmap <https://numpy.org/neps/roadmap.html#other-functionality>`_.

For ``numpy.random``, it's still necessary to make the C-API fit the one
proposed in `NEP-19 <https://numpy.org/neps/nep-0019-rng-policy.html>`_.
This is impossible for `mkl-random`, because then it would need to be
rewritten to fit that framework. The general guarantees on stream
compatibility will be the same as before: If there's a backend that affects
``numpy.random`` set, we make no guarantees about stream compatibility, and it
is up to the backend author to provide their own guarantees.

Providing a way for implicit dispatch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It has been suggested that the ability to dispatch methods which do not take
a dispatchable is needed, while guessing that backend from another dispatchable.

As a concrete example, consider the following:

.. code:: python

    with unumpy.determine_backend(array_like, np.ndarray):
        unumpy.arange(len(array_like))

While this does not exist yet in ``uarray``, it is trivial to add it. The
answer is to simply call ``__ua_convert__`` on the passed-in array with
``coerce=False`` for each backend, and comparing the result to
``NotImplemented``.

The need for an opt-in module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The need for an opt-in module is realised because of a few reasons:

* There are parts of the API (like `numpy.asarray`) that simply cannot be
  overridden due to incompatibility concerns with C/Cython extensions, however,
  one may want to coerce to a duck-array using ``asarray`` with a backend set.
* There are possible issues around an implicit option and monkeypatching.

NEP 18 notes that this may require maintenance of two separate APIs. However,
this burden may be lessened by, for example, parametrizing all tests over
``numpy.overridable`` separately via a fixture. This also has the side-effect
of thoroughly testing it, unlike ``__array_function__``. We also feel that it
provides an oppurtunity to separate the NumPy API contract properly from the
implementation.

Benefits to end-users and mixing backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mixing backends is easy in ``uarray``, one only has to do:

.. code:: python

    # Explicitly say which backends you want to mix
    ua.register_backend(backend1)
    ua.register_backend(backend2)
    ua.register_backend(backend3)

    # Freely use code that mixes backends here.

The benefits to end-users extend beyond just writing new code. Old code
(usually in the form of scripts) can be easily ported to different backends
by a simple import switch and a line adding the preferred backend. This way,
users may find it easier to port existing code to GPU or distributed computing.

Related Work
------------

Other override mechanisms
~~~~~~~~~~~~~~~~~~~~~~~~~

* NEP-18, the ``__array_function__`` protocol. [2]_
* NEP-13, the ``__array_ufunc__`` protocol. [3]_
* NEP-30, the ``__duck_array__`` protocol. [9]_

Existing NumPy-like array implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Dask: https://dask.org/
* CuPy: https://cupy.chainer.org/
* PyData/Sparse: https://sparse.pydata.org/
* Xnd: https://xnd.readthedocs.io/
* Astropy's Quantity: https://docs.astropy.org/en/stable/units/

Existing and potential consumers of alternative arrays
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Dask: https://dask.org/
* scikit-learn: https://scikit-learn.org/
* xarray: https://xarray.pydata.org/
* TensorLy: http://tensorly.org/

Existing alternate dtype implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``ndtypes``: https://ndtypes.readthedocs.io/en/latest/
* Datashape: https://datashape.readthedocs.io
* Plum: https://plum-py.readthedocs.io/

Alternate implementations of parts of the NumPy API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``mkl_random``: https://github.com/IntelPython/mkl_random
* ``mkl_fft``: https://github.com/IntelPython/mkl_fft
* ``bottleneck``: https://github.com/pydata/bottleneck
* ``opt_einsum``: https://github.com/dgasmith/opt_einsum

Implementation
--------------

The implementation of this NEP will require the following steps:

* Implementation of ``uarray`` multimethods corresponding to the
  NumPy API, including classes for overriding ``dtype``, ``ufunc``
  and ``array`` objects, in the ``unumpy`` repository.
* Moving backends from ``unumpy`` into the respective array libraries.

``uarray`` Primer
~~~~~~~~~~~~~~~~~

**Note:** *This section will not attempt to go into too much detail about
uarray, that is the purpose of the uarray documentation.* [1]_
*However, the NumPy community will have input into the design of
uarray, via the issue tracker.*

``unumpy`` is the interface that defines a set of overridable functions
(multimethods) compatible with the numpy API. To do this, it uses the
``uarray`` library. ``uarray`` is a general purpose tool for creating
multimethods that dispatch to one of multiple different possible backend
implementations. In this sense, it is similar to the ``__array_function__``
protocol but with the key difference that the backend is explicitly installed
by the end-user and not coupled into the array type.

Decoupling the backend from the array type gives much more flexibility to
end-users and backend authors. For example, it is possible to:

* override functions not taking arrays as arguments
* create backends out of source from the array type
* install multiple backends for the same array type

This decoupling also means that ``uarray`` is not constrained to dispatching
over array-like types. The backend is free to inspect the entire set of
function arguments to determine if it can implement the function e.g. ``dtype``
parameter dispatching.

Defining backends
^^^^^^^^^^^^^^^^^

``uarray`` consists of two main protocols: ``__ua_convert__`` and
``__ua_function__``, called in that order, along with ``__ua_domain__``.
``__ua_convert__`` is for conversion and coercion. It has the signature
``(dispatchables, coerce)``, where ``dispatchables`` is an iterable of
``ua.Dispatchable`` objects and ``coerce`` is a boolean indicating whether or
not to force the conversion. ``ua.Dispatchable`` is a simple class consisting
of three simple values: ``type``, ``value``, and ``coercible``.
``__ua_convert__`` returns an iterable of the converted values, or
``NotImplemented`` in the case of failure.

``__ua_function__`` has the signature ``(func, args, kwargs)`` and defines
the actual implementation of the function. It recieves the function and its
arguments. Returning ``NotImplemented`` will cause a move to the default
implementation of the function if one exists, and failing that, the next
backend.

Here is what will happen assuming a ``uarray`` multimethod is called:

1. We canonicalise the arguments so any arguments without a default
   are placed in ``*args`` and those with one are placed in ``**kwargs``.
2. We check the list of backends.

   a. If it is empty, we try the default implementation.

3. We check if the backend's ``__ua_convert__`` method exists. If it exists:

   a. We pass it the output of the dispatcher,
      which is an iterable of ``ua.Dispatchable`` objects.
   b. We feed this output, along with the arguments,
      to the argument replacer. ``NotImplemented`` means we move to 3
      with the next backend.
   c. We store the replaced arguments as the new arguments.

4. We feed the arguments into ``__ua_function__``, and return the output, and
   exit if it isn't ``NotImplemented``.
5. If the default implementation exists, we try it with the current backend.
6. On failure,  we move to 3 with the next backend. If there are no more
   backends, we move to 7.
7. We raise a ``ua.BackendNotImplementedError``.

Defining overridable multimethods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To define an overridable function (a multimethod), one needs a few things:

1. A dispatcher that returns an iterable of ``ua.Dispatchable`` objects.
2. A reverse dispatcher that replaces dispatchable values with the supplied
   ones.
3. A domain.
4. Optionally, a default implementation, which can be provided in terms of
   other multimethods.

As an example, consider the following::

    import uarray as ua

    def full_argreplacer(args, kwargs, dispatchables):
        def full(shape, fill_value, dtype=None, order='C'):
            return (shape, fill_value), dict(
                dtype=dispatchables[0],
                order=order
            )

        return full(*args, **kwargs)

    @ua.create_multimethod(full_argreplacer, domain="numpy")
    def full(shape, fill_value, dtype=None, order='C'):
        return (ua.Dispatchable(dtype, np.dtype),)

A large set of examples can be found in the ``unumpy`` repository, [8]_.
This simple act of overriding callables allows us to override:

* Methods
* Properties, via ``fget`` and ``fset``
* Entire objects, via ``__get__``.

Examples for NumPy
^^^^^^^^^^^^^^^^^^

A library that implements a NumPy-like API will use it in the following
manner (as an example)::

    import numpy.overridable as unp
    _ua_implementations = {}

    __ua_domain__ = "numpy"

    def __ua_function__(func, args, kwargs):
        fn = _ua_implementations.get(func, None)
        return fn(*args, **kwargs) if fn is not None else NotImplemented

    def implements(ua_func):
        def inner(func):
            _ua_implementations[ua_func] = func
            return func

        return inner

    @implements(unp.asarray)
    def asarray(a, dtype=None, order=None):
        # Code here
        # Either this method or __ua_convert__ must
        # return NotImplemented for unsupported types,
        # Or they shouldn't be marked as dispatchable.

    # Provides a default implementation for ones and zeros.
    @implements(unp.full)
    def full(shape, fill_value, dtype=None, order='C'):
        # Code here

Backward compatibility
----------------------

There are no backward incompatible changes proposed in this NEP.

Alternatives
------------

The current alternative to this problem is a combination of NEP-18 [2]_,
NEP-13 [4]_ and NEP-30 [9]_ plus adding more protocols (not yet specified)
in addition to it. Even then, some parts of the NumPy API will remain
non-overridable, so it's a partial alternative.

The main alternative to vendoring ``unumpy`` is to simply move it into NumPy
completely and not distribute it as a separate package. This would also achieve
the proposed goals, however we prefer to keep it a separate package for now,
for reasons already stated above.

The third alternative is to move ``unumpy`` into the NumPy organisation and
develop it as a NumPy project. This will also achieve the said goals, and is
also a possibility that can be considered by this NEP. However, the act of
doing an extra ``pip install`` or ``conda install`` may discourage some users
from adopting this method.

An alternative to requiring opt-in is mainly to *not* override ``np.asarray``
and ``np.array``, and making the rest of the NumPy API surface overridable,
instead providing ``np.duckarray`` and ``np.asduckarray``
as duck-array friendly alternatives that used the respective overrides. However,
this has the downside of adding a minor overhead to NumPy calls.

Discussion
----------

* ``uarray`` blogpost: https://labs.quansight.org/blog/2019/07/uarray-update-api-changes-overhead-and-comparison-to-__array_function__/
* The discussion section of NEP-18: https://numpy.org/neps/nep-0018-array-function-protocol.html#discussion
* NEP-22: https://numpy.org/neps/nep-0022-ndarray-duck-typing-overview.html
* Dask issue #4462: https://github.com/dask/dask/issues/4462
* PR #13046: https://github.com/numpy/numpy/pull/13046
* Dask issue #4883: https://github.com/dask/dask/issues/4883
* Issue #13831: https://github.com/numpy/numpy/issues/13831
* Discussion PR 1: https://github.com/hameerabbasi/numpy/pull/3
* Discussion PR 2: https://github.com/hameerabbasi/numpy/pull/4
* Discussion PR 3: https://github.com/numpy/numpy/pull/14389


References and Footnotes
------------------------

.. [1] uarray, A general dispatch mechanism for Python: https://uarray.readthedocs.io

.. [2] NEP 18 — A dispatch mechanism for NumPy’s high level array functions: https://numpy.org/neps/nep-0018-array-function-protocol.html

.. [3] NEP 22 — Duck typing for NumPy arrays – high level overview: https://numpy.org/neps/nep-0022-ndarray-duck-typing-overview.html

.. [4] NEP 13 — A Mechanism for Overriding Ufuncs: https://numpy.org/neps/nep-0013-ufunc-overrides.html

.. [5] Reply to Adding to the non-dispatched implementation of NumPy methods: http://numpy-discussion.10968.n7.nabble.com/Adding-to-the-non-dispatched-implementation-of-NumPy-methods-tp46816p46874.html

.. [6] Custom Dtype/Units discussion: http://numpy-discussion.10968.n7.nabble.com/Custom-Dtype-Units-discussion-td43262.html

.. [7] The epic dtype cleanup plan: https://github.com/numpy/numpy/issues/2899

.. [8] unumpy: NumPy, but implementation-independent: https://unumpy.readthedocs.io

.. [9] NEP 30 — Duck Typing for NumPy Arrays - Implementation: https://www.numpy.org/neps/nep-0030-duck-array-protocol.html

.. [10] http://scipy.github.io/devdocs/fft.html#backend-control


Copyright
---------

This document has been placed in the public domain.
