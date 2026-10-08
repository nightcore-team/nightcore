"""Predefined eager-loading options for SQLAlchemy relationships."""

from sqlalchemy.orm import Load, selectinload

from src.infra.db.models import UserGlobalBadge, UserGuildBadge
from src.infra.db.models.bank import BankAccount
from src.infra.db.models.user import User, UserCase, UserVipStatus

user_load_cases: Load = (
    Load(User).selectinload(User.cases).selectinload(UserCase.item)
)

user_load_colors: Load = Load(User).selectinload(User.colors)

user_load_vip_statuses: Load = Load(User).selectinload(User.vip_statuses)

vip_status_load_vip: Load = Load(UserVipStatus).selectinload(UserVipStatus.vip)

user_load_vip_status_vip: Load = Load(UserVipStatus).options(
    selectinload(UserVipStatus.vip),
    selectinload(UserVipStatus.user),
)

user_load_bank_account_all: list[Load] = [
    Load(User)
    .selectinload(User.bank_account)
    .selectinload(BankAccount.deposit),
    Load(User)
    .selectinload(User.bank_account)
    .selectinload(BankAccount.extra_wallets),
]

user_load_bank_account_wallets: Load = (
    Load(User)
    .selectinload(User.bank_account)
    .selectinload(BankAccount.extra_wallets)
)

user_load_bank_account_only: Load = (
    Load(User)
    .selectinload(User.bank_account)
    .selectinload(BankAccount.deposit)
)

user_load_casino_bets: Load = Load(User).selectinload(User.casino_bets)

user_load_cases_and_colors: list[Load] = [user_load_cases, user_load_colors]

# give_reward_by_type decides whether a drop is a duplicate by walking the
# user's cases (with their item), colors and vip statuses, so every caller
# has to eager load exactly these. A lazy load there is a MissingGreenlet.
user_load_cases_colors_and_vips: list[Load] = [
    *user_load_cases_and_colors,
    user_load_vip_statuses,
]

user_load_guild_badges: Load = Load(User).selectinload(User.guild_badges)
user_guild_badge_load_badge: Load = Load(UserGuildBadge).selectinload(
    UserGuildBadge.badge
)
user_global_badge_load_badge: Load = Load(UserGlobalBadge).selectinload(
    UserGlobalBadge.badge
)
user_load_global_badges: Load = Load(User).selectinload(User.global_badges)
