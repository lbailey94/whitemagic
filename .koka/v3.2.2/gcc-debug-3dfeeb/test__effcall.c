// Koka generated module: test_effcall, koka version: 3.2.2, platform: 64-bit
#include "test__effcall.h"
 
// runtime tag for the effect `:prat-auth`

kk_std_core_hnd__htag kk_test__effcall_prat_auth_fs__tag;
 
// handler for the effect `:prat-auth`

kk_box_t kk_test__effcall_prat_auth_fs__handle(kk_test__effcall__prat_auth hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,b> (hnd : prat-auth<e,b>, ret : (res : a) -> e b, action : () -> <prat-auth|e> a) -> e b */ 
  kk_std_core_hnd__htag _x_x47 = kk_std_core_hnd__htag_dup(kk_test__effcall_prat_auth_fs__tag, _ctx); /*hnd/htag<test_effcall/prat-auth>*/
  return kk_std_core_hnd__hhandle(_x_x47, kk_test__effcall__prat_auth_box(hnd, _ctx), ret, action, _ctx);
}
 
// monadic lift


// lift anonymous function
struct kk_test__effcall__mlift_test_10007_fun54__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__effcall__mlift_test_10007_fun54(kk_function_t _fself, kk_box_t _b_x18, kk_context_t* _ctx);
static kk_function_t kk_test__effcall__new_mlift_test_10007_fun54(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__effcall__mlift_test_10007_fun54, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__effcall__mlift_test_10007_fun54(kk_function_t _fself, kk_box_t _b_x18, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  bool _x_x55;
  bool b_21 = kk_bool_unbox(_b_x18); /*bool*/;
  if (b_21) {
    _x_x55 = false; /*bool*/
  }
  else {
    _x_x55 = true; /*bool*/
  }
  return kk_bool_box(_x_x55);
}

kk_string_t kk_test__effcall__mlift_test_10007(bool _y_x10004, kk_context_t* _ctx) { /* (bool) -> prat-auth string */ 
  bool _match_x41;
  kk_box_t _x_x53 = kk_std_core_hnd__open_none1(kk_test__effcall__new_mlift_test_10007_fun54(_ctx), kk_bool_box(_y_x10004), _ctx); /*10001*/
  _match_x41 = kk_bool_unbox(_x_x53); /*bool*/
  if (_match_x41) {
    kk_define_string_literal(, _s_x56, 2, "no", _ctx)
    return kk_string_dup(_s_x56, _ctx);
  }
  {
    kk_define_string_literal(, _s_x57, 3, "yes", _ctx)
    return kk_string_dup(_s_x57, _ctx);
  }
}


// lift anonymous function
struct kk_test__effcall_test_fun65__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__effcall_test_fun65(kk_function_t _fself, kk_box_t _b_x31, kk_context_t* _ctx);
static kk_function_t kk_test__effcall_new_test_fun65(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__effcall_test_fun65, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__effcall_test_fun65(kk_function_t _fself, kk_box_t _b_x31, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x66;
  bool _x_x67 = kk_bool_unbox(_b_x31); /*bool*/
  _x_x66 = kk_test__effcall__mlift_test_10007(_x_x67, _ctx); /*string*/
  return kk_string_box(_x_x66);
}


// lift anonymous function
struct kk_test__effcall_test_fun69__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__effcall_test_fun69(kk_function_t _fself, kk_box_t _b_x34, kk_context_t* _ctx);
static kk_function_t kk_test__effcall_new_test_fun69(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__effcall_test_fun69, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__effcall_test_fun69(kk_function_t _fself, kk_box_t _b_x34, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  bool _x_x70;
  bool b_38 = kk_bool_unbox(_b_x34); /*bool*/;
  if (b_38) {
    _x_x70 = false; /*bool*/
  }
  else {
    _x_x70 = true; /*bool*/
  }
  return kk_bool_box(_x_x70);
}

kk_string_t kk_test__effcall_test(kk_context_t* _ctx) { /* () -> prat-auth string */ 
  kk_std_core_hnd__ev ev_10015 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_effcall/prat-auth>*/;
  bool x_10012;
  kk_box_t _x_x58;
  {
    struct kk_std_core_hnd_Ev* _con_x59 = kk_std_core_hnd__as_Ev(ev_10015, _ctx);
    kk_box_t _box_x22 = _con_x59->hnd;
    int32_t m = _con_x59->marker;
    kk_test__effcall__prat_auth h = kk_test__effcall__prat_auth_unbox(_box_x22, KK_BORROWED, _ctx);
    kk_test__effcall__prat_auth_dup(h, _ctx);
    {
      struct kk_test__effcall__Hnd_prat_auth* _con_x60 = kk_test__effcall__as_Hnd_prat_auth(h, _ctx);
      kk_integer_t _pat_0 = _con_x60->_cfc;
      kk_std_core_hnd__clause1 _fun_check_auth = _con_x60->_fun_check_auth;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_integer_drop(_pat_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x26 = _fun_check_auth.clause;
        kk_box_t _x_x61;
        kk_string_t _x_x62;
        kk_define_string_literal(, _s_x63, 5, "hello", _ctx)
        _x_x62 = kk_string_dup(_s_x63, _ctx); /*string*/
        _x_x61 = kk_string_box(_x_x62); /*10009*/
        _x_x58 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x26, (_fun_unbox_x26, m, ev_10015, _x_x61, _ctx), _ctx); /*10010*/
      }
    }
  }
  x_10012 = kk_bool_unbox(_x_x58); /*bool*/
  if (kk_yielding(kk_context())) {
    kk_box_t _x_x64 = kk_std_core_hnd_yield_extend(kk_test__effcall_new_test_fun65(_ctx), _ctx); /*10001*/
    return kk_string_unbox(_x_x64);
  }
  {
    bool _match_x40;
    kk_box_t _x_x68 = kk_std_core_hnd__open_none1(kk_test__effcall_new_test_fun69(_ctx), kk_bool_box(x_10012), _ctx); /*10001*/
    _match_x40 = kk_bool_unbox(_x_x68); /*bool*/
    if (_match_x40) {
      kk_define_string_literal(, _s_x71, 2, "no", _ctx)
      return kk_string_dup(_s_x71, _ctx);
    }
    {
      kk_define_string_literal(, _s_x72, 3, "yes", _ctx)
      return kk_string_dup(_s_x72, _ctx);
    }
  }
}

// initialization
void kk_test__effcall__init(kk_context_t* _ctx){
  static bool _kk_initialized = false;
  if (_kk_initialized) return;
  _kk_initialized = true;
  kk_std_core_types__init(_ctx);
  kk_std_core_hnd__init(_ctx);
  kk_std_core_exn__init(_ctx);
  kk_std_core_bool__init(_ctx);
  kk_std_core_order__init(_ctx);
  kk_std_core_char__init(_ctx);
  kk_std_core_int__init(_ctx);
  kk_std_core_vector__init(_ctx);
  kk_std_core_string__init(_ctx);
  kk_std_core_sslice__init(_ctx);
  kk_std_core_list__init(_ctx);
  kk_std_core_maybe__init(_ctx);
  kk_std_core_maybe2__init(_ctx);
  kk_std_core_either__init(_ctx);
  kk_std_core_tuple__init(_ctx);
  kk_std_core_lazy__init(_ctx);
  kk_std_core_show__init(_ctx);
  kk_std_core_debug__init(_ctx);
  kk_std_core_delayed__init(_ctx);
  kk_std_core_console__init(_ctx);
  kk_std_core__init(_ctx);
  #if defined(KK_CUSTOM_INIT)
    KK_CUSTOM_INIT (_ctx);
  #endif
  {
    kk_string_t _x_x45;
    kk_define_string_literal(, _s_x46, 22, "prat-auth@test_effcall", _ctx)
    _x_x45 = kk_string_dup(_s_x46, _ctx); /*string*/
    kk_test__effcall_prat_auth_fs__tag = kk_std_core_hnd__new_Htag(_x_x45, _ctx); /*hnd/htag<test_effcall/prat-auth>*/
  }
}

// termination
void kk_test__effcall__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_std_core_hnd__htag_drop(kk_test__effcall_prat_auth_fs__tag, _ctx);
  kk_std_core__done(_ctx);
  kk_std_core_console__done(_ctx);
  kk_std_core_delayed__done(_ctx);
  kk_std_core_debug__done(_ctx);
  kk_std_core_show__done(_ctx);
  kk_std_core_lazy__done(_ctx);
  kk_std_core_tuple__done(_ctx);
  kk_std_core_either__done(_ctx);
  kk_std_core_maybe2__done(_ctx);
  kk_std_core_maybe__done(_ctx);
  kk_std_core_list__done(_ctx);
  kk_std_core_sslice__done(_ctx);
  kk_std_core_string__done(_ctx);
  kk_std_core_vector__done(_ctx);
  kk_std_core_int__done(_ctx);
  kk_std_core_char__done(_ctx);
  kk_std_core_order__done(_ctx);
  kk_std_core_bool__done(_ctx);
  kk_std_core_exn__done(_ctx);
  kk_std_core_hnd__done(_ctx);
  kk_std_core_types__done(_ctx);
}
