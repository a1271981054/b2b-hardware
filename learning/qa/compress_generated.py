"""Encode generated originals for delivery. Leaves every original PNG intact."""
from pathlib import Path
import json,subprocess,time
root=Path(__file__).resolve().parents[1]
jobs=json.loads((root/'artwork/manifest.json').read_text())
script=Path.home()/'.codex/skills/baoyu-compress-image/scripts/main.ts'
done=set()
while len(done)<len(jobs):
 for j in jobs:
  if j['id'] in done:continue
  original=root/j['path'];webp=original.with_suffix('.webp')
  if j['id']!='role-concept' and not (root/'artwork/results'/f"{j['id']}.json").exists():continue
  if webp.exists() and webp.stat().st_mtime>=original.stat().st_mtime:
   done.add(j['id']);continue
  if not original.exists():continue
  result=subprocess.run(['npx','-y','bun',str(script),str(original),'--format','webp','--quality','90','--keep','--json'],capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stderr)
  done.add(j['id'])
  print(f"WebP {len(done)}/{len(jobs)}: {j['id']}",flush=True)
 if len(done)<len(jobs):time.sleep(5)
print('All generated originals encoded.',flush=True)
