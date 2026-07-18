import random
import hashlib
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from database import get_db, close_db, init_db

app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = "xingce-practice-secret-key-2024"
app.teardown_appcontext(close_db)

QUESTIONS_PER_ROUND = 5


def login_required(f):
    """装饰器：未登录跳转到登录页"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def hash_password(password):
    """SHA256 哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not password:
            return render_template("register.html", error="用户名和密码不能为空")
        if password != password2:
            return render_template("register.html", error="两次密码不一致")

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return render_template("register.html", error="用户名已存在")

        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        db.commit()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password))
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="用户名或密码错误")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    db = get_db()

    categories = [
        row["category"]
        for row in db.execute("SELECT DISTINCT category FROM questions").fetchall()
    ]

    if request.method == "POST":
        selected_category = request.form.get("category", "全部")
        try:
            num_questions = int(request.form.get("num_questions", 5))
        except ValueError:
            num_questions = 5

        if selected_category == "全部":
            rows = db.execute("SELECT id FROM questions").fetchall()
        else:
            rows = db.execute(
                "SELECT id FROM questions WHERE category = ?", (selected_category,)
            ).fetchall()

        all_ids = [row["id"] for row in rows]

        if len(all_ids) < num_questions:
            return "题库题目不足，请选择更少的题量或联系管理员添加题目。"

        selected_ids = random.sample(all_ids, num_questions)
        questions = []
        for qid in selected_ids:
            row = db.execute(
                "SELECT * FROM questions WHERE id = ?", (qid,)
            ).fetchone()
            questions.append(dict(row))

        session["questions"] = questions
        session["current_index"] = 0
        session["answers"] = {}

        return redirect(url_for("question", qindex=1))

    return render_template("index.html", categories=categories)


@app.route("/question/<int:qindex>")
@login_required
def question(qindex):
    questions = session.get("questions", [])
    if not questions or qindex < 1 or qindex > len(questions):
        return redirect(url_for("index"))

    current_q = questions[qindex - 1]
    session["current_index"] = qindex - 1

    is_last = (qindex == len(questions))
    return render_template(
        "question.html",
        question=current_q,
        qindex=qindex,
        total=len(questions),
        is_last=is_last,
        selected_answer=session["answers"].get(str(current_q["id"]), "")
    )


@app.route("/submit", methods=["POST"])
@login_required
def submit():
    questions = session.get("questions", [])
    current_index = session.get("current_index", 0)

    if not questions or current_index >= len(questions):
        return redirect(url_for("index"))

    qid = str(questions[current_index]["id"])
    user_answer = request.form.get("answer", "")
    action = request.form.get("action", "next")

    if user_answer:
        session["answers"][qid] = user_answer
        db = get_db()
        correct = questions[current_index]["correct_answer"]
        db.execute(
            "INSERT INTO answers (user_id, question_id, user_answer, is_correct) VALUES (?, ?, ?, ?)",
            (session["user_id"], int(qid), user_answer, 1 if user_answer == correct else 0)
        )
        db.commit()

    if action == "finish" or current_index + 1 >= len(questions):
        return redirect(url_for("result"))
    else:
        return redirect(url_for("question", qindex=current_index + 2))


@app.route("/result")
@login_required
def result():
    questions = session.get("questions", [])
    answers = session.get("answers", {})

    if not questions:
        return redirect(url_for("index"))

    db = get_db()
    correct_count = 0
    results = []
    for q in questions:
        qid = q["id"]
        user_ans = answers.get(str(qid), "未作答")

        # 从数据库读取实际判分，而不是重新算
        row = db.execute(
            "SELECT is_correct FROM answers WHERE user_id=? AND question_id=? ORDER BY id DESC LIMIT 1",
            (session["user_id"], qid)
        ).fetchone()
        is_correct = bool(row["is_correct"]) if row else False

        if is_correct:
            correct_count += 1
        results.append({
            "question": q,
            "user_answer": user_ans,
            "is_correct": is_correct
        })

    total = len(questions)
    score = round(correct_count / total * 100, 1)

    return render_template(
        "result.html",
        results=results,
        correct_count=correct_count,
        total=total,
        score=score
    )

@app.route("/wrong")
@login_required
def wrong():
    db = get_db()
    rows = db.execute("""
        SELECT DISTINCT q.*, a.user_answer, a.created_at
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.is_correct = 0 AND a.user_id = ?
        ORDER BY a.created_at DESC
    """, (session["user_id"],)).fetchall()

    wrong_list = [dict(row) for row in rows]
    return render_template("wrong.html", wrong_list=wrong_list)


@app.route("/stats")
@login_required
def stats():
    db = get_db()

    row = db.execute("""
        SELECT COUNT(*) AS total, SUM(is_correct) AS correct
        FROM answers WHERE user_id = ?
    """, (session["user_id"],)).fetchone()
    total = row["total"] or 0
    correct = row["correct"] or 0
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    category_stats = db.execute("""
        SELECT q.category,
               COUNT(*) AS total,
               SUM(a.is_correct) AS correct
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.user_id = ?
        GROUP BY q.category
        ORDER BY q.category
    """, (session["user_id"],)).fetchall()

    cat_list = []
    for row in category_stats:
        t = row["total"]
        c = row["correct"] or 0
        cat_list.append({
            "category": row["category"],
            "total": t,
            "correct": c,
            "accuracy": round(c / t * 100, 1)
        })

    return render_template(
        "stats.html",
        total=total,
        correct=correct,
        accuracy=accuracy,
        cat_list=cat_list
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)