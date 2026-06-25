#!/usr/bin/env julia
# WhiteMagic Julia Yield Curve JSON stdio bridge
# Reads JSON requests from stdin, writes JSON responses to stdout

using JSON
include(joinpath(@__DIR__, "..", "src", "YieldCurve.jl"))
using .YieldCurveJL

# Main loop: read JSON line, handle, write JSON line
while !eof(stdin)
    line = readline(stdin)
    isempty(line) && continue
    try
        req = JSON.parse(line)
        resp = YieldCurveJL.handle_request(req)
        println(stdout, JSON.json(resp))
        flush(stdout)
    catch e
        err = Dict("status" => "error", "error" => string(e))
        println(stdout, JSON.json(err))
        flush(stdout)
    end
end
