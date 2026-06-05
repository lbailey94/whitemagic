alias WhiteMagicElixir.{Coordinate}

coords = for i <- 1..10, do: Coordinate.encode("memory #{i}")
IO.inspect(length(coords), label: "n")
IO.inspect(coords, label: "coords")
IO.inspect(hd(coords), label: "first coord")
IO.inspect(Enum.at(coords, 0), label: "at 0")

n = length(coords)
edges = for i <- 0..(n-1), j <- (i+1)..(n-1), Coordinate.distance(Enum.at(coords, i), Enum.at(coords, j)) <= 0.8, do: {i, j}
IO.inspect(edges, label: "edges")
