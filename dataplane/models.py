from dataclasses import dataclass, field, asdict
from typing import Any
@dataclass(frozen=True,slots=True)
class ConnectionProfile:
    name:str; driver:str; database:str; read_only:bool=True; timeout_seconds:int=10; max_rows:int=500; allowed_tables:tuple[str,...]=()
    def safe_summary(self):
        d=asdict(self); d['database']='***'; return d
@dataclass(frozen=True,slots=True)
class QueryParameters: values:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True,slots=True)
class PolicyDecision:
    allowed:bool; reason:str; allow_writeback:bool; max_rows:int; allowed_tables:tuple[str,...]; decision_id:str
@dataclass(frozen=True,slots=True)
class QueryResult:
    columns:tuple[str,...]; rows:tuple[dict[str,Any],...]; row_count:int; source_profile:str; query_hash:str; truncated:bool; elapsed_ms:float
    def as_jsonable(self): return {'columns':list(self.columns),'rows':list(self.rows),'row_count':self.row_count,'source_profile':self.source_profile,'query_hash':self.query_hash,'truncated':self.truncated,'elapsed_ms':self.elapsed_ms}
@dataclass(frozen=True,slots=True)
class WorkflowManifest:
    manifest_id:str; workflow_hash:str; query_hash:str|None; source_profile:str|None; source_row_reference:str|None; created_at:str; metadata:dict[str,Any]
    def as_jsonable(self): return asdict(self)
@dataclass(frozen=True,slots=True)
class WritebackResult:
    success:bool; affected_rows:int; table:str; operation:str; message:str
