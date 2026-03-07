"""Authentication model: password and security question CRUD."""

from datetime import datetime
from app.core.database import get_connection
from app.core import security as sec


def setup_password(password: str, salt: str, questions: list[dict]) -> None:
    """
    Create the app_config row and store hashed security question answers.
    questions: list of {'question_text': str, 'answer': str} (3 items)
    """
    password_hash = sec.hash_password(password)
    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_config (id, password_hash, salt, created_at, updated_at) "
            "VALUES (1, ?, ?, ?, ?)",
            (password_hash, salt, now, now),
        )
        conn.execute("DELETE FROM security_questions")
        for i, q in enumerate(questions, start=1):
            answer_hash = sec.hash_answer(q["answer"])
            conn.execute(
                "INSERT INTO security_questions (question_index, question_text, answer_hash) "
                "VALUES (?, ?, ?)",
                (i, q["question_text"], answer_hash),
            )
        conn.commit()
    finally:
        conn.close()


def get_config() -> dict | None:
    """Return the app_config row as a dict, or None if not set up."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM app_config WHERE id = 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def verify_password(password: str) -> bool:
    """Return True if the given password matches the stored hash."""
    config = get_config()
    if not config:
        return False
    return sec.verify_password(password, config["password_hash"])


def get_security_questions() -> list[dict]:
    """Return the 3 security questions (ordered by question_index)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT question_index, question_text, answer_hash FROM security_questions ORDER BY question_index"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def verify_security_answers(answers: list[str]) -> bool:
    """
    Verify all 3 security answers. Returns True only if ALL match.
    answers: ordered list of plaintext answers [ans1, ans2, ans3]
    """
    questions = get_security_questions()
    if len(questions) != 3 or len(answers) != 3:
        return False
    return all(
        sec.verify_answer(answers[i], questions[i]["answer_hash"])
        for i in range(3)
    )


def change_password(new_password: str) -> None:
    """Update the stored password hash (used after successful security Q reset)."""
    new_hash = sec.hash_password(new_password)
    # Regenerate salt so the AES key changes too (old encrypted fields will be re-decryptable
    # only with the new key — acceptable trade-off for a personal app without stored ciphertext
    # beyond account numbers; user should update those manually if needed).
    new_salt = sec.generate_salt()
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE app_config SET password_hash = ?, salt = ?, updated_at = ? WHERE id = 1",
            (new_hash, new_salt, now),
        )
        conn.commit()
    finally:
        conn.close()


def update_security_questions(questions: list[dict]) -> None:
    """Replace all 3 security questions and answers."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM security_questions")
        for i, q in enumerate(questions, start=1):
            answer_hash = sec.hash_answer(q["answer"])
            conn.execute(
                "INSERT INTO security_questions (question_index, question_text, answer_hash) VALUES (?, ?, ?)",
                (i, q["question_text"], answer_hash),
            )
        conn.commit()
    finally:
        conn.close()
