from flask import Flask, render_template, request, redirect, session, send_file
import mysql.connector
import smtplib
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from config import DB_CONFIG, ADMIN_CREDENTIALS, EMAIL_CONFIG, SECRET_KEY
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import requests
app = Flask(__name__)
app.secret_key = SECRET_KEY

import razorpay

RAZORPAY_KEY_ID = "rzp_test_SZmFxWRuYWEbdt"
RAZORPAY_SECRET = "17trWiP0PwZn5jwUjOMhf2P4"

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

# ---------- SMS API ----------
import os
from dotenv import load_dotenv

load_dotenv()

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY")

# ---------------- DATABASE ----------------

db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# ---------------- HOME ----------------

@app.route('/')
def home():
    return render_template("index.html")

# ---------------- ADMIN LOGIN ----------------

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':
        if (request.form['username'] == ADMIN_CREDENTIALS["username"] and
            request.form['password'] == ADMIN_CREDENTIALS["password"]):

            session['admin'] = True
            return redirect('/admin_dashboard')

    return render_template("admin_login.html")

# ---------------- ADMIN DASHBOARD ----------------

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect('/admin_login')

    # Societies
    cursor.execute("SELECT COUNT(*) FROM societies")
    societies_count = cursor.fetchone()[0]

    # Secretaries
    cursor.execute("SELECT COUNT(*) FROM secretary")
    secretaries_count = cursor.fetchone()[0]

    # Members
    cursor.execute("SELECT COUNT(*) FROM members")
    members_count = cursor.fetchone()[0]

    # Bills Generated
    cursor.execute("SELECT COUNT(*) FROM bills")
    bills_count = cursor.fetchone()[0]

    # Pending Amount
    cursor.execute("SELECT SUM(total) FROM bills WHERE status='Pending'")
    pending_amount = cursor.fetchone()[0] or 0

    # Total Collection (Paid)
    cursor.execute("SELECT SUM(total) FROM bills WHERE status='Paid'")
    total_collection = cursor.fetchone()[0] or 0

    return render_template(
        "admin_dashboard.html",
        societies_count=societies_count,
        secretaries_count=secretaries_count,
        members_count=members_count,
        bills_count=bills_count,
        pending_amount=pending_amount,
        total_collection=total_collection
    )
# ---------------- ADD SOCIETY ----------------

@app.route('/add_society', methods=['GET', 'POST'])
def add_society():

    if request.method == 'POST':

        cursor.execute(
            "INSERT INTO societies(name,address) VALUES(%s,%s)",
            (request.form['name'], request.form['address'])
        )
        db.commit()

        return redirect('/admin_dashboard')

    return render_template("add_society.html")

# ---------------- VIEW SOCIETY ----------------
@app.route('/view_societies')
def view_societies():
    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute("SELECT * FROM societies")
    data = cursor.fetchall()

    return render_template("view_societies.html", societies=data)

# ---------------- DELETE SOCIETY ----------------
@app.route('/delete_society/<int:id>')
def delete_society(id):
    cursor.execute("DELETE FROM societies WHERE id=%s", (id,))
    db.commit()
    return redirect('/view_societies')

# ---------------- EDIT SOCIETY ----------------
@app.route('/edit_society/<int:id>', methods=['GET', 'POST'])
def edit_society(id):
    if request.method == 'POST':
        name = request.form['name']

        cursor.execute("UPDATE societies SET name=%s WHERE id=%s", (name, id))
        conn.commit()

        return redirect('/view_societies')

    cursor.execute("SELECT * FROM societies WHERE id=%s", (id,))
    society = cursor.fetchone()

    return render_template("edit_society.html", society=society)

    
# ---------------- ADD SECRETARY ----------------

@app.route('/add_secretary', methods=['GET', 'POST'])
def add_secretary():

    cursor.execute("SELECT * FROM societies")
    societies = cursor.fetchall()

    if request.method == 'POST':

        cursor.execute("""
        INSERT INTO secretary(name,email,mobile,password,society_id)
        VALUES(%s,%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['email'],
            request.form['mobile'],
            request.form['password'],
            request.form['society']
        ))

        db.commit()
        return redirect('/admin_dashboard')

    return render_template("add_secretary.html", societies=societies)

# ---------------- SECRETARY LOGIN ----------------

@app.route('/secretary_login', methods=['GET', 'POST'])
def secretary_login():

    if request.method == 'POST':

        cursor.execute(
            "SELECT * FROM secretary WHERE email=%s AND password=%s",
            (request.form['email'], request.form['password'])
        )

        sec = cursor.fetchone()

        if sec:
            session['secretary'] = sec[0]
            session['society'] = sec[5]
            return redirect('/secretary_dashboard')

    return render_template("secretary_login.html")

# ---------------- SECRETARY DASHBOARD ----------------

from datetime import datetime

@app.route('/secretary_dashboard')
def secretary_dashboard():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society_id = session['society']
    month = datetime.now().strftime("%B %Y")   # ✅ ADD THIS

    # Fetch Members
    cursor.execute(
        "SELECT * FROM members WHERE society_id=%s",
        (society_id,)
    )
    members = cursor.fetchall()

    # Total Members
    cursor.execute(
        "SELECT COUNT(*) FROM members WHERE society_id=%s",
        (society_id,)
    )
    total_members = cursor.fetchone()[0]

    # Pending Bills Count
    cursor.execute(
        "SELECT COUNT(*) FROM bills WHERE society_id=%s AND status='Pending'",
        (society_id,)
    )
    pending_bills = cursor.fetchone()[0]

    # Paid This Month
    cursor.execute("""
        SELECT COUNT(*) FROM bills 
        WHERE society_id=%s AND status='Paid'
        AND MONTH(date)=MONTH(CURDATE()) 
        AND YEAR(date)=YEAR(CURDATE()) 
    """, (society_id,))
    paid_this_month = cursor.fetchone()[0] 

    # Pending Amount
    cursor.execute(
        "SELECT SUM(total) FROM bills WHERE society_id=%s AND status='Pending'",
        (society_id,)
    )
    pending_amount = cursor.fetchone()[0] or 0

    # Total Collection
    cursor.execute(
        "SELECT SUM(total) FROM bills WHERE society_id=%s AND status='Paid'",
        (society_id,)
    )
    total_collection = cursor.fetchone()[0] or 0

    # ✅ NEW: Members who already have bill this month
    cursor.execute("""
        SELECT member_id FROM bills 
        WHERE society_id=%s AND month=%s
    """, (society_id, month))

    generated_ids = [row[0] for row in cursor.fetchall()]

    return render_template(
        "secretary_dashboard.html",
        members=members,
        total_members=total_members,
        pending_bills=pending_bills,
        paid_this_month=paid_this_month,
        pending_amount=pending_amount,
        total_collection=total_collection,
        generated_ids=generated_ids   # ✅ PASS THIS
    )
# ---------------- VIEW  SECRETARY ----------------

@app.route('/view_secretaries')
def view_secretaries():
    cursor.execute("SELECT * FROM secretary")
    data = cursor.fetchall()
    return render_template("view_secretaries.html", secretaries=data)


@app.route('/delete_secretary/<int:id>')
def delete_secretary(id):
    cursor.execute("DELETE FROM secretary WHERE id=%s", (id,))
    db.commit()
    return redirect('/view_secretaries')


@app.route('/edit_secretary/<int:id>', methods=['GET', 'POST'])
def edit_secretary(id):

    if 'admin' not in session:
        return redirect('/admin_login')

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']

        cursor.execute("""
            UPDATE secretary 
            SET name=%s, email=%s, mobile=%s, password=%s
            WHERE id=%s
        """, (name, email, mobile, password, id))

        conn.commit()

        return redirect('/admin_dashboard')

    cursor.execute("SELECT * FROM secretary WHERE id=%s", (id,))
    secretary = cursor.fetchone()

    return render_template("edit_secretary.html", secretary=secretary)
# ---------------- ADD MEMBER ----------------

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    cur = db.cursor()   # ✅ NEW cursor

    if request.method == 'POST':

        cur.execute("""
        INSERT INTO members
        (name,email,mobile,flat_no,living_type,maintenance,password,society_id)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['email'],
            request.form['mobile'],
            request.form['flat'],
            request.form['type'],
            request.form['maintenance'],
            request.form['password'],
            session['society']
        ))

        db.commit()
        return redirect('/secretary_dashboard')

    return render_template("add_member.html")
# ---------------- MEMBER LOGIN ----------------
@app.route('/member_login', methods=['GET', 'POST'])
def member_login():

    cur = db.cursor()   # ✅ NEW cursor

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur.execute(
            "SELECT id, name, flat_no, society_id FROM members WHERE email=%s AND password=%s",
            (email, password)
        )

        member = cur.fetchone()

        if member:
            session['member_id'] = member[0]
            session['member_name'] = member[1]
            session['flat_no'] = member[2]
            session['society'] = member[3]

            return redirect('/member_dashboard')

        else:
            return render_template("member_login.html", error="Invalid Email or Password")

    return render_template("member_login.html")

# ---------------- MEMBER DASHBOARD ----------------

@app.route('/member_dashboard')
def member_dashboard():

    # ✅ SESSION CHECK
    if 'member_id' not in session:
        return redirect('/member_login')

    member_id = session['member_id']
    society = session['society']

    # ✅ Society name
    cursor.execute("SELECT name FROM societies WHERE id=%s", (society,))
    society_name = cursor.fetchone()[0]

    # ✅ Bills + Charges JOIN
    cursor.execute("""
        SELECT 
            b.id,            -- 0
            b.member_id,     -- 1
            b.month,         -- 2
            b.maintenance,   -- 3
            b.penalty,       -- 4
            b.total,         -- 5
            b.status,        -- 6
            b.society_id,    -- 7
            b.date,          -- 8
            b.due_date,      -- 9
            IFNULL(SUM(c.amount), 0) AS charges   -- 10 ✅
        FROM bills b
        LEFT JOIN charges c ON b.society_id = c.society_id
        WHERE b.member_id = %s
        GROUP BY b.id
    """, (member_id,))

    bills = cursor.fetchall()

    # ✅ Counts
    total_bills = len(bills)
    paid_bills = len([b for b in bills if b[6] == 'Paid'])
    pending_bills = len([b for b in bills if b[6] == 'Pending'])

    # ✅ FIXED Pending Amount (Includes Charges)
    pending_amount = 0

    for b in bills:
        maintenance = b[3] or 0
        penalty = b[4] or 0
        charges = b[10] or 0   # ✅ correct index

        total = maintenance + penalty + charges

        if b[6] == 'Pending':
            pending_amount += total

    # ✅ Announcements
    cursor.execute("""
        SELECT title, message, date 
        FROM announcements 
        WHERE society_id=%s 
        ORDER BY id DESC LIMIT 3
    """, (society,))
    announcements = cursor.fetchall()

    # ✅ Render
    return render_template(
        "member_dashboard.html",
        member_name=session['member_name'],
        flat_no=session['flat_no'],
        society_name=society_name,
        total_bills=total_bills,
        paid_bills=paid_bills,
        pending_bills=pending_bills,
        pending_amount=pending_amount,
        announcements=announcements,
        upi="society@upi",
        bank="SBI Bank",
        account="1234567890",
        ifsc="SBIN0001234"
    )

# ---------------- GENRATE BILL ----------------

def generate_bills():

    month = datetime.now().strftime("%B %Y")
    society_id = session['society']

    # ✅ Get total charges ONCE
    cursor.execute(
        "SELECT IFNULL(SUM(amount), 0) FROM charges WHERE society_id=%s",
        (society_id,)
    )
    charges_total = float(cursor.fetchone()[0] or 0)

    # ✅ Get members
    cursor.execute(
        "SELECT id, maintenance FROM members WHERE society_id=%s",
        (society_id,)
    )
    members = cursor.fetchall()

    count = 0

    for member in members:

        member_id = member[0]
        maintenance = float(member[1] or 0)
        penalty = 0

        total = maintenance + charges_total + penalty

        try:
            # ✅ INSERT with duplicate protection (DB-level)
            cursor.execute("""
                INSERT INTO bills 
                (member_id, society_id, month, maintenance, penalty, total, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                member_id,
                society_id,
                month,
                maintenance,
                penalty,
                total,
                'Pending'
            ))

            count += 1

        except mysql.connector.IntegrityError:
            # 🔐 Skip duplicate safely
            continue

    db.commit()
    return count

@app.route('/generate_bills', methods=['POST'])
def generate_bills():

    cursor = db.cursor()

    # Get all members
    cursor.execute("SELECT id, maintenance FROM members")
    members = cursor.fetchall()

    generated_count = 0

    for member in members:
        member_id = member[0]
        amount = member[1]

        # ✅ Check if bill already exists for this month
        cursor.execute("""
            SELECT * FROM bills 
            WHERE member_id = %s 
            AND MONTH(created_at) = MONTH(CURRENT_DATE())
            AND YEAR(created_at) = YEAR(CURRENT_DATE())
        """, (member_id,))

        exists = cursor.fetchone()

        if not exists:
            # ✅ Insert new bill
            cursor.execute("""
                INSERT INTO bills (member_id, amount, status, created_at)
                VALUES (%s, %s, 'pending', NOW())
            """, (member_id, amount))

            generated_count += 1

    db.commit()
    cursor.close()

    return redirect(f"/secretary_dashboard?msg={generated_count} Bills Generated Successfully")
@app.route('/generate_bill/<int:member_id>')
def generate_single_bill(member_id):

    if 'secretary' not in session:
        return redirect('/secretary_login')

    month = datetime.now().strftime("%B %Y")
    society_id = session['society']

    # ✅ Get member
    cursor.execute(
        "SELECT id, maintenance FROM members WHERE id=%s AND society_id=%s",
        (member_id, society_id)
    )
    m = cursor.fetchone()

    if not m:
        return redirect('/secretary_dashboard?msg=Member Not Found')

    maintenance = float(m[1] or 0)

    # ✅ Get charges
    cursor.execute(
        "SELECT IFNULL(SUM(amount), 0) FROM charges WHERE society_id=%s",
        (society_id,)
    )
    charges_total = float(cursor.fetchone()[0] or 0)

    penalty = 0
    total = maintenance + charges_total + penalty

    try:
        cursor.execute("""
            INSERT INTO bills 
            (member_id, society_id, month, maintenance, penalty, total, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            member_id,
            society_id,
            month,
            maintenance,
            penalty,
            total,
            'Pending'
        ))

        db.commit()
        return redirect('/secretary_dashboard?msg=Bill Generated Successfully')

    except mysql.connector.IntegrityError:
        return redirect('/secretary_dashboard?msg=Bill Already Exists')
# ---------------- PAY BILL ----------------
@app.route('/bills')
def bills():

    if 'society' not in session:
        return redirect('/login')

    society = session['society']
    month_filter = request.args.get('month')

    # ---------------- MAIN BILL QUERY ----------------
    query = """
        SELECT 
            b.id,            
            m.name,          
            b.month,         
            b.maintenance,   
            b.penalty,       
            b.total,         
            b.status,        
            b.due_date,      
            IFNULL(SUM(c.amount), 0) AS charges  
        FROM bills b
        JOIN members m ON b.member_id = m.id
        LEFT JOIN charges c ON b.society_id = c.society_id
        WHERE b.society_id = %s
    """

    params = [society]

    if month_filter:
        query += " AND b.month = %s"
        params.append(month_filter)

    query += " GROUP BY b.id"

    cursor.execute(query, tuple(params))
    bills = cursor.fetchall()

    # ---------------- SUMMARY CALCULATIONS ----------------

    total_bills = len(bills)

    total_collection = 0
    pending_amount = 0

    for bill in bills:
        total = (bill[5] or 0) + (bill[8] or 0)

        if bill[6] == 'Paid':
            total_collection += total
        else:
            pending_amount += total

    # ---------------- RETURN ----------------
    return render_template(
        "bills.html",
        bills=bills,
        total_bills=total_bills,
        total_collection=total_collection,
        pending_amount=pending_amount
    )
# ---------------- VIEW BILLS ----------------

@app.route('/bills')
def view_bills():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society = session['society']
    month = request.args.get('month')

    if month:
        cursor.execute("""
        SELECT b.id, m.name, b.month, b.maintenance, b.penalty, b.total, b.status, b.due_date
        FROM bills b
        JOIN members m ON b.member_id = m.id
        WHERE b.society_id=%s AND b.month=%s
        """, (society, month))
    else:
        cursor.execute("""
        SELECT b.id, m.name, b.month, b.maintenance, b.penalty, b.total, b.status, b.due_date
        FROM bills b
        JOIN members m ON b.member_id = m.id
        WHERE b.society_id=%s
        """, (society,))

    bills = cursor.fetchall()

    today = date.today()

    updated_bills = []

    for b in bills:
        bill_id, name, month, maintenance, penalty, total, status, due_date = b

        # ✅ APPLY PENALTY IF LATE
        if status == 'Pending' and due_date and today > due_date:
            penalty = 500   # fixed late fee
            total = maintenance + penalty

            cursor.execute("""
            UPDATE bills SET penalty=%s, total=%s WHERE id=%s
            """, (penalty, total, bill_id))

            db.commit()

        updated_bills.append((bill_id, name, month, maintenance, penalty, total, status))

    # 📊 Summary
    total_collection = sum(b[5] for b in updated_bills if b[6] == 'Paid')
    pending_amount = sum(b[5] for b in updated_bills if b[6] == 'Pending')
    total_bills = len(updated_bills)

    return render_template("bills.html",
        bills=updated_bills,
        total_collection=total_collection,
        pending_amount=pending_amount,
        total_bills=total_bills
    )
# ---------------- CONFIRM PAYMENT ----------------

@app.route('/confirm_payment/<int:bill_id>')
def confirm_payment(bill_id):

    cursor.execute(
        "UPDATE bills SET status='Paid' WHERE id=%s",
        (bill_id,)
    )

    db.commit()
    return redirect('/member_dashboard')

@app.route('/mark_paid/<int:bill_id>')
def mark_paid(bill_id):

    if 'secretary' not in session:
        return redirect('/secretary_login')
    cursor.execute("UPDATE bills SET status='Paid' WHERE id=%s", (bill_id,))
    db.commit()

    return redirect('/bills')

@app.route('/delete_bill/<int:bill_id>')
def delete_bill(bill_id):

    if 'secretary' not in session:
        return redirect('/secretary_login')

    cursor.execute("DELETE FROM bills WHERE id=%s", (bill_id,))
    db.commit()

    return redirect('/bills')

@app.route('/edit_bill/<int:bill_id>', methods=['GET', 'POST'])
def edit_bill(bill_id):

    if 'secretary' not in session:
        return redirect('/secretary_login')

    if request.method == 'POST':
        maintenance = int(float(request.form['maintenance']))
        penalty = int(float(request.form['penalty']))

        total = maintenance + penalty

        cursor.execute("""
            UPDATE bills 
            SET maintenance=%s, penalty=%s, total=%s
            WHERE id=%s
        """, (maintenance, penalty, total, bill_id))

        db.commit()
        return redirect('/bills')

    cursor.execute("SELECT * FROM bills WHERE id=%s", (bill_id,))
    bill = cursor.fetchone()

    return render_template("edit_bill.html", bill=bill)
# ---------------- DOWNLOAD PDF ----------------

@app.route('/download_bill/<int:bill_id>')
def download_bill(bill_id):

    cursor.execute("""
    SELECT b.*, m.name 
    FROM bills b
    JOIN members m ON b.member_id = m.id
    WHERE b.id=%s
    """, (bill_id,))

    bill = cursor.fetchone()

    file_path = f"bill_{bill_id}.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("MaintenX Bill", styles['Title']))
    content.append(Paragraph(f"Member: {bill[7]}", styles['Normal']))
    content.append(Paragraph(f"Month: {bill[2]}", styles['Normal']))
    content.append(Paragraph(f"Maintenance: ₹{bill[3]}", styles['Normal']))
    content.append(Paragraph(f"Penalty: ₹{bill[4]}", styles['Normal']))
    content.append(Paragraph(f"Total: ₹{bill[5]}", styles['Normal']))
    content.append(Paragraph(f"Status: {bill[6]}", styles['Normal']))

    doc.build(content)

    return send_file(file_path, as_attachment=True)

# ---------------- AUTOMATION ----------------

def generate_bills():
    if datetime.now().day == 25:

        month = datetime.now().strftime("%B")

        cursor.execute("SELECT * FROM members")
        members = cursor.fetchall()

        for m in members:

            cursor.execute(
                "SELECT * FROM bills WHERE member_id=%s AND month=%s",
                (m[0], month)
            )

            if not cursor.fetchone():

                maintenance = m[5]

                cursor.execute("""
                INSERT INTO bills 
                (member_id, month, maintenance, penalty, total, status)
                VALUES (%s,%s,%s,%s,%s,%s)
                """, (m[0], month, maintenance, 0, maintenance, 'Pending'))

        db.commit()
        print("✅ Bills Generated")


def apply_penalty():
    if datetime.now().day > 10:

        cursor.execute("SELECT * FROM bills WHERE status='Pending'")
        bills = cursor.fetchall()

        for b in bills:

            penalty = b[3] * 0.10
            total = b[3] + penalty

            cursor.execute("""
            UPDATE bills SET penalty=%s, total=%s WHERE id=%s
            """, (penalty, total, b[0]))

        db.commit()
        print("✅ Penalty Applied")


# -------- SMS REMINDER --------
def send_sms_reminders():

    print("📱 SMS Reminder Job Running...")

    cursor.execute("""
    SELECT b.total, m.mobile, m.name
    FROM bills b
    JOIN members m ON b.member_id = m.id
    WHERE b.status='Pending'
    """)

    data = cursor.fetchall()

    for d in data:

        amount = d[0]
        mobile = str(d[1]).strip()
        name = d[2]

        if not mobile:
            continue

        sms_text = f"Hello {name}, your maintenance bill is ₹{amount}. Please pay before due date. - MaintenX"

        payload = {
            "route": "q",
            "message": sms_text,
            "language": "english",
            "numbers": mobile
        }

        headers = {
            "authorization": FAST2SMS_API_KEY,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://www.fast2sms.com/dev/bulkV2",
                json=payload,
                headers=headers
            )
            print(f"SMS sent to {mobile}: {response.text}")

        except Exception as e:
            print("SMS Error:", e)

    print("✅ SMS Reminders Sent")


# ---------------- SCHEDULER ----------------

scheduler = BackgroundScheduler()

scheduler.add_job(generate_bills, 'interval', hours=24)
scheduler.add_job(apply_penalty, 'interval', hours=24)

# 🔥 SMS reminder at exact time (25 & 28 at 3 PM)
scheduler.add_job(send_sms_reminders, 'cron', day='25,28', hour=15, minute=0)

scheduler.start()
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- charges ----------------

@app.route('/charges', methods=['GET', 'POST'])
def charges():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society = session['society']

    if request.method == 'POST':
        title = request.form['title']
        amount = int(request.form['amount'])

        # 🔹 Insert charge
        cursor.execute("""
        INSERT INTO charges (society_id, title, amount, created_at)
        VALUES (%s, %s, %s, CURDATE())
        """, (society, title, amount))

        # 🔥 UPDATE ALL EXISTING BILLS
        cursor.execute("""
            UPDATE bills 
            SET total = total + %s
            WHERE society_id=%s AND status='Pending'
        """, (amount, society))

        db.commit()

        return redirect('/charges')

    cursor.execute("SELECT * FROM charges WHERE society_id=%s", (society,))
    data = cursor.fetchall()

    return render_template("charges.html", charges=data)

@app.route('/delete_charge/<int:id>')
def delete_charge(id):

    if 'secretary' not in session:
        return redirect('/secretary_login')

    # 🔹 Get amount before delete
    cursor.execute("SELECT amount, society_id FROM charges WHERE id=%s", (id,))
    charge = cursor.fetchone()

    if charge:
        amount = charge[0]
        society = charge[1]

        # 🔹 Delete charge
        cursor.execute("DELETE FROM charges WHERE id=%s", (id,))

        # 🔥 UPDATE BILLS
        cursor.execute("""
            UPDATE bills 
            SET total = total - %s
            WHERE society_id=%s AND status='Pending'
        """, (amount, society))

        db.commit()

    return redirect('/charges')

@app.route('/announcements', methods=['GET', 'POST'])
def announcements():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society = session['society']
    cur = db.cursor()

    if request.method == 'POST':
        title = request.form['title']
        message = request.form['message']

        # SAVE ANNOUNCEMENT
        cur.execute("""
        INSERT INTO announcements (society_id, title, message, date, time)
        VALUES (%s, %s, %s, CURDATE(), CURTIME())
        """, (society, title, message))

        db.commit()

        # SEND SMS
        cur.execute("SELECT mobile FROM members WHERE society_id=%s", (society,))
        numbers = cur.fetchall()

        phone_list = [str(num[0]).strip() for num in numbers if num[0]]

        if phone_list:
            payload = {
                "route": "q",
                "message": f"Society Notice: {title} - {message}",
                "language": "english",
                "numbers": ",".join(phone_list)
            }

            headers = {
                "authorization": FAST2SMS_API_KEY,
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(
                    "https://www.fast2sms.com/dev/bulkV2",
                    json=payload,
                    headers=headers
                )
                print("SMS:", response.text)
            except Exception as e:
                print("SMS Error:", e)

        return redirect('/announcements')   # 🔥 IMPORTANT

    # FETCH ANNOUNCEMENTS
    cur.execute("""
    SELECT id, title, message, date, time
    FROM announcements
    WHERE society_id=%s
    ORDER BY id DESC
    """, (society,))

    data = cur.fetchall()

    return render_template("announcements.html", announcements=data)

# ---------------- MEMBER ANNOUNCEMENTS ----------------
# ---------------- MEMBER ANNOUNCEMENTS ----------------

@app.route('/member_announcements')
def member_announcements():

    if 'member_id' not in session:
        return redirect('/member_login')

    cur = db.cursor()

    cur.execute("""
    SELECT title, message, date, time
    FROM announcements
    WHERE society_id=%s
    ORDER BY id DESC
    """, (session['society'],))

    data = cur.fetchall()

    return render_template("member_announcements.html", announcements=data)
@app.route('/complaints')
def complaints():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society = session['society']

    cursor.execute("""
    SELECT c.id, m.name, c.subject, c.message, c.status
    FROM complaints c
    JOIN members m ON c.member_id = m.id
    WHERE c.society_id=%s
    """, (society,))

    data = cursor.fetchall()

    return render_template("complaints.html", complaints=data)

@app.route('/resolve_complaint/<int:id>')
def resolve_complaint(id):

    cursor.execute(
        "UPDATE complaints SET status='Resolved' WHERE id=%s",
        (id,)
    )
    db.commit()

    return redirect('/complaints')

# ---------------- reports ----------------

@app.route('/reports')
def reports():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society = session['society']
    month = request.args.get('month')   # ✅ moved above

    # 📊 If month filter applied
    if month:
        cursor.execute("""
        SELECT SUM(total) FROM bills 
        WHERE society_id=%s AND status='Paid' AND month=%s
        """, (society, month))
        total_collection = cursor.fetchone()[0] or 0

        cursor.execute("""
        SELECT SUM(total) FROM bills 
        WHERE society_id=%s AND status='Pending' AND month=%s
        """, (society, month))
        pending_amount = cursor.fetchone()[0] or 0

    else:
        # 📊 Overall report
        cursor.execute("""
        SELECT SUM(total) FROM bills 
        WHERE society_id=%s AND status='Paid'
        """, (society,))
        total_collection = cursor.fetchone()[0] or 0

        cursor.execute("""
        SELECT SUM(total) FROM bills 
        WHERE society_id=%s AND status='Pending'
        """, (society,))
        pending_amount = cursor.fetchone()[0] or 0

    return render_template("reports.html",
        total_collection=total_collection,
        pending_amount=pending_amount,
        selected_month=month   # optional for UI
    )

@app.route('/advanced_reports')
def advanced_reports():

    if 'secretary' not in session:
        return redirect('/secretary_login')

    society = session['society']

    # Total collection
    cursor.execute("""
    SELECT SUM(total) FROM bills 
    WHERE society_id=%s AND status='Paid'
    """, (society,))
    total_collection = cursor.fetchone()[0] or 0

    # Pending amount
    cursor.execute("""
    SELECT SUM(total) FROM bills 
    WHERE society_id=%s AND status='Pending'
    """, (society,))
    pending_amount = cursor.fetchone()[0] or 0

    # Monthly collection data
    cursor.execute("""
    SELECT MONTH(bill_date), SUM(total)
    FROM bills
    WHERE society_id=%s AND status='Paid'
    GROUP BY MONTH(bill_date)
    ORDER BY MONTH(bill_date)
    """, (society,))
    
    data = cursor.fetchall()

    months = []
    amounts = []

    for row in data:
        months.append(row[0])
        amounts.append(float(row[1]))

    return render_template("advanced_reports.html",
        total_collection=total_collection,
        pending_amount=pending_amount,
        months=months,
        amounts=amounts
    )

@app.route('/member_bills')
def member_bills():

    if 'member_id' not in session:
        return redirect('/member_login')

    member_id = session['member_id']
    society_id = session['society']

    cursor.execute("""
        SELECT 
            b.id,              -- 0
            b.month,           -- 1
            b.maintenance,     -- 2
            b.penalty,         -- 3
            b.total,           -- 4
            b.status,          -- 5
            IFNULL(SUM(c.amount), 0) AS charges   -- 6 ✅
        FROM bills b
        LEFT JOIN charges c ON b.society_id = c.society_id
        WHERE b.member_id = %s AND b.society_id = %s
        GROUP BY b.id
    """, (member_id, society_id))

    bills = cursor.fetchall()

    return render_template("member_bills.html", bills=bills)

@app.route('/my_complaints')
def my_complaints():

    if 'member_id' not in session:
        return redirect('/member_login')

    member_id = session['member_id']
    society_id = session['society']

    cursor.execute("""
        SELECT * FROM complaints
        WHERE member_id=%s AND society_id=%s
        ORDER BY id DESC
    """, (member_id, society_id))

    complaints = cursor.fetchall()

    return render_template("my_complaints.html", complaints=complaints)

@app.route('/raise_complaint', methods=['GET', 'POST'])
def raise_complaint():

    if 'member_id' not in session:
        return redirect('/member_login')

    if request.method == 'POST':

        member_id = session['member_id']
        society_id = session['society']

        subject = request.form['subject']
        message = request.form['message']
        today = date.today()

        cursor.execute("""
            INSERT INTO complaints (member_id, society_id, subject, message, status, date)
            VALUES (%s, %s, %s, %s, 'Pending', %s)
        """, (member_id, society_id, subject, message, today))

        db.commit()

        return redirect('/my_complaints')

    return render_template("raise_complaint.html")

@app.route('/pay/<int:bill_id>')
def pay_bill(bill_id):

    if 'member_id' not in session:
        return redirect('/member_login')

    # ✅ Get bill + charges
    cursor.execute("""
        SELECT 
            b.id,            -- 0
            b.member_id,     -- 1
            b.month,         -- 2
            b.maintenance,   -- 3
            b.penalty,       -- 4
            b.total,         -- 5
            b.status,        -- 6
            b.society_id,    -- 7
            IFNULL(SUM(c.amount), 0) AS charges   -- 8 ✅
        FROM bills b
        LEFT JOIN charges c ON b.society_id = c.society_id
        WHERE b.id = %s
        GROUP BY b.id
    """, (bill_id,))

    bill = cursor.fetchone()

    # ✅ Extract values safely
    maintenance = bill[3] or 0
    penalty = bill[4] or 0
    charges = bill[8] or 0

    # ✅ FINAL TOTAL (IMPORTANT)
    final_amount = maintenance + penalty + charges

    # Razorpay uses paise
    amount = int(final_amount * 100)

    # ✅ Create Razorpay order
    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return render_template(
        "pay.html",
        order=order,
        bill=bill,
        final_amount=final_amount,   # ✅ send to UI
        key_id=RAZORPAY_KEY_ID
    )
@app.route('/payment_success/<int:bill_id>')
def payment_success(bill_id):

    cursor.execute("""
        UPDATE bills 
        SET status='Paid'
        WHERE id=%s
    """, (bill_id,))

    db.commit()

    return redirect('/member_bills?msg=Payment Successful')


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)