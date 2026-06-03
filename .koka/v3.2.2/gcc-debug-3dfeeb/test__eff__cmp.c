// Koka generated module: test_eff_cmp, koka version: 3.2.2, platform: 64-bit
#include "test__eff__cmp.h"
 
// runtime tag for the effect `:eff1`

kk_std_core_hnd__htag kk_test__eff__cmp_eff1_fs__tag;
 
// handler for the effect `:eff1`

kk_box_t kk_test__eff__cmp_eff1_fs__handle(kk_test__eff__cmp__eff1 hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx) { /* forall<a,e,b> (hnd : eff1<e,b>, ret : (res : a) -> e b, action : () -> <eff1|e> a) -> e b */ 
  kk_std_core_hnd__htag _x_x19 = kk_std_core_hnd__htag_dup(kk_test__eff__cmp_eff1_fs__tag, _ctx); /*hnd/htag<test_eff_cmp/eff1>*/
  return kk_std_core_hnd__hhandle(_x_x19, kk_test__eff__cmp__eff1_box(hnd, _ctx), ret, action, _ctx);
}

// initialization
void kk_test__eff__cmp__init(kk_context_t* _ctx){
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
    kk_string_t _x_x17;
    kk_define_string_literal(, _s_x18, 17, "eff1@test_eff_cmp", _ctx)
    _x_x17 = kk_string_dup(_s_x18, _ctx); /*string*/
    kk_test__eff__cmp_eff1_fs__tag = kk_std_core_hnd__new_Htag(_x_x17, _ctx); /*hnd/htag<test_eff_cmp/eff1>*/
  }
}

// termination
void kk_test__eff__cmp__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_std_core_hnd__htag_drop(kk_test__eff__cmp_eff1_fs__tag, _ctx);
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
