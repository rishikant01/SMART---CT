"""
CT Setu — Flask backend
========================
A lightweight reference backend for the CT Setu platform.

Run it with:
    pip install flask
    python app.py

Then open http://localhost:5000

Content model: CT Setu is owner-curated. Anyone can browse and read the
Lesson Bank; only the site owner (you) can add, edit, or remove lessons,
via the locked /admin page and the admin-only API below.

    GET    /                        -> the cinematic 3D landing page (main entry point)
    GET    /platform                -> the functional reading platform (Lesson Bank etc.)
    GET    /admin                   -> owner-only content manager (needs the admin key)
    GET    /api/lessons             -> list lessons, filter with ?subject=&grade=&board=&pillar=
    GET    /api/lessons/<id>        -> single lesson detail
    POST   /api/admin/lessons       -> [admin] publish a new lesson
    PUT    /api/admin/lessons/<id>  -> [admin] edit a lesson
    DELETE /api/admin/lessons/<id>  -> [admin] remove a lesson
    POST   /api/admin/uploads       -> [admin] upload a cover/reference photo for a lesson
    GET    /api/training            -> training module list
    GET    /api/forum               -> forum threads
    POST   /api/forum               -> create a forum thread
    GET    /api/dashboard           -> aggregated stats (lessons published, readiness index)

Data is stored in data/lessons.json / data/forum.json, so it survives restarts
without needing a database. Swap the JsonStore class for a real DB
(Postgres/SQLite) when moving past a pilot.

ADMIN KEY: set the CT_SETU_ADMIN_KEY environment variable before running in
anything but a local demo. If unset, a default key is used and a warning is
printed at startup — change this before deploying anywhere reachable by
anyone but you.
"""

import json
import os
import uuid
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

ADMIN_KEY = os.environ.get("CT_SETU_ADMIN_KEY", "setu-admin-2026")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def require_admin(fn):
    """Gate a route behind the X-Admin-Key header. Owner-only content model:
    reading the Lesson Bank is public, writing to it is not."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Admin-Key") != ADMIN_KEY:
            return jsonify({"error": "Invalid or missing admin key"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Tiny JSON-file data store (swap for a real DB later)
# ---------------------------------------------------------------------------
class JsonStore:
    def __init__(self, filename, default):
        self.path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(self.path):
            self._write(default)

    def _write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def read(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def write(self, data):
        self._write(data)


def _lesson(id, subject, grade, board, pillar, title, desc, stages):
    return {
        "id": id, "subject": subject, "grade": grade, "board": board, "pillar": pillar,
        "title": title, "desc": desc, "status": "published", "stages": stages,
    }


SEED_LESSONS = [
    _lesson("l1", "Mathematics", "Grade 6", "CBSE", "Pattern Recognition", "Sharing Rotis Fairly",
        "Students split rotis among friends to discover how fractions are just a pattern of fair division.", [
            "Four friends, three rotis. How does everyone get an equal share?",
            "Students physically cut paper 'rotis' and distribute pieces among groups of 2, 3, 4 and 5 friends.",
            "Groups compare how they cut — some cut all pieces the same size, some didn't. Why does that matter?",
            "Students notice: same-size pieces + same number per person = fair share, regardless of group size.",
            "Predict: how would you cut 5 rotis for 4 friends?",
            "Discuss why the size of each piece depends on both the number of rotis and the number of people.",
            "Write one line: what does the fraction 3/4 actually mean in this activity?",
            "Connect to real-world: recipe scaling, and how apps split delivery bills fairly.",
        ]),
    _lesson("l2", "Science", "Grade 8", "State Board", "Decomposition", "Breaking Down a Leaf's Factory",
        "Students decompose photosynthesis into its separate inputs, processes and outputs.", [
            "How does a leaf 'make its own food' with no kitchen and no shop?",
            "Students draw a leaf and label everything going in and out of it that they can think of.",
            "Groups compare lists — what's missing, what's repeated, what can be grouped together?",
            "Students notice every living process can be split into Inputs → Process → Outputs.",
            "Predict: what happens to the outputs if one input (light) is removed?",
            "Discuss why decomposing photosynthesis into parts makes each part easier to test.",
            "Which part of the process did you find hardest to isolate, and why?",
            "Connect to real-world: engineers decompose machines into small testable parts the same way.",
        ]),
    _lesson("l3", "Social Science", "Grade 7", "CBSE", "Algorithm Design", "Mapping the Spice Route",
        "Students design a step-by-step trade route across historical ports, then compare it to real trade algorithms.", [
            "How did traders decide the order to visit ports, given winds, seasons and goods?",
            "Students sequence port cards on a map to build the shortest safe seasonal route.",
            "Groups justify their order — why this port before that one?",
            "Students notice good routes repeat a pattern: cluster nearby ports, then jump.",
            "Predict: what happens to the route if the monsoon season shifts by two months?",
            "Discuss why traders needed a fixed procedure they could repeat every year.",
            "What was one decision rule your group used without realizing it was a rule?",
            "Connect to real-world: GPS apps and delivery services design step-by-step routes the same way.",
        ]),
    _lesson("l4", "English", "Grade 5", "ICSE", "Pattern Recognition", "Sorting Time Words",
        "Students sort verbs by tense to discover the underlying rule pattern of English grammar.", [
            "How do we know if a sentence is about yesterday, today, or tomorrow from one word?",
            "Students sort a pile of verb cards into three baskets: past, present, future.",
            "Groups check each other's baskets — any disagreements? Why?",
            "Students notice most past-tense verbs share an '-ed' pattern, with some exceptions.",
            "Predict which basket a brand-new invented verb would land in, and why.",
            "Discuss why English has exceptions, and how a 'pattern with exceptions' is still useful.",
            "Which verb was hardest to sort, and what made it tricky?",
            "Connect to real-world: spell-checkers and grammar apps use the same pattern-matching idea.",
        ]),
    _lesson("l5", "Arts", "Grade 4", "State Board", "Abstraction", "Rangoli Rules",
        "Students abstract a rangoli design into a repeatable rule so anyone could recreate it without seeing the original.", [
            "Could you describe a rangoli over the phone so someone draws the exact same one?",
            "Students draw a simple rangoli, then write instructions for a partner to recreate it, sight unseen.",
            "Partners compare the original and the copy — what got lost in translation?",
            "Students notice the best instructions ignored small details and kept only the core repeating rule.",
            "Predict what a rangoli would look like if the core rule was repeated 12 times instead of 6.",
            "Discuss why leaving out unnecessary detail made the instructions easier to follow, not harder.",
            "What's one detail you first included that turned out not to matter?",
            "Connect to real-world: phone icons are abstractions too — simplified pictures that tell you what an app does.",
        ]),
    _lesson("l6", "Mathematics", "Grade 3", "CBSE", "Pattern Recognition", "Reading the Rangoli Row",
        "Students identify repeating bead and tile patterns, then create their own rule-based sequences.", [
            "Can you tell what comes next in a row of colored beads just by looking at what came before?",
            "Students string colored beads (or draw tiles) following a repeating rule, then swap rows with a partner.",
            "Groups explain the rule behind their partner's row before checking if they guessed right.",
            "Students notice a pattern is really just a short rule that repeats, no matter how long the row gets.",
            "Predict bead number 15 in a row that repeats every 3 beads, without counting each one.",
            "Discuss why knowing the repeat-length lets you skip ahead instead of counting one by one.",
            "What's one pattern rule you noticed outside class today — on a sari, a gate, a floor tile?",
            "Connect to real-world: traffic light sequences and phone lock patterns both repeat by a fixed rule too.",
        ]),
    _lesson("l7", "Mathematics", "Grade 7", "State Board", "Algorithm Design", "The Number Line Board Game",
        "Students build a board game where forward/backward moves represent integers, then write scoring rules.", [
            "How do you keep score in a game where you can move both forward and backward?",
            "Students build a number-line board game and write a fixed set of movement rules (algorithm) for scoring gains and losses.",
            "Groups trade rule sets and play each other's games — do the rules ever contradict themselves?",
            "Students notice every 'backward' move behaves the same way regardless of which number you start from.",
            "Predict your position after three forward moves of +4 and two backward moves of -6.",
            "Discuss why a consistent rule set (an algorithm) is what makes the game fair to play twice.",
            "Which of your original rules did you have to rewrite because it broke the game?",
            "Connect to real-world: bank statements and elevator buttons use the same forward/backward integer logic.",
        ]),
    _lesson("l8", "Mathematics", "Grade 8", "ICSE", "Decomposition", "Balancing the Scale",
        "Students represent equations as balance scales, decomposing them into small reversible operations.", [
            "How do you find an unknown weight using only a balance scale and known weights?",
            "Students use a drawn balance-scale model to solve for x, removing or adding the same weight to both sides each step.",
            "Groups compare their step order — did everyone decompose the equation the same way?",
            "Students notice every solved equation breaks into the same small, reversible moves repeated in some order.",
            "Predict how many steps a new, longer equation will take before you solve it.",
            "Discuss why doing the same operation to both sides keeps the scale — and the equation — balanced.",
            "Which single step, if skipped, would have tipped your answer off balance?",
            "Connect to real-world: spreadsheet formulas solve for an unknown cell using the exact same step-by-step balancing.",
        ]),
    _lesson("l9", "Science", "Grade 4", "CBSE", "Pattern Recognition", "Watching a Seed Keep Its Promise",
        "Students track plant growth under different conditions to identify and predict growth patterns.", [
            "Does a seed grow the same way every time, or does it depend on where you put it?",
            "Students plant seeds in different conditions (sun/shade, more/less water) and record height every day for a week.",
            "Groups compare growth charts — whose seedling grew fastest, and under which condition?",
            "Students notice the sunlit, watered seedlings follow a similar day-by-day growth pattern.",
            "Predict how tall the seedling will be in 3 more days if the pattern continues.",
            "Discuss why comparing conditions, not just one plant, is what reveals the real pattern.",
            "What surprised you about how your prediction compared to what actually happened?",
            "Connect to real-world: farmers and weather apps both use past growth patterns to predict future harvests.",
        ]),
    _lesson("l10", "Science", "Grade 6", "State Board", "Decomposition", "Pulling One Card Out of the Web",
        "Students build a food web, remove one organism, and trace the cascading effects.", [
            "What happens to an entire ecosystem if just one animal disappears from it?",
            "Students build a food web with string connecting organism cards, then physically remove one card and watch which connections go slack.",
            "Groups discuss which removed card caused the most collapsed connections, and why.",
            "Students notice organisms near the base of the web affect more connections than ones near the top.",
            "Predict what happens to the rest of the web if you remove the primary producer instead of a top predator.",
            "Discuss how breaking the web into individual links (decomposition) makes a messy ecosystem easier to reason about.",
            "Which single organism did you assume was unimportant, until you traced its connections?",
            "Connect to real-world: engineers decompose power grids the same way to find which single failure would cause the biggest blackout.",
        ]),
    _lesson("l11", "Social Science", "Grade 6", "CBSE", "Algorithm Design", "Shortest Path to the Well",
        "Students design step-by-step routes between landmarks, introducing pathfinding.", [
            "If you had to walk between three landmarks on a map, what order would get you there fastest?",
            "Students mark landmarks on a hand-drawn map and write a step-by-step route (algorithm) between them, then measure the distance.",
            "Groups compare routes for the same landmarks — did everyone find the same shortest path?",
            "Students notice routes that visit the nearest unvisited landmark first tend to come out shorter.",
            "Predict which route will be shortest before measuring a new set of landmarks.",
            "Discuss why writing the route as a fixed set of steps lets a friend follow it without redoing your thinking.",
            "What was one landmark order you were sure was shortest, but measured longer?",
            "Connect to real-world: GPS apps solve this same shortest-path problem for millions of roads at once.",
        ]),
    _lesson("l12", "Social Science", "Grade 8", "ICSE", "Pattern Recognition", "Counting the Class Election",
        "Students simulate an election and analyze voting patterns and fairness.", [
            "How do you turn a room full of different opinions into one fair decision?",
            "Students run a simulated class election with candidates and secret ballots, then tally and chart the results.",
            "Groups discuss what the vote spread tells them about who felt strongly versus who was undecided.",
            "Students notice patterns in how votes cluster — by seating group, by prior friendships, or evenly spread.",
            "Predict how the result might change if one candidate dropped out before the vote.",
            "Discuss why counting every vote the same way, every time, is what makes the count trustworthy.",
            "Did the result match what you expected walking in — why or why not?",
            "Connect to real-world: real election commissions and opinion-poll models look for the same voting patterns at national scale.",
        ]),
    _lesson("l13", "English", "Grade 4", "State Board", "Algorithm Design", "Unscrambling the Sentence",
        "Students rearrange shuffled word cards using grammatical rules.", [
            "Given a pile of shuffled words, how do you know which order makes them a real sentence?",
            "Students receive word cards in random order and physically arrange them into a grammatically correct sentence.",
            "Groups compare their sentence order and explain the rule they used to decide word placement.",
            "Students notice subject usually comes before verb, and verb before object, across most of their sentences.",
            "Predict where a new word card belongs in the sentence before placing it.",
            "Discuss why following the same word-order rule every time makes a sentence make sense to any reader.",
            "Which word was hardest to place, and what rule finally told you where it belonged?",
            "Connect to real-world: grammar-check tools in typing apps follow the same word-order rules to flag broken sentences.",
        ]),
    _lesson("l14", "English", "Grade 6", "CBSE", "Decomposition", "Taking a Story Apart Before Writing One",
        "Students decompose stories into character, setting, conflict, climax, and resolution before writing.", [
            "Before writing a story, how do you make sure it actually has a beginning, middle, and end?",
            "Students take a familiar story and break it into labeled cards: character, setting, conflict, climax, resolution.",
            "Groups compare which part of the story was hardest to separate out from the others.",
            "Students notice every story they decompose, no matter the genre, breaks into the same five parts.",
            "Predict what a story would feel like missing if you wrote it without a clear conflict.",
            "Discuss why planning each part separately (decomposition) makes writing the whole story less overwhelming.",
            "Which part did you write first when you tried it yourself, and why?",
            "Connect to real-world: movie scripts and even AI story generators are built by planning these same story parts separately.",
        ]),
    _lesson("l15", "English", "Grade 8", "ICSE", "Pattern Recognition", "Building a Sentence Decision Tree",
        "Students classify sentences using rule-based decision trees.", [
            "How can you quickly tell whether a sentence is a question, a command, or a statement?",
            "Students sort a mixed pile of sentences by asking a fixed sequence of yes/no questions (a decision tree).",
            "Groups compare which sentences were tricky to classify, and where their decision trees disagreed.",
            "Students notice punctuation and word order both give away the sentence type before you even read the meaning.",
            "Predict how a brand-new sentence will be classified using only the decision tree, before reading it fully.",
            "Discuss why a fixed set of yes/no questions can sort any sentence, no matter the topic.",
            "What's one sentence type your decision tree got wrong the first time, and why?",
            "Connect to real-world: voice assistants use a similar decision tree to tell a question from a command.",
        ]),
    _lesson("l16", "Hindi", "Grade 5", "State Board", "Pattern Recognition", "मुहावरों का समूह (Grouping Idioms)",
        "Students group idioms by meaning to uncover language patterns.", [
            "How can you guess the meaning of a muhavara (idiom) you've never heard before?",
            "Students sort a set of idiom cards into groups by the feeling or situation each one describes.",
            "Groups defend why they placed a tricky idiom in one category instead of another.",
            "Students notice idioms about fear, idioms about anger, and idioms about surprise each share a common shape.",
            "Predict which category a brand-new idiom belongs to just from its keywords.",
            "Discuss why grouping by meaning, not just by the words used, is what makes the categorization actually useful.",
            "Which idiom's real meaning surprised you the most compared to its literal words?",
            "Connect to real-world: translation apps struggle most with idioms for exactly this reason — the words don't mean what they literally say.",
        ]),
    _lesson("l17", "Computer Science", "Grade 6", "CBSE", "Decomposition", "Storyboarding Before Scripting",
        "Students decompose an animation into scenes, sprites, costumes, and events before building it in Scratch.", [
            "Before opening Scratch, how do you plan an animation so you're not guessing as you build it?",
            "Students storyboard a short animation on paper, breaking it into scenes, characters (sprites), costumes, and triggering events.",
            "Groups walk another team through their storyboard before either group touches a computer.",
            "Students notice every scene follows the same shape: something happens, a sprite responds, the scene changes.",
            "Predict how many separate scripts your animation will need before you count them on the storyboard.",
            "Discuss why planning scenes and sprites separately (decomposition) makes the actual Scratch building faster, not slower.",
            "What part of your storyboard did you change once you saw it running in Scratch?",
            "Connect to real-world: film and game studios storyboard for the exact same reason before writing any code.",
        ]),
    _lesson("l18", "Computer Science", "Grade 7", "State Board", "Algorithm Design", "Flowcharting the Rules of Play",
        "Students design game logic with flowcharts before building loops and conditions in Scratch.", [
            "How does a game decide, instantly, whether you've won, lost, or should keep playing?",
            "Students flowchart their game's rules — loops, conditions, and events — before building it in Scratch.",
            "Groups trace a partner's flowchart by hand, playing out what the game would do on a sample turn.",
            "Students notice every working game rule follows the same shape: check a condition, then loop or branch.",
            "Predict what your game will do in an edge case (e.g., score exactly zero) before testing it.",
            "Discuss why writing the algorithm as a flowchart first catches bugs before they're even coded.",
            "Which rule in your flowchart turned out to be missing a condition once you actually played the game?",
            "Connect to real-world: traffic signals and elevators run on the same loop-and-condition logic as your game.",
        ]),
    _lesson("l19", "Computer Science", "Grade 8", "ICSE", "Pattern Recognition", "Teaching a Human to Sort Like AI",
        "Students hand-classify objects using a rule they write, then compare it to how simple AI models work.", [
            "Could you write down a simple rule that sorts your classmates' bags into 'school bag' or 'sports bag' without seeing the label?",
            "Students collect simple data (size, shape, straps) on classroom objects and manually classify them using a rule they write themselves.",
            "Groups test their rule on a new object and discuss where it got the classification wrong.",
            "Students notice their rule is really just a pattern found in the data — the same thing a simple AI model does.",
            "Predict how a new, unusual object will be classified by your rule before testing it.",
            "Discuss why a rule that works on training examples can still fail on a new object it hasn't seen before.",
            "Where did your own 'AI rule' behave differently than how you personally would judge the object?",
            "Connect to real-world: this is exactly how simple AI classifiers work — they find a pattern in labeled examples, then apply it to new ones.",
        ]),
]

SEED_TRAINING = [
    {"stage": 1, "title": "Running Stage 1: Problem in 4 minutes", "duration_min": 4},
    {"stage": 2, "title": "Turning any Activity into evidence", "duration_min": 5},
    {"stage": 3, "title": "Facilitating Discussion without losing time", "duration_min": 4},
    {"stage": 4, "title": "Spotting Pattern Recognition moments", "duration_min": 5},
    {"stage": 5, "title": "Getting real Predictions, not guesses", "duration_min": 3},
    {"stage": 6, "title": "Reasoning: the 'why' behind the pattern", "duration_min": 5},
    {"stage": 7, "title": "Closing with real Reflection", "duration_min": 4},
    {"stage": 8, "title": "Making the AI / Real-World link stick", "duration_min": 5},
]

SEED_FORUM = [
    {"id": "f1", "title": "My Grade 4s got stuck at Stage 6 — Reasoning", "subject": "Mathematics · Grade 4", "replies": 14},
    {"id": "f2", "title": "How long should Stage 2 (Activity) really take?", "subject": "General", "replies": 22},
    {"id": "f3", "title": "Any Hindi-medium version of the Rangoli lesson?", "subject": "Arts · Grade 4", "replies": 6},
    {"id": "f4", "title": "Used the Spice Route lesson for Grade 9 instead — worked!", "subject": "Social Science", "replies": 9},
]

lessons_store = JsonStore("lessons.json", SEED_LESSONS)
forum_store = JsonStore("forum.json", SEED_FORUM)

if ADMIN_KEY == "setu-admin-2026":
    print("\n*** CT Setu: using the DEFAULT admin key ('setu-admin-2026'). ***")
    print("*** Set CT_SETU_ADMIN_KEY before deploying anywhere but your own laptop. ***\n")


# ---------------------------------------------------------------------------
# Static site
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """The cinematic 3D landing page — this is the main entry point."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/platform")
@app.route("/platform.html")
def platform():
    """The functional reading platform: Lesson Bank, Builder, Dashboard, Forum."""
    return send_from_directory(BASE_DIR, "platform.html")


@app.route("/admin")
def admin_page():
    return send_from_directory(BASE_DIR, "admin.html")


# ---------------------------------------------------------------------------
# Photo uploads (admin only — used for a lesson's cover/reference photo)
# ---------------------------------------------------------------------------
def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/admin/uploads", methods=["POST"])
@require_admin
def upload_photo():
    if "photo" not in request.files:
        return jsonify({"error": "No file field named 'photo' in the request"}), 400
    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "Only png, jpg, jpeg, or webp images are allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(safe_name)
    file.save(os.path.join(UPLOAD_DIR, safe_name))
    return jsonify({"url": f"/uploads/{safe_name}"}), 201


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------------------------------------------------------------------
# Lesson Bank API — reading is public, writing is admin-only
# ---------------------------------------------------------------------------
@app.route("/api/lessons", methods=["GET"])
def list_lessons():
    lessons = lessons_store.read()
    for key in ("subject", "grade", "board", "pillar"):
        value = request.args.get(key)
        if value:
            lessons = [l for l in lessons if l.get(key, "").lower() == value.lower()]
    return jsonify(lessons)


@app.route("/api/lessons/<lesson_id>", methods=["GET"])
def get_lesson(lesson_id):
    lessons = lessons_store.read()
    match = next((l for l in lessons if l["id"] == lesson_id), None)
    if not match:
        return jsonify({"error": "Lesson not found"}), 404
    return jsonify(match)


@app.route("/api/admin/lessons", methods=["POST"])
@require_admin
def create_lesson():
    """Owner-only: publish a new lesson directly to the Lesson Bank."""
    payload = request.get_json(force=True, silent=True) or {}
    required = ["subject", "grade", "title", "pillar", "stages"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if not isinstance(payload["stages"], list) or len(payload["stages"]) != 8:
        return jsonify({"error": "stages must be a list of exactly 8 strings"}), 400

    lesson = {
        "id": uuid.uuid4().hex[:8],
        "subject": payload["subject"],
        "grade": payload["grade"],
        "board": payload.get("board", ""),
        "pillar": payload["pillar"],
        "title": payload["title"],
        "desc": payload.get("desc", ""),
        "cover_photo_url": payload.get("cover_photo_url", ""),
        "status": "published",
        "stages": payload["stages"],
    }
    lessons = lessons_store.read()
    lessons.append(lesson)
    lessons_store.write(lessons)
    return jsonify(lesson), 201


@app.route("/api/admin/lessons/<lesson_id>", methods=["PUT"])
@require_admin
def update_lesson(lesson_id):
    """Owner-only: edit an existing lesson."""
    lessons = lessons_store.read()
    match = next((l for l in lessons if l["id"] == lesson_id), None)
    if not match:
        return jsonify({"error": "Lesson not found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    if "stages" in payload and (not isinstance(payload["stages"], list) or len(payload["stages"]) != 8):
        return jsonify({"error": "stages must be a list of exactly 8 strings"}), 400

    for field in ("subject", "grade", "board", "pillar", "title", "desc", "cover_photo_url", "stages"):
        if field in payload:
            match[field] = payload[field]

    lessons_store.write(lessons)
    return jsonify(match)


@app.route("/api/admin/lessons/<lesson_id>", methods=["DELETE"])
@require_admin
def delete_lesson(lesson_id):
    """Owner-only: remove a lesson from the bank."""
    lessons = lessons_store.read()
    remaining = [l for l in lessons if l["id"] != lesson_id]
    if len(remaining) == len(lessons):
        return jsonify({"error": "Lesson not found"}), 404
    lessons_store.write(remaining)
    return jsonify({"message": "Lesson deleted"})


# ---------------------------------------------------------------------------
# Training module API
# ---------------------------------------------------------------------------
@app.route("/api/training", methods=["GET"])
def list_training():
    return jsonify(SEED_TRAINING)


# ---------------------------------------------------------------------------
# Forum API
# ---------------------------------------------------------------------------
@app.route("/api/forum", methods=["GET"])
def list_forum():
    return jsonify(forum_store.read())


@app.route("/api/forum", methods=["POST"])
def create_forum_thread():
    payload = request.get_json(force=True, silent=True) or {}
    if not payload.get("title"):
        return jsonify({"error": "title is required"}), 400
    thread = {
        "id": str(uuid.uuid4())[:8],
        "title": payload["title"],
        "subject": payload.get("subject", "General"),
        "replies": 0,
    }
    threads = forum_store.read()
    threads.insert(0, thread)
    forum_store.write(threads)
    return jsonify(thread), 201


# ---------------------------------------------------------------------------
# Dashboard API — aggregates lesson bank into simple stats
# ---------------------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    lessons = lessons_store.read()
    published = [l for l in lessons if l.get("status") == "published"]

    by_subject = {}
    for l in published:
        by_subject[l["subject"]] = by_subject.get(l["subject"], 0) + 1

    ratings = [l["rating"] for l in published if l.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0

    # A simple, transparent readiness formula for a pilot: lessons published
    # and how many subjects/grades they cover. Replace with a validated
    # formula once real usage data is flowing in from pilot schools.
    subject_spread = len(by_subject)
    readiness = min(100, len(published) * 4 + subject_spread * 5)

    return jsonify({
        "lessons_published": len(published),
        "subjects_covered": subject_spread,
        "avg_lesson_rating": avg_rating or None,
        "lessons_by_subject": by_subject,
        "ct_readiness_index": readiness,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
