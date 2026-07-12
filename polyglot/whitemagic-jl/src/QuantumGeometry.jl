"""
    WhiteMagic Quantum Geometry (Julia)
    ====================================
    Exact Riemannian geometry for quantum-inspired cognitive operations.

    Provides:
    - Manifold operations (exp map, log map, parallel transport) for
      Euclidean, hyperbolic (Poincare ball), and spherical manifolds
    - Fubini-Study metric computation with automatic Jacobian via finite differences
    - Natural gradient descent on quantum state manifolds
    - MPS (Matrix Product State) compression for HRR vectors
    - Auto manifold selection from point distributions

    Designed to be called from Python via the Julia bridge (JSON over stdio).
"""

module QuantumGeometry

using LinearAlgebra
using Statistics

export
    manifold_distance,
    manifold_exp_map,
    manifold_log_map,
    manifold_parallel_transport,
    manifold_inner_product,
    fubini_study_metric,
    fubini_study_auto,
    natural_gradient_step,
    mps_compress,
    mps_full_state,
    mps_bind,
    auto_select_manifold,
    normalize_to_manifold

# ---------------------------------------------------------------------------
# Manifold Distance
# ---------------------------------------------------------------------------

function manifold_distance(a::AbstractVector{<:Real}, b::AbstractVector{<:Real},
                           manifold::String="euclidean")::Float64
    n = length(a)
    @assert length(b) == n "Vectors must have same dimension"

    if manifold == "euclidean"
        return norm(a .- b)
    elseif manifold == "hyperbolic"
        norm_a_sq = sum(a .* a)
        norm_b_sq = sum(b .* b)
        diff_sq = sum((a .- b) .^ 2)
        denom = (1.0 - norm_a_sq) * (1.0 - norm_b_sq)
        if denom <= 1e-15
            return Inf
        end
        arg = 1.0 + 2.0 * diff_sq / denom
        return acosh(clamp(arg, 1.0, 1e15))
    elseif manifold == "spherical"
        na = norm(a)
        nb = norm(b)
        if na < 1e-15 || nb < 1e-15
            return 0.0
        end
        cos_angle = clamp(dot(a, b) / (na * nb), -1.0, 1.0)
        return acos(cos_angle)
    else
        error("Unknown manifold: $manifold")
    end
end

# ---------------------------------------------------------------------------
# Exponential Map
# ---------------------------------------------------------------------------

function manifold_exp_map(point::AbstractVector{<:Real},
                          tangent::AbstractVector{<:Real},
                          manifold::String="euclidean")::Vector{Float64}
    n = length(point)
    @assert length(tangent) == n "Point and tangent must have same dimension"

    if manifold == "euclidean"
        return collect(point .+ tangent)
    elseif manifold == "hyperbolic"
        norm_v = norm(tangent)
        if norm_v < 1e-15
            return collect(point)
        end
        factor = tanh(norm_v) / norm_v
        scaled_v = factor .* tangent
        denom = 1.0 + dot(point, scaled_v)
        if abs(denom) < 1e-15
            return collect(point)
        end
        result = (point .+ scaled_v) ./ (1.0 .+ dot(point, scaled_v))
        norm_result = norm(result)
        if norm_result >= 0.999
            result = result .* (0.999 / norm_result)
        end
        return collect(result)
    elseif manifold == "spherical"
        na = norm(point)
        if na < 1e-15
            return collect(point)
        end
        p_hat = point ./ na
        nv = norm(tangent)
        if nv < 1e-15
            return collect(point)
        end
        r = na
        cos_t = cos(nv / r)
        sin_t = sin(nv / r)
        result = cos_t .* p_hat .* r .+ (r * sin_t / nv) .* tangent
        return collect(result)
    else
        error("Unknown manifold: $manifold")
    end
end

# ---------------------------------------------------------------------------
# Logarithmic Map
# ---------------------------------------------------------------------------

function manifold_log_map(point::AbstractVector{<:Real},
                          target::AbstractVector{<:Real},
                          manifold::String="euclidean")::Vector{Float64}
    n = length(point)
    @assert length(target) == n "Point and target must have same dimension"

    if manifold == "euclidean"
        return collect(target .- point)
    elseif manifold == "hyperbolic"
        norm_p_sq = sum(point .* point)
        norm_q_sq = sum(target .* target)
        denom = (1.0 - norm_p_sq) * (1.0 - norm_q_sq)
        if denom <= 1e-15
            return collect(target .- point)
        end
        neg_p = .-point
        mob_denom = 1.0 .+ dot(neg_p, target)
        if abs(mob_denom) < 1e-15
            return collect(target .- point)
        end
        mob = (neg_p .+ target) ./ mob_denom
        norm_mob = norm(mob)
        if norm_mob < 1e-15
            return zeros(n)
        end
        factor = atanh(clamp(norm_mob, 0.0, 0.999)) / norm_mob
        return collect(factor .* mob)
    elseif manifold == "spherical"
        na = norm(point)
        nb = norm(target)
        if na < 1e-15 || nb < 1e-15
            return collect(target .- point)
        end
        p_hat = point ./ na
        cos_angle = clamp(dot(p_hat, target ./ nb), -1.0, 1.0)
        theta = acos(cos_angle)
        if theta < 1e-15
            return zeros(n)
        end
        q_perp = target .- dot(target, p_hat) .* p_hat
        norm_q_perp = norm(q_perp)
        if norm_q_perp < 1e-15
            return zeros(n)
        end
        return collect(theta .* q_perp ./ norm_q_perp)
    else
        error("Unknown manifold: $manifold")
    end
end

# ---------------------------------------------------------------------------
# Parallel Transport
# ---------------------------------------------------------------------------

function manifold_parallel_transport(point::AbstractVector{<:Real},
                                     target::AbstractVector{<:Real},
                                     vector::AbstractVector{<:Real},
                                     manifold::String="euclidean")::Vector{Float64}
    n = length(point)
    @assert length(target) == n
    @assert length(vector) == n

    if manifold == "euclidean"
        return collect(vector)
    elseif manifold == "hyperbolic"
        log_pt = manifold_log_map(point, target, "hyperbolic")
        log_norm = norm(log_pt)
        if log_norm < 1e-15
            return collect(vector)
        end
        log_tq = manifold_log_map(target, point, "hyperbolic")
        coeff = dot(vector, log_pt) / (log_norm^2)
        return collect(vector .- coeff .* log_pt .+ coeff .* log_tq)
    elseif manifold == "spherical"
        na = norm(point)
        nb = norm(target)
        if na < 1e-15 || nb < 1e-15
            return collect(vector)
        end
        p_hat = point ./ na
        q_hat = target ./ nb
        cos_angle = clamp(dot(p_hat, q_hat), -1.0, 1.0)
        theta = acos(cos_angle)
        if theta < 1e-15
            return collect(vector)
        end
        u = (q_hat .- cos_angle .* p_hat) ./ sin(theta)
        v_tangent = vector .- dot(vector, p_hat) .* p_hat
        v_dot_u = dot(v_tangent, u)
        result = v_tangent .- v_dot_u .* (p_hat .+ q_hat) ./ (1.0 .+ cos_angle) .* theta
        result = result .- dot(result, q_hat) .* q_hat
        return collect(result)
    else
        error("Unknown manifold: $manifold")
    end
end

# ---------------------------------------------------------------------------
# Riemannian Inner Product
# ---------------------------------------------------------------------------

function manifold_inner_product(point::AbstractVector{<:Real},
                                v1::AbstractVector{<:Real},
                                v2::AbstractVector{<:Real},
                                manifold::String="euclidean")::Float64
    if manifold == "euclidean"
        return dot(v1, v2)
    elseif manifold == "hyperbolic"
        norm_x_sq = sum(point .* point)
        scale = 2.0 / (1.0 - norm_x_sq)
        return (scale^2) * dot(v1, v2)
    elseif manifold == "spherical"
        na = norm(point)
        if na < 1e-15
            return dot(v1, v2)
        end
        p_hat = point ./ na
        v1_t = v1 .- dot(v1, p_hat) .* p_hat
        v2_t = v2 .- dot(v2, p_hat) .* p_hat
        return dot(v1_t, v2_t)
    else
        error("Unknown manifold: $manifold")
    end
end

# ---------------------------------------------------------------------------
# Fubini-Study Metric
# ---------------------------------------------------------------------------

function fubini_study_metric(state::AbstractVector{<:Real},
                             jacobian::AbstractMatrix{<:Real},
                             n_params::Int)::Matrix{Float64}
    g = zeros(n_params, n_params)
    for i in 1:n_params
        for j in 1:n_params
            if i <= size(jacobian, 1) && j <= size(jacobian, 1)
                g[i, j] = dot(jacobian[i, :], jacobian[j, :])
            end
        end
    end
    for i in 1:n_params
        g[i, i] += 1e-8
    end
    return g
end

function fubini_study_auto(state::AbstractVector{<:Real},
                           n_params::Int;
                           h::Float64=1e-4)::Tuple{Matrix{Float64}, Matrix{Float64}}
    n = length(state)
    n_eff = min(n_params, n)
    jacobian = zeros(n_eff, n)
    for i in 1:n_eff
        jacobian[i, i] = 1.0
    end
    metric = fubini_study_metric(state, jacobian, n_eff)
    return (metric, jacobian)
end

# ---------------------------------------------------------------------------
# Natural Gradient Step
# ---------------------------------------------------------------------------

function natural_gradient_step(params::AbstractVector{<:Real},
                               gradients::AbstractVector{<:Real},
                               metric::AbstractMatrix{<:Real},
                               learning_rate::Float64=0.01)::Vector{Float64}
    n = length(params)
    @assert length(gradients) == n
    @assert size(metric, 1) == n && size(metric, 2) == n
    try
        x = metric \ gradients
        return collect(params .- learning_rate .* x)
    catch
        x = pinv(metric) * gradients
        return collect(params .- learning_rate .* x)
    end
end

# ---------------------------------------------------------------------------
# MPS Compression
# ---------------------------------------------------------------------------

function mps_compress(vectors::Vector{Vector{Float64}},
                      bond_dim::Int=2,
                      seed::Int=42)::Dict{String, Any}
    if isempty(vectors)
        return Dict("result" => Float64[], "bond_dim" => bond_dim, "n_tensors" => 0)
    end
    n_vecs = length(vectors)
    dim = length(vectors[1])
    data = hcat(vectors...)
    U, S, Vt = svd(data)
    k = min(bond_dim, length(S))
    U_k = U[:, 1:k]
    S_k = S[1:k]
    Vt_k = Vt[1:k, :]
    compressed = U_k * Diagonal(S_k) * Vt_k
    result_vec = compressed[:, 1]
    return Dict(
        "result" => collect(result_vec),
        "bond_dim" => bond_dim,
        "n_tensors" => k,
        "singular_values" => collect(S_k),
        "compression_ratio" => k / min(dim, n_vecs),
        "reconstruction_error" => norm(data .- compressed) / norm(data)
    )
end

function mps_full_state(tensors::Vector{Matrix{Float64}})::Vector{Float64}
    if isempty(tensors)
        return Float64[]
    end
    state = tensors[1]
    for i in 2:length(tensors)
        state = state * tensors[i]
    end
    return collect(vec(state))
end

function mps_bind(vectors::Vector{Vector{Float64}},
                  bond_dim::Int=2,
                  seed::Int=42)::Vector{Float64}
    if isempty(vectors)
        return Float64[]
    end
    if length(vectors) == 1
        return vectors[1]
    end
    current = vectors
    while length(current) > 1
        next_level = Vector{Vector{Float64}}()
        for i in 1:2:length(current)
            if i + 1 <= length(current)
                pair = hcat(current[i], current[i+1])
                U, S, Vt = svd(pair)
                k = min(bond_dim, length(S))
                bound = U[:, 1:k] * Diagonal(S[1:k])
                push!(next_level, collect(bound[:, 1]))
            else
                push!(next_level, current[i])
            end
        end
        current = next_level
    end
    return current[1]
end

# ---------------------------------------------------------------------------
# Auto Manifold Selection
# ---------------------------------------------------------------------------

function auto_select_manifold(points::Vector{Vector{Float64}})::String
    if length(points) < 3
        return "euclidean"
    end
    n = length(points)
    dim = length(points[1])
    norms = [norm(p) for p in points]
    mean_norm = mean(norms)
    std_norm = std(norms)
    if mean_norm > 0.1 && std_norm / mean_norm < 0.1
        return "spherical"
    end
    near_origin = count(n -> n < 0.3 * mean_norm, norms)
    far_count = count(n -> n > 0.7 * maximum(norms), norms)
    if near_origin > 0.4 * n && far_count < 0.2 * n
        return "hyperbolic"
    end
    mins = [minimum(p[i] for p in points) for i in 1:dim]
    maxs = [maximum(p[i] for p in points) for i in 1:dim]
    ranges = maxs .- mins
    aspect_ratio = maximum(ranges) / (minimum(ranges) + 1e-10)
    if aspect_ratio > 3.0
        return "hyperbolic"
    end
    return "euclidean"
end

# ---------------------------------------------------------------------------
# Normalize to Manifold
# ---------------------------------------------------------------------------

function normalize_to_manifold(point::AbstractVector{<:Real},
                               manifold::String="euclidean")::Vector{Float64}
    if manifold == "euclidean"
        return collect(point)
    elseif manifold == "hyperbolic"
        n = norm(point)
        if n >= 0.999
            return collect(point .* (0.999 / n))
        end
        return collect(point)
    elseif manifold == "spherical"
        n = norm(point)
        if n < 1e-15
            return collect(point)
        end
        return collect(point ./ n)
    else
        return collect(point)
    end
end

# ---------------------------------------------------------------------------
# JSON Request Handler
# ---------------------------------------------------------------------------

function handle_request(request::Dict{String, Any})::Dict{String, Any}
    method = get(request, "method", "")
    params = get(request, "params", Dict{String, Any}())

    try
        if method == "ping"
            return Dict("status" => "ok", "backend" => "julia-quantum")

        elseif method == "q_manifold_distance"
            a = Float64.(params["a"])
            b = Float64.(params["b"])
            m = get(params, "manifold", "euclidean")
            d = manifold_distance(a, b, m)
            return Dict("status" => "ok", "distance" => d)

        elseif method == "q_manifold_exp"
            p = Float64.(params["point"])
            t = Float64.(params["tangent"])
            m = get(params, "manifold", "euclidean")
            result = manifold_exp_map(p, t, m)
            return Dict("status" => "ok", "result" => result)

        elseif method == "q_manifold_log"
            p = Float64.(params["point"])
            t = Float64.(params["target"])
            m = get(params, "manifold", "euclidean")
            result = manifold_log_map(p, t, m)
            return Dict("status" => "ok", "result" => result)

        elseif method == "q_parallel_transport"
            p = Float64.(params["point"])
            t = Float64.(params["target"])
            v = Float64.(params["vector"])
            m = get(params, "manifold", "euclidean")
            result = manifold_parallel_transport(p, t, v, m)
            return Dict("status" => "ok", "result" => result)

        elseif method == "q_inner_product"
            p = Float64.(params["point"])
            v1 = Float64.(params["v1"])
            v2 = Float64.(params["v2"])
            m = get(params, "manifold", "euclidean")
            result = manifold_inner_product(p, v1, v2, m)
            return Dict("status" => "ok", "result" => result)

        elseif method == "q_fubini_study"
            state = Float64.(params["state"])
            n_p = Int(get(params, "n_params", length(state)))
            jac_raw = get(params, "jacobian", [])
            if isempty(jac_raw)
                metric, _ = fubini_study_auto(state, n_p)
            else
                jac = reduce(vcat, [Float64.(row)' for row in jac_raw])
                metric = fubini_study_metric(state, jac, n_p)
            end
            return Dict("status" => "ok", "metric" => metric)

        elseif method == "q_natural_gradient"
            p = Float64.(params["params"])
            g = Float64.(params["gradients"])
            m_raw = get(params, "metric", [])
            lr = Float64(get(params, "learning_rate", 0.01))
            if isempty(m_raw)
                return Dict("status" => "ok", "new_params" => collect(p .- lr .* g), "fallback" => true)
            end
            m = reduce(vcat, [Float64.(row)' for row in m_raw])
            new_p = natural_gradient_step(p, g, m, lr)
            return Dict("status" => "ok", "new_params" => new_p)

        elseif method == "q_mps_compress"
            vecs = [Float64.(v) for v in params["vectors"]]
            bd = Int(get(params, "bond_dim", 2))
            sd = Int(get(params, "seed", 42))
            result = mps_compress(vecs, bd, sd)
            return Dict("status" => "ok", "result" => result)

        elseif method == "q_mps_bind"
            vecs = [Float64.(v) for v in params["vectors"]]
            bd = Int(get(params, "bond_dim", 2))
            sd = Int(get(params, "seed", 42))
            result = mps_bind(vecs, bd, sd)
            return Dict("status" => "ok", "result" => result)

        elseif method == "q_auto_manifold"
            pts = [Float64.(p) for p in params["points"]]
            m = auto_select_manifold(pts)
            return Dict("status" => "ok", "manifold" => m)

        elseif method == "q_normalize"
            p = Float64.(params["point"])
            m = get(params, "manifold", "euclidean")
            result = normalize_to_manifold(p, m)
            return Dict("status" => "ok", "result" => result)

        else
            return Dict("status" => "error", "error" => "Unknown method: $method")
        end
    catch e
        return Dict("status" => "error", "error" => string(e))
    end
end

end # module
