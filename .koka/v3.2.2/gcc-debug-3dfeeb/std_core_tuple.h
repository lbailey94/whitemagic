#pragma once
#ifndef kk_std_core_tuple_H
#define kk_std_core_tuple_H
// Koka generated module: std/core/tuple, koka version: 3.2.2, platform: 64-bit
#include <kklib.h>
#include "std_core_types.h"
#include "std_core_hnd.h"

// type declarations

// value declarations
 
// monadic lift

static inline kk_std_core_types__tuple2 kk_std_core_tuple_tuple2_fs__mlift_map_10121(kk_box_t _y_x10000, kk_box_t _y_x10001, kk_context_t* _ctx) { /* forall<a,e> (a, a) -> e (a, a) */ 
  return kk_std_core_types__new_Tuple2(_y_x10000, _y_x10001, _ctx);
}

kk_std_core_types__tuple2 kk_std_core_tuple_tuple2_fs__mlift_map_10122(kk_function_t f, kk_std_core_types__tuple2 t, kk_box_t _y_x10000, kk_context_t* _ctx); /* forall<a,b,e> (f : (a) -> e b, t : (a, a), b) -> e (b, b) */ 

kk_std_core_types__tuple2 kk_std_core_tuple_tuple2_fs_map(kk_std_core_types__tuple2 t, kk_function_t f, kk_context_t* _ctx); /* forall<a,b,e> (t : (a, a), f : (a) -> e b) -> e (b, b) */ 
 
// monadic lift

static inline kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs__mlift_map_10123(kk_box_t _y_x10002, kk_box_t _y_x10003, kk_box_t _y_x10004, kk_context_t* _ctx) { /* forall<a,e> (a, a, a) -> e (a, a, a) */ 
  return kk_std_core_types__new_Tuple3(_y_x10002, _y_x10003, _y_x10004, _ctx);
}

kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs__mlift_map_10124(kk_box_t _y_x10002, kk_function_t f, kk_std_core_types__tuple3 t, kk_box_t _y_x10003, kk_context_t* _ctx); /* forall<a,b,e> (b, f : (a) -> e b, t : (a, a, a), b) -> e (b, b, b) */ 

kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs__mlift_map_10125(kk_function_t f, kk_std_core_types__tuple3 t, kk_box_t _y_x10002, kk_context_t* _ctx); /* forall<a,b,e> (f : (a) -> e b, t : (a, a, a), b) -> e (b, b, b) */ 

kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs_map(kk_std_core_types__tuple3 t, kk_function_t f, kk_context_t* _ctx); /* forall<a,b,e> (t : (a, a, a), f : (a) -> e b) -> e (b, b, b) */ 
 
// monadic lift

static inline kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10126(kk_box_t _y_x10005, kk_box_t _y_x10006, kk_box_t _y_x10007, kk_box_t _y_x10008, kk_context_t* _ctx) { /* forall<a,e> (a, a, a, a) -> e (a, a, a, a) */ 
  return kk_std_core_types__new_Tuple4(kk_reuse_null, 0, _y_x10005, _y_x10006, _y_x10007, _y_x10008, _ctx);
}

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10127(kk_box_t _y_x10005, kk_box_t _y_x10006, kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t _y_x10007, kk_context_t* _ctx); /* forall<a,b,e> (b, b, f : (a) -> e b, t : (a, a, a, a), b) -> e (b, b, b, b) */ 

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10128(kk_box_t _y_x10005, kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t _y_x10006, kk_context_t* _ctx); /* forall<a,b,e> (b, f : (a) -> e b, t : (a, a, a, a), b) -> e (b, b, b, b) */ 

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10129(kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t _y_x10005, kk_context_t* _ctx); /* forall<a,b,e> (f : (a) -> e b, t : (a, a, a, a), b) -> e (b, b, b, b) */ 

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs_map(kk_std_core_types__tuple4 t, kk_function_t f, kk_context_t* _ctx); /* forall<a,b,e> (t : (a, a, a, a), f : (a) -> e b) -> e (b, b, b, b) */ 
 
// monadic lift

static inline kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10130(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_box_t _y_x10011, kk_box_t _y_x10012, kk_box_t _y_x10013, kk_context_t* _ctx) { /* forall<a,e> (a, a, a, a, a) -> e (a, a, a, a, a) */ 
  return kk_std_core_types__new_Tuple5(kk_reuse_null, 0, _y_x10009, _y_x10010, _y_x10011, _y_x10012, _y_x10013, _ctx);
}

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10131(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_box_t _y_x10011, kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10012, kk_context_t* _ctx); /* forall<a,b,e> (b, b, b, f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10132(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10011, kk_context_t* _ctx); /* forall<a,b,e> (b, b, f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10133(kk_box_t _y_x10009, kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10010, kk_context_t* _ctx); /* forall<a,b,e> (b, f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10134(kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10009, kk_context_t* _ctx); /* forall<a,b,e> (f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs_map(kk_std_core_types__tuple5 t, kk_function_t f, kk_context_t* _ctx); /* forall<a,b,e> (t : (a, a, a, a, a), f : (a) -> e b) -> e (b, b, b, b, b) */ 
 
// Compare unit values. Useful to build composite equality for structures containing a unit (e.g. either<string, ()>)

static inline bool kk_std_core_tuple_unit_fs__lp__eq__eq__rp_(kk_unit_t a, kk_unit_t b, kk_context_t* _ctx) { /* (a : (), b : ()) -> bool */ 
  return true;
}
 
// monadic lift

static inline bool kk_std_core_tuple_tuple2_fs__lp__at_mlift_x_10135_eq__eq__rp_(kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_box_t y1, kk_box_t y2, bool _y_x10014, kk_context_t* _ctx) { /* forall<a,e> (?snd/(==) : (a, a) -> e bool, y1 : a, y2 : a, bool) -> e bool */ 
  if (_y_x10014) {
    return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx);
  }
  {
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}

bool kk_std_core_tuple_tuple2_fs__lp__eq__eq__rp_(kk_std_core_types__tuple2 _pat_x36__22, kk_std_core_types__tuple2 _pat_x36__39, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_context_t* _ctx); /* forall<a,b,e> ((a, b), (a, b), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool) -> e bool */ 
 
// monadic lift

static inline bool kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10136_eq__eq__rp_(kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t z1, kk_box_t z2, bool _y_x10020, kk_context_t* _ctx) { /* forall<a,e> (?thd/(==) : (a, a) -> e bool, z1 : a, z2 : a, bool) -> e bool */ 
  if (_y_x10020) {
    return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx);
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}

bool kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_eq__eq__rp_(kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, bool _y_x10019, kk_context_t* _ctx); /* forall<a,b,e> (?snd/(==) : (a, a) -> e bool, ?thd/(==) : (b, b) -> e bool, y1 : a, y2 : a, z1 : b, z2 : b, bool) -> e bool */ 

bool kk_std_core_tuple_tuple3_fs__lp__eq__eq__rp_(kk_std_core_types__tuple3 _pat_x40__22, kk_std_core_types__tuple3 _pat_x40__44, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_context_t* _ctx); /* forall<a,b,c,e> ((a, b, c), (a, b, c), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool, ?thd/(==) : (c, c) -> e bool) -> e bool */ 
 
// monadic lift

static inline bool kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10138_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, bool _y_x10028, kk_context_t* _ctx) { /* forall<a,e> (?field4/(==) : (a, a) -> e bool, w1 : a, w2 : a, bool) -> e bool */ 
  if (_y_x10028) {
    return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx);
  }
  {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}

bool kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, bool _y_x10027, kk_context_t* _ctx); /* forall<a,b,e> (?field4/(==) : (b, b) -> e bool, ?thd/(==) : (a, a) -> e bool, w1 : b, w2 : b, z1 : a, z2 : a, bool) -> e bool */ 

bool kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, bool _y_x10026, kk_context_t* _ctx); /* forall<a,b,c,e> (?field4/(==) : (c, c) -> e bool, ?snd/(==) : (a, a) -> e bool, ?thd/(==) : (b, b) -> e bool, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, bool) -> e bool */ 

bool kk_std_core_tuple_tuple4_fs__lp__eq__eq__rp_(kk_std_core_types__tuple4 _pat_x44__22, kk_std_core_types__tuple4 _pat_x44__49, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_context_t* _ctx); /* forall<a,b,c,d,e> ((a, b, c, d), (a, b, c, d), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool, ?thd/(==) : (c, c) -> e bool, ?field4/(==) : (d, d) -> e bool) -> e bool */ 
 
// monadic lift

static inline bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10141_eq__eq__rp_(kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, bool _y_x10038, kk_context_t* _ctx) { /* forall<e,a> (?field5/(==) : (a, a) -> e bool, v1 : a, v2 : a, bool) -> e bool */ 
  if (_y_x10038) {
    return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs__lp__eq__eq__rp_, (_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx);
  }
  {
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}

bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, bool _y_x10037, kk_context_t* _ctx); /* forall<a,e,b> (?field4/(==) : (a, a) -> e bool, ?field5/(==) : (b, b) -> e bool, v1 : b, v2 : b, w1 : a, w2 : a, bool) -> e bool */ 

bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, bool _y_x10036, kk_context_t* _ctx); /* forall<a,b,e,c> (?field4/(==) : (b, b) -> e bool, ?field5/(==) : (c, c) -> e bool, ?thd/(==) : (a, a) -> e bool, v1 : c, v2 : c, w1 : b, w2 : b, z1 : a, z2 : a, bool) -> e bool */ 

bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, bool _y_x10035, kk_context_t* _ctx); /* forall<a,b,c,e,d> (?field4/(==) : (c, c) -> e bool, ?field5/(==) : (d, d) -> e bool, ?snd/(==) : (a, a) -> e bool, ?thd/(==) : (b, b) -> e bool, v1 : d, v2 : d, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, bool) -> e bool */ 

bool kk_std_core_tuple_tuple5_fs__lp__eq__eq__rp_(kk_std_core_types__tuple5 _pat_x50__22, kk_std_core_types__tuple5 _pat_x50__54, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> ((a, b, c, d, a1), (a, b, c, d, a1), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool, ?thd/(==) : (c, c) -> e bool, ?field4/(==) : (d, d) -> e bool, ?field5/(==) : (a1, a1) -> e bool) -> e bool */ 
 
// Order on unit

static inline kk_std_core_types__order kk_std_core_tuple_unit_fs_cmp(kk_unit_t a, kk_unit_t b, kk_context_t* _ctx) { /* (a : (), b : ()) -> order */ 
  return kk_std_core_types__new_Eq(_ctx);
}
 
// monadic lift

static inline kk_std_core_types__order kk_std_core_tuple_tuple2_fs__mlift_cmp_10145(kk_function_t _implicit_fs_snd_fs_cmp, kk_box_t y1, kk_box_t y2, kk_std_core_types__order _y_x10046, kk_context_t* _ctx) { /* forall<a,e> (?snd/cmp : (a, a) -> e order, y1 : a, y2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10046, _ctx)) {
    return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_cmp, (_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx);
  }
  {
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_function_drop(_implicit_fs_snd_fs_cmp, _ctx);
    return _y_x10046;
  }
}

kk_std_core_types__order kk_std_core_tuple_tuple2_fs_cmp(kk_std_core_types__tuple2 _pat_x60__21, kk_std_core_types__tuple2 _pat_x60__38, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_context_t* _ctx); /* forall<a,b,e> ((a, b), (a, b), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order) -> e order */ 
 
// monadic lift

static inline kk_std_core_types__order kk_std_core_tuple_tuple3_fs__mlift_cmp_10146(kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10052, kk_context_t* _ctx) { /* forall<a,e> (?thd/cmp : (a, a) -> e order, z1 : a, z2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10052, _ctx)) {
    return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_cmp, (_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx);
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    return _y_x10052;
  }
}

kk_std_core_types__order kk_std_core_tuple_tuple3_fs__mlift_cmp_10147(kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10051, kk_context_t* _ctx); /* forall<a,b,e> (?snd/cmp : (a, a) -> e order, ?thd/cmp : (b, b) -> e order, y1 : a, y2 : a, z1 : b, z2 : b, order) -> e order */ 

kk_std_core_types__order kk_std_core_tuple_tuple3_fs_cmp(kk_std_core_types__tuple3 _pat_x66__26, kk_std_core_types__tuple3 _pat_x66__48, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_context_t* _ctx); /* forall<a,b,c,e> ((a, b, c), (a, b, c), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order, ?thd/cmp : (c, c) -> e order) -> e order */ 
 
// monadic lift

static inline kk_std_core_types__order kk_std_core_tuple_tuple4_fs__mlift_cmp_10148(kk_function_t _implicit_fs_field4_fs_cmp, kk_box_t w1, kk_box_t w2, kk_std_core_types__order _y_x10060, kk_context_t* _ctx) { /* forall<a,e> (?field4/cmp : (a, a) -> e order, w1 : a, w2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10060, _ctx)) {
    return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_cmp, (_implicit_fs_field4_fs_cmp, w1, w2, _ctx), _ctx);
  }
  {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    return _y_x10060;
  }
}

kk_std_core_types__order kk_std_core_tuple_tuple4_fs__mlift_cmp_10149(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10059, kk_context_t* _ctx); /* forall<a,b,e> (?field4/cmp : (b, b) -> e order, ?thd/cmp : (a, a) -> e order, w1 : b, w2 : b, z1 : a, z2 : a, order) -> e order */ 

kk_std_core_types__order kk_std_core_tuple_tuple4_fs__mlift_cmp_10150(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10058, kk_context_t* _ctx); /* forall<a,b,c,e> (?field4/cmp : (c, c) -> e order, ?snd/cmp : (a, a) -> e order, ?thd/cmp : (b, b) -> e order, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, order) -> e order */ 

kk_std_core_types__order kk_std_core_tuple_tuple4_fs_cmp(kk_std_core_types__tuple4 _pat_x74__26, kk_std_core_types__tuple4 _pat_x74__53, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_function_t _implicit_fs_field4_fs_cmp, kk_context_t* _ctx); /* forall<a,b,c,d,e> ((a, b, c, d), (a, b, c, d), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order, ?thd/cmp : (c, c) -> e order, ?field4/cmp : (d, d) -> e order) -> e order */ 
 
// monadic lift

static inline kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10151(kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_std_core_types__order _y_x10070, kk_context_t* _ctx) { /* forall<e,a> (?field5/cmp : (a, a) -> e order, v1 : a, v2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10070, _ctx)) {
    return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs_cmp, (_implicit_fs_field5_fs_cmp, v1, v2, _ctx), _ctx);
  }
  {
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
    return _y_x10070;
  }
}

kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10152(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_std_core_types__order _y_x10069, kk_context_t* _ctx); /* forall<a,e,b> (?field4/cmp : (a, a) -> e order, ?field5/cmp : (b, b) -> e order, v1 : b, v2 : b, w1 : a, w2 : a, order) -> e order */ 

kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10153(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10068, kk_context_t* _ctx); /* forall<a,b,e,c> (?field4/cmp : (b, b) -> e order, ?field5/cmp : (c, c) -> e order, ?thd/cmp : (a, a) -> e order, v1 : c, v2 : c, w1 : b, w2 : b, z1 : a, z2 : a, order) -> e order */ 

kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10154(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10067, kk_context_t* _ctx); /* forall<a,b,c,e,d> (?field4/cmp : (c, c) -> e order, ?field5/cmp : (d, d) -> e order, ?snd/cmp : (a, a) -> e order, ?thd/cmp : (b, b) -> e order, v1 : d, v2 : d, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, order) -> e order */ 

kk_std_core_types__order kk_std_core_tuple_tuple5_fs_cmp(kk_std_core_types__tuple5 _pat_x86__26, kk_std_core_types__tuple5 _pat_x86__58, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> ((a, b, c, d, a1), (a, b, c, d, a1), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order, ?thd/cmp : (c, c) -> e order, ?field4/cmp : (d, d) -> e order, ?field5/cmp : (a1, a1) -> e order) -> e order */ 
 
// fip ordering of unit values

static inline kk_std_core_types__order2 kk_std_core_tuple_unit_fs_order2(kk_unit_t a, kk_unit_t b, kk_context_t* _ctx) { /* (a : (), b : ()) -> order2<()> */ 
  return kk_std_core_types__new_Eq2(kk_unit_box(a), _ctx);
}
 
// Convert a unit value `()` to a string

static inline kk_string_t kk_std_core_tuple_unit_fs_show(kk_unit_t u, kk_context_t* _ctx) { /* (u : ()) -> string */ 
  kk_define_string_literal(, _s_x676, 2, "()", _ctx)
  return kk_string_dup(_s_x676, _ctx);
}
 
// monadic lift

static inline kk_string_t kk_std_core_tuple_tuple2_fs__mlift_show_10155(kk_string_t _y_x10078, kk_string_t _y_x10079, kk_context_t* _ctx) { /* forall<e> (string, string) -> e string */ 
  kk_string_t _x_x677;
  kk_define_string_literal(, _s_x678, 1, "(", _ctx)
  _x_x677 = kk_string_dup(_s_x678, _ctx); /*string*/
  kk_string_t _x_x679;
  kk_string_t _x_x680;
  kk_string_t _x_x681;
  kk_define_string_literal(, _s_x682, 1, ",", _ctx)
  _x_x681 = kk_string_dup(_s_x682, _ctx); /*string*/
  kk_string_t _x_x683;
  kk_string_t _x_x684;
  kk_define_string_literal(, _s_x685, 1, ")", _ctx)
  _x_x684 = kk_string_dup(_s_x685, _ctx); /*string*/
  _x_x683 = kk_std_core_types__lp__plus__plus__rp_(_y_x10079, _x_x684, _ctx); /*string*/
  _x_x680 = kk_std_core_types__lp__plus__plus__rp_(_x_x681, _x_x683, _ctx); /*string*/
  _x_x679 = kk_std_core_types__lp__plus__plus__rp_(_y_x10078, _x_x680, _ctx); /*string*/
  return kk_std_core_types__lp__plus__plus__rp_(_x_x677, _x_x679, _ctx);
}

kk_string_t kk_std_core_tuple_tuple2_fs__mlift_show_10156(kk_function_t _implicit_fs_snd_fs_show, kk_std_core_types__tuple2 x, kk_string_t _y_x10078, kk_context_t* _ctx); /* forall<a,b,e> (?snd/show : (b) -> e string, x : (a, b), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple2_fs_show(kk_std_core_types__tuple2 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_context_t* _ctx); /* forall<a,b,e> (x : (a, b), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple3_fs__mlift_show_10157(kk_string_t _y_x10080, kk_string_t _y_x10081, kk_string_t _y_x10082, kk_context_t* _ctx); /* forall<e> (string, string, string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple3_fs__mlift_show_10158(kk_string_t _y_x10080, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_string_t _y_x10081, kk_context_t* _ctx); /* forall<a,b,c,e> (string, ?thd/show : (c) -> e string, x : (a, b, c), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple3_fs__mlift_show_10159(kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_string_t _y_x10080, kk_context_t* _ctx); /* forall<a,b,c,e> (?snd/show : (b) -> e string, ?thd/show : (c) -> e string, x : (a, b, c), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple3_fs_show(kk_std_core_types__tuple3 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_context_t* _ctx); /* forall<a,b,c,e> (x : (a, b, c), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10160(kk_string_t _y_x10083, kk_string_t _y_x10084, kk_string_t _y_x10085, kk_string_t _y_x10086, kk_context_t* _ctx); /* forall<e> (string, string, string, string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10161(kk_string_t _y_x10083, kk_string_t _y_x10084, kk_function_t _implicit_fs_field4_fs_show, kk_std_core_types__tuple4 x, kk_string_t _y_x10085, kk_context_t* _ctx); /* forall<a,b,c,d,e> (string, string, ?field4/show : (d) -> e string, x : (a, b, c, d), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10162(kk_string_t _y_x10083, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_string_t _y_x10084, kk_context_t* _ctx); /* forall<a,b,c,d,e> (string, ?field4/show : (d) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10163(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_string_t _y_x10083, kk_context_t* _ctx); /* forall<a,b,c,d,e> (?field4/show : (d) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple4_fs_show(kk_std_core_types__tuple4 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_function_t _implicit_fs_field4_fs_show, kk_context_t* _ctx); /* forall<a,b,c,d,e> (x : (a, b, c, d), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, ?field4/show : (d) -> e string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10164(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_string_t _y_x10089, kk_string_t _y_x10090, kk_string_t _y_x10091, kk_context_t* _ctx); /* forall<e> (string, string, string, string, string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10165(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_string_t _y_x10089, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10090, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> (string, string, string, ?field5/show : (a1) -> e string, x : (a, b, c, d, a1), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10166(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10089, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> (string, string, ?field4/show : (d) -> e string, ?field5/show : (a1) -> e string, x : (a, b, c, d, a1), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10167(kk_string_t _y_x10087, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10088, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> (string, ?field4/show : (d) -> e string, ?field5/show : (a1) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d, a1), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10168(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10087, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> (?field4/show : (d) -> e string, ?field5/show : (a1) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d, a1), string) -> e string */ 

kk_string_t kk_std_core_tuple_tuple5_fs_show(kk_std_core_types__tuple5 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_context_t* _ctx); /* forall<a,b,c,d,e,a1> (x : (a, b, c, d, a1), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, ?field4/show : (d) -> e string, ?field5/show : (a1) -> e string) -> e string */ 
 
// _deprecated_, use `tuple2/show` instead

static inline kk_string_t kk_std_core_tuple_show_tuple(kk_std_core_types__tuple2 x, kk_function_t showfst, kk_function_t showsnd, kk_context_t* _ctx) { /* forall<a,b,e> (x : (a, b), showfst : (a) -> e string, showsnd : (b) -> e string) -> e string */ 
  return kk_std_core_tuple_tuple2_fs_show(x, showfst, showsnd, _ctx);
}

void kk_std_core_tuple__init(kk_context_t* _ctx);


void kk_std_core_tuple__done(kk_context_t* _ctx);

#endif // header
