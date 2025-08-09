from database import init_db, check_user
import os
print("DB:", os.path.abspath("usuarios.db"))
init_db()
print("check_user(admin, admin):", check_user("admin","admin"))
