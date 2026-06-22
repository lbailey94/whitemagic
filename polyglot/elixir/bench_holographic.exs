alias WhiteMagicElixir.{Coordinate, HolographicMemory}

IO.puts("=== Elixir Holographic Memory Benchmark ===")

{:ok, pid} = HolographicMemory.start_link(name: nil)

# Benchmark encoding
n = 1000
t0 = System.monotonic_time()
for i <- 1..n do
  Coordinate.encode("memory #{i} with some text content")
end
t1 = System.monotonic_time()
enc_ms = System.convert_time_unit(t1 - t0, :native, :millisecond)
IO.puts("Encode #{n} texts: #{enc_ms} ms (#{Float.round(n / max(enc_ms / 1000, 0.001), 1)} texts/sec)")

# Benchmark store
t0 = System.monotonic_time()
for i <- 1..n do
  HolographicMemory.store(pid, "m#{i}", "memory #{i} with some text content", "test")
end
t1 = System.monotonic_time()
store_ms = System.convert_time_unit(t1 - t0, :native, :millisecond)
IO.puts("Store #{n} memories: #{store_ms} ms (#{Float.round(n / max(store_ms / 1000, 0.001), 1)} mems/sec)")

# Benchmark nearest neighbors
query = Coordinate.encode("search query")
t0 = System.monotonic_time()
for _ <- 1..100 do
  HolographicMemory.nearest_neighbors(pid, query, 5)
end
t1 = System.monotonic_time()
nn_ms = System.convert_time_unit(t1 - t0, :native, :millisecond)
IO.puts("NN search (100x): #{nn_ms} ms (#{Float.round(100 / max(nn_ms / 1000, 0.001), 1)} qps)")

# Benchmark constellation detection
t0 = System.monotonic_time()
HolographicMemory.constellations(pid, 0.8, 3)
t1 = System.monotonic_time()
clust_ms = System.convert_time_unit(t1 - t0, :native, :millisecond)
IO.puts("Constellation detect: #{clust_ms} ms")

# Benchmark stats
t0 = System.monotonic_time()
for _ <- 1..100 do
  HolographicMemory.stats(pid)
end
t1 = System.monotonic_time()
stats_ms = System.convert_time_unit(t1 - t0, :native, :millisecond)
IO.puts("Stats (100x): #{stats_ms} ms")

IO.puts("\n=== DONE ===")
