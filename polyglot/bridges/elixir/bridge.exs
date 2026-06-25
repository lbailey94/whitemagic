# WhiteMagic Elixir JSON stdio bridge
# Uses only Coordinate pure functions (no GenServer needed)

defmodule WhiteMagic.Bridge do
  alias WhiteMagicElixir.Coordinate

  def handle(req) do
    method = req["method"]
    p = req["params"]

    case method do
      "ping" ->
        %{status: "ok", backend: "elixir"}

      "encode" ->
        coord = Coordinate.encode(p["text"])
        %{
          status: "ok",
          x: coord.x, y: coord.y, z: coord.z,
          w: coord.w, v: coord.v,
          zone: Coordinate.zone(coord)
        }

      "nearest_neighbors" ->
        query = Coordinate.encode(p["query"])
        coords = Enum.map(p["texts"], &Coordinate.encode/1)
        k = p["k"] || 3
        result = nearest_neighbors(query, coords, k)
        %{
          status: "ok",
          results: Enum.map(result, fn {idx, dist} ->
            %{index: idx, distance: dist}
          end)
        }

      "distance" ->
        a = Coordinate.encode(p["a"])
        b = Coordinate.encode(p["b"])
        %{status: "ok", distance: Coordinate.distance(a, b)}

      "coherence" ->
        coords = Enum.map(p["texts"], &Coordinate.encode/1)
        %{status: "ok", coherence: Coordinate.coherence(coords)}

      _ ->
        %{status: "error", error: "Unknown method: #{method}"}
    end
  end

  defp nearest_neighbors(query, coords, k) do
    coords
    |> Enum.with_index()
    |> Enum.map(fn {c, i} -> {i, Coordinate.distance(query, c)} end)
    |> Enum.sort_by(fn {_, d} -> d end)
    |> Enum.take(k)
  end

  def loop do
    case IO.read(:line) do
      :eof -> :ok
      line when is_binary(line) ->
        text = String.trim(line)
        if text == "" do
          loop()
        else
          try do
            req = Jason.decode!(text)
            resp = handle(req)
            IO.puts(Jason.encode!(resp))
          rescue
            e ->
              err = %{status: "error", error: Exception.message(e)}
              IO.puts(Jason.encode!(err))
          end
          loop()
        end
    end
  end
end

# Warmup: trigger module loading before serving requests
WhiteMagicElixir.Coordinate.encode("warmup")

WhiteMagic.Bridge.loop()
