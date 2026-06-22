from whitemagic.optimization.rust_accelerators import _rs

print(f"_rs type: {type(_rs)}")
print(f"Has search_build_index: {hasattr(_rs, 'search_build_index')}")
