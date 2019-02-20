#ifndef _NPY_ARRAYDESCR_H_
#define _NPY_ARRAYDESCR_H_

NPY_NO_EXPORT PyObject *arraydescr_protocol_typestr_get(PyArray_Descr *);
NPY_NO_EXPORT PyObject *arraydescr_protocol_descr_get(PyArray_Descr *self);

NPY_NO_EXPORT PyObject *
array_set_typeDict(PyObject *NPY_UNUSED(ignored), PyObject *args);

int
_arraydescr_from_dtype_attr(PyObject *obj, PyArray_Descr **newdescr);


NPY_NO_EXPORT int
is_dtype_struct_simple_unaligned_layout(PyArray_Descr *dtype);

extern NPY_NO_EXPORT char *_datetime_strings[];

#endif
