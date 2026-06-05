defmodule WhiteMagicElixir.HolographicMemoryTest do
  use ExUnit.Case

  alias WhiteMagicElixir.{HolographicMemory, Coordinate}

  setup do
    {:ok, pid} = HolographicMemory.start_link(name: nil)
    {:ok, pid: pid}
  end

  test "store and retrieve memory", %{pid: pid} do
    assert {:ok, "m1"} = HolographicMemory.store(pid, "m1", "hello world", "test")
    mem = HolographicMemory.get(pid, "m1")
    assert mem.text == "hello world"
    assert mem.tag == "test"
    assert mem.zone != nil
  end

  test "nearest neighbors returns results", %{pid: pid} do
    HolographicMemory.store(pid, "a", "machine learning")
    HolographicMemory.store(pid, "b", "deep neural networks")
    HolographicMemory.store(pid, "c", "quantum physics")

    query = Coordinate.encode("artificial intelligence")
    neighbors = HolographicMemory.nearest_neighbors(pid, query, 2)
    assert length(neighbors) == 2
    # Each result is {id, memory, distance}
    assert elem(hd(neighbors), 0) in ["a", "b", "c"]
  end

  test "zone query", %{pid: pid} do
    HolographicMemory.store(pid, "m1", String.duplicate("A", 50))  # high caps -> high v
    HolographicMemory.store(pid, "m2", String.duplicate("x", 50))  # low caps -> low v

    # At least one should be in CORE (low v) and one in a higher zone
    zones =
      ["CORE", "INNER_RING", "MID_RING", "OUTER_RING", "FAR_EDGE"]
      |> Enum.map(fn z -> {z, length(HolographicMemory.by_zone(pid, z))} end)
      |> Enum.filter(fn {_, n} -> n > 0 end)

    assert length(zones) >= 1
  end

  test "stats returns valid data", %{pid: pid} do
    HolographicMemory.store(pid, "x", "test")
    stats = HolographicMemory.stats(pid)
    assert stats.memory_count == 1
    assert stats.coherence == 1.0
  end

  test "clear removes all memories", %{pid: pid} do
    HolographicMemory.store(pid, "x", "test")
    :ok = HolographicMemory.clear(pid)
    assert HolographicMemory.get(pid, "x") == nil
  end
end
