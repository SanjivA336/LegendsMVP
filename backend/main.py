from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .firebase import init_firestore
from .routers import characters, context, world, pois, events, quests, combat, worldbible, narrator
from .routers import users, adventures, members, actors, dm_notes
from .routers import entities, status_effects, theme


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Firestore once when the server starts
    init_firestore()
    yield
    # (teardown goes here if ever needed)


app = FastAPI(title="WorldForge Engine", version="0.1.0", lifespan=lifespan)

# Allow the Vite dev server to call the API without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(characters.router)
app.include_router(context.router)
app.include_router(world.router)
app.include_router(pois.router)
app.include_router(events.router)
app.include_router(quests.router)
app.include_router(combat.router)
app.include_router(worldbible.router)
app.include_router(narrator.router)
app.include_router(users.router)
app.include_router(adventures.router)
app.include_router(members.router)
app.include_router(actors.router)
app.include_router(dm_notes.router)
app.include_router(entities.router)
app.include_router(status_effects.router)
app.include_router(theme.router)
