defmodule WhiteMagicElixir.HypothesisActor do
  @moduledoc """
  GenServer actor for a single improvement hypothesis.

  Tracks Bayesian beliefs (Beta distribution) and processes outcome messages.
  This is the Elixir native implementation of the Python HypothesisActor.
  """

  use GenServer

  # ---- Client API ----

  def start_link(opts) do
    hypothesis_id = Keyword.fetch!(opts, :hypothesis_id)
    prior = Keyword.get(opts, :prior, 0.5)
    GenServer.start_link(__MODULE__, %{hypothesis_id: hypothesis_id, prior: prior},
      name: via_tuple(hypothesis_id)
    )
  end

  def handle_outcome(pid_or_id, success, gain \\ 0.0) do
    GenServer.call(via(pid_or_id), {:outcome, success, gain})
  end

  def query(pid_or_id, field) do
    GenServer.call(via(pid_or_id), {:query, field})
  end

  def transfer(pid_or_id, from_id, weight \\ 0.5) do
    GenServer.call(via(pid_or_id), {:transfer, from_id, weight})
  end

  def get_state(pid_or_id) do
    GenServer.call(via(pid_or_id), :get_state)
  end

  defp via_tuple(hypothesis_id) do
    {:via, Registry, {WhiteMagicElixir.ActorRegistry, hypothesis_id}}
  end

  defp via({:via, _, _} = ref), do: ref
  defp via(pid) when is_pid(pid), do: pid
  defp via(id) when is_binary(id), do: via_tuple(id)

  # ---- Server callbacks ----

  @impl true
  def init(%{hypothesis_id: hypothesis_id, prior: prior}) do
    state = %{
      hypothesis_id: hypothesis_id,
      prior: prior,
      posterior: prior,
      outcome_count: 0,
      success_count: 0,
      confidence: 0.5,
      alpha: 1.0,
      beta: 1.0,
      last_update: System.system_time(:second)
    }
    {:ok, state}
  end

  @impl true
  def handle_call({:outcome, success, _gain}, _from, state) do
    state = %{state |
      outcome_count: state.outcome_count + 1,
      success_count: state.success_count + if(success, do: 1, else: 0),
      alpha: state.alpha + if(success, do: 1.0, else: 0.0),
      beta: state.beta + if(success, do: 0.0, else: 1.0),
      last_update: System.system_time(:second)
    }

    total = state.alpha + state.beta
    state = %{state |
      posterior: state.alpha / total,
      confidence: 1.0 - 1.0 / (1.0 + total * 0.1)
    }

    result = %{
      posterior: state.posterior,
      confidence: state.confidence,
      outcome_count: state.outcome_count,
      success_rate: if(state.outcome_count > 0,
        do: state.success_count / state.outcome_count, else: 0.0)
    }

    {:reply, result, state}
  end

  @impl true
  def handle_call({:query, field}, _from, state) do
    value = Map.get(state, String.to_existing_atom(field))
    {:reply, value, state}
  end

  @impl true
  def handle_call({:transfer, from_id, weight}, _from, state) do
    case Registry.lookup(WhiteMagicElixir.ActorRegistry, from_id) do
      [{pid, _}] ->
        from_state = GenServer.call(pid, :get_state)
        blended_prior = weight * from_state.prior + (1 - weight) * state.prior
        blended_alpha = weight * from_state.alpha + (1 - weight) * state.alpha
        blended_beta = weight * from_state.beta + (1 - weight) * state.beta

        total = blended_alpha + blended_beta
        state = %{state |
          prior: blended_prior,
          alpha: max(0.1, blended_alpha),
          beta: max(0.1, blended_beta),
          posterior: max(0.1, blended_alpha) / total
        }
        {:reply, :ok, state}

      [] ->
        {:reply, {:error, :not_found}, state}
    end
  end

  @impl true
  def handle_call(:get_state, _from, state) do
    {:reply, state, state}
  end
end
