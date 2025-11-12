# Latest Independent Review Fixes

**Date**: November 3, 2025  
**Status**: ✅ COMPLETE

---

## Issues Found & Fixed

### 1. ✅ Consolidation API TypeError (HIGH)

**Problem**: `/api/v1/consolidate` passed `min_age_days` to method that didn't accept it
**Error**: `TypeError: consolidate_short_term() got an unexpected keyword argument 'min_age_days'`

**Fix**:
- Added `min_age_days: Optional[int] = None` parameter to `consolidate_short_term()`
- Method now uses this parameter to override default retention period
- API call works without error

**Files Changed**:
- `whitemagic/core.py` - Added parameter and logic
- `whitemagic/api/app.py` - Already passing it (now works)

---

### 2. ✅ Promotion Count Always Zero (MEDIUM)

**Problem**: API looked for `result["promoted"]` but manager returns `result["auto_promoted"]`  
**Impact**: Users always saw 0 promotions even when memories were promoted

**Fix**:
- Changed API to use `result.get("auto_promoted", 0)` instead of `result.get("promoted", 0)`
- Success message now shows correct promotion count

**Files Changed**:
- `whitemagic/api/app.py` - Fixed key lookup (2 locations)

---

## Tests Added

Created `tests/test_consolidation_fix.py`:
- ✅ `test_consolidate_short_term_accepts_min_age_days` - Parameter accepted
- ✅ `test_consolidate_short_term_uses_min_age_days` - Parameter actually works
- ✅ `test_consolidate_returns_auto_promoted_key` - Correct key returned
- ✅ `test_api_response_uses_auto_promoted` - API uses correct key

**Result**: 4/4 tests passing

---

## Status

**All critical issues resolved** - Ready for production deployment!
