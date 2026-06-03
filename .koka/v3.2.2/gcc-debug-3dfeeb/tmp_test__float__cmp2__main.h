#pragma once
#ifndef kk_tmp_test__float__cmp2__main_H
#define kk_tmp_test__float__cmp2__main_H
// Koka generated module: tmp/test_float_cmp2/@main, koka version: 3.2.2, platform: 64-bit
#include <kklib.h>
#include "std_core_undiv.h"
#include "std_text_parse.h"
#include "std_num_int32.h"
#include "std_num_int64.h"
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
#include "std_num_float64.h"
#include "std_core.h"
#include "test__float__cmp2.h"

// type declarations

// value declarations

static inline kk_unit_t kk_tmp_test__float__cmp2__main__expr(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t s_10000;
  bool _match_x1 = ((0x1p-1) < (0x1.999999999999ap-2)); /*bool*/;
  if (_match_x1) {
    kk_define_string_literal(, _s_x2, 3, "low", _ctx)
    s_10000 = kk_string_dup(_s_x2, _ctx); /*string*/
  }
  else {
    kk_define_string_literal(, _s_x3, 4, "high", _ctx)
    s_10000 = kk_string_dup(_s_x3, _ctx); /*string*/
  }
  kk_std_core_console_printsln(s_10000, _ctx); return kk_Unit;
}

static inline kk_unit_t kk_tmp_test__float__cmp2__main__main(kk_context_t* _ctx) { /* () -> <st<global>,console/console,div,fsys,ndet,net,ui> () */ 
  kk_string_t s_10000;
  bool _match_x0 = ((0x1p-1) < (0x1.999999999999ap-2)); /*bool*/;
  if (_match_x0) {
    kk_define_string_literal(, _s_x4, 3, "low", _ctx)
    s_10000 = kk_string_dup(_s_x4, _ctx); /*string*/
  }
  else {
    kk_define_string_literal(, _s_x5, 4, "high", _ctx)
    s_10000 = kk_string_dup(_s_x5, _ctx); /*string*/
  }
  kk_std_core_console_printsln(s_10000, _ctx); return kk_Unit;
}

void kk_tmp_test__float__cmp2__main__init(kk_context_t* _ctx);


void kk_tmp_test__float__cmp2__main__done(kk_context_t* _ctx);

#endif // header
