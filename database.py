import sqlite3
import hashlib
from datetime import datetime
from config import get_database_path, get_database_version

# Usar la configuración dinámica para la base de datos
def get_database_name():
    """Obtiene el nombre de la base de datos según la configuración"""
    return get_database_path()

def init_db():
    """Inicializa la ba+
    se de datos y crea las tablas si no existen."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            birth_date TEXT,
            birth_country TEXT,
            birth_city TEXT,
            residence_country TEXT,
            residence_city TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            must_change_password INTEGER NOT NULL DEFAULT 0
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
    # Verificar si el usuario admin existe
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        # Si no existe, lo creamos
        admin_pass_hash = hash_password("admin")
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, must_change_password)
            VALUES ('admin', ?, 'admin', 1)
        """, (admin_pass_hash,))
        print("Usuario 'admin' creado con contraseña 'admin'. Se requerirá cambio.")

    conn.commit()
    conn.close()

def hash_password(password):
    """Hashea la contraseña usando SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def add_user(username, password, first_name, last_name, email, birth_date, birth_country, birth_city, residence_country, residence_city, role='user'):
    """Agrega un nuevo usuario con todos sus datos a la base de datos."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    
    # Verificar si el usuario o el email ya existen
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
    if cursor.fetchone():
        conn.close()
        return False  # El usuario o email ya existe

    # Si no existe, agregarlo
    password_hash = hash_password(password)
    cursor.execute("""
        INSERT INTO users (username, password_hash, first_name, last_name, email, 
                         birth_date, birth_country, birth_city, residence_country, residence_city, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, password_hash, first_name, last_name, email, 
          birth_date, birth_country, birth_city, residence_country, residence_city, role))
    conn.commit()
    conn.close()
    return True

def check_user(username, password):
    """Verifica si el usuario y la contraseña son correctos. 
    Retorna (user_id, role, must_change_password) si son correctos, None en caso contrario."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, password_hash, role, must_change_password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        user_id, stored_password_hash, role, must_change = result
        input_password_hash = hash_password(password)
        if stored_password_hash == input_password_hash:
            return user_id, role, bool(must_change)
        
    return None

def update_user_password(user_id, new_password):
    """Actualiza la contraseña de un usuario y desactiva el flag de cambio."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    new_password_hash = hash_password(new_password)
    cursor.execute("""
        UPDATE users 
        SET password_hash = ?, must_change_password = 0
        WHERE id = ?
    """, (new_password_hash, user_id))
    conn.commit()
    conn.close()

# --- Funciones de Administrador ---

def get_all_users():
    """Retorna una lista de todos los usuarios (sin la contraseña)."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name, last_name, email, role FROM users ORDER BY username")
    users = cursor.fetchall()
    conn.close()
    return users

def get_user_details_by_id(user_id):
    """Obtiene todos los detalles de un usuario por su ID."""
    conn = sqlite3.connect(get_database_name())
    conn.row_factory = sqlite3.Row # Para poder acceder a los datos por nombre de columna
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_details(user_id, username, first_name, last_name, email, role):
    """Actualiza los detalles de un usuario (versión del admin, sin cambiar contraseña)."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users
            SET username = ?, first_name = ?, last_name = ?, email = ?, role = ?
            WHERE id = ?
        """, (username, first_name, last_name, email, role, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # Ocurre si el username o email ya existen
        return False
    finally:
        conn.close()

def delete_user(user_id):
    """Elimina un usuario y todos sus datos asociados (sesiones, interpretaciones)."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    # Primero, obtener todas las sesiones del usuario
    cursor.execute("SELECT id FROM sessions WHERE user_id = ?", (user_id,))
    session_ids = [row[0] for row in cursor.fetchall()]
    
    if session_ids:
        # Eliminar interpretaciones de esas sesiones
        cursor.execute(f"DELETE FROM interpretations WHERE session_id IN ({','.join('?' for _ in session_ids)})", session_ids)
        # Eliminar las sesiones
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    
    # Finalmente, eliminar al usuario
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_session(session_id):
    """Elimina una sesión y sus interpretaciones asociadas."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interpretations WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def create_session(user_id):
    """Crea una nueva sesión para un usuario y retorna el ID de la sesión."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    
    # Verificar estructura de la tabla para compatibilidad
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'session_type_id' in columns:
        # Base de datos expandida
        cursor.execute("""
            INSERT INTO sessions 
            (user_id, session_type_id, start_time, completion_status) 
            VALUES (?, ?, CURRENT_TIMESTAMP, 'started')
        """, (user_id, 1))  # session_type_id = 1 para sesión básica
    else:
        # Base de datos original
        cursor.execute("INSERT INTO sessions (user_id) VALUES (?)", (user_id,))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def add_interpretation(session_id, word, confidence=None):
    """Agrega una palabra interpretada a una sesión."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(interpretations)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'word_detected' in columns:
        cursor.execute("""
            INSERT INTO interpretations
            (session_id, word_detected, confidence_score, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (session_id, word, confidence))
    else:
        cursor.execute("INSERT INTO interpretations (session_id, word) VALUES (?, ?)", (session_id, word))

    conn.commit()
    conn.close()

def get_user_sessions(user_id):
    """Obtiene todas las sesiones de un usuario, ordenadas por fecha."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    
    # Verificar estructura de la tabla para compatibilidad
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'start_time' in columns:
        # Base de datos expandida
        cursor.execute("SELECT id, start_time FROM sessions WHERE user_id = ? ORDER BY start_time DESC", (user_id,))
    else:
        # Base de datos original
        cursor.execute("SELECT id, timestamp FROM sessions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def get_session_interpretations(session_id):
    """Obtiene todas las interpretaciones de una sesión, en orden."""
    conn = sqlite3.connect(get_database_name())
    cursor = conn.cursor()
    
    # Verificar estructura de la tabla para compatibilidad
    cursor.execute("PRAGMA table_info(interpretations)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'word_detected' in columns:
        # Base de datos expandida
        cursor.execute("SELECT word_detected, timestamp FROM interpretations WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    else:
        # Base de datos original
        cursor.execute("SELECT word, timestamp FROM interpretations WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    
    interpretations = cursor.fetchall()
    conn.close()
    return interpretations

# Las funciones de gestión de gestos complejas han sido eliminadas.
# Ahora se usa detección automática directa en training_utils.py

if __name__ == '__main__':
    # Esto se ejecutará solo cuando corras 'python database.py' directamente
    # Es útil para inicializar la base de datos por primera vez.
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos lista.")
    # El código de ejemplo para agregar usuario ya no es válido, lo eliminamos. 