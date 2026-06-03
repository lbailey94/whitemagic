#pragma once
#ifndef kk_test__struct2_H
#define kk_test__struct2_H
// Koka generated module: test_struct2, koka version: 3.2.2, platform: 64-bit
#include <kklib.h>
#include "std_core_types.h"
#include "std_core_hnd.h"
#include "std_core_exn.h"
#include "std_core_bool.h"
#include "std_core_order.h"
#include "std_core_char.h"
#include "std_core_int.h"
#include "std_core_vector.h"
#include "std_core_string.h"
#include "std_core_sslice.h"
#include "std_core_list.h"
#include "std_core_maybe.h"
#include "std_core_maybe2.h"
#include "std_core_either.h"
#include "std_core_tuple.h"
#include "std_core_lazy.h"
#include "std_core_show.h"
#include "std_core_debug.h"
#include "std_core_delayed.h"
#include "std_core_console.h"
#include "std_core.h"

// type declarations

// type test_struct2/gana-meta
struct kk_test__struct2__gana_meta_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_test__struct2__gana_meta;
struct kk_test__struct2_Gana_meta {
  struct kk_test__struct2__gana_meta_s _base;
  kk_integer_t num;
  kk_string_t name;
};
static inline kk_test__struct2__gana_meta kk_test__struct2__base_Gana_meta(struct kk_test__struct2_Gana_meta* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_test__struct2__gana_meta kk_test__struct2__new_Gana_meta(kk_reuse_t _at, int32_t _cpath, kk_integer_t num, kk_string_t name, kk_context_t* _ctx) {
  struct kk_test__struct2_Gana_meta* _con = kk_block_alloc_at_as(struct kk_test__struct2_Gana_meta, _at, 2 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->num = num;
  _con->name = name;
  return kk_test__struct2__base_Gana_meta(_con, _ctx);
}
static inline struct kk_test__struct2_Gana_meta* kk_test__struct2__as_Gana_meta(kk_test__struct2__gana_meta x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_test__struct2_Gana_meta*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_test__struct2__is_Gana_meta(kk_test__struct2__gana_meta x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_test__struct2__gana_meta kk_test__struct2__gana_meta_dup(kk_test__struct2__gana_meta _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_test__struct2__gana_meta_drop(kk_test__struct2__gana_meta _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_test__struct2__gana_meta_box(kk_test__struct2__gana_meta _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_test__struct2__gana_meta kk_test__struct2__gana_meta_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// value declarations
 
// Automatically generated. Retrieves the `name` constructor field of the `:gana-meta` type.

static inline kk_string_t kk_test__struct2_gana_meta_fs_name(kk_test__struct2__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> string */ 
  {
    struct kk_test__struct2_Gana_meta* _con_x4 = kk_test__struct2__as_Gana_meta(_this, _ctx);
    kk_string_t _x = _con_x4->name;
    return kk_string_dup(_x, _ctx);
  }
}
 
// Automatically generated. Retrieves the `num` constructor field of the `:gana-meta` type.

static inline kk_integer_t kk_test__struct2_gana_meta_fs_num(kk_test__struct2__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> int */ 
  {
    struct kk_test__struct2_Gana_meta* _con_x5 = kk_test__struct2__as_Gana_meta(_this, _ctx);
    kk_integer_t _x = _con_x5->num;
    return kk_integer_dup(_x, _ctx);
  }
}

kk_test__struct2__gana_meta kk_test__struct2_gana_meta_fs__copy(kk_test__struct2__gana_meta _this, kk_std_core_types__optional num, kk_std_core_types__optional name, kk_context_t* _ctx); /* (gana-meta, num : ? int, name : ? string) -> gana-meta */ 

static inline kk_unit_t kk_test__struct2_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t _x_x10;
  kk_define_string_literal(, _s_x11, 4, "test", _ctx)
  _x_x10 = kk_string_dup(_s_x11, _ctx); /*string*/
  kk_std_core_console_printsln(_x_x10, _ctx); return kk_Unit;
}

void kk_test__struct2__init(kk_context_t* _ctx);


void kk_test__struct2__done(kk_context_t* _ctx);

#endif // header
