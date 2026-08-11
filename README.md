# CT Setu — Bridge to Thinking

A national Computational Thinking resource platform for Indian school teachers, grades 3–12,
across subjects, boards, and languages.

**Content model:** CT Setu is owner-curated. Anyone can browse and read the Lesson Bank —
that's the point of the site. Only you (the owner) can add, edit, or remove lessons, through a
locked `/admin` page. There is no teacher-upload or peer-review flow.

## What's in this folder

- **`index.html`** — **the main landing page.** A cinematic, scroll-driven Three.js journey
  through the Sun and 8 planets (each mapped to a CT concept), textured with real planet
  photo-maps (see **Planet textures** below), a 3-layer parallax starfield, and a pointer-driven
  look-around effect layered on top of the scroll path. Ends at the gold bridge, a clickable
  "Subject Galaxy," and a CTA into the platform. Open directly in a browser — double-click it,
  no server required. Uses the classic (non-module) Three.js build specifically so it works from
  `file://` without any setup; if a texture URL ever fails to load, it falls back to a stylized
  flat color automatically.
- **`platform.html`** — the public, read-only working platform: Lesson Bank (19 lessons across
  Mathematics, Science, Social Science, English, Hindi, Arts, and Computer Science, grades 3–8),
  a personal Lesson Builder (build/print your own plan — doesn't publish anywhere), Training
  Library, Dashboard, Forum, and DIKSHA integration strip. English/Hindi toggle included. Works
  standalone with embedded sample data, or reads live from the backend if it's running. Reached
  via the "Enter the Platform" button on the landing page, or the CT Setu logo to come back.
- **`admin.html`** (served at `/admin`) — owner-only. Enter your admin key once per session
  (held in memory, never stored) to add, edit, or delete lessons, with an optional cover photo
  upload. Nothing here is reachable without the key.
- **`app.py`** — Flask backend: public read API for the Lesson Bank, admin-key-protected write
  API, photo uploads, training/forum data, and a dashboard endpoint computed from live data.
- **`data/`** — created automatically on first run (`lessons.json`, `forum.json`, `uploads/`).
  Delete it to reset to the seed lesson set.

## Run it the simple way (no backend)

Double-click `index.html` for the cinematic landing page, or open `platform.html` directly for
the reading platform. Browsing, filtering, and the personal Lesson Builder all work with zero
setup. Adding lessons requires the backend — see below.

## Run it with the Python backend (enables admin editing)

```bash
pip install flask
export CT_SETU_ADMIN_KEY="pick-your-own-key"   # skip this and it uses a default — fine for a local demo, not for anything public
python app.py
```

Then visit `http://localhost:5000`:

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/` | public | The cinematic landing page (main entry point) |
| GET | `/platform` | public | The reading platform (Lesson Bank, Builder, Dashboard, Forum) |
| GET | `/admin` | key required to act | Content manager |
| GET | `/api/lessons?subject=&grade=&board=&pillar=` | public | Filtered lesson bank |
| GET | `/api/lessons/<id>` | public | Single lesson detail |
| POST | `/api/admin/lessons` | **admin** | Publish a new lesson |
| PUT | `/api/admin/lessons/<id>` | **admin** | Edit a lesson |
| DELETE | `/api/admin/lessons/<id>` | **admin** | Remove a lesson |
| POST | `/api/admin/uploads` | **admin** | Upload a lesson cover photo (`multipart/form-data`, field `photo`) |
| GET | `/api/training` | public | Training module list |
| GET | `/api/forum` / POST `/api/forum` | public | Forum threads |
| GET | `/api/dashboard` | public | Lessons published, subject spread, CT Readiness Index |

**Try it:** run the server, open `http://localhost:5000/admin`, enter your admin key, add a
lesson — it appears in the Lesson Bank at `http://localhost:5000/platform` immediately, for anyone.

## Planet textures (index.html)

The 3D journey hotlinks real planet photo-textures from an MIT-licensed GitHub project, whose
imagery is ultimately NASA-derived, loaded via the classic (non-module) Three.js build so the
page works from a plain double-click — no server, and no ES-module `file://` restrictions. If
you're deploying this publicly and want zero licensing ambiguity, swap in your own copies from
the original CC BY 4.0 source instead: **solarsystemscope.com/textures** (free to download,
attribution required). Drop the files in an `img/` folder next to `index.html` and update the
`texture:` paths in the `PLANETS` array near the top of the `<script>` block.

## Next steps toward a real pilot

1. Swap `JsonStore` in `app.py` for Postgres/SQLite once beyond a single-district pilot.
2. Move uploaded photos from local disk (`data/uploads/`) to cloud storage (S3/GCS) before
   deploying anywhere beyond your own laptop.
3. Set a strong, unique `CT_SETU_ADMIN_KEY` (and put the whole app behind HTTPS) before it's
   reachable by anyone but you — the current key check is deliberately simple for a pilot.
4. Extend the Hindi translation set in `platform.html`'s `I18N` object to the remaining 21
   scheduled languages, and translate the lesson content itself, not just the UI chrome.
5. Replace the placeholder CT Readiness Index formula in `/api/dashboard` with a validated
   one once real usage data is flowing in from pilot schools.
6. Bring `index.html` and `platform.html` closer visually (they're deliberately two different
   registers — cinematic vs. functional — but a shared header/footer would help), and self-host
   the planet textures per above if you want full control over licensing and load time.
