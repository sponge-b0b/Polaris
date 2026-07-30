---
name: database-migrations
description: Manage the entire database schema lifecycle, including script generation, version tracking, file squashing, and lifecycle testing using SQLAlchemy and Alembic. Use whenever the database schema is modified, tables are created, migrations are required, or a user asks to update the database.
license: MIT
compatibility: product=codex product=claude-code system=alembic system=postgresql network=none
metadata:
  version: 1.1.0
---

# Database Migrations Skill

## Objective
Manage, generate, and validate database schema migrations seamlessly while ensuring data integrity, absolute backward reversibility, and alignment with the repository's lifecycle release version.

## Initial Pre-flight Check
Before writing or executing any database schema modification:
1. Identify the authoritative SQLAlchemy models being altered.
2. Confirm that changes are driven purely via `alembic` migration scripts.
3. **Constraint:** Projection rebuilds (e.g., Qdrant, Neo4j) are strictly forbidden from deleting canonical PostgreSQL source records.

## Execution Workflow

### Step 1: Check Project Release Version & Apply Strategy
You must check the current project release version prior to modifying or generating migration files:
1. Locate the definitive version string (e.g., in `pyproject.toml` or active Git release tags).
2. **Pre-1.0.0 Squashing Rule:** If the current project version is less than `1.0.0`, you MUST continuously squash revisions into a single clean baseline migration file per feature branch. 
3. Inspect the existing `/migrations` or `alembic/versions` directory. If local modifications already exist on your active branch, alter the baseline file directly rather than appending a new sequential file node.

### Step 2: Generate or Append the Revision Script
If a new revision is permitted by the version rules, run the automated generation tool via `uv`:
```bash
uv run alembic revision --autogenerate -m "type: descriptive migration intent"
```
If squashing, append your structural mutations directly to the target baseline file code block.

### Step 3: Audit the Structural Code Blocks
Open the target migration file and verify that the syntax maps exactly to expected states:
- Explicit column types match your frozen dataclass or model structures.
- Foreign key restraints specify clear cascade actions.
- Indexes are applied cleanly to high-churn lookups to maximize retrieval speeds.

### Step 4: Run the UP / DOWN Lifecycle Validation
You must execute a full round-trip execution matrix to guarantee the migration script is completely reversible and safe:
1. **Apply Upgrade:** Run the upgrade command to test your `upgrade()` block.
   ```bash
   uv run alembic upgrade head
   ```
2. **Verify State:** Confirm database tables and constraints match expected shapes.
3. **Apply Downgrade:** Revert the change immediately by exactly one step to test your `downgrade()` block.
   ```bash
   uv run alembic downgrade -1
   ```
4. **Final Verification:** Confirm your local database schema returns precisely to its baseline state with zero lingering structures, orphaned objects, or active table locks.

## Examples

### Example 1: Creating a Table Modification Plan (Pre-1.0.0)
**User:** "Add an active flag to the user accounts table."
**Agent Action:**
1. Checks `pyproject.toml` and detects version `0.4.2`.
2. Inspects git status and logs to find the current unmerged branch baseline file.
3. Appends `sa.Column('active', sa.Boolean(), default=True)` straight into the existing local migration block instead of spawning a new sequential version file.
4. Executes `uv run alembic upgrade head` followed by `uv run alembic downgrade -1` to validate the round-trip code integrity.
