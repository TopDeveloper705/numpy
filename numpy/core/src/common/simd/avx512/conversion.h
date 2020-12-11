#ifndef NPY_SIMD
    #error "Not a standalone header"
#endif

#ifndef _NPY_SIMD_AVX512_CVT_H
#define _NPY_SIMD_AVX512_CVT_H

// convert mask to integer vectors
#ifdef NPY_HAVE_AVX512BW
    #define npyv_cvt_u8_b8  _mm512_movm_epi8
    #define npyv_cvt_u16_b16 _mm512_movm_epi16
#else
    #define npyv_cvt_u8_b8(BL) BL
    #define npyv_cvt_u16_b16(BL) BL
#endif
#define npyv_cvt_s8_b8  npyv_cvt_u8_b8
#define npyv_cvt_s16_b16 npyv_cvt_u16_b16

#ifdef NPY_HAVE_AVX512DQ
    #define npyv_cvt_u32_b32 _mm512_movm_epi32
    #define npyv_cvt_u64_b64 _mm512_movm_epi64
#else
    #define npyv_cvt_u32_b32(BL) _mm512_maskz_set1_epi32(BL, (int)-1)
    #define npyv_cvt_u64_b64(BL) _mm512_maskz_set1_epi64(BL, (npy_int64)-1)
#endif
#define npyv_cvt_s32_b32 npyv_cvt_u32_b32
#define npyv_cvt_s64_b64 npyv_cvt_u64_b64
#define npyv_cvt_f32_b32(BL) _mm512_castsi512_ps(npyv_cvt_u32_b32(BL))
#define npyv_cvt_f64_b64(BL) _mm512_castsi512_pd(npyv_cvt_u64_b64(BL))

// convert integer vectors to mask
#ifdef NPY_HAVE_AVX512BW
    #define npyv_cvt_b8_u8 _mm512_movepi8_mask
    #define npyv_cvt_b16_u16 _mm512_movepi16_mask
#else
    #define npyv_cvt_b8_u8(A)  A
    #define npyv_cvt_b16_u16(A) A
#endif
#define npyv_cvt_b8_s8  npyv_cvt_b8_u8
#define npyv_cvt_b16_s16 npyv_cvt_b16_u16

#ifdef NPY_HAVE_AVX512DQ
    #define npyv_cvt_b32_u32 _mm512_movepi32_mask
    #define npyv_cvt_b64_u64 _mm512_movepi64_mask
#else
    #define npyv_cvt_b32_u32(A) _mm512_cmpneq_epu32_mask(A, _mm512_setzero_si512())
    #define npyv_cvt_b64_u64(A) _mm512_cmpneq_epu64_mask(A, _mm512_setzero_si512())
#endif
#define npyv_cvt_b32_s32 npyv_cvt_b32_u32
#define npyv_cvt_b64_s64 npyv_cvt_b64_u64
#define npyv_cvt_b32_f32(A) npyv_cvt_b32_u32(_mm512_castps_si512(A))
#define npyv_cvt_b64_f64(A) npyv_cvt_b64_u64(_mm512_castpd_si512(A))

// convert boolean vectors to integer bitfield
NPY_FINLINE npy_uint64 npyv_tobits_b8(npyv_b8 a)
{
#ifdef NPY_HAVE_AVX512BW_MASK
    return (npy_uint64)_cvtmask64_u64(a);
#elif defined(NPY_HAVE_AVX512BW)
    return (npy_uint64)a;
#else
    int mask_lo = _mm256_movemask_epi8(npyv512_lower_si256(a));
    int mask_hi = _mm256_movemask_epi8(npyv512_higher_si256(a));
    return (unsigned)mask_lo | ((npy_uint64)(unsigned)mask_hi << 32);
#endif
}
NPY_FINLINE npy_uint64 npyv_tobits_b16(npyv_b16 a)
{
#ifdef NPY_HAVE_AVX512BW_MASK
    return (npy_uint32)_cvtmask32_u32(a);
#elif defined(NPY_HAVE_AVX512BW)
    return (npy_uint32)a;
#else
    __m256i pack = _mm256_packs_epi16(
        npyv512_lower_si256(a), npyv512_higher_si256(a)
    );
    return (npy_uint32)_mm256_movemask_epi8(_mm256_permute4x64_epi64(pack, _MM_SHUFFLE(3, 1, 2, 0)));
#endif
}
NPY_FINLINE npy_uint64 npyv_tobits_b32(npyv_b32 a)
{ return (npy_uint16)a; }
NPY_FINLINE npy_uint64 npyv_tobits_b64(npyv_b64 a)
{ return (npy_uint8)a; }

#endif // _NPY_SIMD_AVX512_CVT_H
