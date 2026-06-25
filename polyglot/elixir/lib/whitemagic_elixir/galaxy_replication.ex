defmodule WhiteMagicElixir.GalaxyReplication do
  @moduledoc """
  Galaxy Replication — actor-based galaxy sharing with consent negotiation.

  Manages the replication of galaxies between WhiteMagic instances.
  Each replication session is an actor that negotiates consent via
  the Dharma system, then coordinates the export/transfer/import pipeline.

  ## Consent Protocol

  1. Request: Local instance requests a galaxy from a peer
  2. Consent: Dharma system evaluates the request against ethical rules
  3. Export: Peer serializes galaxy to Arrow IPC bytes
  4. Transfer: Galaxy bytes are transferred (via Go gRPC in production)
  5. Import: Local instance imports the galaxy memories
  6. Audit: Karma Ledger records the exchange

  ## States

  - `:idle` — No active replication
  - `:requesting` — Consent request sent
  - `:consented` — Consent granted, ready to transfer
  - `:transferring` — Galaxy data in transit
  - `:importing` — Importing received memories
  - `:complete` — Replication finished
  - `:denied` — Consent denied
  - `:failed` — Replication failed
  """

  use GenServer

  defstruct state: :idle,
            peer_id: nil,
            galaxy_name: nil,
            consent_token: nil,
            error: nil,
            stats: %{}

  # --- Public API ---

  def start_link(opts \\ []) do
    name = opts[:name]
    if name do
      GenServer.start_link(__MODULE__, opts, name: name)
    else
      GenServer.start_link(__MODULE__, opts)
    end
  end

  @doc "Request a galaxy from a peer. Initiates consent negotiation."
  def request_galaxy(pid \\ __MODULE__, peer_id, galaxy_name, opts \\ []) do
    GenServer.call(pid, {:request, peer_id, galaxy_name, opts}, 30_000)
  end

  @doc "Grant consent for a galaxy request (simulated Dharma response)."
  def grant_consent(pid \\ __MODULE__, consent_token) do
    GenServer.call(pid, {:grant, consent_token})
  end

  @doc "Deny consent for a galaxy request."
  def deny_consent(pid \\ __MODULE__, consent_token, reason \\ "unspecified") do
    GenServer.call(pid, {:deny, consent_token, reason})
  end

  @doc "Get current replication status."
  def status(pid \\ __MODULE__) do
    GenServer.call(pid, :status)
  end

  @doc "Complete replication after transfer/import."
  def complete(pid \\ __MODULE__, stats \\ %{}) do
    GenServer.call(pid, {:complete, stats})
  end

  @doc "Fail the current replication."
  def fail(pid \\ __MODULE__, reason) do
    GenServer.call(pid, {:fail, reason})
  end

  # --- GenServer callbacks ---

  @impl true
  def init(_opts) do
    {:ok, %__MODULE__{}}
  end

  @impl true
  def handle_call({:request, peer_id, galaxy_name, opts}, _from, state) do
    if state.state != :idle do
      {:reply, {:error, :busy}, state}
    else
      # Generate consent token
      consent_token = :crypto.strong_rand_bytes(16) |> Base.encode16()

      # Check Dharma consent (simulated — real impl would call Dharma system)
      auto_consent = Keyword.get(opts, :auto_consent, false)

      new_state = %{state |
        state: if(auto_consent, do: :consented, else: :requesting),
        peer_id: peer_id,
        galaxy_name: galaxy_name,
        consent_token: consent_token
      }

      result = if auto_consent do
        {:ok, consent_token}
      else
        {:consent_required, consent_token}
      end

      {:reply, result, new_state}
    end
  end

  @impl true
  def handle_call({:grant, consent_token}, _from, state) do
    if state.consent_token == consent_token and state.state == :requesting do
      {:reply, :ok, %{state | state: :consented}}
    else
      {:reply, {:error, :invalid_token}, state}
    end
  end

  @impl true
  def handle_call({:deny, consent_token, reason}, _from, state) do
    if state.consent_token == consent_token and state.state == :requesting do
      {:reply, :ok, %{state | state: :denied, error: reason}}
    else
      {:reply, {:error, :invalid_token}, state}
    end
  end

  @impl true
  def handle_call(:status, _from, state) do
    info = %{
      state: state.state,
      peer_id: state.peer_id,
      galaxy_name: state.galaxy_name,
      error: state.error,
      stats: state.stats
    }
    {:reply, info, state}
  end

  @impl true
  def handle_call({:complete, stats}, _from, state) do
    {:reply, :ok, %{state | state: :complete, stats: stats}}
  end

  @impl true
  def handle_call({:fail, reason}, _from, state) do
    {:reply, :ok, %{state | state: :failed, error: reason}}
  end
end
