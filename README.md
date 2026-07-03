# WorldForge Engine

An AI-powered tabletop RPG engine. A language-model Dungeon Master narrates a persistent, procedurally generated world — you build a character, explore a hand-tunable biome map, and take actions that the DM resolves into an evolving story.

## Stack

- **Backend**: Python 3.13 + FastAPI (`backend/`), Firestore (Firebase Admin SDK) as the database.
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4 (`frontend/`).
- **Auth**: Firebase Auth (email/password).
- **AI**: Ollama, wrapped behind an `AIProvider` abstraction (`backend/utils/ai_provider.py`) so the model backend can be swapped later.

## Getting started

**Backend**
```
cd backend
# .venv already contains fastapi, uvicorn, firebase-admin, pydantic, python-dotenv
# (no requirements.txt exists yet -- see Known Gaps)
../.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```
Requires a `.env` at the repo root with:
```
FIREBASE_KEY_PATH="C:\path\to\firebase-adminsdk-key.json"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

**Frontend**
```
cd frontend
npm install
npm run dev
```
Requires `frontend/.env.local` with `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_STORAGE_BUCKET`, `VITE_FIREBASE_MESSAGING_SENDER_ID`, `VITE_FIREBASE_APP_ID`.

**Ollama** must be running locally with a model pulled — adventure creation (opening scene, quest generation) and in-game narration and OOC chat all call it directly.

## What's implemented

**Auth & Users** — Email/password sign up, sign in, sign out. Reachable directly from the marketing landing page and from the navbar. Backend verifies Firebase ID tokens on every request (`backend/utils/auth.py`).

**Layout architecture** — Four route-level layout shells (`frontend/src/components/layout/`):
- `MarketingLayout` — no navbar, public. Wraps the landing page.
- `AuthLayout` — no navbar, deliberately separate visual treatment. Wraps login/signup.
- `MenuLayout` — has the navbar (brand, sign-out, Adventures/Preferences/Profile links). Wraps Adventures, adventure creation, Profile, Preferences — all behind `ProtectedRoute`.
- `GameplayLayout` — no navbar. Wraps the in-game 3-column play view, also protected.

**Adventures & Ownership** — Full CRUD, invite-code join, and a four-role permission model (owner/admin/player/viewer). Owner-only: delete adventure, transfer ownership. Admin+: everything else (edit adventure details, add/promote/demote/remove non-owner members, regenerate invite code). Ownership transfer is atomic (single Firestore batch swaps both roles). The Adventures list has an Owned/Member/All filter. **Member management and ownership transfer are fully built and tested at the API level but have no frontend UI yet** — see Known Gaps.

**Actors** — User-level AI party members, reusable across adventures, with adjustable stance/tactics/disposition axes.

**World / Map / POIs** — Procedural map generation (elevation, water, biomes) with a per-adventure biome palette/naming editor in the creation wizard. POIs (dungeons, settlements, encampments, ruins) are seeded deterministically from the map and discovered as you explore. **Dungeon/settlement/ruin interiors generate lazily and procedurally on the backend but have no exploration frontend yet** — see Known Gaps.

**Quests & Events** — LLM-generated opening quests with multi-step arcs; world events drive quest progression.

**Combat** — Full tactical arena system: encounters, LLM-generated arenas, player/NPC turns, AI-driven NPC decisions, hazards and cover.

**DM Notes** — Admin-writable, viewer-readable per-adventure notes surfaced to the DM's narration.

**AI Narrator / OOC Chat** — Opening scene generation, the main narrate-and-resolve action loop, and a separate out-of-character chat channel for asking the DM questions without affecting the story.

**Items / Characters / Context** — Item templates and instances, character sheets with inventory/equipment, prompt-injection "context cards," a running world-state fact log, and an NPC relationship graph that ripples affinity changes through the social web.

**Per-user Preferences** — A `preferences` object on the user record (`backend/models/user.py`), currently covering:
- A custom accent color, applied at runtime via CSS custom properties (`--color-accent`, `--accent`, and their hover variants) so the whole UI repaints live without a rebuild — see `AuthContext.tsx`'s theming effect.
- Custom colors for the 4 player slots, applied globally across all your adventures via a `usePlayerColors()` hook that every color-coded UI element (party panel, action log, combat tokens, chat, cast list, turn order) reads from instead of a hardcoded constant.

Every preference field is optional and nullable (`null` = use the app default) so new preferences can be added later without any data migration — see the schema note in `backend/models/user.py`.

## Known gaps / planned next steps

Roughly in priority order:

1. **Member management UI** — `PATCH`/`DELETE` on members and the ownership-transfer endpoint are all built and tested, but there's no frontend for promoting, demoting, removing a member, or transferring ownership. Right now those actions are only reachable via direct API calls.
2. **Self-service character selection** — there's currently no way for a player (below admin) to link themselves to their own character; that requires an admin/owner to do it on their behalf via the API. The original adventure-creation wizard sidesteps this by keeping the "which character is mine" link entirely client-side (never persisted server-side), which also means it doesn't survive a fresh browser/device. Worth a real design pass rather than a quick patch.
3. **Adventure details editing UI** — `PATCH /adventures/{id}` (rename, change world name) exists and is tested, but nothing in the UI calls it.
4. **Dungeon / settlement / ruin exploration frontend** — the single largest gap between what the backend supports and what's playable today. The procedural generation is all there; there's no in-game surface to walk through it.
5. **Quest step manual resolution UI** — quest progression currently happens implicitly through gameplay events; there's no UI to manually resolve or fail a step.
6. **Context-card authoring UI** — context cards can be created during adventure setup but have no post-creation management screen.
7. **A `requirements.txt`/`pyproject.toml`** for the backend — dependencies currently live only in the local `.venv` with no manifest.

## Architecture notes worth knowing

- **Permission matrix**: owner-only = delete adventure, transfer ownership. Admin+ = everything else. Enforced in `backend/routers/members.py` and `backend/routers/adventures.py`; loosened from an earlier, stricter owner-only model this session.
- **Preferences forward-compatibility**: every field on `UserPreferences` must stay `Optional[...] = None`. Firestore is schemaless, so an old user document simply won't have a newer field's key, and Pydantic fills in the declared default automatically on read — no backfill scripts, ever, as long as this convention holds.
- **Self-update guards in `update_member`**: the checks that block changing your own role, or changing the owner's role, are scoped specifically to `payload.role is not None` — they must not block unrelated fields like `character_id`. This was a real bug found and fixed during verification (the guards were blocking *any* self-update, not just role changes).
