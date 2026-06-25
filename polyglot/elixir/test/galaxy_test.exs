defmodule GalaxyDiscoveryTest do
  use ExUnit.Case, async: true

  alias WhiteMagicElixir.GalaxyDiscovery

  setup do
    {:ok, pid} = GalaxyDiscovery.start_link()
    {:ok, pid: pid}
  end

  test "starts with universal galaxy offered", %{pid: pid} do
    galaxies = GalaxyDiscovery.local_galaxies(pid)
    assert "universal" in galaxies
  end

  test "offer and revoke galaxies", %{pid: pid} do
    :ok = GalaxyDiscovery.offer_galaxy(pid, "oracle")
    galaxies = GalaxyDiscovery.local_galaxies(pid)
    assert "oracle" in galaxies

    :ok = GalaxyDiscovery.revoke_galaxy(pid, "oracle")
    galaxies = GalaxyDiscovery.local_galaxies(pid)
    refute "oracle" in galaxies
  end

  test "register and list peers", %{pid: pid} do
    :ok = GalaxyDiscovery.register_peer(pid, "peer_1", "localhost:4001", ["oracle", "insight"])
    peers = GalaxyDiscovery.list_peers(pid)
    assert length(peers) == 1
    assert hd(peers).id == "peer_1"
  end

  test "unregister peer", %{pid: pid} do
    :ok = GalaxyDiscovery.register_peer(pid, "peer_1", "localhost:4001", ["oracle"])
    :ok = GalaxyDiscovery.unregister_peer(pid, "peer_1")
    peers = GalaxyDiscovery.list_peers(pid)
    assert length(peers) == 0
  end

  test "find peers with specific galaxy", %{pid: pid} do
    :ok = GalaxyDiscovery.register_peer(pid, "peer_1", "localhost:4001", ["oracle", "insight"])
    :ok = GalaxyDiscovery.register_peer(pid, "peer_2", "localhost:4002", ["oracle"])

    oracle_peers = GalaxyDiscovery.find_peers_with_galaxy(pid, "oracle")
    assert length(oracle_peers) == 2

    insight_peers = GalaxyDiscovery.find_peers_with_galaxy(pid, "insight")
    assert length(insight_peers) == 1
    assert hd(insight_peers).id == "peer_1"
  end
end

defmodule GalaxyReplicationTest do
  use ExUnit.Case, async: true

  alias WhiteMagicElixir.GalaxyReplication

  setup do
    {:ok, pid} = GalaxyReplication.start_link()
    {:ok, pid: pid}
  end

  test "starts in idle state", %{pid: pid} do
    status = GalaxyReplication.status(pid)
    assert status.state == :idle
  end

  test "request galaxy with auto-consent", %{pid: pid} do
    {:ok, token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle", auto_consent: true)
    status = GalaxyReplication.status(pid)
    assert status.state == :consented
    assert status.peer_id == "peer_1"
    assert status.galaxy_name == "oracle"
    assert byte_size(token) > 0
  end

  test "request galaxy requires consent", %{pid: pid} do
    {:consent_required, token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle")
    status = GalaxyReplication.status(pid)
    assert status.state == :requesting
    assert byte_size(token) > 0
  end

  test "grant consent transitions to consented", %{pid: pid} do
    {:consent_required, token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle")
    :ok = GalaxyReplication.grant_consent(pid, token)
    status = GalaxyReplication.status(pid)
    assert status.state == :consented
  end

  test "deny consent transitions to denied", %{pid: pid} do
    {:consent_required, token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle")
    :ok = GalaxyReplication.deny_consent(pid, token, "policy_violation")
    status = GalaxyReplication.status(pid)
    assert status.state == :denied
    assert status.error == "policy_violation"
  end

  test "invalid consent token rejected", %{pid: pid} do
    {:consent_required, _token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle")
    result = GalaxyReplication.grant_consent(pid, "invalid_token")
    assert {:error, :invalid_token} = result
  end

  test "complete transitions to complete", %{pid: pid} do
    {:ok, _token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle", auto_consent: true)
    :ok = GalaxyReplication.complete(pid, %{memories_imported: 42})
    status = GalaxyReplication.status(pid)
    assert status.state == :complete
    assert status.stats[:memories_imported] == 42
  end

  test "fail transitions to failed", %{pid: pid} do
    {:ok, _token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle", auto_consent: true)
    :ok = GalaxyReplication.fail(pid, "transfer_timeout")
    status = GalaxyReplication.status(pid)
    assert status.state == :failed
    assert status.error == "transfer_timeout"
  end

  test "busy when already requesting", %{pid: pid} do
    {:consent_required, _token} = GalaxyReplication.request_galaxy(pid, "peer_1", "oracle")
    result = GalaxyReplication.request_galaxy(pid, "peer_2", "insight")
    assert {:error, :busy} = result
  end
end
