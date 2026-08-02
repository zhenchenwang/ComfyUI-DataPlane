import json

from .dataplane.adapters import create_adapter
from .dataplane.manifest import create_manifest
from .dataplane.models import QueryParameters
from .dataplane.policy import evaluate_query_policy
from .dataplane.profiles import ProfileStore

CATEGORY = "DataPlane"


class Connection:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "profile_name": ("STRING", {"default": "research_sqlite"}),
            "profiles_path": ("STRING", {"default": ""}),
            "test_connection": ("BOOLEAN", {"default": True}),
        }}

    RETURN_TYPES = ("DATAPLANE_PROFILE", "STRING")
    RETURN_NAMES = ("profile", "status")
    FUNCTION = "load"
    CATEGORY = CATEGORY + "/Connection"

    def load(self, profile_name, profiles_path, test_connection):
        profile = ProfileStore(profiles_path or None).load(profile_name)
        status = json.dumps(profile.safe_summary(), indent=2)
        if test_connection:
            status = create_adapter(profile).test_connection()[1] + "\n" + status
        return profile, status


class Binder:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"parameters_json": ("STRING", {"default": "{}", "multiline": True})}}

    RETURN_TYPES = ("DATAPLANE_PARAMETERS", "STRING")
    RETURN_NAMES = ("parameters", "preview")
    FUNCTION = "bind"
    CATEGORY = CATEGORY + "/Query"

    def bind(self, parameters_json):
        values = json.loads(parameters_json or "{}")
        if not isinstance(values, dict):
            raise ValueError("parameters_json must contain an object")
        return QueryParameters(values), json.dumps(values, indent=2, default=str)


class Gate:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "profile": ("DATAPLANE_PROFILE", {"forceInput": True}),
            "sql": ("STRING", {"multiline": True, "default": "SELECT * FROM products"}),
            "requested_limit": ("INT", {"default": 100, "min": 1, "max": 100000}),
            "request_writeback": ("BOOLEAN", {"default": False}),
        }}

    RETURN_TYPES = ("DATAPLANE_POLICY", "BOOLEAN", "STRING")
    RETURN_NAMES = ("policy", "allowed", "reason")
    FUNCTION = "evaluate"
    CATEGORY = CATEGORY + "/Governance"

    def evaluate(self, profile, sql, requested_limit, request_writeback):
        decision = evaluate_query_policy(profile, sql, requested_limit, request_writeback)
        return decision, decision.allowed, decision.reason


class Query:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "profile": ("DATAPLANE_PROFILE", {"forceInput": True}),
            "policy": ("DATAPLANE_POLICY", {"forceInput": True}),
            "parameters": ("DATAPLANE_PARAMETERS", {"forceInput": True}),
            "sql": ("STRING", {"multiline": True, "default": "SELECT * FROM products"}),
        }}

    RETURN_TYPES = ("DATAPLANE_QUERY_RESULT", "STRING", "INT")
    RETURN_NAMES = ("query_result", "preview_json", "row_count")
    FUNCTION = "execute"
    CATEGORY = CATEGORY + "/Query"

    def execute(self, profile, policy, parameters, sql):
        result = create_adapter(profile).execute_query(sql, parameters, policy)
        return result, json.dumps(result.as_jsonable(), indent=2, default=str), result.row_count


class Row:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "query_result": ("DATAPLANE_QUERY_RESULT", {"forceInput": True}),
            "row_index": ("INT", {"default": 0, "min": 0, "max": 1000000}),
        }}

    RETURN_TYPES = ("DATAPLANE_ROW", "STRING")
    RETURN_NAMES = ("row", "row_json")
    FUNCTION = "select"
    CATEGORY = CATEGORY + "/Batch"

    def select(self, query_result, row_index):
        if row_index >= query_result.row_count:
            raise IndexError("row_index exceeds result size")
        row = query_result.rows[row_index]
        return row, json.dumps(row, indent=2, default=str)


class Template:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "row": ("DATAPLANE_ROW", {"forceInput": True}),
            "template": ("STRING", {"multiline": True, "default": "A premium image of {product_name} in {colour}."}),
            "strict": ("BOOLEAN", {"default": True}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "render"
    CATEGORY = CATEGORY + "/Transform"

    def render(self, row, template, strict):
        class Safe(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        return (template.format_map(row if strict else Safe(row)),)


class Manifest:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query_result": ("DATAPLANE_QUERY_RESULT", {"forceInput": True}),
                "source_row_reference": ("STRING", {"default": ""}),
                "metadata_json": ("STRING", {"default": "{}", "multiline": True}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("DATAPLANE_MANIFEST", "STRING")
    RETURN_NAMES = ("manifest", "manifest_json")
    FUNCTION = "build"
    CATEGORY = CATEGORY + "/Provenance"

    def build(self, query_result, source_row_reference, metadata_json, prompt=None, extra_pnginfo=None):
        manifest = create_manifest(
            {"prompt": prompt, "extra_pnginfo": extra_pnginfo},
            query_result,
            source_row_reference or None,
            json.loads(metadata_json or "{}"),
        )
        return manifest, json.dumps(manifest.as_jsonable(), indent=2, default=str)


class Writeback:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "profile": ("DATAPLANE_PROFILE", {"forceInput": True}),
            "policy": ("DATAPLANE_POLICY", {"forceInput": True}),
            "table": ("STRING", {"default": "generation_results"}),
            "row_json": ("STRING", {"default": "{}", "multiline": True}),
            "confirmation": ("STRING", {"default": ""}),
        }}

    RETURN_TYPES = ("DATAPLANE_WRITE_RESULT", "STRING")
    RETURN_NAMES = ("write_result", "status")
    FUNCTION = "write"
    CATEGORY = CATEGORY + "/Writeback"
    OUTPUT_NODE = True

    def write(self, profile, policy, table, row_json, confirmation):
        result = create_adapter(profile).insert_row(
            table, json.loads(row_json), policy, confirmation
        )
        return result, json.dumps(result.__dict__, indent=2, default=str)


NODE_CLASS_MAPPINGS = {
    "DataPlaneConnectionProfile": Connection,
    "DataPlaneParameterBinder": Binder,
    "DataPlanePolicyGate": Gate,
    "DataPlaneSQLQuery": Query,
    "DataPlaneRowSelector": Row,
    "DataPlanePromptTemplate": Template,
    "DataPlaneWorkflowManifest": Manifest,
    "DataPlaneWriteback": Writeback,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DataPlaneConnectionProfile": "DataPlane Connection Profile",
    "DataPlaneParameterBinder": "DataPlane Parameter Binder",
    "DataPlanePolicyGate": "DataPlane Policy Gate",
    "DataPlaneSQLQuery": "DataPlane SQL Query",
    "DataPlaneRowSelector": "DataPlane Row Selector",
    "DataPlanePromptTemplate": "DataPlane Prompt Template",
    "DataPlaneWorkflowManifest": "DataPlane Workflow Manifest",
    "DataPlaneWriteback": "DataPlane Writeback",
}
