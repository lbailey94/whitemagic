// Koka generated module: test_handler2, koka version: 3.2.2, platform: 64-bit
#include "test__handler2.h"
 
// runtime tag for the effect `:test-eff`

kk_std_core_hnd__htag kk_test__handler2_test_eff_fs__tag;
 
// handler for the effect `:test-eff`

kk_box_t kk_test__handler2_test_eff_fs__handle(kk_test__handler2__test_eff hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,b> (hnd : test-eff<e,b>, ret : (res : a) -> e b, action : () -> <test-eff|e> a) -> e b */ 
  kk_std_core_hnd__htag _x_x23 = kk_std_core_hnd__htag_dup(kk_test__handler2_test_eff_fs__tag, _ctx); /*hnd/htag<test_handler2/test-eff>*/
  return kk_std_core_hnd__hhandle(_x_x23, kk_test__handler2__test_eff_box(hnd, _ctx), ret, action, _ctx);
}


// lift anonymous function
struct kk_test__handler2_h_fun29__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__handler2_h_fun29(kk_function_t _fself, kk_function_t _action, kk_context_t* _ctx);
static kk_function_t kk_test__handler2_new_h_fun29(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__handler2_h_fun29, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}



// lift anonymous function
struct kk_test__handler2_h_fun30__t {
  struct kk_function_s _base;
};
static bool kk_test__handler2_h_fun30(kk_function_t _fself, kk_string_t y, kk_context_t* _ctx);
static kk_function_t kk_test__handler2_new_h_fun30(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__handler2_h_fun30, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static bool kk_test__handler2_h_fun30(kk_function_t _fself, kk_string_t y, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x31 = kk_string_empty(); /*string*/
  return kk_string_is_neq(y,_x_x31,kk_context());
}


// lift anonymous function
struct kk_test__handler2_h_fun35__t {
  struct kk_function_s _base;
  kk_function_t _b_x16_18;
};
static kk_box_t kk_test__handler2_h_fun35(kk_function_t _fself, kk_box_t _b_x17, kk_context_t* _ctx);
static kk_function_t kk_test__handler2_new_h_fun35(kk_function_t _b_x16_18, kk_context_t* _ctx) {
  struct kk_test__handler2_h_fun35__t* _self = kk_function_alloc_as(struct kk_test__handler2_h_fun35__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_test__handler2_h_fun35, kk_context());
  _self->_b_x16_18 = _b_x16_18;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_test__handler2_h_fun35(kk_function_t _fself, kk_box_t _b_x17, kk_context_t* _ctx) {
  struct kk_test__handler2_h_fun35__t* _self = kk_function_as(struct kk_test__handler2_h_fun35__t*, _fself, _ctx);
  kk_function_t _b_x16_18 = _self->_b_x16_18; /* (y : string) -> 332 bool */
  kk_drop_match(_self, {kk_function_dup(_b_x16_18, _ctx);}, {}, _ctx)
  bool _x_x36;
  kk_string_t _x_x37 = kk_string_unbox(_b_x17); /*string*/
  _x_x36 = kk_function_call(bool, (kk_function_t, kk_string_t, kk_context_t*), _b_x16_18, (_b_x16_18, _x_x37, _ctx), _ctx); /*bool*/
  return kk_bool_box(_x_x36);
}


// lift anonymous function
struct kk_test__handler2_h_fun38__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__handler2_h_fun38(kk_function_t _fself, kk_box_t _res, kk_context_t* _ctx);
static kk_function_t kk_test__handler2_new_h_fun38(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__handler2_h_fun38, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__handler2_h_fun38(kk_function_t _fself, kk_box_t _res, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  return _res;
}
static kk_box_t kk_test__handler2_h_fun29(kk_function_t _fself, kk_function_t _action, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_function_t _b_x16_18 = kk_test__handler2_new_h_fun30(_ctx); /*(y : string) -> 332 bool*/;
  kk_test__handler2__test_eff _x_x33;
  kk_std_core_hnd__clause1 _x_x34 = kk_std_core_hnd_clause_tail1(kk_test__handler2_new_h_fun35(_b_x16_18, _ctx), _ctx); /*hnd/clause1<10003,10004,10002,10000,10001>*/
  _x_x33 = kk_test__handler2__new_Hnd_test_eff(kk_reuse_null, 0, kk_integer_from_small(1), _x_x34, _ctx); /*test_handler2/test-eff<6,7>*/
  return kk_test__handler2_test_eff_fs__handle(_x_x33, kk_test__handler2_new_h_fun38(_ctx), _action, _ctx);
}

kk_function_t kk_test__handler2_h;

// initialization
void kk_test__handler2__init(kk_context_t* _ctx){
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
    kk_string_t _x_x21;
    kk_define_string_literal(, _s_x22, 22, "test-eff@test_handler2", _ctx)
    _x_x21 = kk_string_dup(_s_x22, _ctx); /*string*/
    kk_test__handler2_test_eff_fs__tag = kk_std_core_hnd__new_Htag(_x_x21, _ctx); /*hnd/htag<test_handler2/test-eff>*/
  }
  {
    kk_test__handler2_h = kk_test__handler2_new_h_fun29(_ctx); /*forall<a,e> (() -> <test_handler2/test-eff|e> a) -> e a*/
  }
}

// termination
void kk_test__handler2__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_function_drop(kk_test__handler2_h, _ctx);
  kk_std_core_hnd__htag_drop(kk_test__handler2_test_eff_fs__tag, _ctx);
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
