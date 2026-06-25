defmodule WhiteMagicElixir.Coordinate do
  @moduledoc """
  5D Holographic coordinate for the WhiteMemory galactic system.

  Dimensions:
  - x, y, z : spatial embedding (semantic vector projection)
  - w       : temporal / recency weight (0-1)
  - v       : valence / importance (0-1)
  """

  defstruct [:x, :y, :z, :w, :v]

  @type t :: %__MODULE__{
    x: float(),
    y: float(),
    z: float(),
    w: float(),
    v: float()
  }

  @zones [
    {"CORE",        0.0, 0.2},
    {"INNER_RING",  0.2, 0.4},
    {"MID_RING",    0.4, 0.6},
    {"OUTER_RING",  0.6, 0.8},
    {"FAR_EDGE",    0.8, 1.0}
  ]

  @doc "Create a new 5D coordinate."
  def new(x \\ 0.0, y \\ 0.0, z \\ 0.0, w \\ 0.0, v \\ 0.0) do
    %__MODULE__{
      x: round_to(x, 6),
      y: round_to(y, 6),
      z: round_to(z, 6),
      w: clamp(w, 0.0, 1.0),
      v: clamp(v, 0.0, 1.0)
    }
  end

  @doc "Encode a text string into a 5D holographic coordinate."
  def encode(text, seed \\ 42) when is_binary(text) do
    if text == "" do
      new()
    else
      # Deterministic hash-based projection (no 768-iteration RNG loop)
      h = :erlang.phash2({text, seed}, 2_147_483_647)
      h2 = :erlang.phash2({text, seed + 1}, 2_147_483_647)
      h3 = :erlang.phash2({text, seed + 2}, 2_147_483_647)

      # Project hash to 3D spatial coordinates
      x = rem(h, 100_000) / 100_000.0
      y = rem(h2, 100_000) / 100_000.0
      z = rem(h3, 100_000) / 100_000.0

      # W = temporal recency
      w = clamp(String.length(text) / 1000.0, 0.0, 1.0)

      # V = valence
      caps = count_uppercase(text)
      punct = count_punct(text)
      v = clamp((caps + 2 * punct) / max(String.length(text), 1), 0.0, 1.0)

      new(x, y, z, w, v)
    end
  end

  @doc "Euclidean distance in 5D holographic space."
  def distance(a, b) do
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z
    dw = a.w - b.w
    dv = 2.0 * (a.v - b.v)
    :math.sqrt(dx * dx + dy * dy + dz * dz + dw * dw + dv * dv)
  end

  @doc "Determine galactic zone from valence (v)."
  def zone(coord) do
    Enum.find_value(@zones, "UNKNOWN", fn {name, low, high} ->
      if coord.v >= low and coord.v < high, do: name
    end)
  end

  @doc "Locality-sensitive hash for spatial indexing."
  def lsh(coord, bins \\ 8) do
    q = fn v ->
      min(bins - 1, max(0, trunc((v + 3.0) / 6.0 * bins)))
    end

    bx = q.(coord.x)
    by = q.(coord.y)
    bz = q.(coord.z)
    bw = q.(coord.w)
    bv = q.(coord.v)

    code = bx + by * bins + bz * :math.pow(bins, 2) + bw * :math.pow(bins, 3) + bv * :math.pow(bins, 4)
    "H#{trunc(code)}"
  end

  @doc "Merge multiple coordinates into a centroid."
  def merge(coords, weights \\ nil) do
    n = length(coords)
    if n == 0 do
      new()
    else
      w = weights || List.duplicate(1.0 / n, n)
      total = Enum.sum(w)
      w = Enum.map(w, &(&1 / total))

      xs = sum_product(coords, w, &(&1.x))
      ys = sum_product(coords, w, &(&1.y))
      zs = sum_product(coords, w, &(&1.z))
      ws = sum_product(coords, w, &(&1.w))
      vs = sum_product(coords, w, &(&1.v))

      new(xs, ys, zs, ws, vs)
    end
  end

  @doc "Coherence score of a cluster (0-1, higher = tighter)."
  def coherence(coords) when length(coords) < 2, do: 1.0
  def coherence(coords) do
    indexed = Enum.with_index(coords)
    pairs =
      for {a, i} <- indexed, {b, j} <- indexed, i < j, do: {a, b}

    dists = Enum.map(pairs, fn {a, b} -> distance(a, b) end)
    mean_dist = Enum.sum(dists) / length(dists)
    max(0.0, min(1.0, 1.0 - mean_dist / 2.0))
  end

  # Helpers
  defp round_to(v, digits) do
    d = :math.pow(10, digits)
    trunc(v * d) / d
  end

  defp clamp(v, lo, hi), do: max(lo, min(hi, v))

  defp count_uppercase(text) do
    count_uppercase_bin(text, 0)
  end

  defp count_uppercase_bin(<<c, rest::binary>>, acc) when c >= 65 and c <= 90 do
    count_uppercase_bin(rest, acc + 1)
  end
  defp count_uppercase_bin(<<_, rest::binary>>, acc) do
    count_uppercase_bin(rest, acc)
  end
  defp count_uppercase_bin(<<>>, acc), do: acc

  defp count_punct(text) do
    count_punct_bin(text, 0)
  end

  defp count_punct_bin(<<c, rest::binary>>, acc) when c in [33, 46, 63, 58, 59] do
    count_punct_bin(rest, acc + 1)
  end
  defp count_punct_bin(<<_, rest::binary>>, acc) do
    count_punct_bin(rest, acc)
  end
  defp count_punct_bin(<<>>, acc), do: acc

  defp sum_product(coords, weights, getter) do
    Enum.zip(coords, weights)
    |> Enum.map(fn {c, w} -> getter.(c) * w end)
    |> Enum.sum()
  end
end
