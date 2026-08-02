import hashlib,json,uuid
from datetime import datetime,timezone
from .models import WorkflowManifest
def create_manifest(payload,result,ref,metadata=None):
    wh=hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()
    return WorkflowManifest(str(uuid.uuid4()),wh,result.query_hash if result else None,result.source_profile if result else None,ref,datetime.now(timezone.utc).isoformat(),metadata or {})
