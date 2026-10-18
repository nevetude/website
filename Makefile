.PHONY: reset

# Wipes the local database and rebuilds it from the migrations, without asking (the script itself
# refuses a non-local host). Stop the backend first.
reset:
	cd backend && uv run python scripts/reset_db.py --yes
