#pragma once
#ifndef kk_test__complete_H
#define kk_test__complete_H
// Koka generated module: test_complete, koka version: 3.2.2, platform: 64-bit
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

// type test_complete/test-eff
struct kk_test__complete__test_eff_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_test__complete__test_eff;
struct kk_test__complete__Hnd_test_eff {
  struct kk_test__complete__test_eff_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_check_auth;
  kk_std_core_hnd__clause0 _fun_get_level;
};
static inline kk_test__complete__test_eff kk_test__complete__base_Hnd_test_eff(struct kk_test__complete__Hnd_test_eff* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_test__complete__test_eff kk_test__complete__new_Hnd_test_eff(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_check_auth, kk_std_core_hnd__clause0 _fun_get_level, kk_context_t* _ctx) {
  struct kk_test__complete__Hnd_test_eff* _con = kk_block_alloc_at_as(struct kk_test__complete__Hnd_test_eff, _at, 3 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_check_auth = _fun_check_auth;
  _con->_fun_get_level = _fun_get_level;
  return kk_test__complete__base_Hnd_test_eff(_con, _ctx);
}
static inline struct kk_test__complete__Hnd_test_eff* kk_test__complete__as_Hnd_test_eff(kk_test__complete__test_eff x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_test__complete__Hnd_test_eff*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_test__complete__is_Hnd_test_eff(kk_test__complete__test_eff x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_test__complete__test_eff kk_test__complete__test_eff_dup(kk_test__complete__test_eff _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_test__complete__test_eff_drop(kk_test__complete__test_eff _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_test__complete__test_eff_box(kk_test__complete__test_eff _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_test__complete__test_eff kk_test__complete__test_eff_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// value declarations
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:test-eff` type.

static inline kk_integer_t kk_test__complete_test_eff_fs__cfc(kk_test__complete__test_eff _this, kk_context_t* _ctx) { /* forall<e,a> (test-eff<e,a>) -> int */ 
  {
    struct kk_test__complete__Hnd_test_eff* _con_x29 = kk_test__complete__as_Hnd_test_eff(_this, _ctx);
    kk_integer_t _x = _con_x29->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_test__complete_test_eff_fs__tag;

kk_box_t kk_test__complete_test_eff_fs__handle(kk_test__complete__test_eff hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : test-eff<e,b>, ret : (res : a) -> e b, action : () -> <test-eff|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-check-auth` constructor field of the `:test-eff` type.

static inline kk_std_core_hnd__clause1 kk_test__complete_test_eff_fs__fun_check_auth(kk_test__complete__test_eff _this, kk_context_t* _ctx) { /* forall<e,a> (test-eff<e,a>) -> hnd/clause1<string,bool,test-eff,e,a> */ 
  {
    struct kk_test__complete__Hnd_test_eff* _con_x33 = kk_test__complete__as_Hnd_test_eff(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x33->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `check-auth` operation out of effect `:test-eff`

static inline kk_std_core_hnd__clause1 kk_test__complete_check_auth_fs__select(kk_test__complete__test_eff hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : test-eff<e,a>) -> hnd/clause1<string,bool,test-eff,e,a> */ 
  {
    struct kk_test__complete__Hnd_test_eff* _con_x34 = kk_test__complete__as_Hnd_test_eff(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_check_auth = _con_x34->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
  }
}
 
// Call the `fun check-auth` operation of the effect `:test-eff`

static inline bool kk_test__complete_check_auth(kk_string_t x, kk_context_t* _ctx) { /* (x : string) -> test-eff bool */ 
  kk_std_core_hnd__ev ev_10006 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_complete/test-eff>*/;
  kk_box_t _x_x35;
  {
    struct kk_std_core_hnd_Ev* _con_x36 = kk_std_core_hnd__as_Ev(ev_10006, _ctx);
    kk_box_t _box_x8 = _con_x36->hnd;
    int32_t m = _con_x36->marker;
    kk_test__complete__test_eff h_0 = kk_test__complete__test_eff_unbox(_box_x8, KK_BORROWED, _ctx);
    kk_test__complete__test_eff_dup(h_0, _ctx);
    {
      struct kk_test__complete__Hnd_test_eff* _con_x37 = kk_test__complete__as_Hnd_test_eff(h_0, _ctx);
      kk_integer_t _pat_0_0 = _con_x37->_cfc;
      kk_std_core_hnd__clause1 _fun_check_auth = _con_x37->_fun_check_auth;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x37->_fun_get_level;
      if kk_likely(kk_datatype_ptr_is_unique(h_0, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h_0, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
        kk_datatype_ptr_decref(h_0, _ctx);
      }
      {
        kk_function_t _fun_unbox_x12 = _fun_check_auth.clause;
        _x_x35 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x12, (_fun_unbox_x12, m, ev_10006, kk_string_box(x), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_bool_unbox(_x_x35);
}
 
// Automatically generated. Retrieves the `@fun-get-level` constructor field of the `:test-eff` type.

static inline kk_std_core_hnd__clause0 kk_test__complete_test_eff_fs__fun_get_level(kk_test__complete__test_eff _this, kk_context_t* _ctx) { /* forall<e,a> (test-eff<e,a>) -> hnd/clause0<int,test-eff,e,a> */ 
  {
    struct kk_test__complete__Hnd_test_eff* _con_x38 = kk_test__complete__as_Hnd_test_eff(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x38->_fun_get_level;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `get-level` operation out of effect `:test-eff`

static inline kk_std_core_hnd__clause0 kk_test__complete_get_level_fs__select(kk_test__complete__test_eff hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : test-eff<e,a>) -> hnd/clause0<int,test-eff,e,a> */ 
  {
    struct kk_test__complete__Hnd_test_eff* _con_x39 = kk_test__complete__as_Hnd_test_eff(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_get_level = _con_x39->_fun_get_level;
    return kk_std_core_hnd__clause0_dup(_fun_get_level, _ctx);
  }
}
 
// Call the `fun get-level` operation of the effect `:test-eff`

static inline kk_integer_t kk_test__complete_get_level(kk_context_t* _ctx) { /* () -> test-eff int */ 
  kk_std_core_hnd__ev ev_10009 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_complete/test-eff>*/;
  kk_box_t _x_x40;
  {
    struct kk_std_core_hnd_Ev* _con_x41 = kk_std_core_hnd__as_Ev(ev_10009, _ctx);
    kk_box_t _box_x16 = _con_x41->hnd;
    int32_t m = _con_x41->marker;
    kk_test__complete__test_eff h_0 = kk_test__complete__test_eff_unbox(_box_x16, KK_BORROWED, _ctx);
    kk_test__complete__test_eff_dup(h_0, _ctx);
    {
      struct kk_test__complete__Hnd_test_eff* _con_x42 = kk_test__complete__as_Hnd_test_eff(h_0, _ctx);
      kk_integer_t _pat_0_0 = _con_x42->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x42->_fun_check_auth;
      kk_std_core_hnd__clause0 _fun_get_level = _con_x42->_fun_get_level;
      if kk_likely(kk_datatype_ptr_is_unique(h_0, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h_0, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_get_level, _ctx);
        kk_datatype_ptr_decref(h_0, _ctx);
      }
      {
        kk_function_t _fun_unbox_x19 = _fun_get_level.clause;
        _x_x40 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x19, (_fun_unbox_x19, m, ev_10009, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_integer_unbox(_x_x40, _ctx);
}

extern kk_function_t kk_test__complete_h;

static inline kk_unit_t kk_test__complete_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t _x_x57;
  kk_define_string_literal(, _s_x58, 2, "ok", _ctx)
  _x_x57 = kk_string_dup(_s_x58, _ctx); /*string*/
  kk_std_core_console_printsln(_x_x57, _ctx); return kk_Unit;
}

void kk_test__complete__init(kk_context_t* _ctx);


void kk_test__complete__done(kk_context_t* _ctx);

#endif // header
