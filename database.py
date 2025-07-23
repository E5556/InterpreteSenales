import sqlite3
import hashlib
from datetime import datetime

DATABASE_NAME = "usuarios.db"

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)
    # Tabla de sesiones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Tabla de interpretaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interpretations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    """Hashea la contraseña usando SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def add_user(username, password):
    """Agrega un nuevo usuario a la base de datos. Retorna True si fue exitoso, False si el usuario ya existe."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Verificar si el usuario ya existe
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False  # El usuario ya existe

    # Si no existe, agregarlo
    password_hash = hash_password(password)
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()
    return True

def check_user(username, password):
    """Verifica si el usuario y la contraseña son correctos. 
    Retorna el ID del usuario si son correctos, None en caso contrario."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        user_id, stored_password_hash = result
        input_password_hash = hash_password(password)
        if stored_password_hash == input_password_hash:
            return user_id
        
    return None

def create_session(user_id):
    """Crea una nueva sesión para un usuario y retorna el ID de la sesión."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (user_id) VALUES (?)", (user_id,))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def add_interpretation(session_id, word):
    """Agrega una palabra interpretada a una sesión."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO interpretations (session_id, word) VALUES (?, ?)", (session_id, word))
    conn.commit()
    conn.close()

def get_user_sessions(user_id):
    """Obtiene todas las sesiones de un usuario, ordenadas por fecha."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp FROM sessions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def get_session_interpretations(session_id):
    """Obtiene todas las interpretaciones de una sesión, en orden."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT word, timestamp FROM interpretations WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    interpretations = cursor.fetchall()
    conn.close()
    return interpretations

if __name__ == '__main__':
    # Esto se ejecutará solo cuando corras 'python database.py' directamente
    # Es útil para inicializar la base de datos por primera vez.
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos lista.")

    # Ejemplo de cómo agregar un usuario (puedes descomentar para probar)
    # if add_user("testuser", "password123"):
    #     print("Usuario 'testuser' agregado exitosamente.")
    # else:
    #     print("El usuario 'testuser' ya existía.")

    # Ejemplo de cómo verificar un usuario
    # user_id = check_user('testuser', 'password123')
    # print(f"Verificando 'testuser' con 'password123'. ID de usuario: {user_id}")
    
    # if user_id:
    #     new_session_id = create_session(user_id)
    #     print(f"Nueva sesión creada con ID: {new_session_id}")
    #     add_interpretation(new_session_id, "HOLA")
    #     add_interpretation(new_session_id, "MUNDO")
    #     print("Interpretaciones agregadas.") 