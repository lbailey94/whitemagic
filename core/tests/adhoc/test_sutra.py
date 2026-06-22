import whitemagic_rust

print("Available:", dir(whitemagic_rust.sutra_kernel))
ledger = whitemagic_rust.sutra_kernel.ZodiacLedger()
sig = ledger.record_action("test_action", "payload data", "sattvic", 1.5)
print(f"Recorded action, signature: {sig}")

engine = whitemagic_rust.sutra_kernel.DharmaEngine(1, True)
verdict = engine.evaluate_action("destructive_test", 0.5, 0.5)
print(f"Dharma Verdict: {verdict}")
