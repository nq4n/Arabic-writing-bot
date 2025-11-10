from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from functools import wraps
import json, os, csv, io, sqlite3
from dotenv import load_dotenv
from utils.import_users import import_users_from_file_storage

# Load environment variables from a .env file if present
load_dotenv()

# Subbase (optional) configuration - supports an optional SQLite file path via SUBBASE_SQLITE_PATH
SUBBASE_SQLITE_PATH = os.getenv('SUBBASE_SQLITE_PATH', '')

def get_subbase_conn():
    """Return sqlite3.Connection when SUBBASE_SQLITE_PATH is set, else None."""
    if not SUBBASE_SQLITE_PATH:
        return None
    conn = sqlite3.connect(SUBBASE_SQLITE_PATH, check_same_thread=False)
    return conn

app = Flask(__name__)
# IMPORTANT: Change this secret key in a production environment!
# It's best to load it from an environment variable.



# Ensure data files or DB tables are initialized once before handling requests.
# Some Flask installs may not expose `before_first_request`, so use `before_request`
# with an app-level flag to run initialization exactly once.
@app.before_request
def _ensure_init_request():
    if not app.config.get('DATA_INITIALIZED'):
        try:
            init_data_files()
        except Exception:
            # Initialization errors should not crash the app at request time.
            pass
        app.config['DATA_INITIALIZED'] = True
 
# --- AI Integration Setup ---
# Prefer reading secrets from environment (.env) rather than hardcoding
API_KEY = os.getenv("AI_API_KEY", "")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-secret")

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.json")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")

@app.template_filter('format_datetime')
def format_datetime(iso_string):
    """Format an ISO string to a more readable format."""
    if not iso_string:
        return ""
    dt_object = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt_object.strftime('%Y-%m-%dT%H:%M:%SZ') # Keep it ISO for machine, JS will format

def read_data(file_path):
    # This application is DB-backed (subbase). Read from configured DB.
    from utils.subbase_adapter import get_conn_from_env, read_table
    typ, conn = get_conn_from_env()
    if not conn:
        raise RuntimeError("Subbase is not configured. Set SUBBASE_BACKEND and connection env vars (SUBBASE_SQLITE_PATH or SUBBASE_PG_URL).")

    # Map filename to table name
    name = os.path.basename(file_path)
    table_map = {
        'users.json': 'users',
        'messages.json': 'messages',
        'submissions.json': 'submissions',
        'ratings.json': 'ratings'
    }
    table = table_map.get(name)
    if not table:
        return []

    rows = read_table(table)
    # normalize rows to match expected JSON structure
    out = []
    for r in rows:
        row = dict(r)
        # merge meta fields back into dict if present
        meta = row.pop('meta', None)
        if meta:
            try:
                if isinstance(meta, str):
                    meta = json.loads(meta)
            except Exception:
                pass
            if isinstance(meta, dict):
                row.update(meta)
        out.append(row)
    return out

def write_data(file_path, data):
    # This application is DB-backed (subbase). Write to configured DB table.
    from utils.subbase_adapter import get_conn_from_env, overwrite_table
    typ, conn = get_conn_from_env()
    if not conn:
        raise RuntimeError("Subbase is not configured. Set SUBBASE_BACKEND and connection env vars (SUBBASE_SQLITE_PATH or SUBBASE_PG_URL).")

    name = os.path.basename(file_path)
    table_map = {
        'users.json': 'users',
        'messages.json': 'messages',
        'submissions.json': 'submissions',
        'ratings.json': 'ratings'
    }
    table = table_map.get(name)
    if not table:
        return

    # For submissions and ratings, keep extra fields in 'meta'
    to_write = []
    for item in data:
        rec = dict(item)
        meta = {}
        if table in ('submissions', 'ratings'):
            # collect fields that are not explicit columns
            explicit = set(['id', 'student_id', 'text', 'ai_fixed_text', 'ai_grade', 'created_at', 'submission_id', 'rating_value', 'feedback_type'])
            for k in list(rec.keys()):
                if k not in explicit:
                    meta[k] = rec.pop(k)
            rec['meta'] = meta
        to_write.append(rec)
    overwrite_table(table, to_write)

def get_next_id(data):
    return max([item["id"] for item in data]) + 1 if data else 1

def init_data_files():
    # This application requires a configured subbase (DB). Do not use JSON files.
    from utils.subbase_adapter import get_conn_from_env, ensure_tables, read_table, append_record
    typ, conn = get_conn_from_env()
    if not conn:
        raise RuntimeError(
            "Subbase is not configured. Set SUBBASE_BACKEND and connection env vars (SUBBASE_SQLITE_PATH or SUBBASE_PG_URL) before starting the app."
        )

    # Ensure DB tables exist
    ensure_tables()

    # Ensure admin user exists; let DB assign id when possible
    users = read_table('users') or []
    if not any(u.get('username') == 'admin' for u in users):
        new_user = {
            'username': 'admin',
            'password_hash': generate_password_hash('admin123'),
            'role': 'admin'
        }
        append_record('users', new_user)


# Try to initialize data immediately so files or DB records exist on startup
try:
    init_data_files()
except Exception:
    # Non-fatal: if initialization fails here, the before_request guard will try again.
    pass

def current_user():
    if "user_id" not in session:
        return None
    users = read_data(USERS_FILE)
    return next((u for u in users if u["id"] == session["user_id"]), None)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        u = current_user()
        if not u or u["role"] != "admin":
            flash("صلاحيات غير كافية")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped

# ====== Rubric definition (Arabic, 100 pts) ======
RUBRIC = [
    {"key": "spelling",      "name": "سلامة الإملاء",                         "max": 12},
    {"key": "grammar",       "name": "سلامة التركيب النحوي وصحة الألفاظ",     "max": 12},
    {"key": "punctuation",   "name": "الدقة في علامات الترقيم",               "max": 8},
    {"key": "clarity",       "name": "وضوح الجمل والأسلوب",                   "max": 10},
    {"key": "vocab",         "name": "ثروة المفردات وحسن اختيار الألفاظ",     "max": 8},
    {"key": "organization",  "name": "تنظيم الأفكار وشمولها",                 "max": 12},
    {"key": "coherence",     "name": "تسلسل الأفكار وترابطها وصلتها بالموضوع","max": 10},
    {"key": "evidence",      "name": "استخدام الأدلة والبراهين/الأمثلة",      "max": 8},
    {"key": "imagery",       "name": "جمال التصوير والتعبير",                 "max": 6},
    {"key": "intro_outro",   "name": "حسن البدء وحسن الختام",                  "max": 6},
    {"key": "relevance",     "name": "الالتزام بموضوع الكتابة",               "max": 8},
]
RUBRIC_TOTAL = sum(item["max"] for item in RUBRIC)

LEVELS = [
    ("ممتاز", 0.85),
    ("جيّد",  0.70),
    ("مقبول", 0.50),
    ("ضعيف",  0.00),
]

def _level_from_ratio(r: float) -> str:
    for name, thr in LEVELS:
        if r >= thr:
            return name
    return "ضعيف"

def _safe_len_tokens(txt: str):
    import re
    tokens = [t for t in re.split(r"\s+", txt.strip()) if t]
    return len(tokens)

def _heuristic_scores_for_text(original_text: str):
    """
    Heuristic scoring used ONLY in fallback mode.
    Very light, language-agnostic approximations to distribute points sensibly.
    """
    import re, math, random
    text = original_text or ""
    n_chars = len(text)
    n_tokens = _safe_len_tokens(text)
    n_commas = text.count("،") + text.count(",")
    n_fullstops = text.count(".") + text.count("؟") + text.count("!")
    n_punct = n_commas + n_fullstops
    n_lines = text.count("\n") + 1
    uniq_tokens = len(set(re.split(r"\s+", text))) if n_tokens else 0

    # Base ratios (0..1) estimated from simple features
    r_length      = min(1.0, n_tokens / 120)             # adequate length
    r_punct       = min(1.0, n_punct / max(1, n_lines*2))
    r_variety     = min(1.0, (uniq_tokens / max(1, n_tokens)) * 1.6)
    r_structure   = min(1.0, n_lines / 4 if n_lines < 4 else 1.0)
    r_intro_outro = 1.0 if re.search(r"(مقدمة|في البداية|ختامًا|في الختام)", text) else 0.6 if n_lines >= 2 else 0.4
    r_evidence    = 1.0 if re.search(r"(مثال|على سبيل المثال|دليل|برهان)", text) else 0.55
    r_relevance   = 0.85  # assume mostly on-topic in fallback

    # Light randomness to avoid identical outputs
    jitter = lambda v, j=0.08: max(0, min(1.0, v + random.uniform(-j, j)))

    ratios = {
        "spelling":     jitter(0.75),             # cannot spell-check offline
        "grammar":      jitter(0.72),
        "punctuation":  jitter(r_punct),
        "clarity":      jitter(0.70 + 0.20 * r_length),
        "vocab":        jitter(r_variety),
        "organization": jitter(0.60 + 0.30 * r_structure),
        "coherence":    jitter(0.60 + 0.35 * r_length),
        "evidence":     jitter(r_evidence),
        "imagery":      jitter(0.55 + 0.25 * r_variety),
        "intro_outro":  jitter(r_intro_outro),
        "relevance":    jitter(r_relevance),
    }

    breakdown = []
    total_points = 0.0
    comments_pool = {
        "spelling": "عامّةً سليمة مع هنات بسيطة غير مؤثرة.",
        "grammar": "تراكيب صحيحة أغلب الوقت، تُراجع بعض الصياغات.",
        "punctuation": "علامات الترقيم مستخدمة في مواضع عديدة.",
        "clarity": "الأسلوب واضح ومباشر في معظم الجمل.",
        "vocab": "مفردات مناسبة وفيها قدر جيّد من التنوع.",
        "organization": "تنظيم جيّد للفقرات وعناصر الفكرة.",
        "coherence": "تسلسل منطقي مقنع بين الأفكار.",
        "evidence": "توجد أمثلة/إشارات تدعيمية على الفكرة.",
        "imagery": "تعابير تصويرية محدودة لكنها مناسبة.",
        "intro_outro": "افتتاح وختام مقبولان يدعمان الفكرة.",
        "relevance": "الطرح بقي ضمن إطار الموضوع.",
    }

    for item in RUBRIC:
        r = max(0.0, min(1.0, ratios[item["key"]]))
        pts = round(item["max"] * r, 2)
        total_points += pts
        breakdown.append({
            "key": item["key"],
            "criterion": item["name"],
            "points_awarded": pts,
            "max_points": item["max"],
            "level": _level_from_ratio(r),
            "comment": comments_pool[item["key"]],
        })

    total_points = round(total_points, 2)
    grade_10 = round((total_points / RUBRIC_TOTAL) * 10.0, 1)
    return breakdown, total_points, grade_10


def fallback_ai_processing(original_text):
    """
    Provides a fallback response if the real AI service fails.
    Now aligned to the Arabic rubric with a full breakdown.
    """
    from flask import flash
    flash("حدث خطأ أثناء الاتصال بالذكاء الاصطناعي. يتم عرض نتيجة احتياطية وفق الروبرك.", "error")

    import random
    # Very light "fix"
    fixed_text = (original_text or "").replace("خطأ", "صحيح").replace("مستيك", "تصحيح")
    fixed_text = fixed_text.strip()
    fixed_text += (" " if fixed_text else "") + " (نُسخة محسّنة تلقائيًا)"

    # Heuristic rubric scoring
    breakdown, total_points, grade_10 = _heuristic_scores_for_text(original_text or "")

    # Mistakes/benefits samples
    mistakes = [
        "تعديل بعض التراكيب لتصبح الجمل أكثر تماسكًا.",
        "تحسين توظيف علامات الترقيم في نهايات الجمل.",
    ]
    benefits = [
        "تسلسل منطقي واضح للأفكار.",
        "اختيار مفردات مناسبة لموضوع الكتابة.",
    ]

    return {
        "fixed_text": fixed_text,
        "ai_grade": grade_10,                    # على 10
        "total_points": total_points,            # على 100
        "rubric_total": RUBRIC_TOTAL,
        "rubric_breakdown": breakdown,          # قائمة تفصيلية لكل معيار
        "mistakes": mistakes,
        "benefits": benefits
    }


def get_ai_analysis(original_text):
    """
    Gets analysis from a real AI model if API_KEY is set,
    otherwise falls back to the local simulator.
    """
    if not API_KEY:
        print("AI_API_KEY not found. Using local simulator.")
        return fallback_ai_processing(original_text)

    # --- REAL AI PROCESSING (ACTIVE) ---
    import json, openai
    client = openai.OpenAI(api_key=API_KEY)

    # Updated system prompt to enforce the rubric JSON
    system_prompt = f"""
أنت مساعد خبير في تقويم الكتابة العربية. قيّم النص وفق الروبرك الآتي، وارجع حصراً "JSON" صالحًا بالمفاتيح المطلوبة.
الروبرك يتكوّن من 11 معيارًا بمجاميع نقاط محددة، والمجموع = {RUBRIC_TOTAL}:
{[{(i+1, item["name"], item["max"])} for i, item in enumerate(RUBRIC)]}

أعد الاستجابة بالصيغة التالية (حقول إجبارية):
- "fixed_text": نسخة مصححة ومحسّنة بالفصحى، مع تصحيح الإملاء والنحو والأسلوب والترقيم.
- "mistakes": قائمة أخطاء محدّدة تم تصحيحها (جُمَل قصيرة واضحة).
- "benefits": نقاط قوة واضحة في النص.
- "ai_grade": درجة على 10 (احسبها = total_points / {RUBRIC_TOTAL} * 10، رقم عشري من منزلة واحدة).
- "total_points": مجموع النقاط المحصّلة على {RUBRIC_TOTAL}.
- "rubric_total": قيمة ثابتة = {RUBRIC_TOTAL}.
- "rubric_breakdown": قائمة من العناصر، كل عنصر كائن بالمفاتيح:
   - "key": مفتاح داخلي (مطابق للقائمة أدناه).
   - "criterion": اسم المعيار بالعربية.
   - "points_awarded": نقاط هذا المعيار (0..max).
   - "max_points": الحد الأعلى لنقاط المعيار.
   - "level": أحد القيم { [lvl for lvl, _ in LEVELS] } بناءً على نسبة النقاط (>=85% ممتاز، >=70% جيّد، >=50% مقبول، وإلا ضعيف).
   - "comment": تعليق بنائي مختصر يبرر النقاط.
المفاتيح المعتمدة لمعايير الروبرك بالتسلسل:
{[item["key"] for item in RUBRIC]}

قواعد حساب النقاط:
- وزّع النقاط واقعيًا وفق الجودة الفعلية للنص في كل معيار.
- احرص على اتساق "ai_grade" مع "total_points".
- لا تُدرج أي نص خارج JSON.
    """.strip()

    try:
        print("Sending request to AI API...")
        response = client.chat.completions.create(
            model="gpt-5-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": original_text}
            ]
        )
        ai_results = json.loads(response.choices[0].message.content)

        # Safety net: if model forgot totals, compute them here
        if "rubric_breakdown" in ai_results and "total_points" not in ai_results:
            total = 0.0
            for row in ai_results["rubric_breakdown"]:
                total += float(row.get("points_awarded", 0))
            ai_results["total_points"] = round(total, 2)
            ai_results["rubric_total"] = RUBRIC_TOTAL
            ai_results["ai_grade"] = round((ai_results["total_points"] / RUBRIC_TOTAL) * 10.0, 1)

        return ai_results
    except Exception as e:
        print(f"An error occurred with the AI API: {e}")
        return fallback_ai_processing(original_text)

@app.route("/")
def index():
    # The first page should be the login page for unauthenticated users.
    if not current_user():
        return redirect(url_for("login"))
    # Authenticated users are sent to topics page as the main entry point.
    return redirect(url_for("topics"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        users = read_data(USERS_FILE)
        user = next((u for u in users if u["username"] == username), None)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            # After login, direct user to the topics page (first in the requested flow)
            return redirect(url_for("topics"))
        else:
            return render_template("login.html", error="بيانات الدخول غير صحيحة")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        if not username or not password:
            return render_template("register.html", error="أدخل اسم المستخدم وكلمة المرور")
        
        users = read_data(USERS_FILE)
        if any(u["username"] == username for u in users):
            return render_template("register.html", error="اسم المستخدم موجود بالفعل")
        
        new_user = {
            "id": get_next_id(users),
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": "student"
        }
        users.append(new_user)
        write_data(USERS_FILE, users)
        # After registration, log the user in and send to topics
        session["user_id"] = new_user["id"]
        return redirect(url_for("topics"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    # Render a dedicated chat/submission page for logged-in users.
    if request.method == 'POST':
        # reuse submit_text logic by delegating to the submit_text endpoint
        return submit_text()
    return render_template('chat.html', user=current_user())


@app.route("/topics")
@login_required
def topics():
    """Page: مواضيع التعبير — shows available prompts or topics and link to learn page."""
    # For now show a simple list of example topics and link to learn page
    example_topics = [
        {"id": 1, "title": "التعليم وأهميته"},
        {"id": 2, "title": "التكنولوجيا وتأثيرها"},
        {"id": 3, "title": "البيئة والحفاظ عليها"},
    ]
    return render_template("topics.html", user=current_user(), topics=example_topics)


@app.route("/learn-with-model")
@login_required
def learn_with_model():
    """Page: تعلم مع النموذج — short description and link to chat page."""
    return render_template("learn.html", user=current_user())

@app.route("/submissions")
@login_required
def submissions_log():
    u = current_user()
    all_submissions = read_data(SUBMISSIONS_FILE)
    user_submissions = sorted(
        [s for s in all_submissions if s["student_id"] == u["id"]],
        key=lambda x: x["created_at"], reverse=True
    )
    return render_template("submissions_log.html", user=u, submissions=user_submissions)

@app.route("/profile")
@login_required
def profile():
    flash("صفحة الملف الشخصي - قيد الإنشاء!")
    return redirect(url_for("index"))

@app.route("/grades")
@login_required
def grades():
    flash("صفحة الدرجات - قيد الإنشاء!")
    return redirect(url_for("submissions_log"))

@app.route("/submit", methods=["POST"])
@login_required
def submit_text():
    u = current_user()
    text = request.form.get("text","").strip()
    if text:
        # Get analysis from AI (or simulator if no API key)
        ai_results = get_ai_analysis(text)

        submissions = read_data(SUBMISSIONS_FILE)
        new_submission = {
            "id": get_next_id(submissions),
            "student_id": u["id"],
            "text": text,
            "grade": None, # Teacher's grade
            "comment": None, # Teacher's comment
            "ai_fixed_text": ai_results.get("fixed_text", "حدث خطأ أثناء معالجة النص."),
            "ai_grade": ai_results.get("ai_grade", 0.0),
            "ai_total_points": ai_results.get("total_points"),
            "ai_rubric_total": ai_results.get("rubric_total"),
            "ai_rubric_breakdown": ai_results.get("rubric_breakdown"),
            "ai_mistakes": ai_results.get("mistakes", ["لم يتمكن الذكاء الاصطناعي من تحديد الأخطاء."]),
            "student_reflection": None, # For student's comment
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        submissions.append(new_submission)
        write_data(SUBMISSIONS_FILE, submissions)
        flash("تم إرسال التعبير. شكراً!")
        session['show_feedback_prompt'] = True # Flag to show feedback prompt
        session['last_submission_id'] = new_submission['id'] # Store submission ID for feedback
        return redirect(url_for("submission_detail", submission_id=new_submission['id']))

@app.route("/submission/<int:submission_id>")
@login_required
def submission_detail(submission_id):
    u = current_user()
    submissions = read_data(SUBMISSIONS_FILE)
    submission = next((s for s in submissions if s["id"] == submission_id), None)

    if not submission:
        flash("التسليم غير موجود.")
        return redirect(url_for("index"))

    # Ensure all new rubric-related keys exist for older submissions
    # This prevents UndefinedError if older submissions lack these keys
    submission.setdefault("ai_total_points", None)
    submission.setdefault("ai_rubric_total", None)
    submission.setdefault("ai_rubric_breakdown", None)
    submission.setdefault("student_reflection", None)
    submission.setdefault("ai_mistakes", []) # Ensure it's a list
    submission.setdefault("ai_fixed_text", "لم يتم توفير نسخة مصححة.")
    submission.setdefault("ai_grade", None)

    # Allow access only to the owner or an admin
    if submission["student_id"] != u["id"] and u["role"] != "admin":
        flash("ليس لديك صلاحية لعرض هذا التسليم.")
        return redirect(url_for("index"))

    # Check if feedback prompt should be shown for this specific submission
    show_feedback_prompt = session.pop('show_feedback_prompt', False) and \
                           session.pop('last_submission_id', None) == submission_id
    
    return render_template(
        "submission_detail.html",
        user=u,
        submission=submission,
        show_feedback_prompt=show_feedback_prompt
    )

@app.route("/submit_reflection", methods=["POST"])
@login_required
def submit_reflection():
    submission_id = request.form.get("submission_id")
    reflection_text = request.form.get("reflection", "").strip()

    if submission_id and reflection_text:
        submissions = read_data(SUBMISSIONS_FILE)
        for sub in submissions:
            if sub["id"] == int(submission_id) and sub["student_id"] == session["user_id"]:
                sub["student_reflection"] = reflection_text
                write_data(SUBMISSIONS_FILE, submissions)
                flash("تم حفظ تعليقك بنجاح.")
                break
    
    return redirect(url_for("submission_detail", submission_id=submission_id))

@app.route("/rate", methods=["POST"])
@login_required
def rate():
    u = current_user()
    submission_id = request.form.get("submission_id")
    feedback_type = request.form.get("feedback_type") # 'helpful' or 'not_helpful'
    
    if submission_id and feedback_type in ['helpful', 'not_helpful']:
        ratings = read_data(RATINGS_FILE)
        sub_id_int = int(submission_id)
        rating_value = 1 if feedback_type == 'helpful' else 0 # 1 for helpful, 0 for not helpful
        new_rating = {
            "id": get_next_id(ratings),
            "student_id": u["id"],
            "submission_id": sub_id_int, # Link rating to submission
            "feedback_type": feedback_type, # Store the type of feedback
            "rating_value": rating_value, # Store a numerical value for analysis
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        ratings.append(new_rating)
        write_data(RATINGS_FILE, ratings)
        flash("تم تسجيل التقييم.")
    else:
        flash("بيانات التقييم غير صالحة.")
    
    # Redirect back to the submission detail page
    return redirect(url_for("submission_detail", submission_id=submission_id))

# --- Admin ---
@app.route("/admin")
@admin_required
def admin_dashboard():
    users = read_data(USERS_FILE)
    messages = read_data(MESSAGES_FILE)
    submissions = read_data(SUBMISSIONS_FILE)
    ratings = read_data(RATINGS_FILE)

    counts = {
        "students": len([u for u in users if u["role"] == "student"]),
        "messages": len(messages),
        "submissions": len(submissions),
        "ratings": len(ratings),
    }

    user_map = {user["id"]: user["username"] for user in users}
    recent_subs = sorted(
        [{**s, "username": user_map.get(s["student_id"])} for s in submissions],
        key=lambda x: x.get("created_at", ""), reverse=True # Use .get for safety
    )
    recent_subs_display = sorted( # Filter out submissions without AI data for now if needed, or ensure simulator always runs
        [s for s in recent_subs if "ai_fixed_text" in s], key=lambda x: x.get("created_at", ""), reverse=True
    )[:10]
    recent_ratings = sorted(
        [{**r, "username": user_map.get(r["student_id"])} for r in ratings],
        key=lambda x: x["created_at"], reverse=True
    )[:10]
    return render_template("admin_dashboard.html", counts=counts, recent_subs=recent_subs, recent_ratings=recent_ratings)

@app.route("/admin/grade", methods=["POST"])
@admin_required
def admin_grade():
    sub_id = request.form.get("submission_id")
    redirect_url = request.form.get("redirect_url", url_for("admin_dashboard"))
    grade = request.form.get("grade", "")
    comment = request.form.get("comment", "")
    if sub_id:
        try:
            # You can expand this to calculate the grade from rubric items
            # e.g., spelling = request.form.get("spelling")
            # For now, we just save the manually entered grade and comment.
            submissions = read_data(SUBMISSIONS_FILE)
            for sub in submissions:
                if sub["id"] == int(sub_id):
                    if grade: # Only update grade if a value was provided
                        try:
                            sub["grade"] = float(grade) # Store as float
                        except ValueError:
                            flash("الدرجة المدخلة ليست رقمًا صالحًا.")
                    sub["comment"] = comment.strip()
                    write_data(SUBMISSIONS_FILE, submissions)
                    flash("تم تحديث التقييم.")
                    break
        except ValueError:
            flash("قيمة الدرجة غير صحيحة.")
    return redirect(redirect_url)

@app.route("/admin/users")
@admin_required
def admin_users():
    users = sorted(read_data(USERS_FILE), key=lambda u: u["username"])
    return render_template("admin_users.html", users=users, current_user_id=session.get("user_id"))


@app.route('/admin/users/import', methods=['GET', 'POST'])
@admin_required
def admin_import_users():
    from werkzeug.utils import secure_filename
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف.')
            return redirect(url_for('admin_users'))
        f = request.files['file']
        if f.filename == '':
            flash('لم يتم اختيار ملف.')
            return redirect(url_for('admin_users'))

        # Parse and import users
        parsed = import_users_from_file_storage(f)
        if not parsed:
            flash('لم يتم العثور على مستخدمين صالحين في الملف.')
            return redirect(url_for('admin_users'))

        users = read_data(USERS_FILE)
        added = 0
        # Use DB append_record for each new user (avoids manual id management)
        from utils.subbase_adapter import append_record
        for pu in parsed:
            if any(u['username'] == pu['username'] for u in users):
                continue
            new_user = {
                'username': pu['username'],
                'password_hash': pu['password_hash'],
                'role': pu.get('role', 'student')
            }
            append_record('users', new_user)
            added += 1

        flash(f'تم استيراد {added} مستخدم(ين).')
        return redirect(url_for('admin_users'))
    # GET -> show the admin users page (which includes the import form)
    return redirect(url_for('admin_users'))

@app.route("/admin/user/add", methods=["GET", "POST"])
@admin_required
def admin_add_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")

        if not username or not password:
            flash("اسم المستخدم وكلمة المرور مطلوبان.")
            return render_template("admin_user_add.html")

        users = read_data(USERS_FILE)
        if any(u["username"] == username for u in users):
            flash("اسم المستخدم موجود بالفعل.")
            return render_template("admin_user_add.html")

        # Use DB append_record to let DB assign id
        new_user = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": role
        }
        from utils.subbase_adapter import append_record
        append_record('users', new_user)
        flash(f"تم إنشاء المستخدم '{username}' بنجاح.")
        return redirect(url_for("admin_users"))
    return render_template("admin_user_add.html")

@app.route("/admin/user/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_user(user_id):
    users = read_data(USERS_FILE)
    user_to_edit = next((u for u in users if u["id"] == user_id), None)

    if user_to_edit is None:
        flash("المستخدم غير موجود.")
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_role = request.form.get("role", "student")

        if not new_username or new_role not in ["admin", "student"]:
            flash("بيانات غير صالحة.")
            return render_template("admin_user_edit.html", user=user_to_edit)
        
        # Check for username uniqueness if it's being changed
        if new_username != user_to_edit["username"] and any(u["username"] == new_username for u in users):
            flash("اسم المستخدم موجود بالفعل.")
            return render_template("admin_user_edit.html", user=user_to_edit)

        for user in users:
            if user["id"] == user_id:
                user["username"] = new_username
                user["role"] = new_role
                break
        write_data(USERS_FILE, users)
        flash("تم تحديث المستخدم بنجاح.")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_edit.html", user=user_to_edit)

@app.route("/admin/user/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    # Note: This is a simple delete. In a real app, you might want to handle user's posts/data.
    users = read_data(USERS_FILE)
    users_to_keep = [u for u in users if u["id"] != user_id]
    write_data(USERS_FILE, users_to_keep)
    flash("تم حذف المستخدم.")
    return redirect(url_for("admin_users"))

@app.route("/admin/export")
@admin_required
def admin_export():
    submissions = read_data(SUBMISSIONS_FILE)
    users = read_data(USERS_FILE)
    user_map = {user["id"]: user["username"] for user in users}

    rows = sorted(submissions, key=lambda x: x["created_at"])
    # Create Excel-compatible CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["SubmissionID","Student","Text","Grade","CreatedAt"])
    for s in rows:
        writer.writerow([s["id"], user_map.get(s["student_id"], ""), s["text"], s.get("grade", ""), s["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="grades_export.csv")

if __name__ == "__main__":
    init_data_files()
    app.run(debug=True)