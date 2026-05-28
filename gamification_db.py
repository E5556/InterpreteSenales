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
    ("Primera Señal",   "Reconoce tu primer gesto",                       10,  "common", 1, {"gestures_total": 1}),
    ("Comunicador",     "Alcanza 50 gestos reconocidos en total",          50,  "common", 1, {"gestures_total": 50}),
    ("Velocista",       "Reconoce 10 gestos en una sola sesión",          25,  "common", 7, {"gestures_session": 10}),
    ("Racha de 3 días", "Usa la app 3 días consecutivos",                 30,  "common", 2, {"daily_streak": 3}),
    ("Preciso",         "Completa una sesión con precisión mayor al 90%", 40,  "rare",   3, {"accuracy_rate": 90}),
    ("Semana perfecta", "Usa la app 7 días consecutivos",                100,  "rare",   2, {"daily_streak": 7}),
    ("Gran Explorador", "Alcanza 200 gestos reconocidos en total",        75,  "rare",   5, {"gestures_total": 200}),
    ("Maestro de señas","Alcanza 500 gestos reconocidos en total",       200,  "epic",   6, {"gestures_total": 500}),
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
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT COUNT(*) FROM sessions WHERE user_id=? AND DATE(start_time)=DATE('now') AND completion_status='completed'",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def _get_high_accuracy_sessions_today(user_id):
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT COUNT(*) FROM sessions WHERE user_id=? AND DATE(start_time)=DATE('now') AND accuracy_rate>=80",
        (user_id,)
    )
    return rows[0][0] if rows else 0


def award_session_points(user_id, session_id, gestures_count=0, accuracy=0.0):
    """Otorga puntos al cerrar una sesión y verifica logros nuevos."""
    if gestures_count <= 0:
        return []

    db = DatabaseManager()

    # Puntos base: 2 pts por gesto, bonus por precisión
    base = gestures_count * 2
    bonus = 0
    if accuracy >= 0.9:
        bonus = 10
    elif accuracy >= 0.75:
        bonus = 5
    total = base + bonus

    db.update_user_points(user_id, total, "session",
                          f"Sesión: {gestures_count} gestos (precisión {int(accuracy*100)}%)")

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
    return new_achievements


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
            # Logros que requieren métricas no implementadas se omiten silenciosamente
            # (gestures_mastered, features_used, users_helped, etc.)

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
