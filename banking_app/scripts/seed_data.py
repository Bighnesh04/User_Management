from __future__ import annotations

import argparse
import random
import string
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import delete, select

from database import AsyncSessionLocal, init_db
from models.account import Account, AccountTypeEnum
from models.loan import Loan, LoanStatusEnum
from models.transaction import AuditLog, Transaction, TransactionStatusEnum, TransactionTypeEnum
from models.user import RoleEnum, User
from routes.loan import calculate_emi
from utils.security import get_password_hash

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Krishna", "Ishaan", "Reyansh", "Kabir",
    "Ananya", "Diya", "Saanvi", "Ira", "Aadhya", "Myra", "Sara", "Riya", "Ishita", "Kiara",
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Reddy", "Nair", "Iyer", "Gupta", "Singh", "Khan", "Mehta",
    "Joshi", "Das", "Yadav", "Choudhary", "Kapoor", "Agarwal", "Bose", "Mishra", "Jain", "Roy",
]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad",
    "Jaipur", "Lucknow", "Chandigarh", "Indore", "Bhopal", "Kochi", "Noida", "Surat",
]


def random_pan() -> str:
    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    digits = "".join(random.choices(string.digits, k=4))
    last = random.choice(string.ascii_uppercase)
    return f"{letters}{digits}{last}"


def random_aadhaar() -> str:
    return "".join(random.choices(string.digits, k=12))


def random_amount(min_value: int, max_value: int) -> Decimal:
    value = Decimal(random.uniform(min_value, max_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return value


async def clear_existing_data() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Transaction))
        await db.execute(delete(Loan))
        await db.execute(delete(Account))
        await db.execute(delete(AuditLog))
        await db.execute(delete(User))
        await db.commit()


async def seed_data(customers: int, seed: int, reset: bool) -> None:
    random.seed(seed)
    await init_db()

    if reset:
        await clear_existing_data()

    async with AsyncSessionLocal() as db:
        admin = User(
            full_name="Bighnesh Admin",
            email="admin@bankingapp.in",
            password_hash=get_password_hash("Admin@123"),
            role=RoleEnum.admin,
            pan_number=random_pan(),
            aadhaar_number=random_aadhaar(),
            kyc_verified=True,
        )
        db.add(admin)
        await db.flush()

        users: list[User] = []
        for i in range(customers):
            full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            user = User(
                full_name=full_name,
                email=f"customer{i+1}@bankingapp.in",
                password_hash=get_password_hash("Customer@123"),
                role=RoleEnum.customer,
                pan_number=random_pan(),
                aadhaar_number=random_aadhaar(),
                kyc_verified=True,
            )
            users.append(user)
            db.add(user)

        await db.flush()

        accounts: list[Account] = []
        for user in users:
            account_count = random.choice([1, 2])
            for _ in range(account_count):
                account_type = random.choice([AccountTypeEnum.savings, AccountTypeEnum.current])
                min_balance = Decimal("1000.00") if account_type == AccountTypeEnum.savings else Decimal("0.00")
                interest = Decimal("4.00") if account_type == AccountTypeEnum.savings else Decimal("0.00")
                initial_balance = random_amount(3000, 120000)
                account = Account(
                    account_number=f"AC{user.id}{int(datetime.utcnow().timestamp())}{random.randint(10, 99)}",
                    user_id=user.id,
                    account_type=account_type,
                    balance=initial_balance,
                    minimum_balance=min_balance,
                    annual_interest_rate=interest,
                )
                accounts.append(account)
                db.add(account)

        await db.flush()

        transactions_created = 0
        for account in accounts:
            for _ in range(random.randint(2, 5)):
                tx_type = random.choice([TransactionTypeEnum.deposit, TransactionTypeEnum.withdraw])
                amount = random_amount(500, 15000)
                location = random.choice(INDIAN_CITIES)

                if tx_type == TransactionTypeEnum.deposit:
                    account.balance = Decimal(account.balance) + amount
                    tx = Transaction(
                        transaction_type=TransactionTypeEnum.deposit,
                        source_account_id=None,
                        destination_account_id=account.id,
                        amount=amount,
                        status=TransactionStatusEnum.success,
                        location=location,
                        message="Seed deposit",
                    )
                    db.add(tx)
                    transactions_created += 1
                else:
                    after = Decimal(account.balance) - amount
                    if after >= Decimal(account.minimum_balance):
                        account.balance = after
                        tx = Transaction(
                            transaction_type=TransactionTypeEnum.withdraw,
                            source_account_id=account.id,
                            destination_account_id=None,
                            amount=amount,
                            status=TransactionStatusEnum.success,
                            location=location,
                            message="Seed withdraw",
                        )
                        db.add(tx)
                        transactions_created += 1

        if len(accounts) >= 2:
            for _ in range(max(5, len(accounts) // 2)):
                source, destination = random.sample(accounts, 2)
                amount = random_amount(1000, 50000)
                location = random.choice(INDIAN_CITIES)

                if random.random() < 0.15:
                    amount = random_amount(100000, 250000)

                remaining = Decimal(source.balance) - amount
                if remaining >= Decimal(source.minimum_balance):
                    source.balance = remaining
                    destination.balance = Decimal(destination.balance) + amount

                    tx = Transaction(
                        transaction_type=TransactionTypeEnum.transfer,
                        source_account_id=source.id,
                        destination_account_id=destination.id,
                        amount=amount,
                        status=TransactionStatusEnum.success,
                        location=location,
                        message="Seed transfer",
                    )
                    db.add(tx)
                    transactions_created += 1

        loans_created = 0
        for user in random.sample(users, k=max(1, len(users) // 3)):
            principal = random_amount(50000, 500000)
            annual_rate = Decimal(random.choice(["8.5", "9.2", "10.5", "11.0", "12.0"]))
            months = random.choice([12, 24, 36, 48, 60])
            status = random.choice([LoanStatusEnum.pending, LoanStatusEnum.approved, LoanStatusEnum.rejected])

            loan = Loan(
                user_id=user.id,
                principal=principal,
                annual_interest_rate=annual_rate,
                tenure_months=months,
                emi=calculate_emi(principal, annual_rate, months),
                status=status,
                approved_by=admin.email if status != LoanStatusEnum.pending else None,
            )
            db.add(loan)
            loans_created += 1

        db.add(
            AuditLog(
                user_id=admin.id,
                action="SEED_DATA",
                details=f"Seeded {len(users)} customers, {len(accounts)} accounts, {transactions_created} transactions, {loans_created} loans.",
            )
        )

        await db.commit()

        user_count = (await db.execute(select(User))).scalars().all()
        account_count = (await db.execute(select(Account))).scalars().all()
        transaction_count = (await db.execute(select(Transaction))).scalars().all()
        loan_count = (await db.execute(select(Loan))).scalars().all()

    print("\nSeed complete ✅")
    print(f"Admin login      : admin@bankingapp.in / Admin@123")
    print(f"Customer password: Customer@123")
    print(f"Users            : {len(user_count)}")
    print(f"Accounts         : {len(account_count)}")
    print(f"Transactions     : {len(transaction_count)}")
    print(f"Loans            : {len(loan_count)}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed banking database with Indian demo data")
    parser.add_argument("--customers", type=int, default=20, help="Number of customer users to create")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible data")
    parser.add_argument("--no-reset", action="store_true", help="Do not clear existing data before seeding")
    args = parser.parse_args()

    await seed_data(customers=args.customers, seed=args.seed, reset=not args.no_reset)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
