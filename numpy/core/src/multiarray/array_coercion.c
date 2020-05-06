#define NPY_NO_DEPRECATED_API NPY_API_VERSION
#define _UMATHMODULE
#define _MULTIARRAYMODULE

#include "numpy/arrayobject.h"

#include "Python.h"
#include "descriptor.h"
#include "convert_datatype.h"
#include "dtypemeta.h"

#include "array_coercion.h"
#include "ctors.h"
#include "common.h"
#include "_datetime.h"
#include "npy_import.h"


/*
 * This file defines helpers for some of the ctors.c functions which
 * create an array from Python sequences and types.
 * When creating an array with ``np.array(...)`` we have to do two main things:
 *
 * 1. Find the exact shape of the resulting array
 * 2. Find the correct dtype of the resulting array.
 *
 * In most cases these two things are can be done in a single processing step.
 * There are in principle three different calls that should be distinguished:
 *
 * 1. The user calls ``np.array(..., dtype=np.dtype("<f8"))``
 * 2. The user calls ``np.array(..., dtype="S")``
 * 3. The user calls ``np.array(...)``
 *
 * In the first case, in principle only the shape needs to be found. In the
 * second case, the DType class (e.g. string) is already known but the DType
 * instance (e.g. length of the string) has to be found.
 * In the last case the DType class needs to be found as well. Note that
 * it is not necessary to find the DType class of the entire array, but
 * the DType class needs to be found for each element before the actual
 * dtype instance can be found.
 *
 * Further, there are a few other things to keep in mind when coercing arrays:
 *
 *   * For UFunc promotion, Python scalars need to be handled specially to
 *     allow value based casting. For this purpose they have a ``bound_value``
 *     slot.
 *   * It is necessary to decide whether or not a sequence is an element.
 *     For example tuples are considered elements for structured dtypes, but
 *     otherwise are considered sequences.
 *     This means that if a dtype is given (either as a class or instance),
 *     it can effect the dimension discovery part.
 *
 * In the initial version of this implementation, it is assumed that dtype
 * discovery can be implemented sufficiently fast, that it is not necessary
 * to create fast paths that only find the correct shape e.g. when
 * ``dtype=np.dtype("f8")`` is given.
 *
 * One design goal in this code is to avoid multiple conversions of nested
 * array like objects and sequences. Thus a cache is created to store sequences
 * for the internal API which in almost all cases will, after allocating the
 * new array, iterate all objects a second time to fill that array.
 */


/*
 * For finding a DType quickly from a type, it is easiest to have a
 * a mapping of pytype -> dtype.
 * Since a DType must know its type, but the type not the DType, we will
 * store the DType as a weak reference. When a reference is dead we can
 * remove the item from the dictionary.
 * A cleanup should probably be done occasionally if (and only if) a large
 * number of type -> DType mappings are added.
 * This assumes that the mapping is a bifurcation DType <-> type
 * (there is exactly one DType for each type and vise versa).
 * If it is not, it is possible for a python type to stay alive unnecessarily.
 */
PyObject *_global_pytype_to_type_dict = NULL;


enum _dtype_discovery_flags {
    IS_RAGGED_ARRAY = 1,
    REACHED_MAXDIMS = 2,
    GAVE_SUBCLASS_WARNING = 4,
    PROMOTION_FAILED = 8,
    DISCOVER_STRINGS_AS_SEQUENCES = 16,
    DISCOVER_TUPLES_AS_ELEMENTS = 32,
};


/**
 * Adds known sequence types to the global type dictionary, note that when
 * a DType is passed in, this lookup may be ignored.
 *
 * @return -1 on error 0 on success
 */
static int
_prime_global_pytype_to_type_dict()
{
    int res;

    /* Add the basic Python sequence types */
    res = PyDict_SetItem(_global_pytype_to_type_dict,
                         (PyObject *)&PyList_Type, Py_None);
    if (res < 0) {
        return -1;
    }
    res = PyDict_SetItem(_global_pytype_to_type_dict,
                         (PyObject *)&PyTuple_Type, Py_None);
    if (res < 0) {
        return -1;
    }
    /* NumPy Arrays are not handled as scalars */
    res = PyDict_SetItem(_global_pytype_to_type_dict,
                         (PyObject *)&PyArray_Type, Py_None);
    if (res < 0) {
        return -1;
    }
    return 0;
}


/**
 * Add a new mapping from a python type to the DType class. This assumes
 * that the DType class is guaranteed to hold on the python type (this
 * assumption is guaranteed).
 * This function replaces ``_typenum_fromtypeobj``.
 */
NPY_NO_EXPORT int
_PyArray_MapPyTypeToDType(
        PyArray_DTypeMeta *DType, PyTypeObject *pytype, npy_bool userdef)
{
    PyObject *Dtype_obj = (PyObject *)DType;

    if (userdef) {
        /*
         * It seems we did not strictly enforce this in the legacy dtype
         * API, but assume that it is always true. Further, this could be
         * relaxed in the future. In particular we should have a new
         * superclass of ``np.generic`` in order to note enforce the array
         * scalar behaviour.
         */
        if (!PyObject_IsSubclass((PyObject *)pytype, (PyObject *)&PyGenericArrType_Type)) {
            PyErr_Format(PyExc_RuntimeError,
                    "currently it is only possible to register a DType "
                    "for scalars deriving from `np.generic`, got '%S'.",
                    (PyObject *)pytype);
            return -1;
        }
    }

    /* Create the global dictionary if it does not exist */
    if (NPY_UNLIKELY(_global_pytype_to_type_dict == NULL)) {
        _global_pytype_to_type_dict = PyDict_New();
        if (_global_pytype_to_type_dict == NULL) {
            return -1;
        }
        if (_prime_global_pytype_to_type_dict() < 0) {
            return -1;
        }
    }

    int res = PyDict_Contains(_global_pytype_to_type_dict, Dtype_obj);
    if (res < 0) {
        return -1;
    }
    else if (res) {
        PyErr_SetString(PyExc_RuntimeError,
                "Can only map one python type to DType.");
        return -1;
    }

    PyObject *weakref = PyWeakref_NewRef(Dtype_obj, NULL);
    if (weakref == NULL) {
        return -1;
    }
    return PyDict_SetItem(_global_pytype_to_type_dict,
            (PyObject *)pytype, weakref);
}


/**
 * Lookup the DType for a registered known python scalar type.
 *
 * @param pytype Python Type to look up
 * @return DType, None if it a known non-scalar, or NULL if an unknown object.
 */
static NPY_INLINE PyArray_DTypeMeta *
discover_dtype_from_pytype(PyTypeObject *pytype)
{
    PyObject *weakref = PyDict_GetItem(
            _global_pytype_to_type_dict, (PyObject *)pytype);

    if (weakref == NULL) {
        /* This should not be possible, since types should be hashable */
        assert(!PyErr_Occurred());
        return NULL;
    }
    if (weakref == Py_None) {
        Py_INCREF(Py_None);
        return (PyArray_DTypeMeta *)Py_None;
    }
    else {
        assert(PyWeakref_CheckRef(weakref));
        PyObject *DType = PyWeakref_GET_OBJECT(weakref);
        if (DType == Py_None) {
            /*
             * The weak reference (and thus the mapping) was invalidated, this
             * should not typically happen, but if it does delete it from the
             * mapping.
             */
            int res = PyDict_DelItem(
                    _global_pytype_to_type_dict, (PyObject *)pytype);
            weakref = NULL;
            if (res < 0) {
                return NULL;
            }
        }
        Py_INCREF(DType);
        assert(PyObject_IsInstance(DType, (PyObject *)&PyArrayDTypeMeta_Type) == 1);
        return (PyArray_DTypeMeta *)DType;
    }
}


/**
 * Find the correct DType class for the given python type.
 *
 * @param obj The python object, mainly type(pyobj) is used, the object
 *        is passed to reuse existing code at this time only.
 * @param flags Flags used to know if warnings were already given.
 * @param fixed_DType if not NULL, will be checked first for whether or not
 *        it can/wants to handle the (possible) scalar value.
 * @return New reference to either a DType class, Py_None, or NULL
 */
static PyArray_DTypeMeta *
discover_dtype_from_pyobject(
        PyObject *obj, enum _dtype_discovery_flags *flags,
        PyArray_DTypeMeta *fixed_DType)
{
    if (fixed_DType != NULL) {
        /*
         * Let the given DType handle the discovery, there are three possible
         * result cases here:
         *   1. A descr, which is ready for promotion. (Correct DType)
         *   2. None to indicate that this should be treated as a sequence.
         *   3. NotImplemented to see if this is a known scalar type and
         *      use normal casting logic instead. This can be slow especially
         *      for parametric types.
         *   4. NULL in case of an error.
         */
        if ((Py_TYPE(obj) == fixed_DType->scalar_type) ||
            (fixed_DType->is_known_scalar != NULL &&
             fixed_DType->is_known_scalar(fixed_DType, obj))) {
            /*
             * There are some corner cases, where we want to make sure a
             * sequence is considered a scalar. In particular tuples with
             * structured/void dtype and strings.
             * The type check is simply a fast (and simple default) path
             * which could capture some special dtypes, such as polynomials.
             */
            Py_INCREF(fixed_DType);
            return fixed_DType;
        }
    }

    PyArray_DTypeMeta *DType = discover_dtype_from_pytype(Py_TYPE(obj));
    if (DType != NULL) {
        return DType;
    }
    /*
     * At this point we have not found a clear mapping, but mainly for
     * backward compatibility we have to make some further attempts at
     * interpreting the input correctly.
     */
    PyArray_Descr *legacy_descr;
    if (PyArray_IsScalar(obj, Generic)) {
        legacy_descr = PyArray_DescrFromScalar(obj);
        if (legacy_descr == NULL) {
            return NULL;
        }
    }
    else if (PyBytes_Check(obj)) {
        legacy_descr = PyArray_DescrFromType(NPY_BYTE);
    }
    else if (PyUnicode_Check(obj)) {
        legacy_descr = PyArray_DescrFromType(NPY_UNICODE);
    }
    else {
        legacy_descr = _array_find_python_scalar_type(obj);
    }

    if (legacy_descr != NULL) {
        DType = (PyArray_DTypeMeta *)Py_TYPE(legacy_descr);
        Py_INCREF(DType);
        Py_DECREF(legacy_descr);
        // TODO: Do not add new warning for now...
        if (0 && !((*flags) & GAVE_SUBCLASS_WARNING)) {
            if (DEPRECATE_FUTUREWARNING(
                    "in the future NumPy will not automatically find the "
                    "dtype for subclasses of scalars known to NumPy (i.e. "
                    "python types). Use the appropriate `dtype=...` to create "
                    "this array. This will use the `object` dtype or raise "
                    "an error in the future.") < 0) {
                return NULL;
            }
            *flags |= GAVE_SUBCLASS_WARNING;
        }
        return DType;
    }

    Py_INCREF(Py_None);
    return (PyArray_DTypeMeta *)Py_None;
}


static PyArray_Descr *
cast_descriptor_to_fixed_dtype(
        PyArray_Descr *descr, PyArray_DTypeMeta *fixed_DType)
{
    if (fixed_DType == NULL) {
        /* Nothing to do, we only need to promote the new dtype */
        Py_INCREF(descr);
        return descr;
    }

    if (!fixed_DType->parametric) {
        /*
         * Don't actually do anything, the default is always the result
         * of any cast.
         */
        return fixed_DType->default_descr(fixed_DType);
    }
    if (PyObject_IsInstance((PyObject *)descr, (PyObject *)fixed_DType)) {
        Py_INCREF(descr);
        return descr;
    }
    /*
     * TODO: When this is implemented for all dtypes, the special cases
     *       can be removed...
     */
    if (fixed_DType->legacy && fixed_DType->parametric) {
        /* Fallback to the old AdaptFlexibleDType logic for now */
        PyArray_Descr *flex_dtype = PyArray_DescrFromType(fixed_DType->type_num);
        return PyArray_AdaptFlexibleDType(NULL, descr, flex_dtype);
    }

    PyErr_SetString(PyExc_NotImplementedError,
            "Must use casting to find the correct dtype, this is "
            "not yet implemented, oh noes! "
            "(It should not be possible to hit this code currently!)");
    return NULL;
}


/**
 * Discover the correct descriptor from a known DType class and scalar.
 * If the fixed DType can discover a dtype instance/descr all is fine,
 * if it cannot and DType is used instead, a cast will have to be tried.
 *
 * @param fixed_DType A user provided fixed DType, can be NULL
 * @param DType A discovered DType (by discover_dtype_from_pyobject);
 *              This can be identical to `fixed_DType`, if it obj is a
 *              known scalar. Can be `NULL` indicating no known type.
 * @param obj The Python scalar object. At the time of calling this function
 *            it must be known that `obj` should represent a scalar.
 */
static NPY_INLINE PyArray_Descr *
find_scalar_descriptor(
        PyArray_DTypeMeta *fixed_DType, PyArray_DTypeMeta *DType,
        PyObject *obj, PyArray_Descr *requested_descr)
{
    PyArray_Descr *descr;
    const char *bad_dtype_msg = (
            "DType %R was unable to handle its own scalar type. "
            "This is an error in the DType's implementation.");

    if (requested_descr != NULL) {
        Py_INCREF(requested_descr);
        return requested_descr;
    }

    if (fixed_DType != NULL) {
        /* always give the fixed dtype a first chance */
        descr = fixed_DType->discover_descr_from_pyobject(fixed_DType, obj);
        if (descr == NULL) {
            return NULL;
        }
        if (descr != (PyArray_Descr *)Py_NotImplemented) {
            return descr;
        }
        /*
         * The DType is unable to provide a descr. A non-parametric DType
         * must always just return its canonical instance, though.
         * But a parametric one may not be able to handle certain types which
         * are known scalars (of another DType). And we may still know how
         * to do the cast. For example, a datetime64 may not be able to
         * guess the unit for a user-implemented datetime scalar.
         */
        // TODO: Ensure the parametric check is documented in NEP (at least).
        if (DType == fixed_DType) {
            PyErr_Format(PyExc_RuntimeError, bad_dtype_msg, fixed_DType);
            return NULL;
        }
    }

    if (DType == NULL) {
        /*
         * Only a generic python object can be used at this point since
         * this is not a known scalar type.
         */
        if (fixed_DType != NULL) {
            PyErr_Format(PyExc_TypeError,
                    "unable to represent the object %(50)R using the "
                    "DType %R.", obj, fixed_DType);
            return NULL;
        }
        /* This is the generic fall-back to object path... */
        return PyArray_DescrNewFromType(NPY_OBJECT);
    }

    /* Try with the discovered DType */
    descr = DType->discover_descr_from_pyobject(DType, obj);
    if (descr == NULL) {
        return NULL;
    }
    if (descr == (PyArray_Descr *)Py_NotImplemented) {
        /*
         * If the DType was discovered, it must be able to handle the scalar
         * object here, or is considered buggy.
         */
        PyErr_Format(PyExc_RuntimeError, bad_dtype_msg, DType);
        return NULL;
    }
    if (fixed_DType == NULL) {
        return descr;
    }

    Py_SETREF(descr, cast_descriptor_to_fixed_dtype(descr, fixed_DType));
    return descr;
}


static int
update_shape(int curr_ndim, int *max_ndim,
             npy_intp out_shape[NPY_MAXDIMS], int new_ndim,
             const npy_intp new_shape[NPY_MAXDIMS], npy_bool sequence)
{
    int success = 0;  /* unsuccessful if array is ragged */
    if (curr_ndim + new_ndim > *max_ndim) {
        success = -1;
        /* Only update check as many dims as possible, max_ndim is unchanged */
        new_ndim = *max_ndim - curr_ndim;
    }
    else if (!sequence && (*max_ndim != curr_ndim + new_ndim)) {
        /*
         * Sequences do not update max_ndim, otherwise shrink and check.
         * This is depth first, so if it is already set, `out_shape` is filled.
         */
        *max_ndim = curr_ndim + new_ndim;
        /* If a shape was already set, this is also ragged */
        if (out_shape[*max_ndim] >= 0) {
            success = -1;
        }
    }
    for (int i = 0; i < new_ndim; i++) {
        npy_intp curr_dim = out_shape[curr_ndim + i];
        npy_intp new_dim = new_shape[i];

        if (curr_dim == -1) {
            out_shape[curr_ndim + i] = new_dim;
        }
        else if (new_dim != curr_dim) {
            /* The array is ragged, and this dimension is unusable already */
            success = -1;
            if (!sequence) {
                /* Remove dimensions that we cannot use: */
                *max_ndim -= new_ndim + i;
            }
            else {
                assert(i == 0);
                /* max_ndim is usually not updated for sequences, so set now: */
                *max_ndim = curr_ndim;
            }
            break;
        }
    }
    return success;
}


NPY_NO_EXPORT int
npy_new_coercion_cache(
        PyObject *converted_obj, PyObject *arr_or_sequence, npy_bool sequence,
        coercion_cache_obj ***next_ptr)
{
    coercion_cache_obj *cache = PyArray_malloc(sizeof(coercion_cache_obj));
    if (cache == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    cache->converted_obj = converted_obj;
    Py_INCREF(arr_or_sequence);
    cache->arr_or_sequence = arr_or_sequence;
    cache->sequence = sequence;
    cache->next = NULL;
    **next_ptr = cache;
    *next_ptr = &(cache->next);
    return 0;
}


NPY_NO_EXPORT void
npy_free_coercion_cache(coercion_cache_obj *next) {
    /* We only need to check from the last used cache pos */
    while (next != NULL) {
        coercion_cache_obj *current = next;
        next = current->next;

        Py_DECREF(current->arr_or_sequence);
        PyArray_free(current);
    }
}


/**
 * Do the promotion step and possible casting. This function should
 * never be called if a descriptor was requested. In that case the output
 * dtype is not of importance, so we must not risk promotion errors.
 *
 * @param out_descr The current descriptor.
 * @param descr The newly found descriptor to promote with
 * @param flags dtype discover flags to signal failed promotion.
 * @return -1 on error, 0 on success.
 */
static int
handle_promotion(PyArray_Descr **out_descr, PyArray_Descr *descr,
        PyArray_Descr *requested_descr, enum _dtype_discovery_flags *flags)
{
    if (requested_descr != NULL) {
        /*
         * If the user fixed a descriptor, do not promote, this will just
         * error during assignment if necessary.
         */
        return 0;
    }
    if (*out_descr == NULL) {
        Py_INCREF(descr);
        *out_descr = descr;
        return 0;
    }
    // TODO: Will have to take care of the retry-with-string logic for now :(
    PyArray_Descr *new_descr = PyArray_PromoteTypes(*out_descr, descr);
    if (new_descr == NULL) {
        PyErr_Clear();
        *flags |= PROMOTION_FAILED;
        /* Continue with object, since we may need the dimensionality */
        new_descr = PyArray_DescrFromType(NPY_OBJECT);
    }
    Py_SETREF(*out_descr, new_descr);
    return 0;
}


/**
 * Discover the dtype and shape for a potentially nested sequence of scalars.
 * Note that in the ufunc machinery, when value based casting is desired it
 * is necessary to first check for the scalar case.
 *
 * @param obj The python object or nested sequence to convert
 * @param max_dims The maximum number of dimensions.
 * @param curr_dims The current number of dimensions (depth in the recursion)
 * @param out_shape The discovered output shape, will be filled
 * @param coercion_cache The coercion cache object to use.
 * @param DType the DType class that should be used, or NULL, if not provided.
 * @param requested_descr The dtype instance passed in by the user, this is
 *        passed to array-likes, and otherwise prevents any form of promotion
 *        (to avoid errors).
 * @param flags used signal that this is a ragged array, used internally and
 *        can be expanded if necessary.
 */
int handle_scalar(
        PyObject *obj, int curr_dims, int *max_dims,
        PyArray_Descr **out_descr, npy_intp *out_shape,
        PyArray_DTypeMeta *fixed_DType, PyArray_Descr *requested_descr,
        enum _dtype_discovery_flags *flags,
        PyArray_DTypeMeta *DType, PyArray_Descr *descr)
{
    /* This is a scalar, so find the descriptor */
    descr = find_scalar_descriptor(fixed_DType, DType, obj, requested_descr);
    if (descr == NULL) {
        return -1;
    }
    if (update_shape(curr_dims, max_dims, out_shape, 0, NULL, NPY_FALSE) < 0) {
        *flags |= IS_RAGGED_ARRAY;
        Py_XSETREF(*out_descr, PyArray_DescrFromType(NPY_OBJECT));
        return *max_dims;
    }
    if (handle_promotion(out_descr, descr, requested_descr, flags) < 0) {
        return -1;
    }
    Py_DECREF(descr);
    return *max_dims;
}


NPY_NO_EXPORT int
PyArray_DiscoverDTypeAndShape_Recursive(
        PyObject *obj, int curr_dims, int max_dims, PyArray_Descr**out_descr,
        npy_intp out_shape[NPY_MAXDIMS],
        coercion_cache_obj ***coercion_cache_tail_ptr,
        PyArray_DTypeMeta *fixed_DType, PyArray_Descr *requested_descr,
        enum _dtype_discovery_flags *flags)
{
    PyArrayObject *arr = NULL;
    PyObject *seq;

    /*
     * The first step is to find the DType class if it was not provided,
     * alternatively we have to find out that this is not a scalar at all
     * (which could fail and lead us to `object` dtype).
     */
    PyArray_DTypeMeta *DType = NULL;
    PyArray_Descr *descr = NULL;

    if (NPY_UNLIKELY(*flags & DISCOVER_STRINGS_AS_SEQUENCES)) {
        /*
         * We currently support that bytes/strings are considered sequences,
         * if the dtype is np.dtype('c'), this should be deprecated probably,
         * but requires hacks right now.
         * TODO: Consider passing this as a flag, as it was before?
         */
        if (PyBytes_Check(obj) && PyBytes_Size(obj) != 1) {
            goto force_sequence_due_to_char_dtype;
        }
        else if (PyUnicode_Check(obj) && PyUnicode_GetLength(obj) != 1) {
            goto force_sequence_due_to_char_dtype;
        }
    }

    /* If this is a known scalar, find the corresponding DType class */
    DType = discover_dtype_from_pyobject(obj, flags, fixed_DType);
    if (DType == NULL) {
        return -1;
    }
    if (DType != (PyArray_DTypeMeta *)Py_None) {
        max_dims = handle_scalar(
                obj, curr_dims, &max_dims, out_descr, out_shape, fixed_DType,
                requested_descr, flags, DType, descr);
        Py_DECREF(DType);
        return max_dims;
    }
    Py_DECREF(DType);

    /*
     * At this point we expect to find either a sequence, or an array-like.
     * Although it is still possible that this fails and we have to use
     * `object`.
     */
    if (PyArray_Check(obj)) {
        arr = (PyArrayObject *)obj;
        Py_INCREF(arr);
    }
    else {
        arr = (PyArrayObject *)_array_from_array_like(obj,
                requested_descr, 0, NULL);
        if (arr == NULL) {
            return -1;
        }
        else if (arr == (PyArrayObject *)Py_NotImplemented) {
            Py_DECREF(arr);
            arr = NULL;
        }
    }
    if (arr) {
        /*
         * This is an array object which will be added to the cache, keeps
         * the a reference to the array alive.
         */
        if (npy_new_coercion_cache(obj, (PyObject *)arr, 0, coercion_cache_tail_ptr) < 0) {
            Py_DECREF(arr);
            return -1;
        }
        Py_DECREF(arr);  /* the cache holds on for us */

        if (update_shape(curr_dims, &max_dims, out_shape,
                PyArray_NDIM(arr), PyArray_SHAPE(arr), NPY_FALSE) < 0) {
            *flags |= IS_RAGGED_ARRAY;
            return max_dims;
        }

        if (PyArray_DESCR(arr)->type_num == NPY_OBJECT &&
                    fixed_DType != NULL && fixed_DType->parametric &&
                    requested_descr == NULL) {
            /*
             * We have one special case, if (and only if) the input array is of
             * object DType and the dtype is not fixed already but parametric.
             * Then, we allow inspection of all elements, treating them as
             * elements. We do this recursively, so nested 0-D arrays can work,
             * but nested higher dimensional arrays will lead to an error.
             */
            assert(fixed_DType->type_num != NPY_OBJECT);

            PyArrayIterObject *iter;
            iter = (PyArrayIterObject *)PyArray_IterNew((PyObject *)arr);
            if (iter == NULL) {
                return -1;
            }
            while (iter->index < iter->size) {
                PyObject *elem = (*(PyObject **)(iter->dataptr));
                if (elem == NULL) {
                    assert(0);  /* We really may want to stop supporting this */
                    elem = Py_None;
                }
                DType = discover_dtype_from_pyobject(elem, flags, fixed_DType);
                if (DType == (PyArray_DTypeMeta *)Py_None) {
                    Py_SETREF(DType, NULL);
                }
                int flat_max_dims = 0;
                if (handle_scalar(elem, 0, &flat_max_dims, out_descr,
                        NULL, DType, NULL, flags, fixed_DType, NULL) < 0) {
                    Py_DECREF(iter);
                    Py_XDECREF(DType);
                    return -1;
                }
                Py_XDECREF(DType);
                PyArray_ITER_NEXT(iter);
            }
            Py_DECREF(iter);
        }
        else if (requested_descr == NULL) {
            /*
             * If this is not an object array figure out the dtype cast,
             * or simply use the returned DType.
             */
            descr = cast_descriptor_to_fixed_dtype(
                         PyArray_DESCR(arr), fixed_DType);
            if (descr == NULL) {
                return -1;
            }
            if (handle_promotion(out_descr, descr, requested_descr, flags) < 0) {
                Py_DECREF(descr);
                return -1;
            }
            Py_DECREF(descr);
        }
        return max_dims;
    }

    /*
     * The last step is to assume the input should be handled as a sequence
     * and to handle it recursively. That is, unless we have hit the
     * dimension limit.
     */
    npy_bool is_sequence = (PySequence_Check(obj) && PySequence_Size(obj) >= 0);
    if (NPY_UNLIKELY(*flags & DISCOVER_TUPLES_AS_ELEMENTS) &&
            PyTuple_Check(obj)) {
        is_sequence = NPY_FALSE;
    }
    if (curr_dims == max_dims || !is_sequence) {
        /* Clear any PySequence_Size error which would corrupts further calls */
        PyErr_Clear();
        max_dims = handle_scalar(
                obj, curr_dims, &max_dims, out_descr, out_shape, fixed_DType,
                requested_descr, flags, NULL, descr);
        if (is_sequence) {
            /* This may be ragged (if maxdims is not original), or too deep */
            *flags |= REACHED_MAXDIMS;
        }
        return max_dims;
    }
    /* If we stop supporting bytes/str subclasses, more may be required here: */
    assert(!PyBytes_Check(obj) && !PyUnicode_Check(obj));

  force_sequence_due_to_char_dtype:

    /* Ensure we have a sequence (required for PyPy) */
    seq = PySequence_Fast(obj, "Could not convert object to sequence");
    if (seq == NULL) {
        /*
         * Specifically do not fail on things that look like a dictionary,
         * instead treat them as scalar.
         */
        if (PyErr_ExceptionMatches(PyExc_KeyError)) {
            PyErr_Clear();
            max_dims = handle_scalar(
                    obj, curr_dims, &max_dims, out_descr, out_shape, fixed_DType,
                    requested_descr, flags, NULL, descr);
            return max_dims;
        }
        return -1;
    }
    if (npy_new_coercion_cache(obj, seq, 1, coercion_cache_tail_ptr) < 0) {
        Py_DECREF(seq);
        return -1;
    }
    Py_DECREF(seq);  /* the cache holds on for us */

    npy_intp size = PySequence_Fast_GET_SIZE(seq);
    PyObject **objects = PySequence_Fast_ITEMS(seq);

    if (update_shape(curr_dims, &max_dims,
                     out_shape, 1, &size, NPY_TRUE) < 0) {
        /* But do update, if there this is a ragged case */
        *flags |= IS_RAGGED_ARRAY;
        return max_dims;
    }
    if (size == 0) {
        /* If the sequence is empty, there are no more dimensions */
        return curr_dims+1;
    }

    /* Recursive call for each sequence item */
    for (Py_ssize_t i = 0; i < size; i++) {
        max_dims = PyArray_DiscoverDTypeAndShape_Recursive(
                objects[i], curr_dims + 1, max_dims,
                out_descr, out_shape, coercion_cache_tail_ptr, fixed_DType,
                requested_descr, flags);

        if (max_dims < 0) {
            return -1;
        }
    }
    return max_dims;
}


/**
 * Check the descriptor is a legacy "flexible" DType instance, this is
 * an instance which is (normally) not attached to an array, such as a string
 * of length 0 or a datetime with no unit.
 * These should be largely deprecated, and represent only the DType class
 * for most `dtype` parameters.
 *
 * TODO: This function should eventually recieve a deprecation warning and
 *       be removed.
 *
 * @param descr
 * @return 1 if this is not a concrete dtype instance 0 otherwise
 */
static int
descr_is_legacy_parametric_instance(PyArray_Descr *descr)
{
    if (PyDataType_ISUNSIZED(descr)) {
        return 1;
    }
    /* Flexible descr with generic time unit (which can be adapted) */
    if (PyDataType_ISDATETIME(descr)) {
        PyArray_DatetimeMetaData *meta;
        meta = get_datetime_metadata_from_dtype(descr);
        if (meta->base == NPY_FR_GENERIC) {
            return 1;
        }
    }
    return 0;
}


/**
 * Finds the DType and shape of an arbitrary nested sequence. This is the
 * general purpose function to find the parameters of the array (but not
 * the array itself) as returned by `np.array()`
 *
 * @param obj Scalar or nested sequences.
 * @param max_dims Maximum number of dimensions (after this scalars are forced)
 * @param out_shape Will be filled with the output shape (more than the actual
 *        shape may be written).
 * @param coercion_cache NULL initialized reference to a cache pointer.
 *        May be set to the first coercion_cache, and has to be freed using
 *        npy_free_coercion_cache.
 * @param fixed_DType A user provided fixed DType class.
 * @param requested_descr A user provided fixed descriptor. This is always
 *        returned as the discovered descriptor, but currently only used
 *        for the ``__array__`` protocol.
 * @param out_descr The discovered output descriptor.
 * @return dimensions of the discovered object or -1 on error.
 */
NPY_NO_EXPORT int
PyArray_DiscoverDTypeAndShape(
        PyObject *obj, int max_dims,
        npy_intp out_shape[NPY_MAXDIMS],
        coercion_cache_obj **coercion_cache,
        PyArray_DTypeMeta *fixed_DType, PyArray_Descr *requested_descr,
        PyArray_Descr **out_descr)
{
    *out_descr = NULL;
    *coercion_cache = NULL;
    for (int i = 0; i < max_dims; i++) {
        out_shape[i] = -1;
    }

    /* Validate input of requested descriptor and DType */
    if (fixed_DType != NULL) {
        assert(PyObject_IsInstance(
                (PyObject *)fixed_DType, (PyObject *)&PyArrayDTypeMeta_Type));
    }
    if (requested_descr != NULL) {
        assert(!descr_is_legacy_parametric_instance(requested_descr));
        assert(fixed_DType == NPY_DTYPE(requested_descr));
    }

    /*
     * Call the recursive function, the setup for this may need expanding
     * to handle caching better.
     */
    enum _dtype_discovery_flags flags = 0;

    if (requested_descr != NULL) {
        if (requested_descr->type_num == NPY_STRING &&
                requested_descr->type == 'c') {
            /* Character dtype variation of string (should be deprecated...) */
            flags |= DISCOVER_STRINGS_AS_SEQUENCES;
        }
        else if (requested_descr->type_num == NPY_VOID &&
                    (requested_descr->names || requested_descr->subarray))  {
            /* Void is a chimera, in that it may or may not be structured... */
            flags |= DISCOVER_TUPLES_AS_ELEMENTS;
        }
    }

    int ndim = PyArray_DiscoverDTypeAndShape_Recursive(
            obj, 0, max_dims, out_descr, out_shape, &coercion_cache,
            fixed_DType, requested_descr, &flags);
    if (ndim < 0) {
        goto fail;
    }

    if (flags & IS_RAGGED_ARRAY || (
            /* if maxdims is not reached, but flagged this must be ragged */
            flags & REACHED_MAXDIMS && ndim < max_dims)) {
        if (fixed_DType == NULL) {
            static PyObject *visibleDeprecationWarning = NULL;
            npy_cache_import(
                    "numpy", "VisibleDeprecationWarning",
                    &visibleDeprecationWarning);
            if (visibleDeprecationWarning == NULL) {
                goto fail;
            }
            /* NumPy 1.19, 2019-11-01 */
            /* NumPy 1.20, warning is also given if dimension limit is hit */
            if (PyErr_WarnEx(visibleDeprecationWarning,
                    "Creating an ndarray from ragged nested sequences (which "
                    "is a list-or-tuple of lists-or-tuples-or ndarrays with "
                    "different lengths or shapes) is deprecated. If you "
                    "meant to do this, you must specify 'dtype=object' "
                    "when creating the ndarray.", 1) < 0) {
                goto fail;
            }
            Py_XSETREF(*out_descr, PyArray_DescrNewFromType(NPY_OBJECT));
        }
        else if (fixed_DType->type_num != NPY_OBJECT) {
            /* Only object DType supports ragged cases unify error */
            PyErr_SetString(PyExc_ValueError,
                    "setting an array element with a sequence");
            goto fail;
        }
    }
    /* We could check here for max-ndims being reached as well */

    if (requested_descr != NULL) {
        /* The user had given a specific one, we could sanity check, but... */
        Py_INCREF(requested_descr);
        Py_XSETREF(*out_descr, requested_descr);
    }
    else if (*out_descr == NULL) {
        /*
         * When the object contained no items, we have to use the default.
         * We do this afterwards, to not cause promotion when there is only
         * a single element.
         */
        // TODO: This may be a tiny, unsubstantial behaviour change.
        if (fixed_DType != NULL) {
            if (fixed_DType->default_descr == NULL) {
                Py_INCREF(fixed_DType->singleton);
                *out_descr = fixed_DType->singleton;
            }
            else {
                *out_descr = fixed_DType->default_descr(fixed_DType);
                if (*out_descr == NULL) {
                    goto fail;
                }
            }
        }
        else {
            *out_descr = PyArray_DescrFromType(NPY_DEFAULT_TYPE);
        }
    }
    return ndim;

  fail:
    npy_free_coercion_cache(*coercion_cache);
    *coercion_cache = NULL;
    Py_XSETREF(*out_descr, NULL);
    return -1;
}


/**
 * Given either a DType instance or class, (or legacy flexible instance),
 * ands sets output dtype instance and DType class. Both results may be
 * NULL, but if `out_descr` is set `out_DType` will always be the
 * corresponding class.
 *
 * @param dtype
 * @param out_descr
 * @param out_DType
 * @return
 */
NPY_NO_EXPORT int
PyArray_ExtractDTypeAndDescriptor(PyObject *dtype,
        PyArray_Descr **out_descr, PyArray_DTypeMeta **out_DType)
{
    *out_DType = NULL;
    *out_descr = NULL;

    if (dtype != NULL) {
        if (PyObject_IsInstance(dtype, (PyObject *)&PyArrayDTypeMeta_Type)) {
            assert(dtype != (PyObject * )&PyArrayDescr_Type);  /* not np.dtype */
            *out_DType = (PyArray_DTypeMeta *)dtype;
            Py_INCREF(*out_DType);
        }
        else if (PyObject_IsInstance((PyObject *)Py_TYPE(dtype),
                    (PyObject *)&PyArrayDTypeMeta_Type)) {
            *out_DType = NPY_DTYPE(dtype);
            Py_INCREF(*out_DType);
            if (!descr_is_legacy_parametric_instance((PyArray_Descr *)dtype)) {
                *out_descr = (PyArray_Descr *)dtype;
                Py_INCREF(*out_descr);
            }
        }
        else {
            // TODO: Should not allow known scalar type in this function!
            //       at least not within PyArray_FromAny usage!
            /* Try to interpret it as a known scalar type */
            *out_DType = discover_dtype_from_pytype((PyTypeObject *)dtype);
            if (*out_DType == (PyArray_DTypeMeta *)Py_None) {
                Py_SETREF(*out_DType, NULL);
            }
            if (*out_DType == NULL) {
                PyErr_SetString(PyExc_TypeError,
                        "dtype parameter must be a DType instance or class.");
                return -1;
            }
        }
    }
    return 0;
}


NPY_NO_EXPORT PyObject *
_discover_array_parameters(PyObject *NPY_UNUSED(self),
                           PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"obj", "dtype", NULL};

    PyObject *obj;
    PyObject *dtype = NULL;
    PyArray_Descr *fixed_descriptor = NULL;
    PyArray_DTypeMeta *fixed_DType = NULL;
    npy_intp shape[NPY_MAXDIMS];

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, "O|O:_discover_array_parameters", kwlist,
            &obj, &dtype)) {
        return NULL;
    }

    if (PyArray_ExtractDTypeAndDescriptor(dtype,
            &fixed_descriptor, &fixed_DType) < 0) {
        return NULL;
    }

    coercion_cache_obj *coercion_cache;
    PyArray_Descr *res = NULL;
    int ndim = PyArray_DiscoverDTypeAndShape(
            obj, NPY_MAXDIMS, shape,
            &coercion_cache,
            fixed_DType, fixed_descriptor, &res);
    npy_free_coercion_cache(coercion_cache);

    if (ndim < 0) {
        return NULL;
    }
    PyObject *shape_tuple = PyArray_IntTupleFromIntp(ndim, shape);
    if (shape_tuple == NULL) {
        return NULL;
    }

    return PyTuple_Pack(2, (PyObject *)res, shape_tuple);
}
