"""Autenticação JWT: hash de senha (bcrypt direto) + token + dependências."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario

# ---------- infra de segurança ----------
SECRET_KEY = "troque-por-um-segredo-forte"   # em produção: variável de ambiente
ALGORITHM = "HS256"
TOKEN_HOURS = 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_armazenado.encode())


def criar_token(user: Usuario) -> str:
    payload = {
        "sub": user.email,
        "papel": user.papel,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    cred_exc = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        sub = jwt.decode(token, SECRET_KEY, algorithms=["HS256"]).get("sub")
    except jwt.PyJWTError:
        raise cred_exc
    user = db.scalar(select(Usuario).where(Usuario.email == sub, Usuario.ativo == True))  # noqa: E712
    if not user:
        raise cred_exc
    return user


def exigir(*papeis):
    """Dependência de autorização por papel; admin sempre passa."""
    def dep(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.papel != "admin" and user.papel not in papeis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
        return user
    return dep


# ---------- rotas ----------
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(Usuario).where(Usuario.email == form.username))
    if not user or not verificar_senha(form.password, user.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos")
    if not user.ativo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário inativo")
    user.ultimo_login = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"access_token": criar_token(user), "token_type": "bearer"}