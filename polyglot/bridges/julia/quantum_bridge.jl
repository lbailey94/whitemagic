#!/usr/bin/env julia
# WhiteMagic Julia Quantum Geometry JSON stdio bridge
# Reads JSON requests from stdin, writes JSON responses to stdout
# Dispatches to QuantumGeometry.handle_request

using JSON

# Add the whitemagic-jl src directory to the load path
push!(LOAD_PATH, joinpath(dirname(@__DIR__), "..", "whitemagic-jl", "src"))

using QuantumGeometry

# Warmup: trigger JIT for hot paths
QuantumGeometry.manifold_distance([0.0, 0.0], [1.0, 1.0], "euclidean")
QuantumGeometry.manifold_distance([0.1, 0.1], [0.2, 0.2], "hyperbolic")
QuantumGeometry.manifold_distance([1.0, 0.0], [0.0, 1.0], "spherical")
QuantumGeometry.manifold_exp_map([0.0, 0.0], [0.1, 0.1], "euclidean")
QuantumGeometry.fubini_study_auto([1.0, 0.0, 0.0], 2)
QuantumGeometry.natural_gradient_step([1.0, 1.0], [0.1, 0.1], [1.0 0.0; 0.0 1.0], 0.01)
QuantumGeometry.mps_compress([[1.0, 0.0], [0.0, 1.0]], 2, 42)
QuantumGeometry.auto_select_manifold([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]])

# Main loop: read JSON line, handle, write JSON line
while !eof(stdin)
    line = readline(stdin)
    isempty(line) && continue
    try
        req = Dict{String, Any}(JSON.parse(line))
        resp = QuantumGeometry.handle_request(req)
        println(stdout, JSON.json(resp))
        flush(stdout)
    catch e
        err = Dict("status" => "error", "error" => string(e))
        println(stdout, JSON.json(err))
        flush(stdout)
    end
end
