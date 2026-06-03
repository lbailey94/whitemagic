// Koka generated module: test_complete, koka version: 3.2.2, platform: 64-bit
#include "test__complete.h"
 
// runtime tag for the effect `:test-eff`

kk_std_core_hnd__htag kk_test__complete_test_eff_fs__tag;
 
// handler for the effect `:test-eff`

kk_box_t kk_test__complete_test_eff_fs__handle(kk_test__complete__test_eff hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,b> (hnd : test-eff<e,b>, ret : (res : a) -> e b, action : () -> <test-eff|e> a) -> e b */ 
  kk_std_core_hnd__htag _x_x32 = kk_std_core_hnd__htag_dup(kk_test__complete_test_eff_fs__tag, _ctx); /*hnd/htag<test_complete/test-eff>*/
  return kk_std_core_hnd__hhandle(_x_x32, kk_test__complete__test_eff_box(hnd, _ctx), ret, action, _ctx);
}


// lift anonymous function
struct kk_test__complete_h_fun43__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__complete_h_fun43(kk_function_t _fself, kk_function_t _action, kk_context_t* _ctx);
static kk_function_t kk_test__complete_new_h_fun43(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__complete_h_fun43, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}



// lift anonymous function
struct kk_test__complete_h_fun44__t {
  struct kk_function_s _base;
};
static bool kk_test__complete_h_fun44(kk_function_t _fself, kk_string_t y, kk_context_t* _ctx);
static kk_function_t kk_test__complete_new_h_fun44(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__complete_h_fun44, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static bool kk_test__complete_h_fun44(kk_function_t _fself, kk_string_t y, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x45 = kk_string_empty(); /*string*/
  return kk_string_is_neq(y,_x_x45,kk_context());
}


// lift anonymous function
struct kk_test__complete_h_fun47__t {
  struct kk_function_s _base;
};
static kk_integer_t kk_test__complete_h_fun47(kk_function_t _fself, kk_context_t* _ctx);
static kk_function_t kk_test__complete_new_h_fun47(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__complete_h_fun47, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_integer_t kk_test__complete_h_fun47(kk_function_t _fself, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  return kk_integer_from_small(5);
}


// lift anonymous function
struct kk_test__complete_h_fun50__t {
  struct kk_function_s _base;
  kk_function_t _b_x22_25;
};
static kk_box_t kk_test__complete_h_fun50(kk_function_t _fself, kk_box_t _b_x23, kk_context_t* _ctx);
static kk_function_t kk_test__complete_new_h_fun50(kk_function_t _b_x22_25, kk_context_t* _ctx) {
  struct kk_test__complete_h_fun50__t* _self = kk_function_alloc_as(struct kk_test__complete_h_fun50__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_test__complete_h_fun50, kk_context());
  _self->_b_x22_25 = _b_x22_25;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_test__complete_h_fun50(kk_function_t _fself, kk_box_t _b_x23, kk_context_t* _ctx) {
  struct kk_test__complete_h_fun50__t* _self = kk_function_as(struct kk_test__complete_h_fun50__t*, _fself, _ctx);
  kk_function_t _b_x22_25 = _self->_b_x22_25; /* (y : string) -> 471 bool */
  kk_drop_match(_self, {kk_function_dup(_b_x22_25, _ctx);}, {}, _ctx)
  bool _x_x51;
  kk_string_t _x_x52 = kk_string_unbox(_b_x23); /*string*/
  _x_x51 = kk_function_call(bool, (kk_function_t, kk_string_t, kk_context_t*), _b_x22_25, (_b_x22_25, _x_x52, _ctx), _ctx); /*bool*/
  return kk_bool_box(_x_x51);
}


// lift anonymous function
struct kk_test__complete_h_fun54__t {
  struct kk_function_s _base;
  kk_function_t _b_x24_26;
};
static kk_box_t kk_test__complete_h_fun54(kk_function_t _fself, kk_context_t* _ctx);
static kk_function_t kk_test__complete_new_h_fun54(kk_function_t _b_x24_26, kk_context_t* _ctx) {
  struct kk_test__complete_h_fun54__t* _self = kk_function_alloc_as(struct kk_test__complete_h_fun54__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_test__complete_h_fun54, kk_context());
  _self->_b_x24_26 = _b_x24_26;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_test__complete_h_fun54(kk_function_t _fself, kk_context_t* _ctx) {
  struct kk_test__complete_h_fun54__t* _self = kk_function_as(struct kk_test__complete_h_fun54__t*, _fself, _ctx);
  kk_function_t _b_x24_26 = _self->_b_x24_26; /* () -> 471 int */
  kk_drop_match(_self, {kk_function_dup(_b_x24_26, _ctx);}, {}, _ctx)
  kk_integer_t _x_x55 = kk_function_call(kk_integer_t, (kk_function_t, kk_context_t*), _b_x24_26, (_b_x24_26, _ctx), _ctx); /*int*/
  return kk_integer_box(_x_x55, _ctx);
}


// lift anonymous function
struct kk_test__complete_h_fun56__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__complete_h_fun56(kk_function_t _fself, kk_box_t _res, kk_context_t* _ctx);
static kk_function_t kk_test__complete_new_h_fun56(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__complete_h_fun56, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__complete_h_fun56(kk_function_t _fself, kk_box_t _res, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  return _res;
}
static kk_box_t kk_test__complete_h_fun43(kk_function_t _fself, kk_function_t _action, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_function_t _b_x22_25 = kk_test__complete_new_h_fun44(_ctx); /*(y : string) -> 471 bool*/;
  kk_function_t _b_x24_26 = kk_test__complete_new_h_fun47(_ctx); /*() -> 471 int*/;
  kk_test__complete__test_eff _x_x48;
  kk_std_core_hnd__clause1 _x_x49 = kk_std_core_hnd_clause_tail1(kk_test__complete_new_h_fun50(_b_x22_25, _ctx), _ctx); /*hnd/clause1<10003,10004,10002,10000,10001>*/
  kk_std_core_hnd__clause0 _x_x53 = kk_std_core_hnd_clause_tail0(kk_test__complete_new_h_fun54(_b_x24_26, _ctx), _ctx); /*hnd/clause0<10003,10002,10000,10001>*/
  _x_x48 = kk_test__complete__new_Hnd_test_eff(kk_reuse_null, 0, kk_integer_from_small(1), _x_x49, _x_x53, _ctx); /*test_complete/test-eff<10,11>*/
  return kk_test__complete_test_eff_fs__handle(_x_x48, kk_test__complete_new_h_fun56(_ctx), _action, _ctx);
}

kk_function_t kk_test__complete_h;

// initialization
void kk_test__complete__init(kk_context_t* _ctx){
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
    kk_string_t _x_x30;
    kk_define_string_literal(, _s_x31, 22, "test-eff@test_complete", _ctx)
    _x_x30 = kk_string_dup(_s_x31, _ctx); /*string*/
    kk_test__complete_test_eff_fs__tag = kk_std_core_hnd__new_Htag(_x_x30, _ctx); /*hnd/htag<test_complete/test-eff>*/
  }
  {
    kk_test__complete_h = kk_test__complete_new_h_fun43(_ctx); /*forall<a,e> (() -> <test_complete/test-eff|e> a) -> e a*/
  }
}

// termination
void kk_test__complete__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_function_drop(kk_test__complete_h, _ctx);
  kk_std_core_hnd__htag_drop(kk_test__complete_test_eff_fs__tag, _ctx);
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
