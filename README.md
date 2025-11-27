# career-path-planner-215052-215061

This workspace contains the FastAPI backend, plus a seeding utility to ingest Excel datasets into a Supabase database.

Contents
- career_planner_backend: FastAPI app and scripts
- attachments: Example Excel files used for seeding (provided by the task environment)

Prerequisites
- Python 3.10+ recommended
- A Supabase project with:
  - Tables: roles, competencies, role_competencies, learning_resources, role_adjacency
  - Natural key constraints:
    - roles (unique: role_slug)
    - competencies (unique: competency_slug)
    - role_competencies (unique: (role_id, competency_id))
    - learning_resources (unique: (competency_id, resource_url))
    - role_adjacency (unique: (source_role_id, target_role_id))
  - Service Role key available

Install dependencies
1) Create a virtualenv and install backend requirements:
   cd career-path-planner-215052-215061/career_planner_backend
   pip install -r requirements.txt

2) Copy .env example and set Supabase credentials:
   cp .env.example .env
   Edit .env to set:
     SUPABASE_URL
     SUPABASE_SERVICE_ROLE_KEY

Run the seeding utility
Option A: Using Make (from backend folder)
   cd career-path-planner-215052-215061/career_planner_backend
   make seed-supabase SEED_ARGS="--dir ../../attachments --verbose"

Option B: Directly with Python (from backend folder)
   python scripts/seed_supabase.py --dir ../../attachments -v

Notes
- If you omit --dir and --files, the script searches for a repository-level 'attachments' directory.
- The script reads mapping details from: career_planner_backend/kavia-docs/supabase_schema/columns_mapping.md
- It performs idempotent upserts using on_conflict with the natural keys listed above.

Troubleshooting
- Missing credentials: ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are defined in career_planner_backend/.env
- Schema not found: create tables/constraints per assets/supabase.md (SQL examples provided there).
