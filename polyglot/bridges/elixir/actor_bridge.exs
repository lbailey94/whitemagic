# WhiteMagic Elixir Actor JSON stdio bridge
# Routes hypothesis actor operations to the BEAM GenServer-based actor system.
#
# Methods:
#   - ping
#   - start_actor: {"hypothesis_id": "h1", "prior": 0.5}
#   - send_outcome: {"hypothesis_id": "h1", "success": true, "gain": 2.0}
#   - broadcast_outcome: {"success": true, "gain": 1.0}
#   - transfer_belief: {"from_id": "h1", "to_id": "h2", "weight": 0.5}
#   - get_posteriors: {}
#   - get_stats: {}

defmodule WhiteMagic.ActorBridge do
  alias WhiteMagicElixir.ActorSupervisor

  def handle(req) do
    method = req["method"]
    p = req["params"] || %{}

    case method do
      "ping" ->
        %{status: "ok", backend: "elixir-actor"}

      "start_actor" ->
        hypothesis_id = p["hypothesis_id"]
        prior = p["prior"] || 0.5
        case ActorSupervisor.start_actor(hypothesis_id, prior) do
          {:ok, _pid} -> %{status: "ok", result: %{started: true, hypothesis_id: hypothesis_id}}
          {:error, {:already_started, _}} -> %{status: "ok", result: %{started: false, already_exists: true}}
          {:error, reason} -> %{status: "error", error: inspect(reason)}
        end

      "send_outcome" ->
        hypothesis_id = p["hypothesis_id"]
        success = p["success"]
        gain = p["gain"] || 0.0
        case ActorSupervisor.send_outcome(hypothesis_id, success, gain) do
          nil -> %{status: "error", error: "actor_not_found"}
          result -> %{status: "ok", result: result}
        end

      "broadcast_outcome" ->
        success = p["success"]
        gain = p["gain"] || 0.0
        results = ActorSupervisor.broadcast_outcome(success, gain)
        %{status: "ok", result: results}

      "transfer_belief" ->
        from_id = p["from_id"]
        to_id = p["to_id"]
        weight = p["weight"] || 0.5
        case ActorSupervisor.transfer_belief(from_id, to_id, weight) do
          true -> %{status: "ok", result: %{transferred: true}}
          false -> %{status: "error", error: "actor_not_found"}
        end

      "get_posteriors" ->
        posteriors = ActorSupervisor.get_all_posteriors()
        %{status: "ok", result: %{posteriors: posteriors}}

      "get_stats" ->
        stats = ActorSupervisor.get_stats()
        %{status: "ok", result: stats}

      _ ->
        %{status: "error", error: "Unknown method: #{method}"}
    end
  end

  def loop do
    case IO.read(:line) do
      :eof -> :ok
      line when is_binary(line) ->
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

WhiteMagic.ActorBridge.loop()
