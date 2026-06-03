// Koka generated module: test_findidx, koka version: 3.2.2, platform: 64-bit
#include "test__findidx.h"

kk_integer_t kk_test__findidx_find_index(kk_std_core_types__list list, kk_string_t target, kk_context_t* _ctx) { /* (list : list<string>, target : string) -> int */ 
  if (kk_std_core_types__is_Cons(list, _ctx)) {
    struct kk_std_core_types_Cons* _con_x15 = kk_std_core_types__as_Cons(list, _ctx);
    kk_box_t _box_x0 = _con_x15->head;
    kk_std_core_types__list xs = _con_x15->tail;
    kk_string_t x = kk_string_unbox(_box_x0);
    if kk_likely(kk_datatype_ptr_is_unique(list, _ctx)) {
      kk_datatype_ptr_free(list, _ctx);
    }
    else {
      kk_string_dup(x, _ctx);
      kk_std_core_types__list_dup(xs, _ctx);
      kk_datatype_ptr_decref(list, _ctx);
    }
    bool _match_x13;
    kk_string_t _x_x16 = kk_string_dup(target, _ctx); /*string*/
    _match_x13 = kk_string_is_eq(x,_x_x16,kk_context()); /*bool*/
    if (_match_x13) {
      kk_std_core_types__list_drop(xs, _ctx);
      kk_string_drop(target, _ctx);
      return kk_integer_from_small(0);
    }
    {
      kk_integer_t y_10001 = kk_test__findidx_find_index(xs, target, _ctx); /*int*/;
      return kk_integer_add_small_const(y_10001, 1, _ctx);
    }
  }
  {
    kk_string_drop(target, _ctx);
    return kk_integer_from_small(0);
  }
}

kk_unit_t kk_test__findidx_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_integer_t idx;
  kk_std_core_types__list _x_x17;
  kk_box_t _x_x18;
  kk_string_t _x_x19;
  kk_define_string_literal(, _s_x20, 1, "a", _ctx)
  _x_x19 = kk_string_dup(_s_x20, _ctx); /*string*/
  _x_x18 = kk_string_box(_x_x19); /*10021*/
  kk_std_core_types__list _x_x21;
  kk_box_t _x_x22;
  kk_string_t _x_x23;
  kk_define_string_literal(, _s_x24, 1, "b", _ctx)
  _x_x23 = kk_string_dup(_s_x24, _ctx); /*string*/
  _x_x22 = kk_string_box(_x_x23); /*10021*/
  kk_std_core_types__list _x_x25;
  kk_box_t _x_x26;
  kk_string_t _x_x27;
  kk_define_string_literal(, _s_x28, 1, "c", _ctx)
  _x_x27 = kk_string_dup(_s_x28, _ctx); /*string*/
  _x_x26 = kk_string_box(_x_x27); /*10021*/
  _x_x25 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x26, kk_std_core_types__new_Nil(_ctx), _ctx); /*list<10021>*/
  _x_x21 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x22, _x_x25, _ctx); /*list<10021>*/
  _x_x17 = kk_std_core_types__new_Cons(kk_reuse_null, 0, _x_x18, _x_x21, _ctx); /*list<10021>*/
  kk_string_t _x_x29;
  kk_define_string_literal(, _s_x30, 1, "b", _ctx)
  _x_x29 = kk_string_dup(_s_x30, _ctx); /*string*/
  idx = kk_test__findidx_find_index(_x_x17, _x_x29, _ctx); /*int*/
  kk_string_t s_10002 = kk_std_core_int_show(idx, _ctx); /*string*/;
  kk_std_core_console_printsln(s_10002, _ctx); return kk_Unit;
}

// initialization
void kk_test__findidx__init(kk_context_t* _ctx){
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
void kk_test__findidx__done(kk_context_t* _ctx){
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
