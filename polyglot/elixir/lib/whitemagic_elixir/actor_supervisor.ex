defmodule WhiteMagicElixir.ActorSupervisor do
  @moduledoc """
  Supervisor for hypothesis actors.

  Manages actor lifecycle, restarts failed actors, and provides
  batch operations for the recursive improvement loop.
  """

  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {Registry, keys: :unique, name: WhiteMagicElixir.ActorRegistry},
      {DynamicSupervisor, strategy: :one_for_one, name: WhiteMagicElixir.ActorDynamicSupervisor}
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end

  # ---- Client API ----

  def start_actor(hypothesis_id, prior \\ 0.5) do
    spec = {WhiteMagicElixir.HypothesisActor, hypothesis_id: hypothesis_id, prior: prior}
    DynamicSupervisor.start_child(WhiteMagicElixir.ActorDynamicSupervisor, spec)
  end

  def send_outcome(hypothesis_id, success, gain \\ 0.0) do
    case Registry.lookup(WhiteMagicElixir.ActorRegistry, hypothesis_id) do
      [{pid, _}] -> WhiteMagicElixir.HypothesisActor.handle_outcome(pid, success, gain)
      [] -> nil
    end
  end

  def broadcast_outcome(success, gain \\ 0.0) do
    Registry.select(WhiteMagicElixir.ActorRegistry, [{{:"$1", :"$2", :_}, [], [{{:"$1", :"$2"}}]}])
    |> Enum.map(fn {id, pid} ->
      {id, WhiteMagicElixir.HypothesisActor.handle_outcome(pid, success, gain)}
    end)
    |> Map.new()
  end

  def transfer_belief(from_id, to_id, weight \\ 0.5) do
    case Registry.lookup(WhiteMagicElixir.ActorRegistry, to_id) do
      [{pid, _}] ->
        :ok = WhiteMagicElixir.HypothesisActor.transfer(pid, from_id, weight)
        true
      [] ->
        false
    end
  end

  def get_all_posteriors do
    Registry.select(WhiteMagicElixir.ActorRegistry, [{{:"$1", :"$2", :_}, [], [{{:"$1", :"$2"}}]}])
    |> Enum.map(fn {id, pid} ->
      state = WhiteMagicElixir.HypothesisActor.get_state(pid)
      {id, state.posterior}
    end)
    |> Map.new()
  end

  def get_stats do
    actors = Registry.select(WhiteMagicElixir.ActorRegistry, [{{:"$1", :"$2", :_}, [], [{{:"$1", :"$2"}}]}])

    total_outcomes = Enum.reduce(actors, 0, fn {_, pid}, acc ->
      state = WhiteMagicElixir.HypothesisActor.get_state(pid)
      acc + state.outcome_count
    end)

    %{
      total_actors: length(actors),
      active_actors: length(actors),
      total_outcomes: total_outcomes
    }
  end
end
