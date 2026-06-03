#pragma once
#ifndef kk_test__handler2_H
#define kk_test__handler2_H
// Koka generated module: test_handler2, koka version: 3.2.2, platform: 64-bit
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

// type test_handler2/test-eff
struct kk_test__handler2__test_eff_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_test__handler2__test_eff;
struct kk_test__handler2__Hnd_test_eff {
  struct kk_test__handler2__test_eff_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_check_auth;
};
static inline kk_test__handler2__test_eff kk_test__handler2__base_Hnd_test_eff(struct kk_test__handler2__Hnd_test_eff* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_test__handler2__test_eff kk_test__handler2__new_Hnd_test_eff(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_check_auth, kk_context_t* _ctx) {
  struct kk_test__handler2__Hnd_test_eff* _con = kk_block_alloc_at_as(struct kk_test__handler2__Hnd_test_eff, _at, 2 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_check_auth = _fun_check_auth;
  return kk_test__handler2__base_Hnd_test_eff(_con, _ctx);
}
static inline struct kk_test__handler2__Hnd_test_eff* kk_test__handler2__as_Hnd_test_eff(kk_test__handler2__test_eff x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_test__handler2__Hnd_test_eff*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_test__handler2__is_Hnd_test_eff(kk_test__handler2__test_eff x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_test__handler2__test_eff kk_test__handler2__test_eff_dup(kk_test__handler2__test_eff _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_test__handler2__test_eff_drop(kk_test__handler2__test_eff _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_test__handler2__test_eff_box(kk_test__handler2__test_eff _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_test__handler2__test_eff kk_test__handler2__test_eff_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// value declarations
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:test-eff` type.

static inline kk_integer_t kk_test__handler2_test_eff_fs__cfc(kk_test__handler2__test_eff _this, kk_context_t* _ctx) { /* forall<e,a> (test-eff<e,a>) -> int */ 
  {
    struct kk_test__handler2__Hnd_test_eff* _con_x20 = kk_test__handler2__as_Hnd_test_eff(_this, _ctx);
    kk_integer_t _x = _con_x20->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_test__handler2_test_eff_fs__tag;

kk_box_t kk_test__handler2_test_eff_fs__handle(kk_test__handler2__test_eff hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : test-eff<e,b>, ret : (res : a) -> e b, action : () -> <test-eff|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-check-auth` constructor field of the `:test-eff` type.

static inline kk_std_core_hnd__clause1 kk_test__handler2_test_eff_fs__fun_check_auth(kk_test__handler2__test_eff _this, kk_context_t* _ctx) { /* forall<e,a> (test-eff<e,a>) -> hnd/clause1<string,bool,test-eff,e,a> */ 
  {
    struct kk_test__handler2__Hnd_test_eff* _con_x24 = kk_test__handler2__as_Hnd_test_eff(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x24->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `check-auth` operation out of effect `:test-eff`

static inline kk_std_core_hnd__clause1 kk_test__handler2_check_auth_fs__select(kk_test__handler2__test_eff hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : test-eff<e,a>) -> hnd/clause1<string,bool,test-eff,e,a> */ 
  {
    struct kk_test__handler2__Hnd_test_eff* _con_x25 = kk_test__handler2__as_Hnd_test_eff(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_check_auth = _con_x25->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
  }
}
 
// Call the `fun check-auth` operation of the effect `:test-eff`

static inline bool kk_test__handler2_check_auth(kk_string_t x, kk_context_t* _ctx) { /* (x : string) -> test-eff bool */ 
  kk_std_core_hnd__ev ev_10004 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_handler2/test-eff>*/;
  kk_box_t _x_x26;
  {
    struct kk_std_core_hnd_Ev* _con_x27 = kk_std_core_hnd__as_Ev(ev_10004, _ctx);
    kk_box_t _box_x8 = _con_x27->hnd;
    int32_t m = _con_x27->marker;
    kk_test__handler2__test_eff h_0 = kk_test__handler2__test_eff_unbox(_box_x8, KK_BORROWED, _ctx);
    kk_test__handler2__test_eff_dup(h_0, _ctx);
    {
      struct kk_test__handler2__Hnd_test_eff* _con_x28 = kk_test__handler2__as_Hnd_test_eff(h_0, _ctx);
      kk_integer_t _pat_0_0 = _con_x28->_cfc;
      kk_std_core_hnd__clause1 _fun_check_auth = _con_x28->_fun_check_auth;
      if kk_likely(kk_datatype_ptr_is_unique(h_0, _ctx)) {
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h_0, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
        kk_datatype_ptr_decref(h_0, _ctx);
      }
      {
        kk_function_t _fun_unbox_x12 = _fun_check_auth.clause;
        _x_x26 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x12, (_fun_unbox_x12, m, ev_10004, kk_string_box(x), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_bool_unbox(_x_x26);
}

extern kk_function_t kk_test__handler2_h;

void kk_test__handler2__init(kk_context_t* _ctx);


void kk_test__handler2__done(kk_context_t* _ctx);

#endif // header
