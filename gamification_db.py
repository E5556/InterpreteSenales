import json
from datetime import date, timedelta
from database_v2 import DatabaseManager

LEVELS = [
    (1, "Principiante", 0),
    (2, "Aprendiz",     100),
    (3, "Comunicador",  300),
    (4, "Intérprete",   600),
    (5, "Experto",      1000),
    (6, "Maestro",      2000),
]

# (name, description, points, rarity, type_id, requirements)
# type_ids: 1=Aprendizaje, 2=Constancia, 3=Precisión, 5=Explorador, 6=Maestría, 7=Velocidad
DEFAULT_ACHIEVEMENTS = [
    ("Primera Señal",   "Reconoce tu primer gesto",                       10,  "common",     1, {"gestures_total": 1}),
    ("Comunicador",     "Alcanza 50 gestos reconocidos en total",          50,  "common",     1, {"gestures_total": 50}),
    ("Velocista",       "Reconoce 10 gestos en una sola sesión",          25,  "common",     7, {"gestures_session": 10}),
    ("Racha de 3 días", "Usa la app 3 días consecutivos",                 30,  "common",     2, {"daily_streak": 3}),
    ("Preciso",         "Completa una sesión con precisión mayor al 90%", 40,  "rare",       3, {"accuracy_rate": 90}),
    ("Semana perfecta", "Usa la app 7 días consecutivos",                100,  "rare",       2, {"daily_streak": 7}),
    ("Gran Explorador", "Alcanza 200 gestos reconocidos en total",        75,  "rare",       5, {"gestures_total": 200}),
    ("Maestro de señas","Alcanza 500 gestos reconocidos en total",       200,  "epic",       6, {"gestures_total": 500}),
    # Logros por gesto específico
    ("Experto en HOLA",    "Reconoce HOLA 30 veces con precisión >85%",  35,  "uncommon",   3, {"gesture_mastery": {"word": "HOLA",    "count": 30, "min_confidence": 0.85}}),
    ("Experto en ADIOS",   "Reconoce ADIOS 30 veces con precisión >85%", 35,  "uncommon",   3, {"gesture_mastery": {"word": "ADIOS",   "count": 30, "min_confidence": 0.85}}),
    ("Experto en ADULTO",  "Reconoce ADULTO 20 veces",                   30,  "uncommon",   1, {"gesture_mastery": {"word": "ADULTO",  "count": 20, "min_confidence": 0.0}}),
    ("Experto en ANCIANO", "Reconoce ANCIANO 20 veces",                  30,  "uncommon",   1, {"gesture_mastery": {"word": "ANCIANO", "count": 20, "min_confidence": 0.0}}),
    ("Políglota",          "Practica todos los gestos disponibles 5 veces cada uno", 80, "rare", 5, {"all_gestures_min": 5}),
    ("Perfeccionista",     "Logra una sesión con precisión promedio >95%", 60, "epic",       3, {"accuracy_rate": 95}),
    ("Racha de fuego",     "Usa la app 14 días consecutivos",            150,  "epic",       2, {"daily_streak": 14}),
    ("Velocista extremo",  "Reconoce 25 gestos en una sola sesión",       50,  "rare",       7, {"gestures_session": 25}),
]

DAILY_CHALLENGE_POOL = [
    "Reconoce {n} señas hoy",
    "Completa {n} sesión(es) de interpretación hoy",
    "Logra una sesión con precisión mayor al 80%",
    "Reconoce al menos {n} señas distintas hoy",
]


def _get_level_info(total_points):
    level_num, level_name, _ = LEVELS[0]
    next_points = LEVELS[1][2] if len(LEVELS) > 1 else 9999
    for i, (num, name, req) in enumerate(LEVELS):
        if total_points >= req:
            level_num, level_name = num, name
            next_points = LEVELS[i + 1][2] if i + 1 < len(LEVELS) else req
    return level_num, level_name, next_points


def seed_default_achievements():
    db = DatabaseManager()
    existing = db.execute_query("SELECT achievement_name FROM achievements")
    existing_names = {r[0] for r in existing}
    for name, desc, pts, rarity, type_id, reqs in DEFAULT_ACHIEVEMENTS:
        if name not in existing_names:
            db.execute_query(
                "INSERT INTO achievements (achievement_name, description, points_value, rarity, type_id, requirements, is_active) VALUES (?,?,?,?,?,?,1)",
                (name, desc, pts, rarity, type_id, json.dumps(reqs))
            )


def get_user_gamification_profile(user_id):
    db = DatabaseManager()
    row = db.execute_query(
        "SELECT total_points, current_level, daily_streak, last_activity_date FROM user_points WHERE user_id = ?",
        (user_id,)
    )
    if not row:
        db.execute_query(
            "INSERT OR IGNORE INTO user_points (user_id, total_points, current_level) VALUES (?,0,1)",
            (user_id,)
        )
        total_points, daily_streak = 0, 0
        last_activity = None
    else:
        total_points = row[0][0] or 0
        daily_streak = row[0][2] or 0
        last_activity = row[0][3]

    user_row = db.execute_query("SELECT username FROM users WHERE id = ?", (user_id,))
    username = user_row[0][0] if user_row else "Usuario"

    level_num, level_name, next_level_points = _get_level_info(total_points)
    current_level_points = next(req for num, _, req in LEVELS if num == level_num)
    progress_in_level = total_points - current_level_points
    range_in_level = max(1, next_level_points - current_level_points)
    progress_pct = min(100, int(progress_in_level / range_in_level * 100))

    return {
        "username": username,
        "total_points": total_points,
        "level_num": level_num,
        "level_name": level_name,
        "next_level_points": next_level_points,
        "progress_pct": progress_pct,
        "daily_streak": daily_streak,
        "last_activity": last_activity,
    }


def get_user_achievements(user_id):
    db = DatabaseManager()
    return db.execute_query(
        """SELECT a.achievement_name, a.description, a.points_value, a.rarity, ua.earned_date
           FROM user_achievements ua
           JOIN achievements a ON ua.achievement_id = a.id
           WHERE ua.user_id = ?
           ORDER BY ua.earned_date DESC""",
        (user_id,)
    )


def get_all_achievements():
    db = DatabaseManager()
    return db.execute_query(
        "SELECT id, achievement_name, description, points_value, rarity FROM achievements WHERE is_active=1 ORDER BY points_value"
    )


def get_points_history(user_id, limit=20):
    db = DatabaseManager()
    return db.execute_query(
        "SELECT earned_date, points_type, points_earned, description FROM points_history WHERE user_id=? ORDER BY earned_date DESC LIMIT ?",
        (user_id, limit)
    )


def get_daily_challenges(user_id):
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day

    import random
    rng = random.Random(seed)

    counts_today = _get_gestures_today(user_id)
    sessions_today = _get_sessions_today(user_id)

    challenges = [
        {
            "title": f"Reconoce {rng.randint(5,12)} señas hoy",
            "target": rng.randint(5, 12),
            "current": counts_today,
            "type": "gestures",
        },
        {
            "title": f"Completa {rng.randint(1,3)} sesión(es) hoy",
            "target": rng.randint(1, 3),
            "current": sessions_today,
            "type": "sessions",
        },
        {
            "title": "Logra una sesión con precisión mayor al 80%",
            "target": 1,
            "current": _get_high_accuracy_sessions_today(user_id),
            "type": "accuracy",
        },
    ]
    # Clamp seed-generated targets to be consistent
    rng2 = random.Random(seed + 1)
    challenges[0]["target"] = rng2.randint(5, 12)
    challenges[0]["title"] = f"Reconoce {challenges[0]['target']} señas hoy"
    challenges[1]["target"] = rng2.randint(1, 3)
    challenges[1]["title"] = f"Completa {challenges[1]['target']} sesión(es) hoy"

    return challenges


def get_weekly_challenge(user_id):
    """Reto semanal rotativo basado en el número de semana ISO."""
    today = date.today()
    week_num = today.isocalendar()[1]
    year = today.year
    seed = year * 100 + week_num

    import random
    rng = random.Random(seed)
    challenge_type = rng.randint(0, 2)

    db = DatabaseManager()
    # Gestos esta semana
    rows = db.execute_query(
        """SELECT COUNT(*) FROM interpretations i
           JOIN sessions s ON i.session_id = s.id
           WHERE s.user_id=? AND strftime('%W', i.timestamp)=strftime('%W','now')
             AND strftime('%Y', i.timestamp)=strftime('%Y','now')""",
        (user_id,)
    )
    gestures_week = rows[0][0] if rows else 0

    # Sesiones esta semana
    rows2 = db.execute_query(
        """SELECT COUNT(DISTINCT s.id) FROM sessions s
           JOIN interpretations i ON i.session_id = s.id
           WHERE s.user_id=? AND strftime('%W', s.start_time)=strftime('%W','now')
             AND strftime('%Y', s.start_time)=strftime('%Y','now')""",
        (user_id,)
    )
    sessions_week = rows2[0][0] if rows2 else 0

    # Sesiones con precisión >=80% esta semana
    rows3 = db.execute_query(
        """SELECT COUNT(*) FROM (
               SELECT s.id FROM sessions s
               JOIN interpretations i ON i.session_id = s.id
               WHERE s.user_id=? AND strftime('%W', s.start_time)=strftime('%W','now')
                 AND strftime('%Y', s.start_time)=strftime('%Y','now')
                 AND i.confidence_score IS NOT NULL
               GROUP BY s.id HAVING AVG(i.confidence_score) >= 0.80
           )""",
        (user_id,)
    )
    precise_week = rows3[0][0] if rows3 else 0

    challenges = [
        {"title": f"Acumula {rng.randint(80,150)} gestos esta semana",
         "target": rng.randint(80, 150), "current": gestures_week, "type": "gestures_week"},
        {"title": f"Completa {rng.randint(4,8)} sesiones esta semana",
         "target": rng.randint(4, 8), "current": sessions_week, "type": "sessions_week"},
        {"title": "Logra 3 sesiones con precisión >80% esta semana",
         "target": 3, "current": precise_week, "type": "accuracy_week"},
    ]
    # Usar seed fija para que los targets no cambien al recalcular
    rng2 = random.Random(seed + 99)
    ch = challenges[challenge_type]
    if ch["type"] == "gestures_week":
        ch["target"] = rng2.randint(80, 150)
        ch["title"] = f"Acumula {ch['target']} gestos esta semana"
    elif ch["type"] == "sessions_week":
        ch["target"] = rng2.randint(4, 8)
        ch["title"] = f"Completa {ch['target']} sesiones esta semana"

    return ch


def _get_gestures_today(user_id):
    db = DatabaseManager()
    rows = db.execute_query(
        """SELECT COUNT(*) FROM interpretations i
           JOIN sessions s ON i.session_id = s.id
           WHERE s.user_id = ? AND DATE(i.timestamp) = DATE('now')""",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def _get_sessions_today(user_id):
    # Cuenta sesiones de hoy que tienen al menos 1 interpretación guardada
    db = DatabaseManager()
    rows = db.execute_query(
        """SELECT COUNT(DISTINCT s.id) FROM sessions s
           JOIN interpretations i ON i.session_id = s.id
           WHERE s.user_id=? AND DATE(s.start_time)=DATE('now')""",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def _get_high_accuracy_sessions_today(user_id):
    # Sesiones de hoy donde el confidence promedio de las interpretaciones >= 0.80
    db = DatabaseManager()
    rows = db.execute_query(
        """SELECT COUNT(*) FROM (
               SELECT s.id, AVG(i.confidence_score) as avg_conf
               FROM sessions s
               JOIN interpretations i ON i.session_id = s.id
               WHERE s.user_id=? AND DATE(s.start_time)=DATE('now')
                 AND i.confidence_score IS NOT NULL
               GROUP BY s.id
               HAVING avg_conf >= 0.80
           )""",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def award_session_points(user_id, session_id, gestures_count=0, accuracy=0.0):
    """Otorga puntos al cerrar una sesión y verifica logros nuevos.
    Retorna (new_achievements, new_level_info) donde new_level_info es None o dict si subió de nivel."""
    if gestures_count <= 0:
        return [], None

    db = DatabaseManager()

    # Nivel antes de otorgar puntos
    prev_rows = db.execute_query("SELECT total_points FROM user_points WHERE user_id=?", (user_id,))
    prev_pts = (prev_rows[0][0] or 0) if prev_rows else 0
    prev_level = _get_level_info(prev_pts)[0]

    # Puntos base: 2 pts por gesto, bonus por precisión
    base = gestures_count * 2
    bonus = 0
    if accuracy >= 0.9:
        bonus = 10
    elif accuracy >= 0.75:
        bonus = 5

    # Bonus por racha perfecta: racha >= 3 días Y precisión >= 80% → multiplicador x1.5
    streak_rows = db.execute_query(
        "SELECT daily_streak FROM user_points WHERE user_id=?", (user_id,)
    )
    current_streak = (streak_rows[0][0] or 0) if streak_rows else 0
    streak_multiplier = 1.5 if (current_streak >= 3 and accuracy >= 0.8) else 1.0
    total = int((base + bonus) * streak_multiplier)

    desc = f"Sesión: {gestures_count} gestos (precisión {int(accuracy*100)}%)"
    if streak_multiplier > 1.0:
        desc += f" ✨ Racha perfecta x{streak_multiplier} (racha {current_streak} días)"

    db.update_user_points(user_id, total, "session", desc)

    # Actualizar racha diaria
    _update_daily_streak(user_id)

    # Actualizar accuracy en la sesión si la columna existe
    try:
        db.execute_query(
            "UPDATE sessions SET accuracy_rate=?, completion_status='completed' WHERE id=?",
            (int(accuracy * 100), session_id)
        )
    except Exception:
        pass

    # Verificar logros
    new_achievements = _check_gamification_achievements(user_id, gestures_count, accuracy)

    # Detectar subida de nivel
    new_rows = db.execute_query("SELECT total_points FROM user_points WHERE user_id=?", (user_id,))
    new_pts = (new_rows[0][0] or 0) if new_rows else 0
    new_level_num, new_level_name, _ = _get_level_info(new_pts)
    new_level_info = None
    if new_level_num > prev_level:
        user_row = db.execute_query("SELECT username FROM users WHERE id=?", (user_id,))
        username = user_row[0][0] if user_row else "Usuario"
        new_level_info = {
            "level_num":  new_level_num,
            "level_name": new_level_name,
            "username":   username,
            "total_points": new_pts,
        }

    return new_achievements, new_level_info


def _update_daily_streak(user_id):
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT daily_streak, last_activity_date FROM user_points WHERE user_id=?",
        (user_id,)
    )
    if not rows:
        return
    streak, last_date = rows[0]
    streak = streak or 0
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    if last_date == today_str:
        return  # ya contado hoy
    elif last_date == yesterday_str:
        streak += 1
    else:
        streak = 1

    db.execute_query(
        "UPDATE user_points SET daily_streak=?, last_activity_date=? WHERE user_id=?",
        (streak, today_str, user_id)
    )


def _get_real_gestures_total(user_id):
    """Cuenta interpretaciones reales desde la tabla interpretations."""
    db = DatabaseManager()
    rows = db.execute_query(
        """SELECT COUNT(*) FROM interpretations i
           JOIN sessions s ON i.session_id = s.id
           WHERE s.user_id = ?""",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def _get_real_sessions_completed(user_id):
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT COUNT(*) FROM sessions WHERE user_id=?",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def _get_best_accuracy(user_id):
    """Mejor accuracy_rate registrada en sesiones del usuario (0-100)."""
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT MAX(accuracy_rate) FROM sessions WHERE user_id=? AND accuracy_rate IS NOT NULL",
        (user_id,)
    )
    return rows[0][0] or 0 if rows else 0


def _check_gamification_achievements(user_id, gestures_session, accuracy):
    db = DatabaseManager()

    # Métricas reales desde la BD
    gestures_total   = _get_real_gestures_total(user_id) + gestures_session
    sessions_completed = _get_real_sessions_completed(user_id)
    best_accuracy    = max(_get_best_accuracy(user_id), int(accuracy * 100))

    streak_rows = db.execute_query(
        "SELECT daily_streak FROM user_points WHERE user_id=?", (user_id,)
    )
    streak = (streak_rows[0][0] or 0) if streak_rows else 0

    all_ach = db.execute_query(
        "SELECT id, achievement_name, requirements, points_value FROM achievements WHERE is_active=1"
    )
    earned_rows = db.execute_query(
        "SELECT achievement_id FROM user_achievements WHERE user_id=?", (user_id,)
    )
    already_earned = {r[0] for r in earned_rows}

    new_achievements = []
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        for ach_id, ach_name, reqs_json, pts in all_ach:
            if ach_id in already_earned:
                continue
            reqs = json.loads(reqs_json) if reqs_json else {}
            earned = False

            if "gestures_total" in reqs:
                earned = gestures_total >= reqs["gestures_total"]
            elif "gestures_session" in reqs:
                earned = gestures_session >= reqs["gestures_session"]
            elif "sessions_completed" in reqs:
                earned = sessions_completed >= reqs["sessions_completed"]
            elif "daily_streak" in reqs:
                earned = streak >= reqs["daily_streak"]
            elif "accuracy_rate" in reqs:
                earned = best_accuracy >= reqs["accuracy_rate"]
            elif "gesture_mastery" in reqs:
                gm = reqs["gesture_mastery"]
                word = gm.get("word", "")
                min_count = gm.get("count", 1)
                min_conf = gm.get("min_confidence", 0.0)
                if min_conf > 0:
                    count_rows = db.execute_query(
                        """SELECT COUNT(*) FROM interpretations i
                           JOIN sessions s ON i.session_id = s.id
                           WHERE s.user_id=? AND i.word_detected=? AND i.confidence_score >= ?""",
                        (user_id, word, min_conf)
                    )
                else:
                    count_rows = db.execute_query(
                        """SELECT COUNT(*) FROM interpretations i
                           JOIN sessions s ON i.session_id = s.id
                           WHERE s.user_id=? AND i.word_detected=?""",
                        (user_id, word)
                    )
                earned = (count_rows[0][0] if count_rows else 0) >= min_count
            elif "all_gestures_min" in reqs:
                min_each = reqs["all_gestures_min"]
                # Obtener gestos disponibles del modelo
                try:
                    from training_utils import get_gestures_with_valid_keypoints
                    available = [g.upper() for g in get_gestures_with_valid_keypoints()]
                except Exception:
                    available = ["ADIOS", "ADULTO", "ANCIANO", "GATO", "HOLA"]
                all_ok = True
                for w in available:
                    cnt_rows = db.execute_query(
                        """SELECT COUNT(*) FROM interpretations i
                           JOIN sessions s ON i.session_id = s.id
                           WHERE s.user_id=? AND i.word_detected=?""",
                        (user_id, w)
                    )
                    if (cnt_rows[0][0] if cnt_rows else 0) < min_each:
                        all_ok = False
                        break
                earned = all_ok

            if earned:
                cursor.execute(
                    "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?,?)",
                    (user_id, ach_id)
                )
                conn.commit()
                db.update_user_points(user_id, pts, "achievement", f"Logro: {ach_name}")
                db.create_notification(user_id, "achievement_earned",
                                       "¡Logro desbloqueado!", f"Has obtenido: {ach_name}")
                new_achievements.append(ach_name)
    finally:
        conn.close()

    return new_achievements


def sync_user_gamification(user_id):
    """Recalcula y asigna logros pendientes usando datos históricos reales.
    Llamar una vez para sincronizar usuarios con sesiones previas a la gamificación."""
    return _check_gamification_achievements(user_id, 0, 0.0)


def ensure_evaluation_table():
    """Crea la tabla evaluation_results si no existe."""
    db = DatabaseManager()
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS evaluation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score_pct INTEGER NOT NULL,
            correct INTEGER NOT NULL,
            total INTEGER NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def save_evaluation_result(user_id, score_pct, correct, total, results):
    """Guarda el resultado de una evaluación. results = [(word, pred, ok, conf), ...]"""
    ensure_evaluation_table()
    db = DatabaseManager()
    db.execute_query(
        "INSERT INTO evaluation_results (user_id, score_pct, correct, total, details) VALUES (?,?,?,?,?)",
        (user_id, score_pct, correct, total, json.dumps(
            [{"word": w, "pred": p, "ok": ok, "conf": round(c, 4)} for w, p, ok, c in results]
        ))
    )


def get_evaluation_history(user_id, limit=20):
    """Retorna los últimos resultados de evaluación del usuario."""
    ensure_evaluation_table()
    db = DatabaseManager()
    return db.execute_query(
        "SELECT id, score_pct, correct, total, details, created_at FROM evaluation_results WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )


def generate_level_certificate(level_info, output_path):
    """Genera un certificado PDF al subir de nivel. level_info: dict con username, level_num, level_name, total_points."""
    from datetime import datetime
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.pdfgen import canvas as pdf_canvas

    W, H = landscape(A4)
    c = pdf_canvas.Canvas(output_path, pagesize=landscape(A4))

    # Fondo degradado simulado con rectángulos
    c.setFillColor(colors.HexColor("#0f0f1a"))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Borde decorativo
    c.setStrokeColor(colors.HexColor("#7c3aed"))
    c.setLineWidth(4)
    c.roundRect(1*cm, 1*cm, W - 2*cm, H - 2*cm, 16, fill=0, stroke=1)
    c.setLineWidth(1)
    c.setStrokeColor(colors.HexColor("#a78bfa"))
    c.roundRect(1.3*cm, 1.3*cm, W - 2.6*cm, H - 2.6*cm, 12, fill=0, stroke=1)

    LEVEL_EMOJIS = {1:"🌱", 2:"📚", 3:"💬", 4:"🎯", 5:"⭐", 6:"🏆"}
    emoji = LEVEL_EMOJIS.get(level_info["level_num"], "🏅")

    # Título
    c.setFillColor(colors.HexColor("#a78bfa"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(W/2, H - 3*cm, "SISTEMA INTÉRPRETE LSP")

    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(W/2, H - 5.2*cm, "CERTIFICADO DE NIVEL")

    # Línea decorativa
    c.setStrokeColor(colors.HexColor("#7c3aed"))
    c.setLineWidth(2)
    c.line(W/2 - 6*cm, H - 5.8*cm, W/2 + 6*cm, H - 5.8*cm)

    # Texto principal
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(W/2, H - 7*cm, "Se certifica que")

    c.setFillColor(colors.HexColor("#7c3aed"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(W/2, H - 8.5*cm, level_info["username"].upper())

    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(W/2, H - 9.8*cm, "ha alcanzado el nivel")

    # Nivel destacado
    c.setFillColor(colors.HexColor("#f59e0b"))
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(W/2, H - 12*cm, f"Nivel {level_info['level_num']} — {level_info['level_name']}")

    c.setFillColor(colors.HexColor("#a78bfa"))
    c.setFont("Helvetica", 16)
    c.drawCentredString(W/2, H - 13.2*cm, f"con {level_info['total_points']} puntos acumulados")

    # Fecha
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(W/2, H - 14.5*cm, f"Fecha: {datetime.now().strftime('%d de %B de %Y')}")

    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, 1.6*cm, "Intérprete LSP — Sistema de reconocimiento de lengua de señas peruana")

    c.save()
