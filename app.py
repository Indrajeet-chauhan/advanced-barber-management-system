from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import init_db, get_db
from ai_assistant import BarberAIAssistant

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-production"
init_db()
assistant = BarberAIAssistant()

@app.template_filter("money")
def money(value):
    return f"₹{float(value or 0):,.2f}"

@app.route("/")
def dashboard():
    db = get_db()
    stats = {
        "customers": db.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "appointments": db.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = ?", (date.today().isoformat(),)).fetchone()[0],
        "revenue": db.execute("SELECT COALESCE(SUM(total),0) FROM bills WHERE date(created_at)=?", (date.today().isoformat(),)).fetchone()[0],
        "services": db.execute("SELECT COUNT(*) FROM services WHERE active=1").fetchone()[0],
        "low_stock": db.execute("SELECT COUNT(*) FROM inventory WHERE quantity <= reorder_level").fetchone()[0],
    }
    upcoming = db.execute("""SELECT a.*, c.name customer_name, s.name service_name, e.name staff_name
        FROM appointments a JOIN customers c ON c.id=a.customer_id
        JOIN services s ON s.id=a.service_id LEFT JOIN staff e ON e.id=a.staff_id
        WHERE a.appointment_date >= ? AND a.status != 'Cancelled'
        ORDER BY a.appointment_date, a.appointment_time LIMIT 8""", (date.today().isoformat(),)).fetchall()
    recent_bills = db.execute("""SELECT b.*, c.name customer_name FROM bills b
        JOIN customers c ON c.id=b.customer_id ORDER BY b.id DESC LIMIT 5""").fetchall()
    db.close()
    return render_template("dashboard.html", stats=stats, upcoming=upcoming, recent_bills=recent_bills)

@app.route("/customers", methods=["GET", "POST"])
def customers():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not name or not phone:
            flash("Customer name and phone are required.", "error")
        else:
            try:
                db.execute("INSERT INTO customers(name, phone, email, notes) VALUES(?,?,?,?)",
                           (name, phone, request.form.get("email","").strip(), request.form.get("notes","").strip()))
                db.commit()
                flash("Customer added successfully.", "success")
                return redirect(url_for("customers"))
            except Exception:
                flash("Could not add customer. Phone number may already exist.", "error")
    q = request.args.get("q", "").strip()
    rows = db.execute("""SELECT c.*, COUNT(a.id) visits FROM customers c
        LEFT JOIN appointments a ON a.customer_id=c.id
        WHERE c.name LIKE ? OR c.phone LIKE ? GROUP BY c.id ORDER BY c.name""", (f"%{q}%",f"%{q}%")).fetchall()
    db.close()
    return render_template("customers.html", customers=rows, q=q)

@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
def delete_customer(customer_id):
    db = get_db()
    linked = db.execute("SELECT COUNT(*) FROM appointments WHERE customer_id=?", (customer_id,)).fetchone()[0]
    if linked:
        flash("This customer has appointments and cannot be deleted. Keep the record for history.", "error")
    else:
        db.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        db.commit()
        flash("Customer deleted.", "success")
    db.close()
    return redirect(url_for("customers"))

@app.route("/services", methods=["GET", "POST"])
def services():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name","").strip()
        try:
            price = float(request.form.get("price", "0"))
            duration = int(request.form.get("duration", "30"))
            if not name or price < 0 or duration <= 0: raise ValueError()
            db.execute("INSERT INTO services(name, description, price, duration_minutes) VALUES(?,?,?,?)",
                       (name, request.form.get("description","").strip(), price, duration))
            db.commit()
            flash("Service added.", "success")
            return redirect(url_for("services"))
        except ValueError:
            flash("Enter a service name, valid price, and positive duration.", "error")
    rows = db.execute("SELECT * FROM services ORDER BY active DESC, name").fetchall()
    db.close()
    return render_template("services.html", services=rows)

@app.route("/services/<int:service_id>/toggle", methods=["POST"])
def toggle_service(service_id):
    db = get_db()
    db.execute("UPDATE services SET active = CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (service_id,))
    db.commit(); db.close()
    return redirect(url_for("services"))

@app.route("/staff", methods=["GET", "POST"])
def staff():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name","").strip()
        phone = request.form.get("phone","").strip()
        role = request.form.get("role","Barber").strip()
        try:
            commission = float(request.form.get("commission","0"))
            if not name or not phone or not 0 <= commission <= 100: raise ValueError()
            db.execute("INSERT INTO staff(name, phone, role, commission_percent) VALUES(?,?,?,?)",
                       (name,phone,role,commission))
            db.commit()
            flash("Staff member added.", "success")
            return redirect(url_for("staff"))
        except Exception:
            flash("Please check the details. Phone number may already exist.", "error")
    rows = db.execute("SELECT * FROM staff ORDER BY active DESC, name").fetchall()
    db.close()
    return render_template("staff.html", staff=rows)

@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    db = get_db()
    if request.method == "POST":
        try:
            customer_id = int(request.form["customer_id"])
            service_id = int(request.form["service_id"])
            staff_id = int(request.form["staff_id"]) if request.form.get("staff_id") else None
            day = request.form["appointment_date"]
            time = request.form["appointment_time"]
            # Avoid assigning the same staff member to overlapping appointment slots.
            if staff_id:
                conflict = db.execute("""SELECT COUNT(*) FROM appointments WHERE staff_id=? AND appointment_date=?
                    AND appointment_time=? AND status NOT IN ('Cancelled','Completed')""", (staff_id,day,time)).fetchone()[0]
                if conflict:
                    flash("This barber already has an appointment at that date and time.", "error")
                    return redirect(url_for("appointments"))
            db.execute("""INSERT INTO appointments(customer_id, service_id, staff_id, appointment_date,
                appointment_time, status, notes) VALUES(?,?,?,?,?,'Booked',?)""",
                (customer_id,service_id,staff_id,day,time,request.form.get("notes","").strip()))
            db.commit()
            flash("Appointment booked.", "success")
            return redirect(url_for("appointments"))
        except Exception:
            flash("Appointment could not be booked. Check the selected details.", "error")
    rows = db.execute("""SELECT a.*, c.name customer_name, c.phone, s.name service_name, s.price,
        e.name staff_name FROM appointments a JOIN customers c ON c.id=a.customer_id
        JOIN services s ON s.id=a.service_id LEFT JOIN staff e ON e.id=a.staff_id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC LIMIT 200""").fetchall()
    customers_list = db.execute("SELECT id,name,phone FROM customers ORDER BY name").fetchall()
    services_list = db.execute("SELECT id,name,price,duration_minutes FROM services WHERE active=1 ORDER BY name").fetchall()
    staff_list = db.execute("SELECT id,name FROM staff WHERE active=1 ORDER BY name").fetchall()
    db.close()
    return render_template("appointments.html", appointments=rows, customers=customers_list,
                           services=services_list, staff=staff_list, today=date.today().isoformat())

@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
def appointment_status(appointment_id):
    status = request.form.get("status")
    if status not in {"Booked","Arrived","In Service","Completed","Cancelled","No Show"}:
        flash("Invalid status.", "error")
    else:
        db = get_db()
        db.execute("UPDATE appointments SET status=? WHERE id=?", (status,appointment_id))
        db.commit(); db.close()
        flash("Appointment status updated.", "success")
    return redirect(request.referrer or url_for("appointments"))

@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    db = get_db()
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            quantity = float(request.form["quantity"])
            reorder = float(request.form["reorder_level"])
            unit = request.form.get("unit","pcs").strip()
            cost = float(request.form.get("unit_cost","0"))
            if not name or quantity < 0 or reorder < 0 or cost < 0: raise ValueError()
            db.execute("INSERT INTO inventory(name, quantity, unit, reorder_level, unit_cost) VALUES(?,?,?,?,?)",
                       (name,quantity,unit,reorder,cost))
            db.commit(); flash("Inventory item added.", "success")
            return redirect(url_for("inventory"))
        except Exception:
            flash("Enter valid inventory values.", "error")
    rows = db.execute("SELECT *, quantity <= reorder_level AS low FROM inventory ORDER BY low DESC,name").fetchall()
    db.close()
    return render_template("inventory.html", items=rows)

@app.route("/inventory/<int:item_id>/adjust", methods=["POST"])
def adjust_inventory(item_id):
    try:
        delta = float(request.form["delta"])
        db = get_db()
        item = db.execute("SELECT quantity FROM inventory WHERE id=?", (item_id,)).fetchone()
        if not item or item["quantity"] + delta < 0:
            flash("Stock adjustment would make quantity negative.", "error")
        else:
            db.execute("UPDATE inventory SET quantity=quantity+? WHERE id=?", (delta,item_id))
            db.commit(); flash("Stock updated.", "success")
        db.close()
    except Exception:
        flash("Invalid stock adjustment.", "error")
    return redirect(url_for("inventory"))

@app.route("/billing", methods=["GET", "POST"])
def billing():
    db = get_db()
    if request.method == "POST":
        try:
            customer_id = int(request.form["customer_id"])
            service_id = int(request.form["service_id"])
            qty = int(request.form.get("quantity","1"))
            discount = float(request.form.get("discount","0"))
            tax_rate = float(request.form.get("tax_rate","0"))
            service = db.execute("SELECT * FROM services WHERE id=? AND active=1", (service_id,)).fetchone()
            if not service or qty < 1 or not 0 <= discount <= 100 or not 0 <= tax_rate <= 100: raise ValueError()
            subtotal = service["price"] * qty
            discount_amount = subtotal * discount / 100
            taxable = subtotal - discount_amount
            tax = taxable * tax_rate / 100
            total = round(taxable + tax, 2)
            cur = db.execute("""INSERT INTO bills(customer_id, subtotal, discount_percent, tax_percent, tax_amount, total)
                VALUES(?,?,?,?,?,?)""", (customer_id,subtotal,discount,tax_rate,tax,total))
            bill_id = cur.lastrowid
            db.execute("INSERT INTO bill_items(bill_id, service_id, description, quantity, unit_price, line_total) VALUES(?,?,?,?,?,?)",
                       (bill_id,service_id,service["name"],qty,service["price"],subtotal))
            db.commit()
            flash(f"Bill #{bill_id} created. Total: ₹{total:.2f}", "success")
            return redirect(url_for("billing"))
        except Exception:
            flash("Bill could not be created. Check all values.", "error")
    customers_list = db.execute("SELECT id,name,phone FROM customers ORDER BY name").fetchall()
    services_list = db.execute("SELECT id,name,price FROM services WHERE active=1 ORDER BY name").fetchall()
    bills = db.execute("""SELECT b.*, c.name customer_name FROM bills b JOIN customers c ON c.id=b.customer_id
        ORDER BY b.id DESC LIMIT 100""").fetchall()
    db.close()
    return render_template("billing.html", customers=customers_list, services=services_list, bills=bills)

@app.route("/reports")
def reports():
    db = get_db()
    daily = db.execute("""SELECT date(created_at) day, COUNT(*) bills, SUM(total) revenue
        FROM bills GROUP BY date(created_at) ORDER BY day DESC LIMIT 14""").fetchall()
    popular = db.execute("""SELECT s.name, SUM(bi.quantity) sold, SUM(bi.line_total) revenue
        FROM bill_items bi JOIN services s ON s.id=bi.service_id
        GROUP BY s.id ORDER BY sold DESC LIMIT 10""").fetchall()
    staff_perf = db.execute("""SELECT e.name, COUNT(a.id) appointments
        FROM staff e LEFT JOIN appointments a ON a.staff_id=e.id AND a.status='Completed'
        GROUP BY e.id ORDER BY appointments DESC""").fetchall()
    totals = db.execute("SELECT COUNT(*) bills, COALESCE(SUM(total),0) revenue, COALESCE(AVG(total),0) average_bill FROM bills").fetchone()
    db.close()
    return render_template("reports.html", daily=daily, popular=popular, staff_perf=staff_perf, totals=totals)

@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message","")).strip()
    if not message:
        return jsonify({"reply":"Type a question first."}), 400
    reply, intent = assistant.reply(message)
    db = get_db()
    db.execute("INSERT INTO chat_logs(user_message, bot_reply, intent) VALUES(?,?,?)", (message,reply,intent))
    db.commit(); db.close()
    return jsonify({"reply":reply,"intent":intent})

@app.route("/chat")
def chat():
    return render_template("chat.html")

if __name__ == "__main__":
    app.run(debug=True)
