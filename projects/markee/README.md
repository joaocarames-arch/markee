# Markee — Trademark Monitoring SaaS

> Monitorização de marcas comerciais, gestão do ciclo de vida e prospeção de oportunidades.

## Stack

- **Backend:** FastAPI + SQLAlchemy + asyncpg + Alembic
- **Database:** PostgreSQL 15 (com pg_trgm)
- **Queue:** Celery + Redis
- **Frontend:** Streamlit (MVP) → React (Fase 2)
- **Infra:** Docker Compose, self-hosted

## Início Rápido

```bash
cp .env.example .env
# editar .env com os teus valores
docker compose up -d db redis
docker compose up app worker beat streamlit
```

## Licença

Proprietária — © 2026 Markee.
