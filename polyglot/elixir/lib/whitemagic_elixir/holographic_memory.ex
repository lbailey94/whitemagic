defmodule WhiteMagicElixir.HolographicMemory do
  @moduledoc """
  GenServer for 5D holographic memory operations.

  Maintains an in-memory index of memories with 5D holographic coordinates,
  supporting spatial queries, zone-based retrieval, and constellation detection.

  ## Usage

      iex> {:ok, pid} = WhiteMagicElixir.HolographicMemory.start_link()
      iex> WhiteMagicElixir.HolographicMemory.store(pid, "memory_1", "Hello world", "greeting")
      iex> WhiteMagicElixir.HolographicMemory.nearest_neighbors(pid, query_coord, 5)
  """

  use GenServer

  alias WhiteMagicElixir.Coordinate

  defstruct memories: %{}, index: %{}, next_id: 1

  @doc "Start the holographic memory server."
  def start_link(opts \\ []) do
    name = opts[:name]
    if name do
      GenServer.start_link(__MODULE__, opts, name: name)
    else
      GenServer.start_link(__MODULE__, opts)
    end
  end

  @doc "Store a memory with automatic 5D coordinate encoding."
  def store(pid, id, text, tag \\ nil) do
    GenServer.call(pid, {:store, id, text, tag})
  end

  @doc "Retrieve a memory by ID."
  def get(pid, id) do
    GenServer.call(pid, {:get, id})
  end

  @doc "Find k nearest neighbors to a query coordinate."
  def nearest_neighbors(pid, query, k \\ 5) do
    GenServer.call(pid, {:nearest, query, k})
  end

  @doc "Find nearest neighbors to a text string (auto-encoded)."
  def nearest_neighbors_text(pid, text, k \\ 5) do
    coord = Coordinate.encode(text)
    nearest_neighbors(pid, coord, k)
  end

  @doc "Get all memories in a galactic zone."
  def by_zone(pid, zone) do
    GenServer.call(pid, {:by_zone, zone})
  end

  @doc "Detect constellations (clusters) in memory space."
  def constellations(pid, threshold \\ 0.5, min_size \\ 3) do
    GenServer.call(pid, {:constellations, threshold, min_size})
  end

  @doc "Return statistics: count, zone distribution, coherence."
  def stats(pid) do
    GenServer.call(pid, :stats)
  end

  @doc "Clear all memories."
  def clear(pid) do
    GenServer.call(pid, :clear)
  end

  # ---------------------------------------------------------------------------
  # GenServer callbacks
  # ---------------------------------------------------------------------------

  @impl true
  def init(_opts) do
    {:ok, %__MODULE__{}}
  end

  @impl true
  def handle_call({:store, id, text, tag}, _from, state) do
    coord = Coordinate.encode(text)
    memory = %{
      id: id,
      text: text,
      tag: tag,
      coord: coord,
      zone: Coordinate.zone(coord),
      lsh: Coordinate.lsh(coord),
      inserted_at: DateTime.utc_now()
    }

    new_memories = Map.put(state.memories, id, memory)
    # Also index by LSH bucket for fast spatial filtering
    bucket = Coordinate.lsh(coord)
    bucket_entries = Map.get(state.index, bucket, [])
    new_index = Map.put(state.index, bucket, [id | bucket_entries])

    {:reply, {:ok, id}, %{state | memories: new_memories, index: new_index}}
  end

  @impl true
  def handle_call({:get, id}, _from, state) do
    {:reply, Map.get(state.memories, id), state}
  end

  @impl true
  def handle_call({:nearest, query, k}, _from, state) do
    results =
      state.memories
      |> Enum.map(fn {id, mem} ->
        {id, mem, Coordinate.distance(query, mem.coord)}
      end)
      |> Enum.sort_by(fn {_, _, dist} -> dist end)
      |> Enum.take(k)

    {:reply, results, state}
  end

  @impl true
  def handle_call({:by_zone, zone}, _from, state) do
    matches =
      state.memories
      |> Enum.filter(fn {_, mem} -> mem.zone == zone end)
      |> Enum.map(fn {_, mem} -> mem end)

    {:reply, matches, state}
  end

  @impl true
  def handle_call({:constellations, threshold, min_size}, _from, state) do
    coords = Enum.map(state.memories, fn {_, mem} -> mem.coord end)
    ids = Enum.map(state.memories, fn {id, _} -> id end)
    n = length(coords)

    if n < min_size do
      {:reply, [], state}
    else
      clusters = find_clusters(coords, ids, threshold, min_size)
      {:reply, clusters, state}
    end
  end

  @impl true
  def handle_call(:stats, _from, state) do
    count = map_size(state.memories)
    zones = state.memories |> Enum.map(fn {_, m} -> m.zone end) |> Enum.frequencies()
    coords = state.memories |> Enum.map(fn {_, m} -> m.coord end)
    coherence = if count >= 2, do: Coordinate.coherence(coords), else: 1.0

    stats = %{
      memory_count: count,
      zone_distribution: zones,
      coherence: Float.round(coherence, 6),
      index_buckets: map_size(state.index)
    }

    {:reply, stats, state}
  end

  @impl true
  def handle_call(:clear, _from, _state) do
    {:reply, :ok, %__MODULE__{}}
  end

  # ---------------------------------------------------------------------------
  # Clustering (single-linkage via Union-Find)
  # ---------------------------------------------------------------------------

  defp find_clusters(coords, ids, threshold, min_size) do
    n = length(coords)

    # Build distance graph edges
    edges =
      for i <- 0..max(0, n - 2),
          j <- (i + 1)..(n - 1),
          Coordinate.distance(Enum.at(coords, i), Enum.at(coords, j)) <= threshold,
          do: {i, j}

    # Union-Find
    parent = Enum.into(0..(n - 1), %{}, fn i -> {i, i} end)
    rank = Enum.into(0..(n - 1), %{}, fn i -> {i, 0} end)

    parent =
      Enum.reduce(edges, parent, fn {i, j}, p ->
        union(p, rank, i, j) |> elem(0)
      end)

    # Collect components
    components =
      Enum.group_by(0..(n - 1), fn i -> find(parent, i) end, fn i -> Enum.at(ids, i) end)

    components
    |> Enum.map(fn {_, members} -> members end)
    |> Enum.filter(fn members -> length(members) >= min_size end)
    |> Enum.sort_by(fn members -> -length(members) end)
  end

  defp find(parent, i) do
    if Map.get(parent, i) == i do
      i
    else
      root = find(parent, Map.get(parent, i))
      root
    end
  end

  defp union(parent, rank, i, j) do
    ri = find(parent, i)
    rj = find(parent, j)

    if ri == rj do
      {parent, rank}
    else
      ri_rank = Map.get(rank, ri)
      rj_rank = Map.get(rank, rj)

      cond do
        ri_rank < rj_rank ->
          {Map.put(parent, ri, rj), rank}
        ri_rank > rj_rank ->
          {Map.put(parent, rj, ri), rank}
        true ->
          {Map.put(parent, rj, ri), Map.put(rank, ri, ri_rank + 1)}
      end
    end
  end
end
