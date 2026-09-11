from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth
from .database import engine
from .routers import chamados, kpis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PADRÃO: create_all só para DEV. Em produção, comentar e usar somente
    # `alembic upgrade head` — o Alembic é a fonte de verdade do schema.
    from .models import Base
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Núcleo de Atendimento & Capacitação — API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # front-end; ajuste em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router)        # /auth/token
app.include_router(chamados.router)    # /chamados
app.include_router(kpis.router)        # /dashboard/kpis


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}