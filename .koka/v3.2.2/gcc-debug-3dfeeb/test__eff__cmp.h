#pragma once
#ifndef kk_test__eff__cmp_H
#define kk_test__eff__cmp_H
// Koka generated module: test_eff_cmp, koka version: 3.2.2, platform: 64-bit
#include <kklib.h>
#include "std_core_types.h"
#include "std_core_hnd.h"
#include "std_core_exn.h"
#include "std_core_bool.h"
#include "std_core_order.h"
#include "std_core_char.h"
#include "std_core_int.h"
#include "std_core_vector.h"
#include "std_core_string.h"
#include "std_core_sslice.h"
#include "std_core_list.h"
#include "std_core_maybe.h"
#include "std_core_maybe2.h"
#include "std_core_either.h"
#include "std_core_tuple.h"
#include "std_core_lazy.h"
#include "std_core_show.h"
#include "std_core_debug.h"
#include "std_core_delayed.h"
#include "std_core_console.h"
#include "std_core.h"

// type declarations

// type test_eff_cmp/eff1
struct kk_test__eff__cmp__eff1_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_test__eff__cmp__eff1;
struct kk_test__eff__cmp__Hnd_eff1 {
  struct kk_test__eff__cmp__eff1_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause0 _fun_op1;
};
static inline kk_test__eff__cmp__eff1 kk_test__eff__cmp__base_Hnd_eff1(struct kk_test__eff__cmp__Hnd_eff1* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_test__eff__cmp__eff1 kk_test__eff__cmp__new_Hnd_eff1(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause0 _fun_op1, kk_context_t* _ctx) {
  struct kk_test__eff__cmp__Hnd_eff1* _con = kk_block_alloc_at_as(struct kk_test__eff__cmp__Hnd_eff1, _at, 2 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_op1 = _fun_op1;
  return kk_test__eff__cmp__base_Hnd_eff1(_con, _ctx);
}
static inline struct kk_test__eff__cmp__Hnd_eff1* kk_test__eff__cmp__as_Hnd_eff1(kk_test__eff__cmp__eff1 x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_test__eff__cmp__Hnd_eff1*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_test__eff__cmp__is_Hnd_eff1(kk_test__eff__cmp__eff1 x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_test__eff__cmp__eff1 kk_test__eff__cmp__eff1_dup(kk_test__eff__cmp__eff1 _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_test__eff__cmp__eff1_drop(kk_test__eff__cmp__eff1 _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_test__eff__cmp__eff1_box(kk_test__eff__cmp__eff1 _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_test__eff__cmp__eff1 kk_test__eff__cmp__eff1_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// value declarations
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:eff1` type.

static inline kk_integer_t kk_test__eff__cmp_eff1_fs__cfc(kk_test__eff__cmp__eff1 eff1, kk_context_t* _ctx) { /* forall<e,a> (eff1 : eff1<e,a>) -> int */ 
  {
    struct kk_test__eff__cmp__Hnd_eff1* _con_x16 = kk_test__eff__cmp__as_Hnd_eff1(eff1, _ctx);
    kk_integer_t _x = _con_x16->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_test__eff__cmp_eff1_fs__tag;

kk_box_t kk_test__eff__cmp_eff1_fs__handle(kk_test__eff__cmp__eff1 hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : eff1<e,b>, ret : (res : a) -> e b, action : () -> <eff1|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-op1` constructor field of the `:eff1` type.

static inline kk_std_core_hnd__clause0 kk_test__eff__cmp_eff1_fs__fun_op1(kk_test__eff__cmp__eff1 eff1, kk_context_t* _ctx) { /* forall<e,a> (eff1 : eff1<e,a>) -> hnd/clause0<bool,eff1,e,a> */ 
  {
    struct kk_test__eff__cmp__Hnd_eff1* _con_x20 = kk_test__eff__cmp__as_Hnd_eff1(eff1, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x20->_fun_op1;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `op1` operation out of effect `:eff1`

static inline kk_std_core_hnd__clause0 kk_test__eff__cmp_op1_fs__select(kk_test__eff__cmp__eff1 hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : eff1<e,a>) -> hnd/clause0<bool,eff1,e,a> */ 
  {
    struct kk_test__eff__cmp__Hnd_eff1* _con_x21 = kk_test__eff__cmp__as_Hnd_eff1(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_op1 = _con_x21->_fun_op1;
    return kk_std_core_hnd__clause0_dup(_fun_op1, _ctx);
  }
}
 
// Call the `fun op1` operation of the effect `:eff1`

static inline bool kk_test__eff__cmp_op1(kk_context_t* _ctx) { /* () -> eff1 bool */ 
  kk_std_core_hnd__ev ev_10004 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_eff_cmp/eff1>*/;
  kk_box_t _x_x22;
  {
    struct kk_std_core_hnd_Ev* _con_x23 = kk_std_core_hnd__as_Ev(ev_10004, _ctx);
    kk_box_t _box_x8 = _con_x23->hnd;
    int32_t m = _con_x23->marker;
    kk_test__eff__cmp__eff1 h = kk_test__eff__cmp__eff1_unbox(_box_x8, KK_BORROWED, _ctx);
    kk_test__eff__cmp__eff1_dup(h, _ctx);
    {
      struct kk_test__eff__cmp__Hnd_eff1* _con_x24 = kk_test__eff__cmp__as_Hnd_eff1(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x24->_cfc;
      kk_std_core_hnd__clause0 _fun_op1 = _con_x24->_fun_op1;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_op1, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x11 = _fun_op1.clause;
        _x_x22 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x11, (_fun_unbox_x11, m, ev_10004, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_bool_unbox(_x_x22);
}

static inline bool kk_test__eff__cmp_test(kk_integer_t n, kk_context_t* _ctx) { /* (n : int) -> eff1 bool */ 
  bool _brw_x14 = kk_integer_lt_borrow(n,(kk_integer_from_small(0)),kk_context()); /*bool*/;
  kk_integer_drop(n, _ctx);
  return _brw_x14;
}

static inline kk_unit_t kk_test__eff__cmp_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t _x_x25;
  kk_define_string_literal(, _s_x26, 2, "ok", _ctx)
  _x_x25 = kk_string_dup(_s_x26, _ctx); /*string*/
  kk_std_core_console_printsln(_x_x25, _ctx); return kk_Unit;
}

void kk_test__eff__cmp__init(kk_context_t* _ctx);


void kk_test__eff__cmp__done(kk_context_t* _ctx);

#endif // header
