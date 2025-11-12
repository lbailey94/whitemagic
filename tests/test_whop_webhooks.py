from __future__ import annotations

import os
from datetime import datetime
from typing import Dict
import hashlib
import hmac

import pytest
import pytest_asyncio
from sqlalchemy import select

from whitemagic.api.database import Database, User, APIKey, Quota
from whitemagic.api.routes.whop import (
    handle_membership_created,
    handle_membership_updated,
    handle_membership_deleted,
    handle_membership_went_valid,
    handle_membership_went_invalid,
)
from whitemagic.api.whop import WhopClient

os.environ.setdefault("WHOP_WEBHOOK_SECRET", "test_secret")

def _event(user: str, membership: str, plan: str = "plan_pro") -> Dict[str, str]:
    return {
        "user": user,
        "id": membership,
        "email": f"{user}@example.com",
        "plan": plan,
        "status": "active",
        "valid": True,
    }


@pytest_asyncio.fixture
async def database(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path/'whop.db'}"
    db = Database(db_url)
    await db.create_tables()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def session(database):
    async with database.get_session() as session:
        yield session


@pytest.mark.asyncio
async def test_membership_created(database, session):
    user = await handle_membership_created(_event("alice", "mem_alice"), session)

    result = await session.execute(select(APIKey).where(APIKey.user_id == user.id))
    assert result.scalar_one_or_none() is not None

    result = await session.execute(select(Quota).where(Quota.user_id == user.id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_membership_updated_changes_plan(session):
    user = User(
        email="bob@example.com",
        whop_user_id="user_bob",
        whop_membership_id="mem_bob",
        plan_tier="starter",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await handle_membership_updated(_event("user_bob", "mem_bob", plan="plan_enterprise"), session)
    await session.refresh(user)
    assert user.plan_tier == "enterprise"


@pytest.mark.asyncio
async def test_membership_deleted_downgrades_and_clears_id(session):
    user = User(
        email="carol@example.com",
        whop_user_id="user_carol",
        whop_membership_id="mem_carol",
        plan_tier="pro",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await handle_membership_deleted(_event("user_carol", "mem_carol"), session)
    await session.refresh(user)
    assert user.plan_tier == "free"
    assert user.whop_membership_id is None


@pytest.mark.asyncio
async def test_membership_went_valid_restores_plan(session):
    user = User(
        email="dan@example.com",
        whop_user_id="user_dan",
        whop_membership_id="mem_dan",
        plan_tier="free",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await handle_membership_went_valid(_event("user_dan", "mem_dan", plan="plan_pro"), session)
    await session.refresh(user)
    assert user.plan_tier == "pro"


@pytest.mark.asyncio
async def test_membership_went_invalid_sets_free(session):
    user = User(
        email="eve@example.com",
        whop_user_id="user_eve",
        whop_membership_id="mem_eve",
        plan_tier="pro",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await handle_membership_went_invalid(_event("user_eve", "mem_eve"), session)
    await session.refresh(user)
    assert user.plan_tier == "free"


def test_signature_verification():
    client = WhopClient()
    payload = {"id": "evt_test", "timestamp": int(datetime.utcnow().timestamp())}
    payload_bytes = str(payload).encode()
    signature = hmac.new(
        client.webhook_secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    assert client.verify_webhook_signature(payload_bytes, signature)
    assert not client.verify_webhook_signature(payload_bytes, "bad-signature")
