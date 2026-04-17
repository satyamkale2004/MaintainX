import smtplib
import mysql.connector
from datetime import date

db=mysql.connector.connect(
host="localhost",
user="root",
password="",
database="maintenx"
)

cursor=db.cursor()

cursor.execute("""
SELECT members.email,bills.total
FROM bills
JOIN members ON bills.member_id=members.id
WHERE status='Pending'
""")

rows=cursor.fetchall()

for r in rows:

    email=r[0]
    amount=r[1]

    server=smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()

    server.login("youremail@gmail.com","password")

    message=f"""
Your MaintenX maintenance bill is {amount}.
Please pay before 10th.
"""

    server.sendmail("youremail@gmail.com",email,message)

    server.quit()