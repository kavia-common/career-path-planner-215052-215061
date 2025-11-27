#!/usr/bin/env python3
"""
Seed Supabase from Excel files (idempotent upsert using service role key).

This script:
- Loads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from environment (via .env).
- Reads Excel files supplied via CLI args or from a default attachments directory.
- Parses sheets/columns per kavia-docs/supabase_schema/columns_mapping.md (YAML block).
- Upserts into tables: roles, competencies, role_competencies (level_required),
  learning_resources, role_adjacency (weight) using natural keys with on_conflict.
- Logs summary counts for each table and is idempotent.

Usage examples:
  python scripts/seed_supabase.py
  python scripts/seed_supabase.py --dir ../../attachments
  python scripts/seed_supabase.py --files ../../attachments/20251127_054842_Role_Navigator_Worksheet.xlsx ../../attachments/20251127_054851_Competency_mapping.xlsx
  python scripts/seed_supabase.py --dry-run

Requirements:
  - pandas, openpyxl, httpx, python-dotenv, pyyaml (already pinned in requirements.txt or added)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import httpx
import pandas as pd
import typer
import yaml
from dotenv import load_dotenv

app = typer.Typer(add_completion=False, no_args_is_help=False)


# -------------------------------
# Utilities
# -------------------------------

def _normalize_col_name(col: str) -> str:
    """Normalize DataFrame column name for matching across variants."""
    return re.sub(r"[^a-z0-9]+", "", col.strip().lower())


def _slugify(value: str) -> str:
    """Create a simple slug from an arbitrary string."""
    value = value.strip().lower()
    # Replace non-alphanumeric with hyphens
    value = re.sub(r"[^a-z0-9]+", "-", value)
    # Trim hyphens
    value = value.strip("-")
    return value


def _coerce_str(x: Any) -> Optional[str]:
    """Return stripped string or None."""
    if x is None:
        return None
    s = str(x).strip()
    return s or None


def _find_repo_root(start: Path) -> Path:
    """Walk upward to find repository root (folder containing 'attachments' or '.git' or workspace root)."""
    cur = start.resolve()
    for _ in range(6):
        if (cur / "attachments").exists() or (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _find_default_attachments_dir(start: Path) -> Optional[Path]:
    """Search upwards for 'attachments' directory from starting path."""
    cur = start.resolve()
    for _ in range(6):
        att = cur / "attachments"
        if att.exists() and att.is_dir():
            return att
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _extract_yaml_from_markdown(md_text: str) -> Dict[str, Any]:
    """Extract the first YAML code block from a Markdown string."""
    match = re.search(r"```yaml(.*?)```", md_text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("No YAML code block found in columns_mapping.md")
    yaml_text = match.group(1)
    data = yaml.safe_load(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML in columns_mapping.md must define a mapping at the top level.")
    return data


# -------------------------------
# PostgREST client (Supabase REST)
# -------------------------------

class PostgrestError(RuntimeError):
    """Raised on PostgREST error responses."""


@dataclass
class SupabaseRest:
    """Thin wrapper over Supabase PostgREST (httpx) for upserts and selects."""
    supabase_url: str
    service_key: str
    timeout: float = 30.0

    def __post_init__(self) -> None:
        base = self.supabase_url.rstrip("/")
        self.rest_url = f"{base}/rest/v1"
        self._client = httpx.Client(timeout=self.timeout)
        self._default_headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise PostgrestError(f"PostgREST error {resp.status_code}: {detail}")

    def _build_in_filter(self, column: str, values: Sequence[str]) -> Tuple[str, str]:
        """Build an in.(...) filter; quotes values to be safe."""
        def q(v: str) -> str:
            v = v.replace('"', '\\"')
            return f'"{v}"'
        val = ",".join(q(v) for v in values)
        return column, f"in.({val})"

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Mapping[str, Tuple[str, Any]]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a select with optional filters and return rows."""
        url = f"{self.rest_url}/{table}"
        params: Dict[str, Any] = {"select": columns}
        headers = dict(self._default_headers)
        headers["Prefer"] = "count=exact"
        if filters:
            for col, (op, val) in filters.items():
                if op == "eq":
                    params[col] = f"eq.{val}"
                elif op == "in":
                    k, v = self._build_in_filter(col, list(val or []))
                    params[k] = v
                else:
                    raise ValueError(f"Unsupported filter op: {op}")
        if limit is not None:
            params["limit"] = str(limit)
        resp = self._client.get(url, headers=headers, params=params)
        self._raise_for_status(resp)
        try:
            return resp.json()
        except Exception as e:
            raise PostgrestError(f"Invalid JSON in select response: {e}")

    def upsert(
        self,
        table: str,
        rows: Sequence[Mapping[str, Any]],
        on_conflict: str,
        chunk_size: int = 500,
    ) -> List[Dict[str, Any]]:
        """Bulk upsert rows into a table using on_conflict natural keys."""
        if not rows:
            return []
        url = f"{self.rest_url}/{table}"
        all_rows: List[Dict[str, Any]] = []
        headers = dict(self._default_headers)
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"

        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            params = {"on_conflict": on_conflict}
            resp = self._client.post(url, headers=headers, params=params, content=json.dumps(chunk))
            self._raise_for_status(resp)
            try:
                returned = resp.json()
                if isinstance(returned, list):
                    all_rows.extend(returned)
            except Exception:
                # Some installations might not return JSON for empty sets; ignore
                pass
        return all_rows


# -------------------------------
# Mapping and parsing
# -------------------------------

@dataclass
class ColumnsMapping:
    """Holds the parsed columns mapping specification."""
    raw: Dict[str, Any]

    @classmethod
    def load_from_file(cls, path: Path) -> "ColumnsMapping":
        with path.open("r", encoding="utf-8") as f:
            data = _extract_yaml_from_markdown(f.read())
        return cls(raw=data)

    def find_profile_for_file(self, filename: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Return (profile_key, profile_data) matched by filename_contains."""
        files = self.raw.get("files", {})
        for key, profile in files.items():
            contains: List[str] = profile.get("filename_contains", [])
            if not contains:
                continue
            name_l = filename.lower()
            if any(token.lower() in name_l for token in contains):
                return key, profile
        return None


def _rename_columns(df: pd.DataFrame, mapping: Dict[str, List[str]]) -> pd.DataFrame:
    """Rename DataFrame columns to canonical names based on mapping candidates."""
    norm_map: Dict[str, str] = {}
    canon_to_found: Dict[str, str] = {}

    # Build reverse lookup from normalized col name to original
    current_cols_norm = {_normalize_col_name(c): c for c in df.columns}

    for canonical, candidates in mapping.items():
        for cand in candidates:
            norm = _normalize_col_name(cand)
            if norm in current_cols_norm:
                canon_to_found[canonical] = current_cols_norm[norm]
                break

    # Build final rename dict
    for canonical, found in canon_to_found.items():
        norm_map[found] = canonical

    return df.rename(columns=norm_map)


# -------------------------------
# Seeding logic
# -------------------------------

LEVEL_MAP_TEXT_TO_NUM = {
    "novice": 1,
    "beginner": 1,
    "basic": 1,
    "intermediate": 2,
    "mid": 2,
    "medium": 2,
    "advanced": 3,
    "expert": 3,
    "authority": 4,
    "lead": 4,
    "principal": 4,
}


@dataclass
class SeedSummary:
    roles: int = 0
    competencies: int = 0
    role_competencies: int = 0
    learning_resources: int = 0
    role_adjacency: int = 0


class Seeder:
    """Reads Excel files and upserts into Supabase tables via REST."""

    def __init__(self, client: SupabaseRest, mapping: ColumnsMapping, dry_run: bool = False) -> None:
        self.client = client
        self.mapping = mapping
        self.dry_run = dry_run
        self.logger = logging.getLogger("seeder")

        # Aggregated rows
        self._roles: List[Dict[str, Any]] = []
        self._competencies: List[Dict[str, Any]] = []
        self._role_competencies: List[Dict[str, Any]] = []
        self._learning_resources: List[Dict[str, Any]] = []
        self._role_adjacency: List[Dict[str, Any]] = []

    def _ensure_role_slug(self, row: Dict[str, Any]) -> Dict[str, Any]:
        slug = row.get("role_slug")
        name = row.get("role_name") or row.get("name") or row.get("title")
        if not slug and name:
            slug = _slugify(str(name))
        if slug:
            row["role_slug"] = slug
        return row

    def _ensure_competency_slug(self, row: Dict[str, Any]) -> Dict[str, Any]:
        slug = row.get("competency_slug")
        name = row.get("name") or row.get("competency") or row.get("competency_name")
        if not slug and name:
            slug = _slugify(str(name))
        if slug:
            row["competency_slug"] = slug
        return row

    def _to_int_level(self, val: Any) -> Optional[int]:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            try:
                return int(val)
            except Exception:
                pass
        s = str(val).strip().lower()
        return LEVEL_MAP_TEXT_TO_NUM.get(s)

    def _dedup_by_keys(self, rows: List[Dict[str, Any]], keys: Sequence[str]) -> List[Dict[str, Any]]:
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for r in rows:
            k = tuple(r.get(k) for k in keys)
            if k not in seen:
                seen.add(k)
                deduped.append(r)
        return deduped

    def _parse_file(self, file_path: Path) -> None:
        """Parse a single Excel file based on profile mapping."""
        prof_found = self.mapping.find_profile_for_file(file_path.name)
        if not prof_found:
            self.logger.warning(f"Skipping file (no mapping profile matched): {file_path}")
            return

        profile_key, profile = prof_found
        self.logger.info(f"Parsing '{file_path.name}' using profile '{profile_key}'")

        # Parse generic sheets->tables first
        for sheet_spec in profile.get("sheets", []):
            sheet_name = sheet_spec.get("name")
            table = sheet_spec.get("table")
            columns: Dict[str, List[str]] = sheet_spec.get("columns", {})
            if not sheet_name or not table:
                continue
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
            except Exception as e:
                self.logger.warning(f"  Sheet '{sheet_name}' not found in {file_path.name}: {e}")
                continue

            df = _rename_columns(df, columns)

            rows = df.replace({pd.NA: None}).to_dict(orient="records")

            if table == "roles":
                for r in rows:
                    r = {k: _coerce_str(v) if isinstance(v, str) or v is None else v for k, v in r.items()}
                    r = self._ensure_role_slug(r)
                    if r.get("role_slug"):
                        self._roles.append(
                            {
                                "role_slug": r.get("role_slug"),
                                "role_name": r.get("role_name") or r.get("name") or r.get("title") or r.get("role_slug"),
                                "category": r.get("category"),
                                "description": r.get("description"),
                            }
                        )
            elif table == "competencies":
                for r in rows:
                    r = {k: _coerce_str(v) if isinstance(v, str) or v is None else v for k, v in r.items()}
                    r = self._ensure_competency_slug(r)
                    if r.get("competency_slug"):
                        self._competencies.append(
                            {
                                "competency_slug": r.get("competency_slug"),
                                "name": r.get("name") or r.get("competency") or r.get("competency_name") or r.get("competency_slug"),
                                "category": r.get("category"),
                                "description": r.get("description"),
                            }
                        )
            elif table == "learning_resources":
                for r in rows:
                    r = {k: _coerce_str(v) if isinstance(v, str) or v is None else v for k, v in r.items()}
                    # Keep competency_slug for now; will resolve to competency_id later
                    if r.get("competency_slug") and (r.get("resource_title") or r.get("resource_url")):
                        self._learning_resources.append(
                            {
                                "competency_slug": r.get("competency_slug"),
                                "resource_title": r.get("resource_title") or r.get("title") or "",
                                "resource_url": r.get("resource_url"),
                                "provider": r.get("provider"),
                                "difficulty": r.get("difficulty"),
                            }
                        )
            elif table == "role_adjacency":
                for r in rows:
                    r = {k: _coerce_str(v) if isinstance(v, str) or v is None else v for k, v in r.items()}
                    src = r.get("source_role_slug") or r.get("from_role_slug") or r.get("from_role")
                    tgt = r.get("target_role_slug") or r.get("to_role_slug") or r.get("to_role")
                    if not src or not tgt:
                        continue
                    try:
                        weight = float(r.get("weight")) if r.get("weight") is not None else None
                    except Exception:
                        weight = None
                    self._role_adjacency.append(
                        {
                            "source_role_slug": _slugify(src),
                            "target_role_slug": _slugify(tgt),
                            "weight": weight,
                        }
                    )

        # Parse role_competencies if present in profile
        rc_spec = profile.get("role_competencies")
        if rc_spec:
            sheet_name = rc_spec.get("sheet_name")
            columns: Dict[str, List[str]] = rc_spec.get("columns", {})
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
                df = _rename_columns(df, columns)
                rows = df.replace({pd.NA: None}).to_dict(orient="records")
                for r in rows:
                    r = {k: _coerce_str(v) if isinstance(v, str) or v is None else v for k, v in r.items()}
                    if not r.get("role_slug") or not r.get("competency_slug"):
                        continue
                    level = self._to_int_level(r.get("level_required"))
                    self._role_competencies.append(
                        {
                            "role_slug": _slugify(r["role_slug"]),
                            "competency_slug": _slugify(r["competency_slug"]),
                            "level_required": level,
                        }
                    )
            except Exception as e:
                self.logger.warning(f"  Role competencies sheet '{sheet_name}' not found in {file_path.name}: {e}")

    def _fetch_id_map(self, table: str, slug_field: str, slugs: Sequence[str]) -> Dict[str, str]:
        """Return mapping from slug -> id for given table."""
        ids: Dict[str, str] = {}
        if not slugs:
            return ids
        unique_slugs = sorted(set(slugs))
        # Chunk to avoid URL too long
        for i in range(0, len(unique_slugs), 500):
            chunk = unique_slugs[i : i + 500]
            rows = self.client.select(
                table=table,
                columns=f"id,{slug_field}",
                filters={slug_field: ("in", chunk)},
            )
            for r in rows:
                ids[r[slug_field]] = r["id"]
        return ids

    def _ensure_missing_roles(self, slugs: Sequence[str]) -> None:
        """Ensure roles exist for given slugs (minimal rows for adjacency)."""
        if not slugs:
            return
        existing = self._fetch_id_map("roles", "role_slug", slugs)
        to_create = [s for s in slugs if s not in existing]
        if not to_create:
            return
        rows = [{"role_slug": s, "role_name": s.replace("-", " ").title()} for s in to_create]
        self.logger.info(f"Ensuring {len(rows)} missing roles exist (from adjacency references).")
        if not self.dry_run:
            self.client.upsert("roles", rows, on_conflict="role_slug")

    def parse_files(self, files: Sequence[Path]) -> None:
        """Parse all files and aggregate rows for seeding."""
        for fp in files:
            try:
                self._parse_file(fp)
            except Exception as e:
                self.logger.exception(f"Failed parsing file {fp}: {e}")

        # Deduplicate aggregated rows by natural keys
        self._roles = self._dedup_by_keys(self._roles, ["role_slug"])
        self._competencies = self._dedup_by_keys(self._competencies, ["competency_slug"])
        self._learning_resources = self._dedup_by_keys(self._learning_resources, ["competency_slug", "resource_url"])
        self._role_adjacency = self._dedup_by_keys(self._role_adjacency, ["source_role_slug", "target_role_slug"])
        self._role_competencies = self._dedup_by_keys(self._role_competencies, ["role_slug", "competency_slug"])

    def seed(self) -> SeedSummary:
        """Perform upserts into Supabase tables in dependency order."""
        summary = SeedSummary()

        # First, ensure minimal roles for adjacency references
        adjacency_role_slugs = [r["source_role_slug"] for r in self._role_adjacency] + [
            r["target_role_slug"] for r in self._role_adjacency
        ]
        self._ensure_missing_roles(adjacency_role_slugs)

        # Upsert roles
        if self._roles:
            self.logger.info(f"Upserting roles: {len(self._roles)} rows (on_conflict=role_slug)")
            summary.roles = len(self._roles)
            if not self.dry_run:
                self.client.upsert("roles", self._roles, on_conflict="role_slug")
        else:
            self.logger.info("No roles to upsert.")

        # Upsert competencies
        if self._competencies:
            self.logger.info(f"Upserting competencies: {len(self._competencies)} rows (on_conflict=competency_slug)")
            summary.competencies = len(self._competencies)
            if not self.dry_run:
                self.client.upsert("competencies", self._competencies, on_conflict="competency_slug")
        else:
            self.logger.info("No competencies to upsert.")

        # Fetch id maps for FK tables
        role_slug_to_id = self._fetch_id_map("roles", "role_slug", [r["role_slug"] for r in self._roles] + adjacency_role_slugs)
        comp_slug_to_id = self._fetch_id_map("competencies", "competency_slug", [c["competency_slug"] for c in self._competencies])

        # Upsert learning_resources
        lr_rows: List[Dict[str, Any]] = []
        for r in self._learning_resources:
            cid = comp_slug_to_id.get(r["competency_slug"])
            if not cid:
                continue
            lr_rows.append(
                {
                    "competency_id": cid,
                    "resource_title": r.get("resource_title"),
                    "resource_url": r.get("resource_url"),
                    "provider": r.get("provider"),
                    "difficulty": r.get("difficulty"),
                }
            )
        if lr_rows:
            self.logger.info(f"Upserting learning_resources: {len(lr_rows)} rows (on_conflict=competency_id,resource_url)")
            summary.learning_resources = len(lr_rows)
            if not self.dry_run:
                self.client.upsert("learning_resources", lr_rows, on_conflict="competency_id,resource_url")
        else:
            self.logger.info("No learning_resources to upsert.")

        # Upsert role_competencies
        rc_rows: List[Dict[str, Any]] = []
        for r in self._role_competencies:
            rid = role_slug_to_id.get(r["role_slug"])
            cid = comp_slug_to_id.get(r["competency_slug"])
            if not rid or not cid:
                continue
            rc_rows.append(
                {
                    "role_id": rid,
                    "competency_id": cid,
                    "level_required": r.get("level_required"),
                }
            )
        if rc_rows:
            self.logger.info(f"Upserting role_competencies: {len(rc_rows)} rows (on_conflict=role_id,competency_id)")
            summary.role_competencies = len(rc_rows)
            if not self.dry_run:
                self.client.upsert("role_competencies", rc_rows, on_conflict="role_id,competency_id")
        else:
            self.logger.info("No role_competencies to upsert.")

        # Upsert role_adjacency
        adj_rows: List[Dict[str, Any]] = []
        for r in self._role_adjacency:
            sid = role_slug_to_id.get(r["source_role_slug"])
            tid = role_slug_to_id.get(r["target_role_slug"])
            if not sid or not tid:
                continue
            adj_rows.append(
                {
                    "source_role_id": sid,
                    "target_role_id": tid,
                    "weight": r.get("weight"),
                }
            )
        if adj_rows:
            self.logger.info(f"Upserting role_adjacency: {len(adj_rows)} rows (on_conflict=source_role_id,target_role_id)")
            summary.role_adjacency = len(adj_rows)
            if not self.dry_run:
                self.client.upsert("role_adjacency", adj_rows, on_conflict="source_role_id,target_role_id")
        else:
            self.logger.info("No role_adjacency to upsert.")

        return summary


# -------------------------------
# CLI
# -------------------------------

def _collect_excel_files(files: Optional[List[Path]], default_dir: Optional[Path]) -> List[Path]:
    paths: List[Path] = []
    if files:
        for f in files:
            if f.exists() and f.is_file() and f.suffix.lower() in [".xlsx", ".xlsm", ".xls"]:
                paths.append(f.resolve())
    elif default_dir and default_dir.exists():
        # Prefer latest variants of the 3 requested datasets
        candidates = list(default_dir.glob("*.xlsx"))
        # Basic heuristic: include the three by keyword if present
        keywords = ["Role_Navigator", "Competency", "Adjacency"]
        selected = []
        for kw in keywords:
            match = [p for p in candidates if kw.lower() in p.name.lower()]
            if match:
                # Use the latest by modified time
                match.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                selected.append(match[0])
        # Fallback to all .xlsx if none matched
        paths = selected if selected else candidates
        paths = [p.resolve() for p in paths]
    return paths


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


# PUBLIC_INTERFACE
def run_seeder(
    files: Optional[List[str]] = typer.Option(None, "--files", help="One or more Excel files to ingest.", metavar="FILE", show_default=False),
    dir: Optional[str] = typer.Option(None, "--dir", help="Directory to scan for Excel files (defaults to repository 'attachments' folder)."),
    mapping_file: Optional[str] = typer.Option(
        "kavia-docs/supabase_schema/columns_mapping.md",
        "--mapping-file",
        help="Path to columns mapping markdown file.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse and report only; do not upsert."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
):
    """
    Seed Supabase tables from Excel files using mapping spec.

    Parameters:
    - files: Optional list of Excel file paths to ingest. If omitted, defaults to scanning the repository 'attachments' directory.
    - dir: Optional directory path to scan for Excel files (used when --files is not supplied).
    - mapping_file: Path to kavia-docs/supabase_schema/columns_mapping.md that defines sheet/column mappings.
    - dry_run: If True, no changes are made to Supabase; parsing and planned upserts are logged.
    - verbose: Enable verbose logging for diagnostics.

    Returns:
    None (exits process with non-zero code on failure).
    """
    _configure_logging(verbose)
    logger = logging.getLogger("seeder")

    # Load environment (.env) and read Supabase credentials
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        logger.error("Missing required environment variables SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY. Aborting.")
        raise typer.Exit(code=2)

    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    if dir:
        default_dir = Path(dir).resolve()
    else:
        default_dir = _find_default_attachments_dir(script_dir) or script_dir

    file_paths = [Path(f).resolve() for f in (files or [])]
    excel_files = _collect_excel_files(file_paths, default_dir)

    if not excel_files:
        logger.error("No Excel files found. Provide --files or ensure the attachments directory contains .xlsx files.")
        raise typer.Exit(code=3)

    # Load mapping
    repo_root = _find_repo_root(script_dir)
    mapping_path = (repo_root / mapping_file) if not Path(mapping_file).is_absolute() else Path(mapping_file)
    if not mapping_path.exists():
        logger.error(f"Mapping file not found: {mapping_path}")
        raise typer.Exit(code=4)
    mapping = ColumnsMapping.load_from_file(mapping_path)

    # Initialize client and seeder
    client = SupabaseRest(supabase_url=supabase_url, service_key=service_key)
    seeder = Seeder(client=client, mapping=mapping, dry_run=dry_run)

    # Parse and seed
    logger.info(f"Discovered {len(excel_files)} Excel files to process:")
    for fp in excel_files:
        logger.info(f"  - {fp}")

    seeder.parse_files(excel_files)

    # Log planned counts (pre-seed)
    logger.info("Planned rows after parsing (deduplicated):")
    logger.info(f"  roles:               {len(seeder._roles)}")
    logger.info(f"  competencies:        {len(seeder._competencies)}")
    logger.info(f"  role_competencies:   {len(seeder._role_competencies)}")
    logger.info(f"  learning_resources:  {len(seeder._learning_resources)}")
    logger.info(f"  role_adjacency:      {len(seeder._role_adjacency)}")

    if dry_run:
        logger.info("Dry-run mode enabled; no database changes will be made.")
        raise typer.Exit(code=0)

    try:
        summary = seeder.seed()
    except PostgrestError as e:
        logger.error(f"Seeding failed due to PostgREST error: {e}")
        raise typer.Exit(code=5)
    except Exception as e:
        logger.exception(f"Unexpected error during seeding: {e}")
        raise typer.Exit(code=6)

    logger.info("Seeding complete. Summary:")
    logger.info(f"  roles upserted:               {summary.roles}")
    logger.info(f"  competencies upserted:        {summary.competencies}")
    logger.info(f"  role_competencies upserted:   {summary.role_competencies}")
    logger.info(f"  learning_resources upserted:  {summary.learning_resources}")
    logger.info(f"  role_adjacency upserted:      {summary.role_adjacency}")


# PUBLIC_INTERFACE
def main():
    """CLI entrypoint for the seeding utility."""
    typer.run(run_seeder)


if __name__ == "__main__":
    main()
