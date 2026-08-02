# ComfyUI-DataPlane

**Database, policy, provenance and batch-orchestration interfaces for governed ComfyUI workflows.**

ComfyUI-DataPlane turns a manually operated generation graph into a database-connected,
auditable and resumable production workflow.

## Current release

- Version: 0.1.0
- Stage: interface-first prototype
- Implemented adapters: SQLite, DuckDB
- Planned adapters: PostgreSQL, SQL Server, MySQL, Oracle
- Default query mode: read-only
- Write operations: explicit opt-in only

## Included nodes

- DataPlane Connection Profile
- DataPlane Parameter Binder
- DataPlane Policy Gate
- DataPlane SQL Query
- DataPlane Table Reader
- DataPlane Row Selector
- DataPlane Prompt Template
- DataPlane Workflow Manifest
- DataPlane Writeback

## Installation

Copy this folder into `ComfyUI/custom_nodes/ComfyUI-DataPlane`, install dependencies in the Python environment used by ComfyUI, then restart ComfyUI.

```bash
pip install -r requirements.txt
```

Copy `config/profiles.example.yaml` to `config/profiles.yaml` and set the referenced environment variables.

## Security model

- Connection secrets stay outside workflow JSON.
- Workflows reference named profiles only.
- Query nodes accept SELECT/CTE statements only.
- Queries are parameterized.
- Result rows are capped.
- Table allow-lists are supported.
- Writeback requires policy permission plus `CONFIRM_WRITE`.
- Query and workflow hashes are recorded for provenance.

## Compatibility

The package uses ComfyUI's established Python custom-node interface (`INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, `NODE_CLASS_MAPPINGS`) for broad compatibility.
