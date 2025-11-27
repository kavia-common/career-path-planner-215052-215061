# Makefile for backend utilities

# Optional arguments for the seeding script can be passed via:
#   make seed-supabase SEED_ARGS="--dir ../../attachments --verbose"
SEED_ARGS ?=

.PHONY: seed-supabase
seed-supabase:
\tpython3 scripts/seed_supabase.py $(SEED_ARGS)
