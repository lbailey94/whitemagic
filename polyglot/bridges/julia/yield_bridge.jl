#!/usr/bin/env julia
# WhiteMagic Julia Yield Curve JSON stdio bridge
# Reads JSON requests from stdin, writes JSON responses to stdout
# Protocol: {"method": "value_at", "params": {...}}

using JSON
include(joinpath(@__DIR__, "..", "..", "whitemagic-jl", "src", "YieldCurve.jl"))
using .YieldCurveJL

# Main loop: read JSON line, handle, write JSON line
while !eof(stdin)
    line = readline(stdin)
    isempty(line) && continue
    try
        req = JSON.parse(line)
        # Convert JSON.Object to Dict for handle_request compatibility
        if !isa(req, Dict)
            req = Dict(string(k) => v for (k, v) in req)
        end
        # Translate standard protocol {"method": ..., "params": {...}}
        # to YieldCurveJL format {"command": ..., ...flat params...}
        if haskey(req, "method") && !haskey(req, "command")
            req["command"] = req["method"]
        end
        if haskey(req, "params") && isa(req["params"], Dict)
            for (k, v) in req["params"]
                req[k] = v
            end
            delete!(req, "params")
        end
        resp = YieldCurveJL.handle_request(req)
        println(stdout, JSON.json(resp))
        flush(stdout)
    catch e
        err = Dict("status" => "error", "error" => string(e))
        println(stdout, JSON.json(err))
        flush(stdout)
    end
end
