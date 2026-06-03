// Koka generated module: test_struct2, koka version: 3.2.2, platform: 64-bit
#include "test__struct2.h"

kk_test__struct2__gana_meta kk_test__struct2_gana_meta_fs__copy(kk_test__struct2__gana_meta _this, kk_std_core_types__optional num, kk_std_core_types__optional name, kk_context_t* _ctx) { /* (gana-meta, num : ? int, name : ? string) -> gana-meta */ 
  kk_integer_t _x_x6;
  if (kk_std_core_types__is_Optional(num, _ctx)) {
    kk_box_t _box_x0 = num._cons._Optional.value;
    kk_integer_t _uniq_num_35 = kk_integer_unbox(_box_x0, _ctx);
    kk_integer_dup(_uniq_num_35, _ctx);
    kk_std_core_types__optional_drop(num, _ctx);
    _x_x6 = _uniq_num_35; /*int*/
  }
  else {
    kk_std_core_types__optional_drop(num, _ctx);
    {
      struct kk_test__struct2_Gana_meta* _con_x7 = kk_test__struct2__as_Gana_meta(_this, _ctx);
      kk_integer_t _x = _con_x7->num;
      kk_integer_dup(_x, _ctx);
      _x_x6 = _x; /*int*/
    }
  }
  kk_string_t _x_x8;
  if (kk_std_core_types__is_Optional(name, _ctx)) {
    kk_box_t _box_x1 = name._cons._Optional.value;
    kk_string_t _uniq_name_43 = kk_string_unbox(_box_x1);
    kk_string_dup(_uniq_name_43, _ctx);
    kk_std_core_types__optional_drop(name, _ctx);
    kk_datatype_ptr_dropn(_this, (KK_I32(2)), _ctx);
    _x_x8 = _uniq_name_43; /*string*/
  }
  else {
    kk_std_core_types__optional_drop(name, _ctx);
    {
      struct kk_test__struct2_Gana_meta* _con_x9 = kk_test__struct2__as_Gana_meta(_this, _ctx);
      kk_integer_t _pat_0_1 = _con_x9->num;
      kk_string_t _x_0 = _con_x9->name;
      if kk_likely(kk_datatype_ptr_is_unique(_this, _ctx)) {
        kk_integer_drop(_pat_0_1, _ctx);
        kk_datatype_ptr_free(_this, _ctx);
      }
      else {
        kk_string_dup(_x_0, _ctx);
        kk_datatype_ptr_decref(_this, _ctx);
      }
      _x_x8 = _x_0; /*string*/
    }
  }
  return kk_test__struct2__new_Gana_meta(kk_reuse_null, 0, _x_x6, _x_x8, _ctx);
}

// initialization
void kk_test__struct2__init(kk_context_t* _ctx){
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
void kk_test__struct2__done(kk_context_t* _ctx){
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
