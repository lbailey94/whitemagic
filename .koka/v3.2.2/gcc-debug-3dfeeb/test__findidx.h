#pragma once
#ifndef kk_test__findidx_H
#define kk_test__findidx_H
// Koka generated module: test_findidx, koka version: 3.2.2, platform: 64-bit
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

kk_integer_t kk_test__findidx_find_index(kk_std_core_types__list list, kk_string_t target, kk_context_t* _ctx); /* (list : list<string>, target : string) -> int */ 

kk_unit_t kk_test__findidx_main(kk_context_t* _ctx); /* () -> console/console () */ 

void kk_test__findidx__init(kk_context_t* _ctx);


void kk_test__findidx__done(kk_context_t* _ctx);

#endif // header
