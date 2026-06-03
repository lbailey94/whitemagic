// Koka generated module: test_exn, koka version: 3.2.2, platform: 64-bit
#include "test__exn.h"
 
// runtime tag for the effect `:eff1`

kk_std_core_hnd__htag kk_test__exn_eff1_fs__tag;
 
// handler for the effect `:eff1`

kk_box_t kk_test__exn_eff1_fs__handle(kk_test__exn__eff1 hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,b> (hnd : eff1<e,b>, ret : (res : a) -> e b, action : () -> <eff1|e> a) -> e b */ 
  kk_std_core_hnd__htag _x_x75 = kk_std_core_hnd__htag_dup(kk_test__exn_eff1_fs__tag, _ctx); /*hnd/htag<test_exn/eff1>*/
  return kk_std_core_hnd__hhandle(_x_x75, kk_test__exn__eff1_box(hnd, _ctx), ret, action, _ctx);
}
 
// monadic lift


// lift anonymous function
struct kk_test__exn__mlift_test_10013_fun82__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__exn__mlift_test_10013_fun82(kk_function_t _fself, kk_box_t _b_x16, kk_context_t* _ctx);
static kk_function_t kk_test__exn__new_mlift_test_10013_fun82(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__exn__mlift_test_10013_fun82, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__exn__mlift_test_10013_fun82(kk_function_t _fself, kk_box_t _b_x16, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  bool _x_x83;
  bool b_33 = kk_bool_unbox(_b_x16); /*bool*/;
  if (b_33) {
    _x_x83 = false; /*bool*/
  }
  else {
    _x_x83 = true; /*bool*/
  }
  return kk_bool_box(_x_x83);
}


// lift anonymous function
struct kk_test__exn__mlift_test_10013_fun85__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__exn__mlift_test_10013_fun85(kk_function_t _fself, kk_box_t _b_x23, kk_box_t _b_x24, kk_context_t* _ctx);
static kk_function_t kk_test__exn__new_mlift_test_10013_fun85(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__exn__mlift_test_10013_fun85, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__exn__mlift_test_10013_fun85(kk_function_t _fself, kk_box_t _b_x23, kk_box_t _b_x24, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _b_x17_31 = kk_string_unbox(_b_x23); /*string*/;
  kk_std_core_types__optional _b_x18_32 = kk_std_core_types__optional_unbox(_b_x24, KK_OWNED, _ctx); /*? exception-info*/;
  return kk_std_core_exn_throw(_b_x17_31, _b_x18_32, _ctx);
}

kk_string_t kk_test__exn__mlift_test_10013(bool _y_x10004, kk_context_t* _ctx) { /* (bool) -> <eff1,exn> string */ 
  bool _match_x69;
  kk_box_t _x_x81 = kk_std_core_hnd__open_none1(kk_test__exn__new_mlift_test_10013_fun82(_ctx), kk_bool_box(_y_x10004), _ctx); /*10001*/
  _match_x69 = kk_bool_unbox(_x_x81); /*bool*/
  if (_match_x69) {
    kk_ssize_t _b_x19_27 = (KK_IZ(1)); /*hnd/ev-index*/;
    kk_box_t _x_x84;
    kk_box_t _x_x86;
    kk_string_t _x_x87;
    kk_define_string_literal(, _s_x88, 5, "error", _ctx)
    _x_x87 = kk_string_dup(_s_x88, _ctx); /*string*/
    _x_x86 = kk_string_box(_x_x87); /*10000*/
    _x_x84 = kk_std_core_hnd__open_at2(_b_x19_27, kk_test__exn__new_mlift_test_10013_fun85(_ctx), _x_x86, kk_std_core_types__optional_box(kk_std_core_types__new_None(_ctx), _ctx), _ctx); /*10002*/
    return kk_string_unbox(_x_x84);
  }
  {
    kk_define_string_literal(, _s_x89, 2, "ok", _ctx)
    return kk_string_dup(_s_x89, _ctx);
  }
}


// lift anonymous function
struct kk_test__exn_test_fun91__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__exn_test_fun91(kk_function_t _fself, kk_context_t* _ctx);
static kk_function_t kk_test__exn_new_test_fun91(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__exn_test_fun91, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__exn_test_fun91(kk_function_t _fself, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_std_core_hnd__ev ev_10020 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<test_exn/eff1>*/;
  {
    struct kk_std_core_hnd_Ev* _con_x92 = kk_std_core_hnd__as_Ev(ev_10020, _ctx);
    kk_box_t _box_x34 = _con_x92->hnd;
    int32_t m = _con_x92->marker;
    kk_test__exn__eff1 h = kk_test__exn__eff1_unbox(_box_x34, KK_BORROWED, _ctx);
    kk_test__exn__eff1_dup(h, _ctx);
    {
      struct kk_test__exn__Hnd_eff1* _con_x93 = kk_test__exn__as_Hnd_eff1(h, _ctx);
      kk_integer_t _pat_0 = _con_x93->_cfc;
      kk_std_core_hnd__clause0 _fun_op1 = _con_x93->_fun_op1;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_integer_drop(_pat_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_op1, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x37 = _fun_op1.clause;
        return kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x37, (_fun_unbox_x37, m, ev_10020, _ctx), _ctx);
      }
    }
  }
}


// lift anonymous function
struct kk_test__exn_test_fun95__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__exn_test_fun95(kk_function_t _fself, kk_box_t _b_x45, kk_context_t* _ctx);
static kk_function_t kk_test__exn_new_test_fun95(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__exn_test_fun95, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__exn_test_fun95(kk_function_t _fself, kk_box_t _b_x45, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x96;
  bool _x_x97 = kk_bool_unbox(_b_x45); /*bool*/
  _x_x96 = kk_test__exn__mlift_test_10013(_x_x97, _ctx); /*string*/
  return kk_string_box(_x_x96);
}


// lift anonymous function
struct kk_test__exn_test_fun99__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__exn_test_fun99(kk_function_t _fself, kk_box_t _b_x48, kk_context_t* _ctx);
static kk_function_t kk_test__exn_new_test_fun99(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__exn_test_fun99, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__exn_test_fun99(kk_function_t _fself, kk_box_t _b_x48, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  bool _x_x100;
  bool b_66 = kk_bool_unbox(_b_x48); /*bool*/;
  if (b_66) {
    _x_x100 = false; /*bool*/
  }
  else {
    _x_x100 = true; /*bool*/
  }
  return kk_bool_box(_x_x100);
}


// lift anonymous function
struct kk_test__exn_test_fun102__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__exn_test_fun102(kk_function_t _fself, kk_box_t _b_x55, kk_box_t _b_x56, kk_context_t* _ctx);
static kk_function_t kk_test__exn_new_test_fun102(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__exn_test_fun102, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__exn_test_fun102(kk_function_t _fself, kk_box_t _b_x55, kk_box_t _b_x56, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _b_x49_64 = kk_string_unbox(_b_x55); /*string*/;
  kk_std_core_types__optional _b_x50_65 = kk_std_core_types__optional_unbox(_b_x56, KK_OWNED, _ctx); /*? exception-info*/;
  return kk_std_core_exn_throw(_b_x49_64, _b_x50_65, _ctx);
}

kk_string_t kk_test__exn_test(kk_context_t* _ctx) { /* () -> <eff1,exn> string */ 
  kk_ssize_t _b_x40_42 = (KK_IZ(0)); /*hnd/ev-index*/;
  bool x_10017;
  kk_box_t _x_x90 = kk_std_core_hnd__open_at0(_b_x40_42, kk_test__exn_new_test_fun91(_ctx), _ctx); /*10000*/
  x_10017 = kk_bool_unbox(_x_x90); /*bool*/
  if (kk_yielding(kk_context())) {
    kk_box_t _x_x94 = kk_std_core_hnd_yield_extend(kk_test__exn_new_test_fun95(_ctx), _ctx); /*10001*/
    return kk_string_unbox(_x_x94);
  }
  {
    bool _match_x68;
    kk_box_t _x_x98 = kk_std_core_hnd__open_none1(kk_test__exn_new_test_fun99(_ctx), kk_bool_box(x_10017), _ctx); /*10001*/
    _match_x68 = kk_bool_unbox(_x_x98); /*bool*/
    if (_match_x68) {
      kk_ssize_t _b_x51_60 = (KK_IZ(1)); /*hnd/ev-index*/;
      kk_box_t _x_x101;
      kk_box_t _x_x103;
      kk_string_t _x_x104;
      kk_define_string_literal(, _s_x105, 5, "error", _ctx)
      _x_x104 = kk_string_dup(_s_x105, _ctx); /*string*/
      _x_x103 = kk_string_box(_x_x104); /*10000*/
      _x_x101 = kk_std_core_hnd__open_at2(_b_x51_60, kk_test__exn_new_test_fun102(_ctx), _x_x103, kk_std_core_types__optional_box(kk_std_core_types__new_None(_ctx), _ctx), _ctx); /*10002*/
      return kk_string_unbox(_x_x101);
    }
    {
      kk_define_string_literal(, _s_x106, 2, "ok", _ctx)
      return kk_string_dup(_s_x106, _ctx);
    }
  }
}

// initialization
void kk_test__exn__init(kk_context_t* _ctx){
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
    kk_string_t _x_x73;
    kk_define_string_literal(, _s_x74, 13, "eff1@test_exn", _ctx)
    _x_x73 = kk_string_dup(_s_x74, _ctx); /*string*/
    kk_test__exn_eff1_fs__tag = kk_std_core_hnd__new_Htag(_x_x73, _ctx); /*hnd/htag<test_exn/eff1>*/
  }
}

// termination
void kk_test__exn__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_std_core_hnd__htag_drop(kk_test__exn_eff1_fs__tag, _ctx);
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
