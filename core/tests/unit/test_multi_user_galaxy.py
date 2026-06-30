"""Tests for multi-user galaxy isolation (v23.2).

Verifies that:
- LocalProfileManager creates per-user directories
- GalaxyManager isolates galaxies per user_id
- Users cannot see or switch to each other's galaxies
- Backward compat: no user_id defaults to "local" user
"""

import pytest


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Create an isolated WM_STATE_ROOT for testing."""
    state_root = tmp_path / "wm_state"
    state_root.mkdir(parents=True, exist_ok=True)

    # Patch paths module — it computes paths at import time
    import whitemagic.config.paths as paths_mod

    monkeypatch.setattr(paths_mod, "WM_ROOT", state_root)
    memory_dir = state_root / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths_mod, "MEMORY_DIR", memory_dir)

    # Patch galaxy_manager's module-level _REGISTRY_PATH
    import whitemagic.core.memory.galaxy_manager as gm_mod

    registry_path = state_root / "galaxies.json"
    monkeypatch.setattr(gm_mod, "_REGISTRY_PATH", registry_path)

    # Patch user_profile's get_users_dir / get_user_dir to use state_root
    import whitemagic.core.user_profile as up_mod

    users_dir = state_root / "users"
    monkeypatch.setattr(up_mod, "get_users_dir", lambda: users_dir)
    monkeypatch.setattr(up_mod, "get_user_dir", lambda uid: users_dir / uid)

    # Clear singleton caches
    from whitemagic.core.memory.galaxy_manager import GalaxyManager
    from whitemagic.core.user_profile import LocalProfileManager

    GalaxyManager._instance = None
    LocalProfileManager._instance = None

    yield state_root

    # Cleanup
    GalaxyManager._instance = None
    LocalProfileManager._instance = None


class TestLocalProfileManager:
    """Tests for LocalProfileManager."""

    def test_default_user_is_local(self, isolated_state):
        """get_or_create with no args returns 'local' user."""
        from whitemagic.core.user_profile import get_profile_manager

        pm = get_profile_manager()
        profile = pm.get_or_create()
        assert profile.user_id == "local"
        assert profile.user_dir.exists()
        assert profile.galaxies_dir.exists()

    def test_create_new_user(self, isolated_state):
        """Creating a new user sets up directories."""
        from whitemagic.core.user_profile import get_profile_manager

        pm = get_profile_manager()
        profile = pm.get_or_create("alice")
        assert profile.user_id == "alice"
        assert profile.user_dir.exists()
        assert profile.galaxies_dir.exists()
        assert profile.profile_path.exists()

    def test_get_existing_user(self, isolated_state):
        """Getting an existing user returns the same profile."""
        from whitemagic.core.user_profile import get_profile_manager

        pm = get_profile_manager()
        p1 = pm.get_or_create("bob")
        p2 = pm.get_or_create("bob")
        assert p1.user_id == p2.user_id == "bob"

    def test_list_profiles(self, isolated_state):
        """list_profiles returns all known users."""
        from whitemagic.core.user_profile import get_profile_manager

        pm = get_profile_manager()
        pm.get_or_create("alice")
        pm.get_or_create("bob")
        pm.get_or_create()  # local
        profiles = pm.list_profiles()
        user_ids = [p["user_id"] for p in profiles]
        assert "alice" in user_ids
        assert "bob" in user_ids
        assert "local" in user_ids

    def test_delete_profile(self, isolated_state):
        """Deleting a profile removes it from memory."""
        from whitemagic.core.user_profile import get_profile_manager

        pm = get_profile_manager()
        pm.get_or_create("alice")
        assert pm.delete_profile("alice") is True
        assert pm.get_profile("alice") is None

    def test_cannot_delete_default_user(self, isolated_state):
        """Cannot delete the 'local' default user."""
        from whitemagic.core.user_profile import get_profile_manager

        pm = get_profile_manager()
        pm.get_or_create()
        with pytest.raises(ValueError, match="Cannot delete the default"):
            pm.delete_profile("local")

    def test_sanitize_user_id(self, isolated_state):
        """Unsafe characters are sanitized."""
        from whitemagic.core.user_profile import resolve_user_id

        assert resolve_user_id("user@domain") == "user_domain"
        assert resolve_user_id("alice/bob") == "alice_bob"
        assert resolve_user_id(None) == "local"
        assert resolve_user_id("") == "local"


class TestGalaxyManagerMultiUser:
    """Tests for GalaxyManager per-user isolation."""

    def test_default_galaxy_exists_for_local_user(self, isolated_state):
        """The 'local/default' galaxy always exists."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        assert "local/default" in gm._galaxies
        assert gm.get_active().name == "default"

    def test_create_galaxy_for_user(self, isolated_state):
        """Creating a galaxy for a user stores it under their namespace."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        info = gm.create_galaxy(name="project-x", user_id="alice")
        assert info.user_id == "alice"
        assert "alice/project-x" in gm._galaxies
        assert "alice" in info.db_path

    def test_users_have_isolated_galaxies(self, isolated_state):
        """Two users can have galaxies with the same name."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        alice_info = gm.create_galaxy(name="my-project", user_id="alice")
        bob_info = gm.create_galaxy(name="my-project", user_id="bob")
        assert alice_info.db_path != bob_info.db_path
        assert "alice" in alice_info.db_path
        assert "bob" in bob_info.db_path

    def test_list_galaxies_filtered_by_user(self, isolated_state):
        """list_galaxies only returns galaxies for the specified user."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="alice-galaxy", user_id="alice")
        gm.create_galaxy(name="bob-galaxy", user_id="bob")

        alice_galaxies = gm.list_galaxies(user_id="alice")
        assert len(alice_galaxies) == 1
        assert alice_galaxies[0]["name"] == "alice-galaxy"
        assert alice_galaxies[0]["user_id"] == "alice"

        bob_galaxies = gm.list_galaxies(user_id="bob")
        assert len(bob_galaxies) == 1
        assert bob_galaxies[0]["name"] == "bob-galaxy"

    def test_switch_galaxy_within_user_namespace(self, isolated_state):
        """A user can switch to their own galaxy."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="project-x", user_id="alice")
        info = gm.switch_galaxy("project-x", user_id="alice")
        assert info.name == "project-x"
        assert gm._active_galaxy == "alice/project-x"

    def test_cannot_switch_to_other_users_galaxy(self, isolated_state):
        """A user cannot switch to another user's galaxy."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="alice-secret", user_id="alice")
        with pytest.raises(ValueError, match="not found for user 'bob'"):
            gm.switch_galaxy("alice-secret", user_id="bob")

    def test_delete_galaxy_within_user_namespace(self, isolated_state):
        """A user can delete their own galaxy."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="temp-project", user_id="alice")
        assert gm.delete_galaxy("temp-project", user_id="alice") is True
        assert "alice/temp-project" not in gm._galaxies

    def test_cannot_delete_other_users_galaxy(self, isolated_state):
        """A user cannot delete another user's galaxy."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="alice-galaxy", user_id="alice")
        with pytest.raises(ValueError, match="not found for user 'bob'"):
            gm.delete_galaxy("alice-galaxy", user_id="bob")

    def test_get_galaxy_user_aware(self, isolated_state):
        """get_galaxy respects user_id namespace."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="my-galaxy", user_id="alice")
        assert gm.get_galaxy("my-galaxy", user_id="alice") is not None
        assert gm.get_galaxy("my-galaxy", user_id="bob") is None

    def test_backward_compat_no_user_id(self, isolated_state):
        """Calling methods without user_id defaults to 'local' user."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        info = gm.create_galaxy(name="default-project")
        assert info.user_id == "local"
        assert "local/default-project" in gm._galaxies

    def test_status_filtered_by_user(self, isolated_state):
        """status() with user_id only counts that user's galaxies."""
        from whitemagic.core.memory.galaxy_manager import get_galaxy_manager

        gm = get_galaxy_manager()
        gm.create_galaxy(name="a1", user_id="alice")
        gm.create_galaxy(name="a2", user_id="alice")
        gm.create_galaxy(name="b1", user_id="bob")

        alice_status = gm.status(user_id="alice")
        alice_galaxies = alice_status["galaxies"]
        assert all(g["user_id"] == "alice" for g in alice_galaxies)
        assert len(alice_galaxies) == 2
