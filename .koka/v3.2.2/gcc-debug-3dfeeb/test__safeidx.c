// Koka generated module: test_safeidx, koka version: 3.2.2, platform: 64-bit
#include "test__safeidx.h"

kk_unit_t kk_test__safeidx_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_vector_t v;
  kk_box_t _x_x14;
  kk_string_t _x_x15;
  kk_define_string_literal(, _s_x16, 1, "a", _ctx)
  _x_x15 = kk_string_dup(_s_x16, _ctx); /*string*/
  _x_x14 = kk_string_box(_x_x15); /*10021*/
  kk_box_t _x_x17;
  kk_string_t _x_x18;
  kk_define_string_literal(, _s_x19, 1, "b", _ctx)
  _x_x18 = kk_string_dup(_s_x19, _ctx); /*string*/
  _x_x17 = kk_string_box(_x_x18); /*10021*/
  kk_box_t _x_x20;
  kk_string_t _x_x21;
  kk_define_string_literal(, _s_x22, 1, "c", _ctx)
  _x_x21 = kk_string_dup(_s_x22, _ctx); /*string*/
  _x_x20 = kk_string_box(_x_x21); /*10021*/
  kk_vector_t _vec_x23 = kk_std_core_vector__unsafe_vector((KK_IZ(3)), _ctx);
  kk_box_t* _buf_x24 = kk_vector_buf_borrow(_vec_x23, NULL, _ctx);
  _buf_x24[0] = _x_x14;
  _buf_x24[1] = _x_x17;
  _buf_x24[2] = _x_x20;
  v = _vec_x23; /*vector<string>*/
  kk_std_core_types__maybe m_10001;
  kk_std_core_types__maybe _brw_x13 = kk_std_core_vector_at(v, kk_integer_from_small(1), _ctx); /*maybe<10000>*/;
  kk_vector_drop(v, _ctx);
  m_10001 = _brw_x13; /*maybe<string>*/
  kk_string_t _x_x25;
  if (kk_std_core_types__is_Nothing(m_10001, _ctx)) {
    kk_define_string_literal(, _s_x26, 1, "x", _ctx)
    _x_x25 = kk_string_dup(_s_x26, _ctx); /*string*/
  }
  else {
    kk_box_t _box_x12 = m_10001._cons.Just.value;
    kk_string_t x = kk_string_unbox(_box_x12);
    kk_string_dup(x, _ctx);
    kk_std_core_types__maybe_drop(m_10001, _ctx);
    _x_x25 = x; /*string*/
  }
  kk_std_core_console_printsln(_x_x25, _ctx); return kk_Unit;
}

// initialization
void kk_test__safeidx__init(kk_context_t* _ctx){
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
void kk_test__safeidx__done(kk_context_t* _ctx){
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
