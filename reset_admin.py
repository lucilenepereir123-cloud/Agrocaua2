# reset_admin.py — corra sempre que precisar de redefinir a password
from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect('instance/database.db')
conn.execute("UPDATE users SET password_hash=? WHERE email=?",
    (generate_password_hash('admin123'), 'admin@agrocaua.com'))
conn.commit()
conn.close()
print("✅ Password redefinida para admin123")