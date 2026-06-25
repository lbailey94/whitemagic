defmodule WhitemagicElixir.MixProject do
  use Mix.Project

  def project do
    [
      app: :whitemagic_elixir,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: [
        {:jason, "~> 1.4"}
      ]
    ]
  end

  def application do
    [
      extra_applications: [:logger, :crypto],
      mod: {WhiteMagicElixir.Application, []}
    ]
  end
end
