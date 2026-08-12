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
    def __init__(self, filename, default=None):
        self.path = os.path.join(DATA_DIR, filename)
        self.filename = filename
        self.default = default if default is not None else []
        
        # Create the file with default data if it doesn't exist
        if not os.path.exists(self.path):
            self._write(self.default)
            print(f"Created new {filename} with {len(self.default)} items")

    def _write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def read(self):
        """Read data from the JSON file. Returns empty list if file is empty or corrupted."""
        try:
            with open(self.path, encoding="utf-8") as f:
                content = f.read().strip()
                if not content:  # File is empty
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            # If JSON is corrupted, return empty list
            print(f"Warning: Could not read {self.filename}. Returning empty list.")
            return []

    def write(self, data):
        """Write data to the JSON file."""
        self._write(data)

    def get_lessons(self):
        """Convenience method to get lessons list."""
        data = self.read()
        if isinstance(data, list):
            return data
        return []

    def get_by_id(self, lesson_id):
        """Get a lesson by its ID."""
        lessons = self.get_lessons()
        return next((l for l in lessons if l.get("id") == lesson_id), None)

    def add_lesson(self, lesson):
        """Add a new lesson."""
        lessons = self.get_lessons()
        lessons.append(lesson)
        self.write(lessons)
        return lesson

    def update_lesson(self, lesson_id, updated_data):
        """Update an existing lesson."""
        lessons = self.get_lessons()
        for idx, lesson in enumerate(lessons):
            if lesson.get("id") == lesson_id:
                lessons[idx].update(updated_data)
                self.write(lessons)
                return lessons[idx]
        return None

    def delete_lesson(self, lesson_id):
        """Delete a lesson by its ID."""
        lessons = self.get_lessons()
        remaining = [l for l in lessons if l.get("id") != lesson_id]
        if len(remaining) == len(lessons):
            return False
        self.write(remaining)
        return True


# ---------------------------------------------------------------------------
# Seed data for other stores (forum, training) - we only seed lessons from JSON
# ---------------------------------------------------------------------------
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

# Initialize stores
# lessons_store will read from lessons.json - no seed data provided, 
# so it will start empty if the file doesn't exist
lessons_store = JsonStore("lessons.json", default=[])

# Forum and training stores with seed data
forum_store = JsonStore("forum.json", SEED_FORUM)

# Training data is static for now
TRAINING_DATA = SEED_TRAINING

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
    lessons = lessons_store.get_lessons()
    
    # Filter by query parameters
    for key in ("subject", "grade", "board", "pillar"):
        value = request.args.get(key)
        if value:
            lessons = [l for l in lessons if l.get(key, "").lower() == value.lower()]
    
    # Sort by ID (or title) for consistent ordering
    lessons.sort(key=lambda x: x.get("id", ""))
    
    return jsonify(lessons)


@app.route("/api/lessons/<lesson_id>", methods=["GET"])
def get_lesson(lesson_id):
    lesson = lessons_store.get_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
    return jsonify(lesson)


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

    # Generate a unique ID
    lesson_id = payload.get("id") or f"l{uuid.uuid4().hex[:3]}"
    
    lesson = {
        "id": lesson_id,
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
    
    # Check if lesson with this ID already exists
    existing = lessons_store.get_by_id(lesson_id)
    if existing:
        return jsonify({"error": f"Lesson with ID '{lesson_id}' already exists"}), 409
    
    saved_lesson = lessons_store.add_lesson(lesson)
    return jsonify(saved_lesson), 201


@app.route("/api/admin/lessons/<lesson_id>", methods=["PUT"])
@require_admin
def update_lesson(lesson_id):
    """Owner-only: edit an existing lesson."""
    if not lessons_store.get_by_id(lesson_id):
        return jsonify({"error": "Lesson not found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    if "stages" in payload and (not isinstance(payload["stages"], list) or len(payload["stages"]) != 8):
        return jsonify({"error": "stages must be a list of exactly 8 strings"}), 400

    updated = lessons_store.update_lesson(lesson_id, payload)
    if not updated:
        return jsonify({"error": "Failed to update lesson"}), 500
    
    return jsonify(updated)


@app.route("/api/admin/lessons/<lesson_id>", methods=["DELETE"])
@require_admin
def delete_lesson(lesson_id):
    """Owner-only: remove a lesson from the bank."""
    if not lessons_store.delete_lesson(lesson_id):
        return jsonify({"error": "Lesson not found"}), 404
    
    return jsonify({"message": "Lesson deleted"})


# ---------------------------------------------------------------------------
# Bulk import endpoint - load multiple lessons at once
# ---------------------------------------------------------------------------
@app.route("/api/admin/lessons/bulk", methods=["POST"])
@require_admin
def bulk_import_lessons():
    """Admin-only: import multiple lessons at once."""
    payload = request.get_json(force=True, silent=True) or {}
    
    if not isinstance(payload, list):
        return jsonify({"error": "Expected an array of lessons"}), 400
    
    if len(payload) == 0:
        return jsonify({"error": "No lessons to import"}), 400
    
    imported = []
    errors = []
    
    for idx, lesson_data in enumerate(payload):
        try:
            # Validate required fields
            required = ["subject", "grade", "title", "pillar", "stages"]
            missing = [f for f in required if not lesson_data.get(f)]
            if missing:
                errors.append(f"Lesson {idx}: Missing fields: {', '.join(missing)}")
                continue
            
            if not isinstance(lesson_data["stages"], list) or len(lesson_data["stages"]) != 8:
                errors.append(f"Lesson {idx}: stages must be a list of exactly 8 strings")
                continue
            
            # Generate ID if not provided
            lesson_id = lesson_data.get("id") or f"l{uuid.uuid4().hex[:4]}"
            
            lesson = {
                "id": lesson_id,
                "subject": lesson_data["subject"],
                "grade": lesson_data["grade"],
                "board": lesson_data.get("board", ""),
                "pillar": lesson_data["pillar"],
                "title": lesson_data["title"],
                "desc": lesson_data.get("desc", ""),
                "cover_photo_url": lesson_data.get("cover_photo_url", ""),
                "status": "published",
                "stages": lesson_data["stages"],
            }
            
            # Check if lesson already exists
            existing = lessons_store.get_by_id(lesson_id)
            if existing:
                # Update existing lesson
                lessons_store.update_lesson(lesson_id, lesson)
                imported.append(f"Updated: {lesson_id}")
            else:
                # Add new lesson
                lessons_store.add_lesson(lesson)
                imported.append(f"Added: {lesson_id}")
                
        except Exception as e:
            errors.append(f"Lesson {idx}: {str(e)}")
    
    result = {
        "message": f"Imported {len(imported)} lessons",
        "imported": imported,
        "errors": errors if errors else None,
        "total": len(payload)
    }
    
    if errors:
        result["warning"] = "Some lessons failed to import"
        return jsonify(result), 207  # Multi-status
    
    return jsonify(result), 201


# ---------------------------------------------------------------------------
# Training module API
# ---------------------------------------------------------------------------
@app.route("/api/training", methods=["GET"])
def list_training():
    return jsonify(TRAINING_DATA)


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
    lessons = lessons_store.get_lessons()
    published = [l for l in lessons if l.get("status") == "published"]

    by_subject = {}
    by_grade = {}
    by_pillar = {}
    
    for l in published:
        subject = l.get("subject", "Unknown")
        by_subject[subject] = by_subject.get(subject, 0) + 1
        
        grade = l.get("grade", "Unknown")
        by_grade[grade] = by_grade.get(grade, 0) + 1
        
        pillar = l.get("pillar", "Unknown")
        by_pillar[pillar] = by_pillar.get(pillar, 0) + 1

    # Calculate readiness based on coverage
    subject_spread = len(by_subject)
    grade_spread = len(by_grade)
    pillar_spread = len(by_pillar)
    
    readiness = min(100, len(published) * 3 + subject_spread * 5 + grade_spread * 3 + pillar_spread * 4)

    return jsonify({
        "lessons_published": len(published),
        "total_lessons": len(lessons),
        "subjects_covered": subject_spread,
        "grades_covered": grade_spread,
        "pillars_covered": pillar_spread,
        "lessons_by_subject": by_subject,
        "lessons_by_grade": by_grade,
        "lessons_by_pillar": by_pillar,
        "ct_readiness_index": readiness,
    })


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    lessons_count = len(lessons_store.get_lessons())
    return jsonify({
        "status": "ok",
        "lessons_count": lessons_count,
        "data_directory": DATA_DIR
    })


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CT Setu Backend Server")
    print("="*60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Lessons file: {os.path.join(DATA_DIR, 'lessons.json')}")
    print(f"Current lessons in store: {len(lessons_store.get_lessons())}")
    print("="*60)
    print("\nStarting server at http://localhost:5000")
    print("Admin key: setu-admin-2026 (change this in production!)")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, port=5000)
