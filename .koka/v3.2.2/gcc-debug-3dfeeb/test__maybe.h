#pragma once
#ifndef kk_test__maybe_H
#define kk_test__maybe_H
// Koka generated module: test_maybe, koka version: 3.2.2, platform: 64-bit
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

static inline kk_unit_t kk_test__maybe_main(kk_context_t* _ctx) { /* () -> console/console () */ 
  kk_string_t s_10000 = kk_std_core_int_show(kk_integer_from_small(5), _ctx); /*string*/;
  kk_std_core_console_printsln(s_10000, _ctx); return kk_Unit;
}

void kk_test__maybe__init(kk_context_t* _ctx);


void kk_test__maybe__done(kk_context_t* _ctx);

#endif // header
