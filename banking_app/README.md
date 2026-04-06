# Banking App (FastAPI)

Professional, clean starter for a **User + Banking Management System** with:

- JWT authentication (OAuth2 password flow)
- KYC simulation (PAN/Aadhaar)
- Roles: Admin / Customer
- Multi-account management (Savings / Current)
- Transaction engine (Deposit / Withdraw / Transfer)
- Atomic transaction flow with rollback handling
- Sliding-window fraud detection
- Loan module with EMI formula
- Notification hooks via background tasks
- Audit logging
- Rate limiting + async DB + Redis cache support

## Project Structure

```text
banking_app/
├── main.py
├── database.py
├── requirements.txt
├── .env.example
├── README.md
├── models/
│   ├── user.py
│   ├── account.py
│   ├── transaction.py
│   └── loan.py
├── schemas/
├── routes/
│   ├── auth.py
│   ├── account.py
│   ├── transaction.py
│   └── loan.py
├── services/
│   ├── fraud_detection.py
│   └── payment_service.py
├── utils/
│   ├── security.py
│   ├── logger.py
│   └── rate_limit.py
└── alembic/
```

## Setup

```bash
cd banking_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
cd banking_app
source .venv/bin/activate
uvicorn main:app --reload
```

Open:
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Seed Demo Data (Indian Context)

Populate users, PAN/Aadhaar KYC records, accounts, transactions (including transfers), and loans:

```bash
cd banking_app
/usr/bin/python3 scripts/seed_data.py --customers 20 --seed 42
```

Notes:
- Default mode resets existing tables before seeding.
- Admin credentials after seeding: `admin@bankingapp.in` / `Admin@123`
- Customer login password: `Customer@123`

To append data without clearing old records:

```bash
cd banking_app
/usr/bin/python3 scripts/seed_data.py --customers 10 --seed 101 --no-reset
```

## Core Teaching Concepts (DAA + System Design)

- **Sliding window** in `services/fraud_detection.py` for rapid transaction detection.
- **Atomicity / rollback** in `routes/transaction.py` (`async with db.begin()`).
- **Concurrency handling** with row-level lock attempts (`with_for_update()`).
- **EMI formula** implemented in `routes/loan.py`:

$$
EMI = \frac{P \cdot r \cdot (1+r)^n}{(1+r)^n - 1}
$$

Where:
- $P$ = principal
- $r$ = monthly interest rate
- $n$ = months

## Notes

- Redis is optional; if unavailable, cache falls back in-memory.
- SQLite is used by default for quick local development.
- For production, move to PostgreSQL and proper Alembic migrations.
- For microservices expansion, split routes into dedicated services:
  - Auth Service
  - Transaction Service
  - Notification Service
