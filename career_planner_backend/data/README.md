Place generated JSON files here to seed the catalog on startup or via CLI.

Expected file names (all optional; missing files are skipped with a warning):
- roles.json                  # [{ "id"?: int, "code": str, "name": str, "summary"?: str }, ...]
- competencies.json           # [{ "id"?: int, "code": str, "name": str, "category"?: str }, ...]
- role_adjacency.json         # [{ "from_role_id": int, "to_role_id": int, "weight": number }, ...]
- role_competencies.json      # [{ "role_id": int, "competency_id": int, "required_level": int }, ...]
- users.json                  # [{ "name": str, "email": str }, ...]   (simple users table for /db/users)
- plans.json                  # [{ "user_id": str, "title": str, "target_role_id"?: int }, ...]
- goals.json                  # [{ "plan_id": int, "description": str, "status"?: str }, ...]

Notes:
- Seeding is idempotent. Running the app multiple times will not duplicate rows.
- Unique keys used:
  * roles: code
  * competencies: code
  * role_adjacency: (from_role_id, to_role_id)
  * role_competencies: (role_id, competency_id)
  * users(simple): email
  * plans: (user_id, title)
  * goals: (plan_id, description)
- DATABASE_URL must be set for seeding to operate; otherwise seeding is skipped.
- To run the full seeder: `python -m src.seed_full_cli`
