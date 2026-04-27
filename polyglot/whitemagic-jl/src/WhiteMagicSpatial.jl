module WhiteMagicSpatial

using LinearAlgebra

export cosine_similarity, batch_cosine, euclidean_distance_5d

"""
    cosine_similarity(a, b) -> Float64

Cosine similarity between two vectors.
"""
function cosine_similarity(a::Vector{Float64}, b::Vector{Float64})::Float64
    dot(a, b) / (norm(a) * norm(b))
end

"""
    batch_cosine(query, corpus) -> Vector{Float64}

Compute cosine similarity between query and each vector in corpus.
"""
function batch_cosine(query::Vector{Float64}, corpus::Vector{Vector{Float64}})::Vector{Float64}
    [cosine_similarity(query, v) for v in corpus]
end

"""
    euclidean_distance_5d(c1, c2) -> Float64

Euclidean distance in 5D holographic space.
"""
function euclidean_distance_5d(c1::NTuple{5,Float64}, c2::NTuple{5,Float64})::Float64
    sqrt(sum((c1[i] - c2[i])^2 for i in 1:5))
end

end # module
