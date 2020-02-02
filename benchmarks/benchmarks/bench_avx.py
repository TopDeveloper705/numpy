from .common import Benchmark

import numpy as np

avx_ufuncs = ['sqrt',
              'absolute',
              'reciprocal',
              'square',
              'rint',
              'floor',
              'ceil' ,
              'trunc']
stride = [1, 2, 4]
dtype  = ['f', 'd']

class AVX_UFunc(Benchmark):
    params = [avx_ufuncs, stride, dtype]
    param_names = ['avx_based_ufunc', 'stride', 'dtype']
    timeout = 10

    def setup(self, ufuncname, stride, dtype):
        np.seterr(all='ignore')
        try:
            self.f = getattr(np, ufuncname)
        except AttributeError:
            raise NotImplementedError()
        N = 10000
        self.arr = np.ones(stride*N, dtype)

    def time_ufunc(self, ufuncname, stride, dtype):
        self.f(self.arr[::stride])

avx_bfuncs = ['maximum',
              'minimum']

class AVX_BFunc(Benchmark):

    params = [avx_bfuncs, dtype, stride]
    param_names = ['avx_based_bfunc', 'dtype', 'stride']
    timeout = 10

    def setup(self, ufuncname, dtype, stride):
        np.seterr(all='ignore')
        try:
            self.f = getattr(np, ufuncname)
        except AttributeError:
            raise NotImplementedError()
        N = 10000
        self.arr1 = np.array(np.random.rand(stride*N), dtype=dtype)
        self.arr2 = np.array(np.random.rand(stride*N), dtype=dtype)

    def time_ufunc(self, ufuncname, dtype, stride):
        self.f(self.arr1[::stride], self.arr2[::stride])

cmplx_bfuncs = ['add',
                'subtract',
                'multiply',
                'divide']
cmplxstride = [1, 2, 4]
cmplxdtype  = ['F', 'D']

class AVX_cmplx_arithmetic(Benchmark):
    params = [cmplx_bfuncs, cmplxstride, cmplxdtype]
    param_names = ['bfunc', 'stride', 'dtype']
    timeout = 10

    def setup(self, bfuncname, stride, dtype):
        np.seterr(all='ignore')
        try:
            self.f = getattr(np, bfuncname)
        except AttributeError:
            raise NotImplementedError()
        N = 10000
        self.arr1 = np.ones(stride*N, dtype)
        self.arr2 = np.ones(stride*N, dtype)

    def time_ufunc(self, bfuncname, stride, dtype):
        self.f(self.arr1[::stride], self.arr2[::stride])

cmplx_ufuncs = ['reciprocal',
                'absolute',
                'square',
                'conjugate']

class AVX_cmplx_funcs(Benchmark):
    params = [cmplx_ufuncs, cmplxstride, cmplxdtype]
    param_names = ['bfunc', 'stride', 'dtype']
    timeout = 10

    def setup(self, bfuncname, stride, dtype):
        np.seterr(all='ignore')
        try:
            self.f = getattr(np, bfuncname)
        except AttributeError:
            raise NotImplementedError()
        N = 10000
        self.arr1 = np.ones(stride*N, dtype)

    def time_ufunc(self, bfuncname, stride, dtype):
        self.f(self.arr1[::stride])

class Mandelbrot(Benchmark):
    def f(self,z):
        return np.abs(z) < 4.0

    def g(self,z,c):
        return np.sum(np.multiply(z,z) + c)

    def mandelbrot_numpy(self, c, maxiter):
        output = np.zeros(c.shape, np.int)
        z = np.empty(c.shape, np.complex64)
        for it in range(maxiter):
            notdone = self.f(z)
            output[notdone] = it
            z[notdone] = self.g(z[notdone],c[notdone])
        output[output == maxiter-1] = 0
        return output

    def mandelbrot_set(self,xmin,xmax,ymin,ymax,width,height,maxiter):
        r1 = np.linspace(xmin, xmax, width, dtype=np.float32)
        r2 = np.linspace(ymin, ymax, height, dtype=np.float32)
        c = r1 + r2[:,None]*1j
        n3 = self.mandelbrot_numpy(c,maxiter)
        return (r1,r2,n3.T)

    def time_mandel(self):
        self.mandelbrot_set(-0.74877,-0.74872,0.06505,0.06510,1000,1000,2048)
