"""
    WhiteMagic Cache Analytics
    ==========================
    Statistical analysis of cache access patterns for TTL auto-tuning.

    Provides:
    - KS test for hit/miss distribution comparison
    - TTL auto-tuning based on access frequency and age
    - Cache efficiency scoring per namespace
    - Exponential decay fitting for optimal TTL prediction

    Designed to be called from Python via the JuliaBridge (JSON over stdio).
"""
module CacheAnalytics

using Statistics
using LinearAlgebra

export ks_test,
       auto_tune_ttl,
       cache_efficiency_score,
       fit_decay_model,
       recommend_ttl_adjustments

# ---------------------------------------------------------------------------
# Kolmogorov-Smirnov two-sample test (simplified implementation)
# ---------------------------------------------------------------------------

"""
    ks_test(x::Vector{Float64}, y::Vector{Float64})

Two-sample Kolmogorov-Smirnov test. Returns (D statistic, p-value approximation).

Compares the empirical CDFs of two samples to determine if they come from
the same distribution. Used to detect when cache access patterns have shifted
(e.g., after a workload change) and TTLs need re-tuning.
"""
function ks_test(x::Vector{Float64}, y::Vector{Float64})
    nx, ny = length(x), length(y)
    if nx == 0 || ny == 0
        return Dict("d_statistic" => 0.0, "p_value" => 1.0, "same_distribution" => true)
    end

    # Combine and sort all values
    all_vals = sort(vcat(x, y))

    # Compute empirical CDFs at each point
    x_sorted = sort(x)
    y_sorted = sort(y)

    max_d = 0.0
    for v in all_vals
        cdf_x = searchsortedlast(x_sorted, v) / nx
        cdf_y = searchsortedlast(y_sorted, v) / ny
        d = abs(cdf_x - cdf_y)
        if d > max_d
            max_d = d
        end
    end

    # Approximate p-value using the Kolmogorov distribution
    # en = sqrt(nx * ny / (nx + ny))
    en = sqrt(nx * ny / (nx + ny))
    lambda = (en + 0.12 + 0.11 / en) * max_d
    # p-value approximation: Q_KS(λ) = 2 * Σ (-1)^(k-1) * exp(-2*k^2*λ^2)
    p_value = 0.0
    for k in 1:100
        term = 2.0 * (-1)^(k - 1) * exp(-2.0 * k^2 * lambda^2)
        p_value += term
        if abs(term) < 1e-10
            break
        end
    end
    p_value = clamp(p_value, 0.0, 1.0)

    return Dict(
        "d_statistic" => round(max_d, digits=6),
        "p_value" => round(p_value, digits=6),
        "same_distribution" => p_value > 0.05,
        "n_x" => nx,
        "n_y" => ny,
    )
end

# ---------------------------------------------------------------------------
# TTL auto-tuning
# ---------------------------------------------------------------------------

"""
    auto_tune_ttl(access_times::Vector{Float64}, current_ttl::Float64)

Analyzes access time patterns and recommends an optimal TTL.

Uses the inter-arrival time distribution to determine the TTL that maximizes
cache hit rate. If accesses are frequent and clustered, a shorter TTL suffices.
If accesses are spread out, a longer TTL is needed.

Returns recommended TTL and confidence score.
"""
function auto_tune_ttl(access_times::Vector{Float64}, current_ttl::Float64)
    n = length(access_times)
    if n < 2
        return Dict(
            "recommended_ttl" => current_ttl,
            "confidence" => 0.0,
            "reason" => "insufficient_data",
            "sample_size" => n,
        )
    end

    sorted_times = sort(access_times)
    inter_arrivals = diff(sorted_times)

    if isempty(inter_arrivals)
        return Dict(
            "recommended_ttl" => current_ttl,
            "confidence" => 0.0,
            "reason" => "no_inter_arrivals",
            "sample_size" => n,
        )
    end

    mean_ia = mean(inter_arrivals)
    median_ia = median(inter_arrivals)
    p95_ia = quantile(inter_arrivals, 0.95)
    std_ia = length(inter_arrivals) > 1 ? std(inter_arrivals) : 0.0

    # Optimal TTL: cover 95% of inter-arrival times
    # But not so long that stale data becomes a problem
    recommended = min(p95_ia * 1.5, current_ttl * 3.0)
    recommended = max(recommended, 60.0)  # minimum 1 minute
    recommended = min(recommended, 86400.0 * 7)  # max 1 week

    # Confidence based on sample size and variance
    cv = mean_ia > 0 ? std_ia / mean_ia : 1.0
    confidence = clamp(1.0 - cv * 0.5, 0.0, 1.0)
    confidence *= min(n / 50.0, 1.0)  # more samples = more confidence

    # Direction relative to current
    if recommended < current_ttl * 0.8
        direction = "decrease"
    elseif recommended > current_ttl * 1.2
        direction = "increase"
    else
        direction = "maintain"
    end

    return Dict(
        "recommended_ttl" => round(recommended, digits=1),
        "current_ttl" => current_ttl,
        "confidence" => round(confidence, digits=3),
        "direction" => direction,
        "mean_inter_arrival" => round(mean_ia, digits=3),
        "median_inter_arrival" => round(median_ia, digits=3),
        "p95_inter_arrival" => round(p95_ia, digits=3),
        "std_inter_arrival" => round(std_ia, digits=3),
        "coefficient_of_variation" => round(cv, digits=3),
        "sample_size" => n,
        "reason" => "p95_coverage",
    )
end

# ---------------------------------------------------------------------------
# Cache efficiency score
# ---------------------------------------------------------------------------

"""
    cache_efficiency_score(hits::Int, misses::Int, evictions::Int, expirations::Int, size::Int, max_size::Int)

Computes a composite efficiency score (0-1) for a cache namespace.

Factors:
- Hit rate (weight: 0.5)
- Eviction rate (weight: 0.2) — lower is better
- Expiration rate (weight: 0.15) — lower is better
- Capacity utilization (weight: 0.15) — moderate is better
"""
function cache_efficiency_score(
    hits::Int, misses::Int, evictions::Int,
    expirations::Int, size::Int, max_size::Int,
)
    total = hits + misses
    hit_rate = total > 0 ? hits / total : 0.0

    # Eviction rate: evictions per total write (approximate with hits+misses)
    eviction_rate = total > 0 ? evictions / total : 0.0
    eviction_penalty = 1.0 - min(eviction_rate, 1.0)

    # Expiration rate
    expiration_rate = total > 0 ? expirations / total : 0.0
    expiration_penalty = 1.0 - min(expiration_rate, 1.0)

    # Capacity utilization: sweet spot is 60-80%
    util = max_size > 0 ? size / max_size : 0.0
    if util < 0.1
        util_score = util * 5.0  # underutilized
    elseif util > 0.95
        util_score = 0.5  # nearly full, risk of evictions
    else
        util_score = 1.0
    end

    score = 0.5 * hit_rate + 0.2 * eviction_penalty + 0.15 * expiration_penalty + 0.15 * util_score

    return Dict(
        "score" => round(score, digits=4),
        "hit_rate" => round(hit_rate, digits=4),
        "eviction_rate" => round(eviction_rate, digits=4),
        "expiration_rate" => round(expiration_rate, digits=4),
        "capacity_utilization" => round(util, digits=4),
        "recommendation" => score > 0.7 ? "healthy" : (score > 0.4 ? "monitor" : "tune"),
    )
end

# ---------------------------------------------------------------------------
# Exponential decay model fitting
# ---------------------------------------------------------------------------

"""
    fit_decay_model(access_ages::Vector{Float64}, hit_counts::Vector{Int})

Fits an exponential decay model: hit_count ≈ A * exp(-λ * age)

This models how cache hit probability decays with age. The fitted λ parameter
tells us the decay rate, which can be used to compute the half-life and
optimal TTL.

Uses simple log-linear regression (least squares on log-transformed data).
"""
function fit_decay_model(access_ages::Vector{Float64}, hit_counts::Vector{Int})
    n = length(access_ages)
    if n < 3
        return Dict(
            "fitted" => false,
            "reason" => "insufficient_data",
            "lambda" => 0.0,
            "amplitude" => 0.0,
            "half_life" => 0.0,
            "r_squared" => 0.0,
        )
    end

    # Filter out zero counts (can't take log)
    valid_idx = findall(h -> h > 0, hit_counts)
    if length(valid_idx) < 3
        return Dict(
            "fitted" => false,
            "reason" => "too_many_zeros",
            "lambda" => 0.0,
            "amplitude" => 0.0,
            "half_life" => 0.0,
            "r_squared" => 0.0,
        )
    end

    ages = access_ages[valid_idx]
    log_counts = log.(Float64.(hit_counts[valid_idx]))

    # Linear regression: log(y) = log(A) - λ * x
    n_v = length(ages)
    x_mean = mean(ages)
    y_mean = mean(log_counts)

    ss_xy = sum((ages .- x_mean) .* (log_counts .- y_mean))
    ss_xx = sum((ages .- x_mean) .^ 2)
    ss_yy = sum((log_counts .- y_mean) .^ 2)

    if ss_xx == 0.0
        return Dict(
            "fitted" => false,
            "reason" => "zero_variance_in_ages",
            "lambda" => 0.0,
            "amplitude" => 0.0,
            "half_life" => 0.0,
            "r_squared" => 0.0,
        )
    end

    slope = ss_xy / ss_xx  # This is -λ
    intercept = y_mean - slope * x_mean  # This is log(A)

    lambda = -slope
    amplitude = exp(intercept)
    half_life = lambda > 0 ? log(2) / lambda : Inf
    r_squared = ss_yy > 0 ? (ss_xy^2) / (ss_xx * ss_yy) : 0.0

    # Recommended TTL: 3 half-lives (87.5% of hits captured)
    recommended_ttl = lambda > 0 ? 3.0 * half_life : 3600.0

    return Dict(
        "fitted" => true,
        "lambda" => round(lambda, digits=6),
        "amplitude" => round(amplitude, digits=4),
        "half_life" => round(half_life, digits=2),
        "r_squared" => round(r_squared, digits=4),
        "recommended_ttl" => round(recommended_ttl, digits=1),
        "model" => "exponential_decay",
        "sample_size" => n_v,
    )
end

# ---------------------------------------------------------------------------
# Batch TTL recommendations for multiple namespaces
# ---------------------------------------------------------------------------

"""
    recommend_ttl_adjustments(namespaces::Vector{Dict})

Given per-namespace cache stats, recommends TTL adjustments.

Each namespace dict should have:
- "name": namespace name
- "hits", "misses", "evictions", "expirations", "size", "max_size"
- "current_ttl": current TTL in seconds
- "access_times": list of access timestamps (optional, for auto_tune)
"""
function recommend_ttl_adjustments(namespaces::Vector)
    results = []
    for ns in namespaces
        name = get(ns, "name", "unknown")
        current_ttl = Float64(get(ns, "current_ttl", 3600.0))
        hits = Int(get(ns, "hits", 0))
        misses = Int(get(ns, "misses", 0))
        evictions = Int(get(ns, "evictions", 0))
        expirations = Int(get(ns, "expirations", 0))
        size = Int(get(ns, "size", 0))
        max_size = Int(get(ns, "max_size", 10000))

        # Efficiency score
        eff = cache_efficiency_score(hits, misses, evictions, expirations, size, max_size)

        # TTL tuning if access times available
        access_times = Float64.(get(ns, "access_times", []))
        ttl_result = auto_tune_ttl(access_times, current_ttl)

        push!(results, Dict(
            "namespace" => name,
            "efficiency" => eff,
            "ttl_tuning" => ttl_result,
            "action" => if eff["recommendation"] == "tune"
                "adjust_ttl"
            elseif eff["recommendation"] == "monitor"
                "watch"
            else
                "no_action"
            end,
        ))
    end

    return Dict(
        "namespaces" => results,
        "total_namespaces" => length(results),
        "timestamp" => time(),
    )
end

# ---------------------------------------------------------------------------
# JSON stdio interface (for Python bridge)
# ---------------------------------------------------------------------------

"""
    handle_request(request::Dict)

Process a JSON request from the Python bridge.
"""
function handle_request(request::Dict)
    cmd = get(request, "command", "")

    try
        if cmd == "ks_test"
            x = Float64.(get(request, "x", []))
            y = Float64.(get(request, "y", []))
            return ks_test(x, y)
        elseif cmd == "auto_tune_ttl"
            access_times = Float64.(get(request, "access_times", []))
            current_ttl = Float64(get(request, "current_ttl", 3600.0))
            return auto_tune_ttl(access_times, current_ttl)
        elseif cmd == "cache_efficiency"
            hits = Int(get(request, "hits", 0))
            misses = Int(get(request, "misses", 0))
            evictions = Int(get(request, "evictions", 0))
            expirations = Int(get(request, "expirations", 0))
            size = Int(get(request, "size", 0))
            max_size = Int(get(request, "max_size", 10000))
            return cache_efficiency_score(hits, misses, evictions, expirations, size, max_size)
        elseif cmd == "fit_decay"
            access_ages = Float64.(get(request, "access_ages", []))
            hit_counts = Int.(get(request, "hit_counts", []))
            return fit_decay_model(access_ages, hit_counts)
        elseif cmd == "recommend_ttl_adjustments"
            namespaces = get(request, "namespaces", [])
            return recommend_ttl_adjustments(namespaces)
        else
            return Dict("error" => "Unknown command: $cmd")
        end
    catch e
        return Dict("error" => string(e))
    end
end

end  # module CacheAnalytics
