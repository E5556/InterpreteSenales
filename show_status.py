from database import check_user
import sqlite3, os
print("DB:", os.path.abspath("usuarios.db"))
print("check_user(admin, admin):", check_user("admin","admin"))
con = sqlite3.connect("usuarios.db")
print("row:", con.execute("SELECT username, role, must_change_password FROM users WHERE lower(username)=lower('admin')").fetchall())
