#!/usr/bin/env elixir
# WhiteMagic Elixir Ripple Tagging Bridge
# JSON stdio protocol — tags memories with ripple markers based on co-activation
#
# Methods:
#   "ping" — health check
#   "tag_ripple" — tag memories with ripple markers from a co-activation event
#   "get_tags" — retrieve ripple tags for given memory IDs
#   "batch_tag" — process multiple co-activation events
#   "stats" — get ripple tagging statistics

defmodule WhiteMagic.RippleTagging do
  @moduledoc """
  Ripple tagging engine — marks memories that co-activate within a time window.
  Ripple-tagged memories get stronger consolidation priority during sleep.

  Based on research: sleep ripples elicit stronger reactivation than wake ripples.
  Ripple-tagged memories should be prioritized for transfer and strengthening.
  """

  # Agent state: stores tag registry
  use Agent

  defstruct [
    tags: %{},           # memory_id => list of ripple tags
    co_activations: [],  # recent co-activation events (ring buffer)
    stats: %{total_tags: 0, total_events: 0, ripples_detected: 0}
  ]

  @co_activation_window_ms 500   # memories within 500ms are co-active
  @min_co_activation_size 2      # need at least 2 memories for a ripple
  @ripple_strength_base 0.8      # base strength for ripple-tagged memories
  @decay_per_hour 0.05           # ripple strength decays 5% per hour

  def start_link(_opts) do
    Agent.start_link(fn -> %__MODULE__{} end, name: __MODULE__)
  end

  def handle(req) do
    method = req["method"]
    p = req["params"] || %{}

    case method do
      "ping" ->
        %{status: "ok", backend: "elixir_ripple_tagging"}

      "tag_ripple" ->
        memory_ids = p["memory_ids"] || []
        timestamp = p["timestamp"] || :os.system_time(:millisecond)
        galaxy = p["galaxy"] || "universal"
        emotional_weight = p["emotional_weight"] || 1.0

        result = tag_ripple(memory_ids, timestamp, galaxy, emotional_weight)
        %{status: "ok", result: result}

      "batch_tag" ->
        events = p["events"] || []
        results = Enum.map(events, fn ev ->
          memory_ids = ev["memory_ids"] || []
          timestamp = ev["timestamp"] || :os.system_time(:millisecond)
          galaxy = ev["galaxy"] || "universal"
          emotional_weight = ev["emotional_weight"] || 1.0
          tag_ripple(memory_ids, timestamp, galaxy, emotional_weight)
        end)
        %{status: "ok", results: results, total: length(results)}

      "get_tags" ->
        memory_ids = p["memory_ids"] || []
        tags = get_tags(memory_ids)
        %{status: "ok", tags: tags}

      "detect_ripples" ->
        # Detect ripple events from co-activation history
        window_ms = p["window_ms"] || @co_activation_window_ms
        ripples = detect_ripples(window_ms)
        %{status: "ok", ripples: ripples, count: length(ripples)}

      "decay_tags" ->
        hours = p["hours"] || 1.0
        decayed = decay_tags(hours)
        %{status: "ok", decayed_count: decayed}

      "stats" ->
        stats = Agent.get(__MODULE__, fn state -> state.stats end)
        tag_count = Agent.get(__MODULE__, fn state -> map_size(state.tags) end)
        %{status: "ok", stats: stats, tagged_memories: tag_count}

      _ ->
        %{status: "error", error: "Unknown method: #{method}"}
    end
  end

  defp tag_ripple(memory_ids, timestamp, galaxy, emotional_weight) do
    if length(memory_ids) < @min_co_activation_size do
      %{tagged: false, reason: "insufficient_co_activation"}
    else
      # Calculate ripple strength based on:
      # 1. Number of co-activating memories (more = stronger ripple)
      # 2. Emotional weight (emotionally salient events create stronger ripples)
      # 3. Galaxy affinity (cross-galaxy co-activation is rarer = stronger)
      co_activation_count = length(memory_ids)
      ripple_strength = @ripple_strength_base *
        (1.0 + :math.log(co_activation_count) * 0.2) *
        emotional_weight

      ripple_id = "ripple_#{timestamp}_#{:rand.uniform(999999)}"

      tag = %{
        ripple_id: ripple_id,
        timestamp: timestamp,
        galaxy: galaxy,
        strength: min(ripple_strength, 1.0),
        co_activation_count: co_activation_count,
        emotional_weight: emotional_weight
      }

      Agent.update(__MODULE__, fn state ->
        new_tags = Enum.reduce(memory_ids, state.tags, fn mid, acc ->
          Map.update(acc, mid, [tag], fn existing -> [tag | existing] end)
        end)

        new_co_activations = [
          %{memory_ids: memory_ids, timestamp: timestamp, galaxy: galaxy} |
          Enum.take(state.co_activations, 99)
        ]

        new_stats = %{state.stats |
          total_tags: state.stats.total_tags + length(memory_ids),
          total_events: state.stats.total_events + 1,
          ripples_detected: state.stats.ripples_detected + 1
        }

        %{state | tags: new_tags, co_activations: new_co_activations, stats: new_stats}
      end)

      %{tagged: true, ripple_id: ripple_id, strength: ripple_strength, tagged_count: length(memory_ids)}
    end
  end

  defp get_tags(memory_ids) do
    all_tags = Agent.get(__MODULE__, fn state -> state.tags end)
    Enum.map(memory_ids, fn mid ->
      tags = Map.get(all_tags, mid, [])
      %{memory_id: mid, ripple_count: length(tags), tags: tags}
    end)
  end

  defp detect_ripples(window_ms) do
    co_activations = Agent.get(__MODULE__, fn state -> state.co_activations end)

    # Group co-activations by time window
    sorted = Enum.sort_by(co_activations, & &1.timestamp)

    {ripples, _} = Enum.reduce(sorted, {[], nil}, fn event, {acc, last_window} ->
      case last_window do
        nil ->
          {[ [event] ], event}

        last_event ->
          if event.timestamp - last_event.timestamp <= window_ms do
            # Same ripple window
            {add_to_last(acc, event), event}
          else
            # New ripple window
            {acc ++ [ [event] ], event}
          end
      end
    end)

    # Only return ripples with >= 2 events
    valid_ripples = Enum.filter(ripples, fn events -> length(events) >= 2 end)

    Enum.map(valid_ripples, fn events ->
      memory_ids = Enum.flat_map(events, & &1.memory_ids) |> Enum.uniq()
      galaxies = Enum.map(events, & &1.galaxy) |> Enum.uniq()
      %{
        memory_count: length(memory_ids),
        event_count: length(events),
        galaxies: galaxies,
        cross_galaxy: length(galaxies) > 1,
        memory_ids: memory_ids
      }
    end)
  end

  defp add_to_last(acc, event) do
    case acc do
      [] -> [[event]]
      _ -> Enum.take(acc, length(acc) - 1) ++ [List.last(acc) ++ [event]]
    end
  end

  defp decay_tags(hours) do
    decay_factor = 1.0 - (@decay_per_hour * hours)

    Agent.get_and_update(__MODULE__, fn state ->
      decayed_count = state.tags
        |> Enum.map(fn {_mid, tags} -> length(tags) end)
        |> Enum.sum()

      new_tags = Enum.map(state.tags, fn {mid, tags} ->
        decayed = Enum.map(tags, fn tag ->
          %{tag | strength: tag.strength * decay_factor}
        end)
        |> Enum.filter(fn tag -> tag.strength > 0.05 end)  # prune very weak tags
        {mid, decayed}
      end)
      |> Enum.filter(fn {_, tags} -> tags != [] end)
      |> Map.new()

      {decayed_count, %{state | tags: new_tags}}
    end)
  end

  def loop do
    case IO.read(:line) do
      :eof -> :ok
      {:error, _} -> :ok
      line ->
        text = String.trim(line)
        if text == "" do
          loop()
        else
          try do
            req = Jason.decode!(text)
            resp = handle(req)
            IO.puts(Jason.encode!(resp))
          rescue
            e ->
              err = %{status: "error", error: Exception.message(e)}
              IO.puts(Jason.encode!(err))
          end
          loop()
        end
    end
  end
end

# Start the agent
{:ok, _} = WhiteMagic.RippleTagging.start_link([])

# Warmup
WhiteMagic.RippleTagging.handle(%{"method" => "ping", "params" => %{}})

WhiteMagic.RippleTagging.loop()
