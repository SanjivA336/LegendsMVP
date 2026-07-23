# WorldForge Engine

An AI-powered tabletop RPG engine. A language-model Dungeon Master narrates a persistent, procedurally generated world — you build a character, generate a biome-mapped world, and take turn-based actions that the DM resolves into an evolving story, together with other players and AI-controlled party members.

## Stack

- **Backend**: Python 3.13 + FastAPI (`backend/`), Firestore (Firebase Admin SDK) as the database.
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4 (`frontend/`).
- **Auth**: Firebase Auth (email/password).
- **AI**: Ollama, wrapped behind an `AIProvider` abstraction (`backend/ai_provider.py`) so the model backend can be swapped later.

## Getting started

**Backend**
```
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
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

**Ollama** must be running locally with a model pulled — adventure creation (opening scene, quest generation), in-game narration, skill-check narration, and OOC chat all call it directly.

---

## Current Features

What's actually playable end-to-end today, not just backend-supported:

- **Accounts & Adventures** — email/password sign up/in/out; create, join-by-invite-code, and delete adventures; a four-tier role model (owner/admin/player/viewer) enforced on every backend request (`backend/routers/members.py`, `backend/routers/adventures.py`). Only invite-join and delete are exposed in the UI today — promoting/demoting members and transferring ownership are fully built and tested at the API level but have no frontend yet (see Next Up).
- **Adventure Creation Wizard** — a 15-step, non-linear flow (`frontend/src/pages/wizard/`, driven by `wizardData.ts`) that, via one continuous real API sequence at the final Launch step (not mock data — nothing persists before then), procedurally generates a biome/elevation world map, seeds points of interest, lets you write a world bible (optionally AI-expanded from a one-line pitch via `/theme/expand`), author custom Templates and Instances (races, classes, weapons, wearables, consumables — see Entity System below), generate an opening quest, and — for AI-DM adventures — build your character (fields, stat roll, equip loadout, starting inventory) before generating the opening scene. Human-DM adventures skip the character-building sub-steps.
- **Entity System (Templates & Instances)** — a generic content model (`backend/models/blueprint.py`, `backend/routers/entities.py`) that replaced the old hardcoded Item/Character models. A `Template` (e.g. "Rusty Sword") defines a `Kind` (`character`/`race`/`class`/`weapon`/`consumable`/`wearable`/`custom`) with typed `CustomField`s; `Instance`s are specific copies that sparsely override those fields. This is what lets a DM author custom content per-adventure without code changes, and it's fully wired: the wizard's Template/Instance editors (`frontend/src/components/blueprint/`) and the in-game `CharacterCreationModal` (reachable from any empty party slot) both create real entities through it.
- **Core Gameplay Loop** — the heart of the app, fully working: every round, all human players and AI-controlled "Actor" party members submit an action (or pass); once everyone's in, the DM decides whether any action needs a skill check, auto-rolls for AI actors, presents an interactive dice-roll minigame to human players who need one, then narrates the combined outcome of the round in a single response — optionally introducing NPCs who speak and/or act. Multiple human players in the same adventure see each other's actions and the round resolution live via polling (`backend/routers/narrator.py`, `frontend/src/hooks/useNarrator.ts`). Skill-check outcomes are resolved and narrated directly (there is currently no separate tactical battle-map for this — see Roadmap).
- **Party & AI Party Members ("Actors")** — a real party roster with live HP bars, plus reusable, adjustable AI-controlled party members (stance/tactics/disposition axes) who act automatically each round.
- **World Map (viewing)** — the generated map, biome/elevation view toggle, mini-map, and POI markers are fully viewable with a tile-info panel. You currently can only *view* the map — there's no way to move around it yet (see Next Up).
- **Quest Display** — an opening quest is generated with your adventure and its step progress is shown in a live tracker. Nothing in the current gameplay loop advances a quest past its first step yet — see Next Up.
- **DM Notes** — admin/owner-writable shared campaign notes that the DM references when answering out-of-character questions.
- **OOC Chat** — ask the DM questions without affecting the story. Messages are currently local to your own browser session only, not shared with other players in the adventure (see Next Up).
- **Preferences & Theming** — a custom accent color and per-player colors, applied live across the whole UI (party panel, action log, chat, turn order) via CSS custom properties — no rebuild needed.
- **Relationship Graph (viewing)** — a "Cast" view shows an NPC relationship web (affinity/fear/submission), viewable read-only today.
- **Character Sheets, Creation & Starting Inventory** — stats, HP, description, and inventory display for your own character, plus a full 4-step creation flow (`CharacterCreationModal`, reachable from any empty party slot) for adding a new character with custom fields, an equip loadout, and starting inventory picked from existing Instances. There's still no way to acquire, equip, or use items *during* play — this only covers character creation (see Next Up).

---

## Next Up

Concrete, comparatively contained gaps — the backend is fully or mostly built for each of these; what's missing is wiring and/or a UI. Ranked roughly by how much they block the core experience.

1. **Player → character self-assignment.** Now very close: `CharacterCreationModal` is a real, working 4-step creation flow reachable by any adventure member, and `LaunchStep.tsx` proves the pattern (it calls `updateMember` to link the adventure creator's own character). But `CharacterCreationModal`'s `handleCreate` never makes that same `updateMember` call — so today it's a general "add a character to the roster" tool, not yet a "claim this as *my* character" flow for joining players. Closing this gap looks like one added API call plus knowing which member record is "mine," not a new flow from scratch.
2. **Member management UI.** `PATCH`/`DELETE` on members and the ownership-transfer endpoint (`backend/routers/members.py`) are fully built and tested, but there's no frontend for promoting, demoting, removing a member, or transferring ownership.
3. **Wire quest advancement into the gameplay loop.** The quest state machine — chaining middle steps, completion, failure, and DM-generated recovery steps when a quest is at risk of dead-ending — is complete and correct in `backend/utils/quest_state.py`. But nothing in `narrator.py`'s round resolution ever calls `dispatch_event` or the advance-step functions, so a quest can currently be created and displayed but never actually progresses through real play.
4. **World map travel.** `frontend/src/components/world/WorldMapModal.tsx` already computes a full journey plan (path, encounter estimate, POI stops along the route) — but its "Start Journey" button has no click handler, and `gameStore.setCurrentTile()` is never called anywhere in the app. A player's map position is set once at spawn and never changes.
5. **POI entry.** Dungeons, settlements, and ruins have real, fairly sophisticated procedural generation (`backend/routers/pois.py` — rooms, floors, exits, boss rooms, sub-structures) but no "Enter" UI anywhere; today they only render as colored map markers.
6. **A real way to acquire items during play.** Equip/starting-inventory selection now works at character-creation time (see above), but nothing adds items to inventory afterward — the only loot path runs through the (currently unreachable) tactical combat system.
7. **Adventure details editing UI + invite-code regeneration UI.** Both `PATCH /adventures/{id}` and the invite-regeneration endpoint exist and are tested; nothing in the UI calls either.
8. **Context-card management UI.** Cards can be authored during the wizard but have no post-creation edit/add screen.
9. **Status effect authoring UI.** `backend/routers/status_effects.py` and `models/status_effect.py` are a complete CRUD system for defining effects (damage/heal over time, temporary stat/damage deltas) — but there's zero frontend code referencing it anywhere. Backend-only today.

---

## Tentative Roadmap

Bigger, more open-ended pieces — things worth a real design pass rather than a quick wire-up.

- **Decide the future of tactical combat.** A full tactical grid system exists end-to-end on the backend (LLM-generated arenas, turn order, move/attack/loot, NPC AI, hazards/cover) but is entirely unreachable from the shipped app — nothing ever triggers `startCombat`, so `combatActive` stays permanently false. Before investing more here, worth deciding whether to wire up the existing grid as-is or move toward a more direct, animated click-to-move experience.
- **Items & economy.** Entity Templates/Instances now carry a universal `value` field, but there's still no shop, trading, or crafting *system* built on top of it — value is just a number sitting on the data model today.
- **Fog of war / progressive map discovery.** The whole map is visible from the moment it's generated; there's no discovered/undiscovered concept in the data model yet.
- **Shared, persisted OOC chat + presence.** OOC messages are local-only per browser session today; there's also no "who's online" indicator anywhere.
- **Real-time sync beyond polling.** The current live-sync mechanism is plain polling (2–10s backoff); a websocket layer would be the natural next step once concurrent-player load justifies it.
- **Relationship ripple wired into real gameplay triggers.** The ripple mechanic (`POST /relationships/ripple`) is fully implemented but never fired by narration, combat, or quest outcomes — today it's viewable only if manually seeded via the API.
- **Dungeon/settlement/ruin exploration as a real experience**, not just generation — walking through generated rooms, not just entering and reading a summary.
- **More minigame types, eventually player-authored ones.** The skill-check system is already a pluggable minigame framework (`frontend/src/minigames/registry.ts`) with only dice-roll implemented — a timed maze or similar is a natural next plugin, with player-authored minigames as a longer-term stretch goal.
- **Encounter lifecycle & OOC-as-context.** Encounters never auto-start/end at story beats, and OOC chat doesn't yet feed into action-resolution context.
- **Faction map view mode** — currently a disabled "Coming soon" button in the World Map modal.
