# Columns Mapping for Excel → Supabase

This document defines the mapping between incoming Excel files and Supabase tables.
The seeding script reads the YAML block below to understand which sheets and columns to parse.

Notes:
- This is a flexible mapping: if a candidate column is missing, the seeder will try the next candidate.
- Slugs are generated from names if not provided.
- Level text is mapped to numbers: Novice=1, Intermediate=2, Advanced=3, Authority=4 (plus synonyms).

```yaml
version: 1
files:
  competency_mapping:
    filename_contains: ["Competency_mapping", "Competency mapping"]
    sheets:
      - name: "Competencies"
        table: "competencies"
        columns:
          competency_slug: ["Competency_Slug", "competency_slug", "Slug", "Competency"]
          name: ["Name", "Competency", "Competency Name"]
          category: ["Category", "Family"]
          description: ["Description", "Notes", "Summary"]
      - name: "Learning_Resources"
        table: "learning_resources"
        columns:
          competency_slug: ["Competency_Slug", "Competency Slug", "Competency"]
          resource_title: ["Title", "Resource", "Resource Title", "Name"]
          resource_url: ["URL", "Link"]
          provider: ["Provider", "Source"]
          difficulty: ["Difficulty", "Level"]
    natural_keys:
      competencies: "competency_slug"
      learning_resources: ["competency_id", "resource_url"]

  role_navigator_worksheet:
    filename_contains: ["Role_Navigator", "Role Navigator Worksheet", "Role_Navigator_Worksheet"]
    sheets:
      - name: "Roles"
        table: "roles"
        columns:
          role_slug: ["Role_Slug", "role_slug", "Role", "Role Name", "Title"]
          role_name: ["Role Name", "Role", "Title", "Name"]
          category: ["Category", "Group", "Family"]
          description: ["Description", "Summary"]
    role_competencies:
      sheet_name: "Role_Competencies"
      columns:
        role_slug: ["Role Slug", "Role", "Role_Slug"]
        competency_slug: ["Competency Slug", "Competency", "Competency_Slug"]
        level_required: ["Level Required", "Level", "Required Level"]
      level_map:
        novice: 1
        intermediate: 2
        advanced: 3
        authority: 4
    natural_keys:
      roles: "role_slug"
      role_competencies: ["role_id", "competency_id"]

  role_adjacency:
    filename_contains: ["Role_Adjacency", "Adjacency"]
    sheets:
      - name: "Role_Adjacency"
        table: "role_adjacency"
        columns:
          source_role_slug: ["From Role", "Source Role", "role_slug_from", "source_role_slug", "From"]
          target_role_slug: ["To Role", "Target Role", "role_slug_to", "target_role_slug", "To"]
          weight: ["Weight", "Adjacency Weight", "Score"]
    natural_keys:
      role_adjacency: ["source_role_id", "target_role_id"]
```
