import sys
from typing import (
    Literal as L,
    List,
    Type,
    Sequence,
    Tuple,
    Union,
    Any,
    TypeVar,
    Iterator,
    overload,
    Callable,
    Protocol,
    SupportsIndex,
    Iterable,
)

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

from numpy import (
    vectorize as vectorize,
    dtype,
    generic,
    floating,
    complexfloating,
    object_,
    _OrderKACF,
)

from numpy.typing import (
    NDArray,
    ArrayLike,
    DTypeLike,
    _ShapeLike,
    _ScalarLike_co,
    _SupportsDType,
    _FiniteNestedSequence,
    _SupportsArray,
    _ArrayLikeComplex_co,
    _ArrayLikeFloat_co,
    _ArrayLikeObject_co,
)

from numpy.core.function_base import (
    add_newdoc as add_newdoc,
)

from numpy.core.multiarray import (
    add_docstring as add_docstring,
    bincount as bincount,
)

from numpy.core.umath import _add_newdoc_ufunc

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_SCT = TypeVar("_SCT", bound=generic)
_ArrayType = TypeVar("_ArrayType", bound=NDArray[Any])

_2Tuple = Tuple[_T, _T]
_ArrayLike = _FiniteNestedSequence[_SupportsArray[dtype[_SCT]]]
_DTypeLike = Union[
    dtype[_SCT],
    Type[_SCT],
    _SupportsDType[dtype[_SCT]],
]

class _TrimZerosSequence(Protocol[_T_co]):
    def __len__(self) -> int: ...
    def __getitem__(self, key: slice, /) -> _T_co: ...
    def __iter__(self) -> Iterator[Any]: ...

class _SupportsWriteFlush(Protocol):
    def write(self, s: str, /) -> object: ...
    def flush(self) -> object: ...

__all__: List[str]

add_newdoc_ufunc = _add_newdoc_ufunc

@overload
def rot90(
    m: _ArrayLike[_SCT],
    k: int = ...,
    axes: Tuple[int, int] = ...,
) -> NDArray[_SCT]: ...
@overload
def rot90(
    m: ArrayLike,
    k: int = ...,
    axes: Tuple[int, int] = ...,
) -> NDArray[Any]: ...

@overload
def flip(m: _SCT, axis: None = ...) -> _SCT: ...
@overload
def flip(m: _ScalarLike_co, axis: None = ...) -> Any: ...
@overload
def flip(m: _ArrayLike[_SCT], axis: None | _ShapeLike = ...) -> NDArray[_SCT]: ...
@overload
def flip(m: ArrayLike, axis: None | _ShapeLike = ...) -> NDArray[Any]: ...

def iterable(y: object) -> TypeGuard[Iterable[Any]]: ...

@overload
def average(
    a: _ArrayLikeFloat_co,
    axis: None = ...,
    weights: None | _ArrayLikeFloat_co= ...,
    returned: L[False] = ...,
) -> floating[Any]: ...
@overload
def average(
    a: _ArrayLikeComplex_co,
    axis: None = ...,
    weights: None | _ArrayLikeComplex_co = ...,
    returned: L[False] = ...,
) -> complexfloating[Any, Any]: ...
@overload
def average(
    a: _ArrayLikeObject_co,
    axis: None = ...,
    weights: None | Any = ...,
    returned: L[False] = ...,
) -> Any: ...
@overload
def average(
    a: _ArrayLikeFloat_co,
    axis: None = ...,
    weights: None | _ArrayLikeFloat_co= ...,
    returned: L[True] = ...,
) -> _2Tuple[floating[Any]]: ...
@overload
def average(
    a: _ArrayLikeComplex_co,
    axis: None = ...,
    weights: None | _ArrayLikeComplex_co = ...,
    returned: L[True] = ...,
) -> _2Tuple[complexfloating[Any, Any]]: ...
@overload
def average(
    a: _ArrayLikeObject_co,
    axis: None = ...,
    weights: None | Any = ...,
    returned: L[True] = ...,
) -> _2Tuple[Any]: ...
@overload
def average(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None | _ShapeLike = ...,
    weights: None | Any = ...,
    returned: L[False] = ...,
) -> Any: ...
@overload
def average(
    a: _ArrayLikeComplex_co | _ArrayLikeObject_co,
    axis: None | _ShapeLike = ...,
    weights: None | Any = ...,
    returned: L[True] = ...,
) -> _2Tuple[Any]: ...

@overload
def asarray_chkfinite(
    a: _ArrayLike[_SCT],
    dtype: None = ...,
    order: _OrderKACF = ...,
) -> NDArray[_SCT]: ...
@overload
def asarray_chkfinite(
    a: object,
    dtype: None = ...,
    order: _OrderKACF = ...,
) -> NDArray[Any]: ...
@overload
def asarray_chkfinite(
    a: Any,
    dtype: _DTypeLike[_SCT],
    order: _OrderKACF = ...,
) -> NDArray[_SCT]: ...
@overload
def asarray_chkfinite(
    a: Any,
    dtype: DTypeLike,
    order: _OrderKACF = ...,
) -> NDArray[Any]: ...

@overload
def piecewise(
    x: _ArrayLike[_SCT],
    condlist: ArrayLike,
    funclist: Sequence[Any | Callable[..., Any]],
    *args: Any,
    **kw: Any,
) -> NDArray[_SCT]: ...
@overload
def piecewise(
    x: ArrayLike,
    condlist: ArrayLike,
    funclist: Sequence[Any | Callable[..., Any]],
    *args: Any,
    **kw: Any,
) -> NDArray[Any]: ...

def select(
    condlist: Sequence[ArrayLike],
    choicelist: Sequence[ArrayLike],
    default: ArrayLike = ...,
) -> NDArray[Any]: ...

@overload
def copy(
    a: _ArrayType,
    order: _OrderKACF,
    subok: L[True],
) -> _ArrayType: ...
@overload
def copy(
    a: _ArrayType,
    order: _OrderKACF = ...,
    *,
    subok: L[True],
) -> _ArrayType: ...
@overload
def copy(
    a: _ArrayLike[_SCT],
    order: _OrderKACF = ...,
    subok: L[False] = ...,
) -> NDArray[_SCT]: ...
@overload
def copy(
    a: ArrayLike,
    order: _OrderKACF = ...,
    subok: L[False] = ...,
) -> NDArray[Any]: ...

def gradient(
    f: ArrayLike,
    *varargs: ArrayLike,
    axis: None | _ShapeLike = ...,
    edge_order: L[1, 2] = ...,
) -> Any: ...

@overload
def diff(
    a: _T,
    n: L[0],
    axis: SupportsIndex = ...,
    prepend: ArrayLike = ...,
    append: ArrayLike = ...,
) -> _T: ...
@overload
def diff(
    a: ArrayLike,
    n: int = ...,
    axis: SupportsIndex = ...,
    prepend: ArrayLike = ...,
    append: ArrayLike = ...,
) -> NDArray[Any]: ...

# TODO
def interp(x, xp, fp, left=..., right=..., period=...): ...

@overload
def angle(z: _ArrayLikeFloat_co, deg: bool = ...) -> floating[Any]: ...
@overload
def angle(z: _ArrayLikeComplex_co, deg: bool = ...) -> complexfloating[Any, Any]: ...
@overload
def angle(z: _ArrayLikeObject_co, deg: bool = ...) -> Any: ...

@overload
def unwrap(
    p: _ArrayLikeFloat_co,
    discont: None | float = ...,
    axis: int = ...,
    *,
    period: float = ...,
) -> NDArray[floating[Any]]: ...
@overload
def unwrap(
    p: _ArrayLikeObject_co,
    discont: None | float = ...,
    axis: int = ...,
    *,
    period: float = ...,
) -> NDArray[object_]: ...

def sort_complex(a: ArrayLike) -> NDArray[complexfloating[Any, Any]]: ...

def trim_zeros(
    filt: _TrimZerosSequence[_T],
    trim: L["f", "b", "fb", "bf"] = ...,
) -> _T: ...

@overload
def extract(condition: ArrayLike, arr: _ArrayLike[_SCT]) -> NDArray[_SCT]: ...
@overload
def extract(condition: ArrayLike, arr: ArrayLike) -> NDArray[Any]: ...

def place(arr: NDArray[Any], mask: ArrayLike, vals: Any) -> None: ...

def disp(
    mesg: object,
    device: None | _SupportsWriteFlush = ...,
    linefeed: bool = ...,
) -> None: ...

def cov(m, y=..., rowvar=..., bias=..., ddof=..., fweights=..., aweights=..., *, dtype=...): ...
def corrcoef(x, y=..., rowvar=..., bias = ..., ddof = ..., *, dtype=...): ...
def blackman(M): ...
def bartlett(M): ...
def hanning(M): ...
def hamming(M): ...
def i0(x): ...
def kaiser(M, beta): ...
def sinc(x): ...
def msort(a): ...
def median(a, axis=..., out=..., overwrite_input=..., keepdims=...): ...
def percentile(a, q, axis=..., out=..., overwrite_input=..., interpolation=..., keepdims=...): ...
def quantile(a, q, axis=..., out=..., overwrite_input=..., interpolation=..., keepdims=...): ...
def trapz(y, x=..., dx=..., axis=...): ...
def meshgrid(*xi, copy=..., sparse=..., indexing=...): ...
def delete(arr, obj, axis=...): ...
def insert(arr, obj, values, axis=...): ...
def append(arr, values, axis=...): ...
def digitize(x, bins, right=...): ...
