"""
A module with various ``typing.Protocol`` subclasses that implement
the ``__call__`` magic method.

See the `Mypy documentation`_ on protocols for more details.

.. _`Mypy documentation`: https://mypy.readthedocs.io/en/stable/protocols.html#callback-protocols

"""

import sys
from typing import Union, TypeVar, overload, Any, TYPE_CHECKING, NoReturn

from numpy import (
    generic,
    bool_,
    timedelta64,
    number,
    integer,
    unsignedinteger,
    signedinteger,
    int32,
    int64,
    floating,
    float32,
    float64,
    complexfloating,
    complex64,
    complex128,
)
from ._scalars import (
    _BoolLike,
    _IntLike,
    _FloatLike,
    _ComplexLike,
    _NumberLike,
)
from . import NBitBase, _64Bit

if sys.version_info >= (3, 8):
    from typing import Protocol
    HAVE_PROTOCOL = True
else:
    try:
        from typing_extensions import Protocol
    except ImportError:
        HAVE_PROTOCOL = False
    else:
        HAVE_PROTOCOL = True

if TYPE_CHECKING or HAVE_PROTOCOL:
    _NBit_co = TypeVar("_NBit_co", covariant=True, bound=NBitBase)
    _IntType = TypeVar("_IntType", bound=integer)
    _NumberType = TypeVar("_NumberType", bound=number)
    _NumberType_co = TypeVar("_NumberType_co", covariant=True, bound=number)
    _GenericType_co = TypeVar("_GenericType_co", covariant=True, bound=generic)

    class _BoolOp(Protocol[_GenericType_co]):
        @overload
        def __call__(self, __other: _BoolLike) -> _GenericType_co: ...
        @overload  # platform dependent
        def __call__(self, __other: int) -> Union[int32, int64]: ...
        @overload
        def __call__(self, __other: float) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(self, __other: _NumberType) -> _NumberType: ...

    class _BoolBitOp(Protocol[_GenericType_co]):
        @overload
        def __call__(self, __other: _BoolLike) -> _GenericType_co: ...
        @overload  # platform dependent
        def __call__(self, __other: int) -> Union[int32, int64]: ...
        @overload
        def __call__(self, __other: _IntType) -> _IntType: ...

    class _BoolSub(Protocol):
        # Note that `__other: bool_` is absent here
        @overload
        def __call__(self, __other: bool) -> NoReturn: ...
        @overload  # platform dependent
        def __call__(self, __other: int) -> Union[int32, int64]: ...
        @overload
        def __call__(self, __other: float) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(self, __other: _NumberType) -> _NumberType: ...

    class _BoolTrueDiv(Protocol):
        @overload
        def __call__(self, __other: Union[float, _IntLike, _BoolLike]) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(self, __other: _NumberType) -> _NumberType: ...

    class _TD64Div(Protocol[_NumberType_co]):
        @overload
        def __call__(self, __other: timedelta64) -> _NumberType_co: ...
        @overload
        def __call__(self, __other: _FloatLike) -> timedelta64: ...

    class _IntTrueDiv(Protocol[_NBit_co]):  # type: ignore[misc]
        @overload
        def __call__(self, __other: bool) -> floating[_NBit_co]: ...
        @overload
        def __call__(self, __other: int) -> Union[float32, float64]: ...
        @overload
        def __call__(self, __other: float) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(self, __other: integer[_NBit_co]) -> floating[_NBit_co]: ...

    class _UnsignedIntOp(Protocol[_NBit_co]):  # type: ignore[misc]
        # NOTE: `uint64 + signedinteger -> float64`
        @overload
        def __call__(self, __other: bool) -> unsignedinteger[_NBit_co]: ...
        @overload
        def __call__(
            self, __other: Union[int, signedinteger[Any]]
        ) -> Union[signedinteger[Any], float64]: ...
        @overload
        def __call__(self, __other: float) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(
            self, __other: unsignedinteger[_NBit_co]
        ) -> unsignedinteger[_NBit_co]: ...

    class _UnsignedIntBitOp(Protocol[_NBit_co]):  # type: ignore[misc]
        @overload
        def __call__(self, __other: bool) -> unsignedinteger[_NBit_co]: ...
        @overload
        def __call__(
            self, __other: unsignedinteger[_NBit_co]
        ) -> unsignedinteger[_NBit_co]: ...
        @overload
        def __call__(
            self: _UnsignedIntBitOp[_64Bit],
            __other: Union[int, signedinteger[Any]],
        ) -> NoReturn: ...
        @overload
        def __call__(self, __other: int) -> Union[int32, int64]: ...
        @overload
        def __call__(self, __other: signedinteger[Any]) -> signedinteger[Any]: ...

    class _SignedIntOp(Protocol[_NBit_co]):  # type: ignore[misc]
        @overload
        def __call__(self, __other: bool) -> signedinteger[_NBit_co]: ...
        @overload
        def __call__(self, __other: int) -> Union[int32, int64]: ...
        @overload
        def __call__(self, __other: float) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(
            self, __other: signedinteger[_NBit_co]
        ) -> signedinteger[_NBit_co]: ...

    class _SignedIntBitOp(Protocol[_NBit_co]):  # type: ignore[misc]
        @overload
        def __call__(self, __other: bool) -> signedinteger[_NBit_co]: ...
        @overload
        def __call__(self, __other: int) -> Union[int32, int64]: ...
        @overload
        def __call__(
            self, __other: signedinteger[_NBit_co]
        ) -> signedinteger[_NBit_co]: ...

    class _FloatOp(Protocol[_NBit_co]):  # type: ignore[misc]
        @overload
        def __call__(self, __other: bool) -> floating[_NBit_co]: ...
        @overload
        def __call__(self, __other: int) -> Union[float32, float64]: ...
        @overload
        def __call__(self, __other: float) -> float64: ...
        @overload
        def __call__(self, __other: complex) -> complex128: ...
        @overload
        def __call__(
            self, __other: Union[integer[_NBit_co], floating[_NBit_co]]
        ) -> floating[_NBit_co]: ...

    class _ComplexOp(Protocol[_NBit_co]):  # type: ignore[misc]
        @overload
        def __call__(self, __other: bool) -> complexfloating[_NBit_co, _NBit_co]: ...
        @overload
        def __call__(self, __other: int) -> Union[complex64, complex128]: ...
        @overload
        def __call__(self, __other: Union[float, complex]) -> complex128: ...
        @overload
        def __call__(
            self,
            __other: Union[
                integer[_NBit_co],
                floating[_NBit_co],
                complexfloating[_NBit_co, _NBit_co],
            ]
        ) -> complexfloating[_NBit_co, _NBit_co]: ...

    class _NumberOp(Protocol):
        def __call__(self, __other: _NumberLike) -> number: ...

else:
    _BoolOp = Any
    _BoolBitOp = Any
    _BoolSub = Any
    _BoolTrueDiv = Any
    _TD64Div = Any
    _IntTrueDiv = Any
    _UnsignedIntOp = Any
    _UnsignedIntBitOp = Any
    _SignedIntOp = Any
    _SignedIntBitOp = Any
    _FloatOp = Any
    _ComplexOp = Any
    _NumberOp = Any
