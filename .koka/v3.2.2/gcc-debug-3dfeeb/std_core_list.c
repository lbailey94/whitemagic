// Koka generated module: std/core/list, koka version: 3.2.2, platform: 64-bit
#include "std_core_list.h"
 
// Return the head of list if the list is not empty.

kk_std_core_types__maybe kk_std_core_list_maybe_fs_head(kk_std_core_types__list xs, kk_context_t* _ctx) { /* forall<a> (xs : list<a>) -> maybe<a> */ 
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1201 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1201->head;
    kk_std_core_types__list _pat_0 = _con_x1201->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_std_core_types__list_drop(_pat_0, _ctx);
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    return kk_std_core_types__new_Just(x, _ctx);
  }
  {
    return kk_std_core_types__new_Nothing(_ctx);
  }
}
 
// Return the head of list with a default value in case the list is empty.

kk_box_t kk_std_core_list_head(kk_std_core_types__list xs, kk_box_t kkloc_default, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, default : a) -> a */ 
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1202 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1202->head;
    kk_std_core_types__list _pat_0 = _con_x1202->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_std_core_types__list_drop(_pat_0, _ctx);
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_box_drop(kkloc_default, _ctx);
    return x;
  }
  {
    return kkloc_default;
  }
}
 
// Return the tail of list. Returns the empty list if `xs` is empty.

kk_std_core_types__list kk_std_core_list_tail(kk_std_core_types__list xs, kk_context_t* _ctx) { /* forall<a> (xs : list<a>) -> list<a> */ 
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1203 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _pat_0 = _con_x1203->head;
    kk_std_core_types__list xx = _con_x1203->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_box_drop(_pat_0, _ctx);
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    return xx;
  }
  {
    return kk_std_core_types__new_Nil(_ctx);
  }
}
 
// lifted local: length, len

kk_integer_t kk_std_core_list__lift_length_5730(kk_std_core_types__list ys, kk_integer_t acc, kk_context_t* _ctx) { /* forall<a> (ys : list<a>, acc : int) -> int */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1204 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t _pat_0 = _con_x1204->head;
    kk_std_core_types__list yy = _con_x1204->tail;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      kk_box_drop(_pat_0, _ctx);
      kk_datatype_ptr_free(ys, _ctx);
    }
    else {
      kk_std_core_types__list_dup(yy, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    { // tailcall
      kk_integer_t _x_x1205 = kk_integer_add_small_const(acc, 1, _ctx); /*int*/
      ys = yy;
      acc = _x_x1205;
      goto kk__tailcall;
    }
  }
  {
    return acc;
  }
}
 
// monadic lift

bool kk_std_core_list__lp__at_mlift_x_10278_eq__eq__rp_(kk_function_t _implicit_fs__lp__eq__eq__rp_, kk_std_core_types__list xx, kk_std_core_types__list yy, bool _y_x10104, kk_context_t* _ctx) { /* forall<a,e> (?(==) : (a, a) -> e bool, xx : list<a>, yy : list<a>, bool) -> e bool */ 
  if (_y_x10104) {
    return kk_std_core_list__lp__eq__eq__rp_(xx, yy, _implicit_fs__lp__eq__eq__rp_, _ctx);
  }
  {
    kk_std_core_types__list_drop(yy, _ctx);
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(_implicit_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// Element-wise list equality


// lift anonymous function
struct kk_std_core_list__lp__at_x_fun1210__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs__lp__at_x_0_eq__eq__rp_;
  kk_std_core_types__list xx_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__lp__at_x_fun1210_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x1, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__lp__at_new_x_fun1210_eq__eq__rp_(kk_function_t _implicit_fs__lp__at_x_0_eq__eq__rp_, kk_std_core_types__list xx_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__lp__at_x_fun1210__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_list__lp__at_x_fun1210__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__lp__at_x_fun1210_eq__eq__rp_, kk_context());
  _self->_implicit_fs__lp__at_x_0_eq__eq__rp_ = _implicit_fs__lp__at_x_0_eq__eq__rp_;
  _self->xx_0 = xx_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__lp__at_x_fun1210_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x1, kk_context_t* _ctx) {
  struct kk_std_core_list__lp__at_x_fun1210__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_list__lp__at_x_fun1210__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs__lp__at_x_0_eq__eq__rp_ = _self->_implicit_fs__lp__at_x_0_eq__eq__rp_; /* (802, 802) -> 803 bool */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<802> */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<802> */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs__lp__at_x_0_eq__eq__rp_, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  bool _y_x10104_0_3 = kk_bool_unbox(_b_x1); /*bool*/;
  bool _x_x1211 = kk_std_core_list__lp__at_mlift_x_10278_eq__eq__rp_(_implicit_fs__lp__at_x_0_eq__eq__rp_, xx_0, yy_0, _y_x10104_0_3, _ctx); /*bool*/
  return kk_bool_box(_x_x1211);
}

bool kk_std_core_list__lp__eq__eq__rp_(kk_std_core_types__list xs, kk_std_core_types__list ys, kk_function_t _implicit_fs__lp__at_x_0_eq__eq__rp_, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, ys : list<a>, ?(==) : (a, a) -> e bool) -> e bool */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1206 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1206->head;
    kk_std_core_types__list xx_0 = _con_x1206->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    if (kk_std_core_types__is_Nil(ys, _ctx)) {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_box_drop(x, _ctx);
      kk_function_drop(_implicit_fs__lp__at_x_0_eq__eq__rp_, _ctx);
      return false;
    }
    {
      struct kk_std_core_types_Cons* _con_x1207 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t y = _con_x1207->head;
      kk_std_core_types__list yy_0 = _con_x1207->tail;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        kk_datatype_ptr_free(ys, _ctx);
      }
      else {
        kk_box_dup(y, _ctx);
        kk_std_core_types__list_dup(yy_0, _ctx);
        kk_datatype_ptr_decref(ys, _ctx);
      }
      bool x_0_10310;
      kk_function_t _x_x1208 = kk_function_dup(_implicit_fs__lp__at_x_0_eq__eq__rp_, _ctx); /*(802, 802) -> 803 bool*/
      x_0_10310 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x1208, (_x_x1208, x, y, _ctx), _ctx); /*bool*/
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x1209 = kk_std_core_hnd_yield_extend(kk_std_core_list__lp__at_new_x_fun1210_eq__eq__rp_(_implicit_fs__lp__at_x_0_eq__eq__rp_, xx_0, yy_0, _ctx), _ctx); /*2419*/
        return kk_bool_unbox(_x_x1209);
      }
      if (x_0_10310) { // tailcall
                       xs = xx_0;
                       ys = yy_0;
                       goto kk__tailcall;
      }
      {
        kk_std_core_types__list_drop(yy_0, _ctx);
        kk_std_core_types__list_drop(xx_0, _ctx);
        kk_function_drop(_implicit_fs__lp__at_x_0_eq__eq__rp_, _ctx);
        return false;
      }
    }
  }
  {
    kk_function_drop(_implicit_fs__lp__at_x_0_eq__eq__rp_, _ctx);
    if (kk_std_core_types__is_Nil(ys, _ctx)) {
      return true;
    }
    {
      struct kk_std_core_types_Cons* _con_x1212 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t _pat_7 = _con_x1212->head;
      kk_std_core_types__list _pat_8 = _con_x1212->tail;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        kk_std_core_types__list_drop(_pat_8, _ctx);
        kk_box_drop(_pat_7, _ctx);
        kk_datatype_ptr_free(ys, _ctx);
      }
      else {
        kk_datatype_ptr_decref(ys, _ctx);
      }
      return false;
    }
  }
}
 
// monadic lift

kk_std_core_types__order kk_std_core_list__mlift_cmp_10279(kk_function_t _implicit_fs_cmp, kk_std_core_types__list xx, kk_std_core_types__list yy, kk_std_core_types__order _y_x10109, kk_context_t* _ctx) { /* forall<a,e> (?cmp : (a, a) -> e order, xx : list<a>, yy : list<a>, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10109, _ctx)) {
    return kk_std_core_list_cmp(xx, yy, _implicit_fs_cmp, _ctx);
  }
  {
    kk_std_core_types__list_drop(yy, _ctx);
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(_implicit_fs_cmp, _ctx);
    return _y_x10109;
  }
}
 
// Order on lists


// lift anonymous function
struct kk_std_core_list_cmp_fun1217__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_cmp_0;
  kk_std_core_types__list xx_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list_cmp_fun1217(kk_function_t _fself, kk_box_t _b_x5, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_cmp_fun1217(kk_function_t _implicit_fs_cmp_0, kk_std_core_types__list xx_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list_cmp_fun1217__t* _self = kk_function_alloc_as(struct kk_std_core_list_cmp_fun1217__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_cmp_fun1217, kk_context());
  _self->_implicit_fs_cmp_0 = _implicit_fs_cmp_0;
  _self->xx_0 = xx_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_cmp_fun1217(kk_function_t _fself, kk_box_t _b_x5, kk_context_t* _ctx) {
  struct kk_std_core_list_cmp_fun1217__t* _self = kk_function_as(struct kk_std_core_list_cmp_fun1217__t*, _fself, _ctx);
  kk_function_t _implicit_fs_cmp_0 = _self->_implicit_fs_cmp_0; /* (898, 898) -> 899 order */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<898> */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<898> */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_cmp_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10109_0_7 = kk_std_core_types__order_unbox(_b_x5, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x1218 = kk_std_core_list__mlift_cmp_10279(_implicit_fs_cmp_0, xx_0, yy_0, _y_x10109_0_7, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x1218, _ctx);
}

kk_std_core_types__order kk_std_core_list_cmp(kk_std_core_types__list xs, kk_std_core_types__list ys, kk_function_t _implicit_fs_cmp_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, ys : list<a>, ?cmp : (a, a) -> e order) -> e order */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1213 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1213->head;
    kk_std_core_types__list xx_0 = _con_x1213->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    if (kk_std_core_types__is_Nil(ys, _ctx)) {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_box_drop(x, _ctx);
      kk_function_drop(_implicit_fs_cmp_0, _ctx);
      return kk_std_core_types__new_Gt(_ctx);
    }
    {
      struct kk_std_core_types_Cons* _con_x1214 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t y = _con_x1214->head;
      kk_std_core_types__list yy_0 = _con_x1214->tail;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        kk_datatype_ptr_free(ys, _ctx);
      }
      else {
        kk_box_dup(y, _ctx);
        kk_std_core_types__list_dup(yy_0, _ctx);
        kk_datatype_ptr_decref(ys, _ctx);
      }
      kk_std_core_types__order x_0_10313;
      kk_function_t _x_x1215 = kk_function_dup(_implicit_fs_cmp_0, _ctx); /*(898, 898) -> 899 order*/
      x_0_10313 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x1215, (_x_x1215, x, y, _ctx), _ctx); /*order*/
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x1216 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_cmp_fun1217(_implicit_fs_cmp_0, xx_0, yy_0, _ctx), _ctx); /*2419*/
        return kk_std_core_types__order_unbox(_x_x1216, KK_OWNED, _ctx);
      }
      if (kk_std_core_types__is_Eq(x_0_10313, _ctx)) { // tailcall
                                                       xs = xx_0;
                                                       ys = yy_0;
                                                       goto kk__tailcall;
      }
      {
        kk_std_core_types__list_drop(yy_0, _ctx);
        kk_std_core_types__list_drop(xx_0, _ctx);
        kk_function_drop(_implicit_fs_cmp_0, _ctx);
        return x_0_10313;
      }
    }
  }
  {
    kk_function_drop(_implicit_fs_cmp_0, _ctx);
    if (kk_std_core_types__is_Nil(ys, _ctx)) {
      return kk_std_core_types__new_Eq(_ctx);
    }
    {
      struct kk_std_core_types_Cons* _con_x1219 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t _pat_6 = _con_x1219->head;
      kk_std_core_types__list _pat_7 = _con_x1219->tail;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        kk_std_core_types__list_drop(_pat_7, _ctx);
        kk_box_drop(_pat_6, _ctx);
        kk_datatype_ptr_free(ys, _ctx);
      }
      else {
        kk_datatype_ptr_decref(ys, _ctx);
      }
      return kk_std_core_types__new_Lt(_ctx);
    }
  }
}
 
// Take the first `n` elements of a list (or fewer if the list is shorter than `n`)

kk_std_core_types__list kk_std_core_list__trmc_take(kk_std_core_types__list xs, kk_integer_t n, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, n : int, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1220 = kk_std_core_types__as_Cons(xs, _ctx);
    if (kk_integer_gt_borrow(n,(kk_integer_from_small(0)),kk_context())) {
      kk_box_t x = _con_x1220->head;
      kk_std_core_types__list xx = _con_x1220->tail;
      kk_reuse_t _ru_x1136 = kk_reuse_null; /*@reuse*/;
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        _ru_x1136 = (kk_datatype_ptr_reuse(xs, _ctx));
      }
      else {
        kk_box_dup(x, _ctx);
        kk_std_core_types__list_dup(xx, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      kk_std_core_types__list _trmc_x10048 = kk_datatype_null(); /*list<960>*/;
      kk_std_core_types__list _trmc_x10049 = kk_std_core_types__new_Cons(_ru_x1136, 0, x, _trmc_x10048, _ctx); /*list<960>*/;
      kk_field_addr_t _b_x13_18 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10049, _ctx)->tail, _ctx); /*@field-addr<list<960>>*/;
      { // tailcall
        kk_integer_t _x_x1221 = kk_integer_add_small_const(n, -1, _ctx); /*int*/
        kk_std_core_types__cctx _x_x1222 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10049, _ctx)),_b_x13_18,kk_context()); /*ctx<0>*/
        xs = xx;
        n = _x_x1221;
        _acc = _x_x1222;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_std_core_types__list_drop(xs, _ctx);
    kk_integer_drop(n, _ctx);
    kk_box_t _x_x1223 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1223, KK_OWNED, _ctx);
  }
}
 
// Take the first `n` elements of a list (or fewer if the list is shorter than `n`)

kk_std_core_types__list kk_std_core_list_take(kk_std_core_types__list xs_0, kk_integer_t n_0, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, n : int) -> list<a> */ 
  kk_std_core_types__cctx _x_x1224 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_take(xs_0, n_0, _x_x1224, _ctx);
}
 
// Drop the first `n` elements of a list (or fewer if the list is shorter than `n`)

kk_std_core_types__list kk_std_core_list_drop(kk_std_core_types__list xs, kk_integer_t n, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, n : int) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1225 = kk_std_core_types__as_Cons(xs, _ctx);
    if (kk_integer_gt_borrow(n,(kk_integer_from_small(0)),kk_context())) {
      kk_box_t _pat_0 = _con_x1225->head;
      kk_std_core_types__list xx = _con_x1225->tail;
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        kk_box_drop(_pat_0, _ctx);
        kk_datatype_ptr_free(xs, _ctx);
      }
      else {
        kk_std_core_types__list_dup(xx, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      { // tailcall
        kk_integer_t _x_x1226 = kk_integer_add_small_const(n, -1, _ctx); /*int*/
        xs = xx;
        n = _x_x1226;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_integer_drop(n, _ctx);
    return xs;
  }
}

kk_std_core_types__list kk_std_core_list_reverse_acc(kk_std_core_types__list acc, kk_std_core_types__list ys, kk_context_t* _ctx) { /* forall<a> (acc : list<a>, ys : list<a>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1227 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t x = _con_x1227->head;
    kk_std_core_types__list xx = _con_x1227->tail;
    kk_reuse_t _ru_x1138 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1138 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    { // tailcall
      kk_std_core_types__list _x_x1228 = kk_std_core_types__new_Cons(_ru_x1138, 0, x, acc, _ctx); /*list<79>*/
      acc = _x_x1228;
      ys = xx;
      goto kk__tailcall;
    }
  }
  {
    return acc;
  }
}
 
// Append two lists.

kk_std_core_types__list kk_std_core_list__trmc_append(kk_std_core_types__list xs, kk_std_core_types__list ys, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, ys : list<a>, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1229 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1229->head;
    kk_std_core_types__list xx = _con_x1229->tail;
    kk_reuse_t _ru_x1139 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1139 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__list _trmc_x10050 = kk_datatype_null(); /*list<1121>*/;
    kk_std_core_types__list _trmc_x10051 = kk_std_core_types__new_Cons(_ru_x1139, 0, x, _trmc_x10050, _ctx); /*list<1121>*/;
    kk_field_addr_t _b_x29_34 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10051, _ctx)->tail, _ctx); /*@field-addr<list<1121>>*/;
    { // tailcall
      kk_std_core_types__cctx _x_x1230 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10051, _ctx)),_b_x29_34,kk_context()); /*ctx<0>*/
      xs = xx;
      _acc = _x_x1230;
      goto kk__tailcall;
    }
  }
  {
    kk_box_t _x_x1231 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(ys, _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1231, KK_OWNED, _ctx);
  }
}
 
// Append two lists.

kk_std_core_types__list kk_std_core_list_append(kk_std_core_types__list xs_0, kk_std_core_types__list ys_0, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, ys : list<a>) -> list<a> */ 
  kk_std_core_types__cctx _x_x1232 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_append(xs_0, ys_0, _x_x1232, _ctx);
}
 
// monadic lift

kk_box_t kk_std_core_list__mlift_foldl_10280(kk_function_t f, kk_std_core_types__list xx, kk_box_t _y_x10114, kk_context_t* _ctx) { /* forall<a,b,e> (f : (b, a) -> e b, xx : list<a>, b) -> e b */ 
  return kk_std_core_list_foldl(xx, _y_x10114, f, _ctx);
}
 
// Fold a list from the left, i.e. `foldl([1,2],0,(+)) == (0+1)+2`
// Since `foldl` is tail recursive, it is preferred over `foldr` when using an associative function `f`


// lift anonymous function
struct kk_std_core_list_foldl_fun1236__t {
  struct kk_function_s _base;
  kk_function_t f_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_foldl_fun1236(kk_function_t _fself, kk_box_t _y_x10114_0, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foldl_fun1236(kk_function_t f_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_foldl_fun1236__t* _self = kk_function_alloc_as(struct kk_std_core_list_foldl_fun1236__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_foldl_fun1236, kk_context());
  _self->f_0 = f_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_foldl_fun1236(kk_function_t _fself, kk_box_t _y_x10114_0, kk_context_t* _ctx) {
  struct kk_std_core_list_foldl_fun1236__t* _self = kk_function_as(struct kk_std_core_list_foldl_fun1236__t*, _fself, _ctx);
  kk_function_t f_0 = _self->f_0; /* (1192, 1191) -> 1193 1192 */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<1191> */
  kk_drop_match(_self, {kk_function_dup(f_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  return kk_std_core_list__mlift_foldl_10280(f_0, xx_0, _y_x10114_0, _ctx);
}

kk_box_t kk_std_core_list_foldl(kk_std_core_types__list xs, kk_box_t z, kk_function_t f_0, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, z : b, f : (b, a) -> e b) -> e b */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1234 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1234->head;
    kk_std_core_types__list xx_0 = _con_x1234->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_box_t x_0_10318;
    kk_function_t _x_x1235 = kk_function_dup(f_0, _ctx); /*(1192, 1191) -> 1193 1192*/
    x_0_10318 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x1235, (_x_x1235, z, x, _ctx), _ctx); /*1192*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_0_10318, _ctx);
      return kk_std_core_hnd_yield_extend(kk_std_core_list_new_foldl_fun1236(f_0, xx_0, _ctx), _ctx);
    }
    { // tailcall
      xs = xx_0;
      z = x_0_10318;
      goto kk__tailcall;
    }
  }
  {
    kk_function_drop(f_0, _ctx);
    return z;
  }
}
extern kk_box_t kk_std_core_list_foldr_fun1238(kk_function_t _fself, kk_box_t x, kk_box_t y, kk_context_t* _ctx) {
  struct kk_std_core_list_foldr_fun1238__t* _self = kk_function_as(struct kk_std_core_list_foldr_fun1238__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (1244, 1245) -> 1246 1245 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);}, {}, _ctx)
  return kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), f, (f, y, x, _ctx), _ctx);
}


// lift anonymous function
struct kk_std_core_list_foldl1_fun1241__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_foldl1_fun1241(kk_function_t _fself, kk_box_t _b_x44, kk_box_t _b_x45, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foldl1_fun1241(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_foldl1_fun1241, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_foldl1_fun1241(kk_function_t _fself, kk_box_t _b_x44, kk_box_t _b_x45, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x1242 = kk_string_unbox(_b_x44); /*string*/
  kk_std_core_types__optional _x_x1243 = kk_std_core_types__optional_unbox(_b_x45, KK_OWNED, _ctx); /*? exception-info*/
  return kk_std_core_exn_throw(_x_x1242, _x_x1243, _ctx);
}

kk_box_t kk_std_core_list_foldl1(kk_std_core_types__list xs, kk_function_t f, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, f : (a, a) -> <exn|e> a) -> <exn|e> a */ 
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1239 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1239->head;
    kk_std_core_types__list xx = _con_x1239->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    return kk_std_core_list_foldl(xx, x, f, _ctx);
  }
  {
    kk_function_drop(f, _ctx);
    kk_ssize_t _b_x40_46;
    kk_std_core_hnd__htag _x_x1240 = kk_std_core_hnd__htag_dup(kk_std_core_exn_exn_fs__tag, _ctx); /*hnd/htag<exn>*/
    _b_x40_46 = kk_std_core_hnd__evv_index(_x_x1240, _ctx); /*hnd/ev-index*/
    kk_box_t _x_x1244;
    kk_string_t _x_x1245;
    kk_define_string_literal(, _s_x1246, 33, "unexpected Nil in std/core/foldl1", _ctx)
    _x_x1245 = kk_string_dup(_s_x1246, _ctx); /*string*/
    _x_x1244 = kk_string_box(_x_x1245); /*10665*/
    return kk_std_core_hnd__open_at2(_b_x40_46, kk_std_core_list_new_foldl1_fun1241(_ctx), _x_x1244, kk_std_core_types__optional_box(kk_std_core_types__new_None(_ctx), _ctx), _ctx);
  }
}


// lift anonymous function
struct kk_std_core_list_foldr1_fun1249__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_foldr1_fun1249(kk_function_t _fself, kk_box_t _b_x54, kk_box_t _b_x55, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foldr1_fun1249(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_foldr1_fun1249, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_foldr1_fun1249(kk_function_t _fself, kk_box_t _b_x54, kk_box_t _b_x55, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x1250 = kk_string_unbox(_b_x54); /*string*/
  kk_std_core_types__optional _x_x1251 = kk_std_core_types__optional_unbox(_b_x55, KK_OWNED, _ctx); /*? exception-info*/
  return kk_std_core_exn_throw(_x_x1250, _x_x1251, _ctx);
}

kk_box_t kk_std_core_list_foldr1(kk_std_core_types__list xs, kk_function_t f, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, f : (a, a) -> <exn|e> a) -> <exn|e> a */ 
  kk_std_core_types__list xs_0_10010 = kk_std_core_list_reverse_acc(kk_std_core_types__new_Nil(_ctx), xs, _ctx); /*list<1338>*/;
  if (kk_std_core_types__is_Cons(xs_0_10010, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1247 = kk_std_core_types__as_Cons(xs_0_10010, _ctx);
    kk_box_t x = _con_x1247->head;
    kk_std_core_types__list xx = _con_x1247->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs_0_10010, _ctx)) {
      kk_datatype_ptr_free(xs_0_10010, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs_0_10010, _ctx);
    }
    return kk_std_core_list_foldl(xx, x, f, _ctx);
  }
  {
    kk_function_drop(f, _ctx);
    kk_ssize_t _b_x50_56;
    kk_std_core_hnd__htag _x_x1248 = kk_std_core_hnd__htag_dup(kk_std_core_exn_exn_fs__tag, _ctx); /*hnd/htag<exn>*/
    _b_x50_56 = kk_std_core_hnd__evv_index(_x_x1248, _ctx); /*hnd/ev-index*/
    kk_box_t _x_x1252;
    kk_string_t _x_x1253;
    kk_define_string_literal(, _s_x1254, 33, "unexpected Nil in std/core/foldl1", _ctx)
    _x_x1253 = kk_string_dup(_s_x1254, _ctx); /*string*/
    _x_x1252 = kk_string_box(_x_x1253); /*10665*/
    return kk_std_core_hnd__open_at2(_b_x50_56, kk_std_core_list_new_foldr1_fun1249(_ctx), _x_x1252, kk_std_core_types__optional_box(kk_std_core_types__new_None(_ctx), _ctx), _ctx);
  }
}
 
// split a list at position `n`

kk_std_core_types__tuple2 kk_std_core_list_split(kk_std_core_types__list xs, kk_integer_t n, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, n : int) -> (list<a>, list<a>) */ 
  kk_std_core_types__list _b_x60_62;
  kk_std_core_types__list _x_x1255 = kk_std_core_types__list_dup(xs, _ctx); /*list<1381>*/
  kk_integer_t _x_x1256 = kk_integer_dup(n, _ctx); /*int*/
  kk_std_core_types__cctx _x_x1257 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  _b_x60_62 = kk_std_core_list__trmc_take(_x_x1255, _x_x1256, _x_x1257, _ctx); /*list<1381>*/
  kk_std_core_types__list _b_x61_63 = kk_std_core_list_drop(xs, n, _ctx); /*list<1381>*/;
  return kk_std_core_types__new_Tuple2(kk_std_core_types__list_box(_b_x60_62, _ctx), kk_std_core_types__list_box(_b_x61_63, _ctx), _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_drop_while_10281(kk_function_t predicate, kk_std_core_types__list xs, kk_std_core_types__list xx, bool _y_x10125, kk_context_t* _ctx) { /* forall<a,e> (predicate : (a) -> e bool, xs : list<a>, xx : list<a>, bool) -> e list<a> */ 
  if (_y_x10125) {
    kk_std_core_types__list_drop(xs, _ctx);
    return kk_std_core_list_drop_while(xx, predicate, _ctx);
  }
  {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(predicate, _ctx);
    return xs;
  }
}
 
// Drop all initial elements that satisfy `predicate`


// lift anonymous function
struct kk_std_core_list_drop_while_fun1261__t {
  struct kk_function_s _base;
  kk_function_t predicate_0;
  kk_std_core_types__list xs_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_drop_while_fun1261(kk_function_t _fself, kk_box_t _b_x65, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_drop_while_fun1261(kk_function_t predicate_0, kk_std_core_types__list xs_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_drop_while_fun1261__t* _self = kk_function_alloc_as(struct kk_std_core_list_drop_while_fun1261__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_drop_while_fun1261, kk_context());
  _self->predicate_0 = predicate_0;
  _self->xs_0 = xs_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_drop_while_fun1261(kk_function_t _fself, kk_box_t _b_x65, kk_context_t* _ctx) {
  struct kk_std_core_list_drop_while_fun1261__t* _self = kk_function_as(struct kk_std_core_list_drop_while_fun1261__t*, _fself, _ctx);
  kk_function_t predicate_0 = _self->predicate_0; /* (1427) -> 1428 bool */
  kk_std_core_types__list xs_0 = _self->xs_0; /* list<1427> */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<1427> */
  kk_drop_match(_self, {kk_function_dup(predicate_0, _ctx);kk_std_core_types__list_dup(xs_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10125_0_67 = kk_bool_unbox(_b_x65); /*bool*/;
  kk_std_core_types__list _x_x1262 = kk_std_core_list__mlift_drop_while_10281(predicate_0, xs_0, xx_0, _y_x10125_0_67, _ctx); /*list<1427>*/
  return kk_std_core_types__list_box(_x_x1262, _ctx);
}

kk_std_core_types__list kk_std_core_list_drop_while(kk_std_core_types__list xs_0, kk_function_t predicate_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, predicate : (a) -> e bool) -> e list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs_0, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1258 = kk_std_core_types__as_Cons(xs_0, _ctx);
    kk_box_t x = _con_x1258->head;
    kk_std_core_types__list xx_0 = _con_x1258->tail;
    kk_box_dup(x, _ctx);
    kk_std_core_types__list_dup(xx_0, _ctx);
    bool x_0_10323;
    kk_function_t _x_x1259 = kk_function_dup(predicate_0, _ctx); /*(1427) -> 1428 bool*/
    x_0_10323 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1259, (_x_x1259, x, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x1260 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_drop_while_fun1261(predicate_0, xs_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1260, KK_OWNED, _ctx);
    }
    if (x_0_10323) {
      if kk_likely(kk_datatype_ptr_is_unique(xs_0, _ctx)) {
        kk_std_core_types__list_drop(xx_0, _ctx);
        kk_box_drop(x, _ctx);
        kk_datatype_ptr_free(xs_0, _ctx);
      }
      else {
        kk_datatype_ptr_decref(xs_0, _ctx);
      }
      { // tailcall
        xs_0 = xx_0;
        goto kk__tailcall;
      }
    }
    {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_function_drop(predicate_0, _ctx);
      return xs_0;
    }
  }
  {
    kk_function_drop(predicate_0, _ctx);
    return kk_std_core_types__new_Nil(_ctx);
  }
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_filter_10282(kk_std_core_types__cctx _acc, kk_function_t pred, kk_box_t x, kk_std_core_types__list xx, bool _y_x10129, kk_context_t* _ctx) { /* forall<a,e> (ctx<list<a>>, pred : (a) -> e bool, x : a, xx : list<a>, bool) -> e list<a> */ 
  if (_y_x10129) {
    kk_std_core_types__list _trmc_x10052 = kk_datatype_null(); /*list<1493>*/;
    kk_std_core_types__list _trmc_x10053 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _trmc_x10052, _ctx); /*list<1493>*/;
    kk_field_addr_t _b_x73_76 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10053, _ctx)->tail, _ctx); /*@field-addr<list<1493>>*/;
    kk_std_core_types__cctx _x_x1263 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10053, _ctx)),_b_x73_76,kk_context()); /*ctx<0>*/
    return kk_std_core_list__trmc_filter(xx, pred, _x_x1263, _ctx);
  }
  {
    kk_box_drop(x, _ctx);
    return kk_std_core_list__trmc_filter(xx, pred, _acc, _ctx);
  }
}
 
// Retain only those elements of a list that satisfy the given predicate `pred`.
// For example: `filter([1,2,3],odd?) == [1,3]`


// lift anonymous function
struct kk_std_core_list__trmc_filter_fun1268__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t pred_0;
  kk_box_t x_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list__trmc_filter_fun1268(kk_function_t _fself, kk_box_t _b_x81, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_filter_fun1268(kk_std_core_types__cctx _acc_0, kk_function_t pred_0, kk_box_t x_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_filter_fun1268__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_filter_fun1268__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_filter_fun1268, kk_context());
  _self->_acc_0 = _acc_0;
  _self->pred_0 = pred_0;
  _self->x_0 = x_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_filter_fun1268(kk_function_t _fself, kk_box_t _b_x81, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_filter_fun1268__t* _self = kk_function_as(struct kk_std_core_list__trmc_filter_fun1268__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<1493>> */
  kk_function_t pred_0 = _self->pred_0; /* (1493) -> 1494 bool */
  kk_box_t x_0 = _self->x_0; /* 1493 */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<1493> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(pred_0, _ctx);kk_box_dup(x_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10129_0_99 = kk_bool_unbox(_b_x81); /*bool*/;
  kk_std_core_types__list _x_x1269 = kk_std_core_list__mlift_trmc_filter_10282(_acc_0, pred_0, x_0, xx_0, _y_x10129_0_99, _ctx); /*list<1493>*/
  return kk_std_core_types__list_box(_x_x1269, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_filter(kk_std_core_types__list xs, kk_function_t pred_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, pred : (a) -> e bool, ctx<list<a>>) -> e list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1264 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x_0 = _con_x1264->head;
    kk_std_core_types__list xx_0 = _con_x1264->tail;
    kk_reuse_t _ru_x1144 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1144 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x_0, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool x_1_10326;
    kk_function_t _x_x1266 = kk_function_dup(pred_0, _ctx); /*(1493) -> 1494 bool*/
    kk_box_t _x_x1265 = kk_box_dup(x_0, _ctx); /*1493*/
    x_1_10326 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1266, (_x_x1266, _x_x1265, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1144,kk_context());
      kk_box_t _x_x1267 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_filter_fun1268(_acc_0, pred_0, x_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1267, KK_OWNED, _ctx);
    }
    if (x_1_10326) {
      kk_std_core_types__list _trmc_x10052_0 = kk_datatype_null(); /*list<1493>*/;
      kk_std_core_types__list _trmc_x10053_0 = kk_std_core_types__new_Cons(_ru_x1144, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0, _trmc_x10052_0, _ctx); /*list<1493>*/;
      kk_field_addr_t _b_x87_93 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10053_0, _ctx)->tail, _ctx); /*@field-addr<list<1493>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1270 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10053_0, _ctx)),_b_x87_93,kk_context()); /*ctx<0>*/
        xs = xx_0;
        _acc_0 = _x_x1270;
        goto kk__tailcall;
      }
    }
    {
      kk_reuse_drop(_ru_x1144,kk_context());
      kk_box_drop(x_0, _ctx);
      { // tailcall
        xs = xx_0;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_function_drop(pred_0, _ctx);
    kk_box_t _x_x1271 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1271, KK_OWNED, _ctx);
  }
}
 
// Retain only those elements of a list that satisfy the given predicate `pred`.
// For example: `filter([1,2,3],odd?) == [1,3]`

kk_std_core_types__list kk_std_core_list_filter(kk_std_core_types__list xs_0, kk_function_t pred_1, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, pred : (a) -> e bool) -> e list<a> */ 
  kk_std_core_types__cctx _x_x1272 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_filter(xs_0, pred_1, _x_x1272, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_filter_map_10283(kk_std_core_types__cctx _acc, kk_function_t pred, kk_std_core_types__list xx, kk_std_core_types__maybe _y_x10135, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, pred : (a) -> e maybe<b>, xx : list<a>, maybe<b>) -> e list<b> */ 
  if (kk_std_core_types__is_Nothing(_y_x10135, _ctx)) {
    return kk_std_core_list__trmc_filter_map(xx, pred, _acc, _ctx);
  }
  {
    kk_box_t y = _y_x10135._cons.Just.value;
    kk_std_core_types__list _trmc_x10054 = kk_datatype_null(); /*list<1577>*/;
    kk_std_core_types__list _trmc_x10055 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _trmc_x10054, _ctx); /*list<1577>*/;
    kk_field_addr_t _b_x105_108 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10055, _ctx)->tail, _ctx); /*@field-addr<list<1577>>*/;
    kk_std_core_types__cctx _x_x1273 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10055, _ctx)),_b_x105_108,kk_context()); /*ctx<0>*/
    return kk_std_core_list__trmc_filter_map(xx, pred, _x_x1273, _ctx);
  }
}
 
// Retain only those elements of a list that satisfy the given predicate `pred`.
// For example: `filterMap([1,2,3],fn(i) { if i.odd? then Nothing else Just(i*i) }) == [4]`


// lift anonymous function
struct kk_std_core_list__trmc_filter_map_fun1278__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t pred_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list__trmc_filter_map_fun1278(kk_function_t _fself, kk_box_t _b_x115, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_filter_map_fun1278(kk_std_core_types__cctx _acc_0, kk_function_t pred_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_filter_map_fun1278__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_filter_map_fun1278__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_filter_map_fun1278, kk_context());
  _self->_acc_0 = _acc_0;
  _self->pred_0 = pred_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_filter_map_fun1278(kk_function_t _fself, kk_box_t _b_x115, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_filter_map_fun1278__t* _self = kk_function_as(struct kk_std_core_list__trmc_filter_map_fun1278__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<1577>> */
  kk_function_t pred_0 = _self->pred_0; /* (1576) -> 1578 maybe<1577> */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<1576> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(pred_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  kk_std_core_types__maybe _y_x10135_0_131 = kk_std_core_types__maybe_unbox(_b_x115, KK_OWNED, _ctx); /*maybe<1577>*/;
  kk_std_core_types__list _x_x1279 = kk_std_core_list__mlift_trmc_filter_map_10283(_acc_0, pred_0, xx_0, _y_x10135_0_131, _ctx); /*list<1577>*/
  return kk_std_core_types__list_box(_x_x1279, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_filter_map(kk_std_core_types__list xs, kk_function_t pred_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, pred : (a) -> e maybe<b>, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    kk_function_drop(pred_0, _ctx);
    kk_box_t _x_x1274 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1274, KK_OWNED, _ctx);
  }
  {
    struct kk_std_core_types_Cons* _con_x1275 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1275->head;
    kk_std_core_types__list xx_0 = _con_x1275->tail;
    kk_reuse_t _ru_x1145 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1145 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__maybe x_0_10329;
    kk_function_t _x_x1276 = kk_function_dup(pred_0, _ctx); /*(1576) -> 1578 maybe<1577>*/
    x_0_10329 = kk_function_call(kk_std_core_types__maybe, (kk_function_t, kk_box_t, kk_context_t*), _x_x1276, (_x_x1276, x, _ctx), _ctx); /*maybe<1577>*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1145,kk_context());
      kk_std_core_types__maybe_drop(x_0_10329, _ctx);
      kk_box_t _x_x1277 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_filter_map_fun1278(_acc_0, pred_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1277, KK_OWNED, _ctx);
    }
    if (kk_std_core_types__is_Nothing(x_0_10329, _ctx)) {
      kk_reuse_drop(_ru_x1145,kk_context());
      { // tailcall
        xs = xx_0;
        goto kk__tailcall;
      }
    }
    {
      kk_box_t y_0 = x_0_10329._cons.Just.value;
      kk_std_core_types__list _trmc_x10054_0 = kk_datatype_null(); /*list<1577>*/;
      kk_std_core_types__list _trmc_x10055_0 = kk_std_core_types__new_Cons(_ru_x1145, kk_field_index_of(struct kk_std_core_types_Cons, tail), y_0, _trmc_x10054_0, _ctx); /*list<1577>*/;
      kk_field_addr_t _b_x121_127 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10055_0, _ctx)->tail, _ctx); /*@field-addr<list<1577>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1280 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10055_0, _ctx)),_b_x121_127,kk_context()); /*ctx<0>*/
        xs = xx_0;
        _acc_0 = _x_x1280;
        goto kk__tailcall;
      }
    }
  }
}
 
// Retain only those elements of a list that satisfy the given predicate `pred`.
// For example: `filterMap([1,2,3],fn(i) { if i.odd? then Nothing else Just(i*i) }) == [4]`

kk_std_core_types__list kk_std_core_list_filter_map(kk_std_core_types__list xs_0, kk_function_t pred_1, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, pred : (a) -> e maybe<b>) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1281 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_filter_map(xs_0, pred_1, _x_x1281, _ctx);
}
 
// monadic lift

kk_std_core_types__maybe kk_std_core_list__mlift_foreach_while_10284(kk_function_t action, kk_std_core_types__list xx, kk_std_core_types__maybe _y_x10141, kk_context_t* _ctx) { /* forall<a,b,e> (action : (a) -> e maybe<b>, xx : list<a>, maybe<b>) -> e maybe<b> */ 
  if (kk_std_core_types__is_Nothing(_y_x10141, _ctx)) {
    return kk_std_core_list_foreach_while(xx, action, _ctx);
  }
  {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(action, _ctx);
    return _y_x10141;
  }
}
 
// Invoke `action` for each element of a list while `action` return `Nothing`


// lift anonymous function
struct kk_std_core_list_foreach_while_fun1285__t {
  struct kk_function_s _base;
  kk_function_t action_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_foreach_while_fun1285(kk_function_t _fself, kk_box_t _b_x133, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foreach_while_fun1285(kk_function_t action_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_while_fun1285__t* _self = kk_function_alloc_as(struct kk_std_core_list_foreach_while_fun1285__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_foreach_while_fun1285, kk_context());
  _self->action_0 = action_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_foreach_while_fun1285(kk_function_t _fself, kk_box_t _b_x133, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_while_fun1285__t* _self = kk_function_as(struct kk_std_core_list_foreach_while_fun1285__t*, _fself, _ctx);
  kk_function_t action_0 = _self->action_0; /* (1650) -> 1652 maybe<1651> */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<1650> */
  kk_drop_match(_self, {kk_function_dup(action_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  kk_std_core_types__maybe _y_x10141_0_135 = kk_std_core_types__maybe_unbox(_b_x133, KK_OWNED, _ctx); /*maybe<1651>*/;
  kk_std_core_types__maybe _x_x1286 = kk_std_core_list__mlift_foreach_while_10284(action_0, xx_0, _y_x10141_0_135, _ctx); /*maybe<1651>*/
  return kk_std_core_types__maybe_box(_x_x1286, _ctx);
}

kk_std_core_types__maybe kk_std_core_list_foreach_while(kk_std_core_types__list xs, kk_function_t action_0, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, action : (a) -> e maybe<b>) -> e maybe<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    kk_function_drop(action_0, _ctx);
    return kk_std_core_types__new_Nothing(_ctx);
  }
  {
    struct kk_std_core_types_Cons* _con_x1282 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1282->head;
    kk_std_core_types__list xx_0 = _con_x1282->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__maybe x_0_10332;
    kk_function_t _x_x1283 = kk_function_dup(action_0, _ctx); /*(1650) -> 1652 maybe<1651>*/
    x_0_10332 = kk_function_call(kk_std_core_types__maybe, (kk_function_t, kk_box_t, kk_context_t*), _x_x1283, (_x_x1283, x, _ctx), _ctx); /*maybe<1651>*/
    if (kk_yielding(kk_context())) {
      kk_std_core_types__maybe_drop(x_0_10332, _ctx);
      kk_box_t _x_x1284 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_foreach_while_fun1285(action_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__maybe_unbox(_x_x1284, KK_OWNED, _ctx);
    }
    if (kk_std_core_types__is_Nothing(x_0_10332, _ctx)) { // tailcall
                                                          xs = xx_0;
                                                          goto kk__tailcall;
    }
    {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_function_drop(action_0, _ctx);
      return x_0_10332;
    }
  }
}
 
// Find the first element satisfying some predicate


// lift anonymous function
struct kk_std_core_list_find_fun1287__t {
  struct kk_function_s _base;
  kk_function_t pred;
};
static kk_std_core_types__maybe kk_std_core_list_find_fun1287(kk_function_t _fself, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_find_fun1287(kk_function_t pred, kk_context_t* _ctx) {
  struct kk_std_core_list_find_fun1287__t* _self = kk_function_alloc_as(struct kk_std_core_list_find_fun1287__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_find_fun1287, kk_context());
  _self->pred = pred;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_list_find_fun1290__t {
  struct kk_function_s _base;
  kk_box_t x;
};
static kk_box_t kk_std_core_list_find_fun1290(kk_function_t _fself, kk_box_t _b_x137, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_find_fun1290(kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_list_find_fun1290__t* _self = kk_function_alloc_as(struct kk_std_core_list_find_fun1290__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_find_fun1290, kk_context());
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_find_fun1290(kk_function_t _fself, kk_box_t _b_x137, kk_context_t* _ctx) {
  struct kk_std_core_list_find_fun1290__t* _self = kk_function_as(struct kk_std_core_list_find_fun1290__t*, _fself, _ctx);
  kk_box_t x = _self->x; /* 1719 */
  kk_drop_match(_self, {kk_box_dup(x, _ctx);}, {}, _ctx)
  kk_std_core_types__maybe _x_x1291;
  bool _y_x10145_139 = kk_bool_unbox(_b_x137); /*bool*/;
  if (_y_x10145_139) {
    _x_x1291 = kk_std_core_types__new_Just(x, _ctx); /*maybe<88>*/
  }
  else {
    kk_box_drop(x, _ctx);
    _x_x1291 = kk_std_core_types__new_Nothing(_ctx); /*maybe<88>*/
  }
  return kk_std_core_types__maybe_box(_x_x1291, _ctx);
}
static kk_std_core_types__maybe kk_std_core_list_find_fun1287(kk_function_t _fself, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_list_find_fun1287__t* _self = kk_function_as(struct kk_std_core_list_find_fun1287__t*, _fself, _ctx);
  kk_function_t pred = _self->pred; /* (1719) -> 1720 bool */
  kk_drop_match(_self, {kk_function_dup(pred, _ctx);}, {}, _ctx)
  bool x_0_10335;
  kk_box_t _x_x1288 = kk_box_dup(x, _ctx); /*1719*/
  x_0_10335 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), pred, (pred, _x_x1288, _ctx), _ctx); /*bool*/
  if (kk_yielding(kk_context())) {
    kk_box_t _x_x1289 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_find_fun1290(x, _ctx), _ctx); /*2419*/
    return kk_std_core_types__maybe_unbox(_x_x1289, KK_OWNED, _ctx);
  }
  if (x_0_10335) {
    return kk_std_core_types__new_Just(x, _ctx);
  }
  {
    kk_box_drop(x, _ctx);
    return kk_std_core_types__new_Nothing(_ctx);
  }
}

kk_std_core_types__maybe kk_std_core_list_find(kk_std_core_types__list xs, kk_function_t pred, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, pred : (a) -> e bool) -> e maybe<a> */ 
  return kk_std_core_list_foreach_while(xs, kk_std_core_list_new_find_fun1287(pred, _ctx), _ctx);
}
 
// Returns an integer list of increasing elements from `lo`  to `hi`
// (including both `lo`  and `hi` ).
// If `lo > hi`  the function returns the empty list.

kk_std_core_types__list kk_std_core_list_range_fs__trmc_list(kk_integer_t lo, kk_integer_t hi, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* (lo : int, hi : int, ctx<list<int>>) -> list<int> */ 
  kk__tailcall: ;
  bool _match_x1117 = kk_integer_lte_borrow(lo,hi,kk_context()); /*bool*/;
  if (_match_x1117) {
    kk_std_core_types__list _trmc_x10056 = kk_datatype_null(); /*list<int>*/;
    kk_std_core_types__list _trmc_x10057;
    kk_box_t _x_x1292;
    kk_integer_t _x_x1293 = kk_integer_dup(lo, _ctx); /*int*/
    _x_x1292 = kk_integer_box(_x_x1293, _ctx); /*79*/
    _trmc_x10057 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x1292, _trmc_x10056, _ctx); /*list<int>*/
    kk_field_addr_t _b_x150_155 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10057, _ctx)->tail, _ctx); /*@field-addr<list<int>>*/;
    { // tailcall
      kk_integer_t _x_x1294 = kk_integer_add_small_const(lo, 1, _ctx); /*int*/
      kk_std_core_types__cctx _x_x1295 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10057, _ctx)),_b_x150_155,kk_context()); /*ctx<0>*/
      lo = _x_x1294;
      _acc = _x_x1295;
      goto kk__tailcall;
    }
  }
  {
    kk_integer_drop(lo, _ctx);
    kk_integer_drop(hi, _ctx);
    kk_box_t _x_x1296 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1296, KK_OWNED, _ctx);
  }
}
 
// Returns an integer list of increasing elements from `lo`  to `hi`
// (including both `lo`  and `hi` ).
// If `lo > hi`  the function returns the empty list.

kk_std_core_types__list kk_std_core_list_range_fs_list(kk_integer_t lo_0, kk_integer_t hi_0, kk_context_t* _ctx) { /* (lo : int, hi : int) -> list<int> */ 
  kk_std_core_types__cctx _x_x1297 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list_range_fs__trmc_list(lo_0, hi_0, _x_x1297, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_map_10286(kk_std_core_types__cctx _acc, kk_function_t f, kk_std_core_types__list xx, kk_box_t _trmc_x10058, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, f : (a) -> e b, xx : list<a>, b) -> e list<b> */ 
  kk_std_core_types__list _trmc_x10059 = kk_datatype_null(); /*list<2218>*/;
  kk_std_core_types__list _trmc_x10060 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10058, _trmc_x10059, _ctx); /*list<2218>*/;
  kk_field_addr_t _b_x166_169 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10060, _ctx)->tail, _ctx); /*@field-addr<list<2218>>*/;
  kk_std_core_types__cctx _own_x1115 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10060, _ctx)),_b_x166_169,kk_context()); /*ctx<0>*/;
  kk_std_core_types__list _brw_x1116 = kk_std_core_list__trmc_map(xx, f, _own_x1115, _ctx); /*list<2218>*/;
  kk_function_drop(f, _ctx);
  return _brw_x1116;
}
 
// Apply a function `f` to each element of the input list in sequence.


// lift anonymous function
struct kk_std_core_list__trmc_map_fun1302__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list__trmc_map_fun1302(kk_function_t _fself, kk_box_t _b_x174, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_map_fun1302(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_map_fun1302__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_map_fun1302__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_map_fun1302, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_map_fun1302(kk_function_t _fself, kk_box_t _b_x174, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_map_fun1302__t* _self = kk_function_as(struct kk_std_core_list__trmc_map_fun1302__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<2218>> */
  kk_function_t f_0 = _self->f_0; /* (2217) -> 2219 2218 */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<2217> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10058_0_192 = _b_x174; /*2218*/;
  kk_std_core_types__list _x_x1303 = kk_std_core_list__mlift_trmc_map_10286(_acc_0, f_0, xx_0, _trmc_x10058_0_192, _ctx); /*list<2218>*/
  return kk_std_core_types__list_box(_x_x1303, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_map(kk_std_core_types__list xs, kk_function_t f_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, f : (a) -> e b, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1298 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1298->head;
    kk_std_core_types__list xx_0 = _con_x1298->tail;
    kk_reuse_t _ru_x1147 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1147 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_box_t x_0_10339;
    kk_function_t _x_x1299 = kk_function_dup(f_0, _ctx); /*(2217) -> 2219 2218*/
    x_0_10339 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x1299, (_x_x1299, x, _ctx), _ctx); /*2218*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1147,kk_context());
      kk_box_drop(x_0_10339, _ctx);
      kk_box_t _x_x1300;
      kk_function_t _x_x1301;
      kk_function_dup(f_0, _ctx);
      _x_x1301 = kk_std_core_list__new_trmc_map_fun1302(_acc_0, f_0, xx_0, _ctx); /*(2418) -> 2420 2419*/
      _x_x1300 = kk_std_core_hnd_yield_extend(_x_x1301, _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1300, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__list _trmc_x10059_0 = kk_datatype_null(); /*list<2218>*/;
      kk_std_core_types__list _trmc_x10060_0 = kk_std_core_types__new_Cons(_ru_x1147, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0_10339, _trmc_x10059_0, _ctx); /*list<2218>*/;
      kk_field_addr_t _b_x180_186 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10060_0, _ctx)->tail, _ctx); /*@field-addr<list<2218>>*/;
      kk_std_core_types__cctx _own_x1114 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10060_0, _ctx)),_b_x180_186,kk_context()); /*ctx<0>*/;
      { // tailcall
        xs = xx_0;
        _acc_0 = _own_x1114;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_box_t _x_x1304 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1304, KK_OWNED, _ctx);
  }
}
 
// Apply a function `f` to each element of the input list in sequence.

kk_std_core_types__list kk_std_core_list_map(kk_std_core_types__list xs_0, kk_function_t f_1, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, f : (a) -> e b) -> e list<b> */ 
  kk_std_core_types__cctx _own_x1112 = kk_cctx_empty(kk_context()); /*ctx<0>*/;
  return kk_std_core_list__trmc_map(xs_0, f_1, _own_x1112, _ctx);
}
 
// Create a list of characters from `lo`  to `hi`  (including `hi`).


// lift anonymous function
struct kk_std_core_list_char_fs_list_fun1306__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_char_fs_list_fun1306(kk_function_t _fself, kk_box_t _b_x196, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_char_fs_new_list_fun1306(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_char_fs_list_fun1306, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_char_fs_list_fun1306(kk_function_t _fself, kk_box_t _b_x196, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_char_t _x_x1307;
  kk_integer_t _x_x1308 = kk_integer_unbox(_b_x196, _ctx); /*int*/
  _x_x1307 = kk_integer_clamp32(_x_x1308,kk_context()); /*char*/
  return kk_char_box(_x_x1307, _ctx);
}

kk_std_core_types__list kk_std_core_list_char_fs_list(kk_char_t lo, kk_char_t hi, kk_context_t* _ctx) { /* (lo : char, hi : char) -> list<char> */ 
  kk_integer_t lo_0_10344 = kk_integer_from_int(lo,kk_context()); /*int*/;
  kk_integer_t hi_0_10345 = kk_integer_from_int(hi,kk_context()); /*int*/;
  kk_std_core_types__list xs_10342;
  kk_std_core_types__cctx _x_x1305 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  xs_10342 = kk_std_core_list_range_fs__trmc_list(lo_0_10344, hi_0_10345, _x_x1305, _ctx); /*list<int>*/
  kk_std_core_types__cctx _b_x195_199 = kk_cctx_empty(kk_context()); /*ctx<list<char>>*/;
  kk_function_t _brw_x1110 = kk_std_core_list_char_fs_new_list_fun1306(_ctx); /*(2217) -> 2219 2218*/;
  kk_std_core_types__list _brw_x1111 = kk_std_core_list__trmc_map(xs_10342, _brw_x1110, _b_x195_199, _ctx); /*list<2218>*/;
  kk_function_drop(_brw_x1110, _ctx);
  return _brw_x1111;
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list_function_fs__mlift_trmc_list_10287(kk_std_core_types__cctx _acc, kk_function_t f, kk_integer_t hi, kk_integer_t lo, kk_box_t _trmc_x10061, kk_context_t* _ctx) { /* forall<a,e> (ctx<list<a>>, f : (int) -> e a, hi : int, lo : int, a) -> e list<a> */ 
  kk_std_core_types__list _trmc_x10062 = kk_datatype_null(); /*list<1927>*/;
  kk_std_core_types__list _trmc_x10063 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10061, _trmc_x10062, _ctx); /*list<1927>*/;
  kk_field_addr_t _b_x205_208 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10063, _ctx)->tail, _ctx); /*@field-addr<list<1927>>*/;
  kk_integer_t _x_x1309 = kk_integer_add_small_const(lo, 1, _ctx); /*int*/
  kk_std_core_types__cctx _x_x1310 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10063, _ctx)),_b_x205_208,kk_context()); /*ctx<0>*/
  return kk_std_core_list_function_fs__trmc_list(_x_x1309, hi, f, _x_x1310, _ctx);
}
 
// Applies a function `f` to list of increasing elements from `lo`  to `hi`
// (including both `lo`  and `hi` ).
// If `lo > hi`  the function returns the empty list.


// lift anonymous function
struct kk_std_core_list_function_fs__trmc_list_fun1314__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_integer_t hi_0;
  kk_integer_t lo_0;
};
static kk_box_t kk_std_core_list_function_fs__trmc_list_fun1314(kk_function_t _fself, kk_box_t _b_x213, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_function_fs__new_trmc_list_fun1314(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_integer_t hi_0, kk_integer_t lo_0, kk_context_t* _ctx) {
  struct kk_std_core_list_function_fs__trmc_list_fun1314__t* _self = kk_function_alloc_as(struct kk_std_core_list_function_fs__trmc_list_fun1314__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_function_fs__trmc_list_fun1314, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->hi_0 = hi_0;
  _self->lo_0 = lo_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_function_fs__trmc_list_fun1314(kk_function_t _fself, kk_box_t _b_x213, kk_context_t* _ctx) {
  struct kk_std_core_list_function_fs__trmc_list_fun1314__t* _self = kk_function_as(struct kk_std_core_list_function_fs__trmc_list_fun1314__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<1927>> */
  kk_function_t f_0 = _self->f_0; /* (int) -> 1928 1927 */
  kk_integer_t hi_0 = _self->hi_0; /* int */
  kk_integer_t lo_0 = _self->lo_0; /* int */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_integer_dup(hi_0, _ctx);kk_integer_dup(lo_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10061_0_231 = _b_x213; /*1927*/;
  kk_std_core_types__list _x_x1315 = kk_std_core_list_function_fs__mlift_trmc_list_10287(_acc_0, f_0, hi_0, lo_0, _trmc_x10061_0_231, _ctx); /*list<1927>*/
  return kk_std_core_types__list_box(_x_x1315, _ctx);
}

kk_std_core_types__list kk_std_core_list_function_fs__trmc_list(kk_integer_t lo_0, kk_integer_t hi_0, kk_function_t f_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,e> (lo : int, hi : int, f : (int) -> e a, ctx<list<a>>) -> e list<a> */ 
  kk__tailcall: ;
  bool _match_x1108 = kk_integer_lte_borrow(lo_0,hi_0,kk_context()); /*bool*/;
  if (_match_x1108) {
    kk_box_t x_10346;
    kk_function_t _x_x1312 = kk_function_dup(f_0, _ctx); /*(int) -> 1928 1927*/
    kk_integer_t _x_x1311 = kk_integer_dup(lo_0, _ctx); /*int*/
    x_10346 = kk_function_call(kk_box_t, (kk_function_t, kk_integer_t, kk_context_t*), _x_x1312, (_x_x1312, _x_x1311, _ctx), _ctx); /*1927*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_10346, _ctx);
      kk_box_t _x_x1313 = kk_std_core_hnd_yield_extend(kk_std_core_list_function_fs__new_trmc_list_fun1314(_acc_0, f_0, hi_0, lo_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1313, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__list _trmc_x10062_0 = kk_datatype_null(); /*list<1927>*/;
      kk_std_core_types__list _trmc_x10063_0 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_10346, _trmc_x10062_0, _ctx); /*list<1927>*/;
      kk_field_addr_t _b_x219_225 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10063_0, _ctx)->tail, _ctx); /*@field-addr<list<1927>>*/;
      { // tailcall
        kk_integer_t _x_x1316 = kk_integer_add_small_const(lo_0, 1, _ctx); /*int*/
        kk_std_core_types__cctx _x_x1317 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10063_0, _ctx)),_b_x219_225,kk_context()); /*ctx<0>*/
        lo_0 = _x_x1316;
        _acc_0 = _x_x1317;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_integer_drop(lo_0, _ctx);
    kk_integer_drop(hi_0, _ctx);
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1318 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1318, KK_OWNED, _ctx);
  }
}
 
// Applies a function `f` to list of increasing elements from `lo`  to `hi`
// (including both `lo`  and `hi` ).
// If `lo > hi`  the function returns the empty list.

kk_std_core_types__list kk_std_core_list_function_fs_list(kk_integer_t lo_1, kk_integer_t hi_1, kk_function_t f_1, kk_context_t* _ctx) { /* forall<a,e> (lo : int, hi : int, f : (int) -> e a) -> e list<a> */ 
  kk_std_core_types__cctx _x_x1319 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list_function_fs__trmc_list(lo_1, hi_1, f_1, _x_x1319, _ctx);
}
 
// Returns an integer list of increasing elements from `lo`  to `hi` with stride `stride`.
// If `lo > hi`  the function returns the empty list.

kk_std_core_types__list kk_std_core_list_stride_fs__trmc_list(kk_integer_t lo, kk_integer_t hi, kk_integer_t stride, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* (lo : int, hi : int, stride : int, ctx<list<int>>) -> list<int> */ 
  kk__tailcall: ;
  bool _match_x1107 = kk_integer_lte_borrow(lo,hi,kk_context()); /*bool*/;
  if (_match_x1107) {
    kk_std_core_types__list _trmc_x10064 = kk_datatype_null(); /*list<int>*/;
    kk_std_core_types__list _trmc_x10065;
    kk_box_t _x_x1320;
    kk_integer_t _x_x1321 = kk_integer_dup(lo, _ctx); /*int*/
    _x_x1320 = kk_integer_box(_x_x1321, _ctx); /*79*/
    _trmc_x10065 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x1320, _trmc_x10064, _ctx); /*list<int>*/
    kk_field_addr_t _b_x241_246 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10065, _ctx)->tail, _ctx); /*@field-addr<list<int>>*/;
    { // tailcall
      kk_integer_t _x_x1322;
      kk_integer_t _x_x1323 = kk_integer_dup(stride, _ctx); /*int*/
      _x_x1322 = kk_integer_add(lo,_x_x1323,kk_context()); /*int*/
      kk_std_core_types__cctx _x_x1324 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10065, _ctx)),_b_x241_246,kk_context()); /*ctx<0>*/
      lo = _x_x1322;
      _acc = _x_x1324;
      goto kk__tailcall;
    }
  }
  {
    kk_integer_drop(stride, _ctx);
    kk_integer_drop(lo, _ctx);
    kk_integer_drop(hi, _ctx);
    kk_box_t _x_x1325 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1325, KK_OWNED, _ctx);
  }
}
 
// Returns an integer list of increasing elements from `lo`  to `hi` with stride `stride`.
// If `lo > hi`  the function returns the empty list.

kk_std_core_types__list kk_std_core_list_stride_fs_list(kk_integer_t lo_0, kk_integer_t hi_0, kk_integer_t stride_0, kk_context_t* _ctx) { /* (lo : int, hi : int, stride : int) -> list<int> */ 
  kk_std_core_types__cctx _x_x1326 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list_stride_fs__trmc_list(lo_0, hi_0, stride_0, _x_x1326, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list_stridefunction_fs__mlift_trmc_list_10288(kk_std_core_types__cctx _acc, kk_function_t f, kk_integer_t hi, kk_integer_t lo, kk_integer_t stride, kk_box_t _trmc_x10066, kk_context_t* _ctx) { /* forall<a,e> (ctx<list<a>>, f : (int) -> e a, hi : int, lo : int, stride : int, a) -> e list<a> */ 
  kk_std_core_types__list _trmc_x10067 = kk_datatype_null(); /*list<2107>*/;
  kk_std_core_types__list _trmc_x10068 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10066, _trmc_x10067, _ctx); /*list<2107>*/;
  kk_field_addr_t _b_x257_260 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10068, _ctx)->tail, _ctx); /*@field-addr<list<2107>>*/;
  kk_integer_t _x_x1327;
  kk_integer_t _x_x1328 = kk_integer_dup(stride, _ctx); /*int*/
  _x_x1327 = kk_integer_add(lo,_x_x1328,kk_context()); /*int*/
  kk_std_core_types__cctx _x_x1329 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10068, _ctx)),_b_x257_260,kk_context()); /*ctx<0>*/
  return kk_std_core_list_stridefunction_fs__trmc_list(_x_x1327, hi, stride, f, _x_x1329, _ctx);
}
 
// Returns an integer list of increasing elements from `lo`  to `hi` with stride `stride`.
// If `lo > hi`  the function returns the empty list.


// lift anonymous function
struct kk_std_core_list_stridefunction_fs__trmc_list_fun1333__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_integer_t hi_0;
  kk_integer_t lo_0;
  kk_integer_t stride_0;
};
static kk_box_t kk_std_core_list_stridefunction_fs__trmc_list_fun1333(kk_function_t _fself, kk_box_t _b_x265, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_stridefunction_fs__new_trmc_list_fun1333(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_integer_t hi_0, kk_integer_t lo_0, kk_integer_t stride_0, kk_context_t* _ctx) {
  struct kk_std_core_list_stridefunction_fs__trmc_list_fun1333__t* _self = kk_function_alloc_as(struct kk_std_core_list_stridefunction_fs__trmc_list_fun1333__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_stridefunction_fs__trmc_list_fun1333, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->hi_0 = hi_0;
  _self->lo_0 = lo_0;
  _self->stride_0 = stride_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_stridefunction_fs__trmc_list_fun1333(kk_function_t _fself, kk_box_t _b_x265, kk_context_t* _ctx) {
  struct kk_std_core_list_stridefunction_fs__trmc_list_fun1333__t* _self = kk_function_as(struct kk_std_core_list_stridefunction_fs__trmc_list_fun1333__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<2107>> */
  kk_function_t f_0 = _self->f_0; /* (int) -> 2108 2107 */
  kk_integer_t hi_0 = _self->hi_0; /* int */
  kk_integer_t lo_0 = _self->lo_0; /* int */
  kk_integer_t stride_0 = _self->stride_0; /* int */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_integer_dup(hi_0, _ctx);kk_integer_dup(lo_0, _ctx);kk_integer_dup(stride_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10066_0_283 = _b_x265; /*2107*/;
  kk_std_core_types__list _x_x1334 = kk_std_core_list_stridefunction_fs__mlift_trmc_list_10288(_acc_0, f_0, hi_0, lo_0, stride_0, _trmc_x10066_0_283, _ctx); /*list<2107>*/
  return kk_std_core_types__list_box(_x_x1334, _ctx);
}

kk_std_core_types__list kk_std_core_list_stridefunction_fs__trmc_list(kk_integer_t lo_0, kk_integer_t hi_0, kk_integer_t stride_0, kk_function_t f_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,e> (lo : int, hi : int, stride : int, f : (int) -> e a, ctx<list<a>>) -> e list<a> */ 
  kk__tailcall: ;
  bool _match_x1105 = kk_integer_lte_borrow(lo_0,hi_0,kk_context()); /*bool*/;
  if (_match_x1105) {
    kk_box_t x_10349;
    kk_function_t _x_x1331 = kk_function_dup(f_0, _ctx); /*(int) -> 2108 2107*/
    kk_integer_t _x_x1330 = kk_integer_dup(lo_0, _ctx); /*int*/
    x_10349 = kk_function_call(kk_box_t, (kk_function_t, kk_integer_t, kk_context_t*), _x_x1331, (_x_x1331, _x_x1330, _ctx), _ctx); /*2107*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_10349, _ctx);
      kk_box_t _x_x1332 = kk_std_core_hnd_yield_extend(kk_std_core_list_stridefunction_fs__new_trmc_list_fun1333(_acc_0, f_0, hi_0, lo_0, stride_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1332, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__list _trmc_x10067_0 = kk_datatype_null(); /*list<2107>*/;
      kk_std_core_types__list _trmc_x10068_0 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_10349, _trmc_x10067_0, _ctx); /*list<2107>*/;
      kk_field_addr_t _b_x271_277 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10068_0, _ctx)->tail, _ctx); /*@field-addr<list<2107>>*/;
      { // tailcall
        kk_integer_t _x_x1335;
        kk_integer_t _x_x1336 = kk_integer_dup(stride_0, _ctx); /*int*/
        _x_x1335 = kk_integer_add(lo_0,_x_x1336,kk_context()); /*int*/
        kk_std_core_types__cctx _x_x1337 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10068_0, _ctx)),_b_x271_277,kk_context()); /*ctx<0>*/
        lo_0 = _x_x1335;
        _acc_0 = _x_x1337;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_integer_drop(stride_0, _ctx);
    kk_integer_drop(lo_0, _ctx);
    kk_integer_drop(hi_0, _ctx);
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1338 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1338, KK_OWNED, _ctx);
  }
}
 
// Returns an integer list of increasing elements from `lo`  to `hi` with stride `stride`.
// If `lo > hi`  the function returns the empty list.

kk_std_core_types__list kk_std_core_list_stridefunction_fs_list(kk_integer_t lo_1, kk_integer_t hi_1, kk_integer_t stride_1, kk_function_t f_1, kk_context_t* _ctx) { /* forall<a,e> (lo : int, hi : int, stride : int, f : (int) -> e a) -> e list<a> */ 
  kk_std_core_types__cctx _x_x1339 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list_stridefunction_fs__trmc_list(lo_1, hi_1, stride_1, f_1, _x_x1339, _ctx);
}
 
// Apply a function `f` to each character in a string


// lift anonymous function
struct kk_std_core_list_string_fs_map_fun1340__t {
  struct kk_function_s _base;
  kk_function_t f;
};
static kk_box_t kk_std_core_list_string_fs_map_fun1340(kk_function_t _fself, kk_box_t _b_x287, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_string_fs_new_map_fun1340(kk_function_t f, kk_context_t* _ctx) {
  struct kk_std_core_list_string_fs_map_fun1340__t* _self = kk_function_alloc_as(struct kk_std_core_list_string_fs_map_fun1340__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_string_fs_map_fun1340, kk_context());
  _self->f = f;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_string_fs_map_fun1340(kk_function_t _fself, kk_box_t _b_x287, kk_context_t* _ctx) {
  struct kk_std_core_list_string_fs_map_fun1340__t* _self = kk_function_as(struct kk_std_core_list_string_fs_map_fun1340__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (char) -> 2160 char */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);}, {}, _ctx)
  kk_char_t _x_x1341;
  kk_char_t _x_x1342 = kk_char_unbox(_b_x287, KK_OWNED, _ctx); /*char*/
  _x_x1341 = kk_function_call(kk_char_t, (kk_function_t, kk_char_t, kk_context_t*), f, (f, _x_x1342, _ctx), _ctx); /*char*/
  return kk_char_box(_x_x1341, _ctx);
}


// lift anonymous function
struct kk_std_core_list_string_fs_map_fun1344__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_string_fs_map_fun1344(kk_function_t _fself, kk_box_t _b_x292, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_string_fs_new_map_fun1344(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_string_fs_map_fun1344, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_string_fs_map_fun1344(kk_function_t _fself, kk_box_t _b_x292, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x1345;
  kk_std_core_types__list _x_x1346 = kk_std_core_types__list_unbox(_b_x292, KK_OWNED, _ctx); /*list<char>*/
  _x_x1345 = kk_std_core_string_listchar_fs_string(_x_x1346, _ctx); /*string*/
  return kk_string_box(_x_x1345);
}

kk_string_t kk_std_core_list_string_fs_map(kk_string_t s, kk_function_t f, kk_context_t* _ctx) { /* forall<e> (s : string, f : (char) -> e char) -> e string */ 
  kk_std_core_types__list xs_10354 = kk_std_core_string_list(s, _ctx); /*list<char>*/;
  kk_std_core_types__cctx _b_x286_290 = kk_cctx_empty(kk_context()); /*ctx<list<char>>*/;
  kk_std_core_types__list x_10352;
  kk_function_t _brw_x1103 = kk_std_core_list_string_fs_new_map_fun1340(f, _ctx); /*(2217) -> 2219 2218*/;
  kk_std_core_types__list _brw_x1104 = kk_std_core_list__trmc_map(xs_10354, _brw_x1103, _b_x286_290, _ctx); /*list<2218>*/;
  kk_function_drop(_brw_x1103, _ctx);
  x_10352 = _brw_x1104; /*list<char>*/
  if (kk_yielding(kk_context())) {
    kk_std_core_types__list_drop(x_10352, _ctx);
    kk_box_t _x_x1343 = kk_std_core_hnd_yield_extend(kk_std_core_list_string_fs_new_map_fun1344(_ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x1343);
  }
  {
    return kk_std_core_string_listchar_fs_string(x_10352, _ctx);
  }
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_lift_map_indexed_5731_10289(kk_std_core_types__cctx _acc, kk_function_t f, kk_integer_t i_0_10018, kk_std_core_types__list yy, kk_box_t _trmc_x10069, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, f : (idx : int, value : a) -> e b, i@0@10018 : int, yy : list<a>, b) -> e list<b> */ 
  kk_std_core_types__list _trmc_x10070 = kk_datatype_null(); /*list<2316>*/;
  kk_std_core_types__list _trmc_x10071 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10069, _trmc_x10070, _ctx); /*list<2316>*/;
  kk_field_addr_t _b_x299_302 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10071, _ctx)->tail, _ctx); /*@field-addr<list<2316>>*/;
  kk_std_core_types__cctx _x_x1347 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10071, _ctx)),_b_x299_302,kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_map_indexed_5731(f, yy, i_0_10018, _x_x1347, _ctx);
}
 
// lifted local: map-indexed, map-idx


// lift anonymous function
struct kk_std_core_list__trmc_lift_map_indexed_5731_fun1352__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_integer_t i_0_10018_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__trmc_lift_map_indexed_5731_fun1352(kk_function_t _fself, kk_box_t _b_x307, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_lift_map_indexed_5731_fun1352(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_integer_t i_0_10018_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_map_indexed_5731_fun1352__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_lift_map_indexed_5731_fun1352__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_lift_map_indexed_5731_fun1352, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->i_0_10018_0 = i_0_10018_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_lift_map_indexed_5731_fun1352(kk_function_t _fself, kk_box_t _b_x307, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_map_indexed_5731_fun1352__t* _self = kk_function_as(struct kk_std_core_list__trmc_lift_map_indexed_5731_fun1352__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<2316>> */
  kk_function_t f_0 = _self->f_0; /* (idx : int, value : 2315) -> 2317 2316 */
  kk_integer_t i_0_10018_0 = _self->i_0_10018_0; /* int */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<2315> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_integer_dup(i_0_10018_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10069_0_325 = _b_x307; /*2316*/;
  kk_std_core_types__list _x_x1353 = kk_std_core_list__mlift_trmc_lift_map_indexed_5731_10289(_acc_0, f_0, i_0_10018_0, yy_0, _trmc_x10069_0_325, _ctx); /*list<2316>*/
  return kk_std_core_types__list_box(_x_x1353, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_lift_map_indexed_5731(kk_function_t f_0, kk_std_core_types__list ys, kk_integer_t i, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (idx : int, value : a) -> e b, ys : list<a>, i : int, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1348 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t y = _con_x1348->head;
    kk_std_core_types__list yy_0 = _con_x1348->tail;
    kk_reuse_t _ru_x1148 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1148 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(y, _ctx);
      kk_std_core_types__list_dup(yy_0, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_integer_t i_0_10018_0;
    kk_integer_t _x_x1349 = kk_integer_dup(i, _ctx); /*int*/
    i_0_10018_0 = kk_integer_add_small_const(_x_x1349, 1, _ctx); /*int*/
    kk_box_t x_10356;
    kk_function_t _x_x1350 = kk_function_dup(f_0, _ctx); /*(idx : int, value : 2315) -> 2317 2316*/
    x_10356 = kk_function_call(kk_box_t, (kk_function_t, kk_integer_t, kk_box_t, kk_context_t*), _x_x1350, (_x_x1350, i, y, _ctx), _ctx); /*2316*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1148,kk_context());
      kk_box_drop(x_10356, _ctx);
      kk_box_t _x_x1351 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_lift_map_indexed_5731_fun1352(_acc_0, f_0, i_0_10018_0, yy_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1351, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__list _trmc_x10070_0 = kk_datatype_null(); /*list<2316>*/;
      kk_std_core_types__list _trmc_x10071_0 = kk_std_core_types__new_Cons(_ru_x1148, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_10356, _trmc_x10070_0, _ctx); /*list<2316>*/;
      kk_field_addr_t _b_x313_319 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10071_0, _ctx)->tail, _ctx); /*@field-addr<list<2316>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1354 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10071_0, _ctx)),_b_x313_319,kk_context()); /*ctx<0>*/
        ys = yy_0;
        i = i_0_10018_0;
        _acc_0 = _x_x1354;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_integer_drop(i, _ctx);
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1355 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1355, KK_OWNED, _ctx);
  }
}
 
// lifted local: map-indexed, map-idx

kk_std_core_types__list kk_std_core_list__lift_map_indexed_5731(kk_function_t f_1, kk_std_core_types__list ys_0, kk_integer_t i_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (idx : int, value : a) -> e b, ys : list<a>, i : int) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1356 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_map_indexed_5731(f_1, ys_0, i_0, _x_x1356, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_lift_map_peek_5732_10290(kk_std_core_types__cctx _acc, kk_function_t f, kk_std_core_types__list yy, kk_box_t _trmc_x10072, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, f : (value : a, rest : list<a>) -> e b, yy : list<a>, b) -> e list<b> */ 
  kk_std_core_types__list _trmc_x10073 = kk_datatype_null(); /*list<2378>*/;
  kk_std_core_types__list _trmc_x10074 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10072, _trmc_x10073, _ctx); /*list<2378>*/;
  kk_field_addr_t _b_x331_334 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10074, _ctx)->tail, _ctx); /*@field-addr<list<2378>>*/;
  kk_std_core_types__cctx _x_x1358 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10074, _ctx)),_b_x331_334,kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_map_peek_5732(f, yy, _x_x1358, _ctx);
}
 
// lifted local: map-peek, mappeek


// lift anonymous function
struct kk_std_core_list__trmc_lift_map_peek_5732_fun1363__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__trmc_lift_map_peek_5732_fun1363(kk_function_t _fself, kk_box_t _b_x339, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_lift_map_peek_5732_fun1363(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_map_peek_5732_fun1363__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_lift_map_peek_5732_fun1363__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_lift_map_peek_5732_fun1363, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_lift_map_peek_5732_fun1363(kk_function_t _fself, kk_box_t _b_x339, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_map_peek_5732_fun1363__t* _self = kk_function_as(struct kk_std_core_list__trmc_lift_map_peek_5732_fun1363__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<2378>> */
  kk_function_t f_0 = _self->f_0; /* (value : 2377, rest : list<2377>) -> 2379 2378 */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<2377> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10072_0_357 = _b_x339; /*2378*/;
  kk_std_core_types__list _x_x1364 = kk_std_core_list__mlift_trmc_lift_map_peek_5732_10290(_acc_0, f_0, yy_0, _trmc_x10072_0_357, _ctx); /*list<2378>*/
  return kk_std_core_types__list_box(_x_x1364, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_lift_map_peek_5732(kk_function_t f_0, kk_std_core_types__list ys, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (value : a, rest : list<a>) -> e b, ys : list<a>, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1359 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t y = _con_x1359->head;
    kk_std_core_types__list yy_0 = _con_x1359->tail;
    kk_reuse_t _ru_x1149 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1149 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(y, _ctx);
      kk_std_core_types__list_dup(yy_0, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_box_t x_10362;
    kk_function_t _x_x1361 = kk_function_dup(f_0, _ctx); /*(value : 2377, rest : list<2377>) -> 2379 2378*/
    kk_std_core_types__list _x_x1360 = kk_std_core_types__list_dup(yy_0, _ctx); /*list<2377>*/
    x_10362 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_std_core_types__list, kk_context_t*), _x_x1361, (_x_x1361, y, _x_x1360, _ctx), _ctx); /*2378*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1149,kk_context());
      kk_box_drop(x_10362, _ctx);
      kk_box_t _x_x1362 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_lift_map_peek_5732_fun1363(_acc_0, f_0, yy_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1362, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__list _trmc_x10073_0 = kk_datatype_null(); /*list<2378>*/;
      kk_std_core_types__list _trmc_x10074_0 = kk_std_core_types__new_Cons(_ru_x1149, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_10362, _trmc_x10073_0, _ctx); /*list<2378>*/;
      kk_field_addr_t _b_x345_351 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10074_0, _ctx)->tail, _ctx); /*@field-addr<list<2378>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1365 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10074_0, _ctx)),_b_x345_351,kk_context()); /*ctx<0>*/
        ys = yy_0;
        _acc_0 = _x_x1365;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1366 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1366, KK_OWNED, _ctx);
  }
}
 
// lifted local: map-peek, mappeek

kk_std_core_types__list kk_std_core_list__lift_map_peek_5732(kk_function_t f_1, kk_std_core_types__list ys_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (value : a, rest : list<a>) -> e b, ys : list<a>) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1367 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_map_peek_5732(f_1, ys_0, _x_x1367, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_lift_map_indexed_peek_5733_10291(kk_std_core_types__cctx _acc, kk_function_t f, kk_integer_t i_0_10021, kk_std_core_types__list yy, kk_box_t _trmc_x10075, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, f : (idx : int, value : a, rest : list<a>) -> e b, i@0@10021 : int, yy : list<a>, b) -> e list<b> */ 
  kk_std_core_types__list _trmc_x10076 = kk_datatype_null(); /*list<2449>*/;
  kk_std_core_types__list _trmc_x10077 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10075, _trmc_x10076, _ctx); /*list<2449>*/;
  kk_field_addr_t _b_x363_366 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10077, _ctx)->tail, _ctx); /*@field-addr<list<2449>>*/;
  kk_std_core_types__cctx _x_x1369 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10077, _ctx)),_b_x363_366,kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_map_indexed_peek_5733(f, yy, i_0_10021, _x_x1369, _ctx);
}
 
// lifted local: map-indexed-peek, mapidx


// lift anonymous function
struct kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_integer_t i_0_10021_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375(kk_function_t _fself, kk_box_t _b_x371, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_lift_map_indexed_peek_5733_fun1375(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_integer_t i_0_10021_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->i_0_10021_0 = i_0_10021_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375(kk_function_t _fself, kk_box_t _b_x371, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375__t* _self = kk_function_as(struct kk_std_core_list__trmc_lift_map_indexed_peek_5733_fun1375__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<2449>> */
  kk_function_t f_0 = _self->f_0; /* (idx : int, value : 2448, rest : list<2448>) -> 2450 2449 */
  kk_integer_t i_0_10021_0 = _self->i_0_10021_0; /* int */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<2448> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_integer_dup(i_0_10021_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10075_0_389 = _b_x371; /*2449*/;
  kk_std_core_types__list _x_x1376 = kk_std_core_list__mlift_trmc_lift_map_indexed_peek_5733_10291(_acc_0, f_0, i_0_10021_0, yy_0, _trmc_x10075_0_389, _ctx); /*list<2449>*/
  return kk_std_core_types__list_box(_x_x1376, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_lift_map_indexed_peek_5733(kk_function_t f_0, kk_std_core_types__list ys, kk_integer_t i, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (idx : int, value : a, rest : list<a>) -> e b, ys : list<a>, i : int, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1370 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t y = _con_x1370->head;
    kk_std_core_types__list yy_0 = _con_x1370->tail;
    kk_reuse_t _ru_x1150 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1150 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(y, _ctx);
      kk_std_core_types__list_dup(yy_0, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_integer_t i_0_10021_0;
    kk_integer_t _x_x1371 = kk_integer_dup(i, _ctx); /*int*/
    i_0_10021_0 = kk_integer_add_small_const(_x_x1371, 1, _ctx); /*int*/
    kk_box_t x_10367;
    kk_function_t _x_x1373 = kk_function_dup(f_0, _ctx); /*(idx : int, value : 2448, rest : list<2448>) -> 2450 2449*/
    kk_std_core_types__list _x_x1372 = kk_std_core_types__list_dup(yy_0, _ctx); /*list<2448>*/
    x_10367 = kk_function_call(kk_box_t, (kk_function_t, kk_integer_t, kk_box_t, kk_std_core_types__list, kk_context_t*), _x_x1373, (_x_x1373, i, y, _x_x1372, _ctx), _ctx); /*2449*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1150,kk_context());
      kk_box_drop(x_10367, _ctx);
      kk_box_t _x_x1374 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_lift_map_indexed_peek_5733_fun1375(_acc_0, f_0, i_0_10021_0, yy_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1374, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__list _trmc_x10076_0 = kk_datatype_null(); /*list<2449>*/;
      kk_std_core_types__list _trmc_x10077_0 = kk_std_core_types__new_Cons(_ru_x1150, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_10367, _trmc_x10076_0, _ctx); /*list<2449>*/;
      kk_field_addr_t _b_x377_383 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10077_0, _ctx)->tail, _ctx); /*@field-addr<list<2449>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1377 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10077_0, _ctx)),_b_x377_383,kk_context()); /*ctx<0>*/
        ys = yy_0;
        i = i_0_10021_0;
        _acc_0 = _x_x1377;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_integer_drop(i, _ctx);
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1378 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1378, KK_OWNED, _ctx);
  }
}
 
// lifted local: map-indexed-peek, mapidx

kk_std_core_types__list kk_std_core_list__lift_map_indexed_peek_5733(kk_function_t f_1, kk_std_core_types__list ys_0, kk_integer_t i_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (idx : int, value : a, rest : list<a>) -> e b, ys : list<a>, i : int) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1379 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_map_indexed_peek_5733(f_1, ys_0, i_0, _x_x1379, _ctx);
}
 
// Create a list of `n` repeated elements `x`

kk_std_core_types__list kk_std_core_list__trmc_replicate(kk_box_t x, kk_integer_t n, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (x : a, n : int, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  bool _match_x1098 = kk_integer_gt_borrow(n,(kk_integer_from_small(0)),kk_context()); /*bool*/;
  if (_match_x1098) {
    kk_std_core_types__list _trmc_x10078 = kk_datatype_null(); /*list<2508>*/;
    kk_std_core_types__list _trmc_x10079;
    kk_box_t _x_x1381 = kk_box_dup(x, _ctx); /*2508*/
    _trmc_x10079 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x1381, _trmc_x10078, _ctx); /*list<2508>*/
    kk_field_addr_t _b_x395_400 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10079, _ctx)->tail, _ctx); /*@field-addr<list<2508>>*/;
    { // tailcall
      kk_integer_t _x_x1382 = kk_integer_add_small_const(n, -1, _ctx); /*int*/
      kk_std_core_types__cctx _x_x1383 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10079, _ctx)),_b_x395_400,kk_context()); /*ctx<0>*/
      n = _x_x1382;
      _acc = _x_x1383;
      goto kk__tailcall;
    }
  }
  {
    kk_box_drop(x, _ctx);
    kk_integer_drop(n, _ctx);
    kk_box_t _x_x1384 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1384, KK_OWNED, _ctx);
  }
}
 
// Create a list of `n` repeated elements `x`

kk_std_core_types__list kk_std_core_list_replicate(kk_box_t x_0, kk_integer_t n_0, kk_context_t* _ctx) { /* forall<a> (x : a, n : int) -> list<a> */ 
  kk_std_core_types__cctx _x_x1385 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_replicate(x_0, n_0, _x_x1385, _ctx);
}
 
// Remove those elements of a list that satisfy the given predicate `pred`.
// For example: `remove([1,2,3],odd?) == [2]`


// lift anonymous function
struct kk_std_core_list_remove_fun1386__t {
  struct kk_function_s _base;
  kk_function_t pred;
};
static bool kk_std_core_list_remove_fun1386(kk_function_t _fself, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_remove_fun1386(kk_function_t pred, kk_context_t* _ctx) {
  struct kk_std_core_list_remove_fun1386__t* _self = kk_function_alloc_as(struct kk_std_core_list_remove_fun1386__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_remove_fun1386, kk_context());
  _self->pred = pred;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_list_remove_fun1388__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_remove_fun1388(kk_function_t _fself, kk_box_t _b_x407, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_remove_fun1388(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_remove_fun1388, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_remove_fun1388(kk_function_t _fself, kk_box_t _b_x407, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  bool _y_x10176_409 = kk_bool_unbox(_b_x407); /*bool*/;
  bool _x_x1389;
  if (_y_x10176_409) {
    _x_x1389 = false; /*bool*/
  }
  else {
    _x_x1389 = true; /*bool*/
  }
  return kk_bool_box(_x_x1389);
}
static bool kk_std_core_list_remove_fun1386(kk_function_t _fself, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_list_remove_fun1386__t* _self = kk_function_as(struct kk_std_core_list_remove_fun1386__t*, _fself, _ctx);
  kk_function_t pred = _self->pred; /* (2548) -> 2549 bool */
  kk_drop_match(_self, {kk_function_dup(pred, _ctx);}, {}, _ctx)
  bool x_0_10375 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), pred, (pred, x, _ctx), _ctx); /*bool*/;
  if (kk_yielding(kk_context())) {
    kk_box_t _x_x1387 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_remove_fun1388(_ctx), _ctx); /*2419*/
    return kk_bool_unbox(_x_x1387);
  }
  if (x_0_10375) {
    return false;
  }
  {
    return true;
  }
}

kk_std_core_types__list kk_std_core_list_remove(kk_std_core_types__list xs, kk_function_t pred, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, pred : (a) -> e bool) -> e list<a> */ 
  kk_std_core_types__cctx _x_x1390 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_filter(xs, kk_std_core_list_new_remove_fun1386(pred, _ctx), _x_x1390, _ctx);
}
 
// monadic lift

kk_std_core_types__tuple2 kk_std_core_list__mlift_partition_acc_10293(kk_std_core_types__cctx acc1, kk_std_core_types__cctx acc2, kk_function_t pred, kk_box_t x, kk_std_core_types__list xx, bool _y_x10178, kk_context_t* _ctx) { /* forall<a,e> (acc1 : ctx<list<a>>, acc2 : ctx<list<a>>, pred : (a) -> e bool, x : a, xx : list<a>, bool) -> e (list<a>, list<a>) */ 
  if (_y_x10178) {
    kk_std_core_types__list _cctx_x2651;
    kk_std_core_types__list _x_x1391 = kk_datatype_null(); /*list<2711>*/
    _cctx_x2651 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _x_x1391, _ctx); /*list<2711>*/
    kk_field_addr_t _cctx_x2652 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x2651, _ctx)->tail, _ctx); /*@field-addr<list<2711>>*/;
    kk_std_core_types__list _b_x416_426 = _cctx_x2651; /*list<2711>*/;
    kk_field_addr_t _b_x417_427 = _cctx_x2652; /*@field-addr<list<2711>>*/;
    kk_std_core_types__cctx _own_x1095;
    kk_std_core_types__cctx _x_x1392 = kk_cctx_create((kk_std_core_types__list_box(_b_x416_426, _ctx)),_b_x417_427,kk_context()); /*cctx<0,1>*/
    _own_x1095 = kk_cctx_compose(acc1,_x_x1392,kk_context()); /*cctx<394,396>*/
    kk_std_core_types__tuple2 _brw_x1096 = kk_std_core_list_partition_acc(xx, pred, _own_x1095, acc2, _ctx); /*(list<2711>, list<2711>)*/;
    kk_function_drop(pred, _ctx);
    return _brw_x1096;
  }
  {
    kk_std_core_types__list _cctx_x2698;
    kk_std_core_types__list _x_x1393 = kk_datatype_null(); /*list<2711>*/
    _cctx_x2698 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _x_x1393, _ctx); /*list<2711>*/
    kk_field_addr_t _cctx_x2699 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x2698, _ctx)->tail, _ctx); /*@field-addr<list<2711>>*/;
    kk_std_core_types__list _b_x424_428 = _cctx_x2698; /*list<2711>*/;
    kk_field_addr_t _b_x425_429 = _cctx_x2699; /*@field-addr<list<2711>>*/;
    kk_std_core_types__cctx _own_x1093;
    kk_std_core_types__cctx _x_x1394 = kk_cctx_create((kk_std_core_types__list_box(_b_x424_428, _ctx)),_b_x425_429,kk_context()); /*cctx<0,1>*/
    _own_x1093 = kk_cctx_compose(acc2,_x_x1394,kk_context()); /*cctx<394,396>*/
    kk_std_core_types__tuple2 _brw_x1094 = kk_std_core_list_partition_acc(xx, pred, acc1, _own_x1093, _ctx); /*(list<2711>, list<2711>)*/;
    kk_function_drop(pred, _ctx);
    return _brw_x1094;
  }
}


// lift anonymous function
struct kk_std_core_list_partition_acc_fun1402__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx acc1_0;
  kk_std_core_types__cctx acc2_0;
  kk_function_t pred_0;
  kk_box_t x_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_partition_acc_fun1402(kk_function_t _fself, kk_box_t _b_x437, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_partition_acc_fun1402(kk_std_core_types__cctx acc1_0, kk_std_core_types__cctx acc2_0, kk_function_t pred_0, kk_box_t x_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_partition_acc_fun1402__t* _self = kk_function_alloc_as(struct kk_std_core_list_partition_acc_fun1402__t, 8, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_partition_acc_fun1402, kk_context());
  _self->acc1_0 = acc1_0;
  _self->acc2_0 = acc2_0;
  _self->pred_0 = pred_0;
  _self->x_0 = x_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_partition_acc_fun1402(kk_function_t _fself, kk_box_t _b_x437, kk_context_t* _ctx) {
  struct kk_std_core_list_partition_acc_fun1402__t* _self = kk_function_as(struct kk_std_core_list_partition_acc_fun1402__t*, _fself, _ctx);
  kk_std_core_types__cctx acc1_0 = _self->acc1_0; /* ctx<list<2711>> */
  kk_std_core_types__cctx acc2_0 = _self->acc2_0; /* ctx<list<2711>> */
  kk_function_t pred_0 = _self->pred_0; /* (2711) -> 2712 bool */
  kk_box_t x_0 = _self->x_0; /* 2711 */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<2711> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(acc1_0, _ctx);kk_std_core_types__cctx_dup(acc2_0, _ctx);kk_function_dup(pred_0, _ctx);kk_box_dup(x_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10178_0_465 = kk_bool_unbox(_b_x437); /*bool*/;
  kk_std_core_types__tuple2 _x_x1403 = kk_std_core_list__mlift_partition_acc_10293(acc1_0, acc2_0, pred_0, x_0, xx_0, _y_x10178_0_465, _ctx); /*(list<2711>, list<2711>)*/
  return kk_std_core_types__tuple2_box(_x_x1403, _ctx);
}

kk_std_core_types__tuple2 kk_std_core_list_partition_acc(kk_std_core_types__list xs, kk_function_t pred_0, kk_std_core_types__cctx acc1_0, kk_std_core_types__cctx acc2_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, pred : (a) -> e bool, acc1 : ctx<list<a>>, acc2 : ctx<list<a>>) -> e (list<a>, list<a>) */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    kk_std_core_types__list _b_x434_454;
    kk_box_t _x_x1395 = kk_cctx_apply(acc1_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    _b_x434_454 = kk_std_core_types__list_unbox(_x_x1395, KK_OWNED, _ctx); /*list<2711>*/
    kk_std_core_types__list _b_x435_455;
    kk_box_t _x_x1396 = kk_cctx_apply(acc2_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    _b_x435_455 = kk_std_core_types__list_unbox(_x_x1396, KK_OWNED, _ctx); /*list<2711>*/
    return kk_std_core_types__new_Tuple2(kk_std_core_types__list_box(_b_x434_454, _ctx), kk_std_core_types__list_box(_b_x435_455, _ctx), _ctx);
  }
  {
    struct kk_std_core_types_Cons* _con_x1397 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x_0 = _con_x1397->head;
    kk_std_core_types__list xx_0 = _con_x1397->tail;
    kk_reuse_t _ru_x1151 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1151 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x_0, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool x_1_10378;
    kk_function_t _x_x1399 = kk_function_dup(pred_0, _ctx); /*(2711) -> 2712 bool*/
    kk_box_t _x_x1398 = kk_box_dup(x_0, _ctx); /*2711*/
    x_1_10378 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1399, (_x_x1399, _x_x1398, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1151,kk_context());
      kk_box_t _x_x1400;
      kk_function_t _x_x1401;
      kk_function_dup(pred_0, _ctx);
      _x_x1401 = kk_std_core_list_new_partition_acc_fun1402(acc1_0, acc2_0, pred_0, x_0, xx_0, _ctx); /*(2418) -> 2420 2419*/
      _x_x1400 = kk_std_core_hnd_yield_extend(_x_x1401, _ctx); /*2419*/
      return kk_std_core_types__tuple2_unbox(_x_x1400, KK_OWNED, _ctx);
    }
    if (x_1_10378) {
      kk_std_core_types__list _cctx_x2651_0;
      kk_std_core_types__list _x_x1404 = kk_datatype_null(); /*list<2711>*/
      _cctx_x2651_0 = kk_std_core_types__new_Cons(_ru_x1151, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0, _x_x1404, _ctx); /*list<2711>*/
      kk_field_addr_t _cctx_x2652_0 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x2651_0, _ctx)->tail, _ctx); /*@field-addr<list<2711>>*/;
      kk_std_core_types__list _b_x444_461 = _cctx_x2651_0; /*list<2711>*/;
      kk_field_addr_t _b_x445_462 = _cctx_x2652_0; /*@field-addr<list<2711>>*/;
      kk_std_core_types__cctx _own_x1092;
      kk_std_core_types__cctx _x_x1405 = kk_cctx_create((kk_std_core_types__list_box(_b_x444_461, _ctx)),_b_x445_462,kk_context()); /*cctx<0,1>*/
      _own_x1092 = kk_cctx_compose(acc1_0,_x_x1405,kk_context()); /*cctx<394,396>*/
      { // tailcall
        xs = xx_0;
        acc1_0 = _own_x1092;
        goto kk__tailcall;
      }
    }
    {
      kk_std_core_types__list _cctx_x2698_0;
      kk_std_core_types__list _x_x1406 = kk_datatype_null(); /*list<2711>*/
      _cctx_x2698_0 = kk_std_core_types__new_Cons(_ru_x1151, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0, _x_x1406, _ctx); /*list<2711>*/
      kk_field_addr_t _cctx_x2699_0 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x2698_0, _ctx)->tail, _ctx); /*@field-addr<list<2711>>*/;
      kk_std_core_types__list _b_x452_463 = _cctx_x2698_0; /*list<2711>*/;
      kk_field_addr_t _b_x453_464 = _cctx_x2699_0; /*@field-addr<list<2711>>*/;
      kk_std_core_types__cctx _own_x1091;
      kk_std_core_types__cctx _x_x1407 = kk_cctx_create((kk_std_core_types__list_box(_b_x452_463, _ctx)),_b_x453_464,kk_context()); /*cctx<0,1>*/
      _own_x1091 = kk_cctx_compose(acc2_0,_x_x1407,kk_context()); /*cctx<394,396>*/
      { // tailcall
        xs = xx_0;
        acc2_0 = _own_x1091;
        goto kk__tailcall;
      }
    }
  }
}
 
// Lookup the first element satisfying some predicate


// lift anonymous function
struct kk_std_core_list_lookup_fun1409__t {
  struct kk_function_s _base;
  kk_function_t pred;
};
static kk_std_core_types__maybe kk_std_core_list_lookup_fun1409(kk_function_t _fself, kk_box_t _b_x470, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_lookup_fun1409(kk_function_t pred, kk_context_t* _ctx) {
  struct kk_std_core_list_lookup_fun1409__t* _self = kk_function_alloc_as(struct kk_std_core_list_lookup_fun1409__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_lookup_fun1409, kk_context());
  _self->pred = pred;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_list_lookup_fun1412__t {
  struct kk_function_s _base;
  kk_box_t _b_x470;
};
static kk_std_core_types__maybe kk_std_core_list_lookup_fun1412(kk_function_t _fself, bool _y_x10184, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_lookup_fun1412(kk_box_t _b_x470, kk_context_t* _ctx) {
  struct kk_std_core_list_lookup_fun1412__t* _self = kk_function_alloc_as(struct kk_std_core_list_lookup_fun1412__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_lookup_fun1412, kk_context());
  _self->_b_x470 = _b_x470;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_std_core_types__maybe kk_std_core_list_lookup_fun1412(kk_function_t _fself, bool _y_x10184, kk_context_t* _ctx) {
  struct kk_std_core_list_lookup_fun1412__t* _self = kk_function_as(struct kk_std_core_list_lookup_fun1412__t*, _fself, _ctx);
  kk_box_t _b_x470 = _self->_b_x470; /* 1650 */
  kk_drop_match(_self, {kk_box_dup(_b_x470, _ctx);}, {}, _ctx)
  if (_y_x10184) {
    kk_box_t _x_x1413;
    kk_std_core_types__tuple2 _match_x1086 = kk_std_core_types__tuple2_unbox(_b_x470, KK_OWNED, _ctx); /*(2894, 2895)*/;
    {
      kk_box_t _x_0 = _match_x1086.snd;
      kk_box_dup(_x_0, _ctx);
      kk_std_core_types__tuple2_drop(_match_x1086, _ctx);
      _x_x1413 = _x_0; /*2895*/
    }
    return kk_std_core_types__new_Just(_x_x1413, _ctx);
  }
  {
    kk_box_drop(_b_x470, _ctx);
    return kk_std_core_types__new_Nothing(_ctx);
  }
}


// lift anonymous function
struct kk_std_core_list_lookup_fun1415__t {
  struct kk_function_s _base;
  kk_function_t next_10382;
};
static kk_box_t kk_std_core_list_lookup_fun1415(kk_function_t _fself, kk_box_t _b_x467, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_lookup_fun1415(kk_function_t next_10382, kk_context_t* _ctx) {
  struct kk_std_core_list_lookup_fun1415__t* _self = kk_function_alloc_as(struct kk_std_core_list_lookup_fun1415__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_lookup_fun1415, kk_context());
  _self->next_10382 = next_10382;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_lookup_fun1415(kk_function_t _fself, kk_box_t _b_x467, kk_context_t* _ctx) {
  struct kk_std_core_list_lookup_fun1415__t* _self = kk_function_as(struct kk_std_core_list_lookup_fun1415__t*, _fself, _ctx);
  kk_function_t next_10382 = _self->next_10382; /* (bool) -> 2896 maybe<2895> */
  kk_drop_match(_self, {kk_function_dup(next_10382, _ctx);}, {}, _ctx)
  kk_std_core_types__maybe _x_x1416;
  bool _x_x1417 = kk_bool_unbox(_b_x467); /*bool*/
  _x_x1416 = kk_function_call(kk_std_core_types__maybe, (kk_function_t, bool, kk_context_t*), next_10382, (next_10382, _x_x1417, _ctx), _ctx); /*maybe<2895>*/
  return kk_std_core_types__maybe_box(_x_x1416, _ctx);
}
static kk_std_core_types__maybe kk_std_core_list_lookup_fun1409(kk_function_t _fself, kk_box_t _b_x470, kk_context_t* _ctx) {
  struct kk_std_core_list_lookup_fun1409__t* _self = kk_function_as(struct kk_std_core_list_lookup_fun1409__t*, _fself, _ctx);
  kk_function_t pred = _self->pred; /* (2894) -> 2896 bool */
  kk_drop_match(_self, {kk_function_dup(pred, _ctx);}, {}, _ctx)
  bool x_10381;
  kk_box_t _x_x1410;
  kk_std_core_types__tuple2 _match_x1087;
  kk_box_t _x_x1411 = kk_box_dup(_b_x470, _ctx); /*1650*/
  _match_x1087 = kk_std_core_types__tuple2_unbox(_x_x1411, KK_OWNED, _ctx); /*(2894, 2895)*/
  {
    kk_box_t _x = _match_x1087.fst;
    kk_box_dup(_x, _ctx);
    kk_std_core_types__tuple2_drop(_match_x1087, _ctx);
    _x_x1410 = _x; /*2894*/
  }
  x_10381 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), pred, (pred, _x_x1410, _ctx), _ctx); /*bool*/
  kk_function_t next_10382 = kk_std_core_list_new_lookup_fun1412(_b_x470, _ctx); /*(bool) -> 2896 maybe<2895>*/;
  if (kk_yielding(kk_context())) {
    kk_box_t _x_x1414 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_lookup_fun1415(next_10382, _ctx), _ctx); /*2419*/
    return kk_std_core_types__maybe_unbox(_x_x1414, KK_OWNED, _ctx);
  }
  {
    return kk_function_call(kk_std_core_types__maybe, (kk_function_t, bool, kk_context_t*), next_10382, (next_10382, x_10381, _ctx), _ctx);
  }
}

kk_std_core_types__maybe kk_std_core_list_lookup(kk_std_core_types__list xs, kk_function_t pred, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<(a, b)>, pred : (a) -> e bool) -> e maybe<b> */ 
  return kk_std_core_list_foreach_while(xs, kk_std_core_list_new_lookup_fun1409(pred, _ctx), _ctx);
}
 
// monadic lift

kk_integer_t kk_std_core_list__mlift_index_of_acc_10295(kk_integer_t idx, kk_function_t pred, kk_std_core_types__list xx, bool _y_x10187, kk_context_t* _ctx) { /* forall<a,e> (idx : int, pred : (a) -> e bool, xx : list<a>, bool) -> e int */ 
  if (_y_x10187) {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(pred, _ctx);
    return idx;
  }
  {
    kk_integer_t _x_x1418 = kk_integer_add_small_const(idx, 1, _ctx); /*int*/
    return kk_std_core_list_index_of_acc(xx, pred, _x_x1418, _ctx);
  }
}


// lift anonymous function
struct kk_std_core_list_index_of_acc_fun1422__t {
  struct kk_function_s _base;
  kk_integer_t idx_0;
  kk_function_t pred_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_index_of_acc_fun1422(kk_function_t _fself, kk_box_t _b_x476, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_index_of_acc_fun1422(kk_integer_t idx_0, kk_function_t pred_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_index_of_acc_fun1422__t* _self = kk_function_alloc_as(struct kk_std_core_list_index_of_acc_fun1422__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_index_of_acc_fun1422, kk_context());
  _self->idx_0 = idx_0;
  _self->pred_0 = pred_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_index_of_acc_fun1422(kk_function_t _fself, kk_box_t _b_x476, kk_context_t* _ctx) {
  struct kk_std_core_list_index_of_acc_fun1422__t* _self = kk_function_as(struct kk_std_core_list_index_of_acc_fun1422__t*, _fself, _ctx);
  kk_integer_t idx_0 = _self->idx_0; /* int */
  kk_function_t pred_0 = _self->pred_0; /* (2951) -> 2952 bool */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<2951> */
  kk_drop_match(_self, {kk_integer_dup(idx_0, _ctx);kk_function_dup(pred_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10187_0_478 = kk_bool_unbox(_b_x476); /*bool*/;
  kk_integer_t _x_x1423 = kk_std_core_list__mlift_index_of_acc_10295(idx_0, pred_0, xx_0, _y_x10187_0_478, _ctx); /*int*/
  return kk_integer_box(_x_x1423, _ctx);
}

kk_integer_t kk_std_core_list_index_of_acc(kk_std_core_types__list xs, kk_function_t pred_0, kk_integer_t idx_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, pred : (a) -> e bool, idx : int) -> e int */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1419 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1419->head;
    kk_std_core_types__list xx_0 = _con_x1419->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool x_0_10385;
    kk_function_t _x_x1420 = kk_function_dup(pred_0, _ctx); /*(2951) -> 2952 bool*/
    x_0_10385 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1420, (_x_x1420, x, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x1421 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_index_of_acc_fun1422(idx_0, pred_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_integer_unbox(_x_x1421, _ctx);
    }
    if (x_0_10385) {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_function_drop(pred_0, _ctx);
      return idx_0;
    }
    { // tailcall
      kk_integer_t _x_x1424 = kk_integer_add_small_const(idx_0, 1, _ctx); /*int*/
      xs = xx_0;
      idx_0 = _x_x1424;
      goto kk__tailcall;
    }
  }
  {
    kk_function_drop(pred_0, _ctx);
    kk_integer_drop(idx_0, _ctx);
    return kk_integer_from_small(-1);
  }
}
 
// monadic lift

kk_unit_t kk_std_core_list__mlift_foreach_10296(kk_function_t action, kk_std_core_types__list xx, kk_unit_t wild__, kk_context_t* _ctx) { /* forall<a,e> (action : (a) -> e (), xx : list<a>, wild_ : ()) -> e () */ 
  kk_std_core_list_foreach(xx, action, _ctx); return kk_Unit;
}
 
// Invoke `action` for each element of a list


// lift anonymous function
struct kk_std_core_list_foreach_fun1428__t {
  struct kk_function_s _base;
  kk_function_t action_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_foreach_fun1428(kk_function_t _fself, kk_box_t _b_x480, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foreach_fun1428(kk_function_t action_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_fun1428__t* _self = kk_function_alloc_as(struct kk_std_core_list_foreach_fun1428__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_foreach_fun1428, kk_context());
  _self->action_0 = action_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_foreach_fun1428(kk_function_t _fself, kk_box_t _b_x480, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_fun1428__t* _self = kk_function_as(struct kk_std_core_list_foreach_fun1428__t*, _fself, _ctx);
  kk_function_t action_0 = _self->action_0; /* (3031) -> 3032 () */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<3031> */
  kk_drop_match(_self, {kk_function_dup(action_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  kk_unit_t wild___0_482 = kk_Unit;
  kk_unit_unbox(_b_x480);
  kk_unit_t _x_x1429 = kk_Unit;
  kk_std_core_list__mlift_foreach_10296(action_0, xx_0, wild___0_482, _ctx);
  return kk_unit_box(_x_x1429);
}

kk_unit_t kk_std_core_list_foreach(kk_std_core_types__list xs, kk_function_t action_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, action : (a) -> e ()) -> e () */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1425 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1425->head;
    kk_std_core_types__list xx_0 = _con_x1425->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_unit_t x_0_10388 = kk_Unit;
    kk_function_t _x_x1426 = kk_function_dup(action_0, _ctx); /*(3031) -> 3032 ()*/
    kk_function_call(kk_unit_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x1426, (_x_x1426, x, _ctx), _ctx);
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x1427 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_foreach_fun1428(action_0, xx_0, _ctx), _ctx); /*2419*/
      kk_unit_unbox(_x_x1427); return kk_Unit;
    }
    { // tailcall
      xs = xx_0;
      goto kk__tailcall;
    }
  }
  {
    kk_function_drop(action_0, _ctx);
    kk_Unit; return kk_Unit;
  }
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_map_while_10297(kk_std_core_types__cctx _acc, kk_function_t action, kk_std_core_types__list xx, kk_std_core_types__maybe _y_x10195, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, action : (a) -> e maybe<b>, xx : list<a>, maybe<b>) -> e list<b> */ 
  if (kk_std_core_types__is_Just(_y_x10195, _ctx)) {
    kk_box_t y = _y_x10195._cons.Just.value;
    kk_std_core_types__list _trmc_x10080 = kk_datatype_null(); /*list<3109>*/;
    kk_std_core_types__list _trmc_x10081 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _trmc_x10080, _ctx); /*list<3109>*/;
    kk_field_addr_t _b_x488_493 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10081, _ctx)->tail, _ctx); /*@field-addr<list<3109>>*/;
    kk_std_core_types__cctx _x_x1430 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10081, _ctx)),_b_x488_493,kk_context()); /*ctx<0>*/
    return kk_std_core_list__trmc_map_while(xx, action, _x_x1430, _ctx);
  }
  {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(action, _ctx);
    kk_box_t _x_x1431 = kk_cctx_apply(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1431, KK_OWNED, _ctx);
  }
}
 
// Invoke `action` on each element of a list while `action` returns `Just`


// lift anonymous function
struct kk_std_core_list__trmc_map_while_fun1436__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t action_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list__trmc_map_while_fun1436(kk_function_t _fself, kk_box_t _b_x502, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_map_while_fun1436(kk_std_core_types__cctx _acc_0, kk_function_t action_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_map_while_fun1436__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_map_while_fun1436__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_map_while_fun1436, kk_context());
  _self->_acc_0 = _acc_0;
  _self->action_0 = action_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_map_while_fun1436(kk_function_t _fself, kk_box_t _b_x502, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_map_while_fun1436__t* _self = kk_function_as(struct kk_std_core_list__trmc_map_while_fun1436__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<3109>> */
  kk_function_t action_0 = _self->action_0; /* (3108) -> 3110 maybe<3109> */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<3108> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(action_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  kk_std_core_types__maybe _y_x10195_0_522 = kk_std_core_types__maybe_unbox(_b_x502, KK_OWNED, _ctx); /*maybe<3109>*/;
  kk_std_core_types__list _x_x1437 = kk_std_core_list__mlift_trmc_map_while_10297(_acc_0, action_0, xx_0, _y_x10195_0_522, _ctx); /*list<3109>*/
  return kk_std_core_types__list_box(_x_x1437, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_map_while(kk_std_core_types__list xs, kk_function_t action_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, action : (a) -> e maybe<b>, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    kk_function_drop(action_0, _ctx);
    kk_box_t _x_x1432 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1432, KK_OWNED, _ctx);
  }
  {
    struct kk_std_core_types_Cons* _con_x1433 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1433->head;
    kk_std_core_types__list xx_0 = _con_x1433->tail;
    kk_reuse_t _ru_x1154 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1154 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__maybe x_0_10391;
    kk_function_t _x_x1434 = kk_function_dup(action_0, _ctx); /*(3108) -> 3110 maybe<3109>*/
    x_0_10391 = kk_function_call(kk_std_core_types__maybe, (kk_function_t, kk_box_t, kk_context_t*), _x_x1434, (_x_x1434, x, _ctx), _ctx); /*maybe<3109>*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1154,kk_context());
      kk_std_core_types__maybe_drop(x_0_10391, _ctx);
      kk_box_t _x_x1435 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_map_while_fun1436(_acc_0, action_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1435, KK_OWNED, _ctx);
    }
    if (kk_std_core_types__is_Just(x_0_10391, _ctx)) {
      kk_box_t y_0 = x_0_10391._cons.Just.value;
      kk_std_core_types__list _trmc_x10080_0 = kk_datatype_null(); /*list<3109>*/;
      kk_std_core_types__list _trmc_x10081_0 = kk_std_core_types__new_Cons(_ru_x1154, kk_field_index_of(struct kk_std_core_types_Cons, tail), y_0, _trmc_x10080_0, _ctx); /*list<3109>*/;
      kk_field_addr_t _b_x508_516 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10081_0, _ctx)->tail, _ctx); /*@field-addr<list<3109>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1438 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10081_0, _ctx)),_b_x508_516,kk_context()); /*ctx<0>*/
        xs = xx_0;
        _acc_0 = _x_x1438;
        goto kk__tailcall;
      }
    }
    {
      kk_reuse_drop(_ru_x1154,kk_context());
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_function_drop(action_0, _ctx);
      kk_box_t _x_x1439 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
      return kk_std_core_types__list_unbox(_x_x1439, KK_OWNED, _ctx);
    }
  }
}
 
// Invoke `action` on each element of a list while `action` returns `Just`

kk_std_core_types__list kk_std_core_list_map_while(kk_std_core_types__list xs_0, kk_function_t action_1, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, action : (a) -> e maybe<b>) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1440 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_map_while(xs_0, action_1, _x_x1440, _ctx);
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_list__mlift_foreach_indexed_10299_fun1443__t {
  struct kk_function_s _base;
  kk_ref_t i;
};
static kk_unit_t kk_std_core_list__mlift_foreach_indexed_10299_fun1443(kk_function_t _fself, kk_integer_t _y_x10203, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_mlift_foreach_indexed_10299_fun1443(kk_ref_t i, kk_context_t* _ctx) {
  struct kk_std_core_list__mlift_foreach_indexed_10299_fun1443__t* _self = kk_function_alloc_as(struct kk_std_core_list__mlift_foreach_indexed_10299_fun1443__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__mlift_foreach_indexed_10299_fun1443, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_unit_t kk_std_core_list__mlift_foreach_indexed_10299_fun1443(kk_function_t _fself, kk_integer_t _y_x10203, kk_context_t* _ctx) {
  struct kk_std_core_list__mlift_foreach_indexed_10299_fun1443__t* _self = kk_function_as(struct kk_std_core_list__mlift_foreach_indexed_10299_fun1443__t*, _fself, _ctx);
  kk_ref_t i = _self->i; /* local-var<3237,int> */
  kk_drop_match(_self, {kk_ref_dup(i, _ctx);}, {}, _ctx)
  kk_integer_t _b_x532_534 = kk_integer_add_small_const(_y_x10203, 1, _ctx); /*int*/;
  kk_unit_t _brw_x1080 = kk_Unit;
  kk_ref_set_borrow(i,(kk_integer_box(_b_x532_534, _ctx)),kk_context());
  kk_ref_drop(i, _ctx);
  _brw_x1080; return kk_Unit;
}


// lift anonymous function
struct kk_std_core_list__mlift_foreach_indexed_10299_fun1445__t {
  struct kk_function_s _base;
  kk_function_t next_10395;
};
static kk_box_t kk_std_core_list__mlift_foreach_indexed_10299_fun1445(kk_function_t _fself, kk_box_t _b_x536, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_mlift_foreach_indexed_10299_fun1445(kk_function_t next_10395, kk_context_t* _ctx) {
  struct kk_std_core_list__mlift_foreach_indexed_10299_fun1445__t* _self = kk_function_alloc_as(struct kk_std_core_list__mlift_foreach_indexed_10299_fun1445__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__mlift_foreach_indexed_10299_fun1445, kk_context());
  _self->next_10395 = next_10395;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__mlift_foreach_indexed_10299_fun1445(kk_function_t _fself, kk_box_t _b_x536, kk_context_t* _ctx) {
  struct kk_std_core_list__mlift_foreach_indexed_10299_fun1445__t* _self = kk_function_as(struct kk_std_core_list__mlift_foreach_indexed_10299_fun1445__t*, _fself, _ctx);
  kk_function_t next_10395 = _self->next_10395; /* (int) -> <local<3237>|3248> () */
  kk_drop_match(_self, {kk_function_dup(next_10395, _ctx);}, {}, _ctx)
  kk_unit_t _x_x1446 = kk_Unit;
  kk_integer_t _x_x1447 = kk_integer_unbox(_b_x536, _ctx); /*int*/
  kk_function_call(kk_unit_t, (kk_function_t, kk_integer_t, kk_context_t*), next_10395, (next_10395, _x_x1447, _ctx), _ctx);
  return kk_unit_box(_x_x1446);
}

kk_unit_t kk_std_core_list__mlift_foreach_indexed_10299(kk_ref_t i, kk_unit_t wild__, kk_context_t* _ctx) { /* forall<h,e> (i : local-var<h,int>, wild_ : ()) -> <local<h>|e> () */ 
  kk_integer_t x_10394;
  kk_box_t _x_x1441;
  kk_ref_t _x_x1442 = kk_ref_dup(i, _ctx); /*local-var<3237,int>*/
  _x_x1441 = kk_ref_get(_x_x1442,kk_context()); /*298*/
  x_10394 = kk_integer_unbox(_x_x1441, _ctx); /*int*/
  kk_function_t next_10395 = kk_std_core_list__new_mlift_foreach_indexed_10299_fun1443(i, _ctx); /*(int) -> <local<3237>|3248> ()*/;
  if (kk_yielding(kk_context())) {
    kk_integer_drop(x_10394, _ctx);
    kk_box_t _x_x1444 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_mlift_foreach_indexed_10299_fun1445(next_10395, _ctx), _ctx); /*2419*/
    kk_unit_unbox(_x_x1444); return kk_Unit;
  }
  {
    kk_function_call(kk_unit_t, (kk_function_t, kk_integer_t, kk_context_t*), next_10395, (next_10395, x_10394, _ctx), _ctx); return kk_Unit;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_list__mlift_foreach_indexed_10300_fun1449__t {
  struct kk_function_s _base;
  kk_ref_t i;
};
static kk_box_t kk_std_core_list__mlift_foreach_indexed_10300_fun1449(kk_function_t _fself, kk_box_t _b_x539, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_mlift_foreach_indexed_10300_fun1449(kk_ref_t i, kk_context_t* _ctx) {
  struct kk_std_core_list__mlift_foreach_indexed_10300_fun1449__t* _self = kk_function_alloc_as(struct kk_std_core_list__mlift_foreach_indexed_10300_fun1449__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__mlift_foreach_indexed_10300_fun1449, kk_context());
  _self->i = i;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__mlift_foreach_indexed_10300_fun1449(kk_function_t _fself, kk_box_t _b_x539, kk_context_t* _ctx) {
  struct kk_std_core_list__mlift_foreach_indexed_10300_fun1449__t* _self = kk_function_as(struct kk_std_core_list__mlift_foreach_indexed_10300_fun1449__t*, _fself, _ctx);
  kk_ref_t i = _self->i; /* local-var<3237,int> */
  kk_drop_match(_self, {kk_ref_dup(i, _ctx);}, {}, _ctx)
  kk_unit_t wild___541 = kk_Unit;
  kk_unit_unbox(_b_x539);
  kk_unit_t _x_x1450 = kk_Unit;
  kk_std_core_list__mlift_foreach_indexed_10299(i, wild___541, _ctx);
  return kk_unit_box(_x_x1450);
}

kk_unit_t kk_std_core_list__mlift_foreach_indexed_10300(kk_function_t action, kk_ref_t i, kk_box_t x, kk_integer_t j, kk_context_t* _ctx) { /* forall<h,a,e> (action : (int, a) -> e (), i : local-var<h,int>, x : a, j : int) -> <local<h>|e> () */ 
  kk_unit_t x_0_10398 = kk_Unit;
  kk_function_call(kk_unit_t, (kk_function_t, kk_integer_t, kk_box_t, kk_context_t*), action, (action, j, x, _ctx), _ctx);
  if (kk_yielding(kk_context())) {
    kk_box_t _x_x1448 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_mlift_foreach_indexed_10300_fun1449(i, _ctx), _ctx); /*2419*/
    kk_unit_unbox(_x_x1448); return kk_Unit;
  }
  {
    kk_std_core_list__mlift_foreach_indexed_10299(i, x_0_10398, _ctx); return kk_Unit;
  }
}
 
// Invoke `action` for each element of a list, passing also the position of the element.


// lift anonymous function
struct kk_std_core_list_foreach_indexed_fun1452__t {
  struct kk_function_s _base;
  kk_function_t action;
  kk_ref_t loc;
};
static kk_unit_t kk_std_core_list_foreach_indexed_fun1452(kk_function_t _fself, kk_box_t x, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foreach_indexed_fun1452(kk_function_t action, kk_ref_t loc, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_indexed_fun1452__t* _self = kk_function_alloc_as(struct kk_std_core_list_foreach_indexed_fun1452__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_foreach_indexed_fun1452, kk_context());
  _self->action = action;
  _self->loc = loc;
  return kk_datatype_from_base(&_self->_base, kk_context());
}



// lift anonymous function
struct kk_std_core_list_foreach_indexed_fun1456__t {
  struct kk_function_s _base;
  kk_function_t action;
  kk_ref_t loc;
  kk_box_t x;
};
static kk_box_t kk_std_core_list_foreach_indexed_fun1456(kk_function_t _fself, kk_box_t _b_x549, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_foreach_indexed_fun1456(kk_function_t action, kk_ref_t loc, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_indexed_fun1456__t* _self = kk_function_alloc_as(struct kk_std_core_list_foreach_indexed_fun1456__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_foreach_indexed_fun1456, kk_context());
  _self->action = action;
  _self->loc = loc;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_foreach_indexed_fun1456(kk_function_t _fself, kk_box_t _b_x549, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_indexed_fun1456__t* _self = kk_function_as(struct kk_std_core_list_foreach_indexed_fun1456__t*, _fself, _ctx);
  kk_function_t action = _self->action; /* (int, 3247) -> 3248 () */
  kk_ref_t loc = _self->loc; /* local-var<3237,int> */
  kk_box_t x = _self->x; /* 3247 */
  kk_drop_match(_self, {kk_function_dup(action, _ctx);kk_ref_dup(loc, _ctx);kk_box_dup(x, _ctx);}, {}, _ctx)
  kk_unit_t _x_x1457 = kk_Unit;
  kk_integer_t _x_x1458 = kk_integer_unbox(_b_x549, _ctx); /*int*/
  kk_std_core_list__mlift_foreach_indexed_10300(action, loc, x, _x_x1458, _ctx);
  return kk_unit_box(_x_x1457);
}
static kk_unit_t kk_std_core_list_foreach_indexed_fun1452(kk_function_t _fself, kk_box_t x, kk_context_t* _ctx) {
  struct kk_std_core_list_foreach_indexed_fun1452__t* _self = kk_function_as(struct kk_std_core_list_foreach_indexed_fun1452__t*, _fself, _ctx);
  kk_function_t action = _self->action; /* (int, 3247) -> 3248 () */
  kk_ref_t loc = _self->loc; /* local-var<3237,int> */
  kk_drop_match(_self, {kk_function_dup(action, _ctx);kk_ref_dup(loc, _ctx);}, {}, _ctx)
  kk_integer_t x_0_10403;
  kk_box_t _x_x1453;
  kk_ref_t _x_x1454 = kk_ref_dup(loc, _ctx); /*local-var<3237,int>*/
  _x_x1453 = kk_ref_get(_x_x1454,kk_context()); /*298*/
  x_0_10403 = kk_integer_unbox(_x_x1453, _ctx); /*int*/
  if (kk_yielding(kk_context())) {
    kk_integer_drop(x_0_10403, _ctx);
    kk_box_t _x_x1455 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_foreach_indexed_fun1456(action, loc, x, _ctx), _ctx); /*2419*/
    kk_unit_unbox(_x_x1455); return kk_Unit;
  }
  {
    kk_std_core_list__mlift_foreach_indexed_10300(action, loc, x, x_0_10403, _ctx); return kk_Unit;
  }
}

kk_unit_t kk_std_core_list_foreach_indexed(kk_std_core_types__list xs, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, action : (int, a) -> e ()) -> e () */ 
  kk_ref_t loc = kk_ref_alloc((kk_integer_box(kk_integer_from_small(0), _ctx)),kk_context()); /*local-var<3237,int>*/;
  kk_unit_t res = kk_Unit;
  kk_function_t _x_x1451;
  kk_ref_dup(loc, _ctx);
  _x_x1451 = kk_std_core_list_new_foreach_indexed_fun1452(action, loc, _ctx); /*(x : 3247) -> <local<3237>|3248> ()*/
  kk_std_core_list_foreach(xs, _x_x1451, _ctx);
  kk_box_t _x_x1459 = kk_std_core_hnd_prompt_local_var(loc, kk_unit_box(res), _ctx); /*4162*/
  kk_unit_unbox(_x_x1459); return kk_Unit;
}
 
// lifted local: intersperse, before

kk_std_core_types__list kk_std_core_list__trmc_lift_intersperse_5734(kk_box_t sep, kk_std_core_types__list ys, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (sep : a, ys : list<a>, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1460 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t y = _con_x1460->head;
    kk_std_core_types__list yy = _con_x1460->tail;
    kk_reuse_t _ru_x1155 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1155 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(y, _ctx);
      kk_std_core_types__list_dup(yy, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_std_core_types__list _trmc_x10082;
    kk_std_core_types__list _x_x1461 = kk_datatype_null(); /*list<3324>*/
    _trmc_x10082 = kk_std_core_types__new_Cons(_ru_x1155, 0, y, _x_x1461, _ctx); /*list<3324>*/
    kk_field_addr_t _b_x561_566 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10082, _ctx)->tail, _ctx); /*@field-addr<list<3324>>*/;
    { // tailcall
      kk_box_t _x_x1462 = kk_box_dup(sep, _ctx); /*3324*/
      kk_std_core_types__cctx _x_x1463;
      kk_box_t _x_x1464;
      kk_std_core_types__list _x_x1465 = kk_std_core_types__new_Cons(kk_reuse_null, 0, sep, _trmc_x10082, _ctx); /*list<79>*/
      _x_x1464 = kk_std_core_types__list_box(_x_x1465, _ctx); /*0*/
      _x_x1463 = kk_cctx_extend_linear(_acc,_x_x1464,_b_x561_566,kk_context()); /*ctx<0>*/
      sep = _x_x1462;
      ys = yy;
      _acc = _x_x1463;
      goto kk__tailcall;
    }
  }
  {
    kk_box_drop(sep, _ctx);
    kk_box_t _x_x1466 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1466, KK_OWNED, _ctx);
  }
}
 
// lifted local: intersperse, before

kk_std_core_types__list kk_std_core_list__lift_intersperse_5734(kk_box_t sep_0, kk_std_core_types__list ys_0, kk_context_t* _ctx) { /* forall<a> (sep : a, ys : list<a>) -> list<a> */ 
  kk_std_core_types__cctx _x_x1467 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_intersperse_5734(sep_0, ys_0, _x_x1467, _ctx);
}
 
// Insert a separator `sep`  between all elements of a list `xs` .

kk_std_core_types__list kk_std_core_list_intersperse(kk_std_core_types__list xs, kk_box_t sep, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, sep : a) -> list<a> */ 
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1468 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1468->head;
    kk_std_core_types__list xx = _con_x1468->tail;
    kk_reuse_t _ru_x1156 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1156 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__list _x_x1469;
    kk_std_core_types__cctx _x_x1470 = kk_cctx_empty(kk_context()); /*ctx<0>*/
    _x_x1469 = kk_std_core_list__trmc_lift_intersperse_5734(sep, xx, _x_x1470, _ctx); /*list<3324>*/
    return kk_std_core_types__new_Cons(_ru_x1156, 0, x, _x_x1469, _ctx);
  }
  {
    kk_box_drop(sep, _ctx);
    return kk_std_core_types__new_Nil(_ctx);
  }
}
 
// Concatenate all strings in a list

kk_string_t kk_std_core_list_joinsep(kk_std_core_types__list xs, kk_string_t sep, kk_context_t* _ctx) { /* (xs : list<string>, sep : string) -> string */ 
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    kk_string_drop(sep, _ctx);
    return kk_string_empty();
  }
  {
    struct kk_std_core_types_Cons* _con_x1472 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x572 = _con_x1472->head;
    kk_std_core_types__list _pat_1 = _con_x1472->tail;
    if (kk_std_core_types__is_Nil(_pat_1, _ctx)) {
      kk_string_t x = kk_string_unbox(_box_x572);
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        kk_datatype_ptr_free(xs, _ctx);
      }
      else {
        kk_string_dup(x, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      kk_string_drop(sep, _ctx);
      return x;
    }
  }
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1473 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x573 = _con_x1473->head;
    kk_std_core_types__list _pat_3 = _con_x1473->tail;
    if (kk_std_core_types__is_Cons(_pat_3, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1474 = kk_std_core_types__as_Cons(_pat_3, _ctx);
      kk_box_t _box_x574 = _con_x1474->head;
      kk_std_core_types__list _pat_4 = _con_x1474->tail;
      if (kk_std_core_types__is_Nil(_pat_4, _ctx)) {
        kk_string_t _x_x1475 = kk_string_dup(sep, _ctx); /*string*/
        kk_string_t _x_x1476 = kk_string_empty(); /*string*/
        if (kk_string_is_eq(_x_x1475,_x_x1476,kk_context())) {
          kk_string_t x_0 = kk_string_unbox(_box_x573);
          kk_string_t y = kk_string_unbox(_box_x574);
          if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
            if kk_likely(kk_datatype_ptr_is_unique(_pat_3, _ctx)) {
              kk_datatype_ptr_free(_pat_3, _ctx);
            }
            else {
              kk_string_dup(y, _ctx);
              kk_datatype_ptr_decref(_pat_3, _ctx);
            }
            kk_datatype_ptr_free(xs, _ctx);
          }
          else {
            kk_string_dup(x_0, _ctx);
            kk_string_dup(y, _ctx);
            kk_datatype_ptr_decref(xs, _ctx);
          }
          kk_string_drop(sep, _ctx);
          return kk_std_core_types__lp__plus__plus__rp_(x_0, y, _ctx);
        }
      }
    }
  }
  {
    kk_vector_t _x_x1478 = kk_std_core_vector_unvlist(xs, _ctx); /*vector<978>*/
    return kk_string_join_with(_x_x1478,sep,kk_context());
  }
}
 
// Concatenate all strings in a list

kk_string_t kk_std_core_list_concat_fs_join(kk_std_core_types__list xs, kk_context_t* _ctx) { /* (xs : list<string>) -> string */ 
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    return kk_string_empty();
  }
  {
    struct kk_std_core_types_Cons* _con_x1480 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x575 = _con_x1480->head;
    kk_std_core_types__list _pat_1 = _con_x1480->tail;
    if (kk_std_core_types__is_Nil(_pat_1, _ctx)) {
      kk_string_t x = kk_string_unbox(_box_x575);
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        kk_datatype_ptr_free(xs, _ctx);
      }
      else {
        kk_string_dup(x, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      return x;
    }
  }
  {
    struct kk_std_core_types_Cons* _con_x1481 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x576 = _con_x1481->head;
    kk_std_core_types__list _pat_3 = _con_x1481->tail;
    struct kk_std_core_types_Cons* _con_x1482 = kk_std_core_types__as_Cons(_pat_3, _ctx);
    kk_box_t _box_x577 = _con_x1482->head;
    kk_std_core_types__list _pat_4 = _con_x1482->tail;
    if (kk_std_core_types__is_Nil(_pat_4, _ctx)) {
      kk_string_t x_0 = kk_string_unbox(_box_x576);
      kk_string_t y = kk_string_unbox(_box_x577);
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        if kk_likely(kk_datatype_ptr_is_unique(_pat_3, _ctx)) {
          kk_datatype_ptr_free(_pat_3, _ctx);
        }
        else {
          kk_string_dup(y, _ctx);
          kk_datatype_ptr_decref(_pat_3, _ctx);
        }
        kk_datatype_ptr_free(xs, _ctx);
      }
      else {
        kk_string_dup(x_0, _ctx);
        kk_string_dup(y, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      return kk_std_core_types__lp__plus__plus__rp_(x_0, y, _ctx);
    }
  }
  {
    kk_vector_t _x_x1483 = kk_std_core_vector_unvlist(xs, _ctx); /*vector<978>*/
    return kk_string_join(_x_x1483,kk_context());
  }
}
 
// monadic lift

kk_string_t kk_std_core_list__mlift_show_10301(kk_std_core_types__list _y_x10208, kk_context_t* _ctx) { /* forall<e> (list<string>) -> e string */ 
  kk_string_t _x_x1484;
  kk_define_string_literal(, _s_x1485, 1, "[", _ctx)
  _x_x1484 = kk_string_dup(_s_x1485, _ctx); /*string*/
  kk_string_t _x_x1486;
  kk_string_t _x_x1487;
  if (kk_std_core_types__is_Nil(_y_x10208, _ctx)) {
    _x_x1487 = kk_string_empty(); /*string*/
    goto _match_x1488;
  }
  {
    struct kk_std_core_types_Cons* _con_x1490 = kk_std_core_types__as_Cons(_y_x10208, _ctx);
    kk_box_t _box_x578 = _con_x1490->head;
    kk_std_core_types__list _pat_1 = _con_x1490->tail;
    if (kk_std_core_types__is_Nil(_pat_1, _ctx)) {
      kk_string_t x = kk_string_unbox(_box_x578);
      if kk_likely(kk_datatype_ptr_is_unique(_y_x10208, _ctx)) {
        kk_datatype_ptr_free(_y_x10208, _ctx);
      }
      else {
        kk_string_dup(x, _ctx);
        kk_datatype_ptr_decref(_y_x10208, _ctx);
      }
      _x_x1487 = x; /*string*/
      goto _match_x1488;
    }
  }
  if (kk_std_core_types__is_Cons(_y_x10208, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1491 = kk_std_core_types__as_Cons(_y_x10208, _ctx);
    kk_box_t _box_x579 = _con_x1491->head;
    kk_std_core_types__list _pat_3 = _con_x1491->tail;
    if (kk_std_core_types__is_Cons(_pat_3, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1492 = kk_std_core_types__as_Cons(_pat_3, _ctx);
      kk_box_t _box_x580 = _con_x1492->head;
      kk_std_core_types__list _pat_4 = _con_x1492->tail;
      if (kk_std_core_types__is_Nil(_pat_4, _ctx)) {
        kk_string_t _x_x1493;
        kk_define_string_literal(, _s_x1494, 1, ",", _ctx)
        _x_x1493 = kk_string_dup(_s_x1494, _ctx); /*string*/
        kk_string_t _x_x1495 = kk_string_empty(); /*string*/
        if (kk_string_is_eq(_x_x1493,_x_x1495,kk_context())) {
          kk_string_t x_0 = kk_string_unbox(_box_x579);
          kk_string_t y = kk_string_unbox(_box_x580);
          if kk_likely(kk_datatype_ptr_is_unique(_y_x10208, _ctx)) {
            if kk_likely(kk_datatype_ptr_is_unique(_pat_3, _ctx)) {
              kk_datatype_ptr_free(_pat_3, _ctx);
            }
            else {
              kk_string_dup(y, _ctx);
              kk_datatype_ptr_decref(_pat_3, _ctx);
            }
            kk_datatype_ptr_free(_y_x10208, _ctx);
          }
          else {
            kk_string_dup(x_0, _ctx);
            kk_string_dup(y, _ctx);
            kk_datatype_ptr_decref(_y_x10208, _ctx);
          }
          _x_x1487 = kk_std_core_types__lp__plus__plus__rp_(x_0, y, _ctx); /*string*/
          goto _match_x1488;
        }
      }
    }
  }
  {
    kk_vector_t _x_x1497 = kk_std_core_vector_unvlist(_y_x10208, _ctx); /*vector<978>*/
    kk_string_t _x_x1498;
    kk_define_string_literal(, _s_x1499, 1, ",", _ctx)
    _x_x1498 = kk_string_dup(_s_x1499, _ctx); /*string*/
    _x_x1487 = kk_string_join_with(_x_x1497,_x_x1498,kk_context()); /*string*/
  }
  _match_x1488: ;
  kk_string_t _x_x1500;
  kk_define_string_literal(, _s_x1501, 1, "]", _ctx)
  _x_x1500 = kk_string_dup(_s_x1501, _ctx); /*string*/
  _x_x1486 = kk_std_core_types__lp__plus__plus__rp_(_x_x1487, _x_x1500, _ctx); /*string*/
  return kk_std_core_types__lp__plus__plus__rp_(_x_x1484, _x_x1486, _ctx);
}
 
// Show a list


// lift anonymous function
struct kk_std_core_list_show_fun1502__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_show;
};
static kk_box_t kk_std_core_list_show_fun1502(kk_function_t _fself, kk_box_t _b_x584, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_show_fun1502(kk_function_t _implicit_fs_show, kk_context_t* _ctx) {
  struct kk_std_core_list_show_fun1502__t* _self = kk_function_alloc_as(struct kk_std_core_list_show_fun1502__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_show_fun1502, kk_context());
  _self->_implicit_fs_show = _implicit_fs_show;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_show_fun1502(kk_function_t _fself, kk_box_t _b_x584, kk_context_t* _ctx) {
  struct kk_std_core_list_show_fun1502__t* _self = kk_function_as(struct kk_std_core_list_show_fun1502__t*, _fself, _ctx);
  kk_function_t _implicit_fs_show = _self->_implicit_fs_show; /* (3527) -> 3528 string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_show, _ctx);}, {}, _ctx)
  kk_string_t _x_x1503 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_show, (_implicit_fs_show, _b_x584, _ctx), _ctx); /*string*/
  return kk_string_box(_x_x1503);
}


// lift anonymous function
struct kk_std_core_list_show_fun1505__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_show_fun1505(kk_function_t _fself, kk_box_t _b_x589, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_show_fun1505(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_show_fun1505, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_show_fun1505(kk_function_t _fself, kk_box_t _b_x589, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_std_core_types__list _y_x10208_594 = kk_std_core_types__list_unbox(_b_x589, KK_OWNED, _ctx); /*list<string>*/;
  kk_string_t _x_x1506 = kk_std_core_list__mlift_show_10301(_y_x10208_594, _ctx); /*string*/
  return kk_string_box(_x_x1506);
}

kk_string_t kk_std_core_list_show(kk_std_core_types__list xs, kk_function_t _implicit_fs_show, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, ?show : (a) -> e string) -> e string */ 
  kk_std_core_types__cctx _b_x583_587 = kk_cctx_empty(kk_context()); /*ctx<list<string>>*/;
  kk_std_core_types__list x_10407;
  kk_function_t _brw_x1075 = kk_std_core_list_new_show_fun1502(_implicit_fs_show, _ctx); /*(2217) -> 2219 2218*/;
  kk_std_core_types__list _brw_x1076 = kk_std_core_list__trmc_map(xs, _brw_x1075, _b_x583_587, _ctx); /*list<2218>*/;
  kk_function_drop(_brw_x1075, _ctx);
  x_10407 = _brw_x1076; /*list<string>*/
  if (kk_yielding(kk_context())) {
    kk_std_core_types__list_drop(x_10407, _ctx);
    kk_box_t _x_x1504 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_show_fun1505(_ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x1504);
  }
  {
    kk_string_t _x_x1507;
    kk_define_string_literal(, _s_x1508, 1, "[", _ctx)
    _x_x1507 = kk_string_dup(_s_x1508, _ctx); /*string*/
    kk_string_t _x_x1509;
    kk_string_t _x_x1510;
    if (kk_std_core_types__is_Nil(x_10407, _ctx)) {
      _x_x1510 = kk_string_empty(); /*string*/
      goto _match_x1511;
    }
    {
      struct kk_std_core_types_Cons* _con_x1513 = kk_std_core_types__as_Cons(x_10407, _ctx);
      kk_box_t _box_x590 = _con_x1513->head;
      kk_std_core_types__list _pat_1_0 = _con_x1513->tail;
      if (kk_std_core_types__is_Nil(_pat_1_0, _ctx)) {
        kk_string_t x_0 = kk_string_unbox(_box_x590);
        if kk_likely(kk_datatype_ptr_is_unique(x_10407, _ctx)) {
          kk_datatype_ptr_free(x_10407, _ctx);
        }
        else {
          kk_string_dup(x_0, _ctx);
          kk_datatype_ptr_decref(x_10407, _ctx);
        }
        _x_x1510 = x_0; /*string*/
        goto _match_x1511;
      }
    }
    if (kk_std_core_types__is_Cons(x_10407, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1514 = kk_std_core_types__as_Cons(x_10407, _ctx);
      kk_box_t _box_x591 = _con_x1514->head;
      kk_std_core_types__list _pat_3 = _con_x1514->tail;
      if (kk_std_core_types__is_Cons(_pat_3, _ctx)) {
        struct kk_std_core_types_Cons* _con_x1515 = kk_std_core_types__as_Cons(_pat_3, _ctx);
        kk_box_t _box_x592 = _con_x1515->head;
        kk_std_core_types__list _pat_4 = _con_x1515->tail;
        if (kk_std_core_types__is_Nil(_pat_4, _ctx)) {
          kk_string_t _x_x1516;
          kk_define_string_literal(, _s_x1517, 1, ",", _ctx)
          _x_x1516 = kk_string_dup(_s_x1517, _ctx); /*string*/
          kk_string_t _x_x1518 = kk_string_empty(); /*string*/
          if (kk_string_is_eq(_x_x1516,_x_x1518,kk_context())) {
            kk_string_t x_0_0 = kk_string_unbox(_box_x591);
            kk_string_t y = kk_string_unbox(_box_x592);
            if kk_likely(kk_datatype_ptr_is_unique(x_10407, _ctx)) {
              if kk_likely(kk_datatype_ptr_is_unique(_pat_3, _ctx)) {
                kk_datatype_ptr_free(_pat_3, _ctx);
              }
              else {
                kk_string_dup(y, _ctx);
                kk_datatype_ptr_decref(_pat_3, _ctx);
              }
              kk_datatype_ptr_free(x_10407, _ctx);
            }
            else {
              kk_string_dup(x_0_0, _ctx);
              kk_string_dup(y, _ctx);
              kk_datatype_ptr_decref(x_10407, _ctx);
            }
            _x_x1510 = kk_std_core_types__lp__plus__plus__rp_(x_0_0, y, _ctx); /*string*/
            goto _match_x1511;
          }
        }
      }
    }
    {
      kk_vector_t _x_x1520 = kk_std_core_vector_unvlist(x_10407, _ctx); /*vector<978>*/
      kk_string_t _x_x1521;
      kk_define_string_literal(, _s_x1522, 1, ",", _ctx)
      _x_x1521 = kk_string_dup(_s_x1522, _ctx); /*string*/
      _x_x1510 = kk_string_join_with(_x_x1520,_x_x1521,kk_context()); /*string*/
    }
    _match_x1511: ;
    kk_string_t _x_x1523;
    kk_define_string_literal(, _s_x1524, 1, "]", _ctx)
    _x_x1523 = kk_string_dup(_s_x1524, _ctx); /*string*/
    _x_x1509 = kk_std_core_types__lp__plus__plus__rp_(_x_x1510, _x_x1523, _ctx); /*string*/
    return kk_std_core_types__lp__plus__plus__rp_(_x_x1507, _x_x1509, _ctx);
  }
}
 
// Zip two lists together by pairing the corresponding elements.
// The returned list is only as long as the smallest input list.

kk_std_core_types__list kk_std_core_list__trmc_zip(kk_std_core_types__list xs, kk_std_core_types__list ys, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a,b> (xs : list<a>, ys : list<b>, ctx<list<(a, b)>>) -> list<(a, b)> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1525 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1525->head;
    kk_std_core_types__list xx = _con_x1525->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    if (kk_std_core_types__is_Cons(ys, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1526 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t y = _con_x1526->head;
      kk_std_core_types__list yy = _con_x1526->tail;
      kk_reuse_t _ru_x1170 = kk_reuse_null; /*@reuse*/;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        _ru_x1170 = (kk_datatype_ptr_reuse(ys, _ctx));
      }
      else {
        kk_box_dup(y, _ctx);
        kk_std_core_types__list_dup(yy, _ctx);
        kk_datatype_ptr_decref(ys, _ctx);
      }
      kk_std_core_types__list _trmc_x10084 = kk_datatype_null(); /*list<(3644, 3645)>*/;
      kk_std_core_types__list _trmc_x10085;
      kk_box_t _x_x1527;
      kk_std_core_types__tuple2 _x_x1528 = kk_std_core_types__new_Tuple2(x, y, _ctx); /*(134, 135)*/
      _x_x1527 = kk_std_core_types__tuple2_box(_x_x1528, _ctx); /*79*/
      _trmc_x10085 = kk_std_core_types__new_Cons(_ru_x1170, 0, _x_x1527, _trmc_x10084, _ctx); /*list<(3644, 3645)>*/
      kk_field_addr_t _b_x604_611 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10085, _ctx)->tail, _ctx); /*@field-addr<list<(3644, 3645)>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1529 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10085, _ctx)),_b_x604_611,kk_context()); /*ctx<0>*/
        xs = xx;
        ys = yy;
        _acc = _x_x1529;
        goto kk__tailcall;
      }
    }
    {
      kk_std_core_types__list_drop(xx, _ctx);
      kk_box_drop(x, _ctx);
      kk_box_t _x_x1530 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
      return kk_std_core_types__list_unbox(_x_x1530, KK_OWNED, _ctx);
    }
  }
  {
    kk_std_core_types__list_drop(ys, _ctx);
    kk_box_t _x_x1531 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1531, KK_OWNED, _ctx);
  }
}
 
// Zip two lists together by pairing the corresponding elements.
// The returned list is only as long as the smallest input list.

kk_std_core_types__list kk_std_core_list_zip(kk_std_core_types__list xs_0, kk_std_core_types__list ys_0, kk_context_t* _ctx) { /* forall<a,b> (xs : list<a>, ys : list<b>) -> list<(a, b)> */ 
  kk_std_core_types__cctx _x_x1532 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_zip(xs_0, ys_0, _x_x1532, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_zipwith_10302(kk_std_core_types__cctx _acc, kk_function_t f, kk_std_core_types__list xx, kk_std_core_types__list yy, kk_box_t _trmc_x10086, kk_context_t* _ctx) { /* forall<a,b,c,e> (ctx<list<c>>, f : (a, b) -> e c, xx : list<a>, yy : list<b>, c) -> e list<c> */ 
  kk_std_core_types__list _trmc_x10087 = kk_datatype_null(); /*list<3727>*/;
  kk_std_core_types__list _trmc_x10088 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10086, _trmc_x10087, _ctx); /*list<3727>*/;
  kk_field_addr_t _b_x624_627 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10088, _ctx)->tail, _ctx); /*@field-addr<list<3727>>*/;
  kk_std_core_types__cctx _own_x1072 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10088, _ctx)),_b_x624_627,kk_context()); /*ctx<0>*/;
  kk_std_core_types__list _brw_x1073 = kk_std_core_list__trmc_zipwith(xx, yy, f, _own_x1072, _ctx); /*list<3727>*/;
  kk_function_drop(f, _ctx);
  return _brw_x1073;
}
 
// Zip two lists together by apply a function `f` to all corresponding elements.
// The returned list is only as long as the smallest input list.


// lift anonymous function
struct kk_std_core_list__trmc_zipwith_fun1538__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_std_core_types__list xx_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__trmc_zipwith_fun1538(kk_function_t _fself, kk_box_t _b_x632, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_zipwith_fun1538(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_std_core_types__list xx_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_zipwith_fun1538__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_zipwith_fun1538__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_zipwith_fun1538, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->xx_0 = xx_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_zipwith_fun1538(kk_function_t _fself, kk_box_t _b_x632, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_zipwith_fun1538__t* _self = kk_function_as(struct kk_std_core_list__trmc_zipwith_fun1538__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<3727>> */
  kk_function_t f_0 = _self->f_0; /* (3725, 3726) -> 3728 3727 */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<3725> */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<3726> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10086_0_654 = _b_x632; /*3727*/;
  kk_std_core_types__list _x_x1539 = kk_std_core_list__mlift_trmc_zipwith_10302(_acc_0, f_0, xx_0, yy_0, _trmc_x10086_0_654, _ctx); /*list<3727>*/
  return kk_std_core_types__list_box(_x_x1539, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_zipwith(kk_std_core_types__list xs, kk_std_core_types__list ys, kk_function_t f_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,c,e> (xs : list<a>, ys : list<b>, f : (a, b) -> e c, ctx<list<c>>) -> e list<c> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1533 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1533->head;
    kk_std_core_types__list xx_0 = _con_x1533->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    if (kk_std_core_types__is_Cons(ys, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1534 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t y = _con_x1534->head;
      kk_std_core_types__list yy_0 = _con_x1534->tail;
      kk_reuse_t _ru_x1172 = kk_reuse_null; /*@reuse*/;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        _ru_x1172 = (kk_datatype_ptr_reuse(ys, _ctx));
      }
      else {
        kk_box_dup(y, _ctx);
        kk_std_core_types__list_dup(yy_0, _ctx);
        kk_datatype_ptr_decref(ys, _ctx);
      }
      kk_box_t x_0_10412;
      kk_function_t _x_x1535 = kk_function_dup(f_0, _ctx); /*(3725, 3726) -> 3728 3727*/
      x_0_10412 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x1535, (_x_x1535, x, y, _ctx), _ctx); /*3727*/
      if (kk_yielding(kk_context())) {
        kk_reuse_drop(_ru_x1172,kk_context());
        kk_box_drop(x_0_10412, _ctx);
        kk_box_t _x_x1536;
        kk_function_t _x_x1537;
        kk_function_dup(f_0, _ctx);
        _x_x1537 = kk_std_core_list__new_trmc_zipwith_fun1538(_acc_0, f_0, xx_0, yy_0, _ctx); /*(2418) -> 2420 2419*/
        _x_x1536 = kk_std_core_hnd_yield_extend(_x_x1537, _ctx); /*2419*/
        return kk_std_core_types__list_unbox(_x_x1536, KK_OWNED, _ctx);
      }
      {
        kk_std_core_types__list _trmc_x10087_0 = kk_datatype_null(); /*list<3727>*/;
        kk_std_core_types__list _trmc_x10088_0 = kk_std_core_types__new_Cons(_ru_x1172, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0_10412, _trmc_x10087_0, _ctx); /*list<3727>*/;
        kk_field_addr_t _b_x638_646 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10088_0, _ctx)->tail, _ctx); /*@field-addr<list<3727>>*/;
        kk_std_core_types__cctx _own_x1071 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10088_0, _ctx)),_b_x638_646,kk_context()); /*ctx<0>*/;
        { // tailcall
          xs = xx_0;
          ys = yy_0;
          _acc_0 = _own_x1071;
          goto kk__tailcall;
        }
      }
    }
    {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_box_drop(x, _ctx);
      kk_box_t _x_x1540 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
      return kk_std_core_types__list_unbox(_x_x1540, KK_OWNED, _ctx);
    }
  }
  {
    kk_std_core_types__list_drop(ys, _ctx);
    kk_box_t _x_x1541 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1541, KK_OWNED, _ctx);
  }
}
 
// Zip two lists together by apply a function `f` to all corresponding elements.
// The returned list is only as long as the smallest input list.

kk_std_core_types__list kk_std_core_list_zipwith(kk_std_core_types__list xs_0, kk_std_core_types__list ys_0, kk_function_t f_1, kk_context_t* _ctx) { /* forall<a,b,c,e> (xs : list<a>, ys : list<b>, f : (a, b) -> e c) -> e list<c> */ 
  kk_std_core_types__cctx _own_x1069 = kk_cctx_empty(kk_context()); /*ctx<0>*/;
  return kk_std_core_list__trmc_zipwith(xs_0, ys_0, f_1, _own_x1069, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_zipwith_iter_10303(kk_std_core_types__cctx _acc, kk_function_t f, kk_integer_t i, kk_std_core_types__list xx, kk_std_core_types__list yy, kk_box_t _trmc_x10089, kk_context_t* _ctx) { /* forall<a,b,c,d,e> (ctx<list<a>>, f : (int, b, c) -> e d, i : int, xx : list<b>, yy : list<c>, d) -> e list<d> */ 
  kk_std_core_types__list _trmc_x10090 = kk_datatype_null(); /*list<3813>*/;
  kk_std_core_types__list _trmc_x10091 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), _trmc_x10089, _trmc_x10090, _ctx); /*list<3813>*/;
  kk_field_addr_t _b_x660_663 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10091, _ctx)->tail, _ctx); /*@field-addr<list<3813>>*/;
  kk_integer_t _own_x1067 = kk_integer_add_small_const(i, 1, _ctx); /*int*/;
  kk_std_core_types__cctx _own_x1066 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10091, _ctx)),_b_x660_663,kk_context()); /*ctx<0>*/;
  kk_std_core_types__list _brw_x1068 = kk_std_core_list__trmc_zipwith_iter(_own_x1067, xx, yy, f, _own_x1066, _ctx); /*list<3809>*/;
  kk_function_drop(f, _ctx);
  return _brw_x1068;
}


// lift anonymous function
struct kk_std_core_list__trmc_zipwith_iter_fun1548__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_integer_t i_0;
  kk_std_core_types__list xx_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__trmc_zipwith_iter_fun1548(kk_function_t _fself, kk_box_t _b_x668, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_zipwith_iter_fun1548(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_integer_t i_0, kk_std_core_types__list xx_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_zipwith_iter_fun1548__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_zipwith_iter_fun1548__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_zipwith_iter_fun1548, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->i_0 = i_0;
  _self->xx_0 = xx_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_zipwith_iter_fun1548(kk_function_t _fself, kk_box_t _b_x668, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_zipwith_iter_fun1548__t* _self = kk_function_as(struct kk_std_core_list__trmc_zipwith_iter_fun1548__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<3809>> */
  kk_function_t f_0 = _self->f_0; /* (int, 3811, 3812) -> 3814 3813 */
  kk_integer_t i_0 = _self->i_0; /* int */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<3811> */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<3812> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_integer_dup(i_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  kk_box_t _trmc_x10089_0_690 = _b_x668; /*3813*/;
  kk_std_core_types__list _x_x1549 = kk_std_core_list__mlift_trmc_zipwith_iter_10303(_acc_0, f_0, i_0, xx_0, yy_0, _trmc_x10089_0_690, _ctx); /*list<3813>*/
  return kk_std_core_types__list_box(_x_x1549, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_zipwith_iter(kk_integer_t i_0, kk_std_core_types__list xs, kk_std_core_types__list ys, kk_function_t f_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,c,e> (i : int, xs : list<a>, ys : list<b>, f : (int, a, b) -> e c, ctx<list<c>>) -> e list<c> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1542 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1542->head;
    kk_std_core_types__list xx_0 = _con_x1542->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    if (kk_std_core_types__is_Cons(ys, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1543 = kk_std_core_types__as_Cons(ys, _ctx);
      kk_box_t y = _con_x1543->head;
      kk_std_core_types__list yy_0 = _con_x1543->tail;
      kk_reuse_t _ru_x1174 = kk_reuse_null; /*@reuse*/;
      if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
        _ru_x1174 = (kk_datatype_ptr_reuse(ys, _ctx));
      }
      else {
        kk_box_dup(y, _ctx);
        kk_std_core_types__list_dup(yy_0, _ctx);
        kk_datatype_ptr_decref(ys, _ctx);
      }
      kk_box_t x_0_10415;
      kk_function_t _x_x1545 = kk_function_dup(f_0, _ctx); /*(int, 3811, 3812) -> 3814 3813*/
      kk_integer_t _x_x1544 = kk_integer_dup(i_0, _ctx); /*int*/
      x_0_10415 = kk_function_call(kk_box_t, (kk_function_t, kk_integer_t, kk_box_t, kk_box_t, kk_context_t*), _x_x1545, (_x_x1545, _x_x1544, x, y, _ctx), _ctx); /*3813*/
      if (kk_yielding(kk_context())) {
        kk_reuse_drop(_ru_x1174,kk_context());
        kk_box_drop(x_0_10415, _ctx);
        kk_box_t _x_x1546;
        kk_function_t _x_x1547;
        kk_function_dup(f_0, _ctx);
        _x_x1547 = kk_std_core_list__new_trmc_zipwith_iter_fun1548(_acc_0, f_0, i_0, xx_0, yy_0, _ctx); /*(2418) -> 2420 2419*/
        _x_x1546 = kk_std_core_hnd_yield_extend(_x_x1547, _ctx); /*2419*/
        return kk_std_core_types__list_unbox(_x_x1546, KK_OWNED, _ctx);
      }
      {
        kk_std_core_types__list _trmc_x10090_0 = kk_datatype_null(); /*list<3813>*/;
        kk_std_core_types__list _trmc_x10091_0 = kk_std_core_types__new_Cons(_ru_x1174, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0_10415, _trmc_x10090_0, _ctx); /*list<3813>*/;
        kk_field_addr_t _b_x674_682 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10091_0, _ctx)->tail, _ctx); /*@field-addr<list<3813>>*/;
        kk_integer_t _own_x1065 = kk_integer_add_small_const(i_0, 1, _ctx); /*int*/;
        kk_std_core_types__cctx _own_x1064 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10091_0, _ctx)),_b_x674_682,kk_context()); /*ctx<0>*/;
        { // tailcall
          i_0 = _own_x1065;
          xs = xx_0;
          ys = yy_0;
          _acc_0 = _own_x1064;
          goto kk__tailcall;
        }
      }
    }
    {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_box_drop(x, _ctx);
      kk_integer_drop(i_0, _ctx);
      kk_box_t _x_x1550 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
      return kk_std_core_types__list_unbox(_x_x1550, KK_OWNED, _ctx);
    }
  }
  {
    kk_std_core_types__list_drop(ys, _ctx);
    kk_integer_drop(i_0, _ctx);
    kk_box_t _x_x1551 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1551, KK_OWNED, _ctx);
  }
}

kk_std_core_types__list kk_std_core_list_zipwith_iter(kk_integer_t i_1, kk_std_core_types__list xs_0, kk_std_core_types__list ys_0, kk_function_t f_1, kk_context_t* _ctx) { /* forall<a,b,c,e> (i : int, xs : list<a>, ys : list<b>, f : (int, a, b) -> e c) -> e list<c> */ 
  kk_std_core_types__cctx _own_x1062 = kk_cctx_empty(kk_context()); /*ctx<0>*/;
  return kk_std_core_list__trmc_zipwith_iter(i_1, xs_0, ys_0, f_1, _own_x1062, _ctx);
}
 
// lifted local: unzip, iter

kk_std_core_types__tuple2 kk_std_core_list__lift_unzip_5735(kk_std_core_types__list ys, kk_std_core_types__cctx acc1, kk_std_core_types__cctx acc2, kk_context_t* _ctx) { /* forall<a,b,c,d> (ys : list<(a, b)>, acc1 : cctx<c,list<a>>, acc2 : cctx<d,list<b>>) -> (c, d) */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1552 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t _box_x691 = _con_x1552->head;
    kk_std_core_types__tuple2 _pat_0 = kk_std_core_types__tuple2_unbox(_box_x691, KK_BORROWED, _ctx);
    kk_std_core_types__list xx = _con_x1552->tail;
    kk_box_t x = _pat_0.fst;
    kk_box_t y = _pat_0.snd;
    kk_reuse_t _ru_x1175 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      kk_box_dup(x, _ctx);
      kk_box_dup(y, _ctx);
      kk_box_drop(_box_x691, _ctx);
      _ru_x1175 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_box_dup(y, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_std_core_types__list _cctx_x3917;
    kk_std_core_types__list _x_x1553 = kk_datatype_null(); /*list<4024>*/
    _cctx_x3917 = kk_std_core_types__new_Cons(_ru_x1175, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _x_x1553, _ctx); /*list<4024>*/
    kk_field_addr_t _cctx_x3918 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x3917, _ctx)->tail, _ctx); /*@field-addr<list<4024>>*/;
    kk_std_core_types__list _cctx_x3960;
    kk_std_core_types__list _x_x1554 = kk_datatype_null(); /*list<4025>*/
    _cctx_x3960 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _x_x1554, _ctx); /*list<4025>*/
    kk_field_addr_t _cctx_x3961 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x3960, _ctx)->tail, _ctx); /*@field-addr<list<4025>>*/;
    kk_std_core_types__list _b_x704_712 = _cctx_x3917; /*list<4024>*/;
    kk_field_addr_t _b_x705_713 = _cctx_x3918; /*@field-addr<list<4024>>*/;
    kk_std_core_types__list _b_x706_714 = _cctx_x3960; /*list<4025>*/;
    kk_field_addr_t _b_x707_715 = _cctx_x3961; /*@field-addr<list<4025>>*/;
    { // tailcall
      kk_std_core_types__cctx _x_x1555;
      kk_std_core_types__cctx _x_x1556 = kk_cctx_create((kk_std_core_types__list_box(_b_x704_712, _ctx)),_b_x705_713,kk_context()); /*cctx<0,1>*/
      _x_x1555 = kk_cctx_compose(acc1,_x_x1556,kk_context()); /*cctx<394,396>*/
      kk_std_core_types__cctx _x_x1557;
      kk_std_core_types__cctx _x_x1558 = kk_cctx_create((kk_std_core_types__list_box(_b_x706_714, _ctx)),_b_x707_715,kk_context()); /*cctx<0,1>*/
      _x_x1557 = kk_cctx_compose(acc2,_x_x1558,kk_context()); /*cctx<394,396>*/
      ys = xx;
      acc1 = _x_x1555;
      acc2 = _x_x1557;
      goto kk__tailcall;
    }
  }
  {
    kk_box_t _x_x1559 = kk_cctx_apply(acc1,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    kk_box_t _x_x1560 = kk_cctx_apply(acc2,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    return kk_std_core_types__new_Tuple2(_x_x1559, _x_x1560, _ctx);
  }
}
 
// lifted local: unzip3, iter

kk_std_core_types__tuple3 kk_std_core_list__lift_unzip3_5736(kk_std_core_types__list ys, kk_std_core_types__cctx acc1, kk_std_core_types__cctx acc2, kk_std_core_types__cctx acc3, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,b1> (ys : list<(a, b, c)>, acc1 : cctx<d,list<a>>, acc2 : cctx<a1,list<b>>, acc3 : cctx<b1,list<c>>) -> (d, a1, b1) */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1563 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t _box_x720 = _con_x1563->head;
    kk_std_core_types__tuple3 _pat_0 = kk_std_core_types__tuple3_unbox(_box_x720, KK_BORROWED, _ctx);
    kk_std_core_types__list xx = _con_x1563->tail;
    kk_box_t x = _pat_0.fst;
    kk_box_t y = _pat_0.snd;
    kk_box_t z = _pat_0.thd;
    kk_reuse_t _ru_x1176 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      kk_box_dup(x, _ctx);
      kk_box_dup(y, _ctx);
      kk_box_dup(z, _ctx);
      kk_box_drop(_box_x720, _ctx);
      _ru_x1176 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_box_dup(y, _ctx);
      kk_box_dup(z, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_std_core_types__list _cctx_x4133;
    kk_std_core_types__list _x_x1564 = kk_datatype_null(); /*list<4302>*/
    _cctx_x4133 = kk_std_core_types__new_Cons(_ru_x1176, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _x_x1564, _ctx); /*list<4302>*/
    kk_field_addr_t _cctx_x4134 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4133, _ctx)->tail, _ctx); /*@field-addr<list<4302>>*/;
    kk_std_core_types__list _cctx_x4176;
    kk_std_core_types__list _x_x1565 = kk_datatype_null(); /*list<4303>*/
    _cctx_x4176 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _x_x1565, _ctx); /*list<4303>*/
    kk_field_addr_t _cctx_x4177 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4176, _ctx)->tail, _ctx); /*@field-addr<list<4303>>*/;
    kk_std_core_types__list _cctx_x4219;
    kk_std_core_types__list _x_x1566 = kk_datatype_null(); /*list<4304>*/
    _cctx_x4219 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), z, _x_x1566, _ctx); /*list<4304>*/
    kk_field_addr_t _cctx_x4220 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4219, _ctx)->tail, _ctx); /*@field-addr<list<4304>>*/;
    kk_std_core_types__list _b_x739_751 = _cctx_x4133; /*list<4302>*/;
    kk_field_addr_t _b_x740_752 = _cctx_x4134; /*@field-addr<list<4302>>*/;
    kk_std_core_types__list _b_x741_753 = _cctx_x4176; /*list<4303>*/;
    kk_field_addr_t _b_x742_754 = _cctx_x4177; /*@field-addr<list<4303>>*/;
    kk_std_core_types__list _b_x743_755 = _cctx_x4219; /*list<4304>*/;
    kk_field_addr_t _b_x744_756 = _cctx_x4220; /*@field-addr<list<4304>>*/;
    { // tailcall
      kk_std_core_types__cctx _x_x1567;
      kk_std_core_types__cctx _x_x1568 = kk_cctx_create((kk_std_core_types__list_box(_b_x739_751, _ctx)),_b_x740_752,kk_context()); /*cctx<0,1>*/
      _x_x1567 = kk_cctx_compose(acc1,_x_x1568,kk_context()); /*cctx<394,396>*/
      kk_std_core_types__cctx _x_x1569;
      kk_std_core_types__cctx _x_x1570 = kk_cctx_create((kk_std_core_types__list_box(_b_x741_753, _ctx)),_b_x742_754,kk_context()); /*cctx<0,1>*/
      _x_x1569 = kk_cctx_compose(acc2,_x_x1570,kk_context()); /*cctx<394,396>*/
      kk_std_core_types__cctx _x_x1571;
      kk_std_core_types__cctx _x_x1572 = kk_cctx_create((kk_std_core_types__list_box(_b_x743_755, _ctx)),_b_x744_756,kk_context()); /*cctx<0,1>*/
      _x_x1571 = kk_cctx_compose(acc3,_x_x1572,kk_context()); /*cctx<394,396>*/
      ys = xx;
      acc1 = _x_x1567;
      acc2 = _x_x1569;
      acc3 = _x_x1571;
      goto kk__tailcall;
    }
  }
  {
    kk_box_t _x_x1573 = kk_cctx_apply(acc1,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    kk_box_t _x_x1574 = kk_cctx_apply(acc2,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    kk_box_t _x_x1575 = kk_cctx_apply(acc3,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    return kk_std_core_types__new_Tuple3(_x_x1573, _x_x1574, _x_x1575, _ctx);
  }
}
 
// lifted local: unzip4, iter

kk_std_core_types__tuple4 kk_std_core_list__lift_unzip4_5737(kk_std_core_types__list ys, kk_std_core_types__cctx acc1, kk_std_core_types__cctx acc2, kk_std_core_types__cctx acc3, kk_std_core_types__cctx acc4, kk_context_t* _ctx) { /* forall<a,b,c,d,a1,b1,c1,d1> (ys : list<(a, b, c, d)>, acc1 : cctx<a1,list<a>>, acc2 : cctx<b1,list<b>>, acc3 : cctx<c1,list<c>>, acc4 : cctx<d1,list<d>>) -> (a1, b1, c1, d1) */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1579 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t _box_x763 = _con_x1579->head;
    kk_std_core_types__tuple4 _pat_0 = kk_std_core_types__tuple4_unbox(_box_x763, KK_BORROWED, _ctx);
    struct kk_std_core_types_Tuple4* _con_x1580 = kk_std_core_types__as_Tuple4(_pat_0, _ctx);
    kk_std_core_types__list xx = _con_x1579->tail;
    kk_box_t x = _con_x1580->fst;
    kk_box_t y = _con_x1580->snd;
    kk_box_t z = _con_x1580->thd;
    kk_box_t w = _con_x1580->field4;
    kk_reuse_t _ru_x1178 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      if kk_likely(kk_datatype_ptr_is_unique(_pat_0, _ctx)) {
        kk_datatype_ptr_free(_pat_0, _ctx);
      }
      else {
        kk_box_dup(w, _ctx);
        kk_box_dup(x, _ctx);
        kk_box_dup(y, _ctx);
        kk_box_dup(z, _ctx);
        kk_datatype_ptr_decref(_pat_0, _ctx);
      }
      _ru_x1178 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(w, _ctx);
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_box_dup(y, _ctx);
      kk_box_dup(z, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_std_core_types__list _cctx_x4440;
    kk_std_core_types__list _x_x1581 = kk_datatype_null(); /*list<4671>*/
    _cctx_x4440 = kk_std_core_types__new_Cons(_ru_x1178, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _x_x1581, _ctx); /*list<4671>*/
    kk_field_addr_t _cctx_x4441 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4440, _ctx)->tail, _ctx); /*@field-addr<list<4671>>*/;
    kk_std_core_types__list _cctx_x4483;
    kk_std_core_types__list _x_x1582 = kk_datatype_null(); /*list<4672>*/
    _cctx_x4483 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _x_x1582, _ctx); /*list<4672>*/
    kk_field_addr_t _cctx_x4484 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4483, _ctx)->tail, _ctx); /*@field-addr<list<4672>>*/;
    kk_std_core_types__list _cctx_x4526;
    kk_std_core_types__list _x_x1583 = kk_datatype_null(); /*list<4673>*/
    _cctx_x4526 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), z, _x_x1583, _ctx); /*list<4673>*/
    kk_field_addr_t _cctx_x4527 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4526, _ctx)->tail, _ctx); /*@field-addr<list<4673>>*/;
    kk_std_core_types__list _cctx_x4569;
    kk_std_core_types__list _x_x1584 = kk_datatype_null(); /*list<4674>*/
    _cctx_x4569 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), w, _x_x1584, _ctx); /*list<4674>*/
    kk_field_addr_t _cctx_x4570 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4569, _ctx)->tail, _ctx); /*@field-addr<list<4674>>*/;
    kk_std_core_types__list _b_x788_804 = _cctx_x4440; /*list<4671>*/;
    kk_field_addr_t _b_x789_805 = _cctx_x4441; /*@field-addr<list<4671>>*/;
    kk_std_core_types__list _b_x790_806 = _cctx_x4483; /*list<4672>*/;
    kk_field_addr_t _b_x791_807 = _cctx_x4484; /*@field-addr<list<4672>>*/;
    kk_std_core_types__list _b_x792_808 = _cctx_x4526; /*list<4673>*/;
    kk_field_addr_t _b_x793_809 = _cctx_x4527; /*@field-addr<list<4673>>*/;
    kk_std_core_types__list _b_x794_810 = _cctx_x4569; /*list<4674>*/;
    kk_field_addr_t _b_x795_811 = _cctx_x4570; /*@field-addr<list<4674>>*/;
    { // tailcall
      kk_std_core_types__cctx _x_x1585;
      kk_std_core_types__cctx _x_x1586 = kk_cctx_create((kk_std_core_types__list_box(_b_x788_804, _ctx)),_b_x789_805,kk_context()); /*cctx<0,1>*/
      _x_x1585 = kk_cctx_compose(acc1,_x_x1586,kk_context()); /*cctx<394,396>*/
      kk_std_core_types__cctx _x_x1587;
      kk_std_core_types__cctx _x_x1588 = kk_cctx_create((kk_std_core_types__list_box(_b_x790_806, _ctx)),_b_x791_807,kk_context()); /*cctx<0,1>*/
      _x_x1587 = kk_cctx_compose(acc2,_x_x1588,kk_context()); /*cctx<394,396>*/
      kk_std_core_types__cctx _x_x1589;
      kk_std_core_types__cctx _x_x1590 = kk_cctx_create((kk_std_core_types__list_box(_b_x792_808, _ctx)),_b_x793_809,kk_context()); /*cctx<0,1>*/
      _x_x1589 = kk_cctx_compose(acc3,_x_x1590,kk_context()); /*cctx<394,396>*/
      kk_std_core_types__cctx _x_x1591;
      kk_std_core_types__cctx _x_x1592 = kk_cctx_create((kk_std_core_types__list_box(_b_x794_810, _ctx)),_b_x795_811,kk_context()); /*cctx<0,1>*/
      _x_x1591 = kk_cctx_compose(acc4,_x_x1592,kk_context()); /*cctx<394,396>*/
      ys = xx;
      acc1 = _x_x1585;
      acc2 = _x_x1587;
      acc3 = _x_x1589;
      acc4 = _x_x1591;
      goto kk__tailcall;
    }
  }
  {
    kk_box_t _x_x1593 = kk_cctx_apply(acc1,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    kk_box_t _x_x1594 = kk_cctx_apply(acc2,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    kk_box_t _x_x1595 = kk_cctx_apply(acc3,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    kk_box_t _x_x1596 = kk_cctx_apply(acc4,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*382*/
    return kk_std_core_types__new_Tuple4(kk_reuse_null, 0, _x_x1593, _x_x1594, _x_x1595, _x_x1596, _ctx);
  }
}
 
// monadic lift

kk_std_core_types__tuple2 kk_std_core_list__mlift_lift_span_5738_10304(kk_std_core_types__cctx acc, kk_function_t predicate, kk_box_t y, kk_std_core_types__list ys, kk_std_core_types__list yy, bool _y_x10221, kk_context_t* _ctx) { /* forall<a,b,e> (acc : cctx<a,list<b>>, predicate : (b) -> e bool, y : b, ys : list<b>, yy : list<b>, bool) -> e (a, list<b>) */ 
  if (_y_x10221) {
    kk_std_core_types__list_drop(ys, _ctx);
    kk_std_core_types__list _cctx_x4824;
    kk_std_core_types__list _x_x1601 = kk_datatype_null(); /*list<4921>*/
    _cctx_x4824 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _x_x1601, _ctx); /*list<4921>*/
    kk_field_addr_t _cctx_x4825 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4824, _ctx)->tail, _ctx); /*@field-addr<list<4921>>*/;
    kk_std_core_types__cctx acc_0_10030;
    kk_std_core_types__cctx _x_x1602 = kk_cctx_create((kk_std_core_types__list_box(_cctx_x4824, _ctx)),_cctx_x4825,kk_context()); /*cctx<0,1>*/
    acc_0_10030 = kk_cctx_compose(acc,_x_x1602,kk_context()); /*cctx<4896,list<4921>>*/
    return kk_std_core_list__lift_span_5738(predicate, yy, acc_0_10030, _ctx);
  }
  {
    kk_std_core_types__list_drop(yy, _ctx);
    kk_box_drop(y, _ctx);
    kk_function_drop(predicate, _ctx);
    kk_box_t _b_x832_834 = kk_cctx_apply(acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*4896*/;
    return kk_std_core_types__new_Tuple2(_b_x832_834, kk_std_core_types__list_box(ys, _ctx), _ctx);
  }
}
 
// lifted local: span, span-acc


// lift anonymous function
struct kk_std_core_list__lift_span_5738_fun1607__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx acc_0;
  kk_function_t predicate_0;
  kk_box_t y_0;
  kk_std_core_types__list ys_0;
  kk_std_core_types__list yy_0;
};
static kk_box_t kk_std_core_list__lift_span_5738_fun1607(kk_function_t _fself, kk_box_t _b_x839, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_lift_span_5738_fun1607(kk_std_core_types__cctx acc_0, kk_function_t predicate_0, kk_box_t y_0, kk_std_core_types__list ys_0, kk_std_core_types__list yy_0, kk_context_t* _ctx) {
  struct kk_std_core_list__lift_span_5738_fun1607__t* _self = kk_function_alloc_as(struct kk_std_core_list__lift_span_5738_fun1607__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__lift_span_5738_fun1607, kk_context());
  _self->acc_0 = acc_0;
  _self->predicate_0 = predicate_0;
  _self->y_0 = y_0;
  _self->ys_0 = ys_0;
  _self->yy_0 = yy_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__lift_span_5738_fun1607(kk_function_t _fself, kk_box_t _b_x839, kk_context_t* _ctx) {
  struct kk_std_core_list__lift_span_5738_fun1607__t* _self = kk_function_as(struct kk_std_core_list__lift_span_5738_fun1607__t*, _fself, _ctx);
  kk_std_core_types__cctx acc_0 = _self->acc_0; /* cctx<4896,list<4921>> */
  kk_function_t predicate_0 = _self->predicate_0; /* (4921) -> 4922 bool */
  kk_box_t y_0 = _self->y_0; /* 4921 */
  kk_std_core_types__list ys_0 = _self->ys_0; /* list<4921> */
  kk_std_core_types__list yy_0 = _self->yy_0; /* list<4921> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(acc_0, _ctx);kk_function_dup(predicate_0, _ctx);kk_box_dup(y_0, _ctx);kk_std_core_types__list_dup(ys_0, _ctx);kk_std_core_types__list_dup(yy_0, _ctx);}, {}, _ctx)
  bool _y_x10221_0_867 = kk_bool_unbox(_b_x839); /*bool*/;
  kk_std_core_types__tuple2 _x_x1608 = kk_std_core_list__mlift_lift_span_5738_10304(acc_0, predicate_0, y_0, ys_0, yy_0, _y_x10221_0_867, _ctx); /*(4896, list<4921>)*/
  return kk_std_core_types__tuple2_box(_x_x1608, _ctx);
}

kk_std_core_types__tuple2 kk_std_core_list__lift_span_5738(kk_function_t predicate_0, kk_std_core_types__list ys_0, kk_std_core_types__cctx acc_0, kk_context_t* _ctx) { /* forall<a,e,b> (predicate : (a) -> e bool, ys : list<a>, acc : cctx<b,list<a>>) -> e (b, list<a>) */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys_0, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1603 = kk_std_core_types__as_Cons(ys_0, _ctx);
    kk_box_t y_0 = _con_x1603->head;
    kk_std_core_types__list yy_0 = _con_x1603->tail;
    kk_box_dup(y_0, _ctx);
    kk_std_core_types__list_dup(yy_0, _ctx);
    bool x_10422;
    kk_function_t _x_x1605 = kk_function_dup(predicate_0, _ctx); /*(4921) -> 4922 bool*/
    kk_box_t _x_x1604 = kk_box_dup(y_0, _ctx); /*4921*/
    x_10422 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1605, (_x_x1605, _x_x1604, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x1606 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_lift_span_5738_fun1607(acc_0, predicate_0, y_0, ys_0, yy_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__tuple2_unbox(_x_x1606, KK_OWNED, _ctx);
    }
    if (x_10422) {
      kk_reuse_t _ru_x1179 = kk_reuse_null; /*@reuse*/;
      if kk_likely(kk_datatype_ptr_is_unique(ys_0, _ctx)) {
        kk_std_core_types__list_drop(yy_0, _ctx);
        kk_box_drop(y_0, _ctx);
        _ru_x1179 = (kk_datatype_ptr_reuse(ys_0, _ctx));
      }
      else {
        kk_datatype_ptr_decref(ys_0, _ctx);
      }
      kk_std_core_types__list _cctx_x4824_0;
      kk_std_core_types__list _x_x1609 = kk_datatype_null(); /*list<4921>*/
      _cctx_x4824_0 = kk_std_core_types__new_Cons(_ru_x1179, kk_field_index_of(struct kk_std_core_types_Cons, tail), y_0, _x_x1609, _ctx); /*list<4921>*/
      kk_field_addr_t _cctx_x4825_0 = kk_field_addr_create(&kk_std_core_types__as_Cons(_cctx_x4824_0, _ctx)->tail, _ctx); /*@field-addr<list<4921>>*/;
      kk_std_core_types__cctx acc_0_10030_0;
      kk_std_core_types__cctx _x_x1610 = kk_cctx_create((kk_std_core_types__list_box(_cctx_x4824_0, _ctx)),_cctx_x4825_0,kk_context()); /*cctx<0,1>*/
      acc_0_10030_0 = kk_cctx_compose(acc_0,_x_x1610,kk_context()); /*cctx<4896,list<4921>>*/
      { // tailcall
        ys_0 = yy_0;
        acc_0 = acc_0_10030_0;
        goto kk__tailcall;
      }
    }
    {
      kk_std_core_types__list_drop(yy_0, _ctx);
      kk_box_drop(y_0, _ctx);
      kk_function_drop(predicate_0, _ctx);
      kk_box_t _b_x852_859 = kk_cctx_apply(acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*4896*/;
      return kk_std_core_types__new_Tuple2(_b_x852_859, kk_std_core_types__list_box(ys_0, _ctx), _ctx);
    }
  }
  {
    kk_function_drop(predicate_0, _ctx);
    kk_box_t _b_x856_863 = kk_cctx_apply(acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*4896*/;
    return kk_std_core_types__new_Tuple2(_b_x856_863, kk_std_core_types__list_box(ys_0, _ctx), _ctx);
  }
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_take_while_10305(kk_std_core_types__cctx _acc, kk_function_t predicate, kk_box_t x, kk_std_core_types__list xx, bool _y_x10226, kk_context_t* _ctx) { /* forall<a,e> (ctx<list<a>>, predicate : (a) -> e bool, x : a, xx : list<a>, bool) -> e list<a> */ 
  if (_y_x10226) {
    kk_std_core_types__list _trmc_x10092 = kk_datatype_null(); /*list<4980>*/;
    kk_std_core_types__list _trmc_x10093 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), x, _trmc_x10092, _ctx); /*list<4980>*/;
    kk_field_addr_t _b_x873_878 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10093, _ctx)->tail, _ctx); /*@field-addr<list<4980>>*/;
    kk_std_core_types__cctx _x_x1611 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10093, _ctx)),_b_x873_878,kk_context()); /*ctx<0>*/
    return kk_std_core_list__trmc_take_while(xx, predicate, _x_x1611, _ctx);
  }
  {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_box_drop(x, _ctx);
    kk_function_drop(predicate, _ctx);
    kk_box_t _x_x1612 = kk_cctx_apply(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1612, KK_OWNED, _ctx);
  }
}
 
// Keep only those initial elements that satisfy `predicate`


// lift anonymous function
struct kk_std_core_list__trmc_take_while_fun1617__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t predicate_0;
  kk_box_t x_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list__trmc_take_while_fun1617(kk_function_t _fself, kk_box_t _b_x885, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_take_while_fun1617(kk_std_core_types__cctx _acc_0, kk_function_t predicate_0, kk_box_t x_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_take_while_fun1617__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_take_while_fun1617__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_take_while_fun1617, kk_context());
  _self->_acc_0 = _acc_0;
  _self->predicate_0 = predicate_0;
  _self->x_0 = x_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_take_while_fun1617(kk_function_t _fself, kk_box_t _b_x885, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_take_while_fun1617__t* _self = kk_function_as(struct kk_std_core_list__trmc_take_while_fun1617__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<4980>> */
  kk_function_t predicate_0 = _self->predicate_0; /* (4980) -> 4981 bool */
  kk_box_t x_0 = _self->x_0; /* 4980 */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<4980> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(predicate_0, _ctx);kk_box_dup(x_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10226_0_907 = kk_bool_unbox(_b_x885); /*bool*/;
  kk_std_core_types__list _x_x1618 = kk_std_core_list__mlift_trmc_take_while_10305(_acc_0, predicate_0, x_0, xx_0, _y_x10226_0_907, _ctx); /*list<4980>*/
  return kk_std_core_types__list_box(_x_x1618, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_take_while(kk_std_core_types__list xs, kk_function_t predicate_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, predicate : (a) -> e bool, ctx<list<a>>) -> e list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1613 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x_0 = _con_x1613->head;
    kk_std_core_types__list xx_0 = _con_x1613->tail;
    kk_reuse_t _ru_x1180 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1180 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x_0, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool x_1_10425;
    kk_function_t _x_x1615 = kk_function_dup(predicate_0, _ctx); /*(4980) -> 4981 bool*/
    kk_box_t _x_x1614 = kk_box_dup(x_0, _ctx); /*4980*/
    x_1_10425 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1615, (_x_x1615, _x_x1614, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1180,kk_context());
      kk_box_t _x_x1616 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_take_while_fun1617(_acc_0, predicate_0, x_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1616, KK_OWNED, _ctx);
    }
    if (x_1_10425) {
      kk_std_core_types__list _trmc_x10092_0 = kk_datatype_null(); /*list<4980>*/;
      kk_std_core_types__list _trmc_x10093_0 = kk_std_core_types__new_Cons(_ru_x1180, kk_field_index_of(struct kk_std_core_types_Cons, tail), x_0, _trmc_x10092_0, _ctx); /*list<4980>*/;
      kk_field_addr_t _b_x891_899 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10093_0, _ctx)->tail, _ctx); /*@field-addr<list<4980>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1619 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10093_0, _ctx)),_b_x891_899,kk_context()); /*ctx<0>*/
        xs = xx_0;
        _acc_0 = _x_x1619;
        goto kk__tailcall;
      }
    }
    {
      kk_reuse_drop(_ru_x1180,kk_context());
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_box_drop(x_0, _ctx);
      kk_function_drop(predicate_0, _ctx);
      kk_box_t _x_x1620 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
      return kk_std_core_types__list_unbox(_x_x1620, KK_OWNED, _ctx);
    }
  }
  {
    kk_function_drop(predicate_0, _ctx);
    kk_box_t _x_x1621 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1621, KK_OWNED, _ctx);
  }
}
 
// Keep only those initial elements that satisfy `predicate`

kk_std_core_types__list kk_std_core_list_take_while(kk_std_core_types__list xs_0, kk_function_t predicate_1, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, predicate : (a) -> e bool) -> e list<a> */ 
  kk_std_core_types__cctx _x_x1622 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_take_while(xs_0, predicate_1, _x_x1622, _ctx);
}
 
// Concatenate all strings in a list in reverse order

kk_string_t kk_std_core_list_reverse_join(kk_std_core_types__list xs, kk_context_t* _ctx) { /* (xs : list<string>) -> string */ 
  kk_std_core_types__list xs_0_10031 = kk_std_core_list_reverse_acc(kk_std_core_types__new_Nil(_ctx), xs, _ctx); /*list<string>*/;
  if (kk_std_core_types__is_Nil(xs_0_10031, _ctx)) {
    return kk_string_empty();
  }
  {
    struct kk_std_core_types_Cons* _con_x1624 = kk_std_core_types__as_Cons(xs_0_10031, _ctx);
    kk_box_t _box_x908 = _con_x1624->head;
    kk_std_core_types__list _pat_1 = _con_x1624->tail;
    if (kk_std_core_types__is_Nil(_pat_1, _ctx)) {
      kk_string_t x = kk_string_unbox(_box_x908);
      if kk_likely(kk_datatype_ptr_is_unique(xs_0_10031, _ctx)) {
        kk_datatype_ptr_free(xs_0_10031, _ctx);
      }
      else {
        kk_string_dup(x, _ctx);
        kk_datatype_ptr_decref(xs_0_10031, _ctx);
      }
      return x;
    }
  }
  {
    struct kk_std_core_types_Cons* _con_x1625 = kk_std_core_types__as_Cons(xs_0_10031, _ctx);
    kk_box_t _box_x909 = _con_x1625->head;
    kk_std_core_types__list _pat_3 = _con_x1625->tail;
    struct kk_std_core_types_Cons* _con_x1626 = kk_std_core_types__as_Cons(_pat_3, _ctx);
    kk_box_t _box_x910 = _con_x1626->head;
    kk_std_core_types__list _pat_4 = _con_x1626->tail;
    if (kk_std_core_types__is_Nil(_pat_4, _ctx)) {
      kk_string_t x_0 = kk_string_unbox(_box_x909);
      kk_string_t y = kk_string_unbox(_box_x910);
      if kk_likely(kk_datatype_ptr_is_unique(xs_0_10031, _ctx)) {
        if kk_likely(kk_datatype_ptr_is_unique(_pat_3, _ctx)) {
          kk_datatype_ptr_free(_pat_3, _ctx);
        }
        else {
          kk_string_dup(y, _ctx);
          kk_datatype_ptr_decref(_pat_3, _ctx);
        }
        kk_datatype_ptr_free(xs_0_10031, _ctx);
      }
      else {
        kk_string_dup(x_0, _ctx);
        kk_string_dup(y, _ctx);
        kk_datatype_ptr_decref(xs_0_10031, _ctx);
      }
      return kk_std_core_types__lp__plus__plus__rp_(x_0, y, _ctx);
    }
  }
  {
    kk_vector_t _x_x1627 = kk_std_core_vector_unvlist(xs_0_10031, _ctx); /*vector<978>*/
    return kk_string_join(_x_x1627,kk_context());
  }
}
 
// lifted local: concat, concat-pre

kk_std_core_types__list kk_std_core_list__trmc_lift_concat_5739(kk_std_core_types__list ys, kk_std_core_types__list zss, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (ys : list<a>, zss : list<list<a>>, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1631 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t y = _con_x1631->head;
    kk_std_core_types__list yy = _con_x1631->tail;
    kk_reuse_t _ru_x1184 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1184 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(y, _ctx);
      kk_std_core_types__list_dup(yy, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_std_core_types__list _trmc_x10094 = kk_datatype_null(); /*list<5090>*/;
    kk_std_core_types__list _trmc_x10095 = kk_std_core_types__new_Cons(_ru_x1184, 0, y, _trmc_x10094, _ctx); /*list<5090>*/;
    kk_field_addr_t _b_x916_922 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10095, _ctx)->tail, _ctx); /*@field-addr<list<5090>>*/;
    { // tailcall
      kk_std_core_types__cctx _x_x1632 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10095, _ctx)),_b_x916_922,kk_context()); /*ctx<0>*/
      ys = yy;
      _acc = _x_x1632;
      goto kk__tailcall;
    }
  }
  if (kk_std_core_types__is_Cons(zss, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1633 = kk_std_core_types__as_Cons(zss, _ctx);
    kk_box_t _box_x917 = _con_x1633->head;
    kk_std_core_types__list zzs = _con_x1633->tail;
    kk_std_core_types__list zs = kk_std_core_types__list_unbox(_box_x917, KK_BORROWED, _ctx);
    if kk_likely(kk_datatype_ptr_is_unique(zss, _ctx)) {
      kk_datatype_ptr_free(zss, _ctx);
    }
    else {
      kk_std_core_types__list_dup(zs, _ctx);
      kk_std_core_types__list_dup(zzs, _ctx);
      kk_datatype_ptr_decref(zss, _ctx);
    }
    { // tailcall
      ys = zs;
      zss = zzs;
      goto kk__tailcall;
    }
  }
  {
    kk_box_t _x_x1634 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1634, KK_OWNED, _ctx);
  }
}
 
// lifted local: concat, concat-pre

kk_std_core_types__list kk_std_core_list__lift_concat_5739(kk_std_core_types__list ys_0, kk_std_core_types__list zss_0, kk_context_t* _ctx) { /* forall<a> (ys : list<a>, zss : list<list<a>>) -> list<a> */ 
  kk_std_core_types__cctx _x_x1635 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_concat_5739(ys_0, zss_0, _x_x1635, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_lift_flatmap_5740_10306(kk_std_core_types__cctx _acc, kk_function_t f, kk_std_core_types__list zz, kk_std_core_types__list ys_1_10038, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, f : (a) -> e list<b>, zz : list<a>, ys@1@10038 : list<b>) -> e list<b> */ 
  return kk_std_core_list__trmc_lift_flatmap_5740(f, ys_1_10038, zz, _acc, _ctx);
}
 
// lifted local: flatmap, flatmap-pre


// lift anonymous function
struct kk_std_core_list__trmc_lift_flatmap_5740_fun1642__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_std_core_types__list zz_0;
};
static kk_box_t kk_std_core_list__trmc_lift_flatmap_5740_fun1642(kk_function_t _fself, kk_box_t _b_x935, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_lift_flatmap_5740_fun1642(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_std_core_types__list zz_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_flatmap_5740_fun1642__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_lift_flatmap_5740_fun1642__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_lift_flatmap_5740_fun1642, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->zz_0 = zz_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_lift_flatmap_5740_fun1642(kk_function_t _fself, kk_box_t _b_x935, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_lift_flatmap_5740_fun1642__t* _self = kk_function_as(struct kk_std_core_list__trmc_lift_flatmap_5740_fun1642__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<5182>> */
  kk_function_t f_0 = _self->f_0; /* (5181) -> 5183 list<5182> */
  kk_std_core_types__list zz_0 = _self->zz_0; /* list<5181> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_std_core_types__list_dup(zz_0, _ctx);}, {}, _ctx)
  kk_std_core_types__list ys_1_10038_0_947 = kk_std_core_types__list_unbox(_b_x935, KK_OWNED, _ctx); /*list<5182>*/;
  kk_std_core_types__list _x_x1643 = kk_std_core_list__mlift_trmc_lift_flatmap_5740_10306(_acc_0, f_0, zz_0, ys_1_10038_0_947, _ctx); /*list<5182>*/
  return kk_std_core_types__list_box(_x_x1643, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_lift_flatmap_5740(kk_function_t f_0, kk_std_core_types__list ys, kk_std_core_types__list zs, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (a) -> e list<b>, ys : list<b>, zs : list<a>, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(ys, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1637 = kk_std_core_types__as_Cons(ys, _ctx);
    kk_box_t y = _con_x1637->head;
    kk_std_core_types__list yy = _con_x1637->tail;
    kk_reuse_t _ru_x1186 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(ys, _ctx)) {
      _ru_x1186 = (kk_datatype_ptr_reuse(ys, _ctx));
    }
    else {
      kk_box_dup(y, _ctx);
      kk_std_core_types__list_dup(yy, _ctx);
      kk_datatype_ptr_decref(ys, _ctx);
    }
    kk_std_core_types__list _trmc_x10096 = kk_datatype_null(); /*list<5182>*/;
    kk_std_core_types__list _trmc_x10097 = kk_std_core_types__new_Cons(_ru_x1186, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _trmc_x10096, _ctx); /*list<5182>*/;
    kk_field_addr_t _b_x933_940 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10097, _ctx)->tail, _ctx); /*@field-addr<list<5182>>*/;
    { // tailcall
      kk_std_core_types__cctx _x_x1638 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10097, _ctx)),_b_x933_940,kk_context()); /*ctx<0>*/
      ys = yy;
      _acc_0 = _x_x1638;
      goto kk__tailcall;
    }
  }
  if (kk_std_core_types__is_Cons(zs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1639 = kk_std_core_types__as_Cons(zs, _ctx);
    kk_box_t z = _con_x1639->head;
    kk_std_core_types__list zz_0 = _con_x1639->tail;
    if kk_likely(kk_datatype_ptr_is_unique(zs, _ctx)) {
      kk_datatype_ptr_free(zs, _ctx);
    }
    else {
      kk_box_dup(z, _ctx);
      kk_std_core_types__list_dup(zz_0, _ctx);
      kk_datatype_ptr_decref(zs, _ctx);
    }
    kk_std_core_types__list x_10430;
    kk_function_t _x_x1640 = kk_function_dup(f_0, _ctx); /*(5181) -> 5183 list<5182>*/
    x_10430 = kk_function_call(kk_std_core_types__list, (kk_function_t, kk_box_t, kk_context_t*), _x_x1640, (_x_x1640, z, _ctx), _ctx); /*list<5182>*/
    if (kk_yielding(kk_context())) {
      kk_std_core_types__list_drop(x_10430, _ctx);
      kk_box_t _x_x1641 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_lift_flatmap_5740_fun1642(_acc_0, f_0, zz_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1641, KK_OWNED, _ctx);
    }
    { // tailcall
      ys = x_10430;
      zs = zz_0;
      goto kk__tailcall;
    }
  }
  {
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1644 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1644, KK_OWNED, _ctx);
  }
}
 
// lifted local: flatmap, flatmap-pre

kk_std_core_types__list kk_std_core_list__lift_flatmap_5740(kk_function_t f_1, kk_std_core_types__list ys_0, kk_std_core_types__list zs_0, kk_context_t* _ctx) { /* forall<a,b,e> (f : (a) -> e list<b>, ys : list<b>, zs : list<a>) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1645 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_lift_flatmap_5740(f_1, ys_0, zs_0, _x_x1645, _ctx);
}
 
// monadic lift

kk_std_core_types__list kk_std_core_list__mlift_trmc_flatmap_maybe_10307(kk_std_core_types__cctx _acc, kk_function_t f, kk_std_core_types__list xx, kk_std_core_types__maybe _y_x10238, kk_context_t* _ctx) { /* forall<a,b,e> (ctx<list<b>>, f : (a) -> e maybe<b>, xx : list<a>, maybe<b>) -> e list<b> */ 
  if (kk_std_core_types__is_Just(_y_x10238, _ctx)) {
    kk_box_t y = _y_x10238._cons.Just.value;
    kk_std_core_types__list _trmc_x10098 = kk_datatype_null(); /*list<5269>*/;
    kk_std_core_types__list _trmc_x10099 = kk_std_core_types__new_Cons(kk_reuse_null, kk_field_index_of(struct kk_std_core_types_Cons, tail), y, _trmc_x10098, _ctx); /*list<5269>*/;
    kk_field_addr_t _b_x953_956 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10099, _ctx)->tail, _ctx); /*@field-addr<list<5269>>*/;
    kk_std_core_types__cctx _x_x1647 = kk_cctx_extend(_acc,(kk_std_core_types__list_box(_trmc_x10099, _ctx)),_b_x953_956,kk_context()); /*ctx<0>*/
    return kk_std_core_list__trmc_flatmap_maybe(xx, f, _x_x1647, _ctx);
  }
  {
    return kk_std_core_list__trmc_flatmap_maybe(xx, f, _acc, _ctx);
  }
}
 
// Concatenate the `Just` result elements from applying a function to all elements.


// lift anonymous function
struct kk_std_core_list__trmc_flatmap_maybe_fun1651__t {
  struct kk_function_s _base;
  kk_std_core_types__cctx _acc_0;
  kk_function_t f_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list__trmc_flatmap_maybe_fun1651(kk_function_t _fself, kk_box_t _b_x961, kk_context_t* _ctx);
static kk_function_t kk_std_core_list__new_trmc_flatmap_maybe_fun1651(kk_std_core_types__cctx _acc_0, kk_function_t f_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_flatmap_maybe_fun1651__t* _self = kk_function_alloc_as(struct kk_std_core_list__trmc_flatmap_maybe_fun1651__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list__trmc_flatmap_maybe_fun1651, kk_context());
  _self->_acc_0 = _acc_0;
  _self->f_0 = f_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list__trmc_flatmap_maybe_fun1651(kk_function_t _fself, kk_box_t _b_x961, kk_context_t* _ctx) {
  struct kk_std_core_list__trmc_flatmap_maybe_fun1651__t* _self = kk_function_as(struct kk_std_core_list__trmc_flatmap_maybe_fun1651__t*, _fself, _ctx);
  kk_std_core_types__cctx _acc_0 = _self->_acc_0; /* ctx<list<5269>> */
  kk_function_t f_0 = _self->f_0; /* (5268) -> 5270 maybe<5269> */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<5268> */
  kk_drop_match(_self, {kk_std_core_types__cctx_dup(_acc_0, _ctx);kk_function_dup(f_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  kk_std_core_types__maybe _y_x10238_0_979 = kk_std_core_types__maybe_unbox(_b_x961, KK_OWNED, _ctx); /*maybe<5269>*/;
  kk_std_core_types__list _x_x1652 = kk_std_core_list__mlift_trmc_flatmap_maybe_10307(_acc_0, f_0, xx_0, _y_x10238_0_979, _ctx); /*list<5269>*/
  return kk_std_core_types__list_box(_x_x1652, _ctx);
}

kk_std_core_types__list kk_std_core_list__trmc_flatmap_maybe(kk_std_core_types__list xs, kk_function_t f_0, kk_std_core_types__cctx _acc_0, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, f : (a) -> e maybe<b>, ctx<list<b>>) -> e list<b> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1648 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1648->head;
    kk_std_core_types__list xx_0 = _con_x1648->tail;
    kk_reuse_t _ru_x1188 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      _ru_x1188 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__maybe x_0_10436;
    kk_function_t _x_x1649 = kk_function_dup(f_0, _ctx); /*(5268) -> 5270 maybe<5269>*/
    x_0_10436 = kk_function_call(kk_std_core_types__maybe, (kk_function_t, kk_box_t, kk_context_t*), _x_x1649, (_x_x1649, x, _ctx), _ctx); /*maybe<5269>*/
    if (kk_yielding(kk_context())) {
      kk_reuse_drop(_ru_x1188,kk_context());
      kk_std_core_types__maybe_drop(x_0_10436, _ctx);
      kk_box_t _x_x1650 = kk_std_core_hnd_yield_extend(kk_std_core_list__new_trmc_flatmap_maybe_fun1651(_acc_0, f_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_std_core_types__list_unbox(_x_x1650, KK_OWNED, _ctx);
    }
    if (kk_std_core_types__is_Just(x_0_10436, _ctx)) {
      kk_box_t y_0 = x_0_10436._cons.Just.value;
      kk_std_core_types__list _trmc_x10098_0 = kk_datatype_null(); /*list<5269>*/;
      kk_std_core_types__list _trmc_x10099_0 = kk_std_core_types__new_Cons(_ru_x1188, kk_field_index_of(struct kk_std_core_types_Cons, tail), y_0, _trmc_x10098_0, _ctx); /*list<5269>*/;
      kk_field_addr_t _b_x967_973 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10099_0, _ctx)->tail, _ctx); /*@field-addr<list<5269>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1653 = kk_cctx_extend(_acc_0,(kk_std_core_types__list_box(_trmc_x10099_0, _ctx)),_b_x967_973,kk_context()); /*ctx<0>*/
        xs = xx_0;
        _acc_0 = _x_x1653;
        goto kk__tailcall;
      }
    }
    {
      kk_reuse_drop(_ru_x1188,kk_context());
      { // tailcall
        xs = xx_0;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_function_drop(f_0, _ctx);
    kk_box_t _x_x1654 = kk_cctx_apply(_acc_0,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1654, KK_OWNED, _ctx);
  }
}
 
// Concatenate the `Just` result elements from applying a function to all elements.

kk_std_core_types__list kk_std_core_list_flatmap_maybe(kk_std_core_types__list xs_0, kk_function_t f_1, kk_context_t* _ctx) { /* forall<a,b,e> (xs : list<a>, f : (a) -> e maybe<b>) -> e list<b> */ 
  kk_std_core_types__cctx _x_x1655 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_flatmap_maybe(xs_0, f_1, _x_x1655, _ctx);
}
 
// Concatenate a list of `:maybe` values

kk_std_core_types__list kk_std_core_list__trmc_concat_maybe(kk_std_core_types__list xs, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (xs : list<maybe<a>>, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1656 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x980 = _con_x1656->head;
    kk_std_core_types__list xx = _con_x1656->tail;
    kk_std_core_types__maybe x = kk_std_core_types__maybe_unbox(_box_x980, KK_BORROWED, _ctx);
    kk_reuse_t _ru_x1189 = kk_reuse_null; /*@reuse*/;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_std_core_types__maybe_dup(x, _ctx);
      kk_box_drop(_box_x980, _ctx);
      _ru_x1189 = (kk_datatype_ptr_reuse(xs, _ctx));
    }
    else {
      kk_std_core_types__maybe_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    if (kk_std_core_types__is_Just(x, _ctx)) {
      kk_box_t y = x._cons.Just.value;
      kk_std_core_types__list _trmc_x10100 = kk_datatype_null(); /*list<5334>*/;
      kk_std_core_types__list _trmc_x10101 = kk_std_core_types__new_Cons(_ru_x1189, 0, y, _trmc_x10100, _ctx); /*list<5334>*/;
      kk_field_addr_t _b_x986_991 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10101, _ctx)->tail, _ctx); /*@field-addr<list<5334>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1657 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10101, _ctx)),_b_x986_991,kk_context()); /*ctx<0>*/
        xs = xx;
        _acc = _x_x1657;
        goto kk__tailcall;
      }
    }
    {
      kk_reuse_drop(_ru_x1189,kk_context());
      { // tailcall
        xs = xx;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_box_t _x_x1658 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1658, KK_OWNED, _ctx);
  }
}
 
// Concatenate a list of `:maybe` values

kk_std_core_types__list kk_std_core_list_concat_maybe(kk_std_core_types__list xs_0, kk_context_t* _ctx) { /* forall<a> (xs : list<maybe<a>>) -> list<a> */ 
  kk_std_core_types__cctx _x_x1659 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_concat_maybe(xs_0, _x_x1659, _ctx);
}
 
// Return the last element of a list (or `Nothing` for the empty list)

kk_std_core_types__maybe kk_std_core_list_last(kk_std_core_types__list xs, kk_context_t* _ctx) { /* forall<a> (xs : list<a>) -> maybe<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1660 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_std_core_types__list _pat_0 = _con_x1660->tail;
    if (kk_std_core_types__is_Nil(_pat_0, _ctx)) {
      kk_box_t x = _con_x1660->head;
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        kk_datatype_ptr_free(xs, _ctx);
      }
      else {
        kk_box_dup(x, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      return kk_std_core_types__new_Just(x, _ctx);
    }
  }
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1661 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _pat_2 = _con_x1661->head;
    kk_std_core_types__list xx = _con_x1661->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_box_drop(_pat_2, _ctx);
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    { // tailcall
      xs = xx;
      goto kk__tailcall;
    }
  }
  {
    return kk_std_core_types__new_Nothing(_ctx);
  }
}
 
// Return the list without its last element.
// Return an empty list for an empty list.

kk_std_core_types__list kk_std_core_list__trmc_init(kk_std_core_types__list xs, kk_std_core_types__cctx _acc, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, ctx<list<a>>) -> list<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1662 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_std_core_types__list xx = _con_x1662->tail;
    if (kk_std_core_types__is_Cons(xx, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1663 = kk_std_core_types__as_Cons(xx, _ctx);
      kk_box_t x = _con_x1662->head;
      kk_reuse_t _ru_x1192 = kk_reuse_null; /*@reuse*/;
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        _ru_x1192 = (kk_datatype_ptr_reuse(xs, _ctx));
      }
      else {
        kk_box_dup(x, _ctx);
        kk_std_core_types__list_dup(xx, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      kk_std_core_types__list _trmc_x10102 = kk_datatype_null(); /*list<5425>*/;
      kk_std_core_types__list _trmc_x10103 = kk_std_core_types__new_Cons(_ru_x1192, 0, x, _trmc_x10102, _ctx); /*list<5425>*/;
      kk_field_addr_t _b_x1002_1007 = kk_field_addr_create(&kk_std_core_types__as_Cons(_trmc_x10103, _ctx)->tail, _ctx); /*@field-addr<list<5425>>*/;
      { // tailcall
        kk_std_core_types__cctx _x_x1664 = kk_cctx_extend_linear(_acc,(kk_std_core_types__list_box(_trmc_x10103, _ctx)),_b_x1002_1007,kk_context()); /*ctx<0>*/
        xs = xx;
        _acc = _x_x1664;
        goto kk__tailcall;
      }
    }
  }
  {
    kk_std_core_types__list_drop(xs, _ctx);
    kk_box_t _x_x1665 = kk_cctx_apply_linear(_acc,(kk_std_core_types__list_box(kk_std_core_types__new_Nil(_ctx), _ctx)),kk_context()); /*-1*/
    return kk_std_core_types__list_unbox(_x_x1665, KK_OWNED, _ctx);
  }
}
 
// Return the list without its last element.
// Return an empty list for an empty list.

kk_std_core_types__list kk_std_core_list_init(kk_std_core_types__list xs_0, kk_context_t* _ctx) { /* forall<a> (xs : list<a>) -> list<a> */ 
  kk_std_core_types__cctx _x_x1666 = kk_cctx_empty(kk_context()); /*ctx<0>*/
  return kk_std_core_list__trmc_init(xs_0, _x_x1666, _ctx);
}
 
// Get (zero-based) element `n`  of a list. Return a `:maybe` type.

kk_std_core_types__maybe kk_std_core_list__index(kk_std_core_types__list xs, kk_integer_t n, kk_context_t* _ctx) { /* forall<a> (xs : list<a>, n : int) -> maybe<a> */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1667 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1667->head;
    kk_std_core_types__list xx = _con_x1667->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool _match_x1054 = kk_integer_gt_borrow(n,(kk_integer_from_small(0)),kk_context()); /*bool*/;
    if (_match_x1054) {
      kk_box_drop(x, _ctx);
      { // tailcall
        kk_integer_t _x_x1668 = kk_integer_add_small_const(n, -1, _ctx); /*int*/
        xs = xx;
        n = _x_x1668;
        goto kk__tailcall;
      }
    }
    {
      kk_std_core_types__list_drop(xx, _ctx);
      bool _match_x1055;
      bool _brw_x1056 = kk_integer_eq_borrow(n,(kk_integer_from_small(0)),kk_context()); /*bool*/;
      kk_integer_drop(n, _ctx);
      _match_x1055 = _brw_x1056; /*bool*/
      if (_match_x1055) {
        return kk_std_core_types__new_Just(x, _ctx);
      }
      {
        kk_box_drop(x, _ctx);
        return kk_std_core_types__new_Nothing(_ctx);
      }
    }
  }
  {
    kk_integer_drop(n, _ctx);
    return kk_std_core_types__new_Nothing(_ctx);
  }
}
 
// monadic lift

bool kk_std_core_list__mlift_all_10308(kk_function_t predicate, kk_std_core_types__list xx, bool _y_x10244, kk_context_t* _ctx) { /* forall<a,e> (predicate : (a) -> e bool, xx : list<a>, bool) -> e bool */ 
  if (_y_x10244) {
    return kk_std_core_list_all(xx, predicate, _ctx);
  }
  {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(predicate, _ctx);
    return false;
  }
}
 
// Do all elements satisfy a predicate ?


// lift anonymous function
struct kk_std_core_list_all_fun1672__t {
  struct kk_function_s _base;
  kk_function_t predicate_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_all_fun1672(kk_function_t _fself, kk_box_t _b_x1014, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_all_fun1672(kk_function_t predicate_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_all_fun1672__t* _self = kk_function_alloc_as(struct kk_std_core_list_all_fun1672__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_all_fun1672, kk_context());
  _self->predicate_0 = predicate_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_all_fun1672(kk_function_t _fself, kk_box_t _b_x1014, kk_context_t* _ctx) {
  struct kk_std_core_list_all_fun1672__t* _self = kk_function_as(struct kk_std_core_list_all_fun1672__t*, _fself, _ctx);
  kk_function_t predicate_0 = _self->predicate_0; /* (5562) -> 5563 bool */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<5562> */
  kk_drop_match(_self, {kk_function_dup(predicate_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10244_0_1016 = kk_bool_unbox(_b_x1014); /*bool*/;
  bool _x_x1673 = kk_std_core_list__mlift_all_10308(predicate_0, xx_0, _y_x10244_0_1016, _ctx); /*bool*/
  return kk_bool_box(_x_x1673);
}

bool kk_std_core_list_all(kk_std_core_types__list xs, kk_function_t predicate_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, predicate : (a) -> e bool) -> e bool */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1669 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1669->head;
    kk_std_core_types__list xx_0 = _con_x1669->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool x_0_10439;
    kk_function_t _x_x1670 = kk_function_dup(predicate_0, _ctx); /*(5562) -> 5563 bool*/
    x_0_10439 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1670, (_x_x1670, x, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x1671 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_all_fun1672(predicate_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x1671);
    }
    if (x_0_10439) { // tailcall
                     xs = xx_0;
                     goto kk__tailcall;
    }
    {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_function_drop(predicate_0, _ctx);
      return false;
    }
  }
  {
    kk_function_drop(predicate_0, _ctx);
    return true;
  }
}
 
// monadic lift

bool kk_std_core_list__mlift_any_10309(kk_function_t predicate, kk_std_core_types__list xx, bool _y_x10248, kk_context_t* _ctx) { /* forall<a,e> (predicate : (a) -> e bool, xx : list<a>, bool) -> e bool */ 
  if (_y_x10248) {
    kk_std_core_types__list_drop(xx, _ctx);
    kk_function_drop(predicate, _ctx);
    return true;
  }
  {
    return kk_std_core_list_any(xx, predicate, _ctx);
  }
}
 
// Are there any elements in a list that satisfy a predicate ?


// lift anonymous function
struct kk_std_core_list_any_fun1677__t {
  struct kk_function_s _base;
  kk_function_t predicate_0;
  kk_std_core_types__list xx_0;
};
static kk_box_t kk_std_core_list_any_fun1677(kk_function_t _fself, kk_box_t _b_x1018, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_any_fun1677(kk_function_t predicate_0, kk_std_core_types__list xx_0, kk_context_t* _ctx) {
  struct kk_std_core_list_any_fun1677__t* _self = kk_function_alloc_as(struct kk_std_core_list_any_fun1677__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_list_any_fun1677, kk_context());
  _self->predicate_0 = predicate_0;
  _self->xx_0 = xx_0;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_list_any_fun1677(kk_function_t _fself, kk_box_t _b_x1018, kk_context_t* _ctx) {
  struct kk_std_core_list_any_fun1677__t* _self = kk_function_as(struct kk_std_core_list_any_fun1677__t*, _fself, _ctx);
  kk_function_t predicate_0 = _self->predicate_0; /* (5609) -> 5610 bool */
  kk_std_core_types__list xx_0 = _self->xx_0; /* list<5609> */
  kk_drop_match(_self, {kk_function_dup(predicate_0, _ctx);kk_std_core_types__list_dup(xx_0, _ctx);}, {}, _ctx)
  bool _y_x10248_0_1020 = kk_bool_unbox(_b_x1018); /*bool*/;
  bool _x_x1678 = kk_std_core_list__mlift_any_10309(predicate_0, xx_0, _y_x10248_0_1020, _ctx); /*bool*/
  return kk_bool_box(_x_x1678);
}

bool kk_std_core_list_any(kk_std_core_types__list xs, kk_function_t predicate_0, kk_context_t* _ctx) { /* forall<a,e> (xs : list<a>, predicate : (a) -> e bool) -> e bool */ 
  kk__tailcall: ;
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1674 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t x = _con_x1674->head;
    kk_std_core_types__list xx_0 = _con_x1674->tail;
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_box_dup(x, _ctx);
      kk_std_core_types__list_dup(xx_0, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    bool x_0_10442;
    kk_function_t _x_x1675 = kk_function_dup(predicate_0, _ctx); /*(5609) -> 5610 bool*/
    x_0_10442 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_context_t*), _x_x1675, (_x_x1675, x, _ctx), _ctx); /*bool*/
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x1676 = kk_std_core_hnd_yield_extend(kk_std_core_list_new_any_fun1677(predicate_0, xx_0, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x1676);
    }
    if (x_0_10442) {
      kk_std_core_types__list_drop(xx_0, _ctx);
      kk_function_drop(predicate_0, _ctx);
      return true;
    }
    { // tailcall
      xs = xx_0;
      goto kk__tailcall;
    }
  }
  {
    kk_function_drop(predicate_0, _ctx);
    return false;
  }
}
 
// Return the sum of a list of integers


// lift anonymous function
struct kk_std_core_list_sum_fun1680__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_sum_fun1680(kk_function_t _fself, kk_box_t _b_x1024, kk_box_t _b_x1025, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_sum_fun1680(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_sum_fun1680, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_sum_fun1680(kk_function_t _fself, kk_box_t _b_x1024, kk_box_t _b_x1025, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_integer_t _x_x1681;
  kk_integer_t _x_x1682 = kk_integer_unbox(_b_x1024, _ctx); /*int*/
  kk_integer_t _x_x1683 = kk_integer_unbox(_b_x1025, _ctx); /*int*/
  _x_x1681 = kk_std_core_int__lp__plus__rp_(_x_x1682, _x_x1683, _ctx); /*int*/
  return kk_integer_box(_x_x1681, _ctx);
}

kk_integer_t kk_std_core_list_sum(kk_std_core_types__list xs, kk_context_t* _ctx) { /* (xs : list<int>) -> int */ 
  kk_box_t _x_x1679 = kk_std_core_list_foldl(xs, kk_integer_box(kk_integer_from_small(0), _ctx), kk_std_core_list_new_sum_fun1680(_ctx), _ctx); /*1192*/
  return kk_integer_unbox(_x_x1679, _ctx);
}
 
// Returns the smallest element of a list of integers (or `default` (=`0`) for the empty list)


// lift anonymous function
struct kk_std_core_list_minimum_fun1686__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_minimum_fun1686(kk_function_t _fself, kk_box_t _b_x1034, kk_box_t _b_x1035, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_minimum_fun1686(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_minimum_fun1686, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_minimum_fun1686(kk_function_t _fself, kk_box_t _b_x1034, kk_box_t _b_x1035, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_integer_t _x_x1687;
  kk_integer_t _x_x1688 = kk_integer_unbox(_b_x1034, _ctx); /*int*/
  kk_integer_t _x_x1689 = kk_integer_unbox(_b_x1035, _ctx); /*int*/
  _x_x1687 = kk_std_core_int_min(_x_x1688, _x_x1689, _ctx); /*int*/
  return kk_integer_box(_x_x1687, _ctx);
}

kk_integer_t kk_std_core_list_minimum(kk_std_core_types__list xs, kk_std_core_types__optional kkloc_default, kk_context_t* _ctx) { /* (xs : list<int>, default : ? int) -> int */ 
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    if (kk_std_core_types__is_Optional(kkloc_default, _ctx)) {
      kk_box_t _box_x1029 = kkloc_default._cons._Optional.value;
      kk_integer_t _uniq_default_5643 = kk_integer_unbox(_box_x1029, _ctx);
      kk_integer_dup(_uniq_default_5643, _ctx);
      kk_std_core_types__optional_drop(kkloc_default, _ctx);
      return _uniq_default_5643;
    }
    {
      kk_std_core_types__optional_drop(kkloc_default, _ctx);
      return kk_integer_from_small(0);
    }
  }
  {
    struct kk_std_core_types_Cons* _con_x1684 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x1030 = _con_x1684->head;
    kk_std_core_types__list xx = _con_x1684->tail;
    kk_integer_t x = kk_integer_unbox(_box_x1030, _ctx);
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_integer_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__optional_drop(kkloc_default, _ctx);
    kk_box_t _x_x1685 = kk_std_core_list_foldl(xx, kk_integer_box(x, _ctx), kk_std_core_list_new_minimum_fun1686(_ctx), _ctx); /*1192*/
    return kk_integer_unbox(_x_x1685, _ctx);
  }
}
 
// Returns the largest element of a list of integers (or `default` (=`0`) for the empty list)


// lift anonymous function
struct kk_std_core_list_maximum_fun1692__t {
  struct kk_function_s _base;
};
static kk_box_t kk_std_core_list_maximum_fun1692(kk_function_t _fself, kk_box_t _b_x1044, kk_box_t _b_x1045, kk_context_t* _ctx);
static kk_function_t kk_std_core_list_new_maximum_fun1692(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_std_core_list_maximum_fun1692, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_std_core_list_maximum_fun1692(kk_function_t _fself, kk_box_t _b_x1044, kk_box_t _b_x1045, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_integer_t _x_x1693;
  kk_integer_t _x_x1694 = kk_integer_unbox(_b_x1044, _ctx); /*int*/
  kk_integer_t _x_x1695 = kk_integer_unbox(_b_x1045, _ctx); /*int*/
  _x_x1693 = kk_std_core_int_max(_x_x1694, _x_x1695, _ctx); /*int*/
  return kk_integer_box(_x_x1693, _ctx);
}

kk_integer_t kk_std_core_list_maximum(kk_std_core_types__list xs, kk_std_core_types__optional kkloc_default, kk_context_t* _ctx) { /* (xs : list<int>, default : ? int) -> int */ 
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    if (kk_std_core_types__is_Optional(kkloc_default, _ctx)) {
      kk_box_t _box_x1039 = kkloc_default._cons._Optional.value;
      kk_integer_t _uniq_default_5677 = kk_integer_unbox(_box_x1039, _ctx);
      kk_integer_dup(_uniq_default_5677, _ctx);
      kk_std_core_types__optional_drop(kkloc_default, _ctx);
      return _uniq_default_5677;
    }
    {
      kk_std_core_types__optional_drop(kkloc_default, _ctx);
      return kk_integer_from_small(0);
    }
  }
  {
    struct kk_std_core_types_Cons* _con_x1690 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x1040 = _con_x1690->head;
    kk_std_core_types__list xx = _con_x1690->tail;
    kk_integer_t x = kk_integer_unbox(_box_x1040, _ctx);
    if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
      kk_datatype_ptr_free(xs, _ctx);
    }
    else {
      kk_integer_dup(x, _ctx);
      kk_std_core_types__list_dup(xx, _ctx);
      kk_datatype_ptr_decref(xs, _ctx);
    }
    kk_std_core_types__optional_drop(kkloc_default, _ctx);
    kk_box_t _x_x1691 = kk_std_core_list_foldl(xx, kk_integer_box(x, _ctx), kk_std_core_list_new_maximum_fun1692(_ctx), _ctx); /*1192*/
    return kk_integer_unbox(_x_x1691, _ctx);
  }
}
 
// Join a list of strings with newlines

kk_string_t kk_std_core_list_unlines(kk_std_core_types__list xs, kk_context_t* _ctx) { /* (xs : list<string>) -> string */ 
  if (kk_std_core_types__is_Nil(xs, _ctx)) {
    return kk_string_empty();
  }
  {
    struct kk_std_core_types_Cons* _con_x1699 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x1049 = _con_x1699->head;
    kk_std_core_types__list _pat_1 = _con_x1699->tail;
    if (kk_std_core_types__is_Nil(_pat_1, _ctx)) {
      kk_string_t x = kk_string_unbox(_box_x1049);
      if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
        kk_datatype_ptr_free(xs, _ctx);
      }
      else {
        kk_string_dup(x, _ctx);
        kk_datatype_ptr_decref(xs, _ctx);
      }
      return x;
    }
  }
  if (kk_std_core_types__is_Cons(xs, _ctx)) {
    struct kk_std_core_types_Cons* _con_x1700 = kk_std_core_types__as_Cons(xs, _ctx);
    kk_box_t _box_x1050 = _con_x1700->head;
    kk_std_core_types__list _pat_3 = _con_x1700->tail;
    if (kk_std_core_types__is_Cons(_pat_3, _ctx)) {
      struct kk_std_core_types_Cons* _con_x1701 = kk_std_core_types__as_Cons(_pat_3, _ctx);
      kk_box_t _box_x1051 = _con_x1701->head;
      kk_std_core_types__list _pat_4 = _con_x1701->tail;
      if (kk_std_core_types__is_Nil(_pat_4, _ctx)) {
        kk_string_t _x_x1702;
        kk_define_string_literal(, _s_x1703, 1, "\n", _ctx)
        _x_x1702 = kk_string_dup(_s_x1703, _ctx); /*string*/
        kk_string_t _x_x1704 = kk_string_empty(); /*string*/
        if (kk_string_is_eq(_x_x1702,_x_x1704,kk_context())) {
          kk_string_t x_0 = kk_string_unbox(_box_x1050);
          kk_string_t y = kk_string_unbox(_box_x1051);
          if kk_likely(kk_datatype_ptr_is_unique(xs, _ctx)) {
            if kk_likely(kk_datatype_ptr_is_unique(_pat_3, _ctx)) {
              kk_datatype_ptr_free(_pat_3, _ctx);
            }
            else {
              kk_string_dup(y, _ctx);
              kk_datatype_ptr_decref(_pat_3, _ctx);
            }
            kk_datatype_ptr_free(xs, _ctx);
          }
          else {
            kk_string_dup(x_0, _ctx);
            kk_string_dup(y, _ctx);
            kk_datatype_ptr_decref(xs, _ctx);
          }
          return kk_std_core_types__lp__plus__plus__rp_(x_0, y, _ctx);
        }
      }
    }
  }
  {
    kk_vector_t _x_x1706 = kk_std_core_vector_unvlist(xs, _ctx); /*vector<978>*/
    kk_string_t _x_x1707;
    kk_define_string_literal(, _s_x1708, 1, "\n", _ctx)
    _x_x1707 = kk_string_dup(_s_x1708, _ctx); /*string*/
    return kk_string_join_with(_x_x1706,_x_x1707,kk_context());
  }
}

// initialization
void kk_std_core_list__init(kk_context_t* _ctx){
  static bool _kk_initialized = false;
  if (_kk_initialized) return;
  _kk_initialized = true;
  kk_std_core_types__init(_ctx);
  kk_std_core_undiv__init(_ctx);
  kk_std_core_hnd__init(_ctx);
  kk_std_core_exn__init(_ctx);
  kk_std_core_char__init(_ctx);
  kk_std_core_string__init(_ctx);
  kk_std_core_int__init(_ctx);
  kk_std_core_vector__init(_ctx);
  #if defined(KK_CUSTOM_INIT)
    KK_CUSTOM_INIT (_ctx);
  #endif
}

// termination
void kk_std_core_list__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_std_core_vector__done(_ctx);
  kk_std_core_int__done(_ctx);
  kk_std_core_string__done(_ctx);
  kk_std_core_char__done(_ctx);
  kk_std_core_exn__done(_ctx);
  kk_std_core_hnd__done(_ctx);
  kk_std_core_undiv__done(_ctx);
  kk_std_core_types__done(_ctx);
}
