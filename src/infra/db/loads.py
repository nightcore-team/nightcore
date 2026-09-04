"""Predefined eager-loading options for SQLAlchemy relationships."""

from sqlalchemy.orm import Load

from src.infra.db.models.bank import BankAccount
from src.infra.db.models.user import User, UserCase

user_load_cases: Load = (
    Load(User).selectinload(User.cases).selectinload(UserCase.item)
)

user_load_colors: Load = Load(User).selectinload(User.colors)

user_load_bank_account: Load = (
    Load(User)
    .selectinload(User.bank_account)
    .selectinload(BankAccount.deposit)
    .selectinload(BankAccount.extra_wallets)
)

user_load_casino_bets: Load = Load(User).selectinload(User.casino_bets)

user_load_cases_and_colors: list[Load] = [user_load_cases, user_load_colors]

user_load_all: list[Load] = [
    user_load_cases,
    user_load_colors,
    user_load_bank_account,
    user_load_casino_bets,
]
