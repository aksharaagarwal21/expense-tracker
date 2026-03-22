# Spendly — Full Stack Expense Tracker
### Flask + MySQL + Vanilla JS

---

## 📁 Project Structure

```
spendly-fullstack/
├── backend/                  ← Flask API Server
│   ├── app.py                ← Entry point (run this)
│   ├── .env                  ← ⚠️ EDIT THIS with your MySQL password
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings.py       ← All config loaded from .env
│   │   └── database.py       ← SQLAlchemy setup
│   ├── models/               ← Database models
│   ├── middleware/            ← JWT auth
│   ├── routes/               ← All API endpoints
│   └── utils/                ← Helpers
│
├── frontend/
│   └── index.html            ← Open this in browser
│
├── setup.bat                 ← Windows auto-setup script
└── README.md
```

---

## ⚡ Quick Start (3 Steps)

### Step 1 — Edit your MySQL password

Open `backend/.env` and change:
```
MYSQL_PASSWORD=YOUR_MYSQL_PASSWORD_HERE
```

### Step 2 — Install & Setup

**Option A — Run the setup script (Windows):**
```
Double-click setup.bat
```

**Option B — Manual:**
```powershell
cd backend
pip install -r requirements.txt
```

Then create the database in MySQL:
```sql
CREATE DATABASE spendly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then create tables:
```powershell
python app.py
```
(It will auto-create all tables on first run and print "✅ Tables created")

### Step 3 — Run

**Terminal 1 — Start Flask backend:**
```powershell
cd backend
python app.py
```
You should see: `🚀 Spendly API running at http://localhost:5000`

**Browser — Open the frontend:**
```
Open frontend/index.html in your browser
```

That's it! Register an account and start tracking.

---

## 🔑 Demo Account

You can create any account via Register, or use the "Use Demo Account" button on the login screen after seeding demo data.

To create a demo user manually, register with:
- Email: `demo@spendly.app`
- Password: `Demo@123`

---

## 🌐 API Endpoints

| Module        | Base URL              |
|---------------|-----------------------|
| Auth          | `/api/auth`           |
| Transactions  | `/api/transactions`   |
| Budgets       | `/api/budgets`        |
| Bills         | `/api/bills`          |
| Payments      | `/api/payments`       |
| Dashboard     | `/api/dashboard`      |
| Health check  | `/api/health`         |

---

## 💳 Payment Integration

### Razorpay
1. Get keys from [razorpay.com](https://razorpay.com)
2. Add to `backend/.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxx
   RAZORPAY_KEY_SECRET=your_secret
   ```
3. Call `/api/payments/razorpay/create-order` then verify at `/api/payments/razorpay/verify`

### Stripe
1. Get keys from [stripe.com](https://stripe.com)
2. Add to `backend/.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_xxxx
   STRIPE_PUBLISHABLE_KEY=pk_test_xxxx
   ```

---

## 🚀 Changing the API URL

If you deploy the backend to a server, update this line in `frontend/index.html`:
```javascript
const API = "http://localhost:5000/api";
// Change to:
const API = "https://your-server.com/api";
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `pip install` error | Run: `pip install -r requirements.txt --break-system-packages` |
| MySQL connection error | Check MYSQL_PASSWORD in `.env`, ensure MySQL is running |
| CORS error in browser | Make sure Flask is running on port 5000 |
| Tables don't exist | Run `python app.py` once — it auto-creates all tables |
| "Token expired" | Click logout and log back in |
