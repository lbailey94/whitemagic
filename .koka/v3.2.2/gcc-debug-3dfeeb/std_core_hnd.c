// Koka generated module: std/core/hnd, koka version: 3.2.2, platform: 64-bit
#include "std_core_hnd.h"
/*---------------------------------------------------------------------------
  Copyright 2020-2021, Microsoft Research, Daan Leijen.

  This is free software; you can redistribute it and/or modify it under the
  terms of the Apache License, Version 2.0. A copy of the License can be
  found in the LICENSE file at the root of this distribution.
---------------------------------------------------------------------------*/
/*
typedef datatype_t kk_std_core_hnd__ev;
struct kk_std_core_hnd_Ev {
  kk_std_core_hnd__htag htag;
  kk_box_t hnd;
  // kk_cfc_t cfc;  // control flow context
  kk_std_core_hnd__evv hevv;
  kk_std_core_hnd__marker marker;
};
*/


// Note. We no longer support cfc for `evv_is_affine` in the C backend since we always use context paths now.
//
// typedef int32_t kk_cfc_t;

// static kk_cfc_t kk_handler_cfc_borrow( kk_box_t h, kk_context_t* ctx ) {
//   kk_box_t b = kk_block_field(kk_ptr_unbox(h,ctx),0);  // first field of the handler is the cfc
//   return kk_integer_clamp32_borrow(kk_integer_unbox(b,ctx),ctx);
// }


static kk_evv_vector_t kk_evv_vector_alloc(kk_ssize_t length, kk_context_t* ctx) {
  kk_assert_internal(length>=0);
  kk_evv_vector_t v = (kk_evv_vector_t)kk_block_alloc(kk_ssizeof(struct kk_evv_vector_s) + (length-1)*kk_ssizeof(kk_std_core_hnd__ev_t), length, KK_TAG_EVV_VECTOR, ctx);
  // v->cfc = kk_integer_from_int32(cfc,ctx);
  return v;
}

static kk_std_core_hnd__ev* kk_evv_vector_buf(kk_evv_vector_t vec, kk_ssize_t* len) {
  if (len != NULL) { *len = kk_block_scan_fsize(&vec->_block); }
  return &vec->vec[0];
}

static kk_std_core_hnd__ev* kk_evv_as_vec(kk_evv_t evv, kk_ssize_t* len, kk_std_core_hnd__ev* single, kk_context_t* ctx) {
  if (kk_evv_is_vector(evv,ctx)) {
    kk_evv_vector_t vec = kk_evv_as_vector(evv,ctx);
    *len = kk_block_scan_fsize(&vec->_block);
    return &vec->vec[0];
  }
  else {
    // single evidence
    *single = kk_evv_as_ev(evv,ctx);
    *len = 1;
    return single;
  }
}

// kk_std_core_hnd__ev kk_ev_none(kk_context_t* ctx) {
//   static kk_std_core_hnd__ev ev_none_singleton = { kk_datatype_null_init };
//   if (kk_datatype_is_null(ev_none_singleton)) {
//     ev_none_singleton = kk_std_core_hnd__new_Ev(
//       kk_reuse_null,
//       0, // cpath
//       kk_std_core_hnd__new_Htag(kk_string_empty(),ctx), // tag ""
//       0,                                                // marker 0
//       kk_box_null(),                                    // no handler
//       // -1,                                               // bot
//       kk_evv_empty(ctx),
//       ctx
//     );
//   }
//   return kk_std_core_hnd__ev_dup(ev_none_singleton,ctx);
// }


kk_ssize_t kk_evv_index( struct kk_std_core_hnd_Htag htag, kk_context_t* ctx ) {
  // todo: drop htag?
  kk_ssize_t len;
  kk_std_core_hnd__ev single;
  kk_std_core_hnd__ev* vec = kk_evv_as_vec(ctx->evv,&len,&single,ctx);
  for(kk_ssize_t i = 0; i < len; i++) {
    struct kk_std_core_hnd_Ev* ev = kk_std_core_hnd__as_Ev(vec[i],ctx);
    if (kk_string_cmp_borrow(htag.tagname,ev->htag.tagname,ctx) <= 0) return i; // break on insertion point
  }
  //string_t evvs = kk_evv_show(dup_datatype_as(kk_evv_t,ctx->evv),ctx);
  //fatal_error(EFAULT,"cannot find tag '%s' in: %s", string_cbuf_borrow(htag.htag), string_cbuf_borrow(evvs));
  //drop_string_t(evvs,ctx);
  return len;
}


// static inline kk_cfc_t kk_cfc_lub(kk_cfc_t cfc1, kk_cfc_t cfc2) {
//   if (cfc1 < 0) return cfc2;
//   else if (cfc1+cfc2 == 1) return 2;
//   else if (cfc1>cfc2) return cfc1;
//   else return cfc2;
// }

// static inline struct kk_std_core_hnd_Ev* kk_evv_as_Ev( kk_evv_t evv, kk_context_t* ctx ) {
//   return kk_std_core_hnd__as_Ev(kk_evv_as_ev(evv,ctx),ctx);
// }


// static kk_cfc_t kk_evv_cfc_of_borrow(kk_evv_t evv, kk_context_t* ctx) {
//   if (kk_evv_is_vector(evv,ctx)) {
//     kk_cfc_t cfc = -1;
//     kk_ssize_t len;
//     kk_std_core_hnd__ev single;
//     kk_std_core_hnd__ev* vec = kk_evv_as_vec(ctx->evv,&len,&single,ctx);
//     for(kk_ssize_t i = 0; i < len; i++) {
//       struct kk_std_core_hnd_Ev* ev = kk_std_core_hnd__as_Ev(vec[i],ctx);
//       cfc = kk_cfc_lub(cfc, kk_handler_cfc_borrow(ev->hnd,ctx));
//     }
//     return cfc;
//   }
//   else {
//     struct kk_std_core_hnd_Ev* ev = kk_evv_as_Ev(evv,ctx);
//     return kk_handler_cfc_borrow(ev->hnd,ctx);
//   }
// }

bool kk_evv_is_affine(kk_context_t* ctx) {
  return false;
  // return (kk_evv_cfc_of_borrow(ctx->evv,ctx) <= 2);
}


// static void kk_evv_update_cfc_borrow(kk_evv_t evv, kk_cfc_t cfc, kk_context_t* ctx) {
//   kk_assert_internal(!kk_evv_is_empty(evv,ctx)); // should never happen (as named handlers are always in some context)
//   if (kk_evv_is_vector(evv,ctx)) {
//     kk_evv_vector_t vec = kk_evv_as_vector(evv,ctx);
//     vec->cfc = kk_integer_from_int32(kk_cfc_lub(kk_integer_clamp32_borrow(vec->cfc,ctx),cfc), ctx);
//   }
//   else {
//     struct kk_std_core_hnd_Ev* ev = kk_evv_as_Ev(evv,ctx);
//     ev->cfc = kk_cfc_lub(ev->cfc,cfc);
//   }
// }

kk_evv_t kk_evv_insert(kk_evv_t evvd, kk_std_core_hnd__ev evd, kk_context_t* ctx) {
  struct kk_std_core_hnd_Ev* ev = kk_std_core_hnd__as_Ev(evd,ctx);
  // update ev with parent evidence vector (either at init, or due to non-scoped resumptions)
  kk_marker_t marker = ev->marker;
  if (marker==0) { kk_std_core_hnd__ev_drop(evd,ctx); return evvd; } // ev-none
  kk_evv_drop(ev->hevv,ctx);
  ev->hevv = kk_evv_dup(evvd,ctx); // fixme: update in-place
  if (marker<0) { // negative marker is used for named evidence; this means this evidence should not be inserted into the evidence vector
    // kk_evv_update_cfc_borrow(evvd,ev->cfc,ctx); // update cfc in-place for named evidence
    kk_std_core_hnd__ev_drop(evd,ctx);
    return evvd;
  }
  // for regular handler evidence, insert ev
  kk_ssize_t n;
  kk_std_core_hnd__ev single;
  kk_std_core_hnd__ev* const evv1 = kk_evv_as_vec(evvd, &n, &single, ctx);
  if (n == 0) {
    // use ev directly as the evidence vector
    kk_evv_drop(evvd, ctx);
    return kk_ev_as_evv(evd,ctx);
  }
  else {
    // create evidence vector
    // const kk_cfc_t cfc = kk_cfc_lub(kk_evv_cfc_of_borrow(evvd, ctx), ev->cfc);
    // ev->cfc = cfc; // update in place
    kk_evv_vector_t vec2 = kk_evv_vector_alloc(n+1, /* cfc,*/ ctx);
    kk_std_core_hnd__ev* const evv2 = kk_evv_vector_buf(vec2, NULL);
    kk_ssize_t i;
    for (i = 0; i < n; i++) {
      struct kk_std_core_hnd_Ev* ev1 = kk_std_core_hnd__as_Ev(evv1[i],ctx);
      if (kk_string_cmp_borrow(ev->htag.tagname, ev1->htag.tagname,ctx) <= 0) break;
      evv2[i] = kk_std_core_hnd__ev_dup(evv1[i],ctx);
    }
    evv2[i] = evd;
    for (; i < n; i++) {
      evv2[i+1] = kk_std_core_hnd__ev_dup(evv1[i],ctx);
    }
    kk_evv_drop(evvd, ctx);  // assigned to evidence already
    return kk_datatype_from_base(vec2,ctx);
  }
}

kk_evv_t kk_evv_delete(kk_evv_t evvd, kk_ssize_t index, bool behind, kk_context_t* ctx) {
  kk_ssize_t n;
  kk_std_core_hnd__ev single;
  const kk_std_core_hnd__ev* evv1 = kk_evv_as_vec(evvd, &n, &single, ctx);
  if (n <= 1) {
    kk_evv_drop(evvd,ctx);
    return kk_evv_empty(ctx);
  }
  if (behind) index++;
  kk_assert_internal(index < n);
  // todo: copy without dupping (and later dropping) when possible
  // const kk_cfc_t cfc1 = kk_evv_cfc_of_borrow(evvd,ctx);
  kk_evv_vector_t const vec2 = kk_evv_vector_alloc(n-1,/*cfc1,*/ ctx);
  kk_std_core_hnd__ev* const evv2 = kk_evv_vector_buf(vec2,NULL);
  kk_ssize_t i;
  for(i = 0; i < index; i++) {
    evv2[i] = kk_std_core_hnd__ev_dup(evv1[i],ctx);
  }
  for(; i < n-1; i++) {
    evv2[i] = kk_std_core_hnd__ev_dup(evv1[i+1],ctx);
  }
  struct kk_std_core_hnd_Ev* ev = kk_std_core_hnd__as_Ev(evv1[index],ctx);
  // if (ev->cfc >= cfc1) {
  //   kk_cfc_t cfc = kk_std_core_hnd__as_Ev(evv2[0],ctx)->cfc;
  //   for(i = 1; i < n-1; i++) {
  //     cfc = kk_cfc_lub(cfc,kk_std_core_hnd__as_Ev(evv2[i],ctx)->cfc);
  //   }
  //   vec2->cfc = kk_integer_from_int32(cfc,ctx);
  // }
  kk_evv_drop(evvd,ctx);
  return kk_datatype_from_base(vec2,ctx);
}

kk_evv_t kk_evv_create(kk_evv_t evv1, kk_vector_t indices, kk_context_t* ctx) {
  kk_ssize_t len;
  kk_box_t* elems = kk_vector_buf_borrow(indices,&len,ctx); // borrows
  kk_evv_vector_t evv2 = kk_evv_vector_alloc(len,/* kk_evv_cfc_of_borrow(evv1,ctx),*/ ctx);
  kk_std_core_hnd__ev* buf2 = kk_evv_vector_buf(evv2,NULL);
  kk_assert_internal(kk_evv_is_vector(evv1,ctx));
  kk_ssize_t len1;
  kk_std_core_hnd__ev single;
  kk_std_core_hnd__ev* buf1 = kk_evv_as_vec(evv1,&len1,&single,ctx);
  for(kk_ssize_t i = 0; i < len; i++) {
    kk_ssize_t idx = kk_ssize_unbox(elems[i],KK_BORROWED,ctx);
    kk_assert_internal(idx < len1);
    buf2[i] = kk_std_core_hnd__ev_dup( buf1[idx], ctx );
  }
  kk_vector_drop(indices,ctx);
  kk_evv_drop(evv1,ctx);
  return kk_datatype_from_base(evv2,ctx);
}

kk_evv_t kk_evv_swap_create( kk_vector_t indices, kk_context_t* ctx ) {
  kk_ssize_t len;
  kk_box_t* vec = kk_vector_buf_borrow(indices,&len,ctx);
  if (len==0) {
    kk_vector_drop(indices,ctx);
    return kk_evv_swap_create0(ctx);
  }
  if (len==1) {
    kk_ssize_t i = kk_ssize_unbox(vec[0],KK_BORROWED,ctx);
    kk_vector_drop(indices,ctx);
    return kk_evv_swap_create1(i,ctx);
  }
  return kk_evv_swap( kk_evv_create(kk_evv_dup(ctx->evv,ctx),indices,ctx), ctx );
}


kk_string_t kk_evv_show(kk_evv_t evv, kk_context_t* ctx) {
  return kk_string_alloc_dup_valid_utf8("(not yet implemented: kk_evv_show)",ctx);
}


/*-----------------------------------------------------------------------
  Compose continuations
-----------------------------------------------------------------------*/

struct kcompose_fun_s {
  struct kk_function_s _base;
  kk_box_t      count;
  kk_function_t conts[1];
};

// kleisli composition of continuations
static kk_box_t kcompose( kk_function_t fself, kk_box_t x, kk_context_t* ctx) {
  struct kcompose_fun_s* self = kk_function_as(struct kcompose_fun_s*,fself,ctx);
  kk_intx_t count = kk_intf_unbox(self->count);
  kk_function_t* conts = &self->conts[0];
  // call each continuation in order
  for(kk_intx_t i = 0; i < count; i++) {
    // todo: take uniqueness of fself into account to avoid dup_function
    kk_function_t f = kk_function_dup(conts[i],ctx);
    x = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, x, ctx), ctx);
    if (kk_yielding(ctx)) {
      // if yielding, `yield_next` all continuations that still need to be done
      while(++i < count) {
        // todo: if fself is unique, we could copy without dup?
        kk_yield_extend(kk_function_dup(conts[i],ctx),ctx);
      }
      kk_function_drop(fself,ctx);
      kk_box_drop(x,ctx);     // still drop even though we yield as it may release a boxed value type?
      return kk_box_any(ctx); // return yielding
    }
  }
  kk_function_drop(fself,ctx);
  return x;
}

static kk_function_t new_kcompose( kk_function_t* conts, kk_intf_t count, kk_context_t* ctx ) {
  if (count==0) return kk_function_id(ctx);
  if (count==1) return conts[0];
  struct kcompose_fun_s* f = kk_block_as(struct kcompose_fun_s*,
                               kk_block_alloc(kk_ssizeof(struct kcompose_fun_s) - kk_ssizeof(kk_function_t) + (count*kk_ssizeof(kk_function_t)),
                                 2 + count /* scan size */, KK_TAG_FUNCTION, ctx));
  f->_base.fun = kk_kkfun_ptr_box(&kcompose,ctx);
  f->count = kk_intf_box(count);
  kk_memcpy(f->conts, conts, count * kk_ssizeof(kk_function_t));
  return kk_datatype_from_base(&f->_base,ctx);
}

/*-----------------------------------------------------------------------
  Yield extension
-----------------------------------------------------------------------*/

kk_box_t kk_yield_extend( kk_function_t next, kk_context_t* ctx ) {
  kk_yield_t* yield = &ctx->yield;
  kk_assert_internal(kk_yielding(ctx));  // cannot extend if not yielding
  if (kk_unlikely(kk_yielding_final(ctx))) {
    // todo: can we optimize this so `next` is never allocated in the first place?
    kk_function_drop(next,ctx); // ignore extension if never resuming
  }
  else {
    if (kk_unlikely(yield->conts_count >= KK_YIELD_CONT_MAX)) {
      // alloc a function to compose all continuations in the array
      kk_function_t comp = new_kcompose( yield->conts, yield->conts_count, ctx );
      yield->conts[0] = comp;
      yield->conts_count = 1;
    }
    yield->conts[yield->conts_count++] = next;
  }
  return kk_box_any(ctx);
}

// cont_apply: \x -> f(cont,x)
struct cont_apply_fun_s {
  struct kk_function_s _base;
  kk_function_t f;
  kk_function_t cont;
};

static kk_box_t cont_apply( kk_function_t fself, kk_box_t x, kk_context_t* ctx ) {
  struct cont_apply_fun_s* self = kk_function_as(struct cont_apply_fun_s*, fself, ctx);
  kk_function_t f = self->f;
  kk_function_t cont = self->cont;
  kk_drop_match(self,{kk_function_dup(f,ctx);kk_function_dup(cont,ctx);},{},ctx);
  return kk_function_call( kk_box_t, (kk_function_t, kk_function_t, kk_box_t, kk_context_t* ctx), f, (f, cont, x, ctx), ctx);
}

static kk_function_t kk_new_cont_apply( kk_function_t f, kk_function_t cont, kk_context_t* ctx ) {
  struct cont_apply_fun_s* self = kk_function_alloc_as(struct cont_apply_fun_s, 3, ctx);
  self->_base.fun = kk_kkfun_ptr_box(&cont_apply,ctx);
  self->f = f;
  self->cont = cont;
  return kk_datatype_from_base(&self->_base,ctx);
}

// Unlike `yield_extend`, `yield_cont` gets access to the current continuation. This is used in `yield_prompt`.
kk_box_t kk_yield_cont( kk_function_t f, kk_context_t* ctx ) {
  kk_yield_t* yield = &ctx->yield;
  kk_assert_internal(kk_yielding(ctx)); // cannot extend if not yielding
  if (kk_unlikely(kk_yielding_final(ctx))) {
    kk_function_drop(f,ctx); // ignore extension if never resuming
  }
  else {
    kk_function_t cont = new_kcompose(yield->conts, yield->conts_count, ctx);
    yield->conts_count = 1;
    yield->conts[0] = kk_new_cont_apply(f, cont, ctx);
  }
  return kk_box_any(ctx);
}

kk_function_t kk_yield_to( kk_marker_t m, kk_function_t clause, kk_context_t* ctx ) {
  kk_yield_t* yield = &ctx->yield;
  kk_assert_internal(!kk_yielding(ctx)); // already yielding
  ctx->yielding = KK_YIELD_NORMAL;
  yield->marker = m;
  yield->clause = clause;
  yield->conts_count = 0;
  return kk_datatype_unbox(kk_box_any(ctx));
}

kk_box_t kk_yield_final( kk_marker_t m, kk_function_t clause, kk_context_t* ctx ) {
  kk_yield_to(m,clause,ctx);
  ctx->yielding = KK_YIELD_FINAL;
  return kk_box_any(ctx);
}

kk_box_t kk_fatal_resume_final(kk_context_t* ctx) {
  kk_fatal_error(EFAULT,"trying to resume a finalized resumption");
  return kk_box_any(ctx);
}

static kk_box_t _fatal_resume_final(kk_function_t self, kk_context_t* ctx) {
  kk_function_drop(self,ctx);
  return kk_fatal_resume_final(ctx);
}
static kk_function_t fun_fatal_resume_final(kk_context_t* ctx) {
  kk_define_static_function(f,_fatal_resume_final,ctx);
  return kk_function_dup(f,ctx);
}


struct kk_std_core_hnd_yld_s kk_yield_prompt( kk_marker_t m, kk_context_t* ctx ) {
  kk_yield_t* yield = &ctx->yield;
  if (ctx->yielding == KK_YIELD_NONE) {
    return kk_std_core_hnd__new_Pure(ctx);
  }
  else if (yield->marker != m) {
    return (ctx->yielding == KK_YIELD_FINAL ? kk_std_core_hnd__new_YieldingFinal(ctx) : kk_std_core_hnd__new_Yielding(ctx));
  }
  else {
    kk_function_t cont = (ctx->yielding == KK_YIELD_FINAL ? fun_fatal_resume_final(ctx) : new_kcompose(yield->conts, yield->conts_count, ctx));
    kk_function_t clause = yield->clause;
    ctx->yielding = KK_YIELD_NONE;
    #ifndef NDEBUG
    kk_memset(yield,0,kk_ssizeof(kk_yield_t));
    #endif
    return kk_std_core_hnd__new_Yield(clause, cont, ctx);
  }
}

kk_unit_t  kk_evv_guard(kk_evv_t evv, kk_context_t* ctx) {
  bool eq = kk_datatype_eq(ctx->evv,evv);
  kk_evv_drop(evv,ctx);
  if (!eq) {
    // todo: improve error message with diagnostics
    kk_fatal_error(EFAULT,"trying to resume outside the (handler) scope of the original handler");
  }
  return kk_Unit;
}

typedef struct yield_info_s {
  struct kk_std_core_hnd__yield_info_s _base;
  kk_function_t clause;
  kk_function_t conts[KK_YIELD_CONT_MAX];
  kk_intf_t     conts_count;
  kk_marker_t   marker;
  int8_t        yielding;
}* yield_info_t;

kk_std_core_hnd__yield_info kk_yield_capture(kk_context_t* ctx) {
  kk_assert_internal(kk_yielding(ctx));
  yield_info_t yld = kk_block_alloc_as(struct yield_info_s, 1 + KK_YIELD_CONT_MAX, (kk_tag_t)1, ctx);
  yld->clause = ctx->yield.clause;
  kk_ssize_t i = 0;
  for( ; i < ctx->yield.conts_count; i++) {
    yld->conts[i] = ctx->yield.conts[i];
  }
  for( ; i < KK_YIELD_CONT_MAX; i++) {
    yld->conts[i] = kk_function_null(ctx);
  }
  yld->conts_count = ctx->yield.conts_count;
  yld->marker = ctx->yield.marker;
  yld->yielding = ctx->yielding;
  ctx->yielding = 0;
  ctx->yield.conts_count = 0;
  return kk_datatype_from_base(&yld->_base,ctx);
}

kk_box_t kk_yield_reyield( kk_std_core_hnd__yield_info yldinfo, kk_context_t* ctx) {
  kk_assert_internal(!kk_yielding(ctx));
  yield_info_t yld = kk_datatype_as_assert(yield_info_t, yldinfo, (kk_tag_t)1, ctx);
  ctx->yield.clause = kk_function_dup(yld->clause,ctx);
  ctx->yield.marker = yld->marker;
  ctx->yield.conts_count = yld->conts_count;
  ctx->yielding = yld->yielding;
  for(kk_ssize_t i = 0; i < yld->conts_count; i++) {
    ctx->yield.conts[i] = kk_function_dup(yld->conts[i],ctx);
  }
  kk_constructor_drop(yld,ctx);
  return kk_box_any(ctx);
}


kk_std_core_hnd__htag kk_std_core_hnd_htag_fs__copy(kk_std_core_hnd__htag _this, kk_std_core_types__optional tagname, kk_context_t* _ctx) { /* forall<a> (htag<a>, tagname : ? string) -> htag<a> */ 
  kk_string_t _x_x305;
  if (kk_std_core_types__is_Optional(tagname, _ctx)) {
    kk_box_t _box_x0 = tagname._cons._Optional.value;
    kk_string_t _uniq_tagname_1886 = kk_string_unbox(_box_x0);
    kk_string_dup(_uniq_tagname_1886, _ctx);
    kk_std_core_types__optional_drop(tagname, _ctx);
    kk_std_core_hnd__htag_drop(_this, _ctx);
    _x_x305 = _uniq_tagname_1886; /*string*/
  }
  else {
    kk_std_core_types__optional_drop(tagname, _ctx);
    {
      kk_string_t _x = _this.tagname;
      _x_x305 = _x; /*string*/
    }
  }
  return kk_std_core_hnd__new_Htag(_x_x305, _ctx);
}

kk_std_core_hnd__ev kk_std_core_hnd_ev_fs__copy(kk_std_core_hnd__ev _this, kk_std_core_types__optional htag, int32_t marker, kk_box_t hnd, kk_evv_t hevv, kk_context_t* _ctx) { /* forall<a,e,b> (ev<a>, htag : ? (htag<a>), marker : marker<e,b>, hnd : a<e,b>, hevv : evv<e>) -> ev<a> */ 
  kk_std_core_hnd__htag _x_x307;
  if (kk_std_core_types__is_Optional(htag, _ctx)) {
    kk_box_t _box_x1 = htag._cons._Optional.value;
    kk_std_core_hnd__htag _uniq_htag_1987 = kk_std_core_hnd__htag_unbox(_box_x1, KK_BORROWED, _ctx);
    kk_std_core_hnd__htag_dup(_uniq_htag_1987, _ctx);
    kk_std_core_types__optional_drop(htag, _ctx);
    kk_datatype_ptr_dropn(_this, (KK_I32(3)), _ctx);
    _x_x307 = _uniq_htag_1987; /*hnd/htag<2019>*/
  }
  else {
    kk_std_core_types__optional_drop(htag, _ctx);
    {
      struct kk_std_core_hnd_Ev* _con_x308 = kk_std_core_hnd__as_Ev(_this, _ctx);
      kk_std_core_hnd__htag _x = _con_x308->htag;
      kk_box_t _pat_1_0 = _con_x308->hnd;
      kk_evv_t _pat_2 = _con_x308->hevv;
      if kk_likely(kk_datatype_ptr_is_unique(_this, _ctx)) {
        kk_evv_drop(_pat_2, _ctx);
        kk_box_drop(_pat_1_0, _ctx);
        kk_datatype_ptr_free(_this, _ctx);
      }
      else {
        kk_std_core_hnd__htag_dup(_x, _ctx);
        kk_datatype_ptr_decref(_this, _ctx);
      }
      _x_x307 = _x; /*hnd/htag<2019>*/
    }
  }
  return kk_std_core_hnd__new_Ev(kk_reuse_null, 0, _x_x307, marker, hnd, hevv, _ctx);
}
 
// Are two markers equal?

bool kk_std_core_hnd_eq_marker(int32_t x, int32_t y, kk_context_t* _ctx) { /* forall<a,b,e,e1> (x : marker<e,a>, y : marker<e1,b>) -> bool */ 
  return x==y;
}
 
// Evidence equality compares the markers.

bool kk_std_core_hnd_ev_fs__lp__eq__eq__rp_(kk_std_core_hnd__ev _pat_x141__18, kk_std_core_hnd__ev _pat_x141__37, kk_context_t* _ctx) { /* forall<a> (ev<a>, ev<a>) -> bool */ 
  {
    struct kk_std_core_hnd_Ev* _con_x309 = kk_std_core_hnd__as_Ev(_pat_x141__18, _ctx);
    kk_std_core_hnd__htag _pat_0 = _con_x309->htag;
    int32_t m1 = _con_x309->marker;
    kk_box_t _pat_1 = _con_x309->hnd;
    kk_evv_t _pat_2 = _con_x309->hevv;
    if kk_likely(kk_datatype_ptr_is_unique(_pat_x141__18, _ctx)) {
      kk_evv_drop(_pat_2, _ctx);
      kk_box_drop(_pat_1, _ctx);
      kk_std_core_hnd__htag_drop(_pat_0, _ctx);
      kk_datatype_ptr_free(_pat_x141__18, _ctx);
    }
    else {
      kk_datatype_ptr_decref(_pat_x141__18, _ctx);
    }
    {
      struct kk_std_core_hnd_Ev* _con_x310 = kk_std_core_hnd__as_Ev(_pat_x141__37, _ctx);
      kk_std_core_hnd__htag _pat_4 = _con_x310->htag;
      int32_t m2 = _con_x310->marker;
      kk_box_t _pat_5 = _con_x310->hnd;
      kk_evv_t _pat_6 = _con_x310->hevv;
      if kk_likely(kk_datatype_ptr_is_unique(_pat_x141__37, _ctx)) {
        kk_evv_drop(_pat_6, _ctx);
        kk_box_drop(_pat_5, _ctx);
        kk_std_core_hnd__htag_drop(_pat_4, _ctx);
        kk_datatype_ptr_free(_pat_x141__37, _ctx);
      }
      else {
        kk_datatype_ptr_decref(_pat_x141__37, _ctx);
      }
      return kk_std_core_hnd_eq_marker(m1, m2, _ctx);
    }
  }
}

int32_t kk_std_core_hnd_fresh_marker(kk_context_t* _ctx) { /* forall<a,e> () -> marker<e,a> */ 
  return kk_marker_unique(kk_context());
}

int32_t kk_std_core_hnd_fresh_marker_named(kk_context_t* _ctx) { /* forall<a,e> () -> marker<e,a> */ 
  return -kk_marker_unique(kk_context());
}
 
// Insert new evidence into the given evidence vector.

kk_evv_t kk_std_core_hnd_evv_insert(kk_evv_t evv, kk_std_core_hnd__ev ev, kk_context_t* _ctx) { /* forall<e,e1,a> (evv : evv<e>, ev : ev<a>) -> e evv<e1> */ 
  return kk_evv_insert(evv,ev,kk_context());
}
 
// show evidence for debug purposes

kk_string_t kk_std_core_hnd_evv_show(kk_evv_t evv, kk_context_t* _ctx) { /* forall<e> (evv : evv<e>) -> string */ 
  return kk_evv_show(evv,kk_context());
}
 
// Is an evidence vector unchanged? (i.e. as pointer equality).
// This is used to avoid copying in common cases.

bool kk_std_core_hnd_evv_eq(kk_evv_t evv0, kk_evv_t evv1, kk_context_t* _ctx) { /* forall<e> (evv0 : evv<e>, evv1 : evv<e>) -> bool */ 
  return kk_evv_eq(evv0,evv1,kk_context());
}
 
// (dynamically) find evidence insertion/deletion index in the evidence vector
// The compiler optimizes `@evv-index` to a static index when apparent from the effect type.

kk_ssize_t kk_std_core_hnd__evv_index(kk_std_core_hnd__htag htag, kk_context_t* _ctx) { /* forall<e,a> (htag : htag<a>) -> e ev-index */ 
  return kk_evv_index(htag,kk_context());
}
 
// Get the current evidence vector.

kk_evv_t kk_std_core_hnd_evv_get(kk_context_t* _ctx) { /* forall<e> () -> e evv<e> */ 
  return kk_evv_get(kk_context());
}
 
// Does the current evidence vector consist solely of affine handlers?
// This is called in backends that do not have context paths (like javascript)
// to optimize TRMC (where we can use faster update-in-place TRMC if we know the
// operations are all affine). As such, it is always safe to return `false`.
//
// control flow context:
//                 -1: none: bottom
//                   /
// 0: except: never resumes   1: linear: resumes exactly once
//                   \          /
//           2: affine: resumes never or once
//                        |
//     3: multi: resumes never, once, or multiple times
//

bool kk_std_core_hnd__evv_is_affine(kk_context_t* _ctx) { /* () -> bool */ 
  return kk_evv_is_affine(kk_context());
}
 
// Remove evidence at index `i` of the current evidence vector, and return the old one.
// (used by `mask`)

kk_evv_t kk_std_core_hnd_evv_swap_delete(kk_ssize_t i, bool behind, kk_context_t* _ctx) { /* forall<e,e1> (i : ev-index, behind : bool) -> e1 evv<e> */ 
  return kk_evv_swap_delete(i,behind,kk_context());
}
 
// Swap the current evidence vector with a new vector consisting of evidence
// at indices `indices` in the current vector.

kk_evv_t kk_std_core_hnd_evv_swap_create(kk_vector_t indices, kk_context_t* _ctx) { /* forall<e> (indices : vector<ev-index>) -> e evv<e> */ 
  return kk_evv_swap_create(indices,kk_context());
}

kk_box_t kk_std_core_hnd_yield_extend(kk_function_t next, kk_context_t* _ctx) { /* forall<a,b,e> (next : (a) -> e b) -> e b */ 
  return kk_yield_extend(next,kk_context());
}

kk_box_t kk_std_core_hnd_yield_cont(kk_function_t f, kk_context_t* _ctx) { /* forall<a,e,b> (f : forall<c> ((c) -> e a, c) -> e b) -> e b */ 
  return kk_yield_cont(f,kk_context());
}

kk_std_core_hnd__yld kk_std_core_hnd_yield_prompt(int32_t m, kk_context_t* _ctx) { /* forall<a,e,b> (m : marker<e,b>) -> yld<e,a,b> */ 
  return kk_yield_prompt(m,kk_context());
}

kk_function_t kk_std_core_hnd_yield_to_prim(int32_t m, kk_function_t clause, kk_context_t* _ctx) { /* forall<a,e,e1,b> (m : marker<e1,b>, clause : ((resume-result<a,b>) -> e1 b) -> e1 b) -> e (() -> a) */ 
  return kk_yield_to(m,clause,kk_context());
}

kk_box_t kk_std_core_hnd_yield_to_final(int32_t m, kk_function_t clause, kk_context_t* _ctx) { /* forall<a,e,e1,b> (m : marker<e1,b>, clause : ((resume-result<a,b>) -> e1 b) -> e1 b) -> e a */ 
  return kk_yield_final(m,clause,kk_context());
}


// lift anonymous function
struct kk_std_core_hnd_yield_to_fun311__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_hnd_yield_to_fun311(kk_function_t _fself, kk_box_t _b_x3, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_yield_to_fun311(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_hnd_yield_to_fun311, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_hnd_yield_to_fun311(kk_function_t _fself, kk_box_t _b_x3, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_function_t _x_x312 = kk_function_unbox(_b_x3, _ctx); /*() -> 2786 4*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), _x_x312, (_x_x312, _ctx), _ctx);
}

kk_box_t kk_std_core_hnd_yield_to(int32_t m, kk_function_t clause, kk_context_t* _ctx) { /* forall<a,e,b> (m : marker<e,b>, clause : ((resume-result<a,b>) -> e b) -> e b) -> e a */ 
  kk_function_t g = kk_std_core_hnd_yield_to_prim(m, clause, _ctx); /*() -> 2785*/;
  kk_function_drop(g, _ctx);
  return kk_std_core_hnd_yield_extend(kk_std_core_hnd_new_yield_to_fun311(_ctx), _ctx);
}

kk_std_core_hnd__yield_info kk_std_core_hnd_yield_capture(kk_context_t* _ctx) { /* forall<e> () -> e yield-info */ 
  return kk_yield_capture(kk_context());
}

kk_box_t kk_std_core_hnd_unsafe_reyield(kk_std_core_hnd__yield_info yld, kk_context_t* _ctx) { /* forall<a,e> (yld : yield-info) -> e a */ 
  return kk_yield_reyield(yld,kk_context());
}

kk_unit_t kk_std_core_hnd_guard(kk_evv_t w, kk_context_t* _ctx) { /* forall<e> (w : evv<e>) -> e () */ 
  kk_evv_guard(w,kk_context()); return kk_Unit;
}

kk_box_t kk_std_core_hnd_resume_final(kk_context_t* _ctx) { /* forall<a> () -> a */ 
  return kk_fatal_resume_final(kk_context());
}


// lift anonymous function
struct kk_std_core_hnd_prompt_fun315__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
  kk_function_t ret;
  kk_evv_t w0;
  kk_evv_t w1;
  int32_t m;
};
static kk_box_t kk_std_core_hnd_prompt_fun315(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_fun315(kk_std_core_hnd__ev ev, kk_function_t ret, kk_evv_t w0, kk_evv_t w1, int32_t m, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun315__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_fun315__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_fun315, kk_context());
  _self->ev = ev;
  _self->ret = ret;
  _self->w0 = w0;
  _self->w1 = w1;
  _self->m = m;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_prompt_fun315(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun315__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_fun315__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<3484> */
  kk_function_t ret = _self->ret; /* (3482) -> 3483 3485 */
  kk_evv_t w0 = _self->w0; /* hnd/evv<3483> */
  kk_evv_t w1 = _self->w1; /* hnd/evv<3483> */
  int32_t m = _self->m; /* hnd/marker<3483,3485> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);kk_function_dup(ret, _ctx);kk_evv_dup(w0, _ctx);kk_evv_dup(w1, _ctx);kk_skip_dup(m, _ctx);}, {}, _ctx)
  kk_evv_t w0_sq_ = kk_std_core_hnd_evv_get(_ctx); /*hnd/evv<3483>*/;
  kk_evv_t w1_sq_;
  bool _match_x263;
  kk_evv_t _x_x316 = kk_evv_dup(w0_sq_, _ctx); /*hnd/evv<3483>*/
  _match_x263 = kk_std_core_hnd_evv_eq(w0, _x_x316, _ctx); /*bool*/
  if (_match_x263) {
    w1_sq_ = w1; /*hnd/evv<3483>*/
  }
  else {
    kk_evv_drop(w1, _ctx);
    kk_evv_t _x_x317 = kk_evv_dup(w0_sq_, _ctx); /*hnd/evv<3483>*/
    kk_std_core_hnd__ev _x_x318 = kk_std_core_hnd__ev_dup(ev, _ctx); /*hnd/ev<3484>*/
    w1_sq_ = kk_std_core_hnd_evv_insert(_x_x317, _x_x318, _ctx); /*hnd/evv<3483>*/
  }
  kk_unit_t ___1 = kk_Unit;
  kk_evv_t _x_x319 = kk_evv_dup(w1_sq_, _ctx); /*hnd/evv<3483>*/
  kk_evv_set(_x_x319,kk_context());
  kk_box_t _x_x320 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, res, _ctx), _ctx); /*3482*/
  return kk_std_core_hnd_prompt(w0_sq_, w1_sq_, ev, m, ret, _x_x320, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_prompt_fun321__t {
  struct kk_function_s _base;
  kk_function_t cont_0;
  kk_std_core_hnd__ev ev;
  kk_function_t ret;
  kk_evv_t w0;
  kk_evv_t w1;
  int32_t m;
};
static kk_box_t kk_std_core_hnd_prompt_fun321(kk_function_t _fself, kk_std_core_hnd__resume_result r, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_fun321(kk_function_t cont_0, kk_std_core_hnd__ev ev, kk_function_t ret, kk_evv_t w0, kk_evv_t w1, int32_t m, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun321__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_fun321__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_fun321, kk_context());
  _self->cont_0 = cont_0;
  _self->ev = ev;
  _self->ret = ret;
  _self->w0 = w0;
  _self->w1 = w1;
  _self->m = m;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_prompt_fun327__t {
  struct kk_function_s _base;
  kk_box_t x;
};
static kk_box_t kk_std_core_hnd_prompt_fun327(kk_function_t _fself, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_fun327(kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun327__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_fun327__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_fun327, kk_context());
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_prompt_fun327(kk_function_t _fself, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun327__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_fun327__t*, _fself, _ctx);
  kk_box_t x = _self->x; /* 3463 */
  kk_drop_match(_self, {kk_box_dup(x, _ctx);}, {}, _ctx)
  return x;
}


// lift anonymous function
struct kk_std_core_hnd_prompt_fun328__t {
  struct kk_function_s _base;
  kk_box_t x_0;
};
static kk_box_t kk_std_core_hnd_prompt_fun328(kk_function_t _fself, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_fun328(kk_box_t x_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun328__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_fun328__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_fun328, kk_context());
  _self->x_0 = x_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_prompt_fun328(kk_function_t _fself, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun328__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_fun328__t*, _fself, _ctx);
  kk_box_t x_0 = _self->x_0; /* 3463 */
  kk_drop_match(_self, {kk_box_dup(x_0, _ctx);}, {}, _ctx)
  return x_0;
}


// lift anonymous function
struct kk_std_core_hnd_prompt_fun334__t {
  struct kk_function_s _base;
  kk_box_t x_1_0;
  int32_t m;
};
static kk_box_t kk_std_core_hnd_prompt_fun334(kk_function_t _fself, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_fun334(kk_box_t x_1_0, int32_t m, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun334__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_fun334__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_fun334, kk_context());
  _self->x_1_0 = x_1_0;
  _self->m = m;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_prompt_fun335__t {
  struct kk_function_s _base;
  kk_box_t x_1_0;
};
static kk_box_t kk_std_core_hnd_prompt_fun335(kk_function_t _fself, kk_function_t ___wildcard_x409__85, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_fun335(kk_box_t x_1_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun335__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_fun335__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_fun335, kk_context());
  _self->x_1_0 = x_1_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_prompt_fun335(kk_function_t _fself, kk_function_t ___wildcard_x409__85, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun335__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_fun335__t*, _fself, _ctx);
  kk_box_t x_1_0 = _self->x_1_0; /* 3485 */
  kk_drop_match(_self, {kk_box_dup(x_1_0, _ctx);}, {}, _ctx)
  kk_function_drop(___wildcard_x409__85, _ctx);
  return x_1_0;
}
static kk_box_t kk_std_core_hnd_prompt_fun334(kk_function_t _fself, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun334__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_fun334__t*, _fself, _ctx);
  kk_box_t x_1_0 = _self->x_1_0; /* 3485 */
  int32_t m = _self->m; /* hnd/marker<3483,3485> */
  kk_drop_match(_self, {kk_box_dup(x_1_0, _ctx);kk_skip_dup(m, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_yield_to_final(m, kk_std_core_hnd_new_prompt_fun335(x_1_0, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_prompt_fun321(kk_function_t _fself, kk_std_core_hnd__resume_result r, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_fun321__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_fun321__t*, _fself, _ctx);
  kk_function_t cont_0 = _self->cont_0; /* (() -> 3463) -> 3483 3482 */
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<3484> */
  kk_function_t ret = _self->ret; /* (3482) -> 3483 3485 */
  kk_evv_t w0 = _self->w0; /* hnd/evv<3483> */
  kk_evv_t w1 = _self->w1; /* hnd/evv<3483> */
  int32_t m = _self->m; /* hnd/marker<3483,3485> */
  kk_drop_match(_self, {kk_function_dup(cont_0, _ctx);kk_std_core_hnd__ev_dup(ev, _ctx);kk_function_dup(ret, _ctx);kk_evv_dup(w0, _ctx);kk_evv_dup(w1, _ctx);kk_skip_dup(m, _ctx);}, {}, _ctx)
  if (kk_std_core_hnd__is_Deep(r, _ctx)) {
    kk_box_t x = r._cons.Deep.result;
    kk_evv_t w0_0_sq_ = kk_std_core_hnd_evv_get(_ctx); /*hnd/evv<3483>*/;
    kk_evv_t w1_0_sq_;
    bool _match_x262;
    kk_evv_t _x_x322 = kk_evv_dup(w0_0_sq_, _ctx); /*hnd/evv<3483>*/
    _match_x262 = kk_std_core_hnd_evv_eq(w0, _x_x322, _ctx); /*bool*/
    if (_match_x262) {
      w1_0_sq_ = w1; /*hnd/evv<3483>*/
    }
    else {
      kk_evv_drop(w1, _ctx);
      kk_evv_t _x_x323 = kk_evv_dup(w0_0_sq_, _ctx); /*hnd/evv<3483>*/
      kk_std_core_hnd__ev _x_x324 = kk_std_core_hnd__ev_dup(ev, _ctx); /*hnd/ev<3484>*/
      w1_0_sq_ = kk_std_core_hnd_evv_insert(_x_x323, _x_x324, _ctx); /*hnd/evv<3483>*/
    }
    kk_unit_t ___2 = kk_Unit;
    kk_evv_t _x_x325 = kk_evv_dup(w1_0_sq_, _ctx); /*hnd/evv<3483>*/
    kk_evv_set(_x_x325,kk_context());
    kk_box_t _x_x326 = kk_function_call(kk_box_t, (kk_function_t, kk_function_t, kk_context_t*), cont_0, (cont_0, kk_std_core_hnd_new_prompt_fun327(x, _ctx), _ctx), _ctx); /*3482*/
    return kk_std_core_hnd_prompt(w0_0_sq_, w1_0_sq_, ev, m, ret, _x_x326, _ctx);
  }
  if (kk_std_core_hnd__is_Shallow(r, _ctx)) {
    kk_box_t x_0 = r._cons.Shallow.result;
    kk_evv_drop(w1, _ctx);
    kk_evv_drop(w0, _ctx);
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_box_t x_1_10002 = kk_function_call(kk_box_t, (kk_function_t, kk_function_t, kk_context_t*), cont_0, (cont_0, kk_std_core_hnd_new_prompt_fun328(x_0, _ctx), _ctx), _ctx); /*3482*/;
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_1_10002, _ctx);
      return kk_std_core_hnd_yield_extend(ret, _ctx);
    }
    {
      return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), ret, (ret, x_1_10002, _ctx), _ctx);
    }
  }
  {
    kk_box_t x_1_0 = r._cons.Finalize.result;
    kk_evv_t w0_1_sq_ = kk_std_core_hnd_evv_get(_ctx); /*hnd/evv<3483>*/;
    kk_evv_t w1_1_sq_;
    bool _match_x260;
    kk_evv_t _x_x329 = kk_evv_dup(w0_1_sq_, _ctx); /*hnd/evv<3483>*/
    _match_x260 = kk_std_core_hnd_evv_eq(w0, _x_x329, _ctx); /*bool*/
    if (_match_x260) {
      w1_1_sq_ = w1; /*hnd/evv<3483>*/
    }
    else {
      kk_evv_drop(w1, _ctx);
      kk_evv_t _x_x330 = kk_evv_dup(w0_1_sq_, _ctx); /*hnd/evv<3483>*/
      kk_std_core_hnd__ev _x_x331 = kk_std_core_hnd__ev_dup(ev, _ctx); /*hnd/ev<3484>*/
      w1_1_sq_ = kk_std_core_hnd_evv_insert(_x_x330, _x_x331, _ctx); /*hnd/evv<3483>*/
    }
    kk_unit_t ___3 = kk_Unit;
    kk_evv_t _x_x332 = kk_evv_dup(w1_1_sq_, _ctx); /*hnd/evv<3483>*/
    kk_evv_set(_x_x332,kk_context());
    kk_box_t _x_x333 = kk_function_call(kk_box_t, (kk_function_t, kk_function_t, kk_context_t*), cont_0, (cont_0, kk_std_core_hnd_new_prompt_fun334(x_1_0, m, _ctx), _ctx), _ctx); /*3482*/
    return kk_std_core_hnd_prompt(w0_1_sq_, w1_1_sq_, ev, m, ret, _x_x333, _ctx);
  }
}

kk_box_t kk_std_core_hnd_prompt(kk_evv_t w0, kk_evv_t w1, kk_std_core_hnd__ev ev, int32_t m, kk_function_t ret, kk_box_t result, kk_context_t* _ctx) { /* forall<a,e,b,c> (w0 : evv<e>, w1 : evv<e>, ev : ev<b>, m : marker<e,c>, ret : (a) -> e c, result : a) -> e c */ 
  kk_unit_t __ = kk_Unit;
  kk_evv_t _x_x313 = kk_evv_dup(w1, _ctx); /*hnd/evv<3483>*/
  kk_std_core_hnd_guard(_x_x313, _ctx);
  kk_unit_t ___0 = kk_Unit;
  kk_evv_t _x_x314 = kk_evv_dup(w0, _ctx); /*hnd/evv<3483>*/
  kk_evv_set(_x_x314,kk_context());
  kk_std_core_hnd__yld _match_x259 = kk_std_core_hnd_yield_prompt(m, _ctx); /*hnd/yld<2611,2610,2612>*/;
  if (kk_std_core_hnd__is_Pure(_match_x259, _ctx)) {
    kk_evv_drop(w1, _ctx);
    kk_evv_drop(w0, _ctx);
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), ret, (ret, result, _ctx), _ctx);
  }
  if (kk_std_core_hnd__is_YieldingFinal(_match_x259, _ctx)) {
    kk_evv_drop(w1, _ctx);
    kk_evv_drop(w0, _ctx);
    kk_function_drop(ret, _ctx);
    kk_box_drop(result, _ctx);
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    return kk_box_any(kk_context());
  }
  if (kk_std_core_hnd__is_Yielding(_match_x259, _ctx)) {
    kk_box_drop(result, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_prompt_fun315(ev, ret, w0, w1, m, _ctx), _ctx);
  }
  {
    kk_function_t clause = _match_x259._cons.Yield.clause;
    kk_function_t cont_0 = _match_x259._cons.Yield.cont;
    kk_box_drop(result, _ctx);
    return kk_function_call(kk_box_t, (kk_function_t, kk_function_t, kk_context_t*), clause, (clause, kk_std_core_hnd_new_prompt_fun321(cont_0, ev, ret, w0, w1, m, _ctx), _ctx), _ctx);
  }
}

kk_box_t kk_std_core_hnd__hhandle(kk_std_core_hnd__htag tag, kk_box_t h, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,e1,b,c> (tag : htag<b>, h : b<e,c>, ret : (a) -> e c, action : () -> e1 a) -> e c */ 
  kk_evv_t w0 = kk_std_core_hnd_evv_get(_ctx); /*hnd/evv<3613>*/;
  int32_t m = kk_std_core_hnd_fresh_marker(_ctx); /*hnd/marker<3613,3616>*/;
  kk_std_core_hnd__ev ev;
  kk_evv_t _x_x336 = kk_evv_dup(w0, _ctx); /*hnd/evv<3613>*/
  ev = kk_std_core_hnd__new_Ev(kk_reuse_null, 0, tag, m, h, _x_x336, _ctx); /*hnd/ev<3615>*/
  kk_evv_t w1;
  kk_evv_t _x_x337 = kk_evv_dup(w0, _ctx); /*hnd/evv<3613>*/
  kk_std_core_hnd__ev _x_x338 = kk_std_core_hnd__ev_dup(ev, _ctx); /*hnd/ev<3615>*/
  w1 = kk_std_core_hnd_evv_insert(_x_x337, _x_x338, _ctx); /*hnd/evv<3613>*/
  kk_unit_t __ = kk_Unit;
  kk_evv_t _x_x339 = kk_evv_dup(w1, _ctx); /*hnd/evv<3613>*/
  kk_evv_set(_x_x339,kk_context());
  kk_box_t _x_x340 = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), action, (action, _ctx), _ctx); /*3612*/
  return kk_std_core_hnd_prompt(w0, w1, ev, m, ret, _x_x340, _ctx);
}

kk_box_t kk_std_core_hnd__named_handle(kk_std_core_hnd__htag tag, kk_box_t h, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,e1,b,c> (tag : htag<b>, h : b<e,c>, ret : (a) -> e c, action : (ev<b>) -> e1 a) -> e c */ 
  int32_t m = kk_std_core_hnd_fresh_marker_named(_ctx); /*hnd/marker<3729,3732>*/;
  kk_evv_t w0 = kk_std_core_hnd_evv_get(_ctx); /*hnd/evv<3729>*/;
  kk_std_core_hnd__ev ev;
  kk_evv_t _x_x341 = kk_evv_dup(w0, _ctx); /*hnd/evv<3729>*/
  ev = kk_std_core_hnd__new_Ev(kk_reuse_null, 0, tag, m, h, _x_x341, _ctx); /*hnd/ev<3731>*/
  kk_evv_t _x_x342 = kk_evv_dup(w0, _ctx); /*hnd/evv<3729>*/
  kk_std_core_hnd__ev _x_x343 = kk_std_core_hnd__ev_dup(ev, _ctx); /*hnd/ev<3731>*/
  kk_box_t _x_x344 = kk_function_call(kk_box_t, (kk_function_t, kk_std_core_hnd__ev, kk_context_t*), action, (action, ev, _ctx), _ctx); /*3728*/
  return kk_std_core_hnd_prompt(_x_x342, w0, _x_x343, m, ret, _x_x344, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_mask_at1_fun345__t {
  struct kk_function_s _base;
  kk_ssize_t i;
  bool behind;
};
static kk_box_t kk_std_core_hnd_mask_at1_fun345(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_mask_at1_fun345(kk_ssize_t i, bool behind, kk_context_t* _ctx) {
  struct kk_std_core_hnd_mask_at1_fun345__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_mask_at1_fun345__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_mask_at1_fun345, kk_context());
  _self->i = i;
  _self->behind = behind;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_mask_at1_fun345(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_mask_at1_fun345__t* _self = kk_function_as(struct kk_std_core_hnd_mask_at1_fun345__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  bool behind = _self->behind; /* bool */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);kk_skip_dup(behind, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_mask_at1(i, behind, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd_mask_at1(kk_ssize_t i, bool behind, kk_function_t action, kk_box_t x, kk_context_t* _ctx) { /* forall<a,b,e,e1> (i : ev-index, behind : bool, action : (a) -> e b, x : a) -> e1 b */ 
  kk_evv_t w0 = kk_std_core_hnd_evv_swap_delete(i, behind, _ctx); /*hnd/evv<_3757>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), action, (action, x, _ctx), _ctx); /*3862*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w0,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_mask_at1_fun345(i, behind, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__mask_at_fun346__t {
  struct kk_function_s _base;
  kk_ssize_t i;
  bool behind;
};
static kk_box_t kk_std_core_hnd__mask_at_fun346(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_mask_at_fun346(kk_ssize_t i, bool behind, kk_context_t* _ctx) {
  struct kk_std_core_hnd__mask_at_fun346__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__mask_at_fun346__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__mask_at_fun346, kk_context());
  _self->i = i;
  _self->behind = behind;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__mask_at_fun346(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__mask_at_fun346__t* _self = kk_function_as(struct kk_std_core_hnd__mask_at_fun346__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  bool behind = _self->behind; /* bool */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);kk_skip_dup(behind, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_mask_at1(i, behind, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__mask_at(kk_ssize_t i, bool behind, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,e1> (i : ev-index, behind : bool, action : () -> e a) -> e1 a */ 
  kk_evv_t w0 = kk_std_core_hnd_evv_swap_delete(i, behind, _ctx); /*hnd/evv<_3885>*/;
  kk_box_t x = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), action, (action, _ctx), _ctx); /*3974*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w0,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(x, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_mask_at_fun346(i, behind, _ctx), _ctx);
  }
  {
    return x;
  }
}


// lift anonymous function
struct kk_std_core_hnd_prompt_local_var_fun348__t {
  struct kk_function_s _base;
  kk_ref_t loc;
  kk_box_t v;
};
static kk_box_t kk_std_core_hnd_prompt_local_var_fun348(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_prompt_local_var_fun348(kk_ref_t loc, kk_box_t v, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_local_var_fun348__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_prompt_local_var_fun348__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_prompt_local_var_fun348, kk_context());
  _self->loc = loc;
  _self->v = v;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_prompt_local_var_fun348(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_prompt_local_var_fun348__t* _self = kk_function_as(struct kk_std_core_hnd_prompt_local_var_fun348__t*, _fself, _ctx);
  kk_ref_t loc = _self->loc; /* local-var<4163,4161> */
  kk_box_t v = _self->v; /* 4161 */
  kk_drop_match(_self, {kk_ref_dup(loc, _ctx);kk_box_dup(v, _ctx);}, {}, _ctx)
  kk_unit_t ___0 = kk_Unit;
  kk_ref_set_borrow(loc,v,kk_context());
  kk_box_t _x_x349 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, x, _ctx), _ctx); /*4162*/
  return kk_std_core_hnd_prompt_local_var(loc, _x_x349, _ctx);
}

kk_box_t kk_std_core_hnd_prompt_local_var(kk_ref_t loc, kk_box_t res, kk_context_t* _ctx) { /* forall<a,b,h> (loc : local-var<h,a>, res : b) -> <div,local<h>> b */ 
  if (kk_yielding(kk_context())) {
    kk_box_drop(res, _ctx);
    kk_box_t v;
    kk_ref_t _x_x347 = kk_ref_dup(loc, _ctx); /*local-var<4163,4161>*/
    v = kk_ref_get(_x_x347,kk_context()); /*4161*/
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_prompt_local_var_fun348(loc, v, _ctx), _ctx);
  }
  {
    kk_ref_drop(loc, _ctx);
    return res;
  }
}


// lift anonymous function
struct kk_std_core_hnd_finally_prompt_fun351__t {
  struct kk_function_s _base;
  kk_function_t fin;
};
static kk_box_t kk_std_core_hnd_finally_prompt_fun351(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_finally_prompt_fun351(kk_function_t fin, kk_context_t* _ctx) {
  struct kk_std_core_hnd_finally_prompt_fun351__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_finally_prompt_fun351__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_finally_prompt_fun351, kk_context());
  _self->fin = fin;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_finally_prompt_fun351(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_finally_prompt_fun351__t* _self = kk_function_as(struct kk_std_core_hnd_finally_prompt_fun351__t*, _fself, _ctx);
  kk_function_t fin = _self->fin; /* () -> 4395 () */
  kk_drop_match(_self, {kk_function_dup(fin, _ctx);}, {}, _ctx)
  kk_box_t _x_x352 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, x, _ctx), _ctx); /*4394*/
  return kk_std_core_hnd_finally_prompt(fin, _x_x352, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_finally_prompt_fun353__t {
  struct kk_function_s _base;
  kk_std_core_hnd__yield_info yld;
};
static kk_box_t kk_std_core_hnd_finally_prompt_fun353(kk_function_t _fself, kk_box_t ___wildcard_x489__43, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_finally_prompt_fun353(kk_std_core_hnd__yield_info yld, kk_context_t* _ctx) {
  struct kk_std_core_hnd_finally_prompt_fun353__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_finally_prompt_fun353__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_finally_prompt_fun353, kk_context());
  _self->yld = yld;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_finally_prompt_fun353(kk_function_t _fself, kk_box_t ___wildcard_x489__43, kk_context_t* _ctx) {
  struct kk_std_core_hnd_finally_prompt_fun353__t* _self = kk_function_as(struct kk_std_core_hnd_finally_prompt_fun353__t*, _fself, _ctx);
  kk_std_core_hnd__yield_info yld = _self->yld; /* hnd/yield-info */
  kk_drop_match(_self, {kk_std_core_hnd__yield_info_dup(yld, _ctx);}, {}, _ctx)
  kk_box_drop(___wildcard_x489__43, _ctx);
  return kk_std_core_hnd_unsafe_reyield(yld, _ctx);
}

kk_box_t kk_std_core_hnd_finally_prompt(kk_function_t fin, kk_box_t res, kk_context_t* _ctx) { /* forall<a,e> (fin : () -> e (), res : a) -> e a */ 
  if (kk_yielding(kk_context())) {
    kk_box_drop(res, _ctx);
    bool _match_x255 = kk_yielding_non_final(kk_context()); /*bool*/;
    if (_match_x255) {
      return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_finally_prompt_fun351(fin, _ctx), _ctx);
    }
    {
      kk_std_core_hnd__yield_info yld = kk_std_core_hnd_yield_capture(_ctx); /*hnd/yield-info*/;
      kk_unit_t ___0 = kk_Unit;
      kk_function_call(kk_unit_t, (kk_function_t, kk_context_t*), fin, (fin, _ctx), _ctx);
      if (kk_yielding(kk_context())) {
        return kk_std_core_hnd_yield_extend(kk_std_core_hnd_new_finally_prompt_fun353(yld, _ctx), _ctx);
      }
      {
        return kk_std_core_hnd_unsafe_reyield(yld, _ctx);
      }
    }
  }
  {
    kk_unit_t __ = kk_Unit;
    kk_function_call(kk_unit_t, (kk_function_t, kk_context_t*), fin, (fin, _ctx), _ctx);
    return res;
  }
}


// lift anonymous function
struct kk_std_core_hnd_initially_prompt_fun355__t {
  struct kk_function_s _base;
  kk_ref_t count;
  kk_function_t init;
};
static kk_box_t kk_std_core_hnd_initially_prompt_fun355(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_initially_prompt_fun355(kk_ref_t count, kk_function_t init, kk_context_t* _ctx) {
  struct kk_std_core_hnd_initially_prompt_fun355__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_initially_prompt_fun355__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_initially_prompt_fun355, kk_context());
  _self->count = count;
  _self->init = init;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_initially_prompt_fun361__t {
  struct kk_function_s _base;
  kk_function_t cont;
  kk_function_t init;
  kk_box_t x;
};
static kk_box_t kk_std_core_hnd_initially_prompt_fun361(kk_function_t _fself, kk_box_t ___wildcard_x530__35, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_initially_prompt_fun361(kk_function_t cont, kk_function_t init, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_initially_prompt_fun361__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_initially_prompt_fun361__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_initially_prompt_fun361, kk_context());
  _self->cont = cont;
  _self->init = init;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_initially_prompt_fun361(kk_function_t _fself, kk_box_t ___wildcard_x530__35, kk_context_t* _ctx) {
  struct kk_std_core_hnd_initially_prompt_fun361__t* _self = kk_function_as(struct kk_std_core_hnd_initially_prompt_fun361__t*, _fself, _ctx);
  kk_function_t cont = _self->cont; /* (4616) -> 4630 4629 */
  kk_function_t init = _self->init; /* (int) -> 4630 () */
  kk_box_t x = _self->x; /* 4616 */
  kk_drop_match(_self, {kk_function_dup(cont, _ctx);kk_function_dup(init, _ctx);kk_box_dup(x, _ctx);}, {}, _ctx)
  kk_box_drop(___wildcard_x530__35, _ctx);
  kk_box_t _x_x362 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, x, _ctx), _ctx); /*4629*/
  return kk_std_core_hnd_initially_prompt(init, _x_x362, _ctx);
}
static kk_box_t kk_std_core_hnd_initially_prompt_fun355(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_initially_prompt_fun355__t* _self = kk_function_as(struct kk_std_core_hnd_initially_prompt_fun355__t*, _fself, _ctx);
  kk_ref_t count = _self->count; /* ref<global,int> */
  kk_function_t init = _self->init; /* (int) -> 4630 () */
  kk_drop_match(_self, {kk_ref_dup(count, _ctx);kk_function_dup(init, _ctx);}, {}, _ctx)
  kk_integer_t cnt;
  kk_box_t _x_x356;
  kk_ref_t _x_x357 = kk_ref_dup(count, _ctx); /*ref<global,int>*/
  _x_x356 = kk_ref_get(_x_x357,kk_context()); /*212*/
  cnt = kk_integer_unbox(_x_x356, _ctx); /*int*/
  kk_integer_t _b_x14_16;
  kk_integer_t _x_x358 = kk_integer_dup(cnt, _ctx); /*int*/
  _b_x14_16 = kk_integer_add(_x_x358,(kk_integer_from_small(1)),kk_context()); /*int*/
  kk_unit_t __ = kk_Unit;
  kk_unit_t _brw_x254 = kk_Unit;
  kk_ref_set_borrow(count,(kk_integer_box(_b_x14_16, _ctx)),kk_context());
  kk_ref_drop(count, _ctx);
  _brw_x254;
  kk_unit_t ___1 = kk_Unit;
  bool _match_x252 = kk_integer_eq_borrow(cnt,(kk_integer_from_small(0)),kk_context()); /*bool*/;
  if (_match_x252) {
    kk_integer_drop(cnt, _ctx);
  }
  else {
    kk_unit_t r = kk_Unit;
    kk_function_t _x_x359 = kk_function_dup(init, _ctx); /*(int) -> 4630 ()*/
    kk_function_call(kk_unit_t, (kk_function_t, kk_integer_t, kk_context_t*), _x_x359, (_x_x359, cnt, _ctx), _ctx);
    if (kk_yielding(kk_context())) {
      kk_box_t ___0;
      kk_function_t _x_x360;
      kk_function_dup(cont, _ctx);
      kk_function_dup(init, _ctx);
      kk_box_dup(x, _ctx);
      _x_x360 = kk_std_core_hnd_new_initially_prompt_fun361(cont, init, x, _ctx); /*(_4563) -> 4630 4629*/
      ___0 = kk_std_core_hnd_yield_extend(_x_x360, _ctx); /*4629*/
      kk_box_drop(___0, _ctx);
    }
    else {
      
    }
  }
  kk_box_t _x_x363 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, x, _ctx), _ctx); /*4629*/
  return kk_std_core_hnd_initially_prompt(init, _x_x363, _ctx);
}

kk_box_t kk_std_core_hnd_initially_prompt(kk_function_t init, kk_box_t res, kk_context_t* _ctx) { /* forall<a,e> (init : (int) -> e (), res : a) -> e a */ 
  bool _match_x251 = kk_yielding_non_final(kk_context()); /*bool*/;
  if (_match_x251) {
    kk_box_drop(res, _ctx);
    kk_ref_t count = kk_ref_alloc((kk_integer_box(kk_integer_from_small(0), _ctx)),kk_context()); /*ref<global,int>*/;
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_initially_prompt_fun355(count, init, _ctx), _ctx);
  }
  {
    kk_function_drop(init, _ctx);
    return res;
  }
}


// lift anonymous function
struct kk_std_core_hnd_initially_fun365__t {
  struct kk_function_s _base;
  kk_function_t action;
  kk_function_t init;
};
static kk_box_t kk_std_core_hnd_initially_fun365(kk_function_t _fself, kk_box_t _b_x18, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_initially_fun365(kk_function_t action, kk_function_t init, kk_context_t* _ctx) {
  struct kk_std_core_hnd_initially_fun365__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_initially_fun365__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_initially_fun365, kk_context());
  _self->action = action;
  _self->init = init;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_initially_fun365(kk_function_t _fself, kk_box_t _b_x18, kk_context_t* _ctx) {
  struct kk_std_core_hnd_initially_fun365__t* _self = kk_function_as(struct kk_std_core_hnd_initially_fun365__t*, _fself, _ctx);
  kk_function_t action = _self->action; /* () -> 4695 4694 */
  kk_function_t init = _self->init; /* (int) -> 4695 () */
  kk_drop_match(_self, {kk_function_dup(action, _ctx);kk_function_dup(init, _ctx);}, {}, _ctx)
  kk_box_drop(_b_x18, _ctx);
  kk_box_t _x_x366 = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), action, (action, _ctx), _ctx); /*4694*/
  return kk_std_core_hnd_initially_prompt(init, _x_x366, _ctx);
}

kk_box_t kk_std_core_hnd_initially(kk_function_t init, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e> (init : (int) -> e (), action : () -> e a) -> e a */ 
  kk_unit_t __ = kk_Unit;
  kk_function_t _x_x364 = kk_function_dup(init, _ctx); /*(int) -> 4695 ()*/
  kk_function_call(kk_unit_t, (kk_function_t, kk_integer_t, kk_context_t*), _x_x364, (_x_x364, kk_integer_from_small(0), _ctx), _ctx);
  if (kk_yielding(kk_context())) {
    return kk_std_core_hnd_yield_extend(kk_std_core_hnd_new_initially_fun365(action, init, _ctx), _ctx);
  }
  {
    kk_box_t _x_x367 = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), action, (action, _ctx), _ctx); /*4694*/
    return kk_std_core_hnd_initially_prompt(init, _x_x367, _ctx);
  }
}


// lift anonymous function
struct kk_std_core_hnd_resume_context_fs__copy_fun369__t {
  struct kk_function_s _base;
  kk_box_t _fun_unbox_x24;
};
static kk_box_t kk_std_core_hnd_resume_context_fs__copy_fun369(kk_function_t _fself, kk_std_core_hnd__resume_result _b_x27, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_resume_context_fs__new_copy_fun369(kk_box_t _fun_unbox_x24, kk_context_t* _ctx) {
  struct kk_std_core_hnd_resume_context_fs__copy_fun369__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_resume_context_fs__copy_fun369__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_resume_context_fs__copy_fun369, kk_context());
  _self->_fun_unbox_x24 = _fun_unbox_x24;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_resume_context_fs__copy_fun369(kk_function_t _fself, kk_std_core_hnd__resume_result _b_x27, kk_context_t* _ctx) {
  struct kk_std_core_hnd_resume_context_fs__copy_fun369__t* _self = kk_function_as(struct kk_std_core_hnd_resume_context_fs__copy_fun369__t*, _fself, _ctx);
  kk_box_t _fun_unbox_x24 = _self->_fun_unbox_x24; /* 7 */
  kk_drop_match(_self, {kk_box_dup(_fun_unbox_x24, _ctx);}, {}, _ctx)
  kk_function_t _x_x370 = kk_function_unbox(_fun_unbox_x24, _ctx); /*(25) -> 4814 26*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x370, (_x_x370, kk_std_core_hnd__resume_result_box(_b_x27, _ctx), _ctx), _ctx);
}

kk_std_core_hnd__resume_context kk_std_core_hnd_resume_context_fs__copy(kk_std_core_hnd__resume_context _this, kk_std_core_types__optional k, kk_context_t* _ctx) { /* forall<a,e,e1,b> (resume-context<a,e,e1,b>, k : ? ((resume-result<a,b>) -> e b)) -> resume-context<a,e,e1,b> */ 
  kk_function_t _x_x368;
  if (kk_std_core_types__is_Optional(k, _ctx)) {
    kk_box_t _fun_unbox_x24 = k._cons._Optional.value;
    kk_box_dup(_fun_unbox_x24, _ctx);
    kk_std_core_types__optional_drop(k, _ctx);
    kk_std_core_hnd__resume_context_drop(_this, _ctx);
    _x_x368 = kk_std_core_hnd_resume_context_fs__new_copy_fun369(_fun_unbox_x24, _ctx); /*(hnd/resume-result<4813,4816>) -> 4814 26*/
  }
  else {
    kk_std_core_types__optional_drop(k, _ctx);
    {
      kk_function_t _x = _this.k;
      _x_x368 = _x; /*(hnd/resume-result<4813,4816>) -> 4814 26*/
    }
  }
  return kk_std_core_hnd__new_Resume_context(_x_x368, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause1_fs__copy_fun375__t {
  struct kk_function_s _base;
  kk_box_t _fun_unbox_x35;
};
static kk_box_t kk_std_core_hnd_clause1_fs__copy_fun375(kk_function_t _fself, int32_t _b_x40, kk_std_core_hnd__ev _b_x41, kk_box_t _b_x42, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_clause1_fs__new_copy_fun375(kk_box_t _fun_unbox_x35, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause1_fs__copy_fun375__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause1_fs__copy_fun375__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause1_fs__copy_fun375, kk_context());
  _self->_fun_unbox_x35 = _fun_unbox_x35;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause1_fs__copy_fun375(kk_function_t _fself, int32_t _b_x40, kk_std_core_hnd__ev _b_x41, kk_box_t _b_x42, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause1_fs__copy_fun375__t* _self = kk_function_as(struct kk_std_core_hnd_clause1_fs__copy_fun375__t*, _fself, _ctx);
  kk_box_t _fun_unbox_x35 = _self->_fun_unbox_x35; /* 7 */
  kk_drop_match(_self, {kk_box_dup(_fun_unbox_x35, _ctx);}, {}, _ctx)
  kk_function_t _x_x376 = kk_function_unbox(_fun_unbox_x35, _ctx); /*(36, 37, 38) -> 5180 39*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), _x_x376, (_x_x376, kk_int32_box(_b_x40, _ctx), kk_std_core_hnd__ev_box(_b_x41, _ctx), _b_x42, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause1_fs__copy(kk_std_core_hnd__clause1 _this, kk_std_core_types__optional clause, kk_context_t* _ctx) { /* forall<a,b,c,e,d> (clause1<a,b,c,e,d>, clause : ? ((marker<e,d>, ev<c>, a) -> e b)) -> clause1<a,b,c,e,d> */ 
  kk_function_t _x_x374;
  if (kk_std_core_types__is_Optional(clause, _ctx)) {
    kk_box_t _fun_unbox_x35 = clause._cons._Optional.value;
    kk_box_dup(_fun_unbox_x35, _ctx);
    kk_std_core_types__optional_drop(clause, _ctx);
    kk_std_core_hnd__clause1_drop(_this, _ctx);
    _x_x374 = kk_std_core_hnd_clause1_fs__new_copy_fun375(_fun_unbox_x35, _ctx); /*(hnd/marker<5180,5181>, hnd/ev<5179>, 5177) -> 5180 39*/
  }
  else {
    kk_std_core_types__optional_drop(clause, _ctx);
    {
      kk_function_t _x = _this.clause;
      _x_x374 = _x; /*(hnd/marker<5180,5181>, hnd/ev<5179>, 5177) -> 5180 39*/
    }
  }
  return kk_std_core_hnd__new_Clause1(_x_x374, _ctx);
}

kk_evv_t kk_std_core_hnd_evv_swap_with(kk_std_core_hnd__ev ev, kk_context_t* _ctx) { /* forall<a,e> (ev : ev<a>) -> evv<e> */ 
  kk_evv_t _x_x378;
  {
    struct kk_std_core_hnd_Ev* _con_x379 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_std_core_hnd__htag _pat_0 = _con_x379->htag;
    kk_box_t _pat_2 = _con_x379->hnd;
    kk_evv_t w = _con_x379->hevv;
    if kk_likely(kk_datatype_ptr_is_unique(ev, _ctx)) {
      kk_box_drop(_pat_2, _ctx);
      kk_std_core_hnd__htag_drop(_pat_0, _ctx);
      kk_datatype_ptr_free(ev, _ctx);
    }
    else {
      kk_evv_dup(w, _ctx);
      kk_datatype_ptr_decref(ev, _ctx);
    }
    _x_x378 = w; /*hnd/evv<5330>*/
  }
  return kk_evv_swap(_x_x378,kk_context());
}
 
// extra under1x to make under1 inlineable


// lift anonymous function
struct kk_std_core_hnd_under1x_fun382__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under1x_fun382(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under1x_fun382(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under1x_fun382__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under1x_fun382__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under1x_fun382, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_under1x_fun382(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under1x_fun382__t* _self = kk_function_as(struct kk_std_core_hnd_under1x_fun382__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<5453> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd_under1x(kk_std_core_hnd__ev ev, kk_function_t op, kk_box_t x, kk_context_t* _ctx) { /* forall<a,b,e,c> (ev : ev<c>, op : (a) -> e b, x : a) -> e b */ 
  kk_evv_t w0;
  kk_evv_t _x_x380;
  {
    struct kk_std_core_hnd_Ev* _con_x381 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w = _con_x381->hevv;
    kk_evv_dup(w, _ctx);
    _x_x380 = w; /*hnd/evv<5330>*/
  }
  w0 = kk_evv_swap(_x_x380,kk_context()); /*hnd/evv<_5364>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), op, (op, x, _ctx), _ctx); /*5451*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    kk_evv_drop(w0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under1x_fun382(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0,kk_context());
    return y;
  }
}
extern kk_box_t kk_std_core_hnd_under1_fun385(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under1_fun385__t* _self = kk_function_as(struct kk_std_core_hnd_under1_fun385__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<5566> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont, res, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_control_raw1_fun386__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control_raw1_fun386(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x597__16, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw1_fun386(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw1_fun386__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw1_fun386__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw1_fun386, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control_raw1_fun387__t {
  struct kk_function_s _base;
  kk_function_t op;
  kk_box_t x;
};
static kk_box_t kk_std_core_hnd_clause_control_raw1_fun387(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw1_fun387(kk_function_t op, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw1_fun387__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw1_fun387__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw1_fun387, kk_context());
  _self->op = op;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control_raw1_fun387(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw1_fun387__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw1_fun387__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x : 5664, r : hnd/resume-context<5665,5666,5667,5669>) -> 5666 5669 */
  kk_box_t x = _self->x; /* 5664 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);kk_box_dup(x, _ctx);}, {}, _ctx)
  kk_std_core_hnd__resume_context _x_x388 = kk_std_core_hnd__new_Resume_context(k, _ctx); /*hnd/resume-context<83,84,85,86>*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_std_core_hnd__resume_context, kk_context_t*), op, (op, x, _x_x388, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control_raw1_fun386(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x597__16, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw1_fun386__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw1_fun386__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x : 5664, r : hnd/resume-context<5665,5666,5667,5669>) -> 5666 5669 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x597__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(m, kk_std_core_hnd_new_clause_control_raw1_fun387(op, x, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_control_raw1(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,e,e1,c,d> (op : (x : a, r : resume-context<b,e,e1,d>) -> e d) -> clause1<a,b,c,e,d> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_control_raw1_fun386(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_protect_prompt_fun391__t {
  struct kk_function_s _base;
  kk_function_t k;
  kk_ref_t resumed;
};
static kk_box_t kk_std_core_hnd_protect_prompt_fun391(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_protect_prompt_fun391(kk_function_t k, kk_ref_t resumed, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect_prompt_fun391__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_protect_prompt_fun391__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_protect_prompt_fun391, kk_context());
  _self->k = k;
  _self->resumed = resumed;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_protect_prompt_fun391(kk_function_t _fself, kk_function_t cont, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect_prompt_fun391__t* _self = kk_function_as(struct kk_std_core_hnd_protect_prompt_fun391__t*, _fself, _ctx);
  kk_function_t k = _self->k; /* (hnd/resume-result<5916,5918>) -> 5917 5918 */
  kk_ref_t resumed = _self->resumed; /* ref<global,bool> */
  kk_drop_match(_self, {kk_function_dup(k, _ctx);kk_ref_dup(resumed, _ctx);}, {}, _ctx)
  kk_box_t _x_x392 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, x, _ctx), _ctx); /*5918*/
  return kk_std_core_hnd_protect_prompt(resumed, k, _x_x392, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_protect_prompt_fun394__t {
  struct kk_function_s _base;
  kk_std_core_hnd__yield_info yld;
};
static kk_box_t kk_std_core_hnd_protect_prompt_fun394(kk_function_t _fself, kk_box_t ___wildcard_x620__43, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_protect_prompt_fun394(kk_std_core_hnd__yield_info yld, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect_prompt_fun394__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_protect_prompt_fun394__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_protect_prompt_fun394, kk_context());
  _self->yld = yld;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_protect_prompt_fun394(kk_function_t _fself, kk_box_t ___wildcard_x620__43, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect_prompt_fun394__t* _self = kk_function_as(struct kk_std_core_hnd_protect_prompt_fun394__t*, _fself, _ctx);
  kk_std_core_hnd__yield_info yld = _self->yld; /* hnd/yield-info */
  kk_drop_match(_self, {kk_std_core_hnd__yield_info_dup(yld, _ctx);}, {}, _ctx)
  kk_box_drop(___wildcard_x620__43, _ctx);
  return kk_std_core_hnd_unsafe_reyield(yld, _ctx);
}

kk_box_t kk_std_core_hnd_protect_prompt(kk_ref_t resumed, kk_function_t k, kk_box_t res, kk_context_t* _ctx) { /* forall<a,e,b> (resumed : ref<global,bool>, k : (resume-result<a,b>) -> e b, res : b) -> e b */ 
  bool did_resume;
  kk_box_t _x_x389;
  kk_ref_t _x_x390 = kk_ref_dup(resumed, _ctx); /*ref<global,bool>*/
  _x_x389 = kk_ref_get(_x_x390,kk_context()); /*212*/
  did_resume = kk_bool_unbox(_x_x389); /*bool*/
  if (did_resume) {
    kk_ref_drop(resumed, _ctx);
    kk_function_drop(k, _ctx);
    return res;
  }
  if (kk_yielding(kk_context())) {
    bool _match_x245 = kk_yielding_non_final(kk_context()); /*bool*/;
    if (_match_x245) {
      kk_box_drop(res, _ctx);
      return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_protect_prompt_fun391(k, resumed, _ctx), _ctx);
    }
    {
      kk_ref_drop(resumed, _ctx);
      kk_std_core_hnd__yield_info yld = kk_std_core_hnd_yield_capture(_ctx); /*hnd/yield-info*/;
      kk_box_t __;
      kk_std_core_hnd__resume_result _x_x393 = kk_std_core_hnd__new_Finalize(res, _ctx); /*hnd/resume-result<74,75>*/
      __ = kk_function_call(kk_box_t, (kk_function_t, kk_std_core_hnd__resume_result, kk_context_t*), k, (k, _x_x393, _ctx), _ctx); /*5918*/
      kk_box_drop(__, _ctx);
      if (kk_yielding(kk_context())) {
        return kk_std_core_hnd_yield_extend(kk_std_core_hnd_new_protect_prompt_fun394(yld, _ctx), _ctx);
      }
      {
        return kk_std_core_hnd_unsafe_reyield(yld, _ctx);
      }
    }
  }
  {
    kk_ref_drop(resumed, _ctx);
    kk_std_core_hnd__resume_result _x_x395 = kk_std_core_hnd__new_Finalize(res, _ctx); /*hnd/resume-result<74,75>*/
    return kk_function_call(kk_box_t, (kk_function_t, kk_std_core_hnd__resume_result, kk_context_t*), k, (k, _x_x395, _ctx), _ctx);
  }
}


// lift anonymous function
struct kk_std_core_hnd_protect_fun397__t {
  struct kk_function_s _base;
  kk_function_t k;
  kk_ref_t resumed;
};
static kk_box_t kk_std_core_hnd_protect_fun397(kk_function_t _fself, kk_box_t ret, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_protect_fun397(kk_function_t k, kk_ref_t resumed, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect_fun397__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_protect_fun397__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_protect_fun397, kk_context());
  _self->k = k;
  _self->resumed = resumed;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_protect_fun397(kk_function_t _fself, kk_box_t ret, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect_fun397__t* _self = kk_function_as(struct kk_std_core_hnd_protect_fun397__t*, _fself, _ctx);
  kk_function_t k = _self->k; /* (hnd/resume-result<6036,6038>) -> 6037 6038 */
  kk_ref_t resumed = _self->resumed; /* ref<global,bool> */
  kk_drop_match(_self, {kk_function_dup(k, _ctx);kk_ref_dup(resumed, _ctx);}, {}, _ctx)
  kk_unit_t __ = kk_Unit;
  kk_unit_t _brw_x244 = kk_Unit;
  kk_ref_set_borrow(resumed,(kk_bool_box(true)),kk_context());
  kk_ref_drop(resumed, _ctx);
  _brw_x244;
  kk_std_core_hnd__resume_result _x_x398 = kk_std_core_hnd__new_Deep(ret, _ctx); /*hnd/resume-result<74,75>*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_std_core_hnd__resume_result, kk_context_t*), k, (k, _x_x398, _ctx), _ctx);
}

kk_box_t kk_std_core_hnd_protect(kk_box_t x, kk_function_t clause, kk_function_t k, kk_context_t* _ctx) { /* forall<a,b,e,c> (x : a, clause : (x : a, k : (b) -> e c) -> e c, k : (resume-result<b,c>) -> e c) -> e c */ 
  kk_ref_t resumed = kk_ref_alloc((kk_bool_box(false)),kk_context()); /*ref<global,bool>*/;
  kk_box_t res;
  kk_function_t _x_x396;
  kk_function_dup(k, _ctx);
  kk_ref_dup(resumed, _ctx);
  _x_x396 = kk_std_core_hnd_new_protect_fun397(k, resumed, _ctx); /*(ret : 6036) -> 6037 6038*/
  res = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_function_t, kk_context_t*), clause, (clause, x, _x_x396, _ctx), _ctx); /*6038*/
  return kk_std_core_hnd_protect_prompt(resumed, k, res, _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_control1_fun400(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control1_fun400__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control1_fun400__t*, _fself, _ctx);
  kk_function_t clause = _self->clause; /* (x : 6128, k : (6129) -> 6130 6132) -> 6130 6132 */
  kk_box_t x = _self->x; /* 6128 */
  kk_drop_match(_self, {kk_function_dup(clause, _ctx);kk_box_dup(x, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_protect(x, clause, k, _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_control1_fun399(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x638__16, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control1_fun399__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control1_fun399__t*, _fself, _ctx);
  kk_function_t clause = _self->clause; /* (x : 6128, k : (6129) -> 6130 6132) -> 6130 6132 */
  kk_drop_match(_self, {kk_function_dup(clause, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x638__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(m, kk_std_core_hnd_new_clause_control1_fun400(clause, x, _ctx), _ctx);
}
 
// tail-resumptive clause: resumes exactly once at the end
// (these can be executed 'in-place' without capturing a resumption)


// lift anonymous function
struct kk_std_core_hnd_clause_tail1_fun401__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_tail1_fun401(kk_function_t _fself, int32_t ___wildcard_x643__14, kk_std_core_hnd__ev ev, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail1_fun401(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail1_fun401__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail1_fun401__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail1_fun401, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_tail1_fun404__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_clause_tail1_fun404(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail1_fun404(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail1_fun404__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail1_fun404__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail1_fun404, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_tail1_fun404(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail1_fun404__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail1_fun404__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<6215> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont, res, _ctx);
}
static kk_box_t kk_std_core_hnd_clause_tail1_fun401(kk_function_t _fself, int32_t ___wildcard_x643__14, kk_std_core_hnd__ev ev, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail1_fun401__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail1_fun401__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (6216) -> 6213 6217 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_evv_t w0;
  kk_evv_t _x_x402;
  {
    struct kk_std_core_hnd_Ev* _con_x403 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w = _con_x403->hevv;
    kk_evv_dup(w, _ctx);
    _x_x402 = w; /*hnd/evv<5330>*/
  }
  w0 = kk_evv_swap(_x_x402,kk_context()); /*hnd/evv<_5477>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), op, (op, x, _ctx), _ctx); /*6217*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    kk_evv_drop(w0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_clause_tail1_fun404(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0,kk_context());
    return y;
  }
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_tail1(kk_function_t op, kk_context_t* _ctx) { /* forall<e,a,b,c,d> (op : (c) -> e d) -> clause1<c,d,b,e,a> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_tail1_fun401(op, _ctx), _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_tail_noop1_fun405(kk_function_t _fself, int32_t ___wildcard_x648__14, kk_std_core_hnd__ev ___wildcard_x648__17, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail_noop1_fun405__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail_noop1_fun405__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (6287) -> 6284 6288 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x648__17, (KK_I32(3)), _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), op, (op, x, _ctx), _ctx);
}
 
// clause that never resumes (e.g. an exception handler)
// (these do not need to capture a resumption and execute finally clauses upfront)


// lift anonymous function
struct kk_std_core_hnd_clause_never1_fun406__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never1_fun406(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x653__16, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never1_fun406(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never1_fun406__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never1_fun406__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never1_fun406, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_never1_fun407__t {
  struct kk_function_s _base;
  kk_function_t op;
  kk_box_t x;
};
static kk_box_t kk_std_core_hnd_clause_never1_fun407(kk_function_t _fself, kk_function_t ___wildcard_x653__45, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never1_fun407(kk_function_t op, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never1_fun407__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never1_fun407__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never1_fun407, kk_context());
  _self->op = op;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_never1_fun407(kk_function_t _fself, kk_function_t ___wildcard_x653__45, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never1_fun407__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never1_fun407__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (6371) -> 6373 6375 */
  kk_box_t x = _self->x; /* 6371 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);kk_box_dup(x, _ctx);}, {}, _ctx)
  kk_function_drop(___wildcard_x653__45, _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), op, (op, x, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_never1_fun406(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x653__16, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never1_fun406__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never1_fun406__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (6371) -> 6373 6375 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x653__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to_final(m, kk_std_core_hnd_new_clause_never1_fun407(op, x, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_never1(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,e,c,d> (op : (a) -> e d) -> clause1<a,b,c,e,d> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_never1_fun406(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause0_fs__copy_fun409__t {
  struct kk_function_s _base;
  kk_box_t _fun_unbox_x58;
};
static kk_box_t kk_std_core_hnd_clause0_fs__copy_fun409(kk_function_t _fself, int32_t _b_x62, kk_std_core_hnd__ev _b_x63, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_clause0_fs__new_copy_fun409(kk_box_t _fun_unbox_x58, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause0_fs__copy_fun409__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause0_fs__copy_fun409__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause0_fs__copy_fun409, kk_context());
  _self->_fun_unbox_x58 = _fun_unbox_x58;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause0_fs__copy_fun409(kk_function_t _fself, int32_t _b_x62, kk_std_core_hnd__ev _b_x63, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause0_fs__copy_fun409__t* _self = kk_function_as(struct kk_std_core_hnd_clause0_fs__copy_fun409__t*, _fself, _ctx);
  kk_box_t _fun_unbox_x58 = _self->_fun_unbox_x58; /* 7 */
  kk_drop_match(_self, {kk_box_dup(_fun_unbox_x58, _ctx);}, {}, _ctx)
  kk_function_t _x_x410 = kk_function_unbox(_fun_unbox_x58, _ctx); /*(59, 60) -> 6505 61*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x410, (_x_x410, kk_int32_box(_b_x62, _ctx), kk_std_core_hnd__ev_box(_b_x63, _ctx), _ctx), _ctx);
}

kk_std_core_hnd__clause0 kk_std_core_hnd_clause0_fs__copy(kk_std_core_hnd__clause0 _this, kk_std_core_types__optional clause, kk_context_t* _ctx) { /* forall<a,b,e,c> (clause0<a,b,e,c>, clause : ? ((marker<e,c>, ev<b>) -> e a)) -> clause0<a,b,e,c> */ 
  kk_function_t _x_x408;
  if (kk_std_core_types__is_Optional(clause, _ctx)) {
    kk_box_t _fun_unbox_x58 = clause._cons._Optional.value;
    kk_box_dup(_fun_unbox_x58, _ctx);
    kk_std_core_types__optional_drop(clause, _ctx);
    kk_std_core_hnd__clause0_drop(_this, _ctx);
    _x_x408 = kk_std_core_hnd_clause0_fs__new_copy_fun409(_fun_unbox_x58, _ctx); /*(hnd/marker<6505,6506>, hnd/ev<6504>) -> 6505 61*/
  }
  else {
    kk_std_core_types__optional_drop(clause, _ctx);
    {
      kk_function_t _x = _this.clause;
      _x_x408 = _x; /*(hnd/marker<6505,6506>, hnd/ev<6504>) -> 6505 61*/
    }
  }
  return kk_std_core_hnd__new_Clause0(_x_x408, _ctx);
}
extern kk_box_t kk_std_core_hnd_under0_fun417(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under0_fun417__t* _self = kk_function_as(struct kk_std_core_hnd_under0_fun417__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<6697> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont_0, res_0, _ctx);
}
extern kk_box_t kk_std_core_hnd_under0_fun414(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under0_fun414__t* _self = kk_function_as(struct kk_std_core_hnd_under0_fun414__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<6697> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  kk_evv_t w0_0;
  kk_evv_t _x_x415;
  {
    struct kk_std_core_hnd_Ev* _con_x416 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w_0 = _con_x416->hevv;
    kk_evv_dup(w_0, _ctx);
    _x_x415 = w_0; /*hnd/evv<5330>*/
  }
  w0_0 = kk_evv_swap(_x_x415,kk_context()); /*hnd/evv<_5477>*/
  kk_box_t y_0 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, res, _ctx), _ctx); /*6695*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y_0, _ctx);
    kk_evv_drop(w0_0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under0_fun417(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0_0,kk_context());
    return y_0;
  }
}


// lift anonymous function
struct kk_std_core_hnd_clause_control_raw0_fun418__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control_raw0_fun418(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x679__16, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw0_fun418(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw0_fun418__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw0_fun418__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw0_fun418, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control_raw0_fun419__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control_raw0_fun419(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw0_fun419(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw0_fun419__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw0_fun419__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw0_fun419, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control_raw0_fun419(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw0_fun419__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw0_fun419__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (hnd/resume-context<6783,6784,6785,6787>) -> 6784 6787 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_std_core_hnd__resume_context _x_x420 = kk_std_core_hnd__new_Resume_context(k, _ctx); /*hnd/resume-context<83,84,85,86>*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_std_core_hnd__resume_context, kk_context_t*), op, (op, _x_x420, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control_raw0_fun418(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x679__16, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw0_fun418__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw0_fun418__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (hnd/resume-context<6783,6784,6785,6787>) -> 6784 6787 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x679__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(m, kk_std_core_hnd_new_clause_control_raw0_fun419(op, _ctx), _ctx);
}

kk_std_core_hnd__clause0 kk_std_core_hnd_clause_control_raw0(kk_function_t op, kk_context_t* _ctx) { /* forall<a,e,e1,b,c> (op : (resume-context<a,e,e1,c>) -> e c) -> clause0<a,b,e,c> */ 
  return kk_std_core_hnd__new_Clause0(kk_std_core_hnd_new_clause_control_raw0_fun418(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_control0_fun421__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control0_fun421(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x687__16, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control0_fun421(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control0_fun421__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control0_fun421__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control0_fun421, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control0_fun422__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control0_fun422(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control0_fun422(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control0_fun422__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control0_fun422__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control0_fun422, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control0_fun423__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control0_fun423(kk_function_t _fself, kk_box_t _b_x67, kk_function_t _b_x68, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control0_fun423(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control0_fun423__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control0_fun423__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control0_fun423, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control0_fun423(kk_function_t _fself, kk_box_t _b_x67, kk_function_t _b_x68, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control0_fun423__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control0_fun423__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* ((6876) -> 6877 6879) -> 6877 6879 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_box_drop(_b_x67, _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_function_t, kk_context_t*), op, (op, _b_x68, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control0_fun422(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control0_fun422__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control0_fun422__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* ((6876) -> 6877 6879) -> 6877 6879 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_protect(kk_unit_box(kk_Unit), kk_std_core_hnd_new_clause_control0_fun423(op, _ctx), k, _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control0_fun421(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x687__16, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control0_fun421__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control0_fun421__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* ((6876) -> 6877 6879) -> 6877 6879 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x687__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(m, kk_std_core_hnd_new_clause_control0_fun422(op, _ctx), _ctx);
}

kk_std_core_hnd__clause0 kk_std_core_hnd_clause_control0(kk_function_t op, kk_context_t* _ctx) { /* forall<a,e,b,c> (op : ((a) -> e c) -> e c) -> clause0<a,b,e,c> */ 
  return kk_std_core_hnd__new_Clause0(kk_std_core_hnd_new_clause_control0_fun421(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_tail0_fun424__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_tail0_fun424(kk_function_t _fself, int32_t ___wildcard_x691__14, kk_std_core_hnd__ev ev, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail0_fun424(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail0_fun424__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail0_fun424__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail0_fun424, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_tail0_fun427__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_clause_tail0_fun427(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail0_fun427(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail0_fun427__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail0_fun427__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail0_fun427, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_tail0_fun430__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_clause_tail0_fun430(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail0_fun430(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail0_fun430__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail0_fun430__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail0_fun430, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_tail0_fun430(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail0_fun430__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail0_fun430__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<6947> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont_0, res_0, _ctx);
}
static kk_box_t kk_std_core_hnd_clause_tail0_fun427(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail0_fun427__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail0_fun427__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<6947> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  kk_evv_t w0_0;
  kk_evv_t _x_x428;
  {
    struct kk_std_core_hnd_Ev* _con_x429 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w_0 = _con_x429->hevv;
    kk_evv_dup(w_0, _ctx);
    _x_x428 = w_0; /*hnd/evv<5330>*/
  }
  w0_0 = kk_evv_swap(_x_x428,kk_context()); /*hnd/evv<_5477>*/
  kk_box_t y_0 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, res, _ctx), _ctx); /*6948*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y_0, _ctx);
    kk_evv_drop(w0_0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_clause_tail0_fun430(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0_0,kk_context());
    return y_0;
  }
}
static kk_box_t kk_std_core_hnd_clause_tail0_fun424(kk_function_t _fself, int32_t ___wildcard_x691__14, kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail0_fun424__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail0_fun424__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* () -> 6945 6948 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_evv_t w0;
  kk_evv_t _x_x425;
  {
    struct kk_std_core_hnd_Ev* _con_x426 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w = _con_x426->hevv;
    kk_evv_dup(w, _ctx);
    _x_x425 = w; /*hnd/evv<5330>*/
  }
  w0 = kk_evv_swap(_x_x425,kk_context()); /*hnd/evv<_6621>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), op, (op, _ctx), _ctx); /*6948*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w0,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_clause_tail0_fun427(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    return y;
  }
}

kk_std_core_hnd__clause0 kk_std_core_hnd_clause_tail0(kk_function_t op, kk_context_t* _ctx) { /* forall<e,a,b,c> (op : () -> e c) -> clause0<c,b,e,a> */ 
  return kk_std_core_hnd__new_Clause0(kk_std_core_hnd_new_clause_tail0_fun424(op, _ctx), _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_tail_noop0_fun431(kk_function_t _fself, int32_t ___wildcard_x694__14, kk_std_core_hnd__ev ___wildcard_x694__17, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail_noop0_fun431__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail_noop0_fun431__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* () -> 7003 7006 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x694__17, (KK_I32(3)), _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), op, (op, _ctx), _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_value_fun432(kk_function_t _fself, int32_t ___wildcard_x697__14, kk_std_core_hnd__ev ___wildcard_x697__17, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_value_fun432__t* _self = kk_function_as(struct kk_std_core_hnd_clause_value_fun432__t*, _fself, _ctx);
  kk_box_t v = _self->v; /* 7060 */
  kk_drop_match(_self, {kk_box_dup(v, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x697__17, (KK_I32(3)), _ctx);
  return v;
}


// lift anonymous function
struct kk_std_core_hnd_clause_never0_fun433__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never0_fun433(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x700__16, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never0_fun433(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never0_fun433__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never0_fun433__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never0_fun433, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_never0_fun434__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never0_fun434(kk_function_t _fself, kk_function_t ___wildcard_x700__43, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never0_fun434(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never0_fun434__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never0_fun434__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never0_fun434, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_never0_fun434(kk_function_t _fself, kk_function_t ___wildcard_x700__43, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never0_fun434__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never0_fun434__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* () -> 7135 7137 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_function_drop(___wildcard_x700__43, _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), op, (op, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_never0_fun433(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x700__16, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never0_fun433__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never0_fun433__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* () -> 7135 7137 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x700__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to_final(m, kk_std_core_hnd_new_clause_never0_fun434(op, _ctx), _ctx);
}

kk_std_core_hnd__clause0 kk_std_core_hnd_clause_never0(kk_function_t op, kk_context_t* _ctx) { /* forall<a,e,b,c> (op : () -> e c) -> clause0<a,b,e,c> */ 
  return kk_std_core_hnd__new_Clause0(kk_std_core_hnd_new_clause_never0_fun433(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause2_fs__copy_fun436__t {
  struct kk_function_s _base;
  kk_box_t _fun_unbox_x83;
};
static kk_box_t kk_std_core_hnd_clause2_fs__copy_fun436(kk_function_t _fself, int32_t _b_x89, kk_std_core_hnd__ev _b_x90, kk_box_t _b_x91, kk_box_t _b_x92, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_clause2_fs__new_copy_fun436(kk_box_t _fun_unbox_x83, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause2_fs__copy_fun436__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause2_fs__copy_fun436__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause2_fs__copy_fun436, kk_context());
  _self->_fun_unbox_x83 = _fun_unbox_x83;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause2_fs__copy_fun436(kk_function_t _fself, int32_t _b_x89, kk_std_core_hnd__ev _b_x90, kk_box_t _b_x91, kk_box_t _b_x92, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause2_fs__copy_fun436__t* _self = kk_function_as(struct kk_std_core_hnd_clause2_fs__copy_fun436__t*, _fself, _ctx);
  kk_box_t _fun_unbox_x83 = _self->_fun_unbox_x83; /* 7 */
  kk_drop_match(_self, {kk_box_dup(_fun_unbox_x83, _ctx);}, {}, _ctx)
  kk_function_t _x_x437 = kk_function_unbox(_fun_unbox_x83, _ctx); /*(84, 85, 86, 87) -> 7310 88*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), _x_x437, (_x_x437, kk_int32_box(_b_x89, _ctx), kk_std_core_hnd__ev_box(_b_x90, _ctx), _b_x91, _b_x92, _ctx), _ctx);
}

kk_std_core_hnd__clause2 kk_std_core_hnd_clause2_fs__copy(kk_std_core_hnd__clause2 _this, kk_std_core_types__optional clause, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (clause2<a,b,c,d,e,a1>, clause : ? ((marker<e,a1>, ev<d>, a, b) -> e c)) -> clause2<a,b,c,d,e,a1> */ 
  kk_function_t _x_x435;
  if (kk_std_core_types__is_Optional(clause, _ctx)) {
    kk_box_t _fun_unbox_x83 = clause._cons._Optional.value;
    kk_box_dup(_fun_unbox_x83, _ctx);
    kk_std_core_types__optional_drop(clause, _ctx);
    kk_std_core_hnd__clause2_drop(_this, _ctx);
    _x_x435 = kk_std_core_hnd_clause2_fs__new_copy_fun436(_fun_unbox_x83, _ctx); /*(hnd/marker<7310,7311>, hnd/ev<7309>, 7306, 7307) -> 7310 88*/
  }
  else {
    kk_std_core_types__optional_drop(clause, _ctx);
    {
      kk_function_t _x = _this.clause;
      _x_x435 = _x; /*(hnd/marker<7310,7311>, hnd/ev<7309>, 7306, 7307) -> 7310 88*/
    }
  }
  return kk_std_core_hnd__new_Clause2(_x_x435, _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_under2_fun440__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under2_fun440(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under2_fun440(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under2_fun440__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under2_fun440__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under2_fun440, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_under2_fun443__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under2_fun443(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under2_fun443(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under2_fun443__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under2_fun443__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under2_fun443, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_under2_fun443(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under2_fun443__t* _self = kk_function_as(struct kk_std_core_hnd_under2_fun443__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<7431> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont_0, res_0, _ctx);
}
static kk_box_t kk_std_core_hnd_under2_fun440(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under2_fun440__t* _self = kk_function_as(struct kk_std_core_hnd_under2_fun440__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<7431> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  kk_evv_t w0_0;
  kk_evv_t _x_x441;
  {
    struct kk_std_core_hnd_Ev* _con_x442 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w_0 = _con_x442->hevv;
    kk_evv_dup(w_0, _ctx);
    _x_x441 = w_0; /*hnd/evv<5330>*/
  }
  w0_0 = kk_evv_swap(_x_x441,kk_context()); /*hnd/evv<_5477>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, res, _ctx), _ctx); /*7429*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    kk_evv_drop(w0_0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under2_fun443(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0_0,kk_context());
    return y;
  }
}

kk_box_t kk_std_core_hnd_under2(kk_std_core_hnd__ev ev, kk_function_t op, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) { /* forall<a,b,c,e,d> (ev : ev<d>, op : (a, b) -> e c, x1 : a, x2 : b) -> e c */ 
  kk_evv_t w0;
  kk_evv_t _x_x438;
  {
    struct kk_std_core_hnd_Ev* _con_x439 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w = _con_x439->hevv;
    kk_evv_dup(w, _ctx);
    _x_x438 = w; /*hnd/evv<5330>*/
  }
  w0 = kk_evv_swap(_x_x438,kk_context()); /*hnd/evv<_7343>*/
  kk_box_t z = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, _ctx), _ctx); /*7429*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w0,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(z, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under2_fun440(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    return z;
  }
}


// lift anonymous function
struct kk_std_core_hnd_protect2_fun445__t {
  struct kk_function_s _base;
  kk_function_t k;
  kk_ref_t resumed;
};
static kk_box_t kk_std_core_hnd_protect2_fun445(kk_function_t _fself, kk_box_t ret, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_protect2_fun445(kk_function_t k, kk_ref_t resumed, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect2_fun445__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_protect2_fun445__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_protect2_fun445, kk_context());
  _self->k = k;
  _self->resumed = resumed;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_protect2_fun445(kk_function_t _fself, kk_box_t ret, kk_context_t* _ctx) {
  struct kk_std_core_hnd_protect2_fun445__t* _self = kk_function_as(struct kk_std_core_hnd_protect2_fun445__t*, _fself, _ctx);
  kk_function_t k = _self->k; /* (hnd/resume-result<7562,7564>) -> 7563 7564 */
  kk_ref_t resumed = _self->resumed; /* ref<global,bool> */
  kk_drop_match(_self, {kk_function_dup(k, _ctx);kk_ref_dup(resumed, _ctx);}, {}, _ctx)
  kk_unit_t __ = kk_Unit;
  kk_unit_t _brw_x235 = kk_Unit;
  kk_ref_set_borrow(resumed,(kk_bool_box(true)),kk_context());
  kk_ref_drop(resumed, _ctx);
  _brw_x235;
  kk_std_core_hnd__resume_result _x_x446 = kk_std_core_hnd__new_Deep(ret, _ctx); /*hnd/resume-result<74,75>*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_std_core_hnd__resume_result, kk_context_t*), k, (k, _x_x446, _ctx), _ctx);
}

kk_box_t kk_std_core_hnd_protect2(kk_box_t x1, kk_box_t x2, kk_function_t clause, kk_function_t k, kk_context_t* _ctx) { /* forall<a,b,c,e,d> (x1 : a, x2 : b, clause : (x : a, x : b, k : (c) -> e d) -> e d, k : (resume-result<c,d>) -> e d) -> e d */ 
  kk_ref_t resumed = kk_ref_alloc((kk_bool_box(false)),kk_context()); /*ref<global,bool>*/;
  kk_box_t res;
  kk_function_t _x_x444;
  kk_function_dup(k, _ctx);
  kk_ref_dup(resumed, _ctx);
  _x_x444 = kk_std_core_hnd_new_protect2_fun445(k, resumed, _ctx); /*(ret : 7562) -> 7563 7564*/
  res = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_function_t, kk_context_t*), clause, (clause, x1, x2, _x_x444, _ctx), _ctx); /*7564*/
  return kk_std_core_hnd_protect_prompt(resumed, k, res, _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_control2_fun448(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control2_fun448__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control2_fun448__t*, _fself, _ctx);
  kk_function_t clause = _self->clause; /* (x1 : 7669, x2 : 7670, k : (7671) -> 7672 7674) -> 7672 7674 */
  kk_box_t x1 = _self->x1; /* 7669 */
  kk_box_t x2 = _self->x2; /* 7670 */
  kk_drop_match(_self, {kk_function_dup(clause, _ctx);kk_box_dup(x1, _ctx);kk_box_dup(x2, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_protect2(x1, x2, clause, k, _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_control2_fun447(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x725__16, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control2_fun447__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control2_fun447__t*, _fself, _ctx);
  kk_function_t clause = _self->clause; /* (x1 : 7669, x2 : 7670, k : (7671) -> 7672 7674) -> 7672 7674 */
  kk_drop_match(_self, {kk_function_dup(clause, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x725__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(m, kk_std_core_hnd_new_clause_control2_fun448(clause, x1, x2, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_control_raw2_fun449__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control_raw2_fun449(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x729__16, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw2_fun449(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw2_fun449__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw2_fun449__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw2_fun449, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control_raw2_fun450__t {
  struct kk_function_s _base;
  kk_function_t op;
  kk_box_t x1;
  kk_box_t x2;
};
static kk_box_t kk_std_core_hnd_clause_control_raw2_fun450(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw2_fun450(kk_function_t op, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw2_fun450__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw2_fun450__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw2_fun450, kk_context());
  _self->op = op;
  _self->x1 = x1;
  _self->x2 = x2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control_raw2_fun450(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw2_fun450__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw2_fun450__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 7788, x2 : 7789, r : hnd/resume-context<7790,7791,7792,7794>) -> 7791 7794 */
  kk_box_t x1 = _self->x1; /* 7788 */
  kk_box_t x2 = _self->x2; /* 7789 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);kk_box_dup(x1, _ctx);kk_box_dup(x2, _ctx);}, {}, _ctx)
  kk_std_core_hnd__resume_context _x_x451 = kk_std_core_hnd__new_Resume_context(k, _ctx); /*hnd/resume-context<83,84,85,86>*/
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_std_core_hnd__resume_context, kk_context_t*), op, (op, x1, x2, _x_x451, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control_raw2_fun449(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x729__16, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw2_fun449__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw2_fun449__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 7788, x2 : 7789, r : hnd/resume-context<7790,7791,7792,7794>) -> 7791 7794 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x729__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(m, kk_std_core_hnd_new_clause_control_raw2_fun450(op, x1, x2, _ctx), _ctx);
}

kk_std_core_hnd__clause2 kk_std_core_hnd_clause_control_raw2(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,e,e1,d,a1> (op : (x1 : a, x2 : b, r : resume-context<c,e,e1,a1>) -> e a1) -> clause2<a,b,c,d,e,a1> */ 
  return kk_std_core_hnd__new_Clause2(kk_std_core_hnd_new_clause_control_raw2_fun449(op, _ctx), _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_tail2_fun452(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ev, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail2_fun452__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail2_fun452__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (7896, 7897) -> 7893 7898 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under2(ev, op, x1, x2, _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_tail_noop2_fun453(kk_function_t _fself, int32_t ___wildcard_x735__14, kk_std_core_hnd__ev ___wildcard_x735__17, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail_noop2_fun453__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail_noop2_fun453__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (7980, 7981) -> 7977 7982 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x735__17, (KK_I32(3)), _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_never2_fun455__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never2_fun455(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x743__16, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never2_fun455(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never2_fun455__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never2_fun455__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never2_fun455, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_never2_fun456__t {
  struct kk_function_s _base;
  kk_function_t op;
  kk_box_t x1;
  kk_box_t x2;
};
static kk_box_t kk_std_core_hnd_clause_never2_fun456(kk_function_t _fself, kk_function_t ___wildcard_x743__49, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never2_fun456(kk_function_t op, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never2_fun456__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never2_fun456__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never2_fun456, kk_context());
  _self->op = op;
  _self->x1 = x1;
  _self->x2 = x2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_never2_fun456(kk_function_t _fself, kk_function_t ___wildcard_x743__49, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never2_fun456__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never2_fun456__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (8198, 8199) -> 8201 8203 */
  kk_box_t x1 = _self->x1; /* 8198 */
  kk_box_t x2 = _self->x2; /* 8199 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);kk_box_dup(x1, _ctx);kk_box_dup(x2, _ctx);}, {}, _ctx)
  kk_function_drop(___wildcard_x743__49, _ctx);
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, _ctx), _ctx);
}
static kk_box_t kk_std_core_hnd_clause_never2_fun455(kk_function_t _fself, int32_t m, kk_std_core_hnd__ev ___wildcard_x743__16, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never2_fun455__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never2_fun455__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (8198, 8199) -> 8201 8203 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(___wildcard_x743__16, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to_final(m, kk_std_core_hnd_new_clause_never2_fun456(op, x1, x2, _ctx), _ctx);
}

kk_std_core_hnd__clause2 kk_std_core_hnd_clause_never2(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,e,d,a1> (op : (a, b) -> e a1) -> clause2<a,b,c,d,e,a1> */ 
  return kk_std_core_hnd__new_Clause2(kk_std_core_hnd_new_clause_never2_fun455(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_control_raw3_fun458__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control_raw3_fun458(kk_function_t _fself, int32_t _b_x100, kk_std_core_hnd__ev _b_x101, kk_box_t _b_x102, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw3_fun458(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw3_fun458__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw3_fun458__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw3_fun458, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control_raw3_fun459__t {
  struct kk_function_s _base;
  kk_box_t _b_x102;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control_raw3_fun459(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control_raw3_fun459(kk_box_t _b_x102, kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw3_fun459__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control_raw3_fun459__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control_raw3_fun459, kk_context());
  _self->_b_x102 = _b_x102;
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control_raw3_fun459(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw3_fun459__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw3_fun459__t*, _fself, _ctx);
  kk_box_t _b_x102 = _self->_b_x102; /* 45 */
  kk_function_t op = _self->op; /* (x1 : 8410, x2 : 8411, x3 : 8412, r : hnd/resume-context<8413,8414,8415,8417>) -> 8414 8417 */
  kk_drop_match(_self, {kk_box_dup(_b_x102, _ctx);kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_std_core_types__tuple3 _match_x232 = kk_std_core_types__tuple3_unbox(_b_x102, KK_OWNED, _ctx); /*(8410, 8411, 8412)*/;
  {
    kk_box_t x1 = _match_x232.fst;
    kk_box_t x2 = _match_x232.snd;
    kk_box_t x3 = _match_x232.thd;
    kk_std_core_hnd__resume_context _x_x460 = kk_std_core_hnd__new_Resume_context(k, _ctx); /*hnd/resume-context<83,84,85,86>*/
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_std_core_hnd__resume_context, kk_context_t*), op, (op, x1, x2, x3, _x_x460, _ctx), _ctx);
  }
}
static kk_box_t kk_std_core_hnd_clause_control_raw3_fun458(kk_function_t _fself, int32_t _b_x100, kk_std_core_hnd__ev _b_x101, kk_box_t _b_x102, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control_raw3_fun458__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control_raw3_fun458__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 8410, x2 : 8411, x3 : 8412, r : hnd/resume-context<8413,8414,8415,8417>) -> 8414 8417 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x101, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(_b_x100, kk_std_core_hnd_new_clause_control_raw3_fun459(_b_x102, op, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_control_raw3(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,d,e,e1,a1,b1> (op : (x1 : a, x2 : b, x3 : c, r : resume-context<d,e,e1,b1>) -> e b1) -> clause1<(a, b, c),d,a1,e,b1> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_control_raw3_fun458(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_control3_fun461__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control3_fun461(kk_function_t _fself, int32_t _b_x113, kk_std_core_hnd__ev _b_x114, kk_box_t _b_x115, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control3_fun461(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control3_fun461__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control3_fun461__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control3_fun461, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control3_fun462__t {
  struct kk_function_s _base;
  kk_box_t _b_x115;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control3_fun462(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control3_fun462(kk_box_t _b_x115, kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control3_fun462__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control3_fun462__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control3_fun462, kk_context());
  _self->_b_x115 = _b_x115;
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control3_fun463__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control3_fun463(kk_function_t _fself, kk_box_t _b_x110, kk_function_t _b_x111, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control3_fun463(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control3_fun463__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control3_fun463__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control3_fun463, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control3_fun463(kk_function_t _fself, kk_box_t _b_x110, kk_function_t _b_x111, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control3_fun463__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control3_fun463__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 8516, x2 : 8517, x3 : 8518, k : (8519) -> 8520 8522) -> 8520 8522 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_std_core_types__tuple3 _match_x231 = kk_std_core_types__tuple3_unbox(_b_x110, KK_OWNED, _ctx); /*(8516, 8517, 8518)*/;
  {
    kk_box_t x1 = _match_x231.fst;
    kk_box_t x2 = _match_x231.snd;
    kk_box_t x3 = _match_x231.thd;
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_function_t, kk_context_t*), op, (op, x1, x2, x3, _b_x111, _ctx), _ctx);
  }
}
static kk_box_t kk_std_core_hnd_clause_control3_fun462(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control3_fun462__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control3_fun462__t*, _fself, _ctx);
  kk_box_t _b_x115 = _self->_b_x115; /* 45 */
  kk_function_t op = _self->op; /* (x1 : 8516, x2 : 8517, x3 : 8518, k : (8519) -> 8520 8522) -> 8520 8522 */
  kk_drop_match(_self, {kk_box_dup(_b_x115, _ctx);kk_function_dup(op, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_protect(_b_x115, kk_std_core_hnd_new_clause_control3_fun463(op, _ctx), k, _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control3_fun461(kk_function_t _fself, int32_t _b_x113, kk_std_core_hnd__ev _b_x114, kk_box_t _b_x115, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control3_fun461__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control3_fun461__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 8516, x2 : 8517, x3 : 8518, k : (8519) -> 8520 8522) -> 8520 8522 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x114, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(_b_x113, kk_std_core_hnd_new_clause_control3_fun462(_b_x115, op, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_control3(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1,b1> (op : (x1 : a, x2 : b, x3 : c, k : (d) -> e b1) -> e b1) -> clause1<(a, b, c),d,a1,e,b1> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_control3_fun461(op, _ctx), _ctx);
}
extern kk_box_t kk_std_core_hnd_clause_tail3_fun464(kk_function_t _fself, kk_box_t _b_x126, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail3_fun464__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail3_fun464__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (8620, 8621, 8622) -> 8617 8623 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_std_core_types__tuple3 _match_x230 = kk_std_core_types__tuple3_unbox(_b_x126, KK_OWNED, _ctx); /*(8620, 8621, 8622)*/;
  {
    kk_box_t x1 = _match_x230.fst;
    kk_box_t x2 = _match_x230.snd;
    kk_box_t x3 = _match_x230.thd;
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, _ctx), _ctx);
  }
}
extern kk_box_t kk_std_core_hnd_clause_tail_noop3_fun465(kk_function_t _fself, int32_t _b_x130, kk_std_core_hnd__ev _b_x131, kk_box_t _b_x132, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail_noop3_fun465__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail_noop3_fun465__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (8721, 8722, 8723) -> 8718 8724 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x131, (KK_I32(3)), _ctx);
  kk_std_core_types__tuple3 _match_x229 = kk_std_core_types__tuple3_unbox(_b_x132, KK_OWNED, _ctx); /*(8721, 8722, 8723)*/;
  {
    kk_box_t x1 = _match_x229.fst;
    kk_box_t x2 = _match_x229.snd;
    kk_box_t x3 = _match_x229.thd;
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, _ctx), _ctx);
  }
}


// lift anonymous function
struct kk_std_core_hnd_clause_never3_fun466__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never3_fun466(kk_function_t _fself, int32_t _b_x138, kk_std_core_hnd__ev _b_x139, kk_box_t _b_x140, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never3_fun466(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never3_fun466__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never3_fun466__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never3_fun466, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_never3_fun467__t {
  struct kk_function_s _base;
  kk_box_t _b_x140;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never3_fun467(kk_function_t _fself, kk_function_t ___wildcard_x653__45, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never3_fun467(kk_box_t _b_x140, kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never3_fun467__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never3_fun467__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never3_fun467, kk_context());
  _self->_b_x140 = _b_x140;
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_never3_fun467(kk_function_t _fself, kk_function_t ___wildcard_x653__45, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never3_fun467__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never3_fun467__t*, _fself, _ctx);
  kk_box_t _b_x140 = _self->_b_x140; /* 45 */
  kk_function_t op = _self->op; /* (8819, 8820, 8821) -> 8823 8825 */
  kk_drop_match(_self, {kk_box_dup(_b_x140, _ctx);kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_function_drop(___wildcard_x653__45, _ctx);
  kk_std_core_types__tuple3 _match_x228 = kk_std_core_types__tuple3_unbox(_b_x140, KK_OWNED, _ctx); /*(8819, 8820, 8821)*/;
  {
    kk_box_t x1 = _match_x228.fst;
    kk_box_t x2 = _match_x228.snd;
    kk_box_t x3 = _match_x228.thd;
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, _ctx), _ctx);
  }
}
static kk_box_t kk_std_core_hnd_clause_never3_fun466(kk_function_t _fself, int32_t _b_x138, kk_std_core_hnd__ev _b_x139, kk_box_t _b_x140, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never3_fun466__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never3_fun466__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (8819, 8820, 8821) -> 8823 8825 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x139, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to_final(_b_x138, kk_std_core_hnd_new_clause_never3_fun467(_b_x140, op, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_never3(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1,b1> (op : (a, b, c) -> e b1) -> clause1<(a, b, c),d,a1,e,b1> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_never3_fun466(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_under3_fun473__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under3_fun473(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under3_fun473(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under3_fun473__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under3_fun473__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under3_fun473, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_under3_fun476__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under3_fun476(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under3_fun476(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under3_fun476__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under3_fun476__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under3_fun476, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_under3_fun476(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under3_fun476__t* _self = kk_function_as(struct kk_std_core_hnd_under3_fun476__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<9062> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont_0, res_0, _ctx);
}
static kk_box_t kk_std_core_hnd_under3_fun473(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under3_fun473__t* _self = kk_function_as(struct kk_std_core_hnd_under3_fun473__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<9062> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  kk_evv_t w0_0;
  kk_evv_t _x_x474;
  {
    struct kk_std_core_hnd_Ev* _con_x475 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w_0 = _con_x475->hevv;
    kk_evv_dup(w_0, _ctx);
    _x_x474 = w_0; /*hnd/evv<5330>*/
  }
  w0_0 = kk_evv_swap(_x_x474,kk_context()); /*hnd/evv<_5477>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, res, _ctx), _ctx); /*9060*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    kk_evv_drop(w0_0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under3_fun476(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0_0,kk_context());
    return y;
  }
}

kk_box_t kk_std_core_hnd_under3(kk_std_core_hnd__ev ev, kk_function_t op, kk_box_t x1, kk_box_t x2, kk_box_t x3, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (ev : ev<a1>, op : (a, b, c) -> e d, x1 : a, x2 : b, x3 : c) -> e d */ 
  kk_evv_t w0;
  kk_evv_t _x_x471;
  {
    struct kk_std_core_hnd_Ev* _con_x472 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w = _con_x472->hevv;
    kk_evv_dup(w, _ctx);
    _x_x471 = w; /*hnd/evv<5330>*/
  }
  w0 = kk_evv_swap(_x_x471,kk_context()); /*hnd/evv<_8968>*/
  kk_box_t z = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, _ctx), _ctx); /*9060*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w0,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(z, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under3_fun473(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    return z;
  }
}


// lift anonymous function
struct kk_std_core_hnd_clause_control4_fun477__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control4_fun477(kk_function_t _fself, int32_t _b_x158, kk_std_core_hnd__ev _b_x159, kk_box_t _b_x160, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control4_fun477(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control4_fun477__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control4_fun477__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control4_fun477, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control4_fun478__t {
  struct kk_function_s _base;
  kk_box_t _b_x160;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control4_fun478(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control4_fun478(kk_box_t _b_x160, kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control4_fun478__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control4_fun478__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control4_fun478, kk_context());
  _self->_b_x160 = _b_x160;
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_control4_fun479__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_control4_fun479(kk_function_t _fself, kk_box_t _b_x155, kk_function_t _b_x156, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_control4_fun479(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control4_fun479__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_control4_fun479__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_control4_fun479, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_control4_fun479(kk_function_t _fself, kk_box_t _b_x155, kk_function_t _b_x156, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control4_fun479__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control4_fun479__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 9162, x2 : 9163, x3 : 9164, x4 : 9165, k : (9166) -> 9167 9169) -> 9167 9169 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_std_core_types__tuple4 _match_x224 = kk_std_core_types__tuple4_unbox(_b_x155, KK_OWNED, _ctx); /*(9162, 9163, 9164, 9165)*/;
  {
    struct kk_std_core_types_Tuple4* _con_x480 = kk_std_core_types__as_Tuple4(_match_x224, _ctx);
    kk_box_t x1 = _con_x480->fst;
    kk_box_t x2 = _con_x480->snd;
    kk_box_t x3 = _con_x480->thd;
    kk_box_t x4 = _con_x480->field4;
    if kk_likely(kk_datatype_ptr_is_unique(_match_x224, _ctx)) {
      kk_datatype_ptr_free(_match_x224, _ctx);
    }
    else {
      kk_box_dup(x1, _ctx);
      kk_box_dup(x2, _ctx);
      kk_box_dup(x3, _ctx);
      kk_box_dup(x4, _ctx);
      kk_datatype_ptr_decref(_match_x224, _ctx);
    }
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_function_t, kk_context_t*), op, (op, x1, x2, x3, x4, _b_x156, _ctx), _ctx);
  }
}
static kk_box_t kk_std_core_hnd_clause_control4_fun478(kk_function_t _fself, kk_function_t k, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control4_fun478__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control4_fun478__t*, _fself, _ctx);
  kk_box_t _b_x160 = _self->_b_x160; /* 45 */
  kk_function_t op = _self->op; /* (x1 : 9162, x2 : 9163, x3 : 9164, x4 : 9165, k : (9166) -> 9167 9169) -> 9167 9169 */
  kk_drop_match(_self, {kk_box_dup(_b_x160, _ctx);kk_function_dup(op, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_protect(_b_x160, kk_std_core_hnd_new_clause_control4_fun479(op, _ctx), k, _ctx);
}
static kk_box_t kk_std_core_hnd_clause_control4_fun477(kk_function_t _fself, int32_t _b_x158, kk_std_core_hnd__ev _b_x159, kk_box_t _b_x160, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_control4_fun477__t* _self = kk_function_as(struct kk_std_core_hnd_clause_control4_fun477__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (x1 : 9162, x2 : 9163, x3 : 9164, x4 : 9165, k : (9166) -> 9167 9169) -> 9167 9169 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x159, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to(_b_x158, kk_std_core_hnd_new_clause_control4_fun478(_b_x160, op, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_control4(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,e,b1,c1> (op : (x1 : a, x2 : b, x3 : c, x4 : d, k : (a1) -> e c1) -> e c1) -> clause1<(a, b, c, d),a1,b1,e,c1> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_control4_fun477(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_tail4_fun481__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_tail4_fun481(kk_function_t _fself, kk_box_t _b_x171, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail4_fun481(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail4_fun481__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail4_fun481__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail4_fun481, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_tail4_fun481(kk_function_t _fself, kk_box_t _b_x171, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail4_fun481__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail4_fun481__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (9278, 9279, 9280, 9281) -> 9275 9282 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_std_core_types__tuple4 _match_x223 = kk_std_core_types__tuple4_unbox(_b_x171, KK_OWNED, _ctx); /*(9278, 9279, 9280, 9281)*/;
  {
    struct kk_std_core_types_Tuple4* _con_x482 = kk_std_core_types__as_Tuple4(_match_x223, _ctx);
    kk_box_t x1 = _con_x482->fst;
    kk_box_t x2 = _con_x482->snd;
    kk_box_t x3 = _con_x482->thd;
    kk_box_t x4 = _con_x482->field4;
    if kk_likely(kk_datatype_ptr_is_unique(_match_x223, _ctx)) {
      kk_datatype_ptr_free(_match_x223, _ctx);
    }
    else {
      kk_box_dup(x1, _ctx);
      kk_box_dup(x2, _ctx);
      kk_box_dup(x3, _ctx);
      kk_box_dup(x4, _ctx);
      kk_datatype_ptr_decref(_match_x223, _ctx);
    }
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, x4, _ctx), _ctx);
  }
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_tail4(kk_function_t op, kk_context_t* _ctx) { /* forall<e,a,b,c,d,a1,b1,c1> (op : (c, d, a1, b1) -> e c1) -> clause1<(c, d, a1, b1),c1,b,e,a> */ 
  return kk_std_core_hnd_clause_tail1(kk_std_core_hnd_new_clause_tail4_fun481(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_tail_noop4_fun483__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_tail_noop4_fun483(kk_function_t _fself, int32_t _b_x175, kk_std_core_hnd__ev _b_x176, kk_box_t _b_x177, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_tail_noop4_fun483(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail_noop4_fun483__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_tail_noop4_fun483__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_tail_noop4_fun483, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_tail_noop4_fun483(kk_function_t _fself, int32_t _b_x175, kk_std_core_hnd__ev _b_x176, kk_box_t _b_x177, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_tail_noop4_fun483__t* _self = kk_function_as(struct kk_std_core_hnd_clause_tail_noop4_fun483__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (9391, 9392, 9393, 9394) -> 9388 9395 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x176, (KK_I32(3)), _ctx);
  kk_std_core_types__tuple4 _match_x222 = kk_std_core_types__tuple4_unbox(_b_x177, KK_OWNED, _ctx); /*(9391, 9392, 9393, 9394)*/;
  {
    struct kk_std_core_types_Tuple4* _con_x484 = kk_std_core_types__as_Tuple4(_match_x222, _ctx);
    kk_box_t x1 = _con_x484->fst;
    kk_box_t x2 = _con_x484->snd;
    kk_box_t x3 = _con_x484->thd;
    kk_box_t x4 = _con_x484->field4;
    if kk_likely(kk_datatype_ptr_is_unique(_match_x222, _ctx)) {
      kk_datatype_ptr_free(_match_x222, _ctx);
    }
    else {
      kk_box_dup(x1, _ctx);
      kk_box_dup(x2, _ctx);
      kk_box_dup(x3, _ctx);
      kk_box_dup(x4, _ctx);
      kk_datatype_ptr_decref(_match_x222, _ctx);
    }
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, x4, _ctx), _ctx);
  }
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_tail_noop4(kk_function_t op, kk_context_t* _ctx) { /* forall<e,a,b,c,d,a1,b1,c1> (op : (c, d, a1, b1) -> e c1) -> clause1<(c, d, a1, b1),c1,b,e,a> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_tail_noop4_fun483(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_clause_never4_fun485__t {
  struct kk_function_s _base;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never4_fun485(kk_function_t _fself, int32_t _b_x183, kk_std_core_hnd__ev _b_x184, kk_box_t _b_x185, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never4_fun485(kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never4_fun485__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never4_fun485__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never4_fun485, kk_context());
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_clause_never4_fun486__t {
  struct kk_function_s _base;
  kk_box_t _b_x185;
  kk_function_t op;
};
static kk_box_t kk_std_core_hnd_clause_never4_fun486(kk_function_t _fself, kk_function_t ___wildcard_x653__45, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_clause_never4_fun486(kk_box_t _b_x185, kk_function_t op, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never4_fun486__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_clause_never4_fun486__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_clause_never4_fun486, kk_context());
  _self->_b_x185 = _b_x185;
  _self->op = op;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_clause_never4_fun486(kk_function_t _fself, kk_function_t ___wildcard_x653__45, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never4_fun486__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never4_fun486__t*, _fself, _ctx);
  kk_box_t _b_x185 = _self->_b_x185; /* 45 */
  kk_function_t op = _self->op; /* (9501, 9502, 9503, 9504) -> 9506 9508 */
  kk_drop_match(_self, {kk_box_dup(_b_x185, _ctx);kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_function_drop(___wildcard_x653__45, _ctx);
  kk_std_core_types__tuple4 _match_x221 = kk_std_core_types__tuple4_unbox(_b_x185, KK_OWNED, _ctx); /*(9501, 9502, 9503, 9504)*/;
  {
    struct kk_std_core_types_Tuple4* _con_x487 = kk_std_core_types__as_Tuple4(_match_x221, _ctx);
    kk_box_t x1 = _con_x487->fst;
    kk_box_t x2 = _con_x487->snd;
    kk_box_t x3 = _con_x487->thd;
    kk_box_t x4 = _con_x487->field4;
    if kk_likely(kk_datatype_ptr_is_unique(_match_x221, _ctx)) {
      kk_datatype_ptr_free(_match_x221, _ctx);
    }
    else {
      kk_box_dup(x1, _ctx);
      kk_box_dup(x2, _ctx);
      kk_box_dup(x3, _ctx);
      kk_box_dup(x4, _ctx);
      kk_datatype_ptr_decref(_match_x221, _ctx);
    }
    return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, x4, _ctx), _ctx);
  }
}
static kk_box_t kk_std_core_hnd_clause_never4_fun485(kk_function_t _fself, int32_t _b_x183, kk_std_core_hnd__ev _b_x184, kk_box_t _b_x185, kk_context_t* _ctx) {
  struct kk_std_core_hnd_clause_never4_fun485__t* _self = kk_function_as(struct kk_std_core_hnd_clause_never4_fun485__t*, _fself, _ctx);
  kk_function_t op = _self->op; /* (9501, 9502, 9503, 9504) -> 9506 9508 */
  kk_drop_match(_self, {kk_function_dup(op, _ctx);}, {}, _ctx)
  kk_datatype_ptr_dropn(_b_x184, (KK_I32(3)), _ctx);
  return kk_std_core_hnd_yield_to_final(_b_x183, kk_std_core_hnd_new_clause_never4_fun486(_b_x185, op, _ctx), _ctx);
}

kk_std_core_hnd__clause1 kk_std_core_hnd_clause_never4(kk_function_t op, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,e,b1,c1> (op : (a, b, c, d) -> e c1) -> clause1<(a, b, c, d),a1,b1,e,c1> */ 
  return kk_std_core_hnd__new_Clause1(kk_std_core_hnd_new_clause_never4_fun485(op, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_hnd_under4_fun493__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under4_fun493(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under4_fun493(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under4_fun493__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under4_fun493__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under4_fun493, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_hnd_under4_fun496__t {
  struct kk_function_s _base;
  kk_std_core_hnd__ev ev;
};
static kk_box_t kk_std_core_hnd_under4_fun496(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_under4_fun496(kk_std_core_hnd__ev ev, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under4_fun496__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_under4_fun496__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_under4_fun496, kk_context());
  _self->ev = ev;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_under4_fun496(kk_function_t _fself, kk_function_t cont_0, kk_box_t res_0, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under4_fun496__t* _self = kk_function_as(struct kk_std_core_hnd_under4_fun496__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<9768> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_under1x(ev, cont_0, res_0, _ctx);
}
static kk_box_t kk_std_core_hnd_under4_fun493(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_under4_fun493__t* _self = kk_function_as(struct kk_std_core_hnd_under4_fun493__t*, _fself, _ctx);
  kk_std_core_hnd__ev ev = _self->ev; /* hnd/ev<9768> */
  kk_drop_match(_self, {kk_std_core_hnd__ev_dup(ev, _ctx);}, {}, _ctx)
  kk_evv_t w0_0;
  kk_evv_t _x_x494;
  {
    struct kk_std_core_hnd_Ev* _con_x495 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w_0 = _con_x495->hevv;
    kk_evv_dup(w_0, _ctx);
    _x_x494 = w_0; /*hnd/evv<5330>*/
  }
  w0_0 = kk_evv_swap(_x_x494,kk_context()); /*hnd/evv<_5477>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont, (cont, res, _ctx), _ctx); /*9766*/;
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    kk_evv_drop(w0_0, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under4_fun496(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    kk_unit_t ___0 = kk_Unit;
    kk_evv_set(w0_0,kk_context());
    return y;
  }
}

kk_box_t kk_std_core_hnd_under4(kk_std_core_hnd__ev ev, kk_function_t op, kk_box_t x1, kk_box_t x2, kk_box_t x3, kk_box_t x4, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,e,b1> (ev : ev<b1>, op : (a, b, c, d) -> e a1, x1 : a, x2 : b, x3 : c, x4 : d) -> e a1 */ 
  kk_evv_t w0;
  kk_evv_t _x_x491;
  {
    struct kk_std_core_hnd_Ev* _con_x492 = kk_std_core_hnd__as_Ev(ev, _ctx);
    kk_evv_t w = _con_x492->hevv;
    kk_evv_dup(w, _ctx);
    _x_x491 = w; /*hnd/evv<5330>*/
  }
  w0 = kk_evv_swap(_x_x491,kk_context()); /*hnd/evv<_9668>*/
  kk_box_t z = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), op, (op, x1, x2, x3, x4, _ctx), _ctx); /*9766*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w0,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(z, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_under4_fun493(ev, _ctx), _ctx);
  }
  {
    kk_datatype_ptr_dropn(ev, (KK_I32(3)), _ctx);
    return z;
  }
}


// lift anonymous function
struct kk_std_core_hnd_open_at1_fun497__t {
  struct kk_function_s _base;
  kk_ssize_t i;
};
static kk_box_t kk_std_core_hnd_open_at1_fun497(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_open_at1_fun497(kk_ssize_t i, kk_context_t* _ctx) {
  struct kk_std_core_hnd_open_at1_fun497__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_open_at1_fun497__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_open_at1_fun497, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_open_at1_fun497(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_open_at1_fun497__t* _self = kk_function_as(struct kk_std_core_hnd_open_at1_fun497__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open_at1(i, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd_open_at1(kk_ssize_t i, kk_function_t f, kk_box_t x, kk_context_t* _ctx) { /* forall<a,b,e,e1> (i : ev-index, f : (a) -> e b, x : a) -> e1 b */ 
  kk_evv_t w = kk_evv_swap_create1(i,kk_context()); /*hnd/evv<10321>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, x, _ctx), _ctx); /*10319*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_open_at1_fun497(i, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open_at0_fun498__t {
  struct kk_function_s _base;
  kk_ssize_t i;
};
static kk_box_t kk_std_core_hnd__open_at0_fun498(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open_at0_fun498(kk_ssize_t i, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at0_fun498__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open_at0_fun498__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open_at0_fun498, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open_at0_fun498(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at0_fun498__t* _self = kk_function_as(struct kk_std_core_hnd__open_at0_fun498__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open_at1(i, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open_at0(kk_ssize_t i, kk_function_t f, kk_context_t* _ctx) { /* forall<a,e,e1> (i : ev-index, f : () -> e a) -> e1 a */ 
  kk_evv_t w = kk_evv_swap_create1(i,kk_context()); /*hnd/evv<10428>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), f, (f, _ctx), _ctx); /*10426*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open_at0_fun498(i, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open_at1_fun499__t {
  struct kk_function_s _base;
  kk_ssize_t i;
};
static kk_box_t kk_std_core_hnd__open_at1_fun499(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open_at1_fun499(kk_ssize_t i, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at1_fun499__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open_at1_fun499__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open_at1_fun499, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open_at1_fun499(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at1_fun499__t* _self = kk_function_as(struct kk_std_core_hnd__open_at1_fun499__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open_at1(i, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open_at1(kk_ssize_t i, kk_function_t f, kk_box_t x, kk_context_t* _ctx) { /* forall<a,b,e,e1> (i : ev-index, f : (a) -> e b, x : a) -> e1 b */ 
  kk_evv_t w = kk_evv_swap_create1(i,kk_context()); /*hnd/evv<10542>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, x, _ctx), _ctx); /*10540*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open_at1_fun499(i, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open_at2_fun500__t {
  struct kk_function_s _base;
  kk_ssize_t i;
};
static kk_box_t kk_std_core_hnd__open_at2_fun500(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open_at2_fun500(kk_ssize_t i, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at2_fun500__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open_at2_fun500__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open_at2_fun500, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open_at2_fun500(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at2_fun500__t* _self = kk_function_as(struct kk_std_core_hnd__open_at2_fun500__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open_at1(i, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open_at2(kk_ssize_t i, kk_function_t f, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) { /* forall<a,b,c,e,e1> (i : ev-index, f : (a, b) -> e c, x1 : a, x2 : b) -> e1 c */ 
  kk_evv_t w = kk_evv_swap_create1(i,kk_context()); /*hnd/evv<10669>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, x1, x2, _ctx), _ctx); /*10667*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open_at2_fun500(i, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open_at3_fun501__t {
  struct kk_function_s _base;
  kk_ssize_t i;
};
static kk_box_t kk_std_core_hnd__open_at3_fun501(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open_at3_fun501(kk_ssize_t i, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at3_fun501__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open_at3_fun501__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open_at3_fun501, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open_at3_fun501(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at3_fun501__t* _self = kk_function_as(struct kk_std_core_hnd__open_at3_fun501__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open_at1(i, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open_at3(kk_ssize_t i, kk_function_t f, kk_box_t x1, kk_box_t x2, kk_box_t x3, kk_context_t* _ctx) { /* forall<a,b,c,d,e,e1> (i : ev-index, f : (a, b, c) -> e d, x1 : a, x2 : b, x3 : c) -> e1 d */ 
  kk_evv_t w = kk_evv_swap_create1(i,kk_context()); /*hnd/evv<10809>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, x1, x2, x3, _ctx), _ctx); /*10807*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open_at3_fun501(i, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open_at4_fun502__t {
  struct kk_function_s _base;
  kk_ssize_t i;
};
static kk_box_t kk_std_core_hnd__open_at4_fun502(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open_at4_fun502(kk_ssize_t i, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at4_fun502__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open_at4_fun502__t, 1, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open_at4_fun502, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open_at4_fun502(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open_at4_fun502__t* _self = kk_function_as(struct kk_std_core_hnd__open_at4_fun502__t*, _fself, _ctx);
  kk_ssize_t i = _self->i; /* hnd/ev-index */
  kk_drop_match(_self, {kk_skip_dup(i, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open_at1(i, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open_at4(kk_ssize_t i, kk_function_t f, kk_box_t x1, kk_box_t x2, kk_box_t x3, kk_box_t x4, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,e,e1> (i : ev-index, f : (a, b, c, d) -> e a1, x1 : a, x2 : b, x3 : c, x4 : d) -> e1 a1 */ 
  kk_evv_t w = kk_evv_swap_create1(i,kk_context()); /*hnd/evv<10962>*/;
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, x1, x2, x3, x4, _ctx), _ctx); /*10960*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open_at4_fun502(i, _ctx), _ctx);
  }
  {
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd_open1_fun504__t {
  struct kk_function_s _base;
  kk_vector_t indices;
};
static kk_box_t kk_std_core_hnd_open1_fun504(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_open1_fun504(kk_vector_t indices, kk_context_t* _ctx) {
  struct kk_std_core_hnd_open1_fun504__t* _self = kk_function_alloc_as(struct kk_std_core_hnd_open1_fun504__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd_open1_fun504, kk_context());
  _self->indices = indices;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd_open1_fun504(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd_open1_fun504__t* _self = kk_function_as(struct kk_std_core_hnd_open1_fun504__t*, _fself, _ctx);
  kk_vector_t indices = _self->indices; /* vector<hnd/ev-index> */
  kk_drop_match(_self, {kk_vector_dup(indices, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open1(indices, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd_open1(kk_vector_t indices, kk_function_t f, kk_box_t x, kk_context_t* _ctx) { /* forall<a,b,e,e1> (indices : vector<ev-index>, f : (a) -> e b, x : a) -> e1 b */ 
  kk_evv_t w;
  kk_vector_t _x_x503 = kk_vector_dup(indices, _ctx); /*vector<hnd/ev-index>*/
  w = kk_std_core_hnd_evv_swap_create(_x_x503, _ctx); /*hnd/evv<11095>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, x, _ctx), _ctx); /*11093*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_open1_fun504(indices, _ctx), _ctx);
  }
  {
    kk_vector_drop(indices, _ctx);
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open0_fun506__t {
  struct kk_function_s _base;
  kk_vector_t indices;
};
static kk_box_t kk_std_core_hnd__open0_fun506(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open0_fun506(kk_vector_t indices, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open0_fun506__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open0_fun506__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open0_fun506, kk_context());
  _self->indices = indices;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open0_fun506(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open0_fun506__t* _self = kk_function_as(struct kk_std_core_hnd__open0_fun506__t*, _fself, _ctx);
  kk_vector_t indices = _self->indices; /* vector<hnd/ev-index> */
  kk_drop_match(_self, {kk_vector_dup(indices, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open1(indices, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open0(kk_vector_t indices, kk_function_t f, kk_context_t* _ctx) { /* forall<a,e,e1> (indices : vector<ev-index>, f : () -> e a) -> e1 a */ 
  kk_evv_t w;
  kk_vector_t _x_x505 = kk_vector_dup(indices, _ctx); /*vector<hnd/ev-index>*/
  w = kk_std_core_hnd_evv_swap_create(_x_x505, _ctx); /*hnd/evv<11202>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_context_t*), f, (f, _ctx), _ctx); /*11200*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open0_fun506(indices, _ctx), _ctx);
  }
  {
    kk_vector_drop(indices, _ctx);
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open1_fun508__t {
  struct kk_function_s _base;
  kk_vector_t indices;
};
static kk_box_t kk_std_core_hnd__open1_fun508(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open1_fun508(kk_vector_t indices, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open1_fun508__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open1_fun508__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open1_fun508, kk_context());
  _self->indices = indices;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open1_fun508(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open1_fun508__t* _self = kk_function_as(struct kk_std_core_hnd__open1_fun508__t*, _fself, _ctx);
  kk_vector_t indices = _self->indices; /* vector<hnd/ev-index> */
  kk_drop_match(_self, {kk_vector_dup(indices, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open1(indices, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open1(kk_vector_t indices, kk_function_t f, kk_box_t x, kk_context_t* _ctx) { /* forall<a,b,e,e1> (indices : vector<ev-index>, f : (a) -> e b, x : a) -> e1 b */ 
  kk_evv_t w;
  kk_vector_t _x_x507 = kk_vector_dup(indices, _ctx); /*vector<hnd/ev-index>*/
  w = kk_std_core_hnd_evv_swap_create(_x_x507, _ctx); /*hnd/evv<11316>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, x, _ctx), _ctx); /*11314*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open1_fun508(indices, _ctx), _ctx);
  }
  {
    kk_vector_drop(indices, _ctx);
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open2_fun510__t {
  struct kk_function_s _base;
  kk_vector_t indices;
};
static kk_box_t kk_std_core_hnd__open2_fun510(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open2_fun510(kk_vector_t indices, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open2_fun510__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open2_fun510__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open2_fun510, kk_context());
  _self->indices = indices;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open2_fun510(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open2_fun510__t* _self = kk_function_as(struct kk_std_core_hnd__open2_fun510__t*, _fself, _ctx);
  kk_vector_t indices = _self->indices; /* vector<hnd/ev-index> */
  kk_drop_match(_self, {kk_vector_dup(indices, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open1(indices, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open2(kk_vector_t indices, kk_function_t f, kk_box_t x1, kk_box_t x2, kk_context_t* _ctx) { /* forall<a,b,c,e,e1> (indices : vector<ev-index>, f : (a, b) -> e c, x1 : a, x2 : b) -> e1 c */ 
  kk_evv_t w;
  kk_vector_t _x_x509 = kk_vector_dup(indices, _ctx); /*vector<hnd/ev-index>*/
  w = kk_std_core_hnd_evv_swap_create(_x_x509, _ctx); /*hnd/evv<11443>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, x1, x2, _ctx), _ctx); /*11441*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open2_fun510(indices, _ctx), _ctx);
  }
  {
    kk_vector_drop(indices, _ctx);
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open3_fun512__t {
  struct kk_function_s _base;
  kk_vector_t indices;
};
static kk_box_t kk_std_core_hnd__open3_fun512(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open3_fun512(kk_vector_t indices, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open3_fun512__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open3_fun512__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open3_fun512, kk_context());
  _self->indices = indices;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open3_fun512(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open3_fun512__t* _self = kk_function_as(struct kk_std_core_hnd__open3_fun512__t*, _fself, _ctx);
  kk_vector_t indices = _self->indices; /* vector<hnd/ev-index> */
  kk_drop_match(_self, {kk_vector_dup(indices, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open1(indices, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open3(kk_vector_t indices, kk_function_t f, kk_box_t x1, kk_box_t x2, kk_box_t x3, kk_context_t* _ctx) { /* forall<a,b,c,d,e,e1> (indices : vector<ev-index>, f : (a, b, c) -> e d, x1 : a, x2 : b, x3 : c) -> e1 d */ 
  kk_evv_t w;
  kk_vector_t _x_x511 = kk_vector_dup(indices, _ctx); /*vector<hnd/ev-index>*/
  w = kk_std_core_hnd_evv_swap_create(_x_x511, _ctx); /*hnd/evv<11583>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, x1, x2, x3, _ctx), _ctx); /*11581*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open3_fun512(indices, _ctx), _ctx);
  }
  {
    kk_vector_drop(indices, _ctx);
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd__open4_fun514__t {
  struct kk_function_s _base;
  kk_vector_t indices;
};
static kk_box_t kk_std_core_hnd__open4_fun514(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd__new_open4_fun514(kk_vector_t indices, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open4_fun514__t* _self = kk_function_alloc_as(struct kk_std_core_hnd__open4_fun514__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_hnd__open4_fun514, kk_context());
  _self->indices = indices;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_hnd__open4_fun514(kk_function_t _fself, kk_function_t cont, kk_box_t res, kk_context_t* _ctx) {
  struct kk_std_core_hnd__open4_fun514__t* _self = kk_function_as(struct kk_std_core_hnd__open4_fun514__t*, _fself, _ctx);
  kk_vector_t indices = _self->indices; /* vector<hnd/ev-index> */
  kk_drop_match(_self, {kk_vector_dup(indices, _ctx);}, {}, _ctx)
  return kk_std_core_hnd_open1(indices, cont, res, _ctx);
}

kk_box_t kk_std_core_hnd__open4(kk_vector_t indices, kk_function_t f, kk_box_t x1, kk_box_t x2, kk_box_t x3, kk_box_t x4, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,e,e1> (indices : vector<ev-index>, f : (a, b, c, d) -> e a1, x1 : a, x2 : b, x3 : c, x4 : d) -> e1 a1 */ 
  kk_evv_t w;
  kk_vector_t _x_x513 = kk_vector_dup(indices, _ctx); /*vector<hnd/ev-index>*/
  w = kk_std_core_hnd_evv_swap_create(_x_x513, _ctx); /*hnd/evv<11736>*/
  kk_box_t y = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, x1, x2, x3, x4, _ctx), _ctx); /*11734*/;
  kk_unit_t __ = kk_Unit;
  kk_evv_set(w,kk_context());
  if (kk_yielding(kk_context())) {
    kk_box_drop(y, _ctx);
    return kk_std_core_hnd_yield_cont(kk_std_core_hnd__new_open4_fun514(indices, _ctx), _ctx);
  }
  {
    kk_vector_drop(indices, _ctx);
    return y;
  }
}


// lift anonymous function
struct kk_std_core_hnd_try_finalize_prompt_fun516__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_hnd_try_finalize_prompt_fun516(kk_function_t _fself, kk_function_t _b_x198, kk_box_t _b_x199, kk_context_t* _ctx);
static kk_function_t kk_std_core_hnd_new_try_finalize_prompt_fun516(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_hnd_try_finalize_prompt_fun516, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_hnd_try_finalize_prompt_fun516(kk_function_t _fself, kk_function_t _b_x198, kk_box_t _b_x199, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_function_t cont_203 = _b_x198; /*(11801) -> 11861 11860*/;
  kk_box_t x_204 = _b_x199; /*11801*/;
  kk_std_core_types__either _x_x517;
  kk_box_t _x_x518 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), cont_203, (cont_203, x_204, _ctx), _ctx); /*11860*/
  _x_x517 = kk_std_core_hnd_try_finalize_prompt(_x_x518, _ctx); /*either<hnd/yield-info,11860>*/
  return kk_std_core_types__either_box(_x_x517, _ctx);
}

kk_std_core_types__either kk_std_core_hnd_try_finalize_prompt(kk_box_t res, kk_context_t* _ctx) { /* forall<a,e> (res : a) -> e either<yield-info,a> */ 
  bool _match_x205 = kk_yielding_non_final(kk_context()); /*bool*/;
  if (_match_x205) {
    kk_box_drop(res, _ctx);
    kk_box_t _x_x515 = kk_std_core_hnd_yield_cont(kk_std_core_hnd_new_try_finalize_prompt_fun516(_ctx), _ctx); /*2568*/
    return kk_std_core_types__either_unbox(_x_x515, KK_OWNED, _ctx);
  }
  if (kk_yielding(kk_context())) {
    kk_box_drop(res, _ctx);
    kk_std_core_hnd__yield_info _b_x200_202 = kk_std_core_hnd_yield_capture(_ctx); /*hnd/yield-info*/;
    return kk_std_core_types__new_Left(kk_std_core_hnd__yield_info_box(_b_x200_202, _ctx), _ctx);
  }
  {
    return kk_std_core_types__new_Right(res, _ctx);
  }
}

// initialization
void kk_std_core_hnd__init(kk_context_t* _ctx){
  static bool _kk_initialized = false;
  if (_kk_initialized) return;
  _kk_initialized = true;
  kk_std_core_types__init(_ctx);
  kk_std_core_undiv__init(_ctx);
  #if defined(KK_CUSTOM_INIT)
    KK_CUSTOM_INIT (_ctx);
  #endif
}

// termination
void kk_std_core_hnd__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_std_core_undiv__done(_ctx);
  kk_std_core_types__done(_ctx);
}
