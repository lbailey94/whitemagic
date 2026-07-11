#!/usr/bin/env julia
# WhiteMagic Julia Neuromodulation Bridge
# JSON stdio protocol — computes DA/5HT/ACh modulatory signals
#
# Methods:
#   "ping" — health check
#   "compute" — compute neuromodulator levels from activity signals
#   "modulate" — apply modulation to a set of memories
#   "stats" — get neuromodulation statistics

using JSON

# ── Neuromodulator parameters ─────────────────────────────────────────────

# Dopamine (DA): reward prediction error, novelty seeking, motivation
# High DA → boost learning rate, prioritize novel/rewarding memories
const DA_BASELINE = 0.5
const DA_NOVELTY_WEIGHT = 0.3
const DA_REWARD_WEIGHT = 0.4
const DA_DECAY = 0.95  # per computation cycle

# Serotonin (5HT): mood regulation, patience, impulse control
# High 5HT → boost consolidation, prioritize stable/important memories
const SHT_BASELINE = 0.5
const SHT_STABILITY_WEIGHT = 0.3
const SHT_COHERENCE_WEIGHT = 0.3
const SHT_DECAY = 0.97

# Acetylcholine (ACh): attention, focus, memory encoding
# High ACh → boost attention, prioritize active-context memories
const ACH_BASELINE = 0.5
const ACH_FOCUS_WEIGHT = 0.4
const ACH_ACTIVITY_WEIGHT = 0.2
const ACH_DECAY = 0.93

# ── State ─────────────────────────────────────────────────────────────────

mutable struct NeuroState
    da::Float64
    sht::Float64
    ach::Float64
    total_computations::Int
    total_modulations::Int
end

const state = NeuroState(DA_BASELINE, SHT_BASELINE, ACH_BASELINE, 0, 0)

# ── Handlers ──────────────────────────────────────────────────────────────

function handle(req)
    method = req["method"]
    p = get(req, "params", Dict{String,Any}())

    if method == "ping"
        return Dict("status" => "ok", "backend" => "julia_neuromodulation")

    elseif method == "compute"
        # Inputs: novelty (0-1), reward (0-1), stability (0-1),
        #         coherence (0-1), focus (0-1), activity_level (0-1)
        novelty = get(p, "novelty", 0.5)
        reward = get(p, "reward", 0.5)
        stability = get(p, "stability", 0.5)
        coherence = get(p, "coherence", 0.5)
        focus = get(p, "focus", 0.5)
        activity = get(p, "activity_level", 0.5)

        # Decay current levels
        state.da *= DA_DECAY
        state.sht *= SHT_DECAY
        state.ach *= ACH_DECAY

        # Compute new levels
        da_signal = DA_NOVELTY_WEIGHT * novelty + DA_REWARD_WEIGHT * reward
        state.da = clamp(DA_BASELINE + state.da * 0.5 + da_signal, 0.0, 1.0)

        sht_signal = SHT_STABILITY_WEIGHT * stability + SHT_COHERENCE_WEIGHT * coherence
        state.sht = clamp(SHT_BASELINE + state.sht * 0.5 + sht_signal, 0.0, 1.0)

        ach_signal = ACH_FOCUS_WEIGHT * focus + ACH_ACTIVITY_WEIGHT * activity
        state.ach = clamp(ACH_BASELINE + state.ach * 0.5 + ach_signal, 0.0, 1.0)

        state.total_computations += 1

        return Dict(
            "status" => "ok",
            "da" => state.da,
            "sht" => state.sht,
            "ach" => state.ach,
            "da_signal" => da_signal,
            "sht_signal" => sht_signal,
            "ach_signal" => ach_signal,
            # Modulatory effects
            "learning_rate_boost" => state.da * 0.5,       # DA boosts learning
            "consolidation_priority" => state.sht * 0.7,    # 5HT boosts consolidation
            "attention_focus" => state.ach * 0.8,           # ACh boosts attention
            "novelty_seeking" => state.da * 0.3,            # DA drives novelty seeking
            "patience_factor" => state.sht * 0.4,           # 5HT increases patience
        )

    elseif method == "modulate"
        # Apply modulation to a list of memories
        memories = get(p, "memories", [])
        da = get(p, "da", state.da)
        sht = get(p, "sht", state.sht)
        ach = get(p, "ach", state.ach)

        modulated = []
        for mem in memories
            importance = get(mem, "importance", 0.5)
            novelty = get(mem, "novelty", 0.5)
            is_active = get(mem, "is_active", false)

            # DA modulates: boost novel and rewarding memories
            da_boost = da * novelty * 0.3

            # 5HT modulates: boost stable and important memories
            sht_boost = sht * importance * 0.2

            # ACh modulates: boost active-context memories
            ach_boost = ach * (1.0 if is_active else 0.0) * 0.4

            modulated_importance = clamp(importance + da_boost + sht_boost + ach_boost, 0.0, 1.0)

            push!(modulated, Dict(
                "memory_id" => get(mem, "memory_id", ""),
                "original_importance" => importance,
                "modulated_importance" => modulated_importance,
                "da_boost" => da_boost,
                "sht_boost" => sht_boost,
                "ach_boost" => ach_boost,
            ))
        end

        state.total_modulations += 1

        return Dict(
            "status" => "ok",
            "modulated" => modulated,
            "total" => length(modulated),
            "da" => da,
            "sht" => sht,
            "ach" => ach,
        )

    elseif method == "reset"
        state.da = DA_BASELINE
        state.sht = SHT_BASELINE
        state.ach = ACH_BASELINE
        return Dict("status" => "ok", "message" => "Neuromodulator levels reset")

    elseif method == "stats"
        return Dict(
            "status" => "ok",
            "da" => state.da,
            "sht" => state.sht,
            "ach" => state.ach,
            "total_computations" => state.total_computations,
            "total_modulations" => state.total_modulations,
        )

    else
        return Dict("status" => "error", "error" => "Unknown method: $method")
    end
end

# ── Main loop ─────────────────────────────────────────────────────────────

# Warmup
handle(Dict("method" => "ping", "params" => Dict()))

while true
    line = readline()
    if isempty(strip(line))
        continue
    end
    try
        req = JSON.parse(line)
        resp = handle(req)
        println(JSON.json(resp))
    catch e
        println(JSON.json(Dict("status" => "error", "error" => string(e))))
    end
end
