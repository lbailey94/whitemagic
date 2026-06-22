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
      WhiteMagicElixir.HolographicMemory
    ]

    opts = [strategy: :one_for_one, name: WhiteMagicElixir.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
