// Koka generated module: test_vector, koka version: 3.2.2, platform: 64-bit
#include "test__vector.h"


// lift anonymous function
struct kk_test__vector_main_fun34__t {
  struct kk_function_s _base;
};
static kk_box_t kk_test__vector_main_fun34(kk_function_t _fself, kk_box_t _b_x17, kk_context_t* _ctx);
static kk_function_t kk_test__vector_new_main_fun34(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__vector_main_fun34, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static kk_box_t kk_test__vector_main_fun34(kk_function_t _fself, kk_box_t _b_x17, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_unit_t _x_x35 = kk_Unit;
  kk_string_t _x_x36 = kk_string_unbox(_b_x17); /*string*/
  kk_std_core_console_printsln(_x_x36, _ctx);
  return kk_unit_box(_x_x35);
}

kk_unit_t kk_test__vector_main(kk_context_t* _ctx) { /* () -> <console/console,exn> () */ 
  kk_vector_t order;
  kk_box_t _x_x21;
  kk_string_t _x_x22;
  kk_define_string_literal(, _s_x23, 1, "a", _ctx)
  _x_x22 = kk_string_dup(_s_x23, _ctx); /*string*/
  _x_x21 = kk_string_box(_x_x22); /*10021*/
  kk_box_t _x_x24;
  kk_string_t _x_x25;
  kk_define_string_literal(, _s_x26, 1, "b", _ctx)
  _x_x25 = kk_string_dup(_s_x26, _ctx); /*string*/
  _x_x24 = kk_string_box(_x_x25); /*10021*/
  kk_box_t _x_x27;
  kk_string_t _x_x28;
  kk_define_string_literal(, _s_x29, 1, "c", _ctx)
  _x_x28 = kk_string_dup(_s_x29, _ctx); /*string*/
  _x_x27 = kk_string_box(_x_x28); /*10021*/
  kk_vector_t _vec_x30 = kk_std_core_vector__unsafe_vector((KK_IZ(3)), _ctx);
  kk_box_t* _buf_x31 = kk_vector_buf_borrow(_vec_x30, NULL, _ctx);
  _buf_x31[0] = _x_x21;
  _buf_x31[1] = _x_x24;
  _buf_x31[2] = _x_x27;
  order = _vec_x30; /*vector<string>*/
  kk_string_t x_10002;
  kk_box_t _x_x32;
  kk_box_t _brw_x20 = kk_std_core_vector__index(order, kk_integer_from_small(1), _ctx); /*10000*/;
  kk_vector_drop(order, _ctx);
  _x_x32 = _brw_x20; /*10000*/
  x_10002 = kk_string_unbox(_x_x32); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_10002, _ctx);
    kk_box_t _x_x33 = kk_std_core_hnd_yield_extend(kk_test__vector_new_main_fun34(_ctx), _ctx); /*10001*/
    kk_unit_unbox(_x_x33); return kk_Unit;
  }
  {
    kk_std_core_console_printsln(x_10002, _ctx); return kk_Unit;
  }
}

// initialization
void kk_test__vector__init(kk_context_t* _ctx){
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
}

// termination
void kk_test__vector__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
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
