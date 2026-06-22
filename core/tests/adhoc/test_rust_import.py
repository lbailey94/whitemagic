import whitemagic_rust

print(dir(whitemagic_rust))
if hasattr(whitemagic_rust, 'simhash_lsh'):
    print("simhash_lsh found")
else:
    print("simhash_lsh NOT found")
