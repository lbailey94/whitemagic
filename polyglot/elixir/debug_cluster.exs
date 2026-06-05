alias WhiteMagicElixir.{Coordinate, HolographicMemory}

{:ok, pid} = HolographicMemory.start_link(name: nil)

for i <- 1..10 do
  HolographicMemory.store(pid, "m#{i}", "memory #{i} with some text content", "test")
end

memories = HolographicMemory.stats(pid)
IO.inspect(memories)

result = HolographicMemory.constellations(pid, 0.8, 3)
IO.inspect(result)
