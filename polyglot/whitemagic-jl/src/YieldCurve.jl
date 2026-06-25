"""
    WhiteMagic Yield Curve (Objective Y)
    =====================================
    Models the temporal value of improvements as a yield curve.

    Translated from Python's yield_curve.py for Julia numerics acceleration.
    Designed to be called from Python via JSON stdio bridge.

    Value function models:
    - Decaying (tamasic):    V(t) = V₀ · exp(-λt)
    - Compounding (sattvic): V(t) = V₀ · (1 + r)^t
    - Appreciating (rajasic): V(t) = V₀ · log(1 + t/τ)
    - Transient:             V(t) = V₀ · exp(-λt) · (1 - exp(-t/τ))
"""
module YieldCurveJL

using Statistics

export value_at, duration, fit_parameters, portfolio_duration,
       select_by_horizon, detect_regime_change

# ---------------------------------------------------------------------------
# Yield type enum (encoded as string for JSON compatibility)
# ---------------------------------------------------------------------------

const YIELD_TYPES = ["decaying", "compounding", "appreciating", "transient"]

# ---------------------------------------------------------------------------
# Core value function
# ---------------------------------------------------------------------------

"""
    value_at(yield_type::String, t::Float64; v0, lambda, r, tau)

Compute V(t) at time t for the given yield type.
"""
function value_at(yield_type::String, t::Float64;
                  v0::Float64=1.0, lambda::Float64=0.1,
                  r::Float64=0.05, tau::Float64=10.0)
    if yield_type == "decaying"
        return v0 * exp(-lambda * t)
    elseif yield_type == "compounding"
        return v0 * (1 + r)^t
    elseif yield_type == "appreciating"
        return v0 * log(1 + t / tau)
    elseif yield_type == "transient"
        return v0 * exp(-lambda * t) * (1 - exp(-t / tau))
    end
    return v0
end

# ---------------------------------------------------------------------------
# Duration (weighted average time to value realization)
# ---------------------------------------------------------------------------

"""
    duration(yield_type::String; lambda, r, tau)

Compute the duration for the given yield type.
"""
function duration(yield_type::String;
                  lambda::Float64=0.1, r::Float64=0.05, tau::Float64=10.0)
    if yield_type == "decaying"
        return lambda > 0 ? 1.0 / lambda : Inf
    elseif yield_type == "compounding"
        return r > 0 ? 1.0 / r : Inf
    elseif yield_type == "appreciating"
        return tau * (MathConstants.e - 1)
    elseif yield_type == "transient"
        if abs(lambda - 1.0 / tau) < 1e-6
            return tau
        end
        return log(lambda * tau + 1) / (lambda - 1.0 / tau)
    end
    return 0.0
end

# ---------------------------------------------------------------------------
# Parameter fitting via grid search
# ---------------------------------------------------------------------------

"""
    fit_parameters(yield_type::String, observations::Vector{Tuple{Float64,Float64}})

Fit yield curve parameters from observations using grid search.
Returns Dict with fitted v0, lambda, r, tau.
"""
function fit_parameters(yield_type::String, observations::Vector{Tuple{Float64,Float64}})
    if length(observations) < 3
        return Dict("v0" => 1.0, "lambda" => 0.1, "r" => 0.05, "tau" => 10.0)
    end

    best_error = Inf
    best_v0 = 1.0
    best_lambda = 0.1
    best_r = 0.05
    best_tau = 10.0

    for v0 in [0.5, 1.0, 1.5, 2.0]
        for lam in [0.01, 0.05, 0.1, 0.2, 0.5]
            for r in [0.01, 0.05, 0.1, 0.2]
                for tau in [5.0, 10.0, 20.0, 50.0]
                    error = 0.0
                    for (t, val) in observations
                        predicted = value_at(yield_type, t; v0=v0, lambda=lam, r=r, tau=tau)
                        error += (predicted - val)^2
                    end
                    if error < best_error
                        best_error = error
                        best_v0 = v0
                        best_lambda = lam
                        best_r = r
                        best_tau = tau
                    end
                end
            end
        end
    end

    return Dict(
        "v0" => best_v0,
        "lambda" => best_lambda,
        "r" => best_r,
        "tau" => best_tau,
        "fit_error" => round(best_error; digits=6),
    )
end

# ---------------------------------------------------------------------------
# Portfolio operations
# ---------------------------------------------------------------------------

"""
    portfolio_duration(curves::Vector{Dict})

Compute weighted average duration of all improvements.
Each curve dict has: yield_type, v0, lambda, r, tau.
"""
function portfolio_duration(curves::Vector{Dict})
    if isempty(curves)
        return 0.0
    end
    total_weight = sum(c["v0"] for c in curves)
    if total_weight == 0
        return 0.0
    end
    weighted_sum = sum(
        c["v0"] * duration(c["yield_type"];
                           lambda=get(c, "lambda", 0.1),
                           r=get(c, "r", 0.05),
                           tau=get(c, "tau", 10.0))
        for c in curves
    )
    return weighted_sum / total_weight
end

"""
    select_by_horizon(curves::Vector{Dict}, time_horizon::Float64)

Select improvements that maximize value within the time horizon.
Returns list of (improvement_id, value_at_horizon) sorted by value descending.
"""
function select_by_horizon(curves::Vector{Dict}, time_horizon::Float64)
    results = Tuple{String, Float64}[]
    for c in curves
        imp_id = get(c, "improvement_id", "")
        val = value_at(c["yield_type"], time_horizon;
                       v0=get(c, "v0", 1.0),
                       lambda=get(c, "lambda", 0.1),
                       r=get(c, "r", 0.05),
                       tau=get(c, "tau", 10.0))
        push!(results, (imp_id, val))
    end
    sort!(results; by=x->x[2], rev=true)
    return results
end

# ---------------------------------------------------------------------------
# Regime change detection
# ---------------------------------------------------------------------------

"""
    detect_regime_change(yield_type::String, observations::Vector{Tuple{Float64,Float64}},
                         v0, lambda, r, tau; window=5)

Detect if an improvement's yield curve shape has changed.
Returns true if recent observations are consistently below predictions.
"""
function detect_regime_change(yield_type::String,
                              observations::Vector{Tuple{Float64,Float64}},
                              v0::Float64, lambda::Float64,
                              r::Float64, tau::Float64;
                              window::Int=5)
    if length(observations) < window * 2
        return false
    end

    recent = observations[end-window+1:end]
    below_count = 0

    for (t, val) in recent
        predicted = value_at(yield_type, t; v0=v0, lambda=lambda, r=r, tau=tau)
        if val < predicted * 0.7
            below_count += 1
        end
    end

    return below_count > window * 0.6
end

# ---------------------------------------------------------------------------
# JSON stdio interface (for Python bridge)
# ---------------------------------------------------------------------------

function handle_request(request::Dict)
    cmd = get(request, "command", "")

    try
        if cmd == "value_at"
            yt = get(request, "yield_type", "decaying")
            t = Float64(get(request, "t", 0.0))
            return Dict("status" => "ok", "result" => Dict(
                "value" => round(value_at(yt, t;
                    v0=Float64(get(request, "v0", 1.0)),
                    lambda=Float64(get(request, "lambda", 0.1)),
                    r=Float64(get(request, "r", 0.05)),
                    tau=Float64(get(request, "tau", 10.0))); digits=6)
            ))

        elseif cmd == "duration"
            yt = get(request, "yield_type", "decaying")
            d = duration(yt;
                lambda=Float64(get(request, "lambda", 0.1)),
                r=Float64(get(request, "r", 0.05)),
                tau=Float64(get(request, "tau", 10.0)))
            return Dict("status" => "ok", "result" => Dict(
                "duration" => isinf(d) ? 1e18 : round(d; digits=6)
            ))

        elseif cmd == "fit_parameters"
            yt = get(request, "yield_type", "decaying")
            obs_raw = get(request, "observations", [])
            obs = [(Float64(o[1]), Float64(o[2])) for o in obs_raw]
            return Dict("status" => "ok", "result" => fit_parameters(yt, obs))

        elseif cmd == "portfolio_duration"
            curves = get(request, "curves", [])
            return Dict("status" => "ok", "result" => Dict(
                "portfolio_duration" => round(portfolio_duration(curves); digits=6)
            ))

        elseif cmd == "select_by_horizon"
            curves = get(request, "curves", [])
            horizon = Float64(get(request, "time_horizon", 10.0))
            results = select_by_horizon(curves, horizon)
            return Dict("status" => "ok", "result" => Dict(
                "selections" => [Dict("improvement_id" => r[1], "value" => round(r[2]; digits=6)) for r in results]
            ))

        elseif cmd == "detect_regime_change"
            yt = get(request, "yield_type", "decaying")
            obs_raw = get(request, "observations", [])
            obs = [(Float64(o[1]), Float64(o[2])) for o in obs_raw]
            window = Int(get(request, "window", 5))
            changed = detect_regime_change(yt, obs,
                Float64(get(request, "v0", 1.0)),
                Float64(get(request, "lambda", 0.1)),
                Float64(get(request, "r", 0.05)),
                Float64(get(request, "tau", 10.0));
                window=window)
            return Dict("status" => "ok", "result" => Dict("regime_change" => changed))

        else
            return Dict("status" => "error", "error" => "Unknown command: $cmd")
        end
    catch e
        return Dict("status" => "error", "error" => string(e))
    end
end

end  # module YieldCurveJL
