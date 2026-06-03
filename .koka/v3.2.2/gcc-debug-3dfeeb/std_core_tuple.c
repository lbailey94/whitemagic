// Koka generated module: std/core/tuple, koka version: 3.2.2, platform: 64-bit
#include "std_core_tuple.h"
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425__t {
  struct kk_function_s _base;
  kk_box_t _y_x10000;
};
static kk_box_t kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425(kk_function_t _fself, kk_box_t _b_x1, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs__new_mlift_map_10122_fun425(kk_box_t _y_x10000, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425, kk_context());
  _self->_y_x10000 = _y_x10000;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425(kk_function_t _fself, kk_box_t _b_x1, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs__mlift_map_10122_fun425__t*, _fself, _ctx);
  kk_box_t _y_x10000 = _self->_y_x10000; /* 423 */
  kk_drop_match(_self, {kk_box_dup(_y_x10000, _ctx);}, {}, _ctx)
  kk_box_t _y_x10001_3 = _b_x1; /*423*/;
  kk_std_core_types__tuple2 _x_x426 = kk_std_core_types__new_Tuple2(_y_x10000, _y_x10001_3, _ctx); /*(134, 135)*/
  return kk_std_core_types__tuple2_box(_x_x426, _ctx);
}

kk_std_core_types__tuple2 kk_std_core_tuple_tuple2_fs__mlift_map_10122(kk_function_t f, kk_std_core_types__tuple2 t, kk_box_t _y_x10000, kk_context_t* _ctx) { /* forall<a,b,e> (f : (a) -> e b, t : (a, a), b) -> e (b, b) */ 
  kk_box_t x_10169;
  kk_box_t _x_x423;
  {
    kk_box_t _x_0 = t.snd;
    kk_box_dup(_x_0, _ctx);
    kk_std_core_types__tuple2_drop(t, _ctx);
    _x_x423 = _x_0; /*422*/
  }
  x_10169 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x423, _ctx), _ctx); /*423*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10169, _ctx);
    kk_box_t _x_x424 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs__new_mlift_map_10122_fun425(_y_x10000, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple2_unbox(_x_x424, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_types__new_Tuple2(_y_x10000, x_10169, _ctx);
  }
}
 
// Map a function over a tuple of elements of the same type.


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs_map_fun430__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple2 t;
};
static kk_box_t kk_std_core_tuple_tuple2_fs_map_fun430(kk_function_t _fself, kk_box_t _b_x5, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs_new_map_fun430(kk_function_t f, kk_std_core_types__tuple2 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_map_fun430__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs_map_fun430__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs_map_fun430, kk_context());
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs_map_fun430(kk_function_t _fself, kk_box_t _b_x5, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_map_fun430__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs_map_fun430__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (422) -> 424 423 */
  kk_std_core_types__tuple2 t = _self->t; /* (422, 422) */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple2_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10000_10 = _b_x5; /*423*/;
  kk_std_core_types__tuple2 _x_x431 = kk_std_core_tuple_tuple2_fs__mlift_map_10122(f, t, _y_x10000_10, _ctx); /*(423, 423)*/
  return kk_std_core_types__tuple2_box(_x_x431, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs_map_fun434__t {
  struct kk_function_s _base;
  kk_box_t x_10173;
};
static kk_box_t kk_std_core_tuple_tuple2_fs_map_fun434(kk_function_t _fself, kk_box_t _b_x7, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs_new_map_fun434(kk_box_t x_10173, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_map_fun434__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs_map_fun434__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs_map_fun434, kk_context());
  _self->x_10173 = x_10173;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs_map_fun434(kk_function_t _fself, kk_box_t _b_x7, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_map_fun434__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs_map_fun434__t*, _fself, _ctx);
  kk_box_t x_10173 = _self->x_10173; /* 423 */
  kk_drop_match(_self, {kk_box_dup(x_10173, _ctx);}, {}, _ctx)
  kk_box_t _y_x10001_11 = _b_x7; /*423*/;
  kk_std_core_types__tuple2 _x_x435 = kk_std_core_types__new_Tuple2(x_10173, _y_x10001_11, _ctx); /*(134, 135)*/
  return kk_std_core_types__tuple2_box(_x_x435, _ctx);
}

kk_std_core_types__tuple2 kk_std_core_tuple_tuple2_fs_map(kk_std_core_types__tuple2 t, kk_function_t f, kk_context_t* _ctx) { /* forall<a,b,e> (t : (a, a), f : (a) -> e b) -> e (b, b) */ 
  kk_box_t x_10173;
  kk_function_t _x_x428 = kk_function_dup(f, _ctx); /*(422) -> 424 423*/
  kk_box_t _x_x427;
  {
    kk_box_t _x = t.fst;
    kk_box_dup(_x, _ctx);
    _x_x427 = _x; /*422*/
  }
  x_10173 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x428, (_x_x428, _x_x427, _ctx), _ctx); /*423*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10173, _ctx);
    kk_box_t _x_x429 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs_new_map_fun430(f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple2_unbox(_x_x429, KK_OWNED, _ctx);
  }
  {
    kk_box_t x_0_10176;
    kk_box_t _x_x432;
    {
      kk_box_t _x_0 = t.snd;
      kk_box_dup(_x_0, _ctx);
      kk_std_core_types__tuple2_drop(t, _ctx);
      _x_x432 = _x_0; /*422*/
    }
    x_0_10176 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x432, _ctx), _ctx); /*423*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_0_10176, _ctx);
      kk_box_t _x_x433 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs_new_map_fun434(x_10173, _ctx), _ctx); /*2419*/
      return kk_std_core_types__tuple2_unbox(_x_x433, KK_OWNED, _ctx);
    }
    {
      return kk_std_core_types__new_Tuple2(x_10173, x_0_10176, _ctx);
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438__t {
  struct kk_function_s _base;
  kk_box_t _y_x10002;
  kk_box_t _y_x10003;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438(kk_function_t _fself, kk_box_t _b_x13, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__new_mlift_map_10124_fun438(kk_box_t _y_x10002, kk_box_t _y_x10003, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438, kk_context());
  _self->_y_x10002 = _y_x10002;
  _self->_y_x10003 = _y_x10003;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438(kk_function_t _fself, kk_box_t _b_x13, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__mlift_map_10124_fun438__t*, _fself, _ctx);
  kk_box_t _y_x10002 = _self->_y_x10002; /* 583 */
  kk_box_t _y_x10003 = _self->_y_x10003; /* 583 */
  kk_drop_match(_self, {kk_box_dup(_y_x10002, _ctx);kk_box_dup(_y_x10003, _ctx);}, {}, _ctx)
  kk_box_t _y_x10004_15 = _b_x13; /*583*/;
  kk_std_core_types__tuple3 _x_x439 = kk_std_core_types__new_Tuple3(_y_x10002, _y_x10003, _y_x10004_15, _ctx); /*(141, 142, 143)*/
  return kk_std_core_types__tuple3_box(_x_x439, _ctx);
}

kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs__mlift_map_10124(kk_box_t _y_x10002, kk_function_t f, kk_std_core_types__tuple3 t, kk_box_t _y_x10003, kk_context_t* _ctx) { /* forall<a,b,e> (b, f : (a) -> e b, t : (a, a, a), b) -> e (b, b, b) */ 
  kk_box_t x_10181;
  kk_box_t _x_x436;
  {
    kk_box_t _x_1 = t.thd;
    kk_box_dup(_x_1, _ctx);
    kk_std_core_types__tuple3_drop(t, _ctx);
    _x_x436 = _x_1; /*582*/
  }
  x_10181 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x436, _ctx), _ctx); /*583*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10181, _ctx);
    kk_box_t _x_x437 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__new_mlift_map_10124_fun438(_y_x10002, _y_x10003, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple3_unbox(_x_x437, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_types__new_Tuple3(_y_x10002, _y_x10003, x_10181, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443__t {
  struct kk_function_s _base;
  kk_box_t _y_x10002;
  kk_function_t f;
  kk_std_core_types__tuple3 t;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443(kk_function_t _fself, kk_box_t _b_x17, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__new_mlift_map_10125_fun443(kk_box_t _y_x10002, kk_function_t f, kk_std_core_types__tuple3 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443, kk_context());
  _self->_y_x10002 = _y_x10002;
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443(kk_function_t _fself, kk_box_t _b_x17, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__mlift_map_10125_fun443__t*, _fself, _ctx);
  kk_box_t _y_x10002 = _self->_y_x10002; /* 583 */
  kk_function_t f = _self->f; /* (582) -> 584 583 */
  kk_std_core_types__tuple3 t = _self->t; /* (582, 582, 582) */
  kk_drop_match(_self, {kk_box_dup(_y_x10002, _ctx);kk_function_dup(f, _ctx);kk_std_core_types__tuple3_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10003_19 = _b_x17; /*583*/;
  kk_std_core_types__tuple3 _x_x444 = kk_std_core_tuple_tuple3_fs__mlift_map_10124(_y_x10002, f, t, _y_x10003_19, _ctx); /*(583, 583, 583)*/
  return kk_std_core_types__tuple3_box(_x_x444, _ctx);
}

kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs__mlift_map_10125(kk_function_t f, kk_std_core_types__tuple3 t, kk_box_t _y_x10002, kk_context_t* _ctx) { /* forall<a,b,e> (f : (a) -> e b, t : (a, a, a), b) -> e (b, b, b) */ 
  kk_box_t x_10186;
  kk_function_t _x_x441 = kk_function_dup(f, _ctx); /*(582) -> 584 583*/
  kk_box_t _x_x440;
  {
    kk_box_t _x_0 = t.snd;
    kk_box_dup(_x_0, _ctx);
    _x_x440 = _x_0; /*582*/
  }
  x_10186 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x441, (_x_x441, _x_x440, _ctx), _ctx); /*583*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10186, _ctx);
    kk_box_t _x_x442 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__new_mlift_map_10125_fun443(_y_x10002, f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple3_unbox(_x_x442, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_tuple_tuple3_fs__mlift_map_10124(_y_x10002, f, t, x_10186, _ctx);
  }
}
 
// Map a function over a triple of elements of the same type.


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_map_fun448__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple3 t;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_map_fun448(kk_function_t _fself, kk_box_t _b_x21, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_map_fun448(kk_function_t f, kk_std_core_types__tuple3 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_map_fun448__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_map_fun448__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_map_fun448, kk_context());
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_map_fun448(kk_function_t _fself, kk_box_t _b_x21, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_map_fun448__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_map_fun448__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (582) -> 584 583 */
  kk_std_core_types__tuple3 t = _self->t; /* (582, 582, 582) */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple3_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10002_29 = _b_x21; /*583*/;
  kk_std_core_types__tuple3 _x_x449 = kk_std_core_tuple_tuple3_fs__mlift_map_10125(f, t, _y_x10002_29, _ctx); /*(583, 583, 583)*/
  return kk_std_core_types__tuple3_box(_x_x449, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_map_fun453__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple3 t;
  kk_box_t x_10188;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_map_fun453(kk_function_t _fself, kk_box_t _b_x23, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_map_fun453(kk_function_t f, kk_std_core_types__tuple3 t, kk_box_t x_10188, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_map_fun453__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_map_fun453__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_map_fun453, kk_context());
  _self->f = f;
  _self->t = t;
  _self->x_10188 = x_10188;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_map_fun453(kk_function_t _fself, kk_box_t _b_x23, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_map_fun453__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_map_fun453__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (582) -> 584 583 */
  kk_std_core_types__tuple3 t = _self->t; /* (582, 582, 582) */
  kk_box_t x_10188 = _self->x_10188; /* 583 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple3_dup(t, _ctx);kk_box_dup(x_10188, _ctx);}, {}, _ctx)
  kk_box_t _y_x10003_30 = _b_x23; /*583*/;
  kk_std_core_types__tuple3 _x_x454 = kk_std_core_tuple_tuple3_fs__mlift_map_10124(x_10188, f, t, _y_x10003_30, _ctx); /*(583, 583, 583)*/
  return kk_std_core_types__tuple3_box(_x_x454, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_map_fun457__t {
  struct kk_function_s _base;
  kk_box_t x_0_10191;
  kk_box_t x_10188;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_map_fun457(kk_function_t _fself, kk_box_t _b_x25, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_map_fun457(kk_box_t x_0_10191, kk_box_t x_10188, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_map_fun457__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_map_fun457__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_map_fun457, kk_context());
  _self->x_0_10191 = x_0_10191;
  _self->x_10188 = x_10188;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_map_fun457(kk_function_t _fself, kk_box_t _b_x25, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_map_fun457__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_map_fun457__t*, _fself, _ctx);
  kk_box_t x_0_10191 = _self->x_0_10191; /* 583 */
  kk_box_t x_10188 = _self->x_10188; /* 583 */
  kk_drop_match(_self, {kk_box_dup(x_0_10191, _ctx);kk_box_dup(x_10188, _ctx);}, {}, _ctx)
  kk_box_t _y_x10004_31 = _b_x25; /*583*/;
  kk_std_core_types__tuple3 _x_x458 = kk_std_core_types__new_Tuple3(x_10188, x_0_10191, _y_x10004_31, _ctx); /*(141, 142, 143)*/
  return kk_std_core_types__tuple3_box(_x_x458, _ctx);
}

kk_std_core_types__tuple3 kk_std_core_tuple_tuple3_fs_map(kk_std_core_types__tuple3 t, kk_function_t f, kk_context_t* _ctx) { /* forall<a,b,e> (t : (a, a, a), f : (a) -> e b) -> e (b, b, b) */ 
  kk_box_t x_10188;
  kk_function_t _x_x446 = kk_function_dup(f, _ctx); /*(582) -> 584 583*/
  kk_box_t _x_x445;
  {
    kk_box_t _x = t.fst;
    kk_box_dup(_x, _ctx);
    _x_x445 = _x; /*582*/
  }
  x_10188 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x446, (_x_x446, _x_x445, _ctx), _ctx); /*583*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10188, _ctx);
    kk_box_t _x_x447 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs_new_map_fun448(f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple3_unbox(_x_x447, KK_OWNED, _ctx);
  }
  {
    kk_box_t x_0_10191;
    kk_function_t _x_x451 = kk_function_dup(f, _ctx); /*(582) -> 584 583*/
    kk_box_t _x_x450;
    {
      kk_box_t _x_0 = t.snd;
      kk_box_dup(_x_0, _ctx);
      _x_x450 = _x_0; /*582*/
    }
    x_0_10191 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x451, (_x_x451, _x_x450, _ctx), _ctx); /*583*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_0_10191, _ctx);
      kk_box_t _x_x452 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs_new_map_fun453(f, t, x_10188, _ctx), _ctx); /*2419*/
      return kk_std_core_types__tuple3_unbox(_x_x452, KK_OWNED, _ctx);
    }
    {
      kk_box_t x_1_10194;
      kk_box_t _x_x455;
      {
        kk_box_t _x_1 = t.thd;
        kk_box_dup(_x_1, _ctx);
        kk_std_core_types__tuple3_drop(t, _ctx);
        _x_x455 = _x_1; /*582*/
      }
      x_1_10194 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x455, _ctx), _ctx); /*583*/
      if (kk_yielding(kk_context())) {
        kk_box_drop(x_1_10194, _ctx);
        kk_box_t _x_x456 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs_new_map_fun457(x_0_10191, x_10188, _ctx), _ctx); /*2419*/
        return kk_std_core_types__tuple3_unbox(_x_x456, KK_OWNED, _ctx);
      }
      {
        return kk_std_core_types__new_Tuple3(x_10188, x_0_10191, x_1_10194, _ctx);
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462__t {
  struct kk_function_s _base;
  kk_box_t _y_x10005;
  kk_box_t _y_x10006;
  kk_box_t _y_x10007;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462(kk_function_t _fself, kk_box_t _b_x33, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_map_10127_fun462(kk_box_t _y_x10005, kk_box_t _y_x10006, kk_box_t _y_x10007, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462, kk_context());
  _self->_y_x10005 = _y_x10005;
  _self->_y_x10006 = _y_x10006;
  _self->_y_x10007 = _y_x10007;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462(kk_function_t _fself, kk_box_t _b_x33, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_map_10127_fun462__t*, _fself, _ctx);
  kk_box_t _y_x10005 = _self->_y_x10005; /* 789 */
  kk_box_t _y_x10006 = _self->_y_x10006; /* 789 */
  kk_box_t _y_x10007 = _self->_y_x10007; /* 789 */
  kk_drop_match(_self, {kk_box_dup(_y_x10005, _ctx);kk_box_dup(_y_x10006, _ctx);kk_box_dup(_y_x10007, _ctx);}, {}, _ctx)
  kk_box_t _y_x10008_35 = _b_x33; /*789*/;
  kk_std_core_types__tuple4 _x_x463 = kk_std_core_types__new_Tuple4(kk_reuse_null, 0, _y_x10005, _y_x10006, _y_x10007, _y_x10008_35, _ctx); /*(150, 151, 152, 153)*/
  return kk_std_core_types__tuple4_box(_x_x463, _ctx);
}

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10127(kk_box_t _y_x10005, kk_box_t _y_x10006, kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t _y_x10007, kk_context_t* _ctx) { /* forall<a,b,e> (b, b, f : (a) -> e b, t : (a, a, a, a), b) -> e (b, b, b, b) */ 
  kk_box_t x_10200;
  kk_box_t _x_x459;
  {
    struct kk_std_core_types_Tuple4* _con_x460 = kk_std_core_types__as_Tuple4(t, _ctx);
    kk_box_t _pat_0_2 = _con_x460->fst;
    kk_box_t _pat_1_2 = _con_x460->snd;
    kk_box_t _pat_2_2 = _con_x460->thd;
    kk_box_t _x_2 = _con_x460->field4;
    if kk_likely(kk_datatype_ptr_is_unique(t, _ctx)) {
      kk_box_drop(_pat_2_2, _ctx);
      kk_box_drop(_pat_1_2, _ctx);
      kk_box_drop(_pat_0_2, _ctx);
      kk_datatype_ptr_free(t, _ctx);
    }
    else {
      kk_box_dup(_x_2, _ctx);
      kk_datatype_ptr_decref(t, _ctx);
    }
    _x_x459 = _x_2; /*788*/
  }
  x_10200 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x459, _ctx), _ctx); /*789*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10200, _ctx);
    kk_box_t _x_x461 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_map_10127_fun462(_y_x10005, _y_x10006, _y_x10007, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple4_unbox(_x_x461, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_types__new_Tuple4(kk_reuse_null, 0, _y_x10005, _y_x10006, _y_x10007, x_10200, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468__t {
  struct kk_function_s _base;
  kk_box_t _y_x10005;
  kk_box_t _y_x10006;
  kk_function_t f;
  kk_std_core_types__tuple4 t;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468(kk_function_t _fself, kk_box_t _b_x37, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_map_10128_fun468(kk_box_t _y_x10005, kk_box_t _y_x10006, kk_function_t f, kk_std_core_types__tuple4 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468, kk_context());
  _self->_y_x10005 = _y_x10005;
  _self->_y_x10006 = _y_x10006;
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468(kk_function_t _fself, kk_box_t _b_x37, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_map_10128_fun468__t*, _fself, _ctx);
  kk_box_t _y_x10005 = _self->_y_x10005; /* 789 */
  kk_box_t _y_x10006 = _self->_y_x10006; /* 789 */
  kk_function_t f = _self->f; /* (788) -> 790 789 */
  kk_std_core_types__tuple4 t = _self->t; /* (788, 788, 788, 788) */
  kk_drop_match(_self, {kk_box_dup(_y_x10005, _ctx);kk_box_dup(_y_x10006, _ctx);kk_function_dup(f, _ctx);kk_std_core_types__tuple4_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10007_39 = _b_x37; /*789*/;
  kk_std_core_types__tuple4 _x_x469 = kk_std_core_tuple_tuple4_fs__mlift_map_10127(_y_x10005, _y_x10006, f, t, _y_x10007_39, _ctx); /*(789, 789, 789, 789)*/
  return kk_std_core_types__tuple4_box(_x_x469, _ctx);
}

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10128(kk_box_t _y_x10005, kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t _y_x10006, kk_context_t* _ctx) { /* forall<a,b,e> (b, f : (a) -> e b, t : (a, a, a, a), b) -> e (b, b, b, b) */ 
  kk_box_t x_10206;
  kk_function_t _x_x466 = kk_function_dup(f, _ctx); /*(788) -> 790 789*/
  kk_box_t _x_x464;
  {
    struct kk_std_core_types_Tuple4* _con_x465 = kk_std_core_types__as_Tuple4(t, _ctx);
    kk_box_t _x_1 = _con_x465->thd;
    kk_box_dup(_x_1, _ctx);
    _x_x464 = _x_1; /*788*/
  }
  x_10206 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x466, (_x_x466, _x_x464, _ctx), _ctx); /*789*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10206, _ctx);
    kk_box_t _x_x467 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_map_10128_fun468(_y_x10005, _y_x10006, f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple4_unbox(_x_x467, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_tuple_tuple4_fs__mlift_map_10127(_y_x10005, _y_x10006, f, t, x_10206, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474__t {
  struct kk_function_s _base;
  kk_box_t _y_x10005;
  kk_function_t f;
  kk_std_core_types__tuple4 t;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474(kk_function_t _fself, kk_box_t _b_x41, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_map_10129_fun474(kk_box_t _y_x10005, kk_function_t f, kk_std_core_types__tuple4 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474, kk_context());
  _self->_y_x10005 = _y_x10005;
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474(kk_function_t _fself, kk_box_t _b_x41, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_map_10129_fun474__t*, _fself, _ctx);
  kk_box_t _y_x10005 = _self->_y_x10005; /* 789 */
  kk_function_t f = _self->f; /* (788) -> 790 789 */
  kk_std_core_types__tuple4 t = _self->t; /* (788, 788, 788, 788) */
  kk_drop_match(_self, {kk_box_dup(_y_x10005, _ctx);kk_function_dup(f, _ctx);kk_std_core_types__tuple4_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10006_43 = _b_x41; /*789*/;
  kk_std_core_types__tuple4 _x_x475 = kk_std_core_tuple_tuple4_fs__mlift_map_10128(_y_x10005, f, t, _y_x10006_43, _ctx); /*(789, 789, 789, 789)*/
  return kk_std_core_types__tuple4_box(_x_x475, _ctx);
}

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs__mlift_map_10129(kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t _y_x10005, kk_context_t* _ctx) { /* forall<a,b,e> (f : (a) -> e b, t : (a, a, a, a), b) -> e (b, b, b, b) */ 
  kk_box_t x_10208;
  kk_function_t _x_x472 = kk_function_dup(f, _ctx); /*(788) -> 790 789*/
  kk_box_t _x_x470;
  {
    struct kk_std_core_types_Tuple4* _con_x471 = kk_std_core_types__as_Tuple4(t, _ctx);
    kk_box_t _x_0 = _con_x471->snd;
    kk_box_dup(_x_0, _ctx);
    _x_x470 = _x_0; /*788*/
  }
  x_10208 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x472, (_x_x472, _x_x470, _ctx), _ctx); /*789*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10208, _ctx);
    kk_box_t _x_x473 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_map_10129_fun474(_y_x10005, f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple4_unbox(_x_x473, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_tuple_tuple4_fs__mlift_map_10128(_y_x10005, f, t, x_10208, _ctx);
  }
}
 
// Map a function over a quadruple of elements of the same type.


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_map_fun480__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple4 t;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun480(kk_function_t _fself, kk_box_t _b_x45, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_map_fun480(kk_function_t f, kk_std_core_types__tuple4 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun480__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_map_fun480__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_map_fun480, kk_context());
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun480(kk_function_t _fself, kk_box_t _b_x45, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun480__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_map_fun480__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (788) -> 790 789 */
  kk_std_core_types__tuple4 t = _self->t; /* (788, 788, 788, 788) */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple4_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10005_56 = _b_x45; /*789*/;
  kk_std_core_types__tuple4 _x_x481 = kk_std_core_tuple_tuple4_fs__mlift_map_10129(f, t, _y_x10005_56, _ctx); /*(789, 789, 789, 789)*/
  return kk_std_core_types__tuple4_box(_x_x481, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_map_fun486__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple4 t;
  kk_box_t x_10210;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun486(kk_function_t _fself, kk_box_t _b_x47, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_map_fun486(kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t x_10210, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun486__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_map_fun486__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_map_fun486, kk_context());
  _self->f = f;
  _self->t = t;
  _self->x_10210 = x_10210;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun486(kk_function_t _fself, kk_box_t _b_x47, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun486__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_map_fun486__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (788) -> 790 789 */
  kk_std_core_types__tuple4 t = _self->t; /* (788, 788, 788, 788) */
  kk_box_t x_10210 = _self->x_10210; /* 789 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple4_dup(t, _ctx);kk_box_dup(x_10210, _ctx);}, {}, _ctx)
  kk_box_t _y_x10006_57 = _b_x47; /*789*/;
  kk_std_core_types__tuple4 _x_x487 = kk_std_core_tuple_tuple4_fs__mlift_map_10128(x_10210, f, t, _y_x10006_57, _ctx); /*(789, 789, 789, 789)*/
  return kk_std_core_types__tuple4_box(_x_x487, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_map_fun492__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple4 t;
  kk_box_t x_0_10213;
  kk_box_t x_10210;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun492(kk_function_t _fself, kk_box_t _b_x49, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_map_fun492(kk_function_t f, kk_std_core_types__tuple4 t, kk_box_t x_0_10213, kk_box_t x_10210, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun492__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_map_fun492__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_map_fun492, kk_context());
  _self->f = f;
  _self->t = t;
  _self->x_0_10213 = x_0_10213;
  _self->x_10210 = x_10210;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun492(kk_function_t _fself, kk_box_t _b_x49, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun492__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_map_fun492__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (788) -> 790 789 */
  kk_std_core_types__tuple4 t = _self->t; /* (788, 788, 788, 788) */
  kk_box_t x_0_10213 = _self->x_0_10213; /* 789 */
  kk_box_t x_10210 = _self->x_10210; /* 789 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple4_dup(t, _ctx);kk_box_dup(x_0_10213, _ctx);kk_box_dup(x_10210, _ctx);}, {}, _ctx)
  kk_box_t _y_x10007_58 = _b_x49; /*789*/;
  kk_std_core_types__tuple4 _x_x493 = kk_std_core_tuple_tuple4_fs__mlift_map_10127(x_10210, x_0_10213, f, t, _y_x10007_58, _ctx); /*(789, 789, 789, 789)*/
  return kk_std_core_types__tuple4_box(_x_x493, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_map_fun497__t {
  struct kk_function_s _base;
  kk_box_t x_0_10213;
  kk_box_t x_10210;
  kk_box_t x_1_10216;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun497(kk_function_t _fself, kk_box_t _b_x51, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_map_fun497(kk_box_t x_0_10213, kk_box_t x_10210, kk_box_t x_1_10216, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun497__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_map_fun497__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_map_fun497, kk_context());
  _self->x_0_10213 = x_0_10213;
  _self->x_10210 = x_10210;
  _self->x_1_10216 = x_1_10216;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_map_fun497(kk_function_t _fself, kk_box_t _b_x51, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_map_fun497__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_map_fun497__t*, _fself, _ctx);
  kk_box_t x_0_10213 = _self->x_0_10213; /* 789 */
  kk_box_t x_10210 = _self->x_10210; /* 789 */
  kk_box_t x_1_10216 = _self->x_1_10216; /* 789 */
  kk_drop_match(_self, {kk_box_dup(x_0_10213, _ctx);kk_box_dup(x_10210, _ctx);kk_box_dup(x_1_10216, _ctx);}, {}, _ctx)
  kk_box_t _y_x10008_59 = _b_x51; /*789*/;
  kk_std_core_types__tuple4 _x_x498 = kk_std_core_types__new_Tuple4(kk_reuse_null, 0, x_10210, x_0_10213, x_1_10216, _y_x10008_59, _ctx); /*(150, 151, 152, 153)*/
  return kk_std_core_types__tuple4_box(_x_x498, _ctx);
}

kk_std_core_types__tuple4 kk_std_core_tuple_tuple4_fs_map(kk_std_core_types__tuple4 t, kk_function_t f, kk_context_t* _ctx) { /* forall<a,b,e> (t : (a, a, a, a), f : (a) -> e b) -> e (b, b, b, b) */ 
  kk_box_t x_10210;
  kk_function_t _x_x478 = kk_function_dup(f, _ctx); /*(788) -> 790 789*/
  kk_box_t _x_x476;
  {
    struct kk_std_core_types_Tuple4* _con_x477 = kk_std_core_types__as_Tuple4(t, _ctx);
    kk_box_t _x = _con_x477->fst;
    kk_box_dup(_x, _ctx);
    _x_x476 = _x; /*788*/
  }
  x_10210 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x478, (_x_x478, _x_x476, _ctx), _ctx); /*789*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10210, _ctx);
    kk_box_t _x_x479 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_map_fun480(f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple4_unbox(_x_x479, KK_OWNED, _ctx);
  }
  {
    kk_box_t x_0_10213;
    kk_function_t _x_x484 = kk_function_dup(f, _ctx); /*(788) -> 790 789*/
    kk_box_t _x_x482;
    {
      struct kk_std_core_types_Tuple4* _con_x483 = kk_std_core_types__as_Tuple4(t, _ctx);
      kk_box_t _x_0 = _con_x483->snd;
      kk_box_dup(_x_0, _ctx);
      _x_x482 = _x_0; /*788*/
    }
    x_0_10213 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x484, (_x_x484, _x_x482, _ctx), _ctx); /*789*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_0_10213, _ctx);
      kk_box_t _x_x485 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_map_fun486(f, t, x_10210, _ctx), _ctx); /*2419*/
      return kk_std_core_types__tuple4_unbox(_x_x485, KK_OWNED, _ctx);
    }
    {
      kk_box_t x_1_10216;
      kk_function_t _x_x490 = kk_function_dup(f, _ctx); /*(788) -> 790 789*/
      kk_box_t _x_x488;
      {
        struct kk_std_core_types_Tuple4* _con_x489 = kk_std_core_types__as_Tuple4(t, _ctx);
        kk_box_t _x_1 = _con_x489->thd;
        kk_box_dup(_x_1, _ctx);
        _x_x488 = _x_1; /*788*/
      }
      x_1_10216 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x490, (_x_x490, _x_x488, _ctx), _ctx); /*789*/
      if (kk_yielding(kk_context())) {
        kk_box_drop(x_1_10216, _ctx);
        kk_box_t _x_x491 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_map_fun492(f, t, x_0_10213, x_10210, _ctx), _ctx); /*2419*/
        return kk_std_core_types__tuple4_unbox(_x_x491, KK_OWNED, _ctx);
      }
      {
        kk_box_t x_2_10219;
        kk_box_t _x_x494;
        {
          struct kk_std_core_types_Tuple4* _con_x495 = kk_std_core_types__as_Tuple4(t, _ctx);
          kk_box_t _pat_0_2_0 = _con_x495->fst;
          kk_box_t _pat_1_2 = _con_x495->snd;
          kk_box_t _pat_2_2 = _con_x495->thd;
          kk_box_t _x_2 = _con_x495->field4;
          if kk_likely(kk_datatype_ptr_is_unique(t, _ctx)) {
            kk_box_drop(_pat_2_2, _ctx);
            kk_box_drop(_pat_1_2, _ctx);
            kk_box_drop(_pat_0_2_0, _ctx);
            kk_datatype_ptr_free(t, _ctx);
          }
          else {
            kk_box_dup(_x_2, _ctx);
            kk_datatype_ptr_decref(t, _ctx);
          }
          _x_x494 = _x_2; /*788*/
        }
        x_2_10219 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x494, _ctx), _ctx); /*789*/
        if (kk_yielding(kk_context())) {
          kk_box_drop(x_2_10219, _ctx);
          kk_box_t _x_x496 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_map_fun497(x_0_10213, x_10210, x_1_10216, _ctx), _ctx); /*2419*/
          return kk_std_core_types__tuple4_unbox(_x_x496, KK_OWNED, _ctx);
        }
        {
          return kk_std_core_types__new_Tuple4(kk_reuse_null, 0, x_10210, x_0_10213, x_1_10216, x_2_10219, _ctx);
        }
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502__t {
  struct kk_function_s _base;
  kk_box_t _y_x10009;
  kk_box_t _y_x10010;
  kk_box_t _y_x10011;
  kk_box_t _y_x10012;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502(kk_function_t _fself, kk_box_t _b_x61, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_map_10131_fun502(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_box_t _y_x10011, kk_box_t _y_x10012, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502, kk_context());
  _self->_y_x10009 = _y_x10009;
  _self->_y_x10010 = _y_x10010;
  _self->_y_x10011 = _y_x10011;
  _self->_y_x10012 = _y_x10012;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502(kk_function_t _fself, kk_box_t _b_x61, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10131_fun502__t*, _fself, _ctx);
  kk_box_t _y_x10009 = _self->_y_x10009; /* 1024 */
  kk_box_t _y_x10010 = _self->_y_x10010; /* 1024 */
  kk_box_t _y_x10011 = _self->_y_x10011; /* 1024 */
  kk_box_t _y_x10012 = _self->_y_x10012; /* 1024 */
  kk_drop_match(_self, {kk_box_dup(_y_x10009, _ctx);kk_box_dup(_y_x10010, _ctx);kk_box_dup(_y_x10011, _ctx);kk_box_dup(_y_x10012, _ctx);}, {}, _ctx)
  kk_box_t _y_x10013_63 = _b_x61; /*1024*/;
  kk_std_core_types__tuple5 _x_x503 = kk_std_core_types__new_Tuple5(kk_reuse_null, 0, _y_x10009, _y_x10010, _y_x10011, _y_x10012, _y_x10013_63, _ctx); /*(161, 162, 163, 164, 165)*/
  return kk_std_core_types__tuple5_box(_x_x503, _ctx);
}

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10131(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_box_t _y_x10011, kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10012, kk_context_t* _ctx) { /* forall<a,b,e> (b, b, b, f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 
  kk_box_t x_10226;
  kk_box_t _x_x499;
  {
    struct kk_std_core_types_Tuple5* _con_x500 = kk_std_core_types__as_Tuple5(t, _ctx);
    kk_box_t _pat_0_3 = _con_x500->fst;
    kk_box_t _pat_1_3 = _con_x500->snd;
    kk_box_t _pat_2_3 = _con_x500->thd;
    kk_box_t _pat_3_3 = _con_x500->field4;
    kk_box_t _x_3 = _con_x500->field5;
    if kk_likely(kk_datatype_ptr_is_unique(t, _ctx)) {
      kk_box_drop(_pat_3_3, _ctx);
      kk_box_drop(_pat_2_3, _ctx);
      kk_box_drop(_pat_1_3, _ctx);
      kk_box_drop(_pat_0_3, _ctx);
      kk_datatype_ptr_free(t, _ctx);
    }
    else {
      kk_box_dup(_x_3, _ctx);
      kk_datatype_ptr_decref(t, _ctx);
    }
    _x_x499 = _x_3; /*1023*/
  }
  x_10226 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x499, _ctx), _ctx); /*1024*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10226, _ctx);
    kk_box_t _x_x501 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_map_10131_fun502(_y_x10009, _y_x10010, _y_x10011, _y_x10012, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple5_unbox(_x_x501, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_types__new_Tuple5(kk_reuse_null, 0, _y_x10009, _y_x10010, _y_x10011, _y_x10012, x_10226, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508__t {
  struct kk_function_s _base;
  kk_box_t _y_x10009;
  kk_box_t _y_x10010;
  kk_box_t _y_x10011;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508(kk_function_t _fself, kk_box_t _b_x65, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_map_10132_fun508(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_box_t _y_x10011, kk_function_t f, kk_std_core_types__tuple5 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508, kk_context());
  _self->_y_x10009 = _y_x10009;
  _self->_y_x10010 = _y_x10010;
  _self->_y_x10011 = _y_x10011;
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508(kk_function_t _fself, kk_box_t _b_x65, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10132_fun508__t*, _fself, _ctx);
  kk_box_t _y_x10009 = _self->_y_x10009; /* 1024 */
  kk_box_t _y_x10010 = _self->_y_x10010; /* 1024 */
  kk_box_t _y_x10011 = _self->_y_x10011; /* 1024 */
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_drop_match(_self, {kk_box_dup(_y_x10009, _ctx);kk_box_dup(_y_x10010, _ctx);kk_box_dup(_y_x10011, _ctx);kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10012_67 = _b_x65; /*1024*/;
  kk_std_core_types__tuple5 _x_x509 = kk_std_core_tuple_tuple5_fs__mlift_map_10131(_y_x10009, _y_x10010, _y_x10011, f, t, _y_x10012_67, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x509, _ctx);
}

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10132(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10011, kk_context_t* _ctx) { /* forall<a,b,e> (b, b, f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 
  kk_box_t x_10233;
  kk_function_t _x_x506 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
  kk_box_t _x_x504;
  {
    struct kk_std_core_types_Tuple5* _con_x505 = kk_std_core_types__as_Tuple5(t, _ctx);
    kk_box_t _x_2 = _con_x505->field4;
    kk_box_dup(_x_2, _ctx);
    _x_x504 = _x_2; /*1023*/
  }
  x_10233 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x506, (_x_x506, _x_x504, _ctx), _ctx); /*1024*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10233, _ctx);
    kk_box_t _x_x507 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_map_10132_fun508(_y_x10009, _y_x10010, _y_x10011, f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple5_unbox(_x_x507, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_map_10131(_y_x10009, _y_x10010, _y_x10011, f, t, x_10233, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514__t {
  struct kk_function_s _base;
  kk_box_t _y_x10009;
  kk_box_t _y_x10010;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514(kk_function_t _fself, kk_box_t _b_x69, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_map_10133_fun514(kk_box_t _y_x10009, kk_box_t _y_x10010, kk_function_t f, kk_std_core_types__tuple5 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514, kk_context());
  _self->_y_x10009 = _y_x10009;
  _self->_y_x10010 = _y_x10010;
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514(kk_function_t _fself, kk_box_t _b_x69, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10133_fun514__t*, _fself, _ctx);
  kk_box_t _y_x10009 = _self->_y_x10009; /* 1024 */
  kk_box_t _y_x10010 = _self->_y_x10010; /* 1024 */
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_drop_match(_self, {kk_box_dup(_y_x10009, _ctx);kk_box_dup(_y_x10010, _ctx);kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10011_71 = _b_x69; /*1024*/;
  kk_std_core_types__tuple5 _x_x515 = kk_std_core_tuple_tuple5_fs__mlift_map_10132(_y_x10009, _y_x10010, f, t, _y_x10011_71, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x515, _ctx);
}

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10133(kk_box_t _y_x10009, kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10010, kk_context_t* _ctx) { /* forall<a,b,e> (b, f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 
  kk_box_t x_10235;
  kk_function_t _x_x512 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
  kk_box_t _x_x510;
  {
    struct kk_std_core_types_Tuple5* _con_x511 = kk_std_core_types__as_Tuple5(t, _ctx);
    kk_box_t _x_1 = _con_x511->thd;
    kk_box_dup(_x_1, _ctx);
    _x_x510 = _x_1; /*1023*/
  }
  x_10235 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x512, (_x_x512, _x_x510, _ctx), _ctx); /*1024*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10235, _ctx);
    kk_box_t _x_x513 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_map_10133_fun514(_y_x10009, _y_x10010, f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple5_unbox(_x_x513, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_map_10132(_y_x10009, _y_x10010, f, t, x_10235, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520__t {
  struct kk_function_s _base;
  kk_box_t _y_x10009;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520(kk_function_t _fself, kk_box_t _b_x73, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_map_10134_fun520(kk_box_t _y_x10009, kk_function_t f, kk_std_core_types__tuple5 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520, kk_context());
  _self->_y_x10009 = _y_x10009;
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520(kk_function_t _fself, kk_box_t _b_x73, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_map_10134_fun520__t*, _fself, _ctx);
  kk_box_t _y_x10009 = _self->_y_x10009; /* 1024 */
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_drop_match(_self, {kk_box_dup(_y_x10009, _ctx);kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10010_75 = _b_x73; /*1024*/;
  kk_std_core_types__tuple5 _x_x521 = kk_std_core_tuple_tuple5_fs__mlift_map_10133(_y_x10009, f, t, _y_x10010_75, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x521, _ctx);
}

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs__mlift_map_10134(kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t _y_x10009, kk_context_t* _ctx) { /* forall<a,b,e> (f : (a) -> e b, t : (a, a, a, a, a), b) -> e (b, b, b, b, b) */ 
  kk_box_t x_10237;
  kk_function_t _x_x518 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
  kk_box_t _x_x516;
  {
    struct kk_std_core_types_Tuple5* _con_x517 = kk_std_core_types__as_Tuple5(t, _ctx);
    kk_box_t _x_0 = _con_x517->snd;
    kk_box_dup(_x_0, _ctx);
    _x_x516 = _x_0; /*1023*/
  }
  x_10237 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x518, (_x_x518, _x_x516, _ctx), _ctx); /*1024*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10237, _ctx);
    kk_box_t _x_x519 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_map_10134_fun520(_y_x10009, f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple5_unbox(_x_x519, KK_OWNED, _ctx);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_map_10133(_y_x10009, f, t, x_10237, _ctx);
  }
}
 
// Map a function over a quintuple of elements of the same type.


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_map_fun526__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun526(kk_function_t _fself, kk_box_t _b_x77, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_map_fun526(kk_function_t f, kk_std_core_types__tuple5 t, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun526__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_map_fun526__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_map_fun526, kk_context());
  _self->f = f;
  _self->t = t;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun526(kk_function_t _fself, kk_box_t _b_x77, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun526__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_map_fun526__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);}, {}, _ctx)
  kk_box_t _y_x10009_91 = _b_x77; /*1024*/;
  kk_std_core_types__tuple5 _x_x527 = kk_std_core_tuple_tuple5_fs__mlift_map_10134(f, t, _y_x10009_91, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x527, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_map_fun532__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
  kk_box_t x_10239;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun532(kk_function_t _fself, kk_box_t _b_x79, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_map_fun532(kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t x_10239, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun532__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_map_fun532__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_map_fun532, kk_context());
  _self->f = f;
  _self->t = t;
  _self->x_10239 = x_10239;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun532(kk_function_t _fself, kk_box_t _b_x79, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun532__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_map_fun532__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_box_t x_10239 = _self->x_10239; /* 1024 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);kk_box_dup(x_10239, _ctx);}, {}, _ctx)
  kk_box_t _y_x10010_92 = _b_x79; /*1024*/;
  kk_std_core_types__tuple5 _x_x533 = kk_std_core_tuple_tuple5_fs__mlift_map_10133(x_10239, f, t, _y_x10010_92, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x533, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_map_fun538__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
  kk_box_t x_0_10242;
  kk_box_t x_10239;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun538(kk_function_t _fself, kk_box_t _b_x81, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_map_fun538(kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t x_0_10242, kk_box_t x_10239, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun538__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_map_fun538__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_map_fun538, kk_context());
  _self->f = f;
  _self->t = t;
  _self->x_0_10242 = x_0_10242;
  _self->x_10239 = x_10239;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun538(kk_function_t _fself, kk_box_t _b_x81, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun538__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_map_fun538__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_box_t x_0_10242 = _self->x_0_10242; /* 1024 */
  kk_box_t x_10239 = _self->x_10239; /* 1024 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);kk_box_dup(x_0_10242, _ctx);kk_box_dup(x_10239, _ctx);}, {}, _ctx)
  kk_box_t _y_x10011_93 = _b_x81; /*1024*/;
  kk_std_core_types__tuple5 _x_x539 = kk_std_core_tuple_tuple5_fs__mlift_map_10132(x_10239, x_0_10242, f, t, _y_x10011_93, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x539, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_map_fun544__t {
  struct kk_function_s _base;
  kk_function_t f;
  kk_std_core_types__tuple5 t;
  kk_box_t x_0_10242;
  kk_box_t x_10239;
  kk_box_t x_1_10245;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun544(kk_function_t _fself, kk_box_t _b_x83, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_map_fun544(kk_function_t f, kk_std_core_types__tuple5 t, kk_box_t x_0_10242, kk_box_t x_10239, kk_box_t x_1_10245, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun544__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_map_fun544__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_map_fun544, kk_context());
  _self->f = f;
  _self->t = t;
  _self->x_0_10242 = x_0_10242;
  _self->x_10239 = x_10239;
  _self->x_1_10245 = x_1_10245;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun544(kk_function_t _fself, kk_box_t _b_x83, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun544__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_map_fun544__t*, _fself, _ctx);
  kk_function_t f = _self->f; /* (1023) -> 1025 1024 */
  kk_std_core_types__tuple5 t = _self->t; /* (1023, 1023, 1023, 1023, 1023) */
  kk_box_t x_0_10242 = _self->x_0_10242; /* 1024 */
  kk_box_t x_10239 = _self->x_10239; /* 1024 */
  kk_box_t x_1_10245 = _self->x_1_10245; /* 1024 */
  kk_drop_match(_self, {kk_function_dup(f, _ctx);kk_std_core_types__tuple5_dup(t, _ctx);kk_box_dup(x_0_10242, _ctx);kk_box_dup(x_10239, _ctx);kk_box_dup(x_1_10245, _ctx);}, {}, _ctx)
  kk_box_t _y_x10012_94 = _b_x83; /*1024*/;
  kk_std_core_types__tuple5 _x_x545 = kk_std_core_tuple_tuple5_fs__mlift_map_10131(x_10239, x_0_10242, x_1_10245, f, t, _y_x10012_94, _ctx); /*(1024, 1024, 1024, 1024, 1024)*/
  return kk_std_core_types__tuple5_box(_x_x545, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_map_fun549__t {
  struct kk_function_s _base;
  kk_box_t x_0_10242;
  kk_box_t x_10239;
  kk_box_t x_1_10245;
  kk_box_t x_2_10248;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun549(kk_function_t _fself, kk_box_t _b_x85, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_map_fun549(kk_box_t x_0_10242, kk_box_t x_10239, kk_box_t x_1_10245, kk_box_t x_2_10248, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun549__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_map_fun549__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_map_fun549, kk_context());
  _self->x_0_10242 = x_0_10242;
  _self->x_10239 = x_10239;
  _self->x_1_10245 = x_1_10245;
  _self->x_2_10248 = x_2_10248;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_map_fun549(kk_function_t _fself, kk_box_t _b_x85, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_map_fun549__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_map_fun549__t*, _fself, _ctx);
  kk_box_t x_0_10242 = _self->x_0_10242; /* 1024 */
  kk_box_t x_10239 = _self->x_10239; /* 1024 */
  kk_box_t x_1_10245 = _self->x_1_10245; /* 1024 */
  kk_box_t x_2_10248 = _self->x_2_10248; /* 1024 */
  kk_drop_match(_self, {kk_box_dup(x_0_10242, _ctx);kk_box_dup(x_10239, _ctx);kk_box_dup(x_1_10245, _ctx);kk_box_dup(x_2_10248, _ctx);}, {}, _ctx)
  kk_box_t _y_x10013_95 = _b_x85; /*1024*/;
  kk_std_core_types__tuple5 _x_x550 = kk_std_core_types__new_Tuple5(kk_reuse_null, 0, x_10239, x_0_10242, x_1_10245, x_2_10248, _y_x10013_95, _ctx); /*(161, 162, 163, 164, 165)*/
  return kk_std_core_types__tuple5_box(_x_x550, _ctx);
}

kk_std_core_types__tuple5 kk_std_core_tuple_tuple5_fs_map(kk_std_core_types__tuple5 t, kk_function_t f, kk_context_t* _ctx) { /* forall<a,b,e> (t : (a, a, a, a, a), f : (a) -> e b) -> e (b, b, b, b, b) */ 
  kk_box_t x_10239;
  kk_function_t _x_x524 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
  kk_box_t _x_x522;
  {
    struct kk_std_core_types_Tuple5* _con_x523 = kk_std_core_types__as_Tuple5(t, _ctx);
    kk_box_t _x = _con_x523->fst;
    kk_box_dup(_x, _ctx);
    _x_x522 = _x; /*1023*/
  }
  x_10239 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x524, (_x_x524, _x_x522, _ctx), _ctx); /*1024*/
  if (kk_yielding(kk_context())) {
    kk_box_drop(x_10239, _ctx);
    kk_box_t _x_x525 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_map_fun526(f, t, _ctx), _ctx); /*2419*/
    return kk_std_core_types__tuple5_unbox(_x_x525, KK_OWNED, _ctx);
  }
  {
    kk_box_t x_0_10242;
    kk_function_t _x_x530 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
    kk_box_t _x_x528;
    {
      struct kk_std_core_types_Tuple5* _con_x529 = kk_std_core_types__as_Tuple5(t, _ctx);
      kk_box_t _x_0 = _con_x529->snd;
      kk_box_dup(_x_0, _ctx);
      _x_x528 = _x_0; /*1023*/
    }
    x_0_10242 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x530, (_x_x530, _x_x528, _ctx), _ctx); /*1024*/
    if (kk_yielding(kk_context())) {
      kk_box_drop(x_0_10242, _ctx);
      kk_box_t _x_x531 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_map_fun532(f, t, x_10239, _ctx), _ctx); /*2419*/
      return kk_std_core_types__tuple5_unbox(_x_x531, KK_OWNED, _ctx);
    }
    {
      kk_box_t x_1_10245;
      kk_function_t _x_x536 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
      kk_box_t _x_x534;
      {
        struct kk_std_core_types_Tuple5* _con_x535 = kk_std_core_types__as_Tuple5(t, _ctx);
        kk_box_t _x_1 = _con_x535->thd;
        kk_box_dup(_x_1, _ctx);
        _x_x534 = _x_1; /*1023*/
      }
      x_1_10245 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x536, (_x_x536, _x_x534, _ctx), _ctx); /*1024*/
      if (kk_yielding(kk_context())) {
        kk_box_drop(x_1_10245, _ctx);
        kk_box_t _x_x537 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_map_fun538(f, t, x_0_10242, x_10239, _ctx), _ctx); /*2419*/
        return kk_std_core_types__tuple5_unbox(_x_x537, KK_OWNED, _ctx);
      }
      {
        kk_box_t x_2_10248;
        kk_function_t _x_x542 = kk_function_dup(f, _ctx); /*(1023) -> 1025 1024*/
        kk_box_t _x_x540;
        {
          struct kk_std_core_types_Tuple5* _con_x541 = kk_std_core_types__as_Tuple5(t, _ctx);
          kk_box_t _x_2 = _con_x541->field4;
          kk_box_dup(_x_2, _ctx);
          _x_x540 = _x_2; /*1023*/
        }
        x_2_10248 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), _x_x542, (_x_x542, _x_x540, _ctx), _ctx); /*1024*/
        if (kk_yielding(kk_context())) {
          kk_box_drop(x_2_10248, _ctx);
          kk_box_t _x_x543 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_map_fun544(f, t, x_0_10242, x_10239, x_1_10245, _ctx), _ctx); /*2419*/
          return kk_std_core_types__tuple5_unbox(_x_x543, KK_OWNED, _ctx);
        }
        {
          kk_box_t x_3_10251;
          kk_box_t _x_x546;
          {
            struct kk_std_core_types_Tuple5* _con_x547 = kk_std_core_types__as_Tuple5(t, _ctx);
            kk_box_t _pat_0_3_0 = _con_x547->fst;
            kk_box_t _pat_1_3 = _con_x547->snd;
            kk_box_t _pat_2_3 = _con_x547->thd;
            kk_box_t _pat_3_3 = _con_x547->field4;
            kk_box_t _x_3 = _con_x547->field5;
            if kk_likely(kk_datatype_ptr_is_unique(t, _ctx)) {
              kk_box_drop(_pat_3_3, _ctx);
              kk_box_drop(_pat_2_3, _ctx);
              kk_box_drop(_pat_1_3, _ctx);
              kk_box_drop(_pat_0_3_0, _ctx);
              kk_datatype_ptr_free(t, _ctx);
            }
            else {
              kk_box_dup(_x_3, _ctx);
              kk_datatype_ptr_decref(t, _ctx);
            }
            _x_x546 = _x_3; /*1023*/
          }
          x_3_10251 = kk_function_call(kk_box_t, (kk_function_t, kk_box_t, kk_context_t*), f, (f, _x_x546, _ctx), _ctx); /*1024*/
          if (kk_yielding(kk_context())) {
            kk_box_drop(x_3_10251, _ctx);
            kk_box_t _x_x548 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_map_fun549(x_0_10242, x_10239, x_1_10245, x_2_10248, _ctx), _ctx); /*2419*/
            return kk_std_core_types__tuple5_unbox(_x_x548, KK_OWNED, _ctx);
          }
          {
            return kk_std_core_types__new_Tuple5(kk_reuse_null, 0, x_10239, x_0_10242, x_1_10245, x_2_10248, x_3_10251, _ctx);
          }
        }
      }
    }
  }
}
 
// Element-wise tuple equality


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs__lp__at_x_fun552__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_;
  kk_box_t y1;
  kk_box_t y2;
};
static kk_box_t kk_std_core_tuple_tuple2_fs__lp__at_x_fun552_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x97, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs__lp__at_new_x_fun552_eq__eq__rp_(kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_box_t y1, kk_box_t y2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__lp__at_x_fun552__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs__lp__at_x_fun552__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs__lp__at_x_fun552_eq__eq__rp_, kk_context());
  _self->_implicit_fs_snd_fs__lp__eq__eq__rp_ = _implicit_fs_snd_fs__lp__eq__eq__rp_;
  _self->y1 = y1;
  _self->y2 = y2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs__lp__at_x_fun552_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x97, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__lp__at_x_fun552__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs__lp__at_x_fun552__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_snd_fs__lp__eq__eq__rp_; /* (1162, 1162) -> 1163 bool */
  kk_box_t y1 = _self->y1; /* 1162 */
  kk_box_t y2 = _self->y2; /* 1162 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);}, {}, _ctx)
  bool _y_x10014_99 = kk_bool_unbox(_b_x97); /*bool*/;
  bool _x_x553;
  if (_y_x10014_99) {
    _x_x553 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
    _x_x553 = false; /*bool*/
  }
  return kk_bool_box(_x_x553);
}

bool kk_std_core_tuple_tuple2_fs__lp__eq__eq__rp_(kk_std_core_types__tuple2 _pat_x36__22, kk_std_core_types__tuple2 _pat_x36__39, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_context_t* _ctx) { /* forall<a,b,e> ((a, b), (a, b), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool) -> e bool */ 
  {
    kk_box_t x1 = _pat_x36__22.fst;
    kk_box_t y1 = _pat_x36__22.snd;
    {
      kk_box_t x2 = _pat_x36__39.fst;
      kk_box_t y2 = _pat_x36__39.snd;
      bool x_10259 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs__lp__eq__eq__rp_, (_implicit_fs_fst_fs__lp__eq__eq__rp_, x1, x2, _ctx), _ctx); /*bool*/;
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x551 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs__lp__at_new_x_fun552_eq__eq__rp_(_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*2419*/
        return kk_bool_unbox(_x_x551);
      }
      if (x_10259) {
        return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx);
      }
      {
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
        return false;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x101, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__lp__at_new_mlift_x_10137_fun555_eq__eq__rp_(kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555_eq__eq__rp_, kk_context());
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x101, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_fun555__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1344, 1344) -> 1345 bool */
  kk_box_t z1 = _self->z1; /* 1344 */
  kk_box_t z2 = _self->z2; /* 1344 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _x_x556;
  bool _y_x10020_103 = kk_bool_unbox(_b_x101); /*bool*/;
  if (_y_x10020_103) {
    _x_x556 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    _x_x556 = false; /*bool*/
  }
  return kk_bool_box(_x_x556);
}

bool kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_eq__eq__rp_(kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, bool _y_x10019, kk_context_t* _ctx) { /* forall<a,b,e> (?snd/(==) : (a, a) -> e bool, ?thd/(==) : (b, b) -> e bool, y1 : a, y2 : a, z1 : b, z2 : b, bool) -> e bool */ 
  if (_y_x10019) {
    bool x_10266 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x554 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__lp__at_new_mlift_x_10137_fun555_eq__eq__rp_(_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x554);
    }
    if (x_10266) {
      return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx);
    }
    {
      kk_box_drop(z2, _ctx);
      kk_box_drop(z1, _ctx);
      kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
      return false;
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// Element-wise triple equality


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun558__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t y1;
  kk_box_t y2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__lp__at_x_fun558_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x106, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__lp__at_new_x_fun558_eq__eq__rp_(kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun558__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun558__t_eq__eq__rp_, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__lp__at_x_fun558_eq__eq__rp_, kk_context());
  _self->_implicit_fs_snd_fs__lp__eq__eq__rp_ = _implicit_fs_snd_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->y1 = y1;
  _self->y2 = y2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__lp__at_x_fun558_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x106, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun558__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun558__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_snd_fs__lp__eq__eq__rp_; /* (1343, 1343) -> 1345 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1344, 1344) -> 1345 bool */
  kk_box_t y1 = _self->y1; /* 1343 */
  kk_box_t y2 = _self->y2; /* 1343 */
  kk_box_t z1 = _self->z1; /* 1344 */
  kk_box_t z2 = _self->z2; /* 1344 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10019_111 = kk_bool_unbox(_b_x106); /*bool*/;
  bool _x_x559 = kk_std_core_tuple_tuple3_fs__lp__at_mlift_x_10137_eq__eq__rp_(_implicit_fs_snd_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, y1, y2, z1, z2, _y_x10019_111, _ctx); /*bool*/
  return kk_bool_box(_x_x559);
}


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun561__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__lp__at_x_fun561_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x108, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__lp__at_new_x_fun561_eq__eq__rp_(kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun561__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun561__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__lp__at_x_fun561_eq__eq__rp_, kk_context());
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__lp__at_x_fun561_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x108, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun561__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__lp__at_x_fun561__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1344, 1344) -> 1345 bool */
  kk_box_t z1 = _self->z1; /* 1344 */
  kk_box_t z2 = _self->z2; /* 1344 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10020_112 = kk_bool_unbox(_b_x108); /*bool*/;
  bool _x_x562;
  if (_y_x10020_112) {
    _x_x562 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    _x_x562 = false; /*bool*/
  }
  return kk_bool_box(_x_x562);
}

bool kk_std_core_tuple_tuple3_fs__lp__eq__eq__rp_(kk_std_core_types__tuple3 _pat_x40__22, kk_std_core_types__tuple3 _pat_x40__44, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_context_t* _ctx) { /* forall<a,b,c,e> ((a, b, c), (a, b, c), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool, ?thd/(==) : (c, c) -> e bool) -> e bool */ 
  {
    kk_box_t x1 = _pat_x40__22.fst;
    kk_box_t y1 = _pat_x40__22.snd;
    kk_box_t z1 = _pat_x40__22.thd;
    {
      kk_box_t x2 = _pat_x40__44.fst;
      kk_box_t y2 = _pat_x40__44.snd;
      kk_box_t z2 = _pat_x40__44.thd;
      bool x_10272 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs__lp__eq__eq__rp_, (_implicit_fs_fst_fs__lp__eq__eq__rp_, x1, x2, _ctx), _ctx); /*bool*/;
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x557 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__lp__at_new_x_fun558_eq__eq__rp_(_implicit_fs_snd_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, y1, y2, z1, z2, _ctx), _ctx); /*2419*/
        return kk_bool_unbox(_x_x557);
      }
      if (x_10272) {
        bool x_0_10275 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/;
        if (kk_yielding(kk_context())) {
          kk_box_t _x_x560 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__lp__at_new_x_fun561_eq__eq__rp_(_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*2419*/
          return kk_bool_unbox(_x_x560);
        }
        if (x_0_10275) {
          return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx);
        }
        {
          kk_box_drop(z2, _ctx);
          kk_box_drop(z1, _ctx);
          kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
          return false;
        }
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
        kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
        return false;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x114, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__lp__at_new_mlift_x_10139_fun564_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x114, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_fun564__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1583, 1583) -> 1584 bool */
  kk_box_t w1 = _self->w1; /* 1583 */
  kk_box_t w2 = _self->w2; /* 1583 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  bool _x_x565;
  bool _y_x10028_116 = kk_bool_unbox(_b_x114); /*bool*/;
  if (_y_x10028_116) {
    _x_x565 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    _x_x565 = false; /*bool*/
  }
  return kk_bool_box(_x_x565);
}

bool kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, bool _y_x10027, kk_context_t* _ctx) { /* forall<a,b,e> (?field4/(==) : (b, b) -> e bool, ?thd/(==) : (a, a) -> e bool, w1 : b, w2 : b, z1 : a, z2 : a, bool) -> e bool */ 
  if (_y_x10027) {
    bool x_10282 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*bool*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x563 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__lp__at_new_mlift_x_10139_fun564_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x563);
    }
    if (x_10282) {
      return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx);
    }
    {
      kk_box_drop(w2, _ctx);
      kk_box_drop(w1, _ctx);
      kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
      return false;
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x119, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__lp__at_new_mlift_x_10140_fun567_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567__t_eq__eq__rp_, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x119, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_fun567__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1583, 1583) -> 1584 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1582, 1582) -> 1584 bool */
  kk_box_t w1 = _self->w1; /* 1583 */
  kk_box_t w2 = _self->w2; /* 1583 */
  kk_box_t z1 = _self->z1; /* 1582 */
  kk_box_t z2 = _self->z2; /* 1582 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10027_121 = kk_bool_unbox(_b_x119); /*bool*/;
  bool _x_x568 = kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, z1, z2, _y_x10027_121, _ctx); /*bool*/
  return kk_bool_box(_x_x568);
}

bool kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, bool _y_x10026, kk_context_t* _ctx) { /* forall<a,b,c,e> (?field4/(==) : (c, c) -> e bool, ?snd/(==) : (a, a) -> e bool, ?thd/(==) : (b, b) -> e bool, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, bool) -> e bool */ 
  if (_y_x10026) {
    bool x_10288 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x566 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__lp__at_new_mlift_x_10140_fun567_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, z1, z2, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x566);
    }
    {
      return kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, z1, z2, x_10288, _ctx);
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// Element-wise quadruple equality


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun572__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t y1;
  kk_box_t y2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_x_fun572_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x123, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__lp__at_new_x_fun572_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun572__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun572__t_eq__eq__rp_, 10, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__lp__at_x_fun572_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_snd_fs__lp__eq__eq__rp_ = _implicit_fs_snd_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->y1 = y1;
  _self->y2 = y2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_x_fun572_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x123, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun572__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun572__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1583, 1583) -> 1584 bool */
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_snd_fs__lp__eq__eq__rp_; /* (1581, 1581) -> 1584 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1582, 1582) -> 1584 bool */
  kk_box_t w1 = _self->w1; /* 1583 */
  kk_box_t w2 = _self->w2; /* 1583 */
  kk_box_t y1 = _self->y1; /* 1581 */
  kk_box_t y2 = _self->y2; /* 1581 */
  kk_box_t z1 = _self->z1; /* 1582 */
  kk_box_t z2 = _self->z2; /* 1582 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10026_131 = kk_bool_unbox(_b_x123); /*bool*/;
  bool _x_x573 = kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10140_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_snd_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, y1, y2, z1, z2, _y_x10026_131, _ctx); /*bool*/
  return kk_bool_box(_x_x573);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun575__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_x_fun575_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x125, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__lp__at_new_x_fun575_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun575__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun575__t_eq__eq__rp_, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__lp__at_x_fun575_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_x_fun575_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x125, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun575__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun575__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1583, 1583) -> 1584 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1582, 1582) -> 1584 bool */
  kk_box_t w1 = _self->w1; /* 1583 */
  kk_box_t w2 = _self->w2; /* 1583 */
  kk_box_t z1 = _self->z1; /* 1582 */
  kk_box_t z2 = _self->z2; /* 1582 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10027_132 = kk_bool_unbox(_b_x125); /*bool*/;
  bool _x_x576 = kk_std_core_tuple_tuple4_fs__lp__at_mlift_x_10139_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, z1, z2, _y_x10027_132, _ctx); /*bool*/
  return kk_bool_box(_x_x576);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun578__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_x_fun578_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x127, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__lp__at_new_x_fun578_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun578__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun578__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__lp__at_x_fun578_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__lp__at_x_fun578_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x127, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun578__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__lp__at_x_fun578__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1583, 1583) -> 1584 bool */
  kk_box_t w1 = _self->w1; /* 1583 */
  kk_box_t w2 = _self->w2; /* 1583 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  bool _y_x10028_133 = kk_bool_unbox(_b_x127); /*bool*/;
  bool _x_x579;
  if (_y_x10028_133) {
    _x_x579 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    _x_x579 = false; /*bool*/
  }
  return kk_bool_box(_x_x579);
}

bool kk_std_core_tuple_tuple4_fs__lp__eq__eq__rp_(kk_std_core_types__tuple4 _pat_x44__22, kk_std_core_types__tuple4 _pat_x44__49, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_context_t* _ctx) { /* forall<a,b,c,d,e> ((a, b, c, d), (a, b, c, d), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool, ?thd/(==) : (c, c) -> e bool, ?field4/(==) : (d, d) -> e bool) -> e bool */ 
  {
    struct kk_std_core_types_Tuple4* _con_x569 = kk_std_core_types__as_Tuple4(_pat_x44__22, _ctx);
    kk_box_t x1 = _con_x569->fst;
    kk_box_t y1 = _con_x569->snd;
    kk_box_t z1 = _con_x569->thd;
    kk_box_t w1 = _con_x569->field4;
    if kk_likely(kk_datatype_ptr_is_unique(_pat_x44__22, _ctx)) {
      kk_datatype_ptr_free(_pat_x44__22, _ctx);
    }
    else {
      kk_box_dup(w1, _ctx);
      kk_box_dup(x1, _ctx);
      kk_box_dup(y1, _ctx);
      kk_box_dup(z1, _ctx);
      kk_datatype_ptr_decref(_pat_x44__22, _ctx);
    }
    {
      struct kk_std_core_types_Tuple4* _con_x570 = kk_std_core_types__as_Tuple4(_pat_x44__49, _ctx);
      kk_box_t x2 = _con_x570->fst;
      kk_box_t y2 = _con_x570->snd;
      kk_box_t z2 = _con_x570->thd;
      kk_box_t w2 = _con_x570->field4;
      if kk_likely(kk_datatype_ptr_is_unique(_pat_x44__49, _ctx)) {
        kk_datatype_ptr_free(_pat_x44__49, _ctx);
      }
      else {
        kk_box_dup(w2, _ctx);
        kk_box_dup(x2, _ctx);
        kk_box_dup(y2, _ctx);
        kk_box_dup(z2, _ctx);
        kk_datatype_ptr_decref(_pat_x44__49, _ctx);
      }
      bool x_10290 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs__lp__eq__eq__rp_, (_implicit_fs_fst_fs__lp__eq__eq__rp_, x1, x2, _ctx), _ctx); /*bool*/;
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x571 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__lp__at_new_x_fun572_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_snd_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, y1, y2, z1, z2, _ctx), _ctx); /*2419*/
        return kk_bool_unbox(_x_x571);
      }
      if (x_10290) {
        bool x_0_10293 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/;
        if (kk_yielding(kk_context())) {
          kk_box_t _x_x574 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__lp__at_new_x_fun575_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, w1, w2, z1, z2, _ctx), _ctx); /*2419*/
          return kk_bool_unbox(_x_x574);
        }
        if (x_0_10293) {
          bool x_1_10296 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*bool*/;
          if (kk_yielding(kk_context())) {
            kk_box_t _x_x577 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__lp__at_new_x_fun578_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx); /*2419*/
            return kk_bool_unbox(_x_x577);
          }
          if (x_1_10296) {
            return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx);
          }
          {
            kk_box_drop(w2, _ctx);
            kk_box_drop(w1, _ctx);
            kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
            return false;
          }
        }
        {
          kk_box_drop(z2, _ctx);
          kk_box_drop(z1, _ctx);
          kk_box_drop(w2, _ctx);
          kk_box_drop(w1, _ctx);
          kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
          kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
          return false;
        }
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_box_drop(w2, _ctx);
        kk_box_drop(w1, _ctx);
        kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
        kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
        kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
        return false;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x135, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_mlift_x_10142_fun581_eq__eq__rp_(kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x135, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_fun581__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);}, {}, _ctx)
  bool _x_x582;
  bool _y_x10038_137 = kk_bool_unbox(_b_x135); /*bool*/;
  if (_y_x10038_137) {
    _x_x582 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs__lp__eq__eq__rp_, (_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
    _x_x582 = false; /*bool*/
  }
  return kk_bool_box(_x_x582);
}

bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, bool _y_x10037, kk_context_t* _ctx) { /* forall<a,e,b> (?field4/(==) : (a, a) -> e bool, ?field5/(==) : (b, b) -> e bool, v1 : b, v2 : b, w1 : a, w2 : a, bool) -> e bool */ 
  if (_y_x10037) {
    bool x_10303 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx); /*bool*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x580 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_mlift_x_10142_fun581_eq__eq__rp_(_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x580);
    }
    if (x_10303) {
      return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs__lp__eq__eq__rp_, (_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx);
    }
    {
      kk_box_drop(v2, _ctx);
      kk_box_drop(v1, _ctx);
      kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
      return false;
    }
  }
  {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x140, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_mlift_x_10143_fun584_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584__t_eq__eq__rp_, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x140, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_fun584__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1878, 1878) -> 1879 bool */
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_box_t w1 = _self->w1; /* 1878 */
  kk_box_t w2 = _self->w2; /* 1878 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  bool _y_x10037_142 = kk_bool_unbox(_b_x140); /*bool*/;
  bool _x_x585 = kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, w1, w2, _y_x10037_142, _ctx); /*bool*/
  return kk_bool_box(_x_x585);
}

bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, bool _y_x10036, kk_context_t* _ctx) { /* forall<a,b,e,c> (?field4/(==) : (b, b) -> e bool, ?field5/(==) : (c, c) -> e bool, ?thd/(==) : (a, a) -> e bool, v1 : c, v2 : c, w1 : b, w2 : b, z1 : a, z2 : a, bool) -> e bool */ 
  if (_y_x10036) {
    bool x_10309 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*bool*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x583 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_mlift_x_10143_fun584_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, w1, w2, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x583);
    }
    {
      return kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, w1, w2, x_10309, _ctx);
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x144, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_mlift_x_10144_fun587_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587__t_eq__eq__rp_, 10, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x144, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_fun587__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1878, 1878) -> 1879 bool */
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1877, 1877) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_box_t w1 = _self->w1; /* 1878 */
  kk_box_t w2 = _self->w2; /* 1878 */
  kk_box_t z1 = _self->z1; /* 1877 */
  kk_box_t z2 = _self->z2; /* 1877 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10036_146 = kk_bool_unbox(_b_x144); /*bool*/;
  bool _x_x588 = kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, z1, z2, _y_x10036_146, _ctx); /*bool*/
  return kk_bool_box(_x_x588);
}

bool kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, bool _y_x10035, kk_context_t* _ctx) { /* forall<a,b,c,e,d> (?field4/(==) : (c, c) -> e bool, ?field5/(==) : (d, d) -> e bool, ?snd/(==) : (a, a) -> e bool, ?thd/(==) : (b, b) -> e bool, v1 : d, v2 : d, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, bool) -> e bool */ 
  if (_y_x10035) {
    bool x_10311 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x586 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_mlift_x_10144_fun587_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, z1, z2, _ctx), _ctx); /*2419*/
      return kk_bool_unbox(_x_x586);
    }
    {
      return kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, z1, z2, x_10311, _ctx);
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
    kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
    return false;
  }
}
 
// Element-wise quintuple equality


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun592__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t y1;
  kk_box_t y2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun592_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x148, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun592_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun592__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun592__t_eq__eq__rp_, 13, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_x_fun592_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_snd_fs__lp__eq__eq__rp_ = _implicit_fs_snd_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->y1 = y1;
  _self->y2 = y2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun592_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x148, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun592__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun592__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1878, 1878) -> 1879 bool */
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_snd_fs__lp__eq__eq__rp_; /* (1876, 1876) -> 1879 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1877, 1877) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_box_t w1 = _self->w1; /* 1878 */
  kk_box_t w2 = _self->w2; /* 1878 */
  kk_box_t y1 = _self->y1; /* 1876 */
  kk_box_t y2 = _self->y2; /* 1876 */
  kk_box_t z1 = _self->z1; /* 1877 */
  kk_box_t z2 = _self->z2; /* 1877 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10035_159 = kk_bool_unbox(_b_x148); /*bool*/;
  bool _x_x593 = kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10144_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_snd_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, y1, y2, z1, z2, _y_x10035_159, _ctx); /*bool*/
  return kk_bool_box(_x_x593);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun595__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun595_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x150, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun595_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun595__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun595__t_eq__eq__rp_, 10, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_x_fun595_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_thd_fs__lp__eq__eq__rp_ = _implicit_fs_thd_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun595_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x150, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun595__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun595__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1878, 1878) -> 1879 bool */
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_ = _self->_implicit_fs_thd_fs__lp__eq__eq__rp_; /* (1877, 1877) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_box_t w1 = _self->w1; /* 1878 */
  kk_box_t w2 = _self->w2; /* 1878 */
  kk_box_t z1 = _self->z1; /* 1877 */
  kk_box_t z2 = _self->z2; /* 1877 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  bool _y_x10036_160 = kk_bool_unbox(_b_x150); /*bool*/;
  bool _x_x596 = kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10143_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, z1, z2, _y_x10036_160, _ctx); /*bool*/
  return kk_bool_box(_x_x596);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun598__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun598_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x152, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun598_eq__eq__rp_(kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun598__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun598__t_eq__eq__rp_, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_x_fun598_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field4_fs__lp__eq__eq__rp_ = _implicit_fs_field4_fs__lp__eq__eq__rp_;
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun598_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x152, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun598__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun598__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field4_fs__lp__eq__eq__rp_; /* (1878, 1878) -> 1879 bool */
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_box_t w1 = _self->w1; /* 1878 */
  kk_box_t w2 = _self->w2; /* 1878 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  bool _y_x10037_161 = kk_bool_unbox(_b_x152); /*bool*/;
  bool _x_x599 = kk_std_core_tuple_tuple5_fs__lp__at_mlift_x_10142_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, w1, w2, _y_x10037_161, _ctx); /*bool*/
  return kk_bool_box(_x_x599);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun601__t_eq__eq__rp_ {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_;
  kk_box_t v1;
  kk_box_t v2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun601_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x154, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun601_eq__eq__rp_(kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_box_t v1, kk_box_t v2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun601__t_eq__eq__rp_* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun601__t_eq__eq__rp_, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__lp__at_x_fun601_eq__eq__rp_, kk_context());
  _self->_implicit_fs_field5_fs__lp__eq__eq__rp_ = _implicit_fs_field5_fs__lp__eq__eq__rp_;
  _self->v1 = v1;
  _self->v2 = v2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__lp__at_x_fun601_eq__eq__rp_(kk_function_t _fself, kk_box_t _b_x154, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun601__t_eq__eq__rp_* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__lp__at_x_fun601__t_eq__eq__rp_*, _fself, _ctx);
  kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_ = _self->_implicit_fs_field5_fs__lp__eq__eq__rp_; /* (1880, 1880) -> 1879 bool */
  kk_box_t v1 = _self->v1; /* 1880 */
  kk_box_t v2 = _self->v2; /* 1880 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);}, {}, _ctx)
  bool _y_x10038_162 = kk_bool_unbox(_b_x154); /*bool*/;
  bool _x_x602;
  if (_y_x10038_162) {
    _x_x602 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs__lp__eq__eq__rp_, (_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx); /*bool*/
  }
  else {
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
    _x_x602 = false; /*bool*/
  }
  return kk_bool_box(_x_x602);
}

bool kk_std_core_tuple_tuple5_fs__lp__eq__eq__rp_(kk_std_core_types__tuple5 _pat_x50__22, kk_std_core_types__tuple5 _pat_x50__54, kk_function_t _implicit_fs_fst_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_snd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_thd_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field4_fs__lp__eq__eq__rp_, kk_function_t _implicit_fs_field5_fs__lp__eq__eq__rp_, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> ((a, b, c, d, a1), (a, b, c, d, a1), ?fst/(==) : (a, a) -> e bool, ?snd/(==) : (b, b) -> e bool, ?thd/(==) : (c, c) -> e bool, ?field4/(==) : (d, d) -> e bool, ?field5/(==) : (a1, a1) -> e bool) -> e bool */ 
  {
    struct kk_std_core_types_Tuple5* _con_x589 = kk_std_core_types__as_Tuple5(_pat_x50__22, _ctx);
    kk_box_t x1 = _con_x589->fst;
    kk_box_t y1 = _con_x589->snd;
    kk_box_t z1 = _con_x589->thd;
    kk_box_t w1 = _con_x589->field4;
    kk_box_t v1 = _con_x589->field5;
    if kk_likely(kk_datatype_ptr_is_unique(_pat_x50__22, _ctx)) {
      kk_datatype_ptr_free(_pat_x50__22, _ctx);
    }
    else {
      kk_box_dup(v1, _ctx);
      kk_box_dup(w1, _ctx);
      kk_box_dup(x1, _ctx);
      kk_box_dup(y1, _ctx);
      kk_box_dup(z1, _ctx);
      kk_datatype_ptr_decref(_pat_x50__22, _ctx);
    }
    {
      struct kk_std_core_types_Tuple5* _con_x590 = kk_std_core_types__as_Tuple5(_pat_x50__54, _ctx);
      kk_box_t x2 = _con_x590->fst;
      kk_box_t y2 = _con_x590->snd;
      kk_box_t z2 = _con_x590->thd;
      kk_box_t w2 = _con_x590->field4;
      kk_box_t v2 = _con_x590->field5;
      if kk_likely(kk_datatype_ptr_is_unique(_pat_x50__54, _ctx)) {
        kk_datatype_ptr_free(_pat_x50__54, _ctx);
      }
      else {
        kk_box_dup(v2, _ctx);
        kk_box_dup(w2, _ctx);
        kk_box_dup(x2, _ctx);
        kk_box_dup(y2, _ctx);
        kk_box_dup(z2, _ctx);
        kk_datatype_ptr_decref(_pat_x50__54, _ctx);
      }
      bool x_10313 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs__lp__eq__eq__rp_, (_implicit_fs_fst_fs__lp__eq__eq__rp_, x1, x2, _ctx), _ctx); /*bool*/;
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x591 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun592_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_snd_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, y1, y2, z1, z2, _ctx), _ctx); /*2419*/
        return kk_bool_unbox(_x_x591);
      }
      if (x_10313) {
        bool x_0_10316 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs__lp__eq__eq__rp_, (_implicit_fs_snd_fs__lp__eq__eq__rp_, y1, y2, _ctx), _ctx); /*bool*/;
        if (kk_yielding(kk_context())) {
          kk_box_t _x_x594 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun595_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, _implicit_fs_thd_fs__lp__eq__eq__rp_, v1, v2, w1, w2, z1, z2, _ctx), _ctx); /*2419*/
          return kk_bool_unbox(_x_x594);
        }
        if (x_0_10316) {
          bool x_1_10319 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs__lp__eq__eq__rp_, (_implicit_fs_thd_fs__lp__eq__eq__rp_, z1, z2, _ctx), _ctx); /*bool*/;
          if (kk_yielding(kk_context())) {
            kk_box_t _x_x597 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun598_eq__eq__rp_(_implicit_fs_field4_fs__lp__eq__eq__rp_, _implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, w1, w2, _ctx), _ctx); /*2419*/
            return kk_bool_unbox(_x_x597);
          }
          if (x_1_10319) {
            bool x_2_10322 = kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs__lp__eq__eq__rp_, (_implicit_fs_field4_fs__lp__eq__eq__rp_, w1, w2, _ctx), _ctx); /*bool*/;
            if (kk_yielding(kk_context())) {
              kk_box_t _x_x600 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__lp__at_new_x_fun601_eq__eq__rp_(_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx); /*2419*/
              return kk_bool_unbox(_x_x600);
            }
            if (x_2_10322) {
              return kk_function_call(bool, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs__lp__eq__eq__rp_, (_implicit_fs_field5_fs__lp__eq__eq__rp_, v1, v2, _ctx), _ctx);
            }
            {
              kk_box_drop(v2, _ctx);
              kk_box_drop(v1, _ctx);
              kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
              return false;
            }
          }
          {
            kk_box_drop(w2, _ctx);
            kk_box_drop(w1, _ctx);
            kk_box_drop(v2, _ctx);
            kk_box_drop(v1, _ctx);
            kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
            kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
            return false;
          }
        }
        {
          kk_box_drop(z2, _ctx);
          kk_box_drop(z1, _ctx);
          kk_box_drop(w2, _ctx);
          kk_box_drop(w1, _ctx);
          kk_box_drop(v2, _ctx);
          kk_box_drop(v1, _ctx);
          kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
          kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
          kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
          return false;
        }
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_box_drop(w2, _ctx);
        kk_box_drop(w1, _ctx);
        kk_box_drop(v2, _ctx);
        kk_box_drop(v1, _ctx);
        kk_function_drop(_implicit_fs_thd_fs__lp__eq__eq__rp_, _ctx);
        kk_function_drop(_implicit_fs_snd_fs__lp__eq__eq__rp_, _ctx);
        kk_function_drop(_implicit_fs_field5_fs__lp__eq__eq__rp_, _ctx);
        kk_function_drop(_implicit_fs_field4_fs__lp__eq__eq__rp_, _ctx);
        return false;
      }
    }
  }
}
 
// Order on tuples


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs_cmp_fun604__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_snd_fs_cmp;
  kk_box_t y1;
  kk_box_t y2;
};
static kk_box_t kk_std_core_tuple_tuple2_fs_cmp_fun604(kk_function_t _fself, kk_box_t _b_x164, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs_new_cmp_fun604(kk_function_t _implicit_fs_snd_fs_cmp, kk_box_t y1, kk_box_t y2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_cmp_fun604__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs_cmp_fun604__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs_cmp_fun604, kk_context());
  _self->_implicit_fs_snd_fs_cmp = _implicit_fs_snd_fs_cmp;
  _self->y1 = y1;
  _self->y2 = y2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs_cmp_fun604(kk_function_t _fself, kk_box_t _b_x164, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_cmp_fun604__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs_cmp_fun604__t*, _fself, _ctx);
  kk_function_t _implicit_fs_snd_fs_cmp = _self->_implicit_fs_snd_fs_cmp; /* (1984, 1984) -> 1985 order */
  kk_box_t y1 = _self->y1; /* 1984 */
  kk_box_t y2 = _self->y2; /* 1984 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10046_166 = kk_std_core_types__order_unbox(_b_x164, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x605;
  if (kk_std_core_types__is_Eq(_y_x10046_166, _ctx)) {
    _x_x605 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_cmp, (_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_function_drop(_implicit_fs_snd_fs_cmp, _ctx);
    _x_x605 = _y_x10046_166; /*order*/
  }
  return kk_std_core_types__order_box(_x_x605, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple2_fs_cmp(kk_std_core_types__tuple2 _pat_x60__21, kk_std_core_types__tuple2 _pat_x60__38, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_context_t* _ctx) { /* forall<a,b,e> ((a, b), (a, b), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order) -> e order */ 
  {
    kk_box_t x1 = _pat_x60__21.fst;
    kk_box_t y1 = _pat_x60__21.snd;
    {
      kk_box_t x2 = _pat_x60__38.fst;
      kk_box_t y2 = _pat_x60__38.snd;
      kk_std_core_types__order x_10329 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs_cmp, (_implicit_fs_fst_fs_cmp, x1, x2, _ctx), _ctx); /*order*/;
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x603 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs_new_cmp_fun604(_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx); /*2419*/
        return kk_std_core_types__order_unbox(_x_x603, KK_OWNED, _ctx);
      }
      if (kk_std_core_types__is_Eq(x_10329, _ctx)) {
        return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_cmp, (_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx);
      }
      {
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_function_drop(_implicit_fs_snd_fs_cmp, _ctx);
        return x_10329;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607(kk_function_t _fself, kk_box_t _b_x168, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__new_mlift_cmp_10147_fun607(kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607, kk_context());
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607(kk_function_t _fself, kk_box_t _b_x168, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__mlift_cmp_10147_fun607__t*, _fself, _ctx);
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2049, 2049) -> 2050 order */
  kk_box_t z1 = _self->z1; /* 2049 */
  kk_box_t z2 = _self->z2; /* 2049 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _x_x608;
  kk_std_core_types__order _y_x10052_170 = kk_std_core_types__order_unbox(_b_x168, KK_OWNED, _ctx); /*order*/;
  if (kk_std_core_types__is_Eq(_y_x10052_170, _ctx)) {
    _x_x608 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_cmp, (_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    _x_x608 = _y_x10052_170; /*order*/
  }
  return kk_std_core_types__order_box(_x_x608, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple3_fs__mlift_cmp_10147(kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10051, kk_context_t* _ctx) { /* forall<a,b,e> (?snd/cmp : (a, a) -> e order, ?thd/cmp : (b, b) -> e order, y1 : a, y2 : a, z1 : b, z2 : b, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10051, _ctx)) {
    kk_std_core_types__order x_10336 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_cmp, (_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx); /*order*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x606 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__new_mlift_cmp_10147_fun607(_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx); /*2419*/
      return kk_std_core_types__order_unbox(_x_x606, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__order _y_x10052_171 = x_10336; /*order*/;
      if (kk_std_core_types__is_Eq(_y_x10052_171, _ctx)) {
        return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_cmp, (_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx);
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
        return _y_x10052_171;
      }
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_snd_fs_cmp, _ctx);
    return _y_x10051;
  }
}
 
// Order on triples


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_cmp_fun612__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_snd_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t y1;
  kk_box_t y2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_cmp_fun612(kk_function_t _fself, kk_box_t _b_x173, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_cmp_fun612(kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_cmp_fun612__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_cmp_fun612__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_cmp_fun612, kk_context());
  _self->_implicit_fs_snd_fs_cmp = _implicit_fs_snd_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->y1 = y1;
  _self->y2 = y2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_cmp_fun612(kk_function_t _fself, kk_box_t _b_x173, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_cmp_fun612__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_cmp_fun612__t*, _fself, _ctx);
  kk_function_t _implicit_fs_snd_fs_cmp = _self->_implicit_fs_snd_fs_cmp; /* (2048, 2048) -> 2050 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2049, 2049) -> 2050 order */
  kk_box_t y1 = _self->y1; /* 2048 */
  kk_box_t y2 = _self->y2; /* 2048 */
  kk_box_t z1 = _self->z1; /* 2049 */
  kk_box_t z2 = _self->z2; /* 2049 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10051_178 = kk_std_core_types__order_unbox(_b_x173, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x613 = kk_std_core_tuple_tuple3_fs__mlift_cmp_10147(_implicit_fs_snd_fs_cmp, _implicit_fs_thd_fs_cmp, y1, y2, z1, z2, _y_x10051_178, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x613, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_cmp_fun617__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_cmp_fun617(kk_function_t _fself, kk_box_t _b_x175, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_cmp_fun617(kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_cmp_fun617__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_cmp_fun617__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_cmp_fun617, kk_context());
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_cmp_fun617(kk_function_t _fself, kk_box_t _b_x175, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_cmp_fun617__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_cmp_fun617__t*, _fself, _ctx);
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2049, 2049) -> 2050 order */
  kk_box_t z1 = _self->z1; /* 2049 */
  kk_box_t z2 = _self->z2; /* 2049 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10052_179 = kk_std_core_types__order_unbox(_b_x175, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x618;
  if (kk_std_core_types__is_Eq(_y_x10052_179, _ctx)) {
    _x_x618 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_cmp, (_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    _x_x618 = _y_x10052_179; /*order*/
  }
  return kk_std_core_types__order_box(_x_x618, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple3_fs_cmp(kk_std_core_types__tuple3 _pat_x66__26, kk_std_core_types__tuple3 _pat_x66__48, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_context_t* _ctx) { /* forall<a,b,c,e> ((a, b, c), (a, b, c), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order, ?thd/cmp : (c, c) -> e order) -> e order */ 
  {
    kk_box_t x1 = _pat_x66__26.fst;
    kk_box_t y1 = _pat_x66__26.snd;
    kk_box_t z1 = _pat_x66__26.thd;
    {
      kk_box_t x2 = _pat_x66__48.fst;
      kk_box_t y2 = _pat_x66__48.snd;
      kk_box_t z2 = _pat_x66__48.thd;
      kk_std_core_types__order x_10342;
      kk_function_t _x_x609 = kk_function_dup(_implicit_fs_fst_fs_cmp, _ctx); /*(2047, 2047) -> 2050 order*/
      x_10342 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x609, (_x_x609, x1, x2, _ctx), _ctx); /*order*/
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x610;
        kk_function_t _x_x611;
        kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);
        kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);
        _x_x611 = kk_std_core_tuple_tuple3_fs_new_cmp_fun612(_implicit_fs_snd_fs_cmp, _implicit_fs_thd_fs_cmp, y1, y2, z1, z2, _ctx); /*(2418) -> 2420 2419*/
        _x_x610 = kk_std_core_hnd_yield_extend(_x_x611, _ctx); /*2419*/
        return kk_std_core_types__order_unbox(_x_x610, KK_OWNED, _ctx);
      }
      if (kk_std_core_types__is_Eq(x_10342, _ctx)) {
        kk_std_core_types__order x_0_10345;
        kk_function_t _x_x614 = kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx); /*(2048, 2048) -> 2050 order*/
        x_0_10345 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x614, (_x_x614, y1, y2, _ctx), _ctx); /*order*/
        if (kk_yielding(kk_context())) {
          kk_box_t _x_x615;
          kk_function_t _x_x616;
          kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);
          _x_x616 = kk_std_core_tuple_tuple3_fs_new_cmp_fun617(_implicit_fs_thd_fs_cmp, z1, z2, _ctx); /*(2418) -> 2420 2419*/
          _x_x615 = kk_std_core_hnd_yield_extend(_x_x616, _ctx); /*2419*/
          return kk_std_core_types__order_unbox(_x_x615, KK_OWNED, _ctx);
        }
        if (kk_std_core_types__is_Eq(x_0_10345, _ctx)) {
          kk_function_t _x_x619 = kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx); /*(2049, 2049) -> 2050 order*/
          return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x619, (_x_x619, z1, z2, _ctx), _ctx);
        }
        {
          kk_box_drop(z2, _ctx);
          kk_box_drop(z1, _ctx);
          return x_0_10345;
        }
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        return x_10342;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621(kk_function_t _fself, kk_box_t _b_x181, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_cmp_10149_fun621(kk_function_t _implicit_fs_field4_fs_cmp, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621(kk_function_t _fself, kk_box_t _b_x181, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10149_fun621__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2132, 2132) -> 2133 order */
  kk_box_t w1 = _self->w1; /* 2132 */
  kk_box_t w2 = _self->w2; /* 2132 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _x_x622;
  kk_std_core_types__order _y_x10060_183 = kk_std_core_types__order_unbox(_b_x181, KK_OWNED, _ctx); /*order*/;
  if (kk_std_core_types__is_Eq(_y_x10060_183, _ctx)) {
    _x_x622 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_cmp, (_implicit_fs_field4_fs_cmp, w1, w2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    _x_x622 = _y_x10060_183; /*order*/
  }
  return kk_std_core_types__order_box(_x_x622, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple4_fs__mlift_cmp_10149(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10059, kk_context_t* _ctx) { /* forall<a,b,e> (?field4/cmp : (b, b) -> e order, ?thd/cmp : (a, a) -> e order, w1 : b, w2 : b, z1 : a, z2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10059, _ctx)) {
    kk_std_core_types__order x_10352 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_cmp, (_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx); /*order*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x620 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_cmp_10149_fun621(_implicit_fs_field4_fs_cmp, w1, w2, _ctx), _ctx); /*2419*/
      return kk_std_core_types__order_unbox(_x_x620, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__order _y_x10060_184 = x_10352; /*order*/;
      if (kk_std_core_types__is_Eq(_y_x10060_184, _ctx)) {
        return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_cmp, (_implicit_fs_field4_fs_cmp, w1, w2, _ctx), _ctx);
      }
      {
        kk_box_drop(w2, _ctx);
        kk_box_drop(w1, _ctx);
        kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
        return _y_x10060_184;
      }
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    return _y_x10059;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624(kk_function_t _fself, kk_box_t _b_x186, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_cmp_10150_fun624(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624(kk_function_t _fself, kk_box_t _b_x186, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_cmp_10150_fun624__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2132, 2132) -> 2133 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2131, 2131) -> 2133 order */
  kk_box_t w1 = _self->w1; /* 2132 */
  kk_box_t w2 = _self->w2; /* 2132 */
  kk_box_t z1 = _self->z1; /* 2131 */
  kk_box_t z2 = _self->z2; /* 2131 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10059_188 = kk_std_core_types__order_unbox(_b_x186, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x625 = kk_std_core_tuple_tuple4_fs__mlift_cmp_10149(_implicit_fs_field4_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, z1, z2, _y_x10059_188, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x625, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple4_fs__mlift_cmp_10150(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10058, kk_context_t* _ctx) { /* forall<a,b,c,e> (?field4/cmp : (c, c) -> e order, ?snd/cmp : (a, a) -> e order, ?thd/cmp : (b, b) -> e order, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10058, _ctx)) {
    kk_std_core_types__order x_10358 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_cmp, (_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx); /*order*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x623 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_cmp_10150_fun624(_implicit_fs_field4_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, z1, z2, _ctx), _ctx); /*2419*/
      return kk_std_core_types__order_unbox(_x_x623, KK_OWNED, _ctx);
    }
    {
      return kk_std_core_tuple_tuple4_fs__mlift_cmp_10149(_implicit_fs_field4_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, z1, z2, x_10358, _ctx);
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_snd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    return _y_x10058;
  }
}
 
// Order on quadruples


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_cmp_fun631__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_snd_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t y1;
  kk_box_t y2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_cmp_fun631(kk_function_t _fself, kk_box_t _b_x190, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_cmp_fun631(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_cmp_fun631__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_cmp_fun631__t, 10, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_cmp_fun631, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_snd_fs_cmp = _implicit_fs_snd_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->y1 = y1;
  _self->y2 = y2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_cmp_fun631(kk_function_t _fself, kk_box_t _b_x190, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_cmp_fun631__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_cmp_fun631__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2132, 2132) -> 2133 order */
  kk_function_t _implicit_fs_snd_fs_cmp = _self->_implicit_fs_snd_fs_cmp; /* (2130, 2130) -> 2133 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2131, 2131) -> 2133 order */
  kk_box_t w1 = _self->w1; /* 2132 */
  kk_box_t w2 = _self->w2; /* 2132 */
  kk_box_t y1 = _self->y1; /* 2130 */
  kk_box_t y2 = _self->y2; /* 2130 */
  kk_box_t z1 = _self->z1; /* 2131 */
  kk_box_t z2 = _self->z2; /* 2131 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10058_198 = kk_std_core_types__order_unbox(_b_x190, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x632 = kk_std_core_tuple_tuple4_fs__mlift_cmp_10150(_implicit_fs_field4_fs_cmp, _implicit_fs_snd_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, y1, y2, z1, z2, _y_x10058_198, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x632, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_cmp_fun636__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_cmp_fun636(kk_function_t _fself, kk_box_t _b_x192, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_cmp_fun636(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_cmp_fun636__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_cmp_fun636__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_cmp_fun636, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_cmp_fun636(kk_function_t _fself, kk_box_t _b_x192, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_cmp_fun636__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_cmp_fun636__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2132, 2132) -> 2133 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2131, 2131) -> 2133 order */
  kk_box_t w1 = _self->w1; /* 2132 */
  kk_box_t w2 = _self->w2; /* 2132 */
  kk_box_t z1 = _self->z1; /* 2131 */
  kk_box_t z2 = _self->z2; /* 2131 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10059_199 = kk_std_core_types__order_unbox(_b_x192, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x637 = kk_std_core_tuple_tuple4_fs__mlift_cmp_10149(_implicit_fs_field4_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, z1, z2, _y_x10059_199, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x637, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_cmp_fun641__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_cmp_fun641(kk_function_t _fself, kk_box_t _b_x194, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_cmp_fun641(kk_function_t _implicit_fs_field4_fs_cmp, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_cmp_fun641__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_cmp_fun641__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_cmp_fun641, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_cmp_fun641(kk_function_t _fself, kk_box_t _b_x194, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_cmp_fun641__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_cmp_fun641__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2132, 2132) -> 2133 order */
  kk_box_t w1 = _self->w1; /* 2132 */
  kk_box_t w2 = _self->w2; /* 2132 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10060_200 = kk_std_core_types__order_unbox(_b_x194, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x642;
  if (kk_std_core_types__is_Eq(_y_x10060_200, _ctx)) {
    _x_x642 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_cmp, (_implicit_fs_field4_fs_cmp, w1, w2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    _x_x642 = _y_x10060_200; /*order*/
  }
  return kk_std_core_types__order_box(_x_x642, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple4_fs_cmp(kk_std_core_types__tuple4 _pat_x74__26, kk_std_core_types__tuple4 _pat_x74__53, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_function_t _implicit_fs_field4_fs_cmp, kk_context_t* _ctx) { /* forall<a,b,c,d,e> ((a, b, c, d), (a, b, c, d), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order, ?thd/cmp : (c, c) -> e order, ?field4/cmp : (d, d) -> e order) -> e order */ 
  {
    struct kk_std_core_types_Tuple4* _con_x626 = kk_std_core_types__as_Tuple4(_pat_x74__26, _ctx);
    kk_box_t x1 = _con_x626->fst;
    kk_box_t y1 = _con_x626->snd;
    kk_box_t z1 = _con_x626->thd;
    kk_box_t w1 = _con_x626->field4;
    if kk_likely(kk_datatype_ptr_is_unique(_pat_x74__26, _ctx)) {
      kk_datatype_ptr_free(_pat_x74__26, _ctx);
    }
    else {
      kk_box_dup(w1, _ctx);
      kk_box_dup(x1, _ctx);
      kk_box_dup(y1, _ctx);
      kk_box_dup(z1, _ctx);
      kk_datatype_ptr_decref(_pat_x74__26, _ctx);
    }
    {
      struct kk_std_core_types_Tuple4* _con_x627 = kk_std_core_types__as_Tuple4(_pat_x74__53, _ctx);
      kk_box_t x2 = _con_x627->fst;
      kk_box_t y2 = _con_x627->snd;
      kk_box_t z2 = _con_x627->thd;
      kk_box_t w2 = _con_x627->field4;
      if kk_likely(kk_datatype_ptr_is_unique(_pat_x74__53, _ctx)) {
        kk_datatype_ptr_free(_pat_x74__53, _ctx);
      }
      else {
        kk_box_dup(w2, _ctx);
        kk_box_dup(x2, _ctx);
        kk_box_dup(y2, _ctx);
        kk_box_dup(z2, _ctx);
        kk_datatype_ptr_decref(_pat_x74__53, _ctx);
      }
      kk_std_core_types__order x_10360;
      kk_function_t _x_x628 = kk_function_dup(_implicit_fs_fst_fs_cmp, _ctx); /*(2129, 2129) -> 2133 order*/
      x_10360 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x628, (_x_x628, x1, x2, _ctx), _ctx); /*order*/
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x629;
        kk_function_t _x_x630;
        kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);
        kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);
        kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);
        _x_x630 = kk_std_core_tuple_tuple4_fs_new_cmp_fun631(_implicit_fs_field4_fs_cmp, _implicit_fs_snd_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, y1, y2, z1, z2, _ctx); /*(2418) -> 2420 2419*/
        _x_x629 = kk_std_core_hnd_yield_extend(_x_x630, _ctx); /*2419*/
        return kk_std_core_types__order_unbox(_x_x629, KK_OWNED, _ctx);
      }
      if (kk_std_core_types__is_Eq(x_10360, _ctx)) {
        kk_std_core_types__order x_0_10363;
        kk_function_t _x_x633 = kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx); /*(2130, 2130) -> 2133 order*/
        x_0_10363 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x633, (_x_x633, y1, y2, _ctx), _ctx); /*order*/
        if (kk_yielding(kk_context())) {
          kk_box_t _x_x634;
          kk_function_t _x_x635;
          kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);
          kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);
          _x_x635 = kk_std_core_tuple_tuple4_fs_new_cmp_fun636(_implicit_fs_field4_fs_cmp, _implicit_fs_thd_fs_cmp, w1, w2, z1, z2, _ctx); /*(2418) -> 2420 2419*/
          _x_x634 = kk_std_core_hnd_yield_extend(_x_x635, _ctx); /*2419*/
          return kk_std_core_types__order_unbox(_x_x634, KK_OWNED, _ctx);
        }
        if (kk_std_core_types__is_Eq(x_0_10363, _ctx)) {
          kk_std_core_types__order x_1_10366;
          kk_function_t _x_x638 = kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx); /*(2131, 2131) -> 2133 order*/
          x_1_10366 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x638, (_x_x638, z1, z2, _ctx), _ctx); /*order*/
          if (kk_yielding(kk_context())) {
            kk_box_t _x_x639;
            kk_function_t _x_x640;
            kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);
            _x_x640 = kk_std_core_tuple_tuple4_fs_new_cmp_fun641(_implicit_fs_field4_fs_cmp, w1, w2, _ctx); /*(2418) -> 2420 2419*/
            _x_x639 = kk_std_core_hnd_yield_extend(_x_x640, _ctx); /*2419*/
            return kk_std_core_types__order_unbox(_x_x639, KK_OWNED, _ctx);
          }
          if (kk_std_core_types__is_Eq(x_1_10366, _ctx)) {
            kk_function_t _x_x643 = kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx); /*(2132, 2132) -> 2133 order*/
            return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x643, (_x_x643, w1, w2, _ctx), _ctx);
          }
          {
            kk_box_drop(w2, _ctx);
            kk_box_drop(w1, _ctx);
            return x_1_10366;
          }
        }
        {
          kk_box_drop(z2, _ctx);
          kk_box_drop(z1, _ctx);
          kk_box_drop(w2, _ctx);
          kk_box_drop(w1, _ctx);
          return x_0_10363;
        }
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_box_drop(w2, _ctx);
        kk_box_drop(w1, _ctx);
        return x_10360;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645(kk_function_t _fself, kk_box_t _b_x202, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_cmp_10152_fun645(kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645, kk_context());
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645(kk_function_t _fself, kk_box_t _b_x202, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10152_fun645__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _x_x646;
  kk_std_core_types__order _y_x10070_204 = kk_std_core_types__order_unbox(_b_x202, KK_OWNED, _ctx); /*order*/;
  if (kk_std_core_types__is_Eq(_y_x10070_204, _ctx)) {
    _x_x646 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs_cmp, (_implicit_fs_field5_fs_cmp, v1, v2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
    _x_x646 = _y_x10070_204; /*order*/
  }
  return kk_std_core_types__order_box(_x_x646, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10152(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_std_core_types__order _y_x10069, kk_context_t* _ctx) { /* forall<a,e,b> (?field4/cmp : (a, a) -> e order, ?field5/cmp : (b, b) -> e order, v1 : b, v2 : b, w1 : a, w2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10069, _ctx)) {
    kk_std_core_types__order x_10373 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_cmp, (_implicit_fs_field4_fs_cmp, w1, w2, _ctx), _ctx); /*order*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x644 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_cmp_10152_fun645(_implicit_fs_field5_fs_cmp, v1, v2, _ctx), _ctx); /*2419*/
      return kk_std_core_types__order_unbox(_x_x644, KK_OWNED, _ctx);
    }
    {
      kk_std_core_types__order _y_x10070_205 = x_10373; /*order*/;
      if (kk_std_core_types__is_Eq(_y_x10070_205, _ctx)) {
        return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs_cmp, (_implicit_fs_field5_fs_cmp, v1, v2, _ctx), _ctx);
      }
      {
        kk_box_drop(v2, _ctx);
        kk_box_drop(v1, _ctx);
        kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
        return _y_x10070_205;
      }
    }
  }
  {
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    return _y_x10069;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648(kk_function_t _fself, kk_box_t _b_x207, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_cmp_10153_fun648(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648(kk_function_t _fself, kk_box_t _b_x207, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10153_fun648__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2232, 2232) -> 2233 order */
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_box_t w1 = _self->w1; /* 2232 */
  kk_box_t w2 = _self->w2; /* 2232 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10069_209 = kk_std_core_types__order_unbox(_b_x207, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x649 = kk_std_core_tuple_tuple5_fs__mlift_cmp_10152(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, v1, v2, w1, w2, _y_x10069_209, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x649, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10153(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10068, kk_context_t* _ctx) { /* forall<a,b,e,c> (?field4/cmp : (b, b) -> e order, ?field5/cmp : (c, c) -> e order, ?thd/cmp : (a, a) -> e order, v1 : c, v2 : c, w1 : b, w2 : b, z1 : a, z2 : a, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10068, _ctx)) {
    kk_std_core_types__order x_10379 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_cmp, (_implicit_fs_thd_fs_cmp, z1, z2, _ctx), _ctx); /*order*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x647 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_cmp_10153_fun648(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, v1, v2, w1, w2, _ctx), _ctx); /*2419*/
      return kk_std_core_types__order_unbox(_x_x647, KK_OWNED, _ctx);
    }
    {
      return kk_std_core_tuple_tuple5_fs__mlift_cmp_10152(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, v1, v2, w1, w2, x_10379, _ctx);
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    return _y_x10068;
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651(kk_function_t _fself, kk_box_t _b_x211, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_cmp_10154_fun651(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651__t, 10, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651(kk_function_t _fself, kk_box_t _b_x211, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_cmp_10154_fun651__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2232, 2232) -> 2233 order */
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2231, 2231) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_box_t w1 = _self->w1; /* 2232 */
  kk_box_t w2 = _self->w2; /* 2232 */
  kk_box_t z1 = _self->z1; /* 2231 */
  kk_box_t z2 = _self->z2; /* 2231 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10068_213 = kk_std_core_types__order_unbox(_b_x211, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x652 = kk_std_core_tuple_tuple5_fs__mlift_cmp_10153(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, z1, z2, _y_x10068_213, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x652, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple5_fs__mlift_cmp_10154(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_std_core_types__order _y_x10067, kk_context_t* _ctx) { /* forall<a,b,c,e,d> (?field4/cmp : (c, c) -> e order, ?field5/cmp : (d, d) -> e order, ?snd/cmp : (a, a) -> e order, ?thd/cmp : (b, b) -> e order, v1 : d, v2 : d, w1 : c, w2 : c, y1 : a, y2 : a, z1 : b, z2 : b, order) -> e order */ 
  if (kk_std_core_types__is_Eq(_y_x10067, _ctx)) {
    kk_std_core_types__order x_10381 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_cmp, (_implicit_fs_snd_fs_cmp, y1, y2, _ctx), _ctx); /*order*/;
    if (kk_yielding(kk_context())) {
      kk_box_t _x_x650 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_cmp_10154_fun651(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, z1, z2, _ctx), _ctx); /*2419*/
      return kk_std_core_types__order_unbox(_x_x650, KK_OWNED, _ctx);
    }
    {
      return kk_std_core_tuple_tuple5_fs__mlift_cmp_10153(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, z1, z2, x_10381, _ctx);
    }
  }
  {
    kk_box_drop(z2, _ctx);
    kk_box_drop(z1, _ctx);
    kk_box_drop(y2, _ctx);
    kk_box_drop(y1, _ctx);
    kk_box_drop(w2, _ctx);
    kk_box_drop(w1, _ctx);
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_thd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_snd_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
    kk_function_drop(_implicit_fs_field4_fs_cmp, _ctx);
    return _y_x10067;
  }
}
 
// Order on quintuples


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_cmp_fun658__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_function_t _implicit_fs_snd_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t y1;
  kk_box_t y2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun658(kk_function_t _fself, kk_box_t _b_x215, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_cmp_fun658(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t y1, kk_box_t y2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun658__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun658__t, 13, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_cmp_fun658, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->_implicit_fs_snd_fs_cmp = _implicit_fs_snd_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->y1 = y1;
  _self->y2 = y2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun658(kk_function_t _fself, kk_box_t _b_x215, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun658__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun658__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2232, 2232) -> 2233 order */
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_function_t _implicit_fs_snd_fs_cmp = _self->_implicit_fs_snd_fs_cmp; /* (2230, 2230) -> 2233 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2231, 2231) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_box_t w1 = _self->w1; /* 2232 */
  kk_box_t w2 = _self->w2; /* 2232 */
  kk_box_t y1 = _self->y1; /* 2230 */
  kk_box_t y2 = _self->y2; /* 2230 */
  kk_box_t z1 = _self->z1; /* 2231 */
  kk_box_t z2 = _self->z2; /* 2231 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(y1, _ctx);kk_box_dup(y2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10067_226 = kk_std_core_types__order_unbox(_b_x215, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x659 = kk_std_core_tuple_tuple5_fs__mlift_cmp_10154(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_snd_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, y1, y2, z1, z2, _y_x10067_226, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x659, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_cmp_fun663__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_function_t _implicit_fs_thd_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
  kk_box_t z1;
  kk_box_t z2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun663(kk_function_t _fself, kk_box_t _b_x217, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_cmp_fun663(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_box_t z1, kk_box_t z2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun663__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun663__t, 10, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_cmp_fun663, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->_implicit_fs_thd_fs_cmp = _implicit_fs_thd_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  _self->z1 = z1;
  _self->z2 = z2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun663(kk_function_t _fself, kk_box_t _b_x217, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun663__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun663__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2232, 2232) -> 2233 order */
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_function_t _implicit_fs_thd_fs_cmp = _self->_implicit_fs_thd_fs_cmp; /* (2231, 2231) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_box_t w1 = _self->w1; /* 2232 */
  kk_box_t w2 = _self->w2; /* 2232 */
  kk_box_t z1 = _self->z1; /* 2231 */
  kk_box_t z2 = _self->z2; /* 2231 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);kk_box_dup(z1, _ctx);kk_box_dup(z2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10068_227 = kk_std_core_types__order_unbox(_b_x217, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x664 = kk_std_core_tuple_tuple5_fs__mlift_cmp_10153(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, z1, z2, _y_x10068_227, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x664, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_cmp_fun668__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_cmp;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
  kk_box_t w1;
  kk_box_t w2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun668(kk_function_t _fself, kk_box_t _b_x219, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_cmp_fun668(kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_box_t w1, kk_box_t w2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun668__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun668__t, 7, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_cmp_fun668, kk_context());
  _self->_implicit_fs_field4_fs_cmp = _implicit_fs_field4_fs_cmp;
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  _self->w1 = w1;
  _self->w2 = w2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun668(kk_function_t _fself, kk_box_t _b_x219, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun668__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun668__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_cmp = _self->_implicit_fs_field4_fs_cmp; /* (2232, 2232) -> 2233 order */
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_box_t w1 = _self->w1; /* 2232 */
  kk_box_t w2 = _self->w2; /* 2232 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);kk_box_dup(w1, _ctx);kk_box_dup(w2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10069_228 = kk_std_core_types__order_unbox(_b_x219, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x669 = kk_std_core_tuple_tuple5_fs__mlift_cmp_10152(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, v1, v2, w1, w2, _y_x10069_228, _ctx); /*order*/
  return kk_std_core_types__order_box(_x_x669, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_cmp_fun673__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field5_fs_cmp;
  kk_box_t v1;
  kk_box_t v2;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun673(kk_function_t _fself, kk_box_t _b_x221, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_cmp_fun673(kk_function_t _implicit_fs_field5_fs_cmp, kk_box_t v1, kk_box_t v2, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun673__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun673__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_cmp_fun673, kk_context());
  _self->_implicit_fs_field5_fs_cmp = _implicit_fs_field5_fs_cmp;
  _self->v1 = v1;
  _self->v2 = v2;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_cmp_fun673(kk_function_t _fself, kk_box_t _b_x221, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_cmp_fun673__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_cmp_fun673__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field5_fs_cmp = _self->_implicit_fs_field5_fs_cmp; /* (2234, 2234) -> 2233 order */
  kk_box_t v1 = _self->v1; /* 2234 */
  kk_box_t v2 = _self->v2; /* 2234 */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);kk_box_dup(v1, _ctx);kk_box_dup(v2, _ctx);}, {}, _ctx)
  kk_std_core_types__order _y_x10070_229 = kk_std_core_types__order_unbox(_b_x221, KK_OWNED, _ctx); /*order*/;
  kk_std_core_types__order _x_x674;
  if (kk_std_core_types__is_Eq(_y_x10070_229, _ctx)) {
    _x_x674 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs_cmp, (_implicit_fs_field5_fs_cmp, v1, v2, _ctx), _ctx); /*order*/
  }
  else {
    kk_box_drop(v2, _ctx);
    kk_box_drop(v1, _ctx);
    kk_function_drop(_implicit_fs_field5_fs_cmp, _ctx);
    _x_x674 = _y_x10070_229; /*order*/
  }
  return kk_std_core_types__order_box(_x_x674, _ctx);
}

kk_std_core_types__order kk_std_core_tuple_tuple5_fs_cmp(kk_std_core_types__tuple5 _pat_x86__26, kk_std_core_types__tuple5 _pat_x86__58, kk_function_t _implicit_fs_fst_fs_cmp, kk_function_t _implicit_fs_snd_fs_cmp, kk_function_t _implicit_fs_thd_fs_cmp, kk_function_t _implicit_fs_field4_fs_cmp, kk_function_t _implicit_fs_field5_fs_cmp, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> ((a, b, c, d, a1), (a, b, c, d, a1), ?fst/cmp : (a, a) -> e order, ?snd/cmp : (b, b) -> e order, ?thd/cmp : (c, c) -> e order, ?field4/cmp : (d, d) -> e order, ?field5/cmp : (a1, a1) -> e order) -> e order */ 
  {
    struct kk_std_core_types_Tuple5* _con_x653 = kk_std_core_types__as_Tuple5(_pat_x86__26, _ctx);
    kk_box_t x1 = _con_x653->fst;
    kk_box_t y1 = _con_x653->snd;
    kk_box_t z1 = _con_x653->thd;
    kk_box_t w1 = _con_x653->field4;
    kk_box_t v1 = _con_x653->field5;
    if kk_likely(kk_datatype_ptr_is_unique(_pat_x86__26, _ctx)) {
      kk_datatype_ptr_free(_pat_x86__26, _ctx);
    }
    else {
      kk_box_dup(v1, _ctx);
      kk_box_dup(w1, _ctx);
      kk_box_dup(x1, _ctx);
      kk_box_dup(y1, _ctx);
      kk_box_dup(z1, _ctx);
      kk_datatype_ptr_decref(_pat_x86__26, _ctx);
    }
    {
      struct kk_std_core_types_Tuple5* _con_x654 = kk_std_core_types__as_Tuple5(_pat_x86__58, _ctx);
      kk_box_t x2 = _con_x654->fst;
      kk_box_t y2 = _con_x654->snd;
      kk_box_t z2 = _con_x654->thd;
      kk_box_t w2 = _con_x654->field4;
      kk_box_t v2 = _con_x654->field5;
      if kk_likely(kk_datatype_ptr_is_unique(_pat_x86__58, _ctx)) {
        kk_datatype_ptr_free(_pat_x86__58, _ctx);
      }
      else {
        kk_box_dup(v2, _ctx);
        kk_box_dup(w2, _ctx);
        kk_box_dup(x2, _ctx);
        kk_box_dup(y2, _ctx);
        kk_box_dup(z2, _ctx);
        kk_datatype_ptr_decref(_pat_x86__58, _ctx);
      }
      kk_std_core_types__order x_10383;
      kk_function_t _x_x655 = kk_function_dup(_implicit_fs_fst_fs_cmp, _ctx); /*(2229, 2229) -> 2233 order*/
      x_10383 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x655, (_x_x655, x1, x2, _ctx), _ctx); /*order*/
      if (kk_yielding(kk_context())) {
        kk_box_t _x_x656;
        kk_function_t _x_x657;
        kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);
        kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);
        kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx);
        kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);
        _x_x657 = kk_std_core_tuple_tuple5_fs_new_cmp_fun658(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_snd_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, y1, y2, z1, z2, _ctx); /*(2418) -> 2420 2419*/
        _x_x656 = kk_std_core_hnd_yield_extend(_x_x657, _ctx); /*2419*/
        return kk_std_core_types__order_unbox(_x_x656, KK_OWNED, _ctx);
      }
      if (kk_std_core_types__is_Eq(x_10383, _ctx)) {
        kk_std_core_types__order x_0_10386;
        kk_function_t _x_x660 = kk_function_dup(_implicit_fs_snd_fs_cmp, _ctx); /*(2230, 2230) -> 2233 order*/
        x_0_10386 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x660, (_x_x660, y1, y2, _ctx), _ctx); /*order*/
        if (kk_yielding(kk_context())) {
          kk_box_t _x_x661;
          kk_function_t _x_x662;
          kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);
          kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);
          kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx);
          _x_x662 = kk_std_core_tuple_tuple5_fs_new_cmp_fun663(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, _implicit_fs_thd_fs_cmp, v1, v2, w1, w2, z1, z2, _ctx); /*(2418) -> 2420 2419*/
          _x_x661 = kk_std_core_hnd_yield_extend(_x_x662, _ctx); /*2419*/
          return kk_std_core_types__order_unbox(_x_x661, KK_OWNED, _ctx);
        }
        if (kk_std_core_types__is_Eq(x_0_10386, _ctx)) {
          kk_std_core_types__order x_1_10389;
          kk_function_t _x_x665 = kk_function_dup(_implicit_fs_thd_fs_cmp, _ctx); /*(2231, 2231) -> 2233 order*/
          x_1_10389 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x665, (_x_x665, z1, z2, _ctx), _ctx); /*order*/
          if (kk_yielding(kk_context())) {
            kk_box_t _x_x666;
            kk_function_t _x_x667;
            kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx);
            kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);
            _x_x667 = kk_std_core_tuple_tuple5_fs_new_cmp_fun668(_implicit_fs_field4_fs_cmp, _implicit_fs_field5_fs_cmp, v1, v2, w1, w2, _ctx); /*(2418) -> 2420 2419*/
            _x_x666 = kk_std_core_hnd_yield_extend(_x_x667, _ctx); /*2419*/
            return kk_std_core_types__order_unbox(_x_x666, KK_OWNED, _ctx);
          }
          if (kk_std_core_types__is_Eq(x_1_10389, _ctx)) {
            kk_std_core_types__order x_2_10392;
            kk_function_t _x_x670 = kk_function_dup(_implicit_fs_field4_fs_cmp, _ctx); /*(2232, 2232) -> 2233 order*/
            x_2_10392 = kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x670, (_x_x670, w1, w2, _ctx), _ctx); /*order*/
            if (kk_yielding(kk_context())) {
              kk_box_t _x_x671;
              kk_function_t _x_x672;
              kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx);
              _x_x672 = kk_std_core_tuple_tuple5_fs_new_cmp_fun673(_implicit_fs_field5_fs_cmp, v1, v2, _ctx); /*(2418) -> 2420 2419*/
              _x_x671 = kk_std_core_hnd_yield_extend(_x_x672, _ctx); /*2419*/
              return kk_std_core_types__order_unbox(_x_x671, KK_OWNED, _ctx);
            }
            if (kk_std_core_types__is_Eq(x_2_10392, _ctx)) {
              kk_function_t _x_x675 = kk_function_dup(_implicit_fs_field5_fs_cmp, _ctx); /*(2234, 2234) -> 2233 order*/
              return kk_function_call(kk_std_core_types__order, (kk_function_t, kk_box_t, kk_box_t, kk_context_t*), _x_x675, (_x_x675, v1, v2, _ctx), _ctx);
            }
            {
              kk_box_drop(v2, _ctx);
              kk_box_drop(v1, _ctx);
              return x_2_10392;
            }
          }
          {
            kk_box_drop(w2, _ctx);
            kk_box_drop(w1, _ctx);
            kk_box_drop(v2, _ctx);
            kk_box_drop(v1, _ctx);
            return x_1_10389;
          }
        }
        {
          kk_box_drop(z2, _ctx);
          kk_box_drop(z1, _ctx);
          kk_box_drop(w2, _ctx);
          kk_box_drop(w1, _ctx);
          kk_box_drop(v2, _ctx);
          kk_box_drop(v1, _ctx);
          return x_0_10386;
        }
      }
      {
        kk_box_drop(z2, _ctx);
        kk_box_drop(z1, _ctx);
        kk_box_drop(y2, _ctx);
        kk_box_drop(y1, _ctx);
        kk_box_drop(w2, _ctx);
        kk_box_drop(w1, _ctx);
        kk_box_drop(v2, _ctx);
        kk_box_drop(v1, _ctx);
        return x_10383;
      }
    }
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687__t {
  struct kk_function_s _base;
  kk_string_t _y_x10078;
};
static kk_string_t kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687(kk_function_t _fself, kk_string_t _y_x10079, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs__new_mlift_show_10156_fun687(kk_string_t _y_x10078, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687, kk_context());
  _self->_y_x10078 = _y_x10078;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_string_t kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687(kk_function_t _fself, kk_string_t _y_x10079, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun687__t*, _fself, _ctx);
  kk_string_t _y_x10078 = _self->_y_x10078; /* string */
  kk_drop_match(_self, {kk_string_dup(_y_x10078, _ctx);}, {}, _ctx)
  kk_string_t _x_x688;
  kk_define_string_literal(, _s_x689, 1, "(", _ctx)
  _x_x688 = kk_string_dup(_s_x689, _ctx); /*string*/
  kk_string_t _x_x690;
  kk_string_t _x_x691;
  kk_string_t _x_x692;
  kk_define_string_literal(, _s_x693, 1, ",", _ctx)
  _x_x692 = kk_string_dup(_s_x693, _ctx); /*string*/
  kk_string_t _x_x694;
  kk_string_t _x_x695;
  kk_define_string_literal(, _s_x696, 1, ")", _ctx)
  _x_x695 = kk_string_dup(_s_x696, _ctx); /*string*/
  _x_x694 = kk_std_core_types__lp__plus__plus__rp_(_y_x10079, _x_x695, _ctx); /*string*/
  _x_x691 = kk_std_core_types__lp__plus__plus__rp_(_x_x692, _x_x694, _ctx); /*string*/
  _x_x690 = kk_std_core_types__lp__plus__plus__rp_(_y_x10078, _x_x691, _ctx); /*string*/
  return kk_std_core_types__lp__plus__plus__rp_(_x_x688, _x_x690, _ctx);
}


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698__t {
  struct kk_function_s _base;
  kk_function_t next_10400;
};
static kk_box_t kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698(kk_function_t _fself, kk_box_t _b_x233, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs__new_mlift_show_10156_fun698(kk_function_t next_10400, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698, kk_context());
  _self->next_10400 = next_10400;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698(kk_function_t _fself, kk_box_t _b_x233, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs__mlift_show_10156_fun698__t*, _fself, _ctx);
  kk_function_t next_10400 = _self->next_10400; /* (string) -> 2507 string */
  kk_drop_match(_self, {kk_function_dup(next_10400, _ctx);}, {}, _ctx)
  kk_string_t _x_x699;
  kk_string_t _x_x700 = kk_string_unbox(_b_x233); /*string*/
  _x_x699 = kk_function_call(kk_string_t, (kk_function_t, kk_string_t, kk_context_t*), next_10400, (next_10400, _x_x700, _ctx), _ctx); /*string*/
  return kk_string_box(_x_x699);
}

kk_string_t kk_std_core_tuple_tuple2_fs__mlift_show_10156(kk_function_t _implicit_fs_snd_fs_show, kk_std_core_types__tuple2 x, kk_string_t _y_x10078, kk_context_t* _ctx) { /* forall<a,b,e> (?snd/show : (b) -> e string, x : (a, b), string) -> e string */ 
  kk_string_t x_0_10399;
  kk_box_t _x_x686;
  {
    kk_box_t _x_0 = x.snd;
    kk_box_dup(_x_0, _ctx);
    kk_std_core_types__tuple2_drop(x, _ctx);
    _x_x686 = _x_0; /*2506*/
  }
  x_0_10399 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x686, _ctx), _ctx); /*string*/
  kk_function_t next_10400 = kk_std_core_tuple_tuple2_fs__new_mlift_show_10156_fun687(_y_x10078, _ctx); /*(string) -> 2507 string*/;
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10399, _ctx);
    kk_box_t _x_x697 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs__new_mlift_show_10156_fun698(next_10400, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x697);
  }
  {
    return kk_function_call(kk_string_t, (kk_function_t, kk_string_t, kk_context_t*), next_10400, (next_10400, x_0_10399, _ctx), _ctx);
  }
}
 
// Show a tuple


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs_show_fun703__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_snd_fs_show;
  kk_std_core_types__tuple2 x;
};
static kk_box_t kk_std_core_tuple_tuple2_fs_show_fun703(kk_function_t _fself, kk_box_t _b_x236, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs_new_show_fun703(kk_function_t _implicit_fs_snd_fs_show, kk_std_core_types__tuple2 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_show_fun703__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs_show_fun703__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs_show_fun703, kk_context());
  _self->_implicit_fs_snd_fs_show = _implicit_fs_snd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs_show_fun703(kk_function_t _fself, kk_box_t _b_x236, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_show_fun703__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs_show_fun703__t*, _fself, _ctx);
  kk_function_t _implicit_fs_snd_fs_show = _self->_implicit_fs_snd_fs_show; /* (2506) -> 2507 string */
  kk_std_core_types__tuple2 x = _self->x; /* (2505, 2506) */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_snd_fs_show, _ctx);kk_std_core_types__tuple2_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10078_241 = kk_string_unbox(_b_x236); /*string*/;
  kk_string_t _x_x704 = kk_std_core_tuple_tuple2_fs__mlift_show_10156(_implicit_fs_snd_fs_show, x, _y_x10078_241, _ctx); /*string*/
  return kk_string_box(_x_x704);
}


// lift anonymous function
struct kk_std_core_tuple_tuple2_fs_show_fun707__t {
  struct kk_function_s _base;
  kk_string_t x_0_10403;
};
static kk_box_t kk_std_core_tuple_tuple2_fs_show_fun707(kk_function_t _fself, kk_box_t _b_x238, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple2_fs_new_show_fun707(kk_string_t x_0_10403, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_show_fun707__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple2_fs_show_fun707__t, 2, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple2_fs_show_fun707, kk_context());
  _self->x_0_10403 = x_0_10403;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple2_fs_show_fun707(kk_function_t _fself, kk_box_t _b_x238, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple2_fs_show_fun707__t* _self = kk_function_as(struct kk_std_core_tuple_tuple2_fs_show_fun707__t*, _fself, _ctx);
  kk_string_t x_0_10403 = _self->x_0_10403; /* string */
  kk_drop_match(_self, {kk_string_dup(x_0_10403, _ctx);}, {}, _ctx)
  kk_string_t _y_x10079_242 = kk_string_unbox(_b_x238); /*string*/;
  kk_string_t _x_x708;
  kk_string_t _x_x709;
  kk_define_string_literal(, _s_x710, 1, "(", _ctx)
  _x_x709 = kk_string_dup(_s_x710, _ctx); /*string*/
  kk_string_t _x_x711;
  kk_string_t _x_x712;
  kk_string_t _x_x713;
  kk_define_string_literal(, _s_x714, 1, ",", _ctx)
  _x_x713 = kk_string_dup(_s_x714, _ctx); /*string*/
  kk_string_t _x_x715;
  kk_string_t _x_x716;
  kk_define_string_literal(, _s_x717, 1, ")", _ctx)
  _x_x716 = kk_string_dup(_s_x717, _ctx); /*string*/
  _x_x715 = kk_std_core_types__lp__plus__plus__rp_(_y_x10079_242, _x_x716, _ctx); /*string*/
  _x_x712 = kk_std_core_types__lp__plus__plus__rp_(_x_x713, _x_x715, _ctx); /*string*/
  _x_x711 = kk_std_core_types__lp__plus__plus__rp_(x_0_10403, _x_x712, _ctx); /*string*/
  _x_x708 = kk_std_core_types__lp__plus__plus__rp_(_x_x709, _x_x711, _ctx); /*string*/
  return kk_string_box(_x_x708);
}

kk_string_t kk_std_core_tuple_tuple2_fs_show(kk_std_core_types__tuple2 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_context_t* _ctx) { /* forall<a,b,e> (x : (a, b), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string) -> e string */ 
  kk_string_t x_0_10403;
  kk_box_t _x_x701;
  {
    kk_box_t _x = x.fst;
    kk_box_dup(_x, _ctx);
    _x_x701 = _x; /*2505*/
  }
  x_0_10403 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs_show, (_implicit_fs_fst_fs_show, _x_x701, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10403, _ctx);
    kk_box_t _x_x702 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs_new_show_fun703(_implicit_fs_snd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x702);
  }
  {
    kk_string_t x_1_10406;
    kk_box_t _x_x705;
    {
      kk_box_t _x_0 = x.snd;
      kk_box_dup(_x_0, _ctx);
      kk_std_core_types__tuple2_drop(x, _ctx);
      _x_x705 = _x_0; /*2506*/
    }
    x_1_10406 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x705, _ctx), _ctx); /*string*/
    if (kk_yielding(kk_context())) {
      kk_string_drop(x_1_10406, _ctx);
      kk_box_t _x_x706 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple2_fs_new_show_fun707(x_0_10403, _ctx), _ctx); /*2419*/
      return kk_string_unbox(_x_x706);
    }
    {
      kk_string_t _x_x718;
      kk_define_string_literal(, _s_x719, 1, "(", _ctx)
      _x_x718 = kk_string_dup(_s_x719, _ctx); /*string*/
      kk_string_t _x_x720;
      kk_string_t _x_x721;
      kk_string_t _x_x722;
      kk_define_string_literal(, _s_x723, 1, ",", _ctx)
      _x_x722 = kk_string_dup(_s_x723, _ctx); /*string*/
      kk_string_t _x_x724;
      kk_string_t _x_x725;
      kk_define_string_literal(, _s_x726, 1, ")", _ctx)
      _x_x725 = kk_string_dup(_s_x726, _ctx); /*string*/
      _x_x724 = kk_std_core_types__lp__plus__plus__rp_(x_1_10406, _x_x725, _ctx); /*string*/
      _x_x721 = kk_std_core_types__lp__plus__plus__rp_(_x_x722, _x_x724, _ctx); /*string*/
      _x_x720 = kk_std_core_types__lp__plus__plus__rp_(x_0_10403, _x_x721, _ctx); /*string*/
      return kk_std_core_types__lp__plus__plus__rp_(_x_x718, _x_x720, _ctx);
    }
  }
}
 
// monadic lift

kk_string_t kk_std_core_tuple_tuple3_fs__mlift_show_10157(kk_string_t _y_x10080, kk_string_t _y_x10081, kk_string_t _y_x10082, kk_context_t* _ctx) { /* forall<e> (string, string, string) -> e string */ 
  kk_string_t _x_x727;
  kk_define_string_literal(, _s_x728, 1, "(", _ctx)
  _x_x727 = kk_string_dup(_s_x728, _ctx); /*string*/
  kk_string_t _x_x729;
  kk_string_t _x_x730;
  kk_string_t _x_x731;
  kk_define_string_literal(, _s_x732, 1, ",", _ctx)
  _x_x731 = kk_string_dup(_s_x732, _ctx); /*string*/
  kk_string_t _x_x733;
  kk_string_t _x_x734;
  kk_string_t _x_x735;
  kk_define_string_literal(, _s_x736, 1, ",", _ctx)
  _x_x735 = kk_string_dup(_s_x736, _ctx); /*string*/
  kk_string_t _x_x737;
  kk_string_t _x_x738;
  kk_define_string_literal(, _s_x739, 1, ")", _ctx)
  _x_x738 = kk_string_dup(_s_x739, _ctx); /*string*/
  _x_x737 = kk_std_core_types__lp__plus__plus__rp_(_y_x10082, _x_x738, _ctx); /*string*/
  _x_x734 = kk_std_core_types__lp__plus__plus__rp_(_x_x735, _x_x737, _ctx); /*string*/
  _x_x733 = kk_std_core_types__lp__plus__plus__rp_(_y_x10081, _x_x734, _ctx); /*string*/
  _x_x730 = kk_std_core_types__lp__plus__plus__rp_(_x_x731, _x_x733, _ctx); /*string*/
  _x_x729 = kk_std_core_types__lp__plus__plus__rp_(_y_x10080, _x_x730, _ctx); /*string*/
  return kk_std_core_types__lp__plus__plus__rp_(_x_x727, _x_x729, _ctx);
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742__t {
  struct kk_function_s _base;
  kk_string_t _y_x10080;
  kk_string_t _y_x10081;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742(kk_function_t _fself, kk_box_t _b_x244, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__new_mlift_show_10158_fun742(kk_string_t _y_x10080, kk_string_t _y_x10081, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742, kk_context());
  _self->_y_x10080 = _y_x10080;
  _self->_y_x10081 = _y_x10081;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742(kk_function_t _fself, kk_box_t _b_x244, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__mlift_show_10158_fun742__t*, _fself, _ctx);
  kk_string_t _y_x10080 = _self->_y_x10080; /* string */
  kk_string_t _y_x10081 = _self->_y_x10081; /* string */
  kk_drop_match(_self, {kk_string_dup(_y_x10080, _ctx);kk_string_dup(_y_x10081, _ctx);}, {}, _ctx)
  kk_string_t _y_x10082_246 = kk_string_unbox(_b_x244); /*string*/;
  kk_string_t _x_x743 = kk_std_core_tuple_tuple3_fs__mlift_show_10157(_y_x10080, _y_x10081, _y_x10082_246, _ctx); /*string*/
  return kk_string_box(_x_x743);
}

kk_string_t kk_std_core_tuple_tuple3_fs__mlift_show_10158(kk_string_t _y_x10080, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_string_t _y_x10081, kk_context_t* _ctx) { /* forall<a,b,c,e> (string, ?thd/show : (c) -> e string, x : (a, b, c), string) -> e string */ 
  kk_string_t x_0_10411;
  kk_box_t _x_x740;
  {
    kk_box_t _x_1 = x.thd;
    kk_box_dup(_x_1, _ctx);
    kk_std_core_types__tuple3_drop(x, _ctx);
    _x_x740 = _x_1; /*2810*/
  }
  x_0_10411 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_show, (_implicit_fs_thd_fs_show, _x_x740, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10411, _ctx);
    kk_box_t _x_x741 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__new_mlift_show_10158_fun742(_y_x10080, _y_x10081, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x741);
  }
  {
    return kk_std_core_tuple_tuple3_fs__mlift_show_10157(_y_x10080, _y_x10081, x_0_10411, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746__t {
  struct kk_function_s _base;
  kk_string_t _y_x10080;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple3 x;
};
static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746(kk_function_t _fself, kk_box_t _b_x248, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs__new_mlift_show_10159_fun746(kk_string_t _y_x10080, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746, kk_context());
  _self->_y_x10080 = _y_x10080;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746(kk_function_t _fself, kk_box_t _b_x248, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs__mlift_show_10159_fun746__t*, _fself, _ctx);
  kk_string_t _y_x10080 = _self->_y_x10080; /* string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (2810) -> 2811 string */
  kk_std_core_types__tuple3 x = _self->x; /* (2808, 2809, 2810) */
  kk_drop_match(_self, {kk_string_dup(_y_x10080, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple3_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10081_250 = kk_string_unbox(_b_x248); /*string*/;
  kk_string_t _x_x747 = kk_std_core_tuple_tuple3_fs__mlift_show_10158(_y_x10080, _implicit_fs_thd_fs_show, x, _y_x10081_250, _ctx); /*string*/
  return kk_string_box(_x_x747);
}

kk_string_t kk_std_core_tuple_tuple3_fs__mlift_show_10159(kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_string_t _y_x10080, kk_context_t* _ctx) { /* forall<a,b,c,e> (?snd/show : (b) -> e string, ?thd/show : (c) -> e string, x : (a, b, c), string) -> e string */ 
  kk_string_t x_0_10413;
  kk_box_t _x_x744;
  {
    kk_box_t _x_0 = x.snd;
    kk_box_dup(_x_0, _ctx);
    _x_x744 = _x_0; /*2809*/
  }
  x_0_10413 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x744, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10413, _ctx);
    kk_box_t _x_x745 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs__new_mlift_show_10159_fun746(_y_x10080, _implicit_fs_thd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x745);
  }
  {
    return kk_std_core_tuple_tuple3_fs__mlift_show_10158(_y_x10080, _implicit_fs_thd_fs_show, x, x_0_10413, _ctx);
  }
}
 
// Show a triple


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_show_fun750__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_snd_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple3 x;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_show_fun750(kk_function_t _fself, kk_box_t _b_x252, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_show_fun750(kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_show_fun750__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_show_fun750__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_show_fun750, kk_context());
  _self->_implicit_fs_snd_fs_show = _implicit_fs_snd_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_show_fun750(kk_function_t _fself, kk_box_t _b_x252, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_show_fun750__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_show_fun750__t*, _fself, _ctx);
  kk_function_t _implicit_fs_snd_fs_show = _self->_implicit_fs_snd_fs_show; /* (2809) -> 2811 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (2810) -> 2811 string */
  kk_std_core_types__tuple3 x = _self->x; /* (2808, 2809, 2810) */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_snd_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple3_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10080_260 = kk_string_unbox(_b_x252); /*string*/;
  kk_string_t _x_x751 = kk_std_core_tuple_tuple3_fs__mlift_show_10159(_implicit_fs_snd_fs_show, _implicit_fs_thd_fs_show, x, _y_x10080_260, _ctx); /*string*/
  return kk_string_box(_x_x751);
}


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_show_fun754__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple3 x;
  kk_string_t x_0_10415;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_show_fun754(kk_function_t _fself, kk_box_t _b_x254, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_show_fun754(kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple3 x, kk_string_t x_0_10415, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_show_fun754__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_show_fun754__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_show_fun754, kk_context());
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  _self->x_0_10415 = x_0_10415;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_show_fun754(kk_function_t _fself, kk_box_t _b_x254, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_show_fun754__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_show_fun754__t*, _fself, _ctx);
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (2810) -> 2811 string */
  kk_std_core_types__tuple3 x = _self->x; /* (2808, 2809, 2810) */
  kk_string_t x_0_10415 = _self->x_0_10415; /* string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple3_dup(x, _ctx);kk_string_dup(x_0_10415, _ctx);}, {}, _ctx)
  kk_string_t _y_x10081_261 = kk_string_unbox(_b_x254); /*string*/;
  kk_string_t _x_x755 = kk_std_core_tuple_tuple3_fs__mlift_show_10158(x_0_10415, _implicit_fs_thd_fs_show, x, _y_x10081_261, _ctx); /*string*/
  return kk_string_box(_x_x755);
}


// lift anonymous function
struct kk_std_core_tuple_tuple3_fs_show_fun758__t {
  struct kk_function_s _base;
  kk_string_t x_0_10415;
  kk_string_t x_1_10418;
};
static kk_box_t kk_std_core_tuple_tuple3_fs_show_fun758(kk_function_t _fself, kk_box_t _b_x256, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple3_fs_new_show_fun758(kk_string_t x_0_10415, kk_string_t x_1_10418, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_show_fun758__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple3_fs_show_fun758__t, 3, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple3_fs_show_fun758, kk_context());
  _self->x_0_10415 = x_0_10415;
  _self->x_1_10418 = x_1_10418;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple3_fs_show_fun758(kk_function_t _fself, kk_box_t _b_x256, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple3_fs_show_fun758__t* _self = kk_function_as(struct kk_std_core_tuple_tuple3_fs_show_fun758__t*, _fself, _ctx);
  kk_string_t x_0_10415 = _self->x_0_10415; /* string */
  kk_string_t x_1_10418 = _self->x_1_10418; /* string */
  kk_drop_match(_self, {kk_string_dup(x_0_10415, _ctx);kk_string_dup(x_1_10418, _ctx);}, {}, _ctx)
  kk_string_t _y_x10082_262 = kk_string_unbox(_b_x256); /*string*/;
  kk_string_t _x_x759 = kk_std_core_tuple_tuple3_fs__mlift_show_10157(x_0_10415, x_1_10418, _y_x10082_262, _ctx); /*string*/
  return kk_string_box(_x_x759);
}

kk_string_t kk_std_core_tuple_tuple3_fs_show(kk_std_core_types__tuple3 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_context_t* _ctx) { /* forall<a,b,c,e> (x : (a, b, c), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string) -> e string */ 
  kk_string_t x_0_10415;
  kk_box_t _x_x748;
  {
    kk_box_t _x = x.fst;
    kk_box_dup(_x, _ctx);
    _x_x748 = _x; /*2808*/
  }
  x_0_10415 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs_show, (_implicit_fs_fst_fs_show, _x_x748, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10415, _ctx);
    kk_box_t _x_x749 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs_new_show_fun750(_implicit_fs_snd_fs_show, _implicit_fs_thd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x749);
  }
  {
    kk_string_t x_1_10418;
    kk_box_t _x_x752;
    {
      kk_box_t _x_0 = x.snd;
      kk_box_dup(_x_0, _ctx);
      _x_x752 = _x_0; /*2809*/
    }
    x_1_10418 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x752, _ctx), _ctx); /*string*/
    if (kk_yielding(kk_context())) {
      kk_string_drop(x_1_10418, _ctx);
      kk_box_t _x_x753 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs_new_show_fun754(_implicit_fs_thd_fs_show, x, x_0_10415, _ctx), _ctx); /*2419*/
      return kk_string_unbox(_x_x753);
    }
    {
      kk_string_t x_2_10421;
      kk_box_t _x_x756;
      {
        kk_box_t _x_1 = x.thd;
        kk_box_dup(_x_1, _ctx);
        kk_std_core_types__tuple3_drop(x, _ctx);
        _x_x756 = _x_1; /*2810*/
      }
      x_2_10421 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_show, (_implicit_fs_thd_fs_show, _x_x756, _ctx), _ctx); /*string*/
      if (kk_yielding(kk_context())) {
        kk_string_drop(x_2_10421, _ctx);
        kk_box_t _x_x757 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple3_fs_new_show_fun758(x_0_10415, x_1_10418, _ctx), _ctx); /*2419*/
        return kk_string_unbox(_x_x757);
      }
      {
        kk_string_t _x_x760;
        kk_define_string_literal(, _s_x761, 1, "(", _ctx)
        _x_x760 = kk_string_dup(_s_x761, _ctx); /*string*/
        kk_string_t _x_x762;
        kk_string_t _x_x763;
        kk_string_t _x_x764;
        kk_define_string_literal(, _s_x765, 1, ",", _ctx)
        _x_x764 = kk_string_dup(_s_x765, _ctx); /*string*/
        kk_string_t _x_x766;
        kk_string_t _x_x767;
        kk_string_t _x_x768;
        kk_define_string_literal(, _s_x769, 1, ",", _ctx)
        _x_x768 = kk_string_dup(_s_x769, _ctx); /*string*/
        kk_string_t _x_x770;
        kk_string_t _x_x771;
        kk_define_string_literal(, _s_x772, 1, ")", _ctx)
        _x_x771 = kk_string_dup(_s_x772, _ctx); /*string*/
        _x_x770 = kk_std_core_types__lp__plus__plus__rp_(x_2_10421, _x_x771, _ctx); /*string*/
        _x_x767 = kk_std_core_types__lp__plus__plus__rp_(_x_x768, _x_x770, _ctx); /*string*/
        _x_x766 = kk_std_core_types__lp__plus__plus__rp_(x_1_10418, _x_x767, _ctx); /*string*/
        _x_x763 = kk_std_core_types__lp__plus__plus__rp_(_x_x764, _x_x766, _ctx); /*string*/
        _x_x762 = kk_std_core_types__lp__plus__plus__rp_(x_0_10415, _x_x763, _ctx); /*string*/
        return kk_std_core_types__lp__plus__plus__rp_(_x_x760, _x_x762, _ctx);
      }
    }
  }
}
 
// monadic lift

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10160(kk_string_t _y_x10083, kk_string_t _y_x10084, kk_string_t _y_x10085, kk_string_t _y_x10086, kk_context_t* _ctx) { /* forall<e> (string, string, string, string) -> e string */ 
  kk_string_t _x_x773;
  kk_define_string_literal(, _s_x774, 1, "(", _ctx)
  _x_x773 = kk_string_dup(_s_x774, _ctx); /*string*/
  kk_string_t _x_x775;
  kk_string_t _x_x776;
  kk_string_t _x_x777;
  kk_define_string_literal(, _s_x778, 1, ",", _ctx)
  _x_x777 = kk_string_dup(_s_x778, _ctx); /*string*/
  kk_string_t _x_x779;
  kk_string_t _x_x780;
  kk_string_t _x_x781;
  kk_define_string_literal(, _s_x782, 1, ",", _ctx)
  _x_x781 = kk_string_dup(_s_x782, _ctx); /*string*/
  kk_string_t _x_x783;
  kk_string_t _x_x784;
  kk_string_t _x_x785;
  kk_define_string_literal(, _s_x786, 1, ",", _ctx)
  _x_x785 = kk_string_dup(_s_x786, _ctx); /*string*/
  kk_string_t _x_x787;
  kk_string_t _x_x788;
  kk_define_string_literal(, _s_x789, 1, ")", _ctx)
  _x_x788 = kk_string_dup(_s_x789, _ctx); /*string*/
  _x_x787 = kk_std_core_types__lp__plus__plus__rp_(_y_x10086, _x_x788, _ctx); /*string*/
  _x_x784 = kk_std_core_types__lp__plus__plus__rp_(_x_x785, _x_x787, _ctx); /*string*/
  _x_x783 = kk_std_core_types__lp__plus__plus__rp_(_y_x10085, _x_x784, _ctx); /*string*/
  _x_x780 = kk_std_core_types__lp__plus__plus__rp_(_x_x781, _x_x783, _ctx); /*string*/
  _x_x779 = kk_std_core_types__lp__plus__plus__rp_(_y_x10084, _x_x780, _ctx); /*string*/
  _x_x776 = kk_std_core_types__lp__plus__plus__rp_(_x_x777, _x_x779, _ctx); /*string*/
  _x_x775 = kk_std_core_types__lp__plus__plus__rp_(_y_x10083, _x_x776, _ctx); /*string*/
  return kk_std_core_types__lp__plus__plus__rp_(_x_x773, _x_x775, _ctx);
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793__t {
  struct kk_function_s _base;
  kk_string_t _y_x10083;
  kk_string_t _y_x10084;
  kk_string_t _y_x10085;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793(kk_function_t _fself, kk_box_t _b_x264, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_show_10161_fun793(kk_string_t _y_x10083, kk_string_t _y_x10084, kk_string_t _y_x10085, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793, kk_context());
  _self->_y_x10083 = _y_x10083;
  _self->_y_x10084 = _y_x10084;
  _self->_y_x10085 = _y_x10085;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793(kk_function_t _fself, kk_box_t _b_x264, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_show_10161_fun793__t*, _fself, _ctx);
  kk_string_t _y_x10083 = _self->_y_x10083; /* string */
  kk_string_t _y_x10084 = _self->_y_x10084; /* string */
  kk_string_t _y_x10085 = _self->_y_x10085; /* string */
  kk_drop_match(_self, {kk_string_dup(_y_x10083, _ctx);kk_string_dup(_y_x10084, _ctx);kk_string_dup(_y_x10085, _ctx);}, {}, _ctx)
  kk_string_t _y_x10086_266 = kk_string_unbox(_b_x264); /*string*/;
  kk_string_t _x_x794 = kk_std_core_tuple_tuple4_fs__mlift_show_10160(_y_x10083, _y_x10084, _y_x10085, _y_x10086_266, _ctx); /*string*/
  return kk_string_box(_x_x794);
}

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10161(kk_string_t _y_x10083, kk_string_t _y_x10084, kk_function_t _implicit_fs_field4_fs_show, kk_std_core_types__tuple4 x, kk_string_t _y_x10085, kk_context_t* _ctx) { /* forall<a,b,c,d,e> (string, string, ?field4/show : (d) -> e string, x : (a, b, c, d), string) -> e string */ 
  kk_string_t x_0_10424;
  kk_box_t _x_x790;
  {
    struct kk_std_core_types_Tuple4* _con_x791 = kk_std_core_types__as_Tuple4(x, _ctx);
    kk_box_t _pat_0_2 = _con_x791->fst;
    kk_box_t _pat_1_2 = _con_x791->snd;
    kk_box_t _pat_2_2 = _con_x791->thd;
    kk_box_t _x_2 = _con_x791->field4;
    if kk_likely(kk_datatype_ptr_is_unique(x, _ctx)) {
      kk_box_drop(_pat_2_2, _ctx);
      kk_box_drop(_pat_1_2, _ctx);
      kk_box_drop(_pat_0_2, _ctx);
      kk_datatype_ptr_free(x, _ctx);
    }
    else {
      kk_box_dup(_x_2, _ctx);
      kk_datatype_ptr_decref(x, _ctx);
    }
    _x_x790 = _x_2; /*3212*/
  }
  x_0_10424 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_show, (_implicit_fs_field4_fs_show, _x_x790, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10424, _ctx);
    kk_box_t _x_x792 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_show_10161_fun793(_y_x10083, _y_x10084, _y_x10085, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x792);
  }
  {
    return kk_std_core_tuple_tuple4_fs__mlift_show_10160(_y_x10083, _y_x10084, _y_x10085, x_0_10424, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798__t {
  struct kk_function_s _base;
  kk_string_t _y_x10083;
  kk_string_t _y_x10084;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_std_core_types__tuple4 x;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798(kk_function_t _fself, kk_box_t _b_x268, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_show_10162_fun798(kk_string_t _y_x10083, kk_string_t _y_x10084, kk_function_t _implicit_fs_field4_fs_show, kk_std_core_types__tuple4 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798, kk_context());
  _self->_y_x10083 = _y_x10083;
  _self->_y_x10084 = _y_x10084;
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798(kk_function_t _fself, kk_box_t _b_x268, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_show_10162_fun798__t*, _fself, _ctx);
  kk_string_t _y_x10083 = _self->_y_x10083; /* string */
  kk_string_t _y_x10084 = _self->_y_x10084; /* string */
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3212) -> 3213 string */
  kk_std_core_types__tuple4 x = _self->x; /* (3209, 3210, 3211, 3212) */
  kk_drop_match(_self, {kk_string_dup(_y_x10083, _ctx);kk_string_dup(_y_x10084, _ctx);kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_std_core_types__tuple4_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10085_270 = kk_string_unbox(_b_x268); /*string*/;
  kk_string_t _x_x799 = kk_std_core_tuple_tuple4_fs__mlift_show_10161(_y_x10083, _y_x10084, _implicit_fs_field4_fs_show, x, _y_x10085_270, _ctx); /*string*/
  return kk_string_box(_x_x799);
}

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10162(kk_string_t _y_x10083, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_string_t _y_x10084, kk_context_t* _ctx) { /* forall<a,b,c,d,e> (string, ?field4/show : (d) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d), string) -> e string */ 
  kk_string_t x_0_10426;
  kk_box_t _x_x795;
  {
    struct kk_std_core_types_Tuple4* _con_x796 = kk_std_core_types__as_Tuple4(x, _ctx);
    kk_box_t _x_1 = _con_x796->thd;
    kk_box_dup(_x_1, _ctx);
    _x_x795 = _x_1; /*3211*/
  }
  x_0_10426 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_show, (_implicit_fs_thd_fs_show, _x_x795, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10426, _ctx);
    kk_box_t _x_x797 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_show_10162_fun798(_y_x10083, _y_x10084, _implicit_fs_field4_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x797);
  }
  {
    return kk_std_core_tuple_tuple4_fs__mlift_show_10161(_y_x10083, _y_x10084, _implicit_fs_field4_fs_show, x, x_0_10426, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803__t {
  struct kk_function_s _base;
  kk_string_t _y_x10083;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple4 x;
};
static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803(kk_function_t _fself, kk_box_t _b_x272, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs__new_mlift_show_10163_fun803(kk_string_t _y_x10083, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803, kk_context());
  _self->_y_x10083 = _y_x10083;
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803(kk_function_t _fself, kk_box_t _b_x272, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs__mlift_show_10163_fun803__t*, _fself, _ctx);
  kk_string_t _y_x10083 = _self->_y_x10083; /* string */
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3212) -> 3213 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (3211) -> 3213 string */
  kk_std_core_types__tuple4 x = _self->x; /* (3209, 3210, 3211, 3212) */
  kk_drop_match(_self, {kk_string_dup(_y_x10083, _ctx);kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple4_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10084_274 = kk_string_unbox(_b_x272); /*string*/;
  kk_string_t _x_x804 = kk_std_core_tuple_tuple4_fs__mlift_show_10162(_y_x10083, _implicit_fs_field4_fs_show, _implicit_fs_thd_fs_show, x, _y_x10084_274, _ctx); /*string*/
  return kk_string_box(_x_x804);
}

kk_string_t kk_std_core_tuple_tuple4_fs__mlift_show_10163(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_string_t _y_x10083, kk_context_t* _ctx) { /* forall<a,b,c,d,e> (?field4/show : (d) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d), string) -> e string */ 
  kk_string_t x_0_10428;
  kk_box_t _x_x800;
  {
    struct kk_std_core_types_Tuple4* _con_x801 = kk_std_core_types__as_Tuple4(x, _ctx);
    kk_box_t _x_0 = _con_x801->snd;
    kk_box_dup(_x_0, _ctx);
    _x_x800 = _x_0; /*3210*/
  }
  x_0_10428 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x800, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10428, _ctx);
    kk_box_t _x_x802 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs__new_mlift_show_10163_fun803(_y_x10083, _implicit_fs_field4_fs_show, _implicit_fs_thd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x802);
  }
  {
    return kk_std_core_tuple_tuple4_fs__mlift_show_10162(_y_x10083, _implicit_fs_field4_fs_show, _implicit_fs_thd_fs_show, x, x_0_10428, _ctx);
  }
}
 
// Show a quadruple


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_show_fun808__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_snd_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple4 x;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun808(kk_function_t _fself, kk_box_t _b_x276, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_show_fun808(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun808__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_show_fun808__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_show_fun808, kk_context());
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_snd_fs_show = _implicit_fs_snd_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun808(kk_function_t _fself, kk_box_t _b_x276, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun808__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_show_fun808__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3212) -> 3213 string */
  kk_function_t _implicit_fs_snd_fs_show = _self->_implicit_fs_snd_fs_show; /* (3210) -> 3213 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (3211) -> 3213 string */
  kk_std_core_types__tuple4 x = _self->x; /* (3209, 3210, 3211, 3212) */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_snd_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple4_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10083_287 = kk_string_unbox(_b_x276); /*string*/;
  kk_string_t _x_x809 = kk_std_core_tuple_tuple4_fs__mlift_show_10163(_implicit_fs_field4_fs_show, _implicit_fs_snd_fs_show, _implicit_fs_thd_fs_show, x, _y_x10083_287, _ctx); /*string*/
  return kk_string_box(_x_x809);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_show_fun813__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple4 x;
  kk_string_t x_0_10430;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun813(kk_function_t _fself, kk_box_t _b_x278, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_show_fun813(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple4 x, kk_string_t x_0_10430, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun813__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_show_fun813__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_show_fun813, kk_context());
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  _self->x_0_10430 = x_0_10430;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun813(kk_function_t _fself, kk_box_t _b_x278, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun813__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_show_fun813__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3212) -> 3213 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (3211) -> 3213 string */
  kk_std_core_types__tuple4 x = _self->x; /* (3209, 3210, 3211, 3212) */
  kk_string_t x_0_10430 = _self->x_0_10430; /* string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple4_dup(x, _ctx);kk_string_dup(x_0_10430, _ctx);}, {}, _ctx)
  kk_string_t _y_x10084_288 = kk_string_unbox(_b_x278); /*string*/;
  kk_string_t _x_x814 = kk_std_core_tuple_tuple4_fs__mlift_show_10162(x_0_10430, _implicit_fs_field4_fs_show, _implicit_fs_thd_fs_show, x, _y_x10084_288, _ctx); /*string*/
  return kk_string_box(_x_x814);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_show_fun818__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_std_core_types__tuple4 x;
  kk_string_t x_0_10430;
  kk_string_t x_1_10433;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun818(kk_function_t _fself, kk_box_t _b_x280, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_show_fun818(kk_function_t _implicit_fs_field4_fs_show, kk_std_core_types__tuple4 x, kk_string_t x_0_10430, kk_string_t x_1_10433, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun818__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_show_fun818__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_show_fun818, kk_context());
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->x = x;
  _self->x_0_10430 = x_0_10430;
  _self->x_1_10433 = x_1_10433;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun818(kk_function_t _fself, kk_box_t _b_x280, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun818__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_show_fun818__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3212) -> 3213 string */
  kk_std_core_types__tuple4 x = _self->x; /* (3209, 3210, 3211, 3212) */
  kk_string_t x_0_10430 = _self->x_0_10430; /* string */
  kk_string_t x_1_10433 = _self->x_1_10433; /* string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_std_core_types__tuple4_dup(x, _ctx);kk_string_dup(x_0_10430, _ctx);kk_string_dup(x_1_10433, _ctx);}, {}, _ctx)
  kk_string_t _y_x10085_289 = kk_string_unbox(_b_x280); /*string*/;
  kk_string_t _x_x819 = kk_std_core_tuple_tuple4_fs__mlift_show_10161(x_0_10430, x_1_10433, _implicit_fs_field4_fs_show, x, _y_x10085_289, _ctx); /*string*/
  return kk_string_box(_x_x819);
}


// lift anonymous function
struct kk_std_core_tuple_tuple4_fs_show_fun823__t {
  struct kk_function_s _base;
  kk_string_t x_0_10430;
  kk_string_t x_1_10433;
  kk_string_t x_2_10436;
};
static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun823(kk_function_t _fself, kk_box_t _b_x282, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple4_fs_new_show_fun823(kk_string_t x_0_10430, kk_string_t x_1_10433, kk_string_t x_2_10436, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun823__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple4_fs_show_fun823__t, 4, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple4_fs_show_fun823, kk_context());
  _self->x_0_10430 = x_0_10430;
  _self->x_1_10433 = x_1_10433;
  _self->x_2_10436 = x_2_10436;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple4_fs_show_fun823(kk_function_t _fself, kk_box_t _b_x282, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple4_fs_show_fun823__t* _self = kk_function_as(struct kk_std_core_tuple_tuple4_fs_show_fun823__t*, _fself, _ctx);
  kk_string_t x_0_10430 = _self->x_0_10430; /* string */
  kk_string_t x_1_10433 = _self->x_1_10433; /* string */
  kk_string_t x_2_10436 = _self->x_2_10436; /* string */
  kk_drop_match(_self, {kk_string_dup(x_0_10430, _ctx);kk_string_dup(x_1_10433, _ctx);kk_string_dup(x_2_10436, _ctx);}, {}, _ctx)
  kk_string_t _y_x10086_290 = kk_string_unbox(_b_x282); /*string*/;
  kk_string_t _x_x824 = kk_std_core_tuple_tuple4_fs__mlift_show_10160(x_0_10430, x_1_10433, x_2_10436, _y_x10086_290, _ctx); /*string*/
  return kk_string_box(_x_x824);
}

kk_string_t kk_std_core_tuple_tuple4_fs_show(kk_std_core_types__tuple4 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_function_t _implicit_fs_field4_fs_show, kk_context_t* _ctx) { /* forall<a,b,c,d,e> (x : (a, b, c, d), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, ?field4/show : (d) -> e string) -> e string */ 
  kk_string_t x_0_10430;
  kk_box_t _x_x805;
  {
    struct kk_std_core_types_Tuple4* _con_x806 = kk_std_core_types__as_Tuple4(x, _ctx);
    kk_box_t _x = _con_x806->fst;
    kk_box_dup(_x, _ctx);
    _x_x805 = _x; /*3209*/
  }
  x_0_10430 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs_show, (_implicit_fs_fst_fs_show, _x_x805, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10430, _ctx);
    kk_box_t _x_x807 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_show_fun808(_implicit_fs_field4_fs_show, _implicit_fs_snd_fs_show, _implicit_fs_thd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x807);
  }
  {
    kk_string_t x_1_10433;
    kk_box_t _x_x810;
    {
      struct kk_std_core_types_Tuple4* _con_x811 = kk_std_core_types__as_Tuple4(x, _ctx);
      kk_box_t _x_0 = _con_x811->snd;
      kk_box_dup(_x_0, _ctx);
      _x_x810 = _x_0; /*3210*/
    }
    x_1_10433 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x810, _ctx), _ctx); /*string*/
    if (kk_yielding(kk_context())) {
      kk_string_drop(x_1_10433, _ctx);
      kk_box_t _x_x812 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_show_fun813(_implicit_fs_field4_fs_show, _implicit_fs_thd_fs_show, x, x_0_10430, _ctx), _ctx); /*2419*/
      return kk_string_unbox(_x_x812);
    }
    {
      kk_string_t x_2_10436;
      kk_box_t _x_x815;
      {
        struct kk_std_core_types_Tuple4* _con_x816 = kk_std_core_types__as_Tuple4(x, _ctx);
        kk_box_t _x_1 = _con_x816->thd;
        kk_box_dup(_x_1, _ctx);
        _x_x815 = _x_1; /*3211*/
      }
      x_2_10436 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_show, (_implicit_fs_thd_fs_show, _x_x815, _ctx), _ctx); /*string*/
      if (kk_yielding(kk_context())) {
        kk_string_drop(x_2_10436, _ctx);
        kk_box_t _x_x817 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_show_fun818(_implicit_fs_field4_fs_show, x, x_0_10430, x_1_10433, _ctx), _ctx); /*2419*/
        return kk_string_unbox(_x_x817);
      }
      {
        kk_string_t x_3_10439;
        kk_box_t _x_x820;
        {
          struct kk_std_core_types_Tuple4* _con_x821 = kk_std_core_types__as_Tuple4(x, _ctx);
          kk_box_t _pat_0_2_0 = _con_x821->fst;
          kk_box_t _pat_1_2 = _con_x821->snd;
          kk_box_t _pat_2_2 = _con_x821->thd;
          kk_box_t _x_2 = _con_x821->field4;
          if kk_likely(kk_datatype_ptr_is_unique(x, _ctx)) {
            kk_box_drop(_pat_2_2, _ctx);
            kk_box_drop(_pat_1_2, _ctx);
            kk_box_drop(_pat_0_2_0, _ctx);
            kk_datatype_ptr_free(x, _ctx);
          }
          else {
            kk_box_dup(_x_2, _ctx);
            kk_datatype_ptr_decref(x, _ctx);
          }
          _x_x820 = _x_2; /*3212*/
        }
        x_3_10439 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_show, (_implicit_fs_field4_fs_show, _x_x820, _ctx), _ctx); /*string*/
        if (kk_yielding(kk_context())) {
          kk_string_drop(x_3_10439, _ctx);
          kk_box_t _x_x822 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple4_fs_new_show_fun823(x_0_10430, x_1_10433, x_2_10436, _ctx), _ctx); /*2419*/
          return kk_string_unbox(_x_x822);
        }
        {
          kk_string_t _x_x825;
          kk_define_string_literal(, _s_x826, 1, "(", _ctx)
          _x_x825 = kk_string_dup(_s_x826, _ctx); /*string*/
          kk_string_t _x_x827;
          kk_string_t _x_x828;
          kk_string_t _x_x829;
          kk_define_string_literal(, _s_x830, 1, ",", _ctx)
          _x_x829 = kk_string_dup(_s_x830, _ctx); /*string*/
          kk_string_t _x_x831;
          kk_string_t _x_x832;
          kk_string_t _x_x833;
          kk_define_string_literal(, _s_x834, 1, ",", _ctx)
          _x_x833 = kk_string_dup(_s_x834, _ctx); /*string*/
          kk_string_t _x_x835;
          kk_string_t _x_x836;
          kk_string_t _x_x837;
          kk_define_string_literal(, _s_x838, 1, ",", _ctx)
          _x_x837 = kk_string_dup(_s_x838, _ctx); /*string*/
          kk_string_t _x_x839;
          kk_string_t _x_x840;
          kk_define_string_literal(, _s_x841, 1, ")", _ctx)
          _x_x840 = kk_string_dup(_s_x841, _ctx); /*string*/
          _x_x839 = kk_std_core_types__lp__plus__plus__rp_(x_3_10439, _x_x840, _ctx); /*string*/
          _x_x836 = kk_std_core_types__lp__plus__plus__rp_(_x_x837, _x_x839, _ctx); /*string*/
          _x_x835 = kk_std_core_types__lp__plus__plus__rp_(x_2_10436, _x_x836, _ctx); /*string*/
          _x_x832 = kk_std_core_types__lp__plus__plus__rp_(_x_x833, _x_x835, _ctx); /*string*/
          _x_x831 = kk_std_core_types__lp__plus__plus__rp_(x_1_10433, _x_x832, _ctx); /*string*/
          _x_x828 = kk_std_core_types__lp__plus__plus__rp_(_x_x829, _x_x831, _ctx); /*string*/
          _x_x827 = kk_std_core_types__lp__plus__plus__rp_(x_0_10430, _x_x828, _ctx); /*string*/
          return kk_std_core_types__lp__plus__plus__rp_(_x_x825, _x_x827, _ctx);
        }
      }
    }
  }
}
 
// monadic lift

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10164(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_string_t _y_x10089, kk_string_t _y_x10090, kk_string_t _y_x10091, kk_context_t* _ctx) { /* forall<e> (string, string, string, string, string) -> e string */ 
  kk_string_t _x_x842;
  kk_define_string_literal(, _s_x843, 1, "(", _ctx)
  _x_x842 = kk_string_dup(_s_x843, _ctx); /*string*/
  kk_string_t _x_x844;
  kk_string_t _x_x845;
  kk_string_t _x_x846;
  kk_define_string_literal(, _s_x847, 1, ",", _ctx)
  _x_x846 = kk_string_dup(_s_x847, _ctx); /*string*/
  kk_string_t _x_x848;
  kk_string_t _x_x849;
  kk_string_t _x_x850;
  kk_define_string_literal(, _s_x851, 1, ",", _ctx)
  _x_x850 = kk_string_dup(_s_x851, _ctx); /*string*/
  kk_string_t _x_x852;
  kk_string_t _x_x853;
  kk_string_t _x_x854;
  kk_define_string_literal(, _s_x855, 1, ",", _ctx)
  _x_x854 = kk_string_dup(_s_x855, _ctx); /*string*/
  kk_string_t _x_x856;
  kk_string_t _x_x857;
  kk_string_t _x_x858;
  kk_define_string_literal(, _s_x859, 1, ",", _ctx)
  _x_x858 = kk_string_dup(_s_x859, _ctx); /*string*/
  kk_string_t _x_x860;
  kk_string_t _x_x861;
  kk_define_string_literal(, _s_x862, 1, ")", _ctx)
  _x_x861 = kk_string_dup(_s_x862, _ctx); /*string*/
  _x_x860 = kk_std_core_types__lp__plus__plus__rp_(_y_x10091, _x_x861, _ctx); /*string*/
  _x_x857 = kk_std_core_types__lp__plus__plus__rp_(_x_x858, _x_x860, _ctx); /*string*/
  _x_x856 = kk_std_core_types__lp__plus__plus__rp_(_y_x10090, _x_x857, _ctx); /*string*/
  _x_x853 = kk_std_core_types__lp__plus__plus__rp_(_x_x854, _x_x856, _ctx); /*string*/
  _x_x852 = kk_std_core_types__lp__plus__plus__rp_(_y_x10089, _x_x853, _ctx); /*string*/
  _x_x849 = kk_std_core_types__lp__plus__plus__rp_(_x_x850, _x_x852, _ctx); /*string*/
  _x_x848 = kk_std_core_types__lp__plus__plus__rp_(_y_x10088, _x_x849, _ctx); /*string*/
  _x_x845 = kk_std_core_types__lp__plus__plus__rp_(_x_x846, _x_x848, _ctx); /*string*/
  _x_x844 = kk_std_core_types__lp__plus__plus__rp_(_y_x10087, _x_x845, _ctx); /*string*/
  return kk_std_core_types__lp__plus__plus__rp_(_x_x842, _x_x844, _ctx);
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866__t {
  struct kk_function_s _base;
  kk_string_t _y_x10087;
  kk_string_t _y_x10088;
  kk_string_t _y_x10089;
  kk_string_t _y_x10090;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866(kk_function_t _fself, kk_box_t _b_x292, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_show_10165_fun866(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_string_t _y_x10089, kk_string_t _y_x10090, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866, kk_context());
  _self->_y_x10087 = _y_x10087;
  _self->_y_x10088 = _y_x10088;
  _self->_y_x10089 = _y_x10089;
  _self->_y_x10090 = _y_x10090;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866(kk_function_t _fself, kk_box_t _b_x292, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10165_fun866__t*, _fself, _ctx);
  kk_string_t _y_x10087 = _self->_y_x10087; /* string */
  kk_string_t _y_x10088 = _self->_y_x10088; /* string */
  kk_string_t _y_x10089 = _self->_y_x10089; /* string */
  kk_string_t _y_x10090 = _self->_y_x10090; /* string */
  kk_drop_match(_self, {kk_string_dup(_y_x10087, _ctx);kk_string_dup(_y_x10088, _ctx);kk_string_dup(_y_x10089, _ctx);kk_string_dup(_y_x10090, _ctx);}, {}, _ctx)
  kk_string_t _y_x10091_294 = kk_string_unbox(_b_x292); /*string*/;
  kk_string_t _x_x867 = kk_std_core_tuple_tuple5_fs__mlift_show_10164(_y_x10087, _y_x10088, _y_x10089, _y_x10090, _y_x10091_294, _ctx); /*string*/
  return kk_string_box(_x_x867);
}

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10165(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_string_t _y_x10089, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10090, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (string, string, string, ?field5/show : (a1) -> e string, x : (a, b, c, d, a1), string) -> e string */ 
  kk_string_t x_0_10442;
  kk_box_t _x_x863;
  {
    struct kk_std_core_types_Tuple5* _con_x864 = kk_std_core_types__as_Tuple5(x, _ctx);
    kk_box_t _pat_0_3 = _con_x864->fst;
    kk_box_t _pat_1_3 = _con_x864->snd;
    kk_box_t _pat_2_3 = _con_x864->thd;
    kk_box_t _pat_3_3 = _con_x864->field4;
    kk_box_t _x_3 = _con_x864->field5;
    if kk_likely(kk_datatype_ptr_is_unique(x, _ctx)) {
      kk_box_drop(_pat_3_3, _ctx);
      kk_box_drop(_pat_2_3, _ctx);
      kk_box_drop(_pat_1_3, _ctx);
      kk_box_drop(_pat_0_3, _ctx);
      kk_datatype_ptr_free(x, _ctx);
    }
    else {
      kk_box_dup(_x_3, _ctx);
      kk_datatype_ptr_decref(x, _ctx);
    }
    _x_x863 = _x_3; /*3704*/
  }
  x_0_10442 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs_show, (_implicit_fs_field5_fs_show, _x_x863, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10442, _ctx);
    kk_box_t _x_x865 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_show_10165_fun866(_y_x10087, _y_x10088, _y_x10089, _y_x10090, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x865);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_show_10164(_y_x10087, _y_x10088, _y_x10089, _y_x10090, x_0_10442, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871__t {
  struct kk_function_s _base;
  kk_string_t _y_x10087;
  kk_string_t _y_x10088;
  kk_string_t _y_x10089;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_std_core_types__tuple5 x;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871(kk_function_t _fself, kk_box_t _b_x296, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_show_10166_fun871(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_string_t _y_x10089, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871, kk_context());
  _self->_y_x10087 = _y_x10087;
  _self->_y_x10088 = _y_x10088;
  _self->_y_x10089 = _y_x10089;
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871(kk_function_t _fself, kk_box_t _b_x296, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10166_fun871__t*, _fself, _ctx);
  kk_string_t _y_x10087 = _self->_y_x10087; /* string */
  kk_string_t _y_x10088 = _self->_y_x10088; /* string */
  kk_string_t _y_x10089 = _self->_y_x10089; /* string */
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_drop_match(_self, {kk_string_dup(_y_x10087, _ctx);kk_string_dup(_y_x10088, _ctx);kk_string_dup(_y_x10089, _ctx);kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10090_298 = kk_string_unbox(_b_x296); /*string*/;
  kk_string_t _x_x872 = kk_std_core_tuple_tuple5_fs__mlift_show_10165(_y_x10087, _y_x10088, _y_x10089, _implicit_fs_field5_fs_show, x, _y_x10090_298, _ctx); /*string*/
  return kk_string_box(_x_x872);
}

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10166(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10089, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (string, string, ?field4/show : (d) -> e string, ?field5/show : (a1) -> e string, x : (a, b, c, d, a1), string) -> e string */ 
  kk_string_t x_0_10444;
  kk_box_t _x_x868;
  {
    struct kk_std_core_types_Tuple5* _con_x869 = kk_std_core_types__as_Tuple5(x, _ctx);
    kk_box_t _x_2 = _con_x869->field4;
    kk_box_dup(_x_2, _ctx);
    _x_x868 = _x_2; /*3702*/
  }
  x_0_10444 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_show, (_implicit_fs_field4_fs_show, _x_x868, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10444, _ctx);
    kk_box_t _x_x870 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_show_10166_fun871(_y_x10087, _y_x10088, _y_x10089, _implicit_fs_field5_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x870);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_show_10165(_y_x10087, _y_x10088, _y_x10089, _implicit_fs_field5_fs_show, x, x_0_10444, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876__t {
  struct kk_function_s _base;
  kk_string_t _y_x10087;
  kk_string_t _y_x10088;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_std_core_types__tuple5 x;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876(kk_function_t _fself, kk_box_t _b_x300, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_show_10167_fun876(kk_string_t _y_x10087, kk_string_t _y_x10088, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876, kk_context());
  _self->_y_x10087 = _y_x10087;
  _self->_y_x10088 = _y_x10088;
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876(kk_function_t _fself, kk_box_t _b_x300, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10167_fun876__t*, _fself, _ctx);
  kk_string_t _y_x10087 = _self->_y_x10087; /* string */
  kk_string_t _y_x10088 = _self->_y_x10088; /* string */
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3702) -> 3703 string */
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_drop_match(_self, {kk_string_dup(_y_x10087, _ctx);kk_string_dup(_y_x10088, _ctx);kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10089_302 = kk_string_unbox(_b_x300); /*string*/;
  kk_string_t _x_x877 = kk_std_core_tuple_tuple5_fs__mlift_show_10166(_y_x10087, _y_x10088, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, x, _y_x10089_302, _ctx); /*string*/
  return kk_string_box(_x_x877);
}

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10167(kk_string_t _y_x10087, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10088, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (string, ?field4/show : (d) -> e string, ?field5/show : (a1) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d, a1), string) -> e string */ 
  kk_string_t x_0_10446;
  kk_box_t _x_x873;
  {
    struct kk_std_core_types_Tuple5* _con_x874 = kk_std_core_types__as_Tuple5(x, _ctx);
    kk_box_t _x_1 = _con_x874->thd;
    kk_box_dup(_x_1, _ctx);
    _x_x873 = _x_1; /*3701*/
  }
  x_0_10446 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_show, (_implicit_fs_thd_fs_show, _x_x873, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10446, _ctx);
    kk_box_t _x_x875 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_show_10167_fun876(_y_x10087, _y_x10088, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x875);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_show_10166(_y_x10087, _y_x10088, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, x, x_0_10446, _ctx);
  }
}
 
// monadic lift


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881__t {
  struct kk_function_s _base;
  kk_string_t _y_x10087;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple5 x;
};
static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881(kk_function_t _fself, kk_box_t _b_x304, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs__new_mlift_show_10168_fun881(kk_string_t _y_x10087, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881, kk_context());
  _self->_y_x10087 = _y_x10087;
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881(kk_function_t _fself, kk_box_t _b_x304, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs__mlift_show_10168_fun881__t*, _fself, _ctx);
  kk_string_t _y_x10087 = _self->_y_x10087; /* string */
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3702) -> 3703 string */
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (3701) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_drop_match(_self, {kk_string_dup(_y_x10087, _ctx);kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10088_306 = kk_string_unbox(_b_x304); /*string*/;
  kk_string_t _x_x882 = kk_std_core_tuple_tuple5_fs__mlift_show_10167(_y_x10087, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_thd_fs_show, x, _y_x10088_306, _ctx); /*string*/
  return kk_string_box(_x_x882);
}

kk_string_t kk_std_core_tuple_tuple5_fs__mlift_show_10168(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_string_t _y_x10087, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (?field4/show : (d) -> e string, ?field5/show : (a1) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, x : (a, b, c, d, a1), string) -> e string */ 
  kk_string_t x_0_10448;
  kk_box_t _x_x878;
  {
    struct kk_std_core_types_Tuple5* _con_x879 = kk_std_core_types__as_Tuple5(x, _ctx);
    kk_box_t _x_0 = _con_x879->snd;
    kk_box_dup(_x_0, _ctx);
    _x_x878 = _x_0; /*3700*/
  }
  x_0_10448 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x878, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10448, _ctx);
    kk_box_t _x_x880 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs__new_mlift_show_10168_fun881(_y_x10087, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_thd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x880);
  }
  {
    return kk_std_core_tuple_tuple5_fs__mlift_show_10167(_y_x10087, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_thd_fs_show, x, x_0_10448, _ctx);
  }
}
 
// Show a quintuple


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_show_fun886__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_function_t _implicit_fs_snd_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple5 x;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun886(kk_function_t _fself, kk_box_t _b_x308, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_show_fun886(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun886__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_show_fun886__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_show_fun886, kk_context());
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->_implicit_fs_snd_fs_show = _implicit_fs_snd_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun886(kk_function_t _fself, kk_box_t _b_x308, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun886__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_show_fun886__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3702) -> 3703 string */
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_function_t _implicit_fs_snd_fs_show = _self->_implicit_fs_snd_fs_show; /* (3700) -> 3703 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (3701) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_function_dup(_implicit_fs_snd_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);}, {}, _ctx)
  kk_string_t _y_x10087_322 = kk_string_unbox(_b_x308); /*string*/;
  kk_string_t _x_x887 = kk_std_core_tuple_tuple5_fs__mlift_show_10168(_implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_snd_fs_show, _implicit_fs_thd_fs_show, x, _y_x10087_322, _ctx); /*string*/
  return kk_string_box(_x_x887);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_show_fun891__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_function_t _implicit_fs_thd_fs_show;
  kk_std_core_types__tuple5 x;
  kk_string_t x_0_10450;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun891(kk_function_t _fself, kk_box_t _b_x310, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_show_fun891(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_std_core_types__tuple5 x, kk_string_t x_0_10450, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun891__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_show_fun891__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_show_fun891, kk_context());
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->_implicit_fs_thd_fs_show = _implicit_fs_thd_fs_show;
  _self->x = x;
  _self->x_0_10450 = x_0_10450;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun891(kk_function_t _fself, kk_box_t _b_x310, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun891__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_show_fun891__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3702) -> 3703 string */
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_function_t _implicit_fs_thd_fs_show = _self->_implicit_fs_thd_fs_show; /* (3701) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_string_t x_0_10450 = _self->x_0_10450; /* string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_function_dup(_implicit_fs_thd_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);kk_string_dup(x_0_10450, _ctx);}, {}, _ctx)
  kk_string_t _y_x10088_323 = kk_string_unbox(_b_x310); /*string*/;
  kk_string_t _x_x892 = kk_std_core_tuple_tuple5_fs__mlift_show_10167(x_0_10450, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_thd_fs_show, x, _y_x10088_323, _ctx); /*string*/
  return kk_string_box(_x_x892);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_show_fun896__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field4_fs_show;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_std_core_types__tuple5 x;
  kk_string_t x_0_10450;
  kk_string_t x_1_10453;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun896(kk_function_t _fself, kk_box_t _b_x312, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_show_fun896(kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_string_t x_0_10450, kk_string_t x_1_10453, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun896__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_show_fun896__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_show_fun896, kk_context());
  _self->_implicit_fs_field4_fs_show = _implicit_fs_field4_fs_show;
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->x = x;
  _self->x_0_10450 = x_0_10450;
  _self->x_1_10453 = x_1_10453;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun896(kk_function_t _fself, kk_box_t _b_x312, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun896__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_show_fun896__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field4_fs_show = _self->_implicit_fs_field4_fs_show; /* (3702) -> 3703 string */
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_string_t x_0_10450 = _self->x_0_10450; /* string */
  kk_string_t x_1_10453 = _self->x_1_10453; /* string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field4_fs_show, _ctx);kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);kk_string_dup(x_0_10450, _ctx);kk_string_dup(x_1_10453, _ctx);}, {}, _ctx)
  kk_string_t _y_x10089_324 = kk_string_unbox(_b_x312); /*string*/;
  kk_string_t _x_x897 = kk_std_core_tuple_tuple5_fs__mlift_show_10166(x_0_10450, x_1_10453, _implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, x, _y_x10089_324, _ctx); /*string*/
  return kk_string_box(_x_x897);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_show_fun901__t {
  struct kk_function_s _base;
  kk_function_t _implicit_fs_field5_fs_show;
  kk_std_core_types__tuple5 x;
  kk_string_t x_0_10450;
  kk_string_t x_1_10453;
  kk_string_t x_2_10456;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun901(kk_function_t _fself, kk_box_t _b_x314, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_show_fun901(kk_function_t _implicit_fs_field5_fs_show, kk_std_core_types__tuple5 x, kk_string_t x_0_10450, kk_string_t x_1_10453, kk_string_t x_2_10456, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun901__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_show_fun901__t, 6, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_show_fun901, kk_context());
  _self->_implicit_fs_field5_fs_show = _implicit_fs_field5_fs_show;
  _self->x = x;
  _self->x_0_10450 = x_0_10450;
  _self->x_1_10453 = x_1_10453;
  _self->x_2_10456 = x_2_10456;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun901(kk_function_t _fself, kk_box_t _b_x314, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun901__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_show_fun901__t*, _fself, _ctx);
  kk_function_t _implicit_fs_field5_fs_show = _self->_implicit_fs_field5_fs_show; /* (3704) -> 3703 string */
  kk_std_core_types__tuple5 x = _self->x; /* (3699, 3700, 3701, 3702, 3704) */
  kk_string_t x_0_10450 = _self->x_0_10450; /* string */
  kk_string_t x_1_10453 = _self->x_1_10453; /* string */
  kk_string_t x_2_10456 = _self->x_2_10456; /* string */
  kk_drop_match(_self, {kk_function_dup(_implicit_fs_field5_fs_show, _ctx);kk_std_core_types__tuple5_dup(x, _ctx);kk_string_dup(x_0_10450, _ctx);kk_string_dup(x_1_10453, _ctx);kk_string_dup(x_2_10456, _ctx);}, {}, _ctx)
  kk_string_t _y_x10090_325 = kk_string_unbox(_b_x314); /*string*/;
  kk_string_t _x_x902 = kk_std_core_tuple_tuple5_fs__mlift_show_10165(x_0_10450, x_1_10453, x_2_10456, _implicit_fs_field5_fs_show, x, _y_x10090_325, _ctx); /*string*/
  return kk_string_box(_x_x902);
}


// lift anonymous function
struct kk_std_core_tuple_tuple5_fs_show_fun906__t {
  struct kk_function_s _base;
  kk_string_t x_0_10450;
  kk_string_t x_1_10453;
  kk_string_t x_2_10456;
  kk_string_t x_3_10459;
};
static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun906(kk_function_t _fself, kk_box_t _b_x316, kk_context_t* _ctx);
static kk_function_t kk_std_core_tuple_tuple5_fs_new_show_fun906(kk_string_t x_0_10450, kk_string_t x_1_10453, kk_string_t x_2_10456, kk_string_t x_3_10459, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun906__t* _self = kk_function_alloc_as(struct kk_std_core_tuple_tuple5_fs_show_fun906__t, 5, _ctx);
  _self->_base.fun = kk_kkfun_ptr_box(&kk_std_core_tuple_tuple5_fs_show_fun906, kk_context());
  _self->x_0_10450 = x_0_10450;
  _self->x_1_10453 = x_1_10453;
  _self->x_2_10456 = x_2_10456;
  _self->x_3_10459 = x_3_10459;
  return kk_datatype_from_base(&_self->_base, kk_context());
}

static kk_box_t kk_std_core_tuple_tuple5_fs_show_fun906(kk_function_t _fself, kk_box_t _b_x316, kk_context_t* _ctx) {
  struct kk_std_core_tuple_tuple5_fs_show_fun906__t* _self = kk_function_as(struct kk_std_core_tuple_tuple5_fs_show_fun906__t*, _fself, _ctx);
  kk_string_t x_0_10450 = _self->x_0_10450; /* string */
  kk_string_t x_1_10453 = _self->x_1_10453; /* string */
  kk_string_t x_2_10456 = _self->x_2_10456; /* string */
  kk_string_t x_3_10459 = _self->x_3_10459; /* string */
  kk_drop_match(_self, {kk_string_dup(x_0_10450, _ctx);kk_string_dup(x_1_10453, _ctx);kk_string_dup(x_2_10456, _ctx);kk_string_dup(x_3_10459, _ctx);}, {}, _ctx)
  kk_string_t _y_x10091_326 = kk_string_unbox(_b_x316); /*string*/;
  kk_string_t _x_x907 = kk_std_core_tuple_tuple5_fs__mlift_show_10164(x_0_10450, x_1_10453, x_2_10456, x_3_10459, _y_x10091_326, _ctx); /*string*/
  return kk_string_box(_x_x907);
}

kk_string_t kk_std_core_tuple_tuple5_fs_show(kk_std_core_types__tuple5 x, kk_function_t _implicit_fs_fst_fs_show, kk_function_t _implicit_fs_snd_fs_show, kk_function_t _implicit_fs_thd_fs_show, kk_function_t _implicit_fs_field4_fs_show, kk_function_t _implicit_fs_field5_fs_show, kk_context_t* _ctx) { /* forall<a,b,c,d,e,a1> (x : (a, b, c, d, a1), ?fst/show : (a) -> e string, ?snd/show : (b) -> e string, ?thd/show : (c) -> e string, ?field4/show : (d) -> e string, ?field5/show : (a1) -> e string) -> e string */ 
  kk_string_t x_0_10450;
  kk_box_t _x_x883;
  {
    struct kk_std_core_types_Tuple5* _con_x884 = kk_std_core_types__as_Tuple5(x, _ctx);
    kk_box_t _x = _con_x884->fst;
    kk_box_dup(_x, _ctx);
    _x_x883 = _x; /*3699*/
  }
  x_0_10450 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_fst_fs_show, (_implicit_fs_fst_fs_show, _x_x883, _ctx), _ctx); /*string*/
  if (kk_yielding(kk_context())) {
    kk_string_drop(x_0_10450, _ctx);
    kk_box_t _x_x885 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_show_fun886(_implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_snd_fs_show, _implicit_fs_thd_fs_show, x, _ctx), _ctx); /*2419*/
    return kk_string_unbox(_x_x885);
  }
  {
    kk_string_t x_1_10453;
    kk_box_t _x_x888;
    {
      struct kk_std_core_types_Tuple5* _con_x889 = kk_std_core_types__as_Tuple5(x, _ctx);
      kk_box_t _x_0 = _con_x889->snd;
      kk_box_dup(_x_0, _ctx);
      _x_x888 = _x_0; /*3700*/
    }
    x_1_10453 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_snd_fs_show, (_implicit_fs_snd_fs_show, _x_x888, _ctx), _ctx); /*string*/
    if (kk_yielding(kk_context())) {
      kk_string_drop(x_1_10453, _ctx);
      kk_box_t _x_x890 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_show_fun891(_implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, _implicit_fs_thd_fs_show, x, x_0_10450, _ctx), _ctx); /*2419*/
      return kk_string_unbox(_x_x890);
    }
    {
      kk_string_t x_2_10456;
      kk_box_t _x_x893;
      {
        struct kk_std_core_types_Tuple5* _con_x894 = kk_std_core_types__as_Tuple5(x, _ctx);
        kk_box_t _x_1 = _con_x894->thd;
        kk_box_dup(_x_1, _ctx);
        _x_x893 = _x_1; /*3701*/
      }
      x_2_10456 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_thd_fs_show, (_implicit_fs_thd_fs_show, _x_x893, _ctx), _ctx); /*string*/
      if (kk_yielding(kk_context())) {
        kk_string_drop(x_2_10456, _ctx);
        kk_box_t _x_x895 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_show_fun896(_implicit_fs_field4_fs_show, _implicit_fs_field5_fs_show, x, x_0_10450, x_1_10453, _ctx), _ctx); /*2419*/
        return kk_string_unbox(_x_x895);
      }
      {
        kk_string_t x_3_10459;
        kk_box_t _x_x898;
        {
          struct kk_std_core_types_Tuple5* _con_x899 = kk_std_core_types__as_Tuple5(x, _ctx);
          kk_box_t _x_2 = _con_x899->field4;
          kk_box_dup(_x_2, _ctx);
          _x_x898 = _x_2; /*3702*/
        }
        x_3_10459 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_field4_fs_show, (_implicit_fs_field4_fs_show, _x_x898, _ctx), _ctx); /*string*/
        if (kk_yielding(kk_context())) {
          kk_string_drop(x_3_10459, _ctx);
          kk_box_t _x_x900 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_show_fun901(_implicit_fs_field5_fs_show, x, x_0_10450, x_1_10453, x_2_10456, _ctx), _ctx); /*2419*/
          return kk_string_unbox(_x_x900);
        }
        {
          kk_string_t x_4_10462;
          kk_box_t _x_x903;
          {
            struct kk_std_core_types_Tuple5* _con_x904 = kk_std_core_types__as_Tuple5(x, _ctx);
            kk_box_t _pat_0_3_0 = _con_x904->fst;
            kk_box_t _pat_1_3 = _con_x904->snd;
            kk_box_t _pat_2_3 = _con_x904->thd;
            kk_box_t _pat_3_3 = _con_x904->field4;
            kk_box_t _x_3 = _con_x904->field5;
            if kk_likely(kk_datatype_ptr_is_unique(x, _ctx)) {
              kk_box_drop(_pat_3_3, _ctx);
              kk_box_drop(_pat_2_3, _ctx);
              kk_box_drop(_pat_1_3, _ctx);
              kk_box_drop(_pat_0_3_0, _ctx);
              kk_datatype_ptr_free(x, _ctx);
            }
            else {
              kk_box_dup(_x_3, _ctx);
              kk_datatype_ptr_decref(x, _ctx);
            }
            _x_x903 = _x_3; /*3704*/
          }
          x_4_10462 = kk_function_call(kk_string_t, (kk_function_t, kk_box_t, kk_context_t*), _implicit_fs_field5_fs_show, (_implicit_fs_field5_fs_show, _x_x903, _ctx), _ctx); /*string*/
          if (kk_yielding(kk_context())) {
            kk_string_drop(x_4_10462, _ctx);
            kk_box_t _x_x905 = kk_std_core_hnd_yield_extend(kk_std_core_tuple_tuple5_fs_new_show_fun906(x_0_10450, x_1_10453, x_2_10456, x_3_10459, _ctx), _ctx); /*2419*/
            return kk_string_unbox(_x_x905);
          }
          {
            kk_string_t _x_x908;
            kk_define_string_literal(, _s_x909, 1, "(", _ctx)
            _x_x908 = kk_string_dup(_s_x909, _ctx); /*string*/
            kk_string_t _x_x910;
            kk_string_t _x_x911;
            kk_string_t _x_x912;
            kk_define_string_literal(, _s_x913, 1, ",", _ctx)
            _x_x912 = kk_string_dup(_s_x913, _ctx); /*string*/
            kk_string_t _x_x914;
            kk_string_t _x_x915;
            kk_string_t _x_x916;
            kk_define_string_literal(, _s_x917, 1, ",", _ctx)
            _x_x916 = kk_string_dup(_s_x917, _ctx); /*string*/
            kk_string_t _x_x918;
            kk_string_t _x_x919;
            kk_string_t _x_x920;
            kk_define_string_literal(, _s_x921, 1, ",", _ctx)
            _x_x920 = kk_string_dup(_s_x921, _ctx); /*string*/
            kk_string_t _x_x922;
            kk_string_t _x_x923;
            kk_string_t _x_x924;
            kk_define_string_literal(, _s_x925, 1, ",", _ctx)
            _x_x924 = kk_string_dup(_s_x925, _ctx); /*string*/
            kk_string_t _x_x926;
            kk_string_t _x_x927;
            kk_define_string_literal(, _s_x928, 1, ")", _ctx)
            _x_x927 = kk_string_dup(_s_x928, _ctx); /*string*/
            _x_x926 = kk_std_core_types__lp__plus__plus__rp_(x_4_10462, _x_x927, _ctx); /*string*/
            _x_x923 = kk_std_core_types__lp__plus__plus__rp_(_x_x924, _x_x926, _ctx); /*string*/
            _x_x922 = kk_std_core_types__lp__plus__plus__rp_(x_3_10459, _x_x923, _ctx); /*string*/
            _x_x919 = kk_std_core_types__lp__plus__plus__rp_(_x_x920, _x_x922, _ctx); /*string*/
            _x_x918 = kk_std_core_types__lp__plus__plus__rp_(x_2_10456, _x_x919, _ctx); /*string*/
            _x_x915 = kk_std_core_types__lp__plus__plus__rp_(_x_x916, _x_x918, _ctx); /*string*/
            _x_x914 = kk_std_core_types__lp__plus__plus__rp_(x_1_10453, _x_x915, _ctx); /*string*/
            _x_x911 = kk_std_core_types__lp__plus__plus__rp_(_x_x912, _x_x914, _ctx); /*string*/
            _x_x910 = kk_std_core_types__lp__plus__plus__rp_(x_0_10450, _x_x911, _ctx); /*string*/
            return kk_std_core_types__lp__plus__plus__rp_(_x_x908, _x_x910, _ctx);
          }
        }
      }
    }
  }
}

// initialization
void kk_std_core_tuple__init(kk_context_t* _ctx){
  static bool _kk_initialized = false;
  if (_kk_initialized) return;
  _kk_initialized = true;
  kk_std_core_types__init(_ctx);
  kk_std_core_hnd__init(_ctx);
  #if defined(KK_CUSTOM_INIT)
    KK_CUSTOM_INIT (_ctx);
  #endif
}

// termination
void kk_std_core_tuple__done(kk_context_t* _ctx){
  static bool _kk_done = false;
  if (_kk_done) return;
  _kk_done = true;
  #if defined(KK_CUSTOM_DONE)
    KK_CUSTOM_DONE (_ctx);
  #endif
  kk_std_core_hnd__done(_ctx);
  kk_std_core_types__done(_ctx);
}
