#pragma once
#ifndef kk_test__lt_H
#define kk_test__lt_H
// Koka generated module: test_lt, koka version: 3.2.2, platform: 64-bit
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

// value declarations

static inline bool kk_test__lt_is__neg(kk_integer_t n, kk_context_t* _ctx) { /* (n : int) -> bool */ 
  bool _brw_x0 = kk_integer_lt_borrow(n,(kk_integer_from_small(0)),kk_context()); /*bool*/;
  kk_integer_drop(n, _ctx);
  return _brw_x0;
}

static inline kk_unit_t kk_test__lt_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  bool b_10001 = kk_integer_lt_borrow((kk_integer_from_small(5)),(kk_integer_from_small(0)),kk_context()); /*bool*/;
  kk_string_t _x_x1;
  if (b_10001) {
    kk_define_string_literal(, _s_x2, 4, "True", _ctx)
    _x_x1 = kk_string_dup(_s_x2, _ctx); /*string*/
  }
  else {
    kk_define_string_literal(, _s_x3, 5, "False", _ctx)
    _x_x1 = kk_string_dup(_s_x3, _ctx); /*string*/
  }
  kk_std_core_console_printsln(_x_x1, _ctx); return kk_Unit;
}

void kk_test__lt__init(kk_context_t* _ctx);


void kk_test__lt__done(kk_context_t* _ctx);

#endif // header
