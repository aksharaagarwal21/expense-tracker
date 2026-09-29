# Spendly · Expense Tracker

A full-stack personal finance app to track transactions, budgets and bills.

## Features

- Register and log in with JWT access and refresh tokens
- Add, edit and categorise income and expense transactions
- Monthly budgets with a spending overview
- Bill reminders with due dates and payment marking
- Dashboard summary
- Payment endpoints for Razorpay and Stripe, and saved cards

## Tech stack

Python · Flask · SQLAlchemy · MySQL · JWT · HTML, CSS and JavaScript

## Run locally

The app lives in [spendly-fullstack/](spendly-fullstack), and its [README](spendly-fullstack/README.md) has the full setup steps. In short:

```bash
cd spendly-fullstack/backend
pip install -r requirements.txt
# create a .env file with your MySQL settings (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
python app.py
```

Then open `spendly-fullstack/frontend/index.html` in a browser. The API runs on http://localhost:5000.
