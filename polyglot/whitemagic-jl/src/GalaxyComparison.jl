module GalaxyComparison

using Statistics
using LinearAlgebra

# Export public functions
export GalaxyStats, compare_galaxies, ks_statistic, js_divergence, 
       emd_estimate, galaxy_density, cross_galaxy_correlation,
       GalaxyComparisonResult, compute_galaxy_stats

"""
    GalaxyStats

Statistical summary of a galaxy's memory distribution.
"""
struct GalaxyStats
    galaxy_id::String
    n_memories::Int
    mean_importance::Float64
    std_importance::Float64
    mean_x::Float64  # temporal
    mean_y::Float64  # semantic
    mean_z::Float64  # emotional
    mean_w::Float64  # relational
    mean_v::Float64  # importance dimension
    min_importance::Float64
    max_importance::Float64
end

"""
    GalaxyComparisonResult

Result of comparing two galaxies.
"""
struct GalaxyComparisonResult
    galaxy_a::String
    galaxy_b::String
    ks_statistic::Float64       # Kolmogorov-Smirnov
    ks_pvalue_approx::Float64   # Approximate p-value
    js_divergence::Float64      # Jensen-Shannon Divergence
    emd_estimate::Float64       # Earth Mover's Distance (approximate)
    correlation::Float64        # Pearson correlation
    density_ratio::Float64      # Ratio of memory densities
    summary::String
end

"""
    compute_galaxy_stats(galaxy_id, importance, coords)

Compute statistics for a galaxy from its memory data.
"""
function compute_galaxy_stats(galaxy_id::String, importance::Vector{Float64}, 
                              coords::Matrix{Float64})::GalaxyStats
    n = length(importance)
    if n == 0
        return GalaxyStats(galaxy_id, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    end
    
    imp_mean = mean(importance)
    imp_std = n > 1 ? std(importance) : 0.0
    
    # coords is 5×N matrix (x, y, z, w, v)
    mx = size(coords, 2) > 0 ? mean(coords[1, :]) : 0.0
    my = size(coords, 2) > 0 ? mean(coords[2, :]) : 0.0
    mz = size(coords, 2) > 0 ? mean(coords[3, :]) : 0.0
    mw = size(coords, 2) > 0 ? mean(coords[4, :]) : 0.0
    mv = size(coords, 2) > 0 ? mean(coords[5, :]) : 0.0
    
    GalaxyStats(galaxy_id, n, imp_mean, imp_std, mx, my, mz, mw, mv,
                minimum(importance), maximum(importance))
end

"""
    ks_statistic(a, b)

Compute the Kolmogorov-Smirnov statistic between two distributions.
Returns (D, approximate p-value).
"""
function ks_statistic(a::Vector{Float64}, b::Vector{Float64})
    na = length(a)
    nb = length(b)
    
    if na == 0 || nb == 0
        return (0.0, 1.0)
    end
    
    # Combine and sort
    all_vals = sort(vcat(a, b))
    
    # Compute CDFs at each point
    a_sorted = sort(a)
    b_sorted = sort(b)
    
    max_d = 0.0
    for v in all_vals
        cdf_a = count(x -> x <= v, a_sorted) / na
        cdf_b = count(x -> x <= v, b_sorted) / nb
        d = abs(cdf_a - cdf_b)
        if d > max_d
            max_d = d
        end
    end
    
    # Approximate p-value using the KS distribution
    ne = (na * nb) / (na + nb)
    lambda = (sqrt(ne) + 0.12 + 0.11 / sqrt(ne)) * max_d
    p_value = exp(-2.0 * lambda^2)
    
    return (max_d, p_value)
end

"""
    js_divergence(p, q)

Compute Jensen-Shannon Divergence between two probability distributions.
JSD = 0.5 * KL(P||M) + 0.5 * KL(Q||M) where M = 0.5*(P+Q)
"""
function js_divergence(p::Vector{<:Number}, q::Vector{<:Number})
    # Normalize
    sp = sum(p)
    sq = sum(q)
    if sp == 0 || sq == 0
        return 0.0
    end
    
    p_norm = p ./ sp
    q_norm = q ./ sq
    
    # Ensure same length
    n = min(length(p_norm), length(q_norm))
    p_n = p_norm[1:n]
    q_n = q_norm[1:n]
    
    m = 0.5 .* (p_n .+ q_n)
    
    # KL divergence with epsilon for numerical stability
    eps = 1e-10
    
    kl_pm = sum(p_n[i] * log((p_n[i] + eps) / (m[i] + eps)) for i in 1:n)
    kl_qm = sum(q_n[i] * log((q_n[i] + eps) / (m[i] + eps)) for i in 1:n)
    
    return 0.5 * kl_pm + 0.5 * kl_qm
end

"""
    emd_estimate(a, b)

Estimate Earth Mover's Distance between two distributions.
Uses a simple sorted-match approach (approximate EMD for 1D).
"""
function emd_estimate(a::Vector{Float64}, b::Vector{Float64})
    na = length(a)
    nb = length(b)
    
    if na == 0 || nb == 0
        return 0.0
    end
    
    # Sort both distributions
    a_sorted = sort(a)
    b_sorted = sort(b)
    
    # Match quantiles and compute average distance
    n = min(na, nb)
    total = 0.0
    for i in 1:n
        ai = a_sorted[floor(Int, (i - 0.5) * na / n) + 1]
        bi = b_sorted[floor(Int, (i - 0.5) * nb / n) + 1]
        total += abs(ai - bi)
    end
    
    return total / n
end

"""
    galaxy_density(coords, bandwidth)

Estimate memory density using a simple kernel density estimate.
Returns the average number of neighbors within bandwidth.
"""
function galaxy_density(coords::Matrix{Float64}, bandwidth::Float64 = 0.5)
    n = size(coords, 2)
    if n <= 1
        return 0.0
    end
    
    total_neighbors = 0
    for i in 1:n
        for j in (i+1):n
            dist = norm(coords[:, i] .- coords[:, j])
            if dist < bandwidth
                total_neighbors += 1
            end
        end
    end
    
    # Normalize by possible pairs
    max_pairs = n * (n - 1) / 2
    return max_pairs > 0 ? total_neighbors / max_pairs : 0.0
end

"""
    cross_galaxy_correlation(stats_a, stats_b)

Compute correlation between two galaxies based on their statistical properties.
"""
function cross_galaxy_correlation(stats_a::GalaxyStats, stats_b::GalaxyStats)
    # Compare coordinate means
    vec_a = [stats_a.mean_x, stats_a.mean_y, stats_a.mean_z, stats_a.mean_w, stats_a.mean_v]
    vec_b = [stats_b.mean_x, stats_b.mean_y, stats_b.mean_z, stats_b.mean_w, stats_b.mean_v]
    
    # Cosine similarity as correlation proxy
    na = norm(vec_a)
    nb = norm(vec_b)
    
    if na == 0 || nb == 0
        return 0.0
    end
    
    return dot(vec_a, vec_b) / (na * nb)
end

"""
    compare_galaxies(galaxy_a_id, importance_a, coords_a, 
                     galaxy_b_id, importance_b, coords_b)

Full statistical comparison between two galaxies.
"""
function compare_galaxies(galaxy_a_id::String, importance_a::Vector{Float64}, coords_a::Matrix{Float64},
                          galaxy_b_id::String, importance_b::Vector{Float64}, coords_b::Matrix{Float64})
    
    stats_a = compute_galaxy_stats(galaxy_a_id, importance_a, coords_a)
    stats_b = compute_galaxy_stats(galaxy_b_id, importance_b, coords_b)
    
    # KS test on importance distributions
    ks_d, ks_p = ks_statistic(importance_a, importance_b)
    
    # JSD on importance histograms
    n_bins = 10
    all_imp = vcat(importance_a, importance_b)
    if length(all_imp) > 0
        edges = range(minimum(all_imp), stop=maximum(all_imp) + 1e-10, length=n_bins+1)
        hist_a = [count(x -> edges[i] <= x < edges[i+1], importance_a) for i in 1:n_bins]
        hist_b = [count(x -> edges[i] <= x < edges[i+1], importance_b) for i in 1:n_bins]
        # Add last edge inclusive
        hist_a[end] += count(x -> x == edges[end], importance_a)
        hist_b[end] += count(x -> x == edges[end], importance_b)
    else
        hist_a = zeros(n_bins)
        hist_b = zeros(n_bins)
    end
    jsd = js_divergence(hist_a, hist_b)
    
    # EMD estimate
    emd = emd_estimate(importance_a, importance_b)
    
    # Cross-galaxy correlation
    corr = cross_galaxy_correlation(stats_a, stats_b)
    
    # Density ratio
    density_a = galaxy_density(coords_a)
    density_b = galaxy_density(coords_b)
    density_ratio = density_b > 0 ? density_a / density_b : (density_a > 0 ? Inf : 1.0)
    
    # Summary
    summary = if ks_d < 0.1 && jsd < 0.1
        "Galaxies are statistically similar"
    elseif ks_d < 0.3
        "Galaxies show moderate differences"
    else
        "Galaxies are significantly different"
    end
    
    GalaxyComparisonResult(galaxy_a_id, galaxy_b_id, ks_d, ks_p, jsd, emd, corr, density_ratio, summary)
end

end # module
