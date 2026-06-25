defmodule WhiteMagicElixir.Application do
  @moduledoc """
  OTP Application for WhiteMagicElixir.

  Starts the holographic memory supervision tree.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Holographic memory GenServer
      WhiteMagicElixir.HolographicMemory,
      # Actor supervisor for hypothesis actors
      WhiteMagicElixir.ActorSupervisor,
      # v23.1: Galaxy discovery and replication
      {WhiteMagicElixir.GalaxyDiscovery, name: WhiteMagicElixir.GalaxyDiscovery},
      {WhiteMagicElixir.GalaxyReplication, name: WhiteMagicElixir.GalaxyReplication}
    ]

    opts = [strategy: :one_for_one, name: WhiteMagicElixir.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
