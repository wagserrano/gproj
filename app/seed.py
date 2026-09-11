"""Seed inicial: cria o schema (se necessário) + área TI + usuário admin.

Uso: python -m app.seed
"""
from sqlalchemy import select

from .auth import hash_senha
from .database import SessionLocal, engine
from .models import Area, Base, Usuario


def main() -> None:
    # 1) Garante o schema antes de qualquer consulta
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2) Idempotente: só popula se o banco estiver vazio
        # if db.scalar(select(Usuario).limit(1)):
        #     print("Seed já aplicado — nada a fazer.")
        #     return

        db.add(Area(nome="Desenvolvimento de Sistemas", sigla="SI-Dev"))
        db.flush()  # resolve o id da área antes do commit

        db.add(Usuario(
            nome="Tejo-Dev-Wagner",
            email="wserrano@tejofran.com.br",
            senha_hash=hash_senha("Boss@1234"),
            papel="admin",
        ))
        db.commit()
        print("Seed aplicado: admin@empresa.com / troque-esta-senha")
    finally:
        db.close()


if __name__ == "__main__":
    main()