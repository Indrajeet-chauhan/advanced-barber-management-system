"""Simple ML-backed salon assistant. Falls back to rules if scikit-learn is unavailable."""
import re

TRAINING = [
    ("appointment", "How do I book an appointment?"),
    ("appointment", "show me appointment booking steps"),
    ("billing", "How can I create a bill invoice payment"),
    ("billing", "calculate customer bill"),
    ("inventory", "How do I check low stock inventory products"),
    ("inventory", "which products need reorder"),
    ("services", "show services and prices haircut beard facial"),
    ("services", "how can I add a new service"),
    ("customers", "how do I add a customer client"),
    ("customers", "search customer phone number"),
    ("reports", "show revenue report sales popular services"),
    ("reports", "how much money did the shop earn"),
    ("staff", "how do I add barber staff member"),
    ("ai", "what is machine learning artificial intelligence"),
    ("dbms", "what is DBMS database SQL tables"),
    ("help", "hello hi hey help"),
]
ANSWERS = {
    "appointment": "Open Appointments → choose a customer, service, date and time, optionally assign a barber, then click Book appointment. A barber cannot be double-booked in the same time slot.",
    "billing": "Open Billing → select customer and service, enter quantity, discount % and tax % → Create bill. The system calculates subtotal, discount, tax and final total, and stores the bill in SQLite.",
    "inventory": "Open Inventory to see stock. Items at or below their reorder level are marked LOW. Use the stock adjustment field to add or remove stock.",
    "services": "Open Services to view service prices and durations. Add a service using the form; deactivate old services instead of deleting them so historical records remain meaningful.",
    "customers": "Open Customers to add a client with a unique phone number, search by name/phone and view visit counts.",
    "reports": "Open Reports for revenue by day, average bill, popular services and completed appointments per staff member.",
    "staff": "Open Staff to add barbers, roles and commission percentages. Assign active staff to appointments.",
    "ai": "AI is the broad field of making systems perform tasks that seem intelligent. Machine learning (ML) learns patterns from examples. This chatbot uses a small TF-IDF + Logistic Regression intent classifier when scikit-learn is installed; it is not a generative LLM.",
    "dbms": "A DBMS manages data. This project uses SQLite, a relational database with tables, primary keys, foreign keys, indexes and SQL queries. Data is stored locally in barber_management.db.",
    "help": "Hi! I can guide you on appointments, customers, staff, services, billing, inventory, reports, AI/ML and the database. Try: 'how do I create a bill?'"
}
class BarberAIAssistant:
    def __init__(self):
        self.model = None
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            texts = [x[1] for x in TRAINING]
            labels = [x[0] for x in TRAINING]
            self.vectorizer = TfidfVectorizer(ngram_range=(1,2), stop_words="english")
            X = self.vectorizer.fit_transform(texts)
            self.model = LogisticRegression(max_iter=1000).fit(X, labels)
        except Exception:
            self.vectorizer = None

    def reply(self, message):
        text = message.lower()
        if any(x in text for x in ["thank", "thanks", "shukriya"]):
            return "You're welcome! Let me know if you need help managing the shop.", "thanks"
        if self.model:
            intent = self.model.predict(self.vectorizer.transform([message]))[0]
            confidence = max(self.model.predict_proba(self.vectorizer.transform([message]))[0])
            if confidence < 0.24:
                return "I'm not sure I understood. Ask about appointments, customers, staff, services, billing, inventory, reports, AI/ML or DBMS.", "unknown"
        else:
            intent = "help"
            for key, words in {
                "appointment":["appointment","booking"], "billing":["bill","invoice","payment"],
                "inventory":["stock","inventory","reorder"], "services":["service","price","haircut"],
                "customers":["customer","client"], "reports":["report","revenue","sales"],
                "staff":["staff","barber"], "ai":["machine learning","artificial intelligence"," ai "],
                "dbms":["dbms","database","sql"]
            }.items():
                if any(w in text for w in words):
                    intent = key; break
        return ANSWERS.get(intent, ANSWERS["help"]), intent
