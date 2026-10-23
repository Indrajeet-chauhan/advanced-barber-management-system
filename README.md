# Advanced Barber Management System (Python + AIML + DBMS)

A beginner-friendly Flask web application for a barber shop / salon. Includes customer records, appointment booking, staff, services and pricing, inventory with low-stock warnings, billing with discount/tax calculations, reports, and an AI/ML help chatbot.

## Technology
- Python + Flask web framework
- SQLite relational DBMS (no separate database server required)
- SQL tables, primary/foreign keys, indexes
- scikit-learn TF-IDF + Logistic Regression intent classifier for chatbot help
- HTML, CSS and JavaScript

## Run on Windows (VS Code)
1. Extract this ZIP.
2. Open the `Advanced_Barber_Management_System` folder in VS Code.
3. Open Terminal in VS Code and run:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

4. Open `http://127.0.0.1:5000` in Chrome.

If the `py` command is unavailable, try `python -m venv .venv`. The first run creates `barber_management.db` and adds example services/inventory.

## Main modules
- Dashboard: today's appointments, today's revenue, customers, services and low stock
- Customers: add/search clients and visit counts
- Services: price, duration, active/inactive services
- Staff: barber profiles and commission %
- Appointments: booking and status updates; prevents same barber being booked twice in the same slot
- Inventory: stock quantity, reorder level and stock adjustment
- Billing: service line, quantity, discount, tax, final total and persistent bill history
- Reports: daily revenue, popular services, average bill and completed appointments per staff member
- AI Assistant: ML intent classifier + practical app guidance
- Database: `database.py` creates tables and indexes automatically

## DBMS schema
`customers`, `services`, `staff`, `appointments`, `inventory`, `bills`, `bill_items`, `chat_logs`.

## Important notes
- This is a local learning/demo project, not a production-ready point-of-sale system.
- Before public deployment, set a secure secret key, add authentication/roles, CSRF protection, backups, audit logs, input validation, and HTTPS.
- Tax fields are configurable and are not tax/legal advice. Confirm the correct GST treatment with an accountant.
- The chatbot is an intent classifier with fixed answers, not ChatGPT or a large language model.
