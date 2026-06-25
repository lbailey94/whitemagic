"""
    WhiteMagic Holographic Memory Core (Julia)
    ===========================================
    5D holographic coordinate encoding, spatial indexing, and galactic
    memory operations for the WhiteMagic cognitive OS.

    Designed to be called from Python via the JuliaBridge (JSON over stdio).
"""
module HolographicMemory

using LinearAlgebra
using Statistics
using Random
using StaticArrays
using NearestNeighbors
using PrecompileTools

export encode_5d,
       nearest_neighbors,
       nearest_neighbors_kdtree,
       constellation_detect,
       holographic_hash,
       zone_of,
       coherence_score,
       merge_coordinates

# Stack-allocated 5D coordinate type for zero-alloc hot paths
const Coord5D = SVector{5, Float64}

const ZONE_NAMES = ["CORE", "INNER_RING", "MID_RING", "OUTER_RING", "FAR_EDGE"]
const ZONE_BOUNDS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# ---------------------------------------------------------------------------
# 5D Holographic Coordinate Encoding
# ---------------------------------------------------------------------------

"""
    encode_5d(text::String; embedding_dim=768, seed=42) -> Coord5D

Deterministically encode a text string into a 5D holographic coordinate
(X, Y, Z, W, V) using a simple but stable hash-to-vector projection.

Dimensions:
- X,Y,Z : spatial embedding (semantic vector projection)
- W     : temporal / recency weight
- V     : valence / importance (0-1)
"""
function encode_5d(text::String; embedding_dim::Int=768, seed::Int=42)::Coord5D
    isempty(text) && return Coord5D(0.0, 0.0, 0.0, 0.0, 0.0)

    # Deterministic hash-based projection (no RNG needed — avoids MersenneTwister JIT)
    h = hash(text) ⊻ UInt64(seed)
    h2 = (h >> 8) ⊻ 0x517cc1b727220a95
    h3 = (h >> 16) ⊻ 0x6c62272e07bb0142
    h4 = (h >> 24) ⊻ 0x62b821756295c58d

    # Project hash bits to 3D spatial coordinates via signed normalization
    x = Float64(reinterpret(Int64, h) % 100000) / 100000.0
    y = Float64(reinterpret(Int64, h2) % 100000) / 100000.0
    z = Float64(reinterpret(Int64, h3) % 100000) / 100000.0

    # W = temporal recency factor (derived from character entropy)
    w = clamp(length(text) / 1000.0, 0.0, 1.0)

    # V = valence (derived from capitalisation ratio + punctuation density)
    caps = count(isuppercase, text)
    punct = count(c -> c in "!?.;:", text)
    v = clamp((caps + 2 * punct) / max(length(text), 1), 0.0, 1.0)

    Coord5D(round(x; digits=6), round(y; digits=6), round(z; digits=6), round(w; digits=6), round(v; digits=6))
end

"""
    encode_5d(embedding::Vector{Float64}; w=0.5, v=0.5) -> Coord5D

Encode a pre-computed embedding vector into 5D holographic space.
"""
function encode_5d(embedding::Vector{Float64}; w::Float64=0.5, v::Float64=0.5)::Coord5D
    n = length(embedding)
    n == 0 && return Coord5D(0.0, 0.0, 0.0, w, v)

    emb = embedding ./ norm(embedding)
    dim = min(n, 768)

    x = sum(emb[1:min(256, dim)]) / 16.0
    y = sum(emb[max(1, min(257, dim)):min(512, dim)]) / 16.0
    z = sum(emb[max(1, min(513, dim)):dim]) / 16.0

    Coord5D(round(x; digits=6), round(y; digits=6), round(z; digits=6), clamp(w, 0.0, 1.0), clamp(v, 0.0, 1.0))
end

# ---------------------------------------------------------------------------
# Spatial Queries
# ---------------------------------------------------------------------------

"""
    euclidean_5d(a::Coord5D, b::Coord5D) -> Float64

Euclidean distance in 5D holographic space (includes V weighting).
"""
@inline function euclidean_5d(a::Coord5D, b::Coord5D)::Float64
    # V (valence) gets 2× weight because zone transitions matter more than spatial drift
    dx = a[1] - b[1]
    dy = a[2] - b[2]
    dz = a[3] - b[3]
    dw = a[4] - b[4]
    dv = 2.0 * (a[5] - b[5])
    @fastmath sqrt(dx*dx + dy*dy + dz*dz + dw*dw + dv*dv)
end

"""
    nearest_neighbors(query::Coord5D, coords::Vector{Coord5D}, k::Int=5)

Find k nearest neighbors to a query point in 5D holographic space.
Returns vector of (index, distance) tuples sorted by distance.

For small coordinate sets (< 64), uses brute-force scan.
For larger sets, use nearest_neighbors_kdtree for O(log n) performance.
"""
function nearest_neighbors(
    query::Coord5D,
    coords::Vector{Coord5D},
    k::Int=5,
)::Vector{Tuple{Int, Float64}}
    isempty(coords) && return Tuple{Int, Float64}[]

    distances = [(i, euclidean_5d(query, c)) for (i, c) in enumerate(coords)]
    sort!(distances, by=x -> x[2])
    k = min(k, length(distances))
    distances[1:k]
end

"""
    nearest_neighbors_kdtree(query::Coord5D, coords::Vector{Coord5D}, k::Int=5)

Find k nearest neighbors using a KD-tree for O(log n) queries.
Builds the tree on each call — for repeated queries, build the tree once
and reuse it.

Returns vector of (index, distance) tuples sorted by distance.
"""
function nearest_neighbors_kdtree(
    query::Coord5D,
    coords::Vector{Coord5D},
    k::Int=5,
)::Vector{Tuple{Int, Float64}}
    isempty(coords) && return Tuple{Int, Float64}[]
    n = length(coords)
    k = min(k, n)

    # For small n, brute force is faster (no tree build overhead)
    if n < 64
        return nearest_neighbors(query, coords, k)
    end

    # Build KD-tree from coordinate matrix
    # Coord5D is SVector{5,Float64}, so we can stack them into a matrix
    data = Matrix{Float64}(undef, 5, n)
    for (i, c) in enumerate(coords)
        data[:, i] = c
    end

    # Custom metric: weighted Euclidean with 2× V weight
    # NearestNeighbors uses standard Euclidean, so we pre-scale V
    scaled_data = copy(data)
    @inbounds for i in 1:n
        scaled_data[5, i] *= 2.0
    end
    scaled_query = Coord5D(query[1], query[2], query[3], query[4], 2.0 * query[5])

    tree = KDTree(scaled_data)
    idxs, dists = knn(tree, collect(scaled_query), k, true)

    [(idxs[i], dists[i]) for i in 1:length(idxs)]
end

"""
    zone_of(coord::NTuple{5,Float64}) -> String

Determine galactic zone from the V (valence) coordinate.
"""
function zone_of(coord::Coord5D)::String
    v = coord[5]
    for i in 1:(length(ZONE_BOUNDS)-1)
        if v < ZONE_BOUNDS[i+1]
            return ZONE_NAMES[i]
        end
    end
    ZONE_NAMES[end]
end

# ---------------------------------------------------------------------------
# Constellation Detection
# ---------------------------------------------------------------------------

"""
    constellation_detect(coords::Vector{NTuple{5,Float64}}; threshold=0.5, min_size=3)

Detect constellations (dense clusters) in holographic memory space using
single-linkage clustering with a distance threshold.

Returns vector of cluster indices (each cluster is a Vector{Int}).
"""
function constellation_detect(
    coords::Vector{Coord5D};
    threshold::Float64=0.5,
    min_size::Int=3,
)::Vector{Vector{Int}}
    n = length(coords)
    n < min_size && return Vector{Int}[]

    # Union-Find for connected components
    parent = collect(1:n)
    rank = zeros(Int, n)

    find(i) = parent[i] == i ? i : (parent[i] = find(parent[i]))
    function union!(a, b)
        ra = find(a)
        rb = find(b)
        ra == rb && return
        if rank[ra] < rank[rb]
            parent[ra] = rb
        elseif rank[ra] > rank[rb]
            parent[rb] = ra
        else
            parent[rb] = ra
            rank[ra] += 1
        end
    end

    # Link points within threshold
    for i in 1:n
        for j in (i+1):n
            if euclidean_5d(coords[i], coords[j]) <= threshold
                union!(i, j)
            end
        end
    end

    # Collect components
    comps = Dict{Int, Vector{Int}}()
    for i in 1:n
        root = find(i)
        push!(get!(comps, root, Int[]), i)
    end

    # Filter by minimum size and sort by size descending
    clusters = collect(values(comps))
    filter!(c -> length(c) >= min_size, clusters)
    sort!(clusters, by=length, rev=true)
    clusters
end

# ---------------------------------------------------------------------------
# Coherence & Hashing
# ---------------------------------------------------------------------------

"""
    coherence_score(coords::Vector{NTuple{5,Float64}}) -> Float64

Measure the internal coherence of a memory cluster.
High coherence = tight cluster (low mean pairwise distance).
Returns 0.0-1.0.
"""
function coherence_score(coords::Vector{Coord5D})::Float64
    n = length(coords)
    n < 2 && return 1.0

    total = 0.0
    count = 0
    for i in 1:n
        for j in (i+1):n
            total += euclidean_5d(coords[i], coords[j])
            count += 1
        end
    end
    mean_dist = total / count
    # Map mean distance [0, 2.0] to coherence [1, 0]
    clamp(1.0 - mean_dist / 2.0, 0.0, 1.0)
end

"""
    holographic_hash(coord::NTuple{5,Float64}; bins_per_dim=8) -> String

Locality-sensitive hash for 5D holographic coordinates.
Memories with similar coordinates get the same hash prefix.
"""
function holographic_hash(coord::Coord5D; bins_per_dim::Int=8)::String
    # Quantise each dimension into bins
    bins = [clamp(floor(Int, (coord[i] + 3.0) / 6.0 * bins_per_dim), 0, bins_per_dim - 1) for i in 1:5]
    # Encode as base-32 string
    code = sum(b * bins_per_dim^(i-1) for (i, b) in enumerate(bins))
    string(code, base=32, pad=5)
end

"""
    merge_coordinates(coords::Vector{NTuple{5,Float64}}; weights=nothing) -> NTuple{5,Float64}

Merge multiple holographic coordinates into a centroid.
Optional weights default to uniform.
"""
function merge_coordinates(
    coords::Vector{Coord5D};
    weights::Union{Nothing, Vector{Float64}}=nothing,
)::Coord5D
    n = length(coords)
    n == 0 && return Coord5D(0.0, 0.0, 0.0, 0.0, 0.0)

    w = weights === nothing ? fill(1.0 / n, n) : weights ./ sum(weights)
    xs = sum(c[1] * w[i] for (i, c) in enumerate(coords))
    ys = sum(c[2] * w[i] for (i, c) in enumerate(coords))
    zs = sum(c[3] * w[i] for (i, c) in enumerate(coords))
    ws = sum(c[4] * w[i] for (i, c) in enumerate(coords))
    vs = sum(c[5] * w[i] for (i, c) in enumerate(coords))

    Coord5D(round(xs; digits=6), round(ys; digits=6), round(zs; digits=6), round(ws; digits=6), round(vs; digits=6))
end

# ---------------------------------------------------------------------------
# JSON stdio interface (for Python bridge)
# ---------------------------------------------------------------------------

function handle_request(request::Dict)
    cmd = get(request, "command", "")

    try
        if cmd == "encode_5d"
            text = get(request, "text", "")
            seed = Int(get(request, "seed", 42))
            return Dict("coordinate" => collect(encode_5d(text; seed=seed)))

        elseif cmd == "nearest_neighbors"
            query = Coord5D(get(request, "query", [0.0, 0.0, 0.0, 0.0, 0.0])...)
            coords = [Coord5D(c...) for c in get(request, "coords", [])]
            k = Int(get(request, "k", 5))
            # Use KD-tree for large coordinate sets
            if length(coords) >= 64
                nn = nearest_neighbors_kdtree(query, coords, k)
            else
                nn = nearest_neighbors(query, coords, k)
            end
            return Dict("neighbors" => [Dict("index" => i, "distance" => round(d; digits=6)) for (i, d) in nn])

        elseif cmd == "constellation_detect"
            coords = [Coord5D(c...) for c in get(request, "coords", [])]
            threshold = Float64(get(request, "threshold", 0.5))
            min_size = Int(get(request, "min_size", 3))
            clusters = constellation_detect(coords; threshold=threshold, min_size=min_size)
            return Dict("clusters" => clusters, "cluster_count" => length(clusters))

        elseif cmd == "zone_of"
            coord = Coord5D(get(request, "coord", [0.0, 0.0, 0.0, 0.0, 0.0])...)
            return Dict("zone" => zone_of(coord))

        elseif cmd == "coherence"
            coords = [Coord5D(c...) for c in get(request, "coords", [])]
            return Dict("coherence" => round(coherence_score(coords); digits=6))

        elseif cmd == "holographic_hash"
            coord = Coord5D(get(request, "coord", [0.0, 0.0, 0.0, 0.0, 0.0])...)
            bins = Int(get(request, "bins", 8))
            return Dict("hash" => holographic_hash(coord; bins_per_dim=bins))

        elseif cmd == "merge_coordinates"
            coords = [Coord5D(c...) for c in get(request, "coords", [])]
            return Dict("centroid" => collect(merge_coordinates(coords)))

        else
            return Dict("error" => "Unknown command: $cmd")
        end
    catch e
        return Dict("error" => string(e))
    end
end

# Precompile hot functions to eliminate JIT cold-start
@compile_workload begin
    encode_5d("precompile test string")
    encode_5d("another test")
    c1 = encode_5d("test")
    c2 = encode_5d("another")
    euclidean_5d(c1, c2)
    nearest_neighbors(c1, [c1, c2], 2)
    zone_of(c1)
    coherence_score([c1, c2])
    holographic_hash(c1)
    merge_coordinates([c1, c2])
    constellation_detect([c1, c2]; threshold=1.0, min_size=1)
    # Warmup KD-tree path with enough points to trigger it
    many_coords = [encode_5d("point_$i") for i in 1:70]
    nearest_neighbors_kdtree(c1, many_coords, 5)
end

end  # module HolographicMemory
