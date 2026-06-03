#pragma once
#ifndef kk_test__effcall_H
#define kk_test__effcall_H
// Koka generated module: test_effcall, koka version: 3.2.2, platform: 64-bit
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

// type test_effcall/prat-auth
struct kk_test__effcall__prat_auth_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_test__effcall__prat_auth;
struct kk_test__effcall__Hnd_prat_auth {
  struct kk_test__effcall__prat_auth_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_check_auth;
};
static inline kk_test__effcall__prat_auth kk_test__effcall__base_Hnd_prat_auth(struct kk_test__effcall__Hnd_prat_auth* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_test__effcall__prat_auth kk_test__effcall__new_Hnd_prat_auth(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_check_auth, kk_context_t* _ctx) {
  struct kk_test__effcall__Hnd_prat_auth* _con = kk_block_alloc_at_as(struct kk_test__effcall__Hnd_prat_auth, _at, 2 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_check_auth = _fun_check_auth;
  return kk_test__effcall__base_Hnd_prat_auth(_con, _ctx);
}
static inline struct kk_test__effcall__Hnd_prat_auth* kk_test__effcall__as_Hnd_prat_auth(kk_test__effcall__prat_auth x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_test__effcall__Hnd_prat_auth*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_test__effcall__is_Hnd_prat_auth(kk_test__effcall__prat_auth x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_test__effcall__prat_auth kk_test__effcall__prat_auth_dup(kk_test__effcall__prat_auth _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_test__effcall__prat_auth_drop(kk_test__effcall__prat_auth _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_test__effcall__prat_auth_box(kk_test__effcall__prat_auth _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_test__effcall__prat_auth kk_test__effcall__prat_auth_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// value declarations
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:prat-auth` type.

static inline kk_integer_t kk_test__effcall_prat_auth_fs__cfc(kk_test__effcall__prat_auth _this, kk_context_t* _ctx) { /* forall<e,a> (prat-auth<e,a>) -> int */ 
  {
    struct kk_test__effcall__Hnd_prat_auth* _con_x44 = kk_test__effcall__as_Hnd_prat_auth(_this, _ctx);
    kk_integer_t _x = _con_x44->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_test__effcall_prat_auth_fs__tag;

kk_box_t kk_test__effcall_prat_auth_fs__handle(kk_test__effcall__prat_auth hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : prat-auth<e,b>, ret : (res : a) -> e b, action : () -> <prat-auth|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-check-auth` constructor field of the `:prat-auth` type.

static inline kk_std_core_hnd__clause1 kk_test__effcall_prat_auth_fs__fun_check_auth(kk_test__effcall__prat_auth _this, kk_context_t* _ctx) { /* forall<e,a> (prat-auth<e,a>) -> hnd/clause1<string,bool,prat-auth,e,a> */ 
  {
    struct kk_test__effcall__Hnd_prat_auth* _con_x48 = kk_test__effcall__as_Hnd_prat_auth(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x48->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `check-auth` operation out of effect `:prat-auth`

static inline kk_std_core_hnd__clause1 kk_test__effcall_check_auth_fs__select(kk_test__effcall__prat_auth hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-auth<e,a>) -> hnd/clause1<string,bool,prat-auth,e,a> */ 
  {
    struct kk_test__effcall__Hnd_prat_auth* _con_x49 = kk_test__effcall__as_Hnd_prat_auth(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_check_auth = _con_x49->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
  }
}
 
// Call the `fun check-auth` operation of the effect `:prat-auth`

static inline bool kk_test__effcall_check_auth(kk_string_t x, kk_context_t* _ctx) { /* (x : string) -> prat-auth bool */ 
  kk_std_core_hnd__ev ev_10009 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_effcall/prat-auth>*/;
  kk_box_t _x_x50;
  {
    struct kk_std_core_hnd_Ev* _con_x51 = kk_std_core_hnd__as_Ev(ev_10009, _ctx);
    kk_box_t _box_x8 = _con_x51->hnd;
    int32_t m = _con_x51->marker;
    kk_test__effcall__prat_auth h = kk_test__effcall__prat_auth_unbox(_box_x8, KK_BORROWED, _ctx);
    kk_test__effcall__prat_auth_dup(h, _ctx);
    {
      struct kk_test__effcall__Hnd_prat_auth* _con_x52 = kk_test__effcall__as_Hnd_prat_auth(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x52->_cfc;
      kk_std_core_hnd__clause1 _fun_check_auth = _con_x52->_fun_check_auth;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x12 = _fun_check_auth.clause;
        _x_x50 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x12, (_fun_unbox_x12, m, ev_10009, kk_string_box(x), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_bool_unbox(_x_x50);
}

kk_string_t kk_test__effcall__mlift_test_10007(bool _y_x10004, kk_context_t* _ctx); /* (bool) -> prat-auth string */ 

kk_string_t kk_test__effcall_test(kk_context_t* _ctx); /* () -> prat-auth string */ 

static inline kk_unit_t kk_test__effcall_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t _x_x73;
  kk_define_string_literal(, _s_x74, 2, "ok", _ctx)
  _x_x73 = kk_string_dup(_s_x74, _ctx); /*string*/
  kk_std_core_console_printsln(_x_x73, _ctx); return kk_Unit;
}

void kk_test__effcall__init(kk_context_t* _ctx);


void kk_test__effcall__done(kk_context_t* _ctx);

#endif // header
