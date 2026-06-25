defmodule WhiteMagicElixir.GalaxyDiscovery do
  @moduledoc """
  Galaxy Discovery — discovers peer WhiteMagic instances and their galaxies.

  Uses a registry-based approach for local development. In production,
  this would use DNS-SD or a gossip protocol for peer discovery.

  ## Galaxy Sharing Protocol

  1. Discovery (this module) — find peers and their galaxies
  2. Request + Consent (GalaxyReplication) — negotiate sharing terms
  3. Export (Rust Arrow) — serialize galaxy to IPC bytes
  4. Transfer (Go gRPC) — stream Arrow bytes to peer
  5. Import (Rust Arrow) — deserialize and store
  """

  use GenServer

  defstruct peers: %{}, local_galaxies: MapSet.new(["universal"])

  # --- Public API ---

  def start_link(opts \\ []) do
    name = opts[:name]
    if name do
      GenServer.start_link(__MODULE__, opts, name: name)
    else
      GenServer.start_link(__MODULE__, opts)
    end
  end

  @doc "Register this instance as offering a galaxy for sharing."
  def offer_galaxy(pid \\ __MODULE__, galaxy_name) do
    GenServer.call(pid, {:offer, galaxy_name})
  end

  @doc "Revoke a galaxy offering."
  def revoke_galaxy(pid \\ __MODULE__, galaxy_name) do
    GenServer.call(pid, {:revoke, galaxy_name})
  end

  @doc "Register a discovered peer instance."
  def register_peer(pid \\ __MODULE__, peer_id, endpoint, galaxies \\ []) do
    GenServer.call(pid, {:register_peer, peer_id, endpoint, galaxies})
  end

  @doc "Unregister a peer."
  def unregister_peer(pid \\ __MODULE__, peer_id) do
    GenServer.call(pid, {:unregister_peer, peer_id})
  end

  @doc "List all known peers and their galaxies."
  def list_peers(pid \\ __MODULE__) do
    GenServer.call(pid, :list_peers)
  end

  @doc "List local galaxies offered for sharing."
  def local_galaxies(pid \\ __MODULE__) do
    GenServer.call(pid, :local_galaxies)
  end

  @doc "Find peers that offer a specific galaxy."
  def find_peers_with_galaxy(pid \\ __MODULE__, galaxy_name) do
    GenServer.call(pid, {:find_galaxy, galaxy_name})
  end

  # --- GenServer callbacks ---

  @impl true
  def init(_opts) do
    {:ok, %__MODULE__{}}
  end

  @impl true
  def handle_call({:offer, galaxy_name}, _from, state) do
    new_galaxies = MapSet.put(state.local_galaxies, galaxy_name)
    {:reply, :ok, %{state | local_galaxies: new_galaxies}}
  end

  @impl true
  def handle_call({:revoke, galaxy_name}, _from, state) do
    new_galaxies = MapSet.delete(state.local_galaxies, galaxy_name)
    {:reply, :ok, %{state | local_galaxies: new_galaxies}}
  end

  @impl true
  def handle_call({:register_peer, peer_id, endpoint, galaxies}, _from, state) do
    peer_info = %{
      id: peer_id,
      endpoint: endpoint,
      galaxies: MapSet.new(galaxies),
      discovered_at: DateTime.utc_now()
    }
    new_peers = Map.put(state.peers, peer_id, peer_info)
    {:reply, :ok, %{state | peers: new_peers}}
  end

  @impl true
  def handle_call({:unregister_peer, peer_id}, _from, state) do
    new_peers = Map.delete(state.peers, peer_id)
    {:reply, :ok, %{state | peers: new_peers}}
  end

  @impl true
  def handle_call(:list_peers, _from, state) do
    peers_list = Map.values(state.peers)
    {:reply, peers_list, state}
  end

  @impl true
  def handle_call(:local_galaxies, _from, state) do
    {:reply, MapSet.to_list(state.local_galaxies), state}
  end

  @impl true
  def handle_call({:find_galaxy, galaxy_name}, _from, state) do
    matching = state.peers
    |> Map.values()
    |> Enum.filter(fn peer -> MapSet.member?(peer.galaxies, galaxy_name) end)
    {:reply, matching, state}
  end
end
