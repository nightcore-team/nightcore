"""Regression tests for race condition fixes."""

import pathlib
import sys

# Ensure src is importable when running from repo root or parent
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _repo_path(rel: str) -> pathlib.Path:
    return ROOT / rel


def test_operations_support_for_update():
    """DB helpers must accept for_update param."""
    text = _repo_path("src/infra/db/operations.py").read_text(encoding="utf-8")
    for name in [
        "get_or_create_user",
        "get_specified_guild_config",
        "get_clan_member",
        "get_clan_by_id",
        "get_clan_by_name",
        "get_user_ticket",
        "get_ticket_state",
        "get_latest_user_role_request",
        "get_casino_game_by_message_id",
        "get_last_logging_revision",
        "get_custom_component_by_id",
    ]:
        # find def and check for_update in signature slice
        idx = text.find(f"async def {name}(")
        assert idx != -1, f"{name} not found"
        snippet = text[idx : idx + 600]
        assert "for_update" in snippet, f"{name} missing for_update"
        assert (
            "for_update: bool = False" in snippet
            or "for_update=False" in snippet
        )


def test_task_helpers_use_skip_locked():
    """Task selectors must use SKIP LOCKED."""
    text = _repo_path("src/infra/db/operations.py").read_text(encoding="utf-8")
    for fn in [
        "get_all_expired_temp_roles",
        "get_all_expired_temp_multipliers",
        "get_expired_temp_infractions",
        "get_active_casino_games",
        "get_due_rainbow_roles",
        "get_all_pending_notifications",
        "get_tickets_to_delete",
        "get_role_requests_to_delete",
    ]:
        idx = text.find(f"async def {fn}")
        assert idx != -1, f"{fn} not found"
        snippet = text[idx : idx + 900]
        assert "skip_locked=True" in snippet, f"{fn} missing skip_locked"


def test_pay_uses_ordered_for_update():
    """pay.py must lock sender/receiver in sorted order."""
    t = _repo_path("src/nightcore/features/economy/commands/pay.py").read_text(
        encoding="utf-8"
    )
    assert "for_update=True" in t
    assert "sorted([interaction.user.id, member.id])" in t
    assert t.count("for_update=True") >= 2
    assert t.count("async with specified_guild_config") == 1


def test_count_message_uses_for_update():
    txt = _repo_path(
        "src/nightcore/features/economy/events/count_message.py"
    ).read_text(encoding="utf-8")
    assert "get_or_create_user" in txt and "for_update=True" in txt


def test_battlepass_claim_uses_for_update():
    txt = _repo_path(
        "src/nightcore/features/economy/components/v2/view/handlers/battlepass/claim.py"
    ).read_text(encoding="utf-8")
    assert "for_update=True" in txt


def test_roulette_modal_uses_for_update_and_duplicate_check():
    txt = _repo_path(
        "src/nightcore/features/economy/components/modal/roulette.py"
    ).read_text(encoding="utf-8")
    assert "for_update=True" in txt
    assert "already_joined" in txt
    assert "already_in" in txt


def test_shop_handlers_lock_money_row():
    for p in [
        "src/nightcore/features/economy/components/v2/view/handlers/shop/approve.py",
        "src/nightcore/features/clans/components/v2/view/handlers/shop/approve.py",
    ]:
        t = _repo_path(p).read_text(encoding="utf-8")
        assert "for_update=True" in t, f"{p} missing lock"


def test_faq_and_proposals_lock_config():
    for p in [
        "src/nightcore/features/faq/components/modal/new_page.py",
        "src/nightcore/features/faq/components/modal/change_page.py",
        "src/nightcore/features/faq/commands/delete_page.py",
        "src/nightcore/features/proposals/events/proposal.py",
    ]:
        t = _repo_path(p).read_text(encoding="utf-8")
        assert "for_update=True" in t, p


def test_guild_state_and_logging_revision_lock():
    assert "for_update=True" in _repo_path(
        "src/nightcore/api/services/guild_state.py"
    ).read_text(encoding="utf-8")
    assert "for_update=True" in _repo_path(
        "src/nightcore/api/services/logging_revision.py"
    ).read_text(encoding="utf-8")


def test_no_asyncio_lock_for_db_races():
    """Ensure DB races are not fixed with asyncio.Lock."""
    forbidden = [
        "src/nightcore/features/economy/events/count_message.py",
        "src/nightcore/features/economy/commands/pay.py",
        "src/nightcore/features/economy/commands/reward.py",
        "src/nightcore/features/economy/components/v2/view/handlers/battlepass/claim.py",
        "src/nightcore/features/economy/components/modal/roulette.py",
    ]
    for p in forbidden:
        t = _repo_path(p).read_text(encoding="utf-8")
        assert "asyncio.Lock" not in t, f"{p} incorrectly uses asyncio.Lock"


def test_try_deduct_exists():
    text = _repo_path("src/infra/db/operations.py").read_text(encoding="utf-8")
    assert "async def try_deduct_user_coins" in text
    assert "UPDATE" in text and "User.coins" in text
