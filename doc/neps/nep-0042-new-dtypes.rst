.. _NEP42:

==============================================================================
NEP 42 — User-extensible dtypes
==============================================================================

:title: User-extensible dtypes
:Author: Sebastian Berg
:Author: Ben Nathanson
:Author: Marten van Kerkwijk
:Status: Draft
:Type: Standard
:Created: 2019-07-17


.. note::

    This NEP is third in a series:

    - :ref:`NEP 40 <NEP40>` explains the shortcomings of NumPy's dtype implementation.

    - :ref:`NEP 41 <NEP41>` gives an overview of our proposed replacement.

    - NEP 42 (this document) describes the new design's datatype-related APIs.

    - NEP 43 describes the new design's API for universal functions.


******************************************************************************
Abstract
******************************************************************************

NumPy's dtype architecture is monolithic, built around a single class that
handles each dtype as an instance. There's no principled way to expand it to
new dtypes, and the code is difficult to read and maintain.

As NEP 41 explains, we are proposing a new architecture that is modular and
open to user additions. dtypes will derive from a new ``DType`` class serving
as the extension point for new types. ``np.dtype("float64")`` will return an
instance of a ``Float64`` class, a subclass of root class ``np.dtype``.

This NEP is one of two that lay out the design and API of this new
architecture. This NEP addresses dtype implementation; NEP 43 addresses
universal functions.

.. note::

    Details of the private and external APIs may change to reflect user
    comments and implementation constraints. The underlying principles and
    choices should not change significantly.


******************************************************************************
Motivation and scope
******************************************************************************

Our goal is to allow user code to create fully featured dtypes for a broad
variety of uses, from physical units (such as meters) to domain-specific
representations of geometric objects. NEP 41 describes a number of these new
dtypes and their benefits.

Any design supporting dtypes must consider:

- How shape and dtype are determined when an array is created
- How array elements are stored and accessed
- The rules for casting dtypes to other dtypes

In addition:

- We want dtypes to comprise a class hierarchy open to new types and to
  subhierarchies, as motivated in :ref:`NEP 41 <NEP41>`.

And to provide this,

- We need to define a user API.

All these are the subjects of this NEP.

- The class hierarchy, its relation to the Python scalar types, and its
  important attributes are described in `DType class`_.

- The functionality that will support dtype casting is described in `Casting`_.

- The implementation of item access and storage, and the way shape and dtype
  are determined when creating an array, are described in `Array coercion`_.

- The functionality for users to define their own DTypes is described in
  `Public C-API`_.

The API here and in NEP 43 is entirely on the C side. A Python-side version
will be proposed in a future NEP.
A future Python API is expected to be similar, but provide a more convenient
API to reuse the functionality of existing DTypes.
It could also provide shorthands to create structured DTypes similar to python's
`dataclasses <https://docs.python.org/3.8/library/dataclasses.html>`_.


******************************************************************************
Backward compatibility
******************************************************************************

The disruption is expected to be no greater than that of a typical NumPy
release.

- The main issues are noted in :ref:`NEP 41 <NEP41>` and will mostly affect
  heavy users of the NumPy C-API.

- Eventually we will want to deprecate the API currently used for creating
  user-defined dtypes.

- Small, rarely noticed inconsistencies are likely to change. Examples:

  - ``np.array(np.nan, dtype=np.int64)`` behaves differently from
    ``np.array([np.nan], dtype=np.int64)`` with the latter raising an error.
    This may require identical results (either both error or both succeed).
  - ``np.array([array_like])`` sometimes behaves differently from
    ``np.array([np.array(array_like)])``
  - array operations may or may not preserve dtype metadata

The new code must pass NumPy's regular test suite, giving some assurance that
the changes are compatible with existing code.

******************************************************************************
Usage and impact
******************************************************************************

We believe the few structures in this section are sufficient to consolidate
NumPy's present functionality and also to support complex user-defined DTypes.

The rest of the NEP fills in details and provides support for the claim.

Again, though Python is used for illustration, the implementation is a C API only; a
future NEP will tackle the Python API.

After implementing this NEP, creating a DType will be possible by implementing
the following outlined DType base class,
that is further described in `DType class`_:

.. code-block:: python
    :dedent: 0

    class DType(np.dtype):
        type : type        # Python scalar type
        parametric : bool  # (may be indicated by superclass)

        @property
        def canonical(self) -> bool:
            raise NotImplementedError

        def ensure_canonical(self : DType) -> DType:
            raise NotImplementedError

For casting, a large part of the functionality is provided by the "methods" stored
in ``_castingimpl``

.. code-block:: python
    :dedent: 0

        @classmethod
        def common_dtype(cls : DTypeMeta, other : DTypeMeta) -> DTypeMeta:
            raise NotImplementedError

        def common_instance(self : DType, other : DType) -> DType:
            raise NotImplementedError

        # A mapping of "methods" each detailing how to cast to another DType
        # (further specified at the end of the section)
        _castingimpl = {}

For array-coercion, also part of casting:

.. code-block:: python
    :dedent: 0

        def __dtype_setitem__(self, item_pointer, value):
            raise NotImplementedError

        def __dtype_getitem__(self, item_pointer, base_obj) -> object:
            raise NotImplementedError

        @classmethod
        def __discover_descr_from_pyobject__(cls, obj : object) -> DType:
            raise NotImplementedError

        # initially private:
        @classmethod
        def _known_scalar_type(cls, obj : object) -> bool:
            raise NotImplementedError


Other elements of the casting implementation is the ``CastingImpl``:

.. code-block:: python
    :dedent: 0

    casting = Union["safe", "same_kind", "unsafe"]

    class CastingImpl:
        # Object describing and performing the cast
        casting : casting

        def resolve_descriptors(self, Tuple[DType] : input) -> (casting, Tuple[DType]):
            raise NotImplementedError

        # initially private:
        def _get_loop(...) -> lowlevel_C_loop:
            raise NotImplementedError

which describes the casting from one DType to another.
In NEP 43 this ``CastingImpl`` object is used unchanged to support
universal functions.


******************************************************************************
Definitions
******************************************************************************
.. glossary::

   dtype
      The dtype *instance*; this is the object attached to a numpy array.

   DType
      Any subclass of the base type ``np.dtype``.

   coercion
      Conversion of Python types to NumPy arrays and values stored in a NumPy
      array.

   cast
      Conversion of an array to a different dtype.

   promotion
      Finding a dtype that can perform an operation on a mix of dtypes without
      loss of information.

   safe cast
      A cast is safe if no information is lost when changing type.

On the C level we use ``descriptor`` or ``descr`` to mean
*dtype instance*. In the proposed C-API, these terms will distinguish
dtype instances from DType classes.

.. note::
   Perhaps confusingly, NumPy already has a class hierarchy for numeric types, as
   seen :ref:`in the figure <nep-0040_dtype-hierarchy>` of NEP 40, and the new
   DType hierarchy will resemble it. But the existing hierarchy is for scalar
   types, not DTypes, and its existence is largely irrelevant here, as NEP 40 and
   41 explain.

.. _DType class:

******************************************************************************
The DType class
******************************************************************************

This section reviews the structure underlying the proposed DType class,
including the type hierarchy and the use of abstract DTypes.

Class getter
==============================================================================

To create a dtype instance from a scalar type users now call ``np.dtype`` (for
instance, ``np.dtype(np.int64)``).

To get the DType of a scalar type, we propose this getter syntax::

    np.dtype[np.int64]

The notation works equally well with built-in and user-defined DTypes
and is inspired by and potentially useful for type hinting.

This getter eliminates the need to create an explicit name for every
DType, crowding the ``np`` namespace; the getter itself signifies the type.

Since getter calls won't be needed often, this is unlikely to be burdensome.
Classes can also offer concise alternatives.

The initial implementation probably will return only concrete (not abstract)
DTypes.

*This item is still under review.*


Hierarchy and abstract classes
==============================================================================

We will use abstract classes as building blocks of our extensible DType class
hierarchy.

1. Abstract classes are inherited cleanly, in principle allowing checks like
   ``isinstance(np.dtype("float64"), np.inexact)``.

2. Abstract classes allow a single piece of code to handle a multiplicity of
   input types. Code written to accept Complex objects can work with numbers
   of any precision; the precision of the results is determined by the
   precision of the arguments.

3. There is room for user-created families of DTypes. We can envision an
   abstract ``Unit`` class for physical units, with a concrete subclass like
   ``Float64Unit``. Calling ``Unit(np.float64, "m")`` (``m`` for meters) would
   be equivalent to ``Float64Unit("m")``.

4. The implementation of universal functions in NEP 43 may require
   a class hierarchy.

**Example:** A NumPy ``Categorical`` class would be a match for pandas
``Categorical`` objects, which can contain integers or general Python objects.
NumPy needs a DType that it can assign a Categorical to, but it also needs
DTypes like ``CategoricalInt64`` and ``CategoricalObject`` such that
``common_dtype(CategoricalInt64, String)`` raises an error, but
``common_dtype(CategoricalObject, String)`` returns an ``object`` DType. In
our scheme, ``Categorical`` is an abstract type with ``CategoricalInt64`` and
``CategoricalObject`` subclasses.


Rules for the class structure, illustrated :ref:`below <nep42_hierarchy_figure>`:

1. Abstract DTypes cannot be instantiated. Instantiating an abstract DType
   raises an error, or perhaps returns an instance of a concrete subclass.
   Raising an error will be the default behavior and may be required initially.

2. While abstract DTypes may be superclasses, they may also act like Python's
   abstract base classes (ABC) allowing registration instead of subclassing.
   It may be possible to simply use or inherit from Python ABCs.

3. Concrete DTypes may not be subclassed. In the future this might be relaxed
   to allow specialized implementations such as a GPU float64 subclassing a
   NumPy float64.

The
`Julia language <https://docs.julialang.org/en/v1/manual/types/#man-abstract-types-1>`_
has a similar prohibition against subclassing concrete types.
For example methods such as the later ``__common_instance__`` or
``__common_dtype__`` cannot work for a subclass unless they were designed
very carefully.
It helps avoid unintended vulnerabilities to implementation changes that
result from subclassing types that were not written to be subclassed.
We believe that the DType API should rather be extended to simplify wrapping
of existing functionality.

The DType class requires C-side storage of methods and additional information,
to be implemented by a ``DTypeMeta`` class. Each ``DType`` class is an
instance of ``DTypeMeta`` with a well-defined and extensible interface;
end users ignore it.

.. _nep42_hierarchy_figure:
.. figure:: _static/dtype_hierarchy.svg
    :figclass: align-center


Miscellaneous methods and attributes
==============================================================================

This section collects definitions in the DType class that are not used in
casting and array coercion, which are described in detail below.

* Existing dtype methods and C-side fields are preserved.

* ``DType.type`` replaces ``dtype.type``. Unless a use case arises,
  ``dtype.type`` will be deprecated.
  This indicates a Python scalar type which represents the same values as
  the DType. This is the same type as used in the proposed `Class getter`_
  and for `DType discovery during array coercion`_.
  (This can may also be set for abstract DTypes, this is necessary
  for array coercion.)

* A new ``self.canonical`` property generalizes the notion of byte order to
  indicate whether data has been stored in a default/canonical way. For
  existing code, "canonical" will just signify native byte order, but it can
  take on new meanings in new DTypes -- for instance, to distinguish a
  complex-conjugated instance of Complex which stores ``real - imag`` instead
  of ``real + imag`` and is thus not the canonical storage. The ISNBO ("is
  native byte order") flag might be repurposed as the canonical flag.

* Support is included for parametric DTypes. As explained in
  :ref:`NEP 40 <parametric-datatype-discussion>`, parametric types have a
  value associated with them. A DType will be deemed parametric if it
  inherits from ParametricDType.

  Strings are one example of a parametric type -- ``S8`` is different from
  ``S4`` because ``S4`` cannot store a length 8 string such as ``"length 8"``
  while ``S8`` can.
  Similarly, the ``datetime64`` DType is parametric, since its unit must be specified.
  The associated ``type`` is the ``np.datetime64`` scalar.

* DType methods may resemble or even reuse existing Python slots. Thus Python
  special slots are off-limits for user-defined DTypes (for instance, defining
  ``Unit("m") > Unit("cm")``), since we may want to develop a meaning for these
  operators that is common to all DTypes.

* Sorting functions are moved to the DType class. They may be implemented by
  defining a method ``dtype_get_sort_function(self, sortkind="stable") ->
  sortfunction`` that must return ``NotImplemented`` if the given ``sortkind``
  is not known.

* Functions that cannot be removed are implemented as special methods. 
  Many of these were previously defined part of the :c:type:`PyArray_ArrFuncs`
  slot of the dtype instance (``PyArray_Descr *``) and include functions
  such as ``nonzero``, ``fill`` (used for ``np.arange``), and
  ``fromstr`` (used to parse text files).
  These old methods will be deprecated and replacements
  following the new design principles added.
  The API is not defined here. Since these methods can be deprecated and renamed
  replacements added, it is acceptable if these new methods have to be modified.

* Use of ``kind`` for non-built-in types is discouraged in favor of
  ``isinstance`` checks.  ``kind`` will return the ``__qualname__`` of the
  object to ensure uniqueness for all DTypes. On the C side, ``kind`` and
  ``char`` are set to ``\0`` (NULL character).
  While ``kind`` will be discouraged, the current ``np.issubdtype``
  may remain the preferred method for this type of check. 

* A method ``ensure_canonical(self) -> dtype`` returns a new dtype (or
  ``self``) with the ``canonical`` flag set.

* Since NumPy's approach is to provide functionality through unfuncs,
  functions like sorting that will be implemented in DTypes might eventually be
  reimplemented as generalized ufuncs.

.. _casting:

******************************************************************************
Casting
******************************************************************************

We review here the operations related to casting arrays:

- Finding the "common dtype," currently exposed by ``np.promote_types`` or
  ``np.result_type``

- The result of calling ``np.can_cast``

We show how casting arrays with ``arr.astype(new_dtype)`` will be implemented.

`Common DType` operations
==============================================================================

Common-type operations are vital for array coercion when input types are
mixed. They determine the output dtype of ``np.concatenate()`` and are useful
in themselves.

NumPy provides ``np.result_type`` and
``np.promote_types``.
These differ in that ``np.result_type`` can take arrays and scalars as input
and implements value-based promotion [1]_.

To distinguish between the promotion occurring during universal function
application, we will call it "common type" operation here.

**Motivation:**

Furthermore, common type operations may be used to find the correct dtype
to use for functions with different inputs (including universal functions).
This includes an interesting distinction:

1. Universal functions use the DType classes for dispatching, they thus
   require the common DType class (as a first step).
   While this can help with finding the correct loop to execute, the loop
   may not need the actual common dtype instance.
   (Hypothetical example:
   ``float_arr + string_arr -> string``, but the output string length is
   not the same as ``np.concatenate(float_arr, string_arr)).dtype``.)

2. Array coercion and concatenation require the common dtype *instance*.

**Implementation:** The implementation of the common dtype (instance)
determination has some overlap with casting. Casting from a specific dtype
(Float64) to a String needs to find the correct string length (a step that is
mainly necessary for parametric dtypes).

We propose the following implementation:

1. ``__common_dtype__(cls, other : DTypeMeta) -> DTypeMeta`` answers what the
   common DType class is, given two DType class objects. It may return
   ``NotImplemented`` to defer to ``other``. (For abstract DTypes, subclasses
   get precedence, concrete types are never superclasses, so always get preference
   or are tried from left to right).

2. ``__common_instance__(self: SelfT, other : SelfT) -> SelfT`` is used when
   two instances of the same DType are given.
   For built-in dtypes (that are not parametric), this
   currently always returns ``self`` (but ensures canonical representation).
   This is to preserve metadata. We can thus provide a default implementation
   for non-parametric user dtypes.

These two cases do *not* cover the case where two different dtype instances
need to be promoted. For example `">float64"` and `"S8"`. The solution is
partially "outsourced" to the casting machinery by splitting the operation up
into three steps:

1. ``Float64.__common_dtype__(type(>float64), type(S8))``
   returns `String` (or defers to ``String.__common_dtype__``).
2. The casting machinery provides the information that `">float64"` casts
   to `"S32"` (see below for how casting will be defined).
3. ``String.__common_instance__("S8", "S32")`` returns the final `"S32"`.

The main reason for this is to avoid the need to implement identical
functionality multiple times. The design (together with casting) naturally
separates the concerns of different Datatypes. In the above example, Float64
does not need to know about the cast. While the casting machinery
(``CastingImpl[Float64, String]``) could include the third step, it is not
required to do so and the string can always be extended (e.g. with new
encodings) without extending the ``CastingImpl[Float64, String]``.

This means the implementation will work like this::

    def common_dtype(DType1, DType2):
        common_dtype = type(dtype1).__common_dtype__(type(dtype2))
        if common_dtype is NotImplemented:
            common_dtype = type(dtype2).__common_dtype__(type(dtype1))
            if common_dtype is NotImplemented:
                raise TypeError("no common dtype")
        return common_dtype

    def promote_types(dtype1, dtyp2):
        common = common_dtype(type(dtype1), type(dtype2))

        if type(dtype1) is not common:
            # Find what dtype1 is cast to when cast to the common DType
            # by using the CastingImpl as described below:
            castingimpl = get_castingimpl(type(dtype1), common)
            safety, (_, dtype1) = castingimpl.resolve_descriptors((dtype1, None))
            assert safety == "safe"  # promotion should normally be a safe cast

        if type(dtype2) is not common:
            # Same as above branch for dtype1.

        if dtype1 is not dtype2:
            return common.__common_instance__(dtype1, dtype2)

Some of these steps may be optimized for non-parametric DTypes.

**Note:** A currently implemented fallback for the ``__common_dtype__``
operation is to use the "safe" casting logic. Since ``int16`` can safely cast
to ``int64``, it is clear that ``np.promote_types(int16, int64)`` should be
``int64``.

However, this cannot define all such operations, and will fail for example for::

    np.promote_types("int64", "float32") -> np.dtype("float64")

In this design, it is the responsibility of the DType author to ensure that
in most cases a safe-cast implies that this will be the result of the
``__common_dtype__`` method.

Note that some exceptions may apply. For example casting ``int32`` to
a (long enough) string is  at least at this time  considered "safe".
However ``np.promote_types(int32, String)`` will *not* be defined.

**Alternatives:** The use of casting for common dtype (instance) determination
neatly separates the concerns and allows for a minimal set of duplicate
functionality being implemented. In cases of mixed DType (classes), it also
adds an additional step to finding the common dtype. The common dtype (of two
instances) could thus be implemented explicitly to avoid this indirection,
potentially only as a fast-path. The above suggestion assumes that this is,
however, not a speed relevant path, since in most cases, e.g. in array
coercion, only a single Python type (and thus dtype) is involved. The proposed
design hinges in the implementation of casting to be separated into its own
ufunc-like object as described below.

In principle common DType could be defined only based on "safe casting" rules,
if we order all DTypes and find the first one both can cast to safely.
However, the issue with this approach is that a newly added DType can change
the behaviour of an existing program.  For example, a new ``int24`` would be
the first valid common type for ``int16`` and ``uint16``, demoting the
currently defined behavior of ``int32``.
Both, the need of a linear type hierarchy and the potential of changing
existing behaviour by adding a new DType, are a downside to using a generic
rule based on "safe casting".
However, a more generic common DType could be implemented in the future, since
``__common_dtype__`` can in principle use casting information internally.

**Example:** ``object`` always chooses ``object`` as the common DType.  For
``datetime64`` type promotion is defined with no other datatype, but if
someone were to implement a new higher precision datetime, then::

    HighPrecisionDatetime.__common_dtype__(np.dtype[np.datetime64])

would return ``HighPrecisionDatetime``, and the below casting may need to
decide how to handle the datetime unit.


The cast operation
==============================================================================

Perhaps the most complex and interesting DType operation is casting. Casting
is much like a typical universal function on arrays, converting one input to a
new output. There are two key distinctions:

1. Casting always requires an explicit output datatype.
2. The NumPy iterator API requires access to functions that are lower-level
   than what universal functions currently need.

Casting can be complex, and may not implement all details of each input
datatype (such as non-native byte order or unaligned access). Thus casting
naturally is performed in up to three steps:

1. The given datatype is normalized and prepared for the actual cast.
2. The cast is performed.
3. The cast result, which is in a normalized form, is cast to the requested
   form (non-native byte order).

Often only step 2 is required.

Further, NumPy provides different casting kinds or safety specifiers:

* "equivalent"
* "safe"
* "same_kind"
* "unsafe"

and in some cases a cast may even be represented as a simple view.


**Motivation:** Similar to the common dtype/DType operation above, we again
have two use cases:

1. ``arr.astype(np.String)`` (current spelling ``arr.astype("S")``)
2. ``arr.astype(np.dtype("S8"))``

where the first case is also noted in NEP 40 and 41 as a design goal, since
``np.String`` could also be an abstract DType as mentioned above.

The implementation of casting should also come with as little duplicate
implementation as necessary, i.e. to avoid unnecessary methods on the DTypes.
Furthermore, it is desirable that casting is implemented similar to universal
functions.

Analogous to the above, the following also need to be defined:

1. ``np.can_cast(dtype, DType, "safe")`` (instance to class)
2. ``np.can_cast(dtype, other_dtype, "safe")`` (casting an instance to another
   instance)

overloading the meaning of ``dtype`` to mean either class or instance (on the
Python level). The question of ``np.can_cast(DType, OtherDType, "safe")`` is
also a possibility and may be used internally. However, it is initially not
necessary to expose to Python.


**Implementation:** During DType creation, DTypes will have the ability to
pass a list of ``CastingImpl`` objects, which can define casting to and from
the DType. One of these ``CastingImpl`` objects is special because it should
define the cast within the same DType (from one instance to another). A DType
which does not define this, must have only a single implementation and not be
parametric.

Each ``CastingImpl`` has a specific DType signature:
``CastingImpl[InputDtype, RequestedDtype]``
and implements the following methods and attributes:

* ``resolve_descriptors(self, Tuple[DType] : input) -> casting, Tuple[DType]``.
  Here ``casting`` signals the casting safeness (safe, unsafe, or same-kind)
  and the output dtype tuple is used for more multi-step casting (see below).
* ``get_transferfunction(...) -> function handling cast`` (signature to be decided).
  This function returns a low-level implementation of a strided casting function
  ("transfer function").
* ``casting`` attribute with one of equivalent, safe, unsafe, or same-kind. Used to
  quickly decide casting safety when this is relevant.

``resolve_descriptors`` provides information about whether or
not a cast is safe and is of importance mainly for parametric DTypes.
``get_transferfunction`` provides NumPy with a function capable of performing
the actual cast.  Initially the implementation of ``get_transferfunction``
will be *private*, and users will only be able to provide strided loops
with the signature.

**Performing the cast**

.. _cast_figure:

.. figure:: _static/casting_flow.svg
    :figclass: align-center

`The above figure <cast_figure>`_ illustrates the multi-step logic necessary to
cast for example an ``int24`` with a value of ``42`` to a string of length 20
(``"S20"``).
In this example, the implementer only provided the functionality of casting
an ``int24`` to an ``S8`` string (which can hold all 24bit integers).
Due to this limited implementation, the full cast has to do multiple
conversions.  The full process is:

1. Call ``CastingImpl[Int24, String].resolve_descriptors((int24, "S20"))``.
   This provides the information that ``CastingImpl[Int24, String]`` only
   implements the cast of ``int24`` to ``"S8"``.
2. Since ``"S8"`` does not match ``"S20"``, use
   ``CastingImpl[String, String].get_transferfunction()``
   to find the transfer (casting) function to convert an ``"S8"`` into an ``"S20"``
3. Fetch the transfer function to convert an ``int24`` to an ``"S8"`` using
   ``CastingImpl[Int24, String].get_transferfunction()``
4. Perform the actual cast using the two transfer functions:
   ``int24(42) -> S8("42") -> S20("42")``.

Note that in this example the ``resolve_descriptors`` function plays a less
central role.  It becomes more important for ``np.can_cast``.

Further, ``resolve_descriptors`` allows the implementation for
``np.array(42, dtype=int24).astype(String)`` to call
``CastingImpl[Int24, String].resolve_descriptors((int24, None))``.
In this case the result of ``(int24, "S8")`` defines the correct cast:
``np.array(42, dtype=int24),astype(String) == np.array("42", dtype="S8")``.

**Casting safety**

To answer the question of casting safety ``np.can_cast(int24, "S20",
casting="safe")``, only the ``resolve_descriptors`` function is required and
is called in the same way as in `the figure describing a cast <cast_figure>`_.
In this case, the calls to ``resolve_descriptors``, will also provide the
information that ``int24 -> "S8"`` as well as ``"S8" -> "S20"`` are safe
casts, and thus also the ``int24 -> "S20"`` is a safe cast.

In some cases, no cast is necessary. For example, on most Linux systems
``np.dtype("long")`` and ``np.dtype("longlong")`` are different dtypes but are
both 64bit integers.
In this case, the cast can be performed using ``long_arr.view("longlong")``.
The information that a cast is a
"view" will be handled by an additional flag.  Thus the ``casting``
can have the 8 values in total: equivalent, safe, unsafe, same-kind as well as equivalent+view, safe+view,
unsafe+view, and same-kind+view.
NumPy currently defines ``dtype1 == dtype2`` to be True only if byte order matches.
This functionality can be replaced with the combination of "equivalent" casting
and the "view" flag.

(For more information on the ``resolve_descriptors`` signature see the C-API
section below and NEP 43.)


**Casting between instances of the same DType**

In general one of the casting implementations defined by the DType implementor
must be ``CastingImpl[DType, DType]`` (unless there is only a singleton
instance). To keep the casting to as few steps as possible, this
implementation must initially be capable of any conversions between all instances of this
DType.


**General multistep casting**

In general we could implement certain casts, such as ``int8`` to ``int24``
even if the user only provides an ``int16 -> int24`` cast. This proposal
currently does not provide this functionality.  However, it could be extended
in the future to either find such casts dynamically, or at least allow
``resolve_descriptors`` to return arbitrary ``dtypes``. If ``CastingImpl[Int8,
Int24].resolve_descriptors((int8, int24))`` returns ``(int16, int24)``, the
actual casting process could be extended to include the ``int8 -> int16``
cast. This adds an additional step to the casting process.


**Alternatives:** The choice of using only the DType classes in the first step
of finding the correct ``CastingImpl`` means that the default implementation
of ``__common_dtype__`` has a reasonable definition of "safe casting" between
DTypes classes (although e.g. the concatenate operation using it may still
fail when attempting to find the actual common instance or cast).

The split into multiple steps may seem to add complexity rather than reduce
it, however, it consolidates that we have the two distinct signatures of
``np.can_cast(dtype, DTypeClass)`` and ``np.can_cast(dtype, other_dtype)``.
Further, the above API guarantees the separation of concerns for user DTypes.
The user ``Int24`` dtype does not have to handle all string lengths if it does
not wish to do so.  Further, if an encoding was added to the ``String`` DType,
this does not affect the overall cast. The ``resolve_descriptors`` function can
keep returning the default encoding and the ``CastingImpl[String, String]``
can take care of any necessary encoding changes.

The main alternative to the proposed design is to move most of the information
which is here pushed into the ``CastingImpl`` directly into methods on the
DTypes. This, however, will not allow the close similarity between casting and
universal functions. On the up side, it reduces the necessary indirection as
noted below.

An initial proposal defined two methods ``__can_cast_to__(self, other)`` to
dynamically return ``CastingImpl``. The advantage of this addition is that it
removes the requirement to define all possible casts at DType creation time (of
one of the involved DTypes).
Such API could be added at a later time. This is similar to Python which
provides ``__getattr__`` for additional control over attribute lookup.

**Notes:** The proposed ``CastingImpl`` is designed to be identical to the
``PyArrayMethod`` proposed in NEP 43 as part of restructuring ufuncs to handle
new DTypes.

The way dispatching works for ``CastingImpl`` is planned to be limited
initially and fully opaque. In the future, it may or may not be moved into a
special UFunc, or behave more like a universal function.


**Example:** The implementation for casting integers to datetime would generally
say that this cast is unsafe (because it is always an unsafe cast).
Its ``resolve_descriptors`` function may look like::

    def resolve_descriptors(self, given_dtypes):
        from_dtype, to_dtype = given_dtypes

        from_dtype = from_dtype.ensure_canonical()  # ensure not byte-swapped
        if to_dtype is None:
            raise TypeError("Cannot convert to a NumPy datetime without a unit")
        to_dtype = to_dtype.ensure_canonical()  # ensure not byte-swapped

        # This is always an "unsafe" cast, but for int64, we can represent
        # it by a simple view (if the dtypes are both canonical).
        # (represented as C-side flags here).
        safety_and_view = NPY_UNSAFE_CASTING | NPY_CAST_IS_VIEW
        return safety_and_view, (from_dtype, to_dtype)

.. note::

    While NumPy currently defines integer to datetime casts, with the possible
    exception of the unit-less ``timedelta64`` it may be better to not define
    these casts at all.  In general we expect that user defined DTypes will be
    using custom methods such as ``unit.drop_unit(arr)`` or ``arr *
    unit.seconds``.


******************************************************************************
Array coercion
******************************************************************************

The following sections discuss the two aspects related to creating an array from
arbitrary python objects. This requires a defined protocol to store data
inside the array. Further, it requires the ability to find the correct dtype
when a user does not provide the dtype explicitly.

Coercion to and from Python objects
==============================================================================

**Motivation:** When storing a single value in an array or taking it out, it
is necessary to coerce (convert) it to and from the low-level representation
inside the array.

**Description:** Coercing to and from Python scalars requires two to three
methods:

1. ``__dtype_setitem__(self, item_pointer, value)``
2. ``__dtype_getitem__(self, item_pointer, base_obj) -> object``;
   ``base_obj`` is for memory management and usually ignored; it points to
   an object owning the data. Its only role is to support structured datatypes
   with subarrays within NumPy, which currently return views into the array.
   The function returns an equivalent Python scalar (i.e. typically a NumPy
   scalar).
3. ``__dtype_get_pyitem__(self, item_pointer, base_obj) -> object`` (initially
   hidden for new-style user-defined datatypes, may be exposed on user
   request). This corresponds to the ``arr.item()`` method also used by
   ``arr.tolist()`` and returns Python floats, for example, instead of NumPy
   floats.

(The above is meant for C-API. A Python-side API would have to use byte
buffers or similar to implement this, which may be useful for prototyping.)

These largely correspond to the current definitions.  When a certain scalar
has a known (different) dtype, NumPy may in the future use casting instead of
``__dtype_setitem__``. A user datatype is (initially) expected to implement
``__dtype_setitem__`` for its own ``DType.type`` and all basic Python scalars
it wishes to support (e.g. ``int`` and ``float``). In the future a
function "``known_scalartype``" may be made public to allow a user dtype to signal
which Python scalars it can store directly.


**Implementation:** The pseudocode implementation for setting a single item in
an array from an arbitrary Python object ``value`` is (note that some
functions are only defined below)::

    def PyArray_Pack(dtype, item_pointer, value):
        DType = type(dtype)
        if DType.type is type(value) or DType.known_scalartype(type(value)):
            return dtype.__dtype_setitem__(item_pointer, value)

        # The dtype cannot handle the value, so try casting:
        arr = np.array(value)
        if arr.dtype is object or arr.ndim != 0:
            # not a numpy or user scalar; try using the dtype after all:
            return dtype.__dtype_setitem__(item_pointer, value)

         arr.astype(dtype)
         item_pointer.write(arr[()])

where the call to ``np.array()`` represents the dtype discovery and is
not actually performed.

**Example:** Current ``datetime64`` returns ``np.datetime64`` scalars and can
be assigned from ``np.datetime64``. However, the datetime
``__dtype_setitem__`` also allows assignment from date strings ("2016-05-01")
or Python integers. Additionally the datetime ``__dtype_get_pyitem__``
function actually returns a Python ``datetime.datetime`` object (most of the
time).


**Alternatives:** This functionality could also be implemented as a cast to and
from the ``object`` dtype.
However, coercion is slightly more complex than typical casts.
One reason is that in general a Python object could itself be a
zero-dimensional array or scalar with an associated DType.
Such an object has a DType, and the correct cast to another DType is already
defined::

    np.array(np.float32(4), dtype=object).astype(np.float64)

is identical to::

    np.array(4, dtype=np.float32).astype(np.float64)

Implementing the first ``object`` to ``np.float64`` cast explicitly,
would require the user to take to duplicate or fall back to existing
casting functionality.

It is certainly possible to describe the coercion to and from Python objects
using the general casting machinery,
but the ``object`` dtype is special and important enough to be handled by NumPy
using the presented methods.

**Further Issues and Discussion:** The ``__dtype_setitem__`` function currently duplicates
some code, such as coercion from a string. ``datetime64`` allows assignment
from string, but the same conversion also occurs for casting from the string
dtype to ``datetime64``. In the future, we may expose the ``known_scalartype``
function to allow the user to implement such duplication.
For example, NumPy would normally use ``np.array(np.string_("2019")).astype(datetime64)``,
but ``datetime64`` could choose to use its ``__dtype_setitem__`` instead,
e.g. for performance reasons.

There is an issue about how subclasses of scalars should be handled.
We anticipate to stop automatically detecting the dtype for
``np.array(float64_subclass)`` to be float64.
The user can still provide ``dtype=np.float64``.
However, the above automatic casting using ``np.array(scalar_subclass).astype(requested_dtype)``
will fail.
In many cases, this is not an issue, since the Python ``__float__`` protocol
can be used instead.  But in some cases, this will mean that subclasses of
Python scalars will behave differently.

.. note::

    *Example:* ``np.complex256`` should not use ``__float__`` in its
    ``__dtype_setitem__`` method in the future unless it is a known floating
    point type.  If the scalar is a subclass of a different high precision
    floating point type (e.g. ``np.float128``) then this currently loses
    precision without notifying the user.
    In that case ``np.array(float128_subclass(3), dtype=np.complex256)``
    may fail unless the ``float128_subclass`` is first converted to the
    ``np.float128`` base class.


DType discovery during array coercion
==============================================================================

An important step in the use of NumPy arrays is creation of the array
from collections of generic Python objects.

**Motivation:** Although the distinction is not clear currently, there are two main needs::

    np.array([1, 2, 3, 4.])

needs to guess the correct dtype based on the Python objects inside.
Such an array may include a mix of datatypes, as long as they can be
promoted.
A second use case is when users provide the output DType class, but not the
specific DType instance::

    np.array([object(), None], dtype=np.dtype[np.string_])  # (or `dtype="S"`)

In this case the user indicates that ``object()`` and ``None`` should be
interpreted as strings.
The need to consider the user provided DType also arises for a future
``Categorical``::

    np.array([1, 2, 1, 1, 2], dtype=Categorical)

which must interpret the numbers as unique categorical values rather than
integers.

There are three further issues to consider:

1. It may be desirable to create datatypes associated
   with normal Python scalars (such as ``datetime.datetime``) that do not
   have a ``dtype`` attribute already.
2. In general, a datatype could represent a sequence, however, NumPy currently
   assumes that sequences are always collections of elements
   (the sequence cannot be an element itself).
   An example would be a ``vector`` DType.
3. An array may itself contain arrays with a specific dtype (even
   general Python objects).  For example:
   ``np.array([np.array(None, dtype=object)], dtype=np.String)``
   poses the issue of how to handle the included array.

Some of these difficulties arise because finding the correct shape
of the output array and finding the correct datatype are closely related.

**Implementation:** There are two distinct cases above:

1. The user has provided no dtype information.
2. The user provided a DType class  -- as represented, for example, by ``"S"``
   representing a string of any length.

In the first case, it is necessary to establish a mapping from the Python type(s)
of the constituent elements to the DType class.
Once the DType class is known, the correct dtype instance needs to be found.
In the case of strings, this requires to find the string length.

These two cases shall be implemented by leveraging two pieces of information:

1. ``DType.type``: The current type attribute to indicate which Python scalar
   type is associated with the DType class (this is a *class* attribute that always
   exists for any datatype and is not limited to array coercion).
2. ``__discover_descr_from_pyobject__(cls, obj) -> dtype``: A classmethod that
   returns the correct descriptor given the input object.
   Note that only parametric DTypes have to implement this.
   For non-parametric DTypes using the default instance will always be acceptable.

The Python scalar type which is already associated with a DType through the
``DType.type`` attribute maps from the DType to the Python scalar type.
At registration time, a DType may choose to allow automatically discover for
this Python scalar type.
This requires a lookup in the opposite direction, which will be implemented
using global a mapping (dictionary-like) of::

   known_python_types[type] = DType

Correct garbage collection requires additional care.
If both the Python scalar type (``pytype``) and ``DType`` are created dynamically,
they will potentially be deleted again.
To allow this, it must be possible to make the above mapping weak.
This requires that the ``pytype`` holds a reference of ``DType`` explicitly.
Thus, in addition to building the global mapping, NumPy will store the ``DType`` as
``pytype.__associated_array_dtype__`` in the Python type.
This does *not* define the mapping and should *not* be accessed directly.
In particular potential inheritance of the attribute does not mean that NumPy will use the
superclasses ``DType`` automatically. A new ``DType`` must be created for the
subclass.

.. note::

    Python integers do not have a clear/concrete NumPy type associated right
    now. This is because during array coercion NumPy currently finds the first
    type capable of representing their value in the list of `long`, `unsigned
    long`, `int64`, `unsigned int64`, and `object` (on many machines `long` is
    64 bit).

    Instead they will need to be implemented using an ``AbstractPyInt``. This
    DType class can then provide ``__discover_descr_from_pyobject__`` and
    return the actual dtype which is e.g. ``np.dtype("int64")``. For
    dispatching/promotion in ufuncs, it will also be necessary to dynamically
    create ``AbstractPyInt[value]`` classes (creation can be cached), so that
    they can provide the current value based promotion functionality provided
    by ``np.result_type(python_integer, array)`` [1]_.

To allow for a DType to accept inputs as scalars that are not basic Python
types or instances of ``DType.type``, we use ``known_scalar_type`` method.
This can allow discovery of a ``vector`` as a scalar (element) instead of a sequence
(for the command ``np.array(vector, dtype=VectorDType)``) even when ``vector`` is itself a
sequence or even an array subclass. This will *not* be public API initially,
but may be made public at a later time.

**Example:** The current datetime DType requires a
``__discover_descr_from_pyobject__`` which returns the correct unit for string
inputs.  This allows it to support::

    np.array(["2020-01-02", "2020-01-02 11:24"], dtype="M8")

By inspecting the date strings. Together with the common dtype
operation, this allows it to automatically find that the datetime64 unit
should be "minutes".


**NumPy Internal Implementation:** The implementation to find the correct dtype
will work similar to the following pseudocode::

    def find_dtype(array_like):
        common_dtype = None
        for element in array_like:
            # default to object dtype, if unknown
            DType = known_python_types.get(type(element), np.dtype[object])
            dtype = DType.__discover_descr_from_pyobject__(element)

            if common_dtype is None:
                common_dtype = dtype
            else:
                common_dtype = np.promote_types(common_dtype, dtype)

In practice, the input to ``np.array()`` is a mix of sequences and array-like
objects, so that deciding what is an element requires to check whether it
is a sequence.
The full algorithm (without user provided dtypes) thus looks more like::

    def find_dtype_recursive(array_like, dtype=None):
        """
        Recursively find the dtype for a nested sequences (arrays are not
        supported here).
        """
        DType = known_python_types.get(type(element), None)

        if DType is None and is_array_like(array_like):
            # Code for a sequence, an array_like may have a DType we
            # can use directly:
            for element in array_like:
                dtype = find_dtype_recursive(element, dtype=dtype)
            return dtype

        elif DType is None:
            DType = np.dtype[object]

        # dtype discovery and promotion as in `find_dtype` above

If the user provides ``DType``, then this DType will be tried first, and the
``dtype`` may need to be cast before the promotion is performed.

**Limitations:** The motivational point 3. of a nested array
``np.array([np.array(None, dtype=object)], dtype=np.String)`` is currently
(sometimes) supported by inspecting all elements of the nested array.
User DTypes will implicitly handle these correctly if the nested array
is of ``object`` dtype.
In some other cases NumPy will retain backward compatibility for existing
functionality only.
NumPy uses such functionality to allow code such as::

    >>> np.array([np.array(["2020-05-05"], dtype="S")], dtype=np.datetime64)
    array([['2020-05-05']], dtype='datetime64[D]')

which discovers the datetime unit ``D`` (days).
This possibility will not be accessible to user DTypes without an
intermediate cast to ``object`` or a custom function.

The use of a global type map means that an error or warning has to be given if
two DTypes wish to map to the same Python type. In most cases user DTypes
should only be implemented for types defined within the same library to avoid
the potential for conflicts. It will be the DType implementor's responsibility
to be careful about this and use avoid registration when in doubt.

**Alternatives:** Instead of a global mapping, we could rely on the scalar
attribute ``scalar.__associated_array_dtype__``.
This only creates a difference in behaviour for subclasses and the exact
implementation can be undefined initially.
Scalars will be expected to derive from a NumPy scalar.
In principle NumPy could, for a time, still choose to rely on the attribute.

An earlier proposal for the ``dtype`` discovery algorithm,
was to use a two-pass approach.
First finding only the correct ``DType`` class and only then discovering the parametric
``dtype`` instance.
This was rejected for unnecessary complexity.
The main advantage of this method is that it would have enabled value
based promotion in universal functions, allowing::

    np.add(np.array([8], dtype="uint8"), [4])

to return a ``uint8`` result (instead of ``int16``), which currently happens for::

    np.add(np.array([8], dtype="uint8"), 4)

(note the list ``[4]`` instead of scalar ``4``).
This is not a feature NumPy currently has or desires to support.

**Further Issues and Discussion:** It is possible to create a DType
such as Categorical, array, or vector which can only be used if ``dtype=DType``
is provided. Such DTypes cannot roundtrip correctly. For example::

    np.array(np.array(1, dtype=Categorical)[()])

will result in an integer array. To get the original ``Categorical`` array
``dtype=Categorical`` will need to be passed explicitly.
This is a general limitation, but round-tripping is always possible if
``dtype=original_arr.dtype`` is passed.


.. _c-api:

******************************************************************************
Public C-API
******************************************************************************

A Python side API shall not be defined here. This is a general side approach.


DType creation
==============================================================================

To create a new DType the user will need to define all the methods and
attributes as presented above and outlined in the `Usage and impact`_
section.
Some additional methods similar to those currently defined as part of
:c:type:`PyArray_ArrFuncs` will be necessary and part of the slots struct
below.

As already mentioned in NEP 41, the interface to define this DType class in C is
modeled after the `Python limited API <https://www.python.org/dev/peps/pep-0384/>`_:
the above-mentioned slots and some additional necessary information will
thus be passed within a slots struct and identified by ``ssize_t`` integers::

    static struct PyArrayMethodDef slots[] = {
        {NPY_dt_method, method_implementation},
        ...,
        {0, NULL}
    }

    typedef struct{
      PyTypeObject *typeobj;    /* type of python scalar or NULL */
      int flags                 /* flags, including parametric and abstract */
      /* NULL terminated CastingImpl; is copied and references are stolen */
      CastingImpl *castingimpls[];
      PyType_Slot *slots;
      PyTypeObject *baseclass;  /* Baseclass or NULL */
    } PyArrayDTypeMeta_Spec;

    PyObject* PyArray_InitDTypeMetaFromSpec(PyArrayDTypeMeta_Spec *dtype_spec);

All of this information will be copied.

**TODO:** The DType author should be able to define new methods for their
DType, up to defining a full type object and in the future possibly even
extending the ``PyArrayDTypeMeta_Type`` struct. We have to decide on how (and
what) to make available to the user initially. A possible initial solution may
be to only allow inheriting from an existing class: ``class MyDType(np.dtype,
MyBaseclass)``. If ``np.dtype`` is first in the method resolution order, this
also prevents overriding some slots, such as ``==`` which may not be desirable.


The ``slots`` will be identified by names which are prefixed with ``NPY_dt_``
and are:

* ``is_canonical(self) -> {0, 1}``
* ``ensure_canonical(self) -> dtype``
* ``default_descr(self) -> dtype`` (return must be native and should normally be a singleton)
* ``setitem(self, char *item_ptr, PyObject *value) -> {-1, 0}``
* ``getitem(self, char *item_ptr, PyObject (base_obj) -> object or NULL``
* ``discover_descr_from_pyobject(cls, PyObject) -> dtype or NULL``
* ``common_dtype(cls, other) -> DType, NotImplemented, or NULL``
* ``common_instance(self, other) -> dtype or NULL``

Where possible, a default implementation will be provided if the slot is
ommitted or set to ``NULL``.
Non-parametric dtypes do not have to implement:

* ``discover_descr_from_pyobject`` (uses ``default_descr`` instead)
* ``common_instance`` (uses ``default_descr`` instead)
* ``ensure_canonical`` (uses ``default_descr`` instead). 

Sorting is expected to be implemented using:

* ``get_sort_function(self, NPY_SORTKIND sort_kind) -> {out_sortfunction, NotImplemented, NULL}``.

Although for convenience, it will be sufficient if the user implements only:

* ``compare(self, char *item_ptr1, char *item_ptr2, int *res) -> {-1, 0, 1}``


**Limitations:** Using the above ``PyArrayDTypeMeta_Spec`` struct, the
structure itself can only be extended clumsily (e.g. by adding a version tag
to the ``slots`` to indicate a new, longer version of the struct). We could
also provide the struct using a function, which however will require memory
management but would allow ABI-compatible extension (the struct is freed again
when the DType is created).


CastingImpl
==============================================================================

The external API for ``CastingImpl`` will be limited initially to defining:

* ``casting`` attribute, which can be one of the supported casting kinds.
  This is the safest cast possible. For example casting between two NumPy
  strings is of course "safe" in general, but may be "same kind" in a specific
  instance if the second string is shorter. If neither type is parametric the
  ``resolve_descriptors`` must use it.

* ``resolve_descriptors(self, given_descrs[2], loop_descrs[2]) -> int {casting, -1}``:
  The ``loop_descrs`` must be set correctly to dtypes which the strided loop
  (transfer function) can handle.  Initially the result must have instances
  of the same DType class as the ``CastingImpl`` is defined for. The
  ``casting`` will be set to ``NPY_EQUIV_CASTING``, ``NPY_SAFE_CASTING``,
  ``NPY_UNSAFE_CASTING``, or ``NPY_SAME_KIND_CASTING``.
  A new, additional flag, ``NPY_CAST_IS_VIEW``, can be set to indicate that
  no cast is necessary and a view is sufficient to perform the cast.
  The return value shall be ``-1`` to indicate that the cast is not possible.
  If no error is set, a generic error message will be given. If an error is
  already set it will be chained and may provide additional information.
  Note that ``self`` represents additional call information; details are given
  in NEP 43.

* ``strided_loop(char **args, npy_intp *dimensions, npy_intp *strides,
  ...) -> int {0, -1}`` (signature will be fully defined in NEP 43)

This is identical to the proposed API for ufuncs. The additional ``...``
part of the signature will include information such as the two ``dtype``\s.
More optimized loops are in use internally, and
will be made available to users in the future (see notes).

Although verbose, the API shall mimic the one for creating a new DType:

.. code-block:: C

    typedef struct{
      int flags;                  /* e.g. whether the cast requires the API */
      int nin, nout;              /* Number of Input and outputs (always 1) */
      NPY_CASTING casting;        /* The default casting level */
      PyArray_DTypeMeta *dtypes;  /* input and output DType class */
      /* NULL terminated slots defining the methods */
      PyType_Slot *slots;
    } PyArrayMethod_Spec;

The focus differs between casting and general ufuncs.  For example for casts
``nin == nout == 1`` is always correct, while for ufuncs ``casting`` is
expected to be usually `"safe"`.

**Notes:** We may initially allow users to define only a single loop. However,
internally NumPy optimizes far more, and this should be made public
incrementally, either by allowing multiple versions, such as:

* contiguous inner loop
* strided inner loop
* scalar inner loop

or more likely through exposure of the ``get_loop`` function which is passed
additional information, such as the fixed strides (similar to our internal
API).

The above example does not yet include potential setup and error handling
requirements. Since these are similar to the UFunc machinery, this will be
defined in detail in NEP 43 and then incorporated identically into casting.

The slots/methods used will be prefixed ``NPY_uf_`` for similarity to the
ufunc machinery.



**Alternatives:** Aside from name changes, and possible signature tweaks,
there seem to be few alternatives to the above structure.
The proposed API using ``*_FromSpec`` function is a good way to achieve a stable
and extensible API. The slots design is extensible and can be
changed without breaking binary compatibility.
Convenience functions can still be provided to allow creation with less code.

One downside of this approach is that compilers cannot warn about function pointer
incompatibilities.


******************************************************************************
Implementation
******************************************************************************

Steps for implementation are outlined in :ref:`NEP 41 <NEP41>`. This includes
internal restructuring for the new casting and array-coercion.
First, the NumPy will internally be rewritten using the above methods for
casting and array-coercion.

After that, the new public API will be added incrementally.
We plan to expose it in a preliminary state initially to allow modification
after some experience can be gained.
In addition to the features presented in detail in this NEP, all functionality
currently implemented on the dtypes will be replaced systematically.


******************************************************************************
Alternatives
******************************************************************************

The space of possible implementations is large, so there have been many
discussions, conceptions, and design documents. These are listed in NEP 40.
Since this NEP encompasses multiple individual decisions, alternatives
are discussed in the above individual sections.


******************************************************************************
References
******************************************************************************

.. [1] NumPy currently inspects the value to allow the operations::

     np.array([1], dtype=np.uint8) + 1
     np.array([1.2], dtype=np.float32) + 1.

   to return a ``uint8`` or ``float32`` array respectively.  This is
   further described in the documentation for :func:`numpy.result_type`.


******************************************************************************
Copyright
******************************************************************************

This document has been placed in the public domain.
