#pragma once
#ifndef kk_polyglot_whitemagic_dash_koka_src_effects_prat_H
#define kk_polyglot_whitemagic_dash_koka_src_effects_prat_H
// Koka generated module: polyglot/whitemagic-koka/src/effects/prat, koka version: 3.2.2, platform: 64-bit
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

// type polyglot/whitemagic-koka/src/effects/prat/gana-horn
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_bootstrap_session;
  kk_std_core_hnd__clause1 _fun_create_session;
  kk_std_core_hnd__clause1 _fun_resume_session;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_gana_horn(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_gana_horn(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_bootstrap_session, kk_std_core_hnd__clause1 _fun_create_session, kk_std_core_hnd__clause1 _fun_resume_session, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn, _at, 4 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_bootstrap_session = _fun_bootstrap_session;
  _con->_fun_create_session = _fun_create_session;
  _con->_fun_resume_session = _fun_resume_session;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_gana_horn(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_gana_horn(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/gana-meta
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta_s _base;
  kk_integer_t mansion_num;
  kk_string_t quadrant;
  kk_string_t meaning;
  kk_string_t garden;
  kk_string_t chinese;
  kk_string_t pinyin;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Gana_meta(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Gana_meta(kk_reuse_t _at, int32_t _cpath, kk_integer_t mansion_num, kk_string_t quadrant, kk_string_t meaning, kk_string_t garden, kk_string_t chinese, kk_string_t pinyin, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta, _at, 6 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->mansion_num = mansion_num;
  _con->quadrant = quadrant;
  _con->meaning = meaning;
  _con->garden = garden;
  _con->chinese = chinese;
  _con->pinyin = pinyin;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Gana_meta(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Gana_meta(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/gana-neck
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause2 _fun_create_memory;
  kk_std_core_hnd__clause1 _fun_import_memories;
  kk_std_core_hnd__clause2 _fun_update_memory;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_gana_neck(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_gana_neck(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause2 _fun_create_memory, kk_std_core_hnd__clause1 _fun_import_memories, kk_std_core_hnd__clause2 _fun_update_memory, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck, _at, 4 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_create_memory = _fun_create_memory;
  _con->_fun_import_memories = _fun_import_memories;
  _con->_fun_update_memory = _fun_update_memory;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_gana_neck(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_gana_neck(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/gana-root
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause0 _fun_check_ship;
  kk_std_core_hnd__clause0 _fun_health_report;
  kk_std_core_hnd__clause0 _fun_rust_status;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_gana_root(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_gana_root(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause0 _fun_check_ship, kk_std_core_hnd__clause0 _fun_health_report, kk_std_core_hnd__clause0 _fun_rust_status, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root, _at, 4 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_check_ship = _fun_check_ship;
  _con->_fun_health_report = _fun_health_report;
  _con->_fun_rust_status = _fun_rust_status;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_gana_root(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_gana_root(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/prat-auth
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_check_auth;
  kk_std_core_hnd__clause0 _fun_get_auth_level;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_auth(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_prat_auth(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_check_auth, kk_std_core_hnd__clause0 _fun_get_auth_level, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth, _at, 3 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_check_auth = _fun_check_auth;
  _con->_fun_get_auth_level = _fun_get_auth_level;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_auth(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_prat_auth(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/prat-karma
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_calculate_ethics_score;
  kk_std_core_hnd__clause1 _fun_get_karmic_trace;
  kk_std_core_hnd__clause2 _fun_log_operation;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_karma(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_prat_karma(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_calculate_ethics_score, kk_std_core_hnd__clause1 _fun_get_karmic_trace, kk_std_core_hnd__clause2 _fun_log_operation, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma, _at, 4 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_calculate_ethics_score = _fun_calculate_ethics_score;
  _con->_fun_get_karmic_trace = _fun_get_karmic_trace;
  _con->_fun_log_operation = _fun_log_operation;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_karma(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_prat_karma(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/prat-rate
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause1 _fun_check_limit;
  kk_std_core_hnd__clause0 _fun_get_quota_remaining;
  kk_std_core_hnd__clause1 _fun_record_request;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_rate(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_prat_rate(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause1 _fun_check_limit, kk_std_core_hnd__clause0 _fun_get_quota_remaining, kk_std_core_hnd__clause1 _fun_record_request, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate, _at, 4 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_check_limit = _fun_check_limit;
  _con->_fun_get_quota_remaining = _fun_get_quota_remaining;
  _con->_fun_record_request = _fun_record_request;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_rate(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_prat_rate(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/prat-resonance
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause0 _fun_get_harmony_score;
  kk_std_core_hnd__clause0 _fun_get_lunar_phase;
  kk_std_core_hnd__clause0 _fun_get_predecessor_gana;
  kk_std_core_hnd__clause1 _fun_record_invocation;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_resonance(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_prat_resonance(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause0 _fun_get_harmony_score, kk_std_core_hnd__clause0 _fun_get_lunar_phase, kk_std_core_hnd__clause0 _fun_get_predecessor_gana, kk_std_core_hnd__clause1 _fun_record_invocation, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance, _at, 5 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_get_harmony_score = _fun_get_harmony_score;
  _con->_fun_get_lunar_phase = _fun_get_lunar_phase;
  _con->_fun_get_predecessor_gana = _fun_get_predecessor_gana;
  _con->_fun_record_invocation = _fun_record_invocation;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_resonance(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_prat_resonance(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// type polyglot/whitemagic-koka/src/effects/prat/prat-route
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_s {
  kk_block_t _block;
};
typedef kk_datatype_ptr_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route;
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_s _base;
  kk_integer_t _cfc;
  kk_std_core_hnd__clause2 _fun_dispatch_tool;
  kk_std_core_hnd__clause1 _fun_get_tool_metadata;
  kk_std_core_hnd__clause0 _fun_list_available_tools;
};
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_route(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _x, kk_context_t* _ctx) {
  return kk_datatype_from_base(&_x->_base, _ctx);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route kk_polyglot_whitemagic_dash_koka_src_effects_prat__new_Hnd_prat_route(kk_reuse_t _at, int32_t _cpath, kk_integer_t _cfc, kk_std_core_hnd__clause2 _fun_dispatch_tool, kk_std_core_hnd__clause1 _fun_get_tool_metadata, kk_std_core_hnd__clause0 _fun_list_available_tools, kk_context_t* _ctx) {
  struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con = kk_block_alloc_at_as(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route, _at, 4 /* scan count */, _cpath, (kk_tag_t)(1), _ctx);
  _con->_cfc = _cfc;
  _con->_fun_dispatch_tool = _fun_dispatch_tool;
  _con->_fun_get_tool_metadata = _fun_get_tool_metadata;
  _con->_fun_list_available_tools = _fun_list_available_tools;
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat__base_Hnd_prat_route(_con, _ctx);
}
static inline struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route x, kk_context_t* _ctx) {
  return kk_datatype_as_assert(struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route*, x, (kk_tag_t)(1), _ctx);
}
static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat__is_Hnd_prat_route(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route x, kk_context_t* _ctx) {
  return (true);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_dup(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_dup(_x, _ctx);
}
static inline void kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_drop(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _x, kk_context_t* _ctx) {
  kk_datatype_ptr_drop(_x, _ctx);
}
static inline kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_box(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _x, kk_context_t* _ctx) {
  return kk_datatype_ptr_box(_x);
}
static inline kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_unbox(kk_box_t _x, kk_borrow_t _borrow, kk_context_t* _ctx) {
  return kk_datatype_ptr_unbox(_x);
}

// value declarations
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:prat-auth` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_auth_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth _this, kk_context_t* _ctx) { /* forall<e,a> (prat-auth<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1255 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(_this, _ctx);
    kk_integer_t _x = _con_x1255->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_auth_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_auth_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : prat-auth<e,b>, ret : (res : a) -> e b, action : () -> <prat-auth|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-check-auth` constructor field of the `:prat-auth` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_auth_fs__fun_check_auth(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth _this, kk_context_t* _ctx) { /* forall<e,a> (prat-auth<e,a>) -> hnd/clause1<string,bool,prat-auth,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1259 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1259->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `check-auth` operation out of effect `:prat-auth`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_check_auth_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-auth<e,a>) -> hnd/clause1<string,bool,prat-auth,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1260 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_check_auth = _con_x1260->_fun_check_auth;
    return kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
  }
}
 
// Call the `fun check-auth` operation of the effect `:prat-auth`

static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat_check_auth(kk_string_t ctxt, kk_context_t* _ctx) { /* (ctxt : string) -> prat-auth bool */ 
  kk_std_core_hnd__ev ev_10113 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-auth>*/;
  kk_box_t _x_x1261;
  {
    struct kk_std_core_hnd_Ev* _con_x1262 = kk_std_core_hnd__as_Ev(ev_10113, _ctx);
    kk_box_t _box_x8 = _con_x1262->hnd;
    int32_t m = _con_x1262->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_unbox(_box_x8, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1263 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1263->_cfc;
      kk_std_core_hnd__clause1 _fun_check_auth = _con_x1263->_fun_check_auth;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1263->_fun_get_auth_level;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_check_auth, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x12 = _fun_check_auth.clause;
        _x_x1261 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x12, (_fun_unbox_x12, m, ev_10113, kk_string_box(ctxt), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_bool_unbox(_x_x1261);
}
 
// Automatically generated. Retrieves the `@fun-get-auth-level` constructor field of the `:prat-auth` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_auth_fs__fun_get_auth_level(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth _this, kk_context_t* _ctx) { /* forall<e,a> (prat-auth<e,a>) -> hnd/clause0<int,prat-auth,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1264 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1264->_fun_get_auth_level;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `get-auth-level` operation out of effect `:prat-auth`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_auth_level_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-auth<e,a>) -> hnd/clause0<int,prat-auth,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1265 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_get_auth_level = _con_x1265->_fun_get_auth_level;
    return kk_std_core_hnd__clause0_dup(_fun_get_auth_level, _ctx);
  }
}
 
// Call the `fun get-auth-level` operation of the effect `:prat-auth`

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_auth_level(kk_context_t* _ctx) { /* () -> prat-auth int */ 
  kk_std_core_hnd__ev ev_10116 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-auth>*/;
  kk_box_t _x_x1266;
  {
    struct kk_std_core_hnd_Ev* _con_x1267 = kk_std_core_hnd__as_Ev(ev_10116, _ctx);
    kk_box_t _box_x16 = _con_x1267->hnd;
    int32_t m = _con_x1267->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_unbox(_box_x16, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_auth_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_auth* _con_x1268 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_auth(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1268->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1268->_fun_check_auth;
      kk_std_core_hnd__clause0 _fun_get_auth_level = _con_x1268->_fun_get_auth_level;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_get_auth_level, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x19 = _fun_get_auth_level.clause;
        _x_x1266 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x19, (_fun_unbox_x19, m, ev_10116, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_integer_unbox(_x_x1266, _ctx);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:prat-rate` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_rate_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _this, kk_context_t* _ctx) { /* forall<e,a> (prat-rate<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1269 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(_this, _ctx);
    kk_integer_t _x = _con_x1269->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_rate_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_rate_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : prat-rate<e,b>, ret : (res : a) -> e b, action : () -> <prat-rate|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-check-limit` constructor field of the `:prat-rate` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_rate_fs__fun_check_limit(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _this, kk_context_t* _ctx) { /* forall<e,a> (prat-rate<e,a>) -> hnd/clause1<string,bool,prat-rate,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1273 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1273->_fun_check_limit;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `check-limit` operation out of effect `:prat-rate`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_check_limit_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-rate<e,a>) -> hnd/clause1<string,bool,prat-rate,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1274 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_check_limit = _con_x1274->_fun_check_limit;
    return kk_std_core_hnd__clause1_dup(_fun_check_limit, _ctx);
  }
}
 
// Call the `fun check-limit` operation of the effect `:prat-rate`

static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat_check_limit(kk_string_t ctxt, kk_context_t* _ctx) { /* (ctxt : string) -> prat-rate bool */ 
  kk_std_core_hnd__ev ev_10119 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-rate>*/;
  kk_box_t _x_x1275;
  {
    struct kk_std_core_hnd_Ev* _con_x1276 = kk_std_core_hnd__as_Ev(ev_10119, _ctx);
    kk_box_t _box_x30 = _con_x1276->hnd;
    int32_t m = _con_x1276->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_unbox(_box_x30, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1277 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1277->_cfc;
      kk_std_core_hnd__clause1 _fun_check_limit = _con_x1277->_fun_check_limit;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1277->_fun_get_quota_remaining;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1277->_fun_record_request;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_check_limit, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x34 = _fun_check_limit.clause;
        _x_x1275 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x34, (_fun_unbox_x34, m, ev_10119, kk_string_box(ctxt), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_bool_unbox(_x_x1275);
}
 
// Automatically generated. Retrieves the `@fun-record-request` constructor field of the `:prat-rate` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_rate_fs__fun_record_request(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _this, kk_context_t* _ctx) { /* forall<e,a> (prat-rate<e,a>) -> hnd/clause1<string,(),prat-rate,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1278 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1278->_fun_record_request;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `record-request` operation out of effect `:prat-rate`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_request_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-rate<e,a>) -> hnd/clause1<string,(),prat-rate,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1279 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_record_request = _con_x1279->_fun_record_request;
    return kk_std_core_hnd__clause1_dup(_fun_record_request, _ctx);
  }
}
 
// Call the `fun record-request` operation of the effect `:prat-rate`

static inline kk_unit_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_request(kk_string_t ctxt, kk_context_t* _ctx) { /* (ctxt : string) -> prat-rate () */ 
  kk_std_core_hnd__ev ev_10122 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-rate>*/;
  kk_box_t _x_x1280;
  {
    struct kk_std_core_hnd_Ev* _con_x1281 = kk_std_core_hnd__as_Ev(ev_10122, _ctx);
    kk_box_t _box_x38 = _con_x1281->hnd;
    int32_t m = _con_x1281->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_unbox(_box_x38, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1282 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1282->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1282->_fun_check_limit;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1282->_fun_get_quota_remaining;
      kk_std_core_hnd__clause1 _fun_record_request = _con_x1282->_fun_record_request;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_record_request, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x42 = _fun_record_request.clause;
        _x_x1280 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x42, (_fun_unbox_x42, m, ev_10122, kk_string_box(ctxt), _ctx), _ctx); /*10010*/
      }
    }
  }
  kk_unit_unbox(_x_x1280); return kk_Unit;
}
 
// Automatically generated. Retrieves the `@fun-get-quota-remaining` constructor field of the `:prat-rate` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_rate_fs__fun_get_quota_remaining(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate _this, kk_context_t* _ctx) { /* forall<e,a> (prat-rate<e,a>) -> hnd/clause0<int,prat-rate,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1283 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1283->_fun_get_quota_remaining;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `get-quota-remaining` operation out of effect `:prat-rate`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_quota_remaining_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-rate<e,a>) -> hnd/clause0<int,prat-rate,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1284 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_get_quota_remaining = _con_x1284->_fun_get_quota_remaining;
    return kk_std_core_hnd__clause0_dup(_fun_get_quota_remaining, _ctx);
  }
}
 
// Call the `fun get-quota-remaining` operation of the effect `:prat-rate`

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_quota_remaining(kk_context_t* _ctx) { /* () -> prat-rate int */ 
  kk_std_core_hnd__ev ev_10125 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-rate>*/;
  kk_box_t _x_x1285;
  {
    struct kk_std_core_hnd_Ev* _con_x1286 = kk_std_core_hnd__as_Ev(ev_10125, _ctx);
    kk_box_t _box_x46 = _con_x1286->hnd;
    int32_t m = _con_x1286->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_unbox(_box_x46, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_rate_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_rate* _con_x1287 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_rate(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1287->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1287->_fun_check_limit;
      kk_std_core_hnd__clause0 _fun_get_quota_remaining = _con_x1287->_fun_get_quota_remaining;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1287->_fun_record_request;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_get_quota_remaining, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x49 = _fun_get_quota_remaining.clause;
        _x_x1285 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x49, (_fun_unbox_x49, m, ev_10125, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_integer_unbox(_x_x1285, _ctx);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:prat-route` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_route_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _this, kk_context_t* _ctx) { /* forall<e,a> (prat-route<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1288 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(_this, _ctx);
    kk_integer_t _x = _con_x1288->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_route_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_route_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : prat-route<e,b>, ret : (res : a) -> e b, action : () -> <prat-route|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-dispatch-tool` constructor field of the `:prat-route` type.

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_route_fs__fun_dispatch_tool(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _this, kk_context_t* _ctx) { /* forall<e,a> (prat-route<e,a>) -> hnd/clause2<string,string,string,prat-route,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1292 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(_this, _ctx);
    kk_std_core_hnd__clause2 _x = _con_x1292->_fun_dispatch_tool;
    return kk_std_core_hnd__clause2_dup(_x, _ctx);
  }
}
 
// select `dispatch-tool` operation out of effect `:prat-route`

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_dispatch_tool_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-route<e,a>) -> hnd/clause2<string,string,string,prat-route,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1293 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(hnd, _ctx);
    kk_std_core_hnd__clause2 _fun_dispatch_tool = _con_x1293->_fun_dispatch_tool;
    return kk_std_core_hnd__clause2_dup(_fun_dispatch_tool, _ctx);
  }
}
 
// Call the `fun dispatch-tool` operation of the effect `:prat-route`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_dispatch_tool(kk_string_t tool_name, kk_string_t args, kk_context_t* _ctx) { /* (tool-name : string, args : string) -> prat-route string */ 
  kk_std_core_hnd__ev evx_10128 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-route>*/;
  kk_box_t _x_x1294;
  {
    struct kk_std_core_hnd_Ev* _con_x1295 = kk_std_core_hnd__as_Ev(evx_10128, _ctx);
    kk_box_t _box_x60 = _con_x1295->hnd;
    int32_t m = _con_x1295->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_unbox(_box_x60, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1296 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1296->_cfc;
      kk_std_core_hnd__clause2 _fun_dispatch_tool = _con_x1296->_fun_dispatch_tool;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1296->_fun_get_tool_metadata;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1296->_fun_list_available_tools;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause2_dup(_fun_dispatch_tool, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x65 = _fun_dispatch_tool.clause;
        _x_x1294 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_box_t, kk_context_t*), _fun_unbox_x65, (_fun_unbox_x65, m, evx_10128, kk_string_box(tool_name), kk_string_box(args), _ctx), _ctx); /*10016*/
      }
    }
  }
  return kk_string_unbox(_x_x1294);
}
 
// Automatically generated. Retrieves the `@fun-get-tool-metadata` constructor field of the `:prat-route` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_route_fs__fun_get_tool_metadata(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _this, kk_context_t* _ctx) { /* forall<e,a> (prat-route<e,a>) -> hnd/clause1<string,string,prat-route,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1297 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1297->_fun_get_tool_metadata;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `get-tool-metadata` operation out of effect `:prat-route`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_tool_metadata_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-route<e,a>) -> hnd/clause1<string,string,prat-route,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1298 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_get_tool_metadata = _con_x1298->_fun_get_tool_metadata;
    return kk_std_core_hnd__clause1_dup(_fun_get_tool_metadata, _ctx);
  }
}
 
// Call the `fun get-tool-metadata` operation of the effect `:prat-route`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_tool_metadata(kk_string_t tool_name, kk_context_t* _ctx) { /* (tool-name : string) -> prat-route string */ 
  kk_std_core_hnd__ev ev_10132 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-route>*/;
  kk_box_t _x_x1299;
  {
    struct kk_std_core_hnd_Ev* _con_x1300 = kk_std_core_hnd__as_Ev(ev_10132, _ctx);
    kk_box_t _box_x70 = _con_x1300->hnd;
    int32_t m = _con_x1300->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_unbox(_box_x70, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1301 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1301->_cfc;
      kk_std_core_hnd__clause2 _pat_1_0 = _con_x1301->_fun_dispatch_tool;
      kk_std_core_hnd__clause1 _fun_get_tool_metadata = _con_x1301->_fun_get_tool_metadata;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1301->_fun_list_available_tools;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause2_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_get_tool_metadata, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x74 = _fun_get_tool_metadata.clause;
        _x_x1299 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x74, (_fun_unbox_x74, m, ev_10132, kk_string_box(tool_name), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_string_unbox(_x_x1299);
}
 
// Automatically generated. Retrieves the `@fun-list-available-tools` constructor field of the `:prat-route` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_route_fs__fun_list_available_tools(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route _this, kk_context_t* _ctx) { /* forall<e,a> (prat-route<e,a>) -> hnd/clause0<list<string>,prat-route,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1302 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1302->_fun_list_available_tools;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `list-available-tools` operation out of effect `:prat-route`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_list_available_tools_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-route<e,a>) -> hnd/clause0<list<string>,prat-route,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1303 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_list_available_tools = _con_x1303->_fun_list_available_tools;
    return kk_std_core_hnd__clause0_dup(_fun_list_available_tools, _ctx);
  }
}
 
// Call the `fun list-available-tools` operation of the effect `:prat-route`

static inline kk_std_core_types__list kk_polyglot_whitemagic_dash_koka_src_effects_prat_list_available_tools(kk_context_t* _ctx) { /* () -> prat-route list<string> */ 
  kk_std_core_hnd__ev ev_10135 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-route>*/;
  kk_box_t _x_x1304;
  {
    struct kk_std_core_hnd_Ev* _con_x1305 = kk_std_core_hnd__as_Ev(ev_10135, _ctx);
    kk_box_t _box_x78 = _con_x1305->hnd;
    int32_t m = _con_x1305->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_unbox(_box_x78, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_route_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_route* _con_x1306 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_route(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1306->_cfc;
      kk_std_core_hnd__clause2 _pat_1_0 = _con_x1306->_fun_dispatch_tool;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1306->_fun_get_tool_metadata;
      kk_std_core_hnd__clause0 _fun_list_available_tools = _con_x1306->_fun_list_available_tools;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause2_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_list_available_tools, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x81 = _fun_list_available_tools.clause;
        _x_x1304 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x81, (_fun_unbox_x81, m, ev_10135, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_std_core_types__list_unbox(_x_x1304, KK_OWNED, _ctx);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:prat-karma` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_karma_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _this, kk_context_t* _ctx) { /* forall<e,a> (prat-karma<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1307 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(_this, _ctx);
    kk_integer_t _x = _con_x1307->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_karma_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_karma_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : prat-karma<e,b>, ret : (res : a) -> e b, action : () -> <prat-karma|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-log-operation` constructor field of the `:prat-karma` type.

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_karma_fs__fun_log_operation(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _this, kk_context_t* _ctx) { /* forall<e,a> (prat-karma<e,a>) -> hnd/clause2<string,string,(),prat-karma,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1311 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(_this, _ctx);
    kk_std_core_hnd__clause2 _x = _con_x1311->_fun_log_operation;
    return kk_std_core_hnd__clause2_dup(_x, _ctx);
  }
}
 
// select `log-operation` operation out of effect `:prat-karma`

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_log_operation_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-karma<e,a>) -> hnd/clause2<string,string,(),prat-karma,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1312 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(hnd, _ctx);
    kk_std_core_hnd__clause2 _fun_log_operation = _con_x1312->_fun_log_operation;
    return kk_std_core_hnd__clause2_dup(_fun_log_operation, _ctx);
  }
}
 
// Call the `fun log-operation` operation of the effect `:prat-karma`

static inline kk_unit_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_log_operation(kk_string_t ctxt, kk_string_t result, kk_context_t* _ctx) { /* (ctxt : string, result : string) -> prat-karma () */ 
  kk_std_core_hnd__ev evx_10138 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-karma>*/;
  kk_box_t _x_x1313;
  {
    struct kk_std_core_hnd_Ev* _con_x1314 = kk_std_core_hnd__as_Ev(evx_10138, _ctx);
    kk_box_t _box_x92 = _con_x1314->hnd;
    int32_t m = _con_x1314->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_unbox(_box_x92, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1315 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1315->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1315->_fun_calculate_ethics_score;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1315->_fun_get_karmic_trace;
      kk_std_core_hnd__clause2 _fun_log_operation = _con_x1315->_fun_log_operation;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause2_dup(_fun_log_operation, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x97 = _fun_log_operation.clause;
        _x_x1313 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_box_t, kk_context_t*), _fun_unbox_x97, (_fun_unbox_x97, m, evx_10138, kk_string_box(ctxt), kk_string_box(result), _ctx), _ctx); /*10016*/
      }
    }
  }
  kk_unit_unbox(_x_x1313); return kk_Unit;
}
 
// Automatically generated. Retrieves the `@fun-get-karmic-trace` constructor field of the `:prat-karma` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_karma_fs__fun_get_karmic_trace(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _this, kk_context_t* _ctx) { /* forall<e,a> (prat-karma<e,a>) -> hnd/clause1<int,list<string>,prat-karma,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1316 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1316->_fun_get_karmic_trace;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `get-karmic-trace` operation out of effect `:prat-karma`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_karmic_trace_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-karma<e,a>) -> hnd/clause1<int,list<string>,prat-karma,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1317 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_get_karmic_trace = _con_x1317->_fun_get_karmic_trace;
    return kk_std_core_hnd__clause1_dup(_fun_get_karmic_trace, _ctx);
  }
}
 
// Call the `fun get-karmic-trace` operation of the effect `:prat-karma`

static inline kk_std_core_types__list kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_karmic_trace(kk_integer_t limit, kk_context_t* _ctx) { /* (limit : int) -> prat-karma list<string> */ 
  kk_std_core_hnd__ev ev_10142 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-karma>*/;
  kk_box_t _x_x1318;
  {
    struct kk_std_core_hnd_Ev* _con_x1319 = kk_std_core_hnd__as_Ev(ev_10142, _ctx);
    kk_box_t _box_x102 = _con_x1319->hnd;
    int32_t m = _con_x1319->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_unbox(_box_x102, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1320 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1320->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1320->_fun_calculate_ethics_score;
      kk_std_core_hnd__clause1 _fun_get_karmic_trace = _con_x1320->_fun_get_karmic_trace;
      kk_std_core_hnd__clause2 _pat_2_0 = _con_x1320->_fun_log_operation;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause2_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_get_karmic_trace, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x106 = _fun_get_karmic_trace.clause;
        _x_x1318 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x106, (_fun_unbox_x106, m, ev_10142, kk_integer_box(limit, _ctx), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_std_core_types__list_unbox(_x_x1318, KK_OWNED, _ctx);
}
 
// Automatically generated. Retrieves the `@fun-calculate-ethics-score` constructor field of the `:prat-karma` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_karma_fs__fun_calculate_ethics_score(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma _this, kk_context_t* _ctx) { /* forall<e,a> (prat-karma<e,a>) -> hnd/clause1<string,float64,prat-karma,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1321 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1321->_fun_calculate_ethics_score;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `calculate-ethics-score` operation out of effect `:prat-karma`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_calculate_ethics_score_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-karma<e,a>) -> hnd/clause1<string,float64,prat-karma,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1322 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_calculate_ethics_score = _con_x1322->_fun_calculate_ethics_score;
    return kk_std_core_hnd__clause1_dup(_fun_calculate_ethics_score, _ctx);
  }
}
 
// Call the `fun calculate-ethics-score` operation of the effect `:prat-karma`

static inline double kk_polyglot_whitemagic_dash_koka_src_effects_prat_calculate_ethics_score(kk_string_t action, kk_context_t* _ctx) { /* (action : string) -> prat-karma float64 */ 
  kk_std_core_hnd__ev ev_10145 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-karma>*/;
  kk_box_t _x_x1323;
  {
    struct kk_std_core_hnd_Ev* _con_x1324 = kk_std_core_hnd__as_Ev(ev_10145, _ctx);
    kk_box_t _box_x110 = _con_x1324->hnd;
    int32_t m = _con_x1324->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_unbox(_box_x110, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_karma_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_karma* _con_x1325 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_karma(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1325->_cfc;
      kk_std_core_hnd__clause1 _fun_calculate_ethics_score = _con_x1325->_fun_calculate_ethics_score;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1325->_fun_get_karmic_trace;
      kk_std_core_hnd__clause2 _pat_2_0 = _con_x1325->_fun_log_operation;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause2_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_calculate_ethics_score, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x114 = _fun_calculate_ethics_score.clause;
        _x_x1323 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x114, (_fun_unbox_x114, m, ev_10145, kk_string_box(action), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_double_unbox(_x_x1323, KK_OWNED, _ctx);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:prat-resonance` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _this, kk_context_t* _ctx) { /* forall<e,a> (prat-resonance<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1326 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(_this, _ctx);
    kk_integer_t _x = _con_x1326->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : prat-resonance<e,b>, ret : (res : a) -> e b, action : () -> <prat-resonance|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-get-predecessor-gana` constructor field of the `:prat-resonance` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__fun_get_predecessor_gana(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _this, kk_context_t* _ctx) { /* forall<e,a> (prat-resonance<e,a>) -> hnd/clause0<string,prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1330 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1330->_fun_get_predecessor_gana;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `get-predecessor-gana` operation out of effect `:prat-resonance`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_predecessor_gana_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-resonance<e,a>) -> hnd/clause0<string,prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1331 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_get_predecessor_gana = _con_x1331->_fun_get_predecessor_gana;
    return kk_std_core_hnd__clause0_dup(_fun_get_predecessor_gana, _ctx);
  }
}
 
// Call the `fun get-predecessor-gana` operation of the effect `:prat-resonance`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_predecessor_gana(kk_context_t* _ctx) { /* () -> prat-resonance string */ 
  kk_std_core_hnd__ev ev_10149 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-resonance>*/;
  kk_box_t _x_x1332;
  {
    struct kk_std_core_hnd_Ev* _con_x1333 = kk_std_core_hnd__as_Ev(ev_10149, _ctx);
    kk_box_t _box_x126 = _con_x1333->hnd;
    int32_t m = _con_x1333->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_unbox(_box_x126, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1334 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1334->_cfc;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1334->_fun_get_harmony_score;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1334->_fun_get_lunar_phase;
      kk_std_core_hnd__clause0 _fun_get_predecessor_gana = _con_x1334->_fun_get_predecessor_gana;
      kk_std_core_hnd__clause1 _pat_3 = _con_x1334->_fun_record_invocation;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_3, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_get_predecessor_gana, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x129 = _fun_get_predecessor_gana.clause;
        _x_x1332 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x129, (_fun_unbox_x129, m, ev_10149, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_string_unbox(_x_x1332);
}
 
// Automatically generated. Retrieves the `@fun-record-invocation` constructor field of the `:prat-resonance` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__fun_record_invocation(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _this, kk_context_t* _ctx) { /* forall<e,a> (prat-resonance<e,a>) -> hnd/clause1<(string, string, string),(),prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1335 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1335->_fun_record_invocation;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `record-invocation` operation out of effect `:prat-resonance`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_invocation_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-resonance<e,a>) -> hnd/clause1<(string, string, string),(),prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1336 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_record_invocation = _con_x1336->_fun_record_invocation;
    return kk_std_core_hnd__clause1_dup(_fun_record_invocation, _ctx);
  }
}
 
// Call the `fun record-invocation` operation of the effect `:prat-resonance`


// lift anonymous function
struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_invocation_fun1338__t {
  struct kk_function_s _base;
};
extern kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_invocation_fun1338(kk_function_t _fself, kk_box_t _b_x137, kk_context_t* _ctx);
static inline kk_function_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_new_record_invocation_fun1338(kk_context_t* _ctx) {
  kk_define_static_function(_fself, kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_invocation_fun1338, _ctx)
  return kk_function_static_dup(_fself,kk_context());
}


static inline kk_unit_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_record_invocation(kk_string_t gana_name, kk_string_t tool_name, kk_string_t output, kk_context_t* _ctx) { /* (gana-name : string, tool-name : string, output : string) -> prat-resonance () */ 
  kk_std_core_hnd__ev _b_x132_138 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-resonance>*/;
  kk_box_t _x_x1337 = kk_std_core_hnd__perform3(_b_x132_138, kk_polyglot_whitemagic_dash_koka_src_effects_prat_new_record_invocation_fun1338(_ctx), kk_string_box(gana_name), kk_string_box(tool_name), kk_string_box(output), _ctx); /*10003*/
  kk_unit_unbox(_x_x1337); return kk_Unit;
}
 
// Automatically generated. Retrieves the `@fun-get-lunar-phase` constructor field of the `:prat-resonance` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__fun_get_lunar_phase(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _this, kk_context_t* _ctx) { /* forall<e,a> (prat-resonance<e,a>) -> hnd/clause0<float64,prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1339 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1339->_fun_get_lunar_phase;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `get-lunar-phase` operation out of effect `:prat-resonance`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_lunar_phase_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-resonance<e,a>) -> hnd/clause0<float64,prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1340 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_get_lunar_phase = _con_x1340->_fun_get_lunar_phase;
    return kk_std_core_hnd__clause0_dup(_fun_get_lunar_phase, _ctx);
  }
}
 
// Call the `fun get-lunar-phase` operation of the effect `:prat-resonance`

static inline double kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_lunar_phase(kk_context_t* _ctx) { /* () -> prat-resonance float64 */ 
  kk_std_core_hnd__ev ev_10151 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-resonance>*/;
  kk_box_t _x_x1341;
  {
    struct kk_std_core_hnd_Ev* _con_x1342 = kk_std_core_hnd__as_Ev(ev_10151, _ctx);
    kk_box_t _box_x143 = _con_x1342->hnd;
    int32_t m = _con_x1342->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_unbox(_box_x143, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1343 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1343->_cfc;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1343->_fun_get_harmony_score;
      kk_std_core_hnd__clause0 _fun_get_lunar_phase = _con_x1343->_fun_get_lunar_phase;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1343->_fun_get_predecessor_gana;
      kk_std_core_hnd__clause1 _pat_3 = _con_x1343->_fun_record_invocation;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_3, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_get_lunar_phase, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x146 = _fun_get_lunar_phase.clause;
        _x_x1341 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x146, (_fun_unbox_x146, m, ev_10151, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_double_unbox(_x_x1341, KK_OWNED, _ctx);
}
 
// Automatically generated. Retrieves the `@fun-get-harmony-score` constructor field of the `:prat-resonance` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_prat_resonance_fs__fun_get_harmony_score(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance _this, kk_context_t* _ctx) { /* forall<e,a> (prat-resonance<e,a>) -> hnd/clause0<float64,prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1344 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1344->_fun_get_harmony_score;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `get-harmony-score` operation out of effect `:prat-resonance`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_harmony_score_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : prat-resonance<e,a>) -> hnd/clause0<float64,prat-resonance,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1345 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_get_harmony_score = _con_x1345->_fun_get_harmony_score;
    return kk_std_core_hnd__clause0_dup(_fun_get_harmony_score, _ctx);
  }
}
 
// Call the `fun get-harmony-score` operation of the effect `:prat-resonance`

static inline double kk_polyglot_whitemagic_dash_koka_src_effects_prat_get_harmony_score(kk_context_t* _ctx) { /* () -> prat-resonance float64 */ 
  kk_std_core_hnd__ev ev_10153 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/prat-resonance>*/;
  kk_box_t _x_x1346;
  {
    struct kk_std_core_hnd_Ev* _con_x1347 = kk_std_core_hnd__as_Ev(ev_10153, _ctx);
    kk_box_t _box_x149 = _con_x1347->hnd;
    int32_t m = _con_x1347->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_unbox(_box_x149, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__prat_resonance_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_prat_resonance* _con_x1348 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_prat_resonance(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1348->_cfc;
      kk_std_core_hnd__clause0 _fun_get_harmony_score = _con_x1348->_fun_get_harmony_score;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1348->_fun_get_lunar_phase;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1348->_fun_get_predecessor_gana;
      kk_std_core_hnd__clause1 _pat_3 = _con_x1348->_fun_record_invocation;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_3, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_get_harmony_score, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x152 = _fun_get_harmony_score.clause;
        _x_x1346 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x152, (_fun_unbox_x152, m, ev_10153, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_double_unbox(_x_x1346, KK_OWNED, _ctx);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:gana-horn` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_horn_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _this, kk_context_t* _ctx) { /* forall<e,a> (gana-horn<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1349 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(_this, _ctx);
    kk_integer_t _x = _con_x1349->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_horn_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_horn_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : gana-horn<e,b>, ret : (res : a) -> e b, action : () -> <gana-horn|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-bootstrap-session` constructor field of the `:gana-horn` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_horn_fs__fun_bootstrap_session(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _this, kk_context_t* _ctx) { /* forall<e,a> (gana-horn<e,a>) -> hnd/clause1<string,string,gana-horn,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1353 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1353->_fun_bootstrap_session;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `bootstrap-session` operation out of effect `:gana-horn`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_bootstrap_session_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-horn<e,a>) -> hnd/clause1<string,string,gana-horn,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1354 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_bootstrap_session = _con_x1354->_fun_bootstrap_session;
    return kk_std_core_hnd__clause1_dup(_fun_bootstrap_session, _ctx);
  }
}
 
// Call the `fun bootstrap-session` operation of the effect `:gana-horn`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_bootstrap_session(kk_string_t config, kk_context_t* _ctx) { /* (config : string) -> gana-horn string */ 
  kk_std_core_hnd__ev ev_10156 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-horn>*/;
  kk_box_t _x_x1355;
  {
    struct kk_std_core_hnd_Ev* _con_x1356 = kk_std_core_hnd__as_Ev(ev_10156, _ctx);
    kk_box_t _box_x163 = _con_x1356->hnd;
    int32_t m = _con_x1356->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_unbox(_box_x163, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1357 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1357->_cfc;
      kk_std_core_hnd__clause1 _fun_bootstrap_session = _con_x1357->_fun_bootstrap_session;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1357->_fun_create_session;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1357->_fun_resume_session;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_bootstrap_session, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x167 = _fun_bootstrap_session.clause;
        _x_x1355 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x167, (_fun_unbox_x167, m, ev_10156, kk_string_box(config), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_string_unbox(_x_x1355);
}
 
// Automatically generated. Retrieves the `@fun-create-session` constructor field of the `:gana-horn` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_horn_fs__fun_create_session(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _this, kk_context_t* _ctx) { /* forall<e,a> (gana-horn<e,a>) -> hnd/clause1<string,string,gana-horn,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1358 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1358->_fun_create_session;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `create-session` operation out of effect `:gana-horn`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_create_session_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-horn<e,a>) -> hnd/clause1<string,string,gana-horn,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1359 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_create_session = _con_x1359->_fun_create_session;
    return kk_std_core_hnd__clause1_dup(_fun_create_session, _ctx);
  }
}
 
// Call the `fun create-session` operation of the effect `:gana-horn`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_create_session(kk_string_t params, kk_context_t* _ctx) { /* (params : string) -> gana-horn string */ 
  kk_std_core_hnd__ev ev_10159 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-horn>*/;
  kk_box_t _x_x1360;
  {
    struct kk_std_core_hnd_Ev* _con_x1361 = kk_std_core_hnd__as_Ev(ev_10159, _ctx);
    kk_box_t _box_x171 = _con_x1361->hnd;
    int32_t m = _con_x1361->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_unbox(_box_x171, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1362 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1362->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1362->_fun_bootstrap_session;
      kk_std_core_hnd__clause1 _fun_create_session = _con_x1362->_fun_create_session;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1362->_fun_resume_session;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_create_session, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x175 = _fun_create_session.clause;
        _x_x1360 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x175, (_fun_unbox_x175, m, ev_10159, kk_string_box(params), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_string_unbox(_x_x1360);
}
 
// Automatically generated. Retrieves the `@fun-resume-session` constructor field of the `:gana-horn` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_horn_fs__fun_resume_session(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn _this, kk_context_t* _ctx) { /* forall<e,a> (gana-horn<e,a>) -> hnd/clause1<string,bool,gana-horn,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1363 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1363->_fun_resume_session;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `resume-session` operation out of effect `:gana-horn`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_resume_session_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-horn<e,a>) -> hnd/clause1<string,bool,gana-horn,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1364 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_resume_session = _con_x1364->_fun_resume_session;
    return kk_std_core_hnd__clause1_dup(_fun_resume_session, _ctx);
  }
}
 
// Call the `fun resume-session` operation of the effect `:gana-horn`

static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat_resume_session(kk_string_t session_id, kk_context_t* _ctx) { /* (session-id : string) -> gana-horn bool */ 
  kk_std_core_hnd__ev ev_10162 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-horn>*/;
  kk_box_t _x_x1365;
  {
    struct kk_std_core_hnd_Ev* _con_x1366 = kk_std_core_hnd__as_Ev(ev_10162, _ctx);
    kk_box_t _box_x179 = _con_x1366->hnd;
    int32_t m = _con_x1366->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_unbox(_box_x179, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_horn_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_horn* _con_x1367 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_horn(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1367->_cfc;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1367->_fun_bootstrap_session;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1367->_fun_create_session;
      kk_std_core_hnd__clause1 _fun_resume_session = _con_x1367->_fun_resume_session;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_resume_session, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x183 = _fun_resume_session.clause;
        _x_x1365 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x183, (_fun_unbox_x183, m, ev_10162, kk_string_box(session_id), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_bool_unbox(_x_x1365);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:gana-neck` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_neck_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _this, kk_context_t* _ctx) { /* forall<e,a> (gana-neck<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1368 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(_this, _ctx);
    kk_integer_t _x = _con_x1368->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_neck_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_neck_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : gana-neck<e,b>, ret : (res : a) -> e b, action : () -> <gana-neck|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-create-memory` constructor field of the `:gana-neck` type.

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_neck_fs__fun_create_memory(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _this, kk_context_t* _ctx) { /* forall<e,a> (gana-neck<e,a>) -> hnd/clause2<string,float64,string,gana-neck,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1372 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(_this, _ctx);
    kk_std_core_hnd__clause2 _x = _con_x1372->_fun_create_memory;
    return kk_std_core_hnd__clause2_dup(_x, _ctx);
  }
}
 
// select `create-memory` operation out of effect `:gana-neck`

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_create_memory_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-neck<e,a>) -> hnd/clause2<string,float64,string,gana-neck,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1373 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(hnd, _ctx);
    kk_std_core_hnd__clause2 _fun_create_memory = _con_x1373->_fun_create_memory;
    return kk_std_core_hnd__clause2_dup(_fun_create_memory, _ctx);
  }
}
 
// Call the `fun create-memory` operation of the effect `:gana-neck`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_create_memory(kk_string_t content, double importance, kk_context_t* _ctx) { /* (content : string, importance : float64) -> gana-neck string */ 
  kk_std_core_hnd__ev evx_10166 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-neck>*/;
  kk_box_t _x_x1374;
  {
    struct kk_std_core_hnd_Ev* _con_x1375 = kk_std_core_hnd__as_Ev(evx_10166, _ctx);
    kk_box_t _box_x195 = _con_x1375->hnd;
    int32_t m = _con_x1375->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_unbox(_box_x195, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1376 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1376->_cfc;
      kk_std_core_hnd__clause2 _fun_create_memory = _con_x1376->_fun_create_memory;
      kk_std_core_hnd__clause1 _pat_1_0 = _con_x1376->_fun_import_memories;
      kk_std_core_hnd__clause2 _pat_2_0 = _con_x1376->_fun_update_memory;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause2_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause1_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause2_dup(_fun_create_memory, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x200 = _fun_create_memory.clause;
        _x_x1374 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_box_t, kk_context_t*), _fun_unbox_x200, (_fun_unbox_x200, m, evx_10166, kk_string_box(content), kk_double_box(importance, _ctx), _ctx), _ctx); /*10016*/
      }
    }
  }
  return kk_string_unbox(_x_x1374);
}
 
// Automatically generated. Retrieves the `@fun-update-memory` constructor field of the `:gana-neck` type.

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_neck_fs__fun_update_memory(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _this, kk_context_t* _ctx) { /* forall<e,a> (gana-neck<e,a>) -> hnd/clause2<string,string,bool,gana-neck,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1377 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(_this, _ctx);
    kk_std_core_hnd__clause2 _x = _con_x1377->_fun_update_memory;
    return kk_std_core_hnd__clause2_dup(_x, _ctx);
  }
}
 
// select `update-memory` operation out of effect `:gana-neck`

static inline kk_std_core_hnd__clause2 kk_polyglot_whitemagic_dash_koka_src_effects_prat_update_memory_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-neck<e,a>) -> hnd/clause2<string,string,bool,gana-neck,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1378 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(hnd, _ctx);
    kk_std_core_hnd__clause2 _fun_update_memory = _con_x1378->_fun_update_memory;
    return kk_std_core_hnd__clause2_dup(_fun_update_memory, _ctx);
  }
}
 
// Call the `fun update-memory` operation of the effect `:gana-neck`

static inline bool kk_polyglot_whitemagic_dash_koka_src_effects_prat_update_memory(kk_string_t id, kk_string_t content, kk_context_t* _ctx) { /* (id : string, content : string) -> gana-neck bool */ 
  kk_std_core_hnd__ev evx_10170 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-neck>*/;
  kk_box_t _x_x1379;
  {
    struct kk_std_core_hnd_Ev* _con_x1380 = kk_std_core_hnd__as_Ev(evx_10170, _ctx);
    kk_box_t _box_x205 = _con_x1380->hnd;
    int32_t m = _con_x1380->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_unbox(_box_x205, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1381 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1381->_cfc;
      kk_std_core_hnd__clause2 _pat_1_0 = _con_x1381->_fun_create_memory;
      kk_std_core_hnd__clause1 _pat_2_0 = _con_x1381->_fun_import_memories;
      kk_std_core_hnd__clause2 _fun_update_memory = _con_x1381->_fun_update_memory;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause1_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause2_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause2_dup(_fun_update_memory, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x210 = _fun_update_memory.clause;
        _x_x1379 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_box_t, kk_context_t*), _fun_unbox_x210, (_fun_unbox_x210, m, evx_10170, kk_string_box(id), kk_string_box(content), _ctx), _ctx); /*10016*/
      }
    }
  }
  return kk_bool_unbox(_x_x1379);
}
 
// Automatically generated. Retrieves the `@fun-import-memories` constructor field of the `:gana-neck` type.

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_neck_fs__fun_import_memories(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck _this, kk_context_t* _ctx) { /* forall<e,a> (gana-neck<e,a>) -> hnd/clause1<string,int,gana-neck,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1382 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(_this, _ctx);
    kk_std_core_hnd__clause1 _x = _con_x1382->_fun_import_memories;
    return kk_std_core_hnd__clause1_dup(_x, _ctx);
  }
}
 
// select `import-memories` operation out of effect `:gana-neck`

static inline kk_std_core_hnd__clause1 kk_polyglot_whitemagic_dash_koka_src_effects_prat_import_memories_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-neck<e,a>) -> hnd/clause1<string,int,gana-neck,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1383 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(hnd, _ctx);
    kk_std_core_hnd__clause1 _fun_import_memories = _con_x1383->_fun_import_memories;
    return kk_std_core_hnd__clause1_dup(_fun_import_memories, _ctx);
  }
}
 
// Call the `fun import-memories` operation of the effect `:gana-neck`

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_import_memories(kk_string_t source, kk_context_t* _ctx) { /* (source : string) -> gana-neck int */ 
  kk_std_core_hnd__ev ev_10174 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-neck>*/;
  kk_box_t _x_x1384;
  {
    struct kk_std_core_hnd_Ev* _con_x1385 = kk_std_core_hnd__as_Ev(ev_10174, _ctx);
    kk_box_t _box_x215 = _con_x1385->hnd;
    int32_t m = _con_x1385->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_unbox(_box_x215, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_neck_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_neck* _con_x1386 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_neck(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1386->_cfc;
      kk_std_core_hnd__clause2 _pat_1_0 = _con_x1386->_fun_create_memory;
      kk_std_core_hnd__clause1 _fun_import_memories = _con_x1386->_fun_import_memories;
      kk_std_core_hnd__clause2 _pat_2_0 = _con_x1386->_fun_update_memory;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause2_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause2_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause1_dup(_fun_import_memories, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x219 = _fun_import_memories.clause;
        _x_x1384 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_box_t, kk_context_t*), _fun_unbox_x219, (_fun_unbox_x219, m, ev_10174, kk_string_box(source), _ctx), _ctx); /*10010*/
      }
    }
  }
  return kk_integer_unbox(_x_x1384, _ctx);
}
 
// Automatically generated. Retrieves the `@cfc` constructor field of the `:gana-root` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_root_fs__cfc(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _this, kk_context_t* _ctx) { /* forall<e,a> (gana-root<e,a>) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1387 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(_this, _ctx);
    kk_integer_t _x = _con_x1387->_cfc;
    return kk_integer_dup(_x, _ctx);
  }
}

extern kk_std_core_hnd__htag kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_root_fs__tag;

kk_box_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_root_fs__handle(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root hnd, kk_function_t ret, kk_function_t action, kk_context_t* _ctx); /* forall<a,e,b> (hnd : gana-root<e,b>, ret : (res : a) -> e b, action : () -> <gana-root|e> a) -> e b */ 
 
// Automatically generated. Retrieves the `@fun-health-report` constructor field of the `:gana-root` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_root_fs__fun_health_report(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _this, kk_context_t* _ctx) { /* forall<e,a> (gana-root<e,a>) -> hnd/clause0<string,gana-root,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1391 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1391->_fun_health_report;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `health-report` operation out of effect `:gana-root`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_health_report_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-root<e,a>) -> hnd/clause0<string,gana-root,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1392 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_health_report = _con_x1392->_fun_health_report;
    return kk_std_core_hnd__clause0_dup(_fun_health_report, _ctx);
  }
}
 
// Call the `fun health-report` operation of the effect `:gana-root`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_health_report(kk_context_t* _ctx) { /* () -> gana-root string */ 
  kk_std_core_hnd__ev ev_10178 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-root>*/;
  kk_box_t _x_x1393;
  {
    struct kk_std_core_hnd_Ev* _con_x1394 = kk_std_core_hnd__as_Ev(ev_10178, _ctx);
    kk_box_t _box_x231 = _con_x1394->hnd;
    int32_t m = _con_x1394->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_unbox(_box_x231, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1395 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1395->_cfc;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1395->_fun_check_ship;
      kk_std_core_hnd__clause0 _fun_health_report = _con_x1395->_fun_health_report;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1395->_fun_rust_status;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_health_report, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x234 = _fun_health_report.clause;
        _x_x1393 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x234, (_fun_unbox_x234, m, ev_10178, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_string_unbox(_x_x1393);
}
 
// Automatically generated. Retrieves the `@fun-rust-status` constructor field of the `:gana-root` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_root_fs__fun_rust_status(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _this, kk_context_t* _ctx) { /* forall<e,a> (gana-root<e,a>) -> hnd/clause0<string,gana-root,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1396 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1396->_fun_rust_status;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `rust-status` operation out of effect `:gana-root`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_rust_status_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-root<e,a>) -> hnd/clause0<string,gana-root,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1397 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_rust_status = _con_x1397->_fun_rust_status;
    return kk_std_core_hnd__clause0_dup(_fun_rust_status, _ctx);
  }
}
 
// Call the `fun rust-status` operation of the effect `:gana-root`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_rust_status(kk_context_t* _ctx) { /* () -> gana-root string */ 
  kk_std_core_hnd__ev ev_10180 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-root>*/;
  kk_box_t _x_x1398;
  {
    struct kk_std_core_hnd_Ev* _con_x1399 = kk_std_core_hnd__as_Ev(ev_10180, _ctx);
    kk_box_t _box_x237 = _con_x1399->hnd;
    int32_t m = _con_x1399->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_unbox(_box_x237, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1400 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1400->_cfc;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1400->_fun_check_ship;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1400->_fun_health_report;
      kk_std_core_hnd__clause0 _fun_rust_status = _con_x1400->_fun_rust_status;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_rust_status, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x240 = _fun_rust_status.clause;
        _x_x1398 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x240, (_fun_unbox_x240, m, ev_10180, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_string_unbox(_x_x1398);
}
 
// Automatically generated. Retrieves the `@fun-check-ship` constructor field of the `:gana-root` type.

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_root_fs__fun_check_ship(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root _this, kk_context_t* _ctx) { /* forall<e,a> (gana-root<e,a>) -> hnd/clause0<string,gana-root,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1401 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(_this, _ctx);
    kk_std_core_hnd__clause0 _x = _con_x1401->_fun_check_ship;
    return kk_std_core_hnd__clause0_dup(_x, _ctx);
  }
}
 
// select `check-ship` operation out of effect `:gana-root`

static inline kk_std_core_hnd__clause0 kk_polyglot_whitemagic_dash_koka_src_effects_prat_check_ship_fs__select(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root hnd, kk_context_t* _ctx) { /* forall<e,a> (hnd : gana-root<e,a>) -> hnd/clause0<string,gana-root,e,a> */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1402 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(hnd, _ctx);
    kk_std_core_hnd__clause0 _fun_check_ship = _con_x1402->_fun_check_ship;
    return kk_std_core_hnd__clause0_dup(_fun_check_ship, _ctx);
  }
}
 
// Call the `fun check-ship` operation of the effect `:gana-root`

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_check_ship(kk_context_t* _ctx) { /* () -> gana-root string */ 
  kk_std_core_hnd__ev ev_10182 = kk_evv_at(((KK_IZ(0))),kk_context()); /*hnd/ev<polyglot/whitemagic-koka/src/effects/prat/gana-root>*/;
  kk_box_t _x_x1403;
  {
    struct kk_std_core_hnd_Ev* _con_x1404 = kk_std_core_hnd__as_Ev(ev_10182, _ctx);
    kk_box_t _box_x243 = _con_x1404->hnd;
    int32_t m = _con_x1404->marker;
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root h = kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_unbox(_box_x243, KK_BORROWED, _ctx);
    kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_root_dup(h, _ctx);
    {
      struct kk_polyglot_whitemagic_dash_koka_src_effects_prat__Hnd_gana_root* _con_x1405 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Hnd_gana_root(h, _ctx);
      kk_integer_t _pat_0_0 = _con_x1405->_cfc;
      kk_std_core_hnd__clause0 _fun_check_ship = _con_x1405->_fun_check_ship;
      kk_std_core_hnd__clause0 _pat_1_0 = _con_x1405->_fun_health_report;
      kk_std_core_hnd__clause0 _pat_2_0 = _con_x1405->_fun_rust_status;
      if kk_likely(kk_datatype_ptr_is_unique(h, _ctx)) {
        kk_std_core_hnd__clause0_drop(_pat_2_0, _ctx);
        kk_std_core_hnd__clause0_drop(_pat_1_0, _ctx);
        kk_integer_drop(_pat_0_0, _ctx);
        kk_datatype_ptr_free(h, _ctx);
      }
      else {
        kk_std_core_hnd__clause0_dup(_fun_check_ship, _ctx);
        kk_datatype_ptr_decref(h, _ctx);
      }
      {
        kk_function_t _fun_unbox_x246 = _fun_check_ship.clause;
        _x_x1403 = kk_function_call(kk_box_t, (kk_function_t, int32_t, kk_std_core_hnd__ev, kk_context_t*), _fun_unbox_x246, (_fun_unbox_x246, m, ev_10182, _ctx), _ctx); /*10005*/
      }
    }
  }
  return kk_string_unbox(_x_x1403);
}

extern kk_function_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_handle_prat_auth_production;

extern kk_function_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_handle_prat_rate_production;

extern kk_function_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_handle_prat_route_production;

extern kk_function_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_handle_prat_karma_production;
 
// monadic lift

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10103(kk_string_t result, kk_unit_t wild___3, kk_context_t* _ctx) { /* (result : string, wild_@3 : ()) -> <prat-resonance,prat-karma,prat-route,prat-rate,exn,prat-auth> string */ 
  return result;
}

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10104(kk_string_t result, kk_string_t tool_name, kk_unit_t wild___2, kk_context_t* _ctx); /* (result : string, tool-name : string, wild_@2 : ()) -> <prat-karma,prat-resonance,prat-route,prat-rate,exn,prat-auth> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10105(kk_string_t ctxt, kk_string_t tool_name, kk_string_t result, kk_context_t* _ctx); /* (ctxt : string, tool-name : string, result : string) -> <prat-route,prat-karma,prat-resonance,prat-rate,exn,prat-auth> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10106(kk_string_t args, kk_string_t ctxt, kk_string_t tool_name, kk_string_t predecessor, kk_context_t* _ctx); /* (args : string, ctxt : string, tool-name : string, predecessor : string) -> <prat-resonance,prat-karma,prat-route,prat-rate,exn,prat-auth> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10107(kk_string_t args, kk_string_t ctxt, kk_string_t tool_name, kk_unit_t wild___1, kk_context_t* _ctx); /* (args : string, ctxt : string, tool-name : string, wild_@1 : ()) -> <prat-rate,prat-karma,prat-resonance,prat-route,exn,prat-auth> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10108(kk_string_t args, kk_string_t ctxt, kk_string_t tool_name, kk_unit_t _c_x10064, kk_context_t* _ctx); /* (args : string, ctxt : string, tool-name : string, ()) -> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10109(kk_string_t args, kk_string_t ctxt, kk_string_t tool_name, bool _y_x10062, kk_context_t* _ctx); /* (args : string, ctxt : string, tool-name : string, bool) -> <prat-rate,exn,prat-karma,prat-resonance,prat-route,prat-auth> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10110(kk_string_t args, kk_string_t ctxt, kk_string_t tool_name, kk_unit_t _c_x10060, kk_context_t* _ctx); /* (args : string, ctxt : string, tool-name : string, ()) -> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat__mlift_route_prat_call_10111(kk_string_t args, kk_string_t ctxt, kk_string_t tool_name, bool _y_x10058, kk_context_t* _ctx); /* (args : string, ctxt : string, tool-name : string, bool) -> <prat-auth,exn,prat-karma,prat-rate,prat-resonance,prat-route> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_route_prat_call(kk_string_t tool_name, kk_string_t ctxt, kk_string_t args, kk_context_t* _ctx); /* (tool-name : string, ctxt : string, args : string) -> <exn,prat-auth,prat-karma,prat-rate,prat-resonance,prat-route> string */ 

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_dispatch_gana(kk_string_t gana_name, kk_string_t tool, kk_string_t args, kk_context_t* _ctx) { /* (gana-name : string, tool : string, args : string) -> <exn,prat-auth,prat-karma,prat-rate,prat-resonance,prat-route> string */ 
  kk_string_t _x_x1672;
  kk_string_t _x_x1673;
  kk_define_string_literal(, _s_x1674, 5, "gana:", _ctx)
  _x_x1673 = kk_string_dup(_s_x1674, _ctx); /*string*/
  _x_x1672 = kk_std_core_types__lp__plus__plus__rp_(_x_x1673, gana_name, _ctx); /*string*/
  return kk_polyglot_whitemagic_dash_koka_src_effects_prat_route_prat_call(tool, _x_x1672, args, _ctx);
}
 
// Automatically generated. Retrieves the `chinese` constructor field of the `:gana-meta` type.

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs_chinese(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> string */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con_x1675 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(_this, _ctx);
    kk_string_t _x = _con_x1675->chinese;
    return kk_string_dup(_x, _ctx);
  }
}
 
// Automatically generated. Retrieves the `garden` constructor field of the `:gana-meta` type.

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs_garden(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> string */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con_x1676 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(_this, _ctx);
    kk_string_t _x = _con_x1676->garden;
    return kk_string_dup(_x, _ctx);
  }
}
 
// Automatically generated. Retrieves the `mansion-num` constructor field of the `:gana-meta` type.

static inline kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs_mansion_num(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> int */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con_x1677 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(_this, _ctx);
    kk_integer_t _x = _con_x1677->mansion_num;
    return kk_integer_dup(_x, _ctx);
  }
}
 
// Automatically generated. Retrieves the `meaning` constructor field of the `:gana-meta` type.

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs_meaning(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> string */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con_x1678 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(_this, _ctx);
    kk_string_t _x = _con_x1678->meaning;
    return kk_string_dup(_x, _ctx);
  }
}
 
// Automatically generated. Retrieves the `pinyin` constructor field of the `:gana-meta` type.

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs_pinyin(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> string */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con_x1679 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(_this, _ctx);
    kk_string_t _x = _con_x1679->pinyin;
    return kk_string_dup(_x, _ctx);
  }
}
 
// Automatically generated. Retrieves the `quadrant` constructor field of the `:gana-meta` type.

static inline kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs_quadrant(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_context_t* _ctx) { /* (gana-meta) -> string */ 
  {
    struct kk_polyglot_whitemagic_dash_koka_src_effects_prat_Gana_meta* _con_x1680 = kk_polyglot_whitemagic_dash_koka_src_effects_prat__as_Gana_meta(_this, _ctx);
    kk_string_t _x = _con_x1680->quadrant;
    return kk_string_dup(_x, _ctx);
  }
}

kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_meta_fs__copy(kk_polyglot_whitemagic_dash_koka_src_effects_prat__gana_meta _this, kk_std_core_types__optional mansion_num, kk_std_core_types__optional quadrant, kk_std_core_types__optional meaning, kk_std_core_types__optional garden, kk_std_core_types__optional chinese, kk_std_core_types__optional pinyin, kk_context_t* _ctx); /* (gana-meta, mansion-num : ? int, quadrant : ? string, meaning : ? string, garden : ? string, chinese : ? string, pinyin : ? string) -> gana-meta */ 

kk_std_core_types__list kk_polyglot_whitemagic_dash_koka_src_effects_prat_gana_metadata(kk_context_t* _ctx); /* () -> list<(string, gana-meta)> */ 

kk_integer_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_find_index(kk_std_core_types__list list, kk_string_t target, kk_context_t* _ctx); /* (list : list<string>, target : string) -> int */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_lookup_predecessor_gana(kk_string_t gana_name, kk_context_t* _ctx); /* (gana-name : string) -> string */ 

kk_string_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_lookup_successor_gana(kk_string_t gana_name, kk_context_t* _ctx); /* (gana-name : string) -> string */ 
 
// Dummy main for compilation testing

static inline kk_unit_t kk_polyglot_whitemagic_dash_koka_src_effects_prat_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t _x_x2426;
  kk_define_string_literal(, _s_x2427, 26, "prat_effects module loaded", _ctx)
  _x_x2426 = kk_string_dup(_s_x2427, _ctx); /*string*/
  kk_std_core_console_printsln(_x_x2426, _ctx); return kk_Unit;
}

void kk_polyglot_whitemagic_dash_koka_src_effects_prat__init(kk_context_t* _ctx);


void kk_polyglot_whitemagic_dash_koka_src_effects_prat__done(kk_context_t* _ctx);

#endif // header
