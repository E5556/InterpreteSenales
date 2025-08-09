import sqlite3, hashlib, os
db = os.path.abspath("usuarios.db")
print("DB:", db)
con = sqlite3.connect(db); cur = con.cursor()

# Añade columnas si faltan
cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
if "role" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
if "must_change_password" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")

# Crea/forza admin con rol admin y clave "admin"
ph = hashlib.sha256(b"admin").hexdigest()
cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role,must_change_password) VALUES(?, ?, 'admin', 1)", ("admin", ph))
cur.execute("UPDATE users SET password_hash=?, role='admin', must_change_password=1 WHERE lower(username)=lower('admin')", (ph,))
con.commit()
print("row:", cur.execute("SELECT username, role, must_change_password FROM users WHERE lower(username)=lower('admin')").fetchall())
