import random
from flask import Flask, render_template, request, session, redirect, url_for
from database import get_db, close_db, init_db

app = Flask(__name__)
app.secret_key = "xingce-practice-secret-key-2024"
app.teardown_appcontext(close_db)

QUESTIONS_PER_ROUND = 5


@app.route("/", methods=["GET", "POST"])
def index():
    """首页：选择类别和题量，开始刷题"""
    db = get_db()

    # 获取所有类别
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

        # 根据类别筛选题目
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

    # GET 请求：显示选择页面
    return render_template("index.html", categories=categories)

@app.route("/question/<int:qindex>")
def question(qindex):
    """显示第 qindex 道题（1-based）"""
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
def submit():
    """提交当前题目的答案"""
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
            "INSERT INTO answers (question_id, user_answer, is_correct) VALUES (?, ?, ?)",
            (int(qid), user_answer, 1 if user_answer == correct else 0)
        )
        db.commit()

    if action == "finish" or current_index + 1 >= len(questions):
        return redirect(url_for("result"))
    else:
        return redirect(url_for("question", qindex=current_index + 2))


@app.route("/result")
def result():
    """显示本轮答题结果"""
    questions = session.get("questions", [])
    answers = session.get("answers", {})

    if not questions:
        return redirect(url_for("index"))

    correct_count = 0
    results = []
    for q in questions:
        qid = str(q["id"])
        user_ans = answers.get(qid, "未作答")
        is_correct = user_ans == q["correct_answer"]
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
def wrong():
    """查看所有错题"""
    db = get_db()
    rows = db.execute("""
        SELECT DISTINCT q.*, a.user_answer, a.created_at
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.is_correct = 0
        ORDER BY a.created_at DESC
    """).fetchall()

    wrong_list = [dict(row) for row in rows]
    return render_template("wrong.html", wrong_list=wrong_list)

@app.route("/stats")
def stats():
    """历史成绩统计页"""
    db = get_db()

    # 总答题数和正确率
    row = db.execute("""
        SELECT COUNT(*) AS total,
               SUM(is_correct) AS correct
        FROM answers
    """).fetchone()
    total = row["total"] or 0
    correct = row["correct"] or 0
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    # 各模块正确率
    category_stats = db.execute("""
        SELECT q.category,
               COUNT(*) AS total,
               SUM(a.is_correct) AS correct
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        GROUP BY q.category
        ORDER BY q.category
    """).fetchall()

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