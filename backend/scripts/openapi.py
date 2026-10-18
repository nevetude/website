"""Print the OpenAPI schema; the frontend generates its API types from it (`pnpm gen:api`)."""

import json

from music_backend.main import create_app

print(json.dumps(create_app().openapi()))
