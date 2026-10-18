# music-backend

The API and the Genius importer of the Music app. See the [root README](../README.md) for how to run it.

```
src/music_backend/
  api/       FastAPI routers, schemas and the SQL pieces they share
  imports/   one handler per Genius entity, the task runner and the job manager
  models/    SQLAlchemy models (the Alembic migrations are in `migrations/`)
```
