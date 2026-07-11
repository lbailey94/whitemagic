#!/usr/bin/env julia
# WhiteMagic Julia JSON stdio bridge
# Reads JSON requests from stdin, writes JSON responses to stdout

using JSON

function handle(req)
    method = req["method"]
    p = req["params"]

    if method == "ping"
        return Dict("status" => "ok", "backend" => "julia")

    elseif method == "encode"
        coord = HolographicMemory.encode_5d(p["text"])
        return Dict(
            "status" => "ok",
            "x" => coord[1], "y" => coord[2], "z" => coord[3],
            "w" => coord[4], "v" => coord[5],
            "zone" => HolographicMemory.zone_of(coord)
        )

    elseif method == "nearest_neighbors"
        query = HolographicMemory.encode_5d(p["query"])
        coords = [HolographicMemory.encode_5d(t) for t in p["texts"]]
        k = get(p, "k", 3)
        # Use KD-tree for large coordinate sets (O(log n) vs O(n))
        if length(coords) >= 64
            result = HolographicMemory.nearest_neighbors_kdtree(query, coords, k)
        else
            result = HolographicMemory.nearest_neighbors(query, coords, k)
        end
        return Dict(
            "status" => "ok",
            "results" => [Dict("index" => r[1], "distance" => r[2]) for r in result]
        )

    elseif method == "constellation_detect"
        coords = [HolographicMemory.encode_5d(t) for t in p["texts"]]
        threshold = get(p, "threshold", 0.8)
        min_size = get(p, "min_size", 2)
        clusters = HolographicMemory.constellation_detect(coords, threshold, min_size)
        return Dict(
            "status" => "ok",
            "clusters" => [c for c in clusters]
        )

    elseif method == "coherence"
        coords = [HolographicMemory.encode_5d(t) for t in p["texts"]]
        score = HolographicMemory.coherence_score(coords)
        return Dict("status" => "ok", "coherence" => score)

    else
        return Dict("status" => "error", "error" => "Unknown method: $method")
    end
end

# Main loop: read JSON line, handle, write JSON line

# Warmup: trigger JIT for hot paths (reduces first-request latency from 9.5s to 3s)
HolographicMemory.encode_5d("warmup")
c1 = HolographicMemory.encode_5d("w")
c2 = HolographicMemory.encode_5d("x")
HolographicMemory.nearest_neighbors(c1, [c2], 1)
HolographicMemory.zone_of(c1)
# Warmup KD-tree path with enough points to trigger it
many_coords = [HolographicMemory.encode_5d("warmup_$i") for i in 1:70]
HolographicMemory.nearest_neighbors_kdtree(c1, many_coords, 5)

while !eof(stdin)
    line = readline(stdin)
    isempty(line) && continue
    try
        req = JSON.parse(line)
        resp = handle(req)
        println(stdout, JSON.json(resp))
        flush(stdout)
    catch e
        err = Dict("status" => "error", "error" => string(e))
        println(stdout, JSON.json(err))
        flush(stdout)
    end
end
