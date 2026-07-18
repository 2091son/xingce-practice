import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "xingce.db")


def get_db():
    """获取数据库连接（每次请求用同一个连接）"""
    import flask
    if "db" not in flask.g:
        flask.g.db = sqlite3.connect(DATABASE)
        flask.g.db.row_factory = sqlite3.Row
    return flask.g.db


def close_db(exception=None):
    """请求结束后关闭数据库连接"""
    import flask
    db = flask.g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """创建表并插入示例题目"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            question_id INTEGER NOT NULL,
            user_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        sample_questions = [
            ("言语理解", "填入划横线部分最恰当的一项是：\n近年来，我国在信息技术领域取得了____的成就。",
             "举世瞩目", "微不足道", "差强人意", "乏善可陈", "A",
             "举世瞩目意为全世界都关注，符合'取得了成就'的语境。"),
            ("言语理解", "下列句子中，没有语病的一项是：",
             "通过这次学习，使我提高了认识。", "他的写作水平有了明显的提高。",
             "我们认真研究听取了大家的意见。", "能否刻苦学习是取得好成绩的关键。", "B",
             "A缺少主语，C语序不当（应先听取后研究），D一面与两面搭配不当。"),
            ("数量关系", "某商店购进一批商品，按50%的利润定价，结果只销售了70%。为了尽快售完，商店决定打折出售剩余商品，这样全部售完后实际利润是原定利润的80%。问剩余商品打了几折？",
             "六折", "七折", "八折", "九折", "A",
             "设成本为100，总数量为100件。定价150，卖出70件。设折扣为x。总利润=70×50+30×(150x-100)。原定利润=5000，实际=4000。解得x≈0.78，即约六折。"),
            ("数量关系", "甲、乙两人同时从A、B两地相向而行，甲的速度是乙的1.5倍。两人相遇后，甲又用了2小时到达B地。问乙从B地到A地需要多少小时？",
             "4.5", "5", "6", "7.5", "D",
             "设乙速为v，甲速为1.5v。相遇时甲走了全程的3/5，乙走了2/5。甲走剩余2/5用了2小时，全程S=5×甲速。乙走全程需要S/v=7.5小时。"),
            ("判断推理", "所有的猫都是哺乳动物。\n有些哺乳动物是水生动物。\n由此可以推出：",
             "有些猫是水生动物", "有些水生动物是猫", "有些哺乳动物是猫", "以上都不必然推出", "D",
             "从'所有猫是哺乳动物'和'有些哺乳动物是水生动物'不能必然推出猫与水生动物有任何关系。"),
            ("判断推理", "从所给的四个选项中，选择最合适的一个填入问号处，使之呈现一定的规律性。\n\n○ △ □\n△ □ ○\n□ ○ ？",
             "○", "△", "□", "☆", "B",
             "每行第一个图形移动到第三个位置，第二个移动到第一个，第三个移动到第二个。第三行应为△。"),
            ("资料分析", "2023年某省GDP为5.2万亿元，同比增长6.5%。2024年目标增速为6%。若达成目标，2024年该省GDP约为多少万亿元？",
             "5.41", "5.51", "5.61", "5.71", "B",
             "2024年GDP=5.2×(1+6%)=5.2×1.06=5.512≈5.51万亿元。"),
            ("资料分析", "某公司2023年上半年销售额为1200万元，下半年销售额比上半年增长了25%，全年销售额同比增长了20%。问该公司2022年全年销售额为多少万元？",
             "2250", "2375", "2500", "2625", "A",
             "2023全年=1200+1200×1.25=2700万元。2022全年=2700÷1.2=2250万元。"),
            ("常识判断", "根据我国宪法规定，下列哪项属于公民的基本权利？",
             "依法纳税", "服兵役", "受教育权", "遵守劳动纪律", "C",
             "受教育权是宪法规定的公民基本权利。A、B、D均为公民的基本义务。"),
            ("常识判断", "下列关于我国地理的表述，正确的是：",
             "黄河是我国最长的河流", "塔里木盆地是我国面积最大的盆地",
             "洞庭湖是我国最大的淡水湖", "秦岭-淮河一线是400毫米等降水量线", "B",
             "A长江最长；C鄱阳湖是最大淡水湖；D秦岭-淮河是800毫米等降水量线。塔里木盆地正确。"),
        ]
        cursor.executemany(
            "INSERT INTO questions (category, question_text, option_a, option_b, option_c, option_d, correct_answer, explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            sample_questions
        )

    conn.commit()
    conn.close()
    print("数据库初始化完成！")


if __name__ == "__main__":
    init_db()