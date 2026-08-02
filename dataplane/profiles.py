import os,re
from pathlib import Path
import yaml
from .models import ConnectionProfile
PAT=re.compile(r"\$\{([A-Z0-9_]+)\}")
def exp(v):
    if isinstance(v,dict): return {k:exp(x) for k,x in v.items()}
    if isinstance(v,list): return [exp(x) for x in v]
    if not isinstance(v,str): return v
    def r(m):
        n=m.group(1)
        if n not in os.environ: raise EnvironmentError(f"Required environment variable is not set: {n}")
        return os.environ[n]
    return PAT.sub(r,v)
class ProfileStore:
    def __init__(self,path=None): self.path=Path(path) if path else Path(__file__).resolve().parents[1]/'config'/'profiles.yaml'
    def load(self,name):
        if not self.path.exists(): raise FileNotFoundError(f"Profile file not found: {self.path}")
        raw=yaml.safe_load(self.path.read_text(encoding='utf-8')) or {}
        cfg=exp(raw.get('profiles',{}).get(name))
        if cfg is None: raise KeyError(f"Unknown profile: {name}")
        return ConnectionProfile(name=name,driver=str(cfg['driver']).lower(),database=str(cfg['database']),read_only=bool(cfg.get('read_only',True)),timeout_seconds=int(cfg.get('timeout_seconds',10)),max_rows=int(cfg.get('max_rows',500)),allowed_tables=tuple(cfg.get('allowed_tables',()) or ()))
