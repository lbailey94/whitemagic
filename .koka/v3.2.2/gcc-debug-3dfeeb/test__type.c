// Koka generated module: test_type, koka version: 3.2.2, platform: 64-bit
#include "test__type.h"


// lift anonymous function
struct kk_test__type_main_fun30__t {
  struct kk_function_s _base;
};
static bool kk_test__type_main_fun30(kk_function_t _fself, kk_box_t _b_x8, kk_context_t* _ctx);
static kk_function_t kk_test__type_new_main_fun30(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_test__type_main_fun30, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}

static bool kk_test__type_main_fun30(kk_function_t _fself, kk_box_t _b_x8, kk_context_t* _ctx) {
  kk_function_static_drop(_fself,kk_context());
  kk_string_t _x_x31 = kk_string_unbox(_b_x8); /*string*/
  kk_string_t _x_x32;
  kk_define_string_literal(, _s_x33, 1, "b", _ctx)
  _x_x32 = kk_string_dup(_s_x33, _ctx); /*string*/
  return kk_string_is_eq(_x_x31,_x_x32,kk_context());
}

kk_unit_t kk_test__type_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_integer_t idx;
  kk_std_core_types__list _x_x18;
  kk_box_t _x_x19;
  kk_string_t _x_x20;
  kk_define_string_literal(, _s_x21, 1, "a", _ctx)
  _x_x20 = kk_string_dup(_s_x21, _ctx); /*string*/
  _x_x19 = kk_string_box(_x_x20); /*10021*/
  kk_std_core_types__list _x_x22;
  kk_box_t _x_x23;
  kk_string_t _x_x24;
  kk_define_string_literal(, _s_x25, 1, "b", _ctx)
  _x_x24 = kk_string_dup(_s_x25, _ctx); /*string*/
  _x_x23 = kk_string_box(_x_x24); /*10021*/
  kk_std_core_types__list _x_x26;
  kk_box_t _x_x27;
  kk_string_t _x_x28;
  kk_define_string_literal(, _s_x29, 1, "c", _ctx)
  _x_x28 = kk_string_dup(_s_x29, _ctx); /*string*/
  _x_x27 = kk_string_box(_x_x28); /*10021*/
  _x_x26 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x27, kk_std_core_types__new_Nil(_ctx), _ctx); /*list<10021>*/
  _x_x22 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x23, _x_x26, _ctx); /*list<10021>*/
  _x_x18 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x19, _x_x22, _ctx); /*list<10021>*/
  idx = kk_std_core_list_index_of(_x_x18, kk_test__type_new_main_fun30(_ctx), _ctx); /*int*/
  kk_integer_drop(idx, _ctx);
  kk_string_t _x_x34;
  kk_define_string_literal(, _s_x35, 2, "ok", _ctx)
  _x_x34 = kk_string_dup(_s_x35, _ctx); /*string*/
  kk_std_core_console_printsln(_x_x34, _ctx); return kk_Unit;
}

// initialization
void kk_test__type__init(kk_context_t* _ctx){
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
void kk_test__type__done(kk_context_t* _ctx){
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
