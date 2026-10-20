#!/usr/bin/env python3
"""Rebuild the standalone learning folder from project sources and course.py."""
from pathlib import Path
import sys, importlib.util, json, re, shutil, hashlib, datetime, html
ROOT=Path(__file__).resolve().parents[1]; SCRIPT_DIR=Path(__file__).resolve().parent
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)==3 and sys.argv[1]=='--output' else SCRIPT_DIR
for folder in ('sources','assets','qa'):
 (OUT/folder).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(SCRIPT_DIR))
from course import GROUPS,TOPICS,TERMS
from curriculum import register_new,enrich,SOURCES,NEW
register_new(TOPICS)
TERMS.extend((n['term'],n['cards'][0],n['id']) for n in NEW)
spec=importlib.util.spec_from_file_location('legacy_renderer',ROOT/'docs/build.py')
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)
docs=r.discover_documents()
ids={d.path.resolve():f'doc-{i+1:02}' for i,d in enumerate(docs)}
media=[];paths={}
for n,folder in enumerate(sorted((ROOT/'video/lessons').iterdir()),1):
 if not folder.is_dir() or not (folder/'script.md').exists():continue
 key='lesson-'+folder.name[:3];title=folder.name[4:].replace('-',' ')
 title=re.sub(r'^(第\s*\d+\s*课[：:]?\s*|\d+[-\s])','',title)
 item={'id':key,'title':title,'kind':'lesson','source':ids[(folder/'script.md').resolve()]}
 for suffix,source in [('audio',folder/'narration.mp3'),('video',folder/'render'/f'{key}.mp4')]:
  if source.exists():
   target=f'media/{key}{source.suffix}';paths[source.resolve()]=target;item[suffix]=target
 timing=folder/'timing.json'
 if timing.exists():
  t=json.loads(timing.read_text());item['timing']=t
 media.append(item)
for folder in sorted((ROOT/'podcast/episodes').iterdir()):
 if not folder.is_dir() or not (folder/'script.md').exists():continue
 key='podcast-'+folder.name[:3];source=folder/'episode.mp3'
 if not source.exists():continue
 target=f'media/{key}.mp3';paths[source.resolve()]=target
 media.append({'id':key,'title':folder.name[4:],'kind':'sample' if key.endswith('000') else 'podcast','audio':target,'source':ids[(folder/'script.md').resolve()]})
for p in (ROOT/'diagram').glob('*.svg'):
 target='assets/mindmap.svg';shutil.copy2(p,OUT/target);paths[p.resolve()]=target

def link(target,src):
 if target.startswith(('https://','http://','mailto:','#')):return target
 if target.startswith(('javascript:','data:')):return '#'
 clean=target.split('#')[0]
 for p in [src.parent/clean,ROOT/clean]:
  p=p.resolve()
  if p in ids:return '#/document/'+ids[p]
  if p in paths:return '#/map' if paths[p].startswith('media/') else paths[p]
 # technical production links are not necessary for the portable learner bundle
 return '#/library'
r.source_href=link
def render_md(text,path):
 rendered,headings=r.markdown_to_html(text,path)
 starts=[];fenced=False;numbered=False
 for line in text.splitlines():
  if line.lstrip().startswith('```'):
   fenced=not fenced;numbered=False;continue
  if fenced:continue
  match=re.match(r'^\s*(\d+)[.)]\s+',line)
  if match and not numbered:starts.append(match.group(1))
  numbered=bool(match)
 cursor=iter(starts)
 rendered=re.sub(r'<ol>',lambda _: '<ol start="'+next(cursor,'1')+'">',rendered)
 return rendered,headings
catalog=[]
for d in docs:
 ident=ids[d.path.resolve()];text=d.path.read_text();rendered,headings=render_md(text,d.path)
 shutil.copy2(d.path,OUT/'sources'/f'{ident}.md')
 catalog.append({'id':ident,'title':d.title,'group':d.group,'kind':d.kind,'path':d.source,'text':text,'html':rendered,'headings':headings,'download':f'sources/{ident}.md','hash':hashlib.sha256(d.path.read_bytes()).hexdigest()})
core={'notes':0,'questions':1,'gateway':2,'quality':3,'acs':4}
from details import build_details
coverage=build_details(TOPICS,docs,catalog,core,render_md)
(OUT/'qa/content-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2))
for t in TOPICS:
 t['sources']=[]
 for key,needle in t.pop('refs'):
  d=docs[core[key]];record=catalog[core[key]];lines=record['text'].splitlines();start=None
  for j,line in enumerate(lines):
   if re.match(r'^#{1,6} ',line) and needle in line:start=j;break
  if start is None:raise ValueError(f'{t["id"]}: missing {needle}')
  level=len(lines[start])-len(lines[start].lstrip('#'));end=len(lines)
  for k in range(start+1,len(lines)):
   if re.match(r'^#{1,'+str(level)+r'} ',lines[k]):end=k;break
  fragment='\n'.join(lines[start:end]);rendered,_=render_md(fragment,d.path)
  t['sources'].append({'doc':record['id'],'title':re.sub(r'^#+\s*','',lines[start]),'html':rendered})
 # Related audio where a topic has no short lesson.
 if not t.get('media'):
  t['media']={'customer':'podcast-102','business':'podcast-103','product':'podcast-104','hardware':'podcast-104','start':'podcast-101'}.get(t['group'])
stages=enrich(TOPICS,render_md,OUT/'curriculum.py')
from plain_language import finish,terms_for_reader,GLOSS
finish(TOPICS,stages,render_md,OUT/'curriculum.py')
from diagrams import illustrate
illustrate(TOPICS)
assert len({t['id'] for t in TOPICS})==len(TOPICS)
assert all(p in {t['id'] for t in TOPICS} for t in TOPICS for p in t['pre'])
media=[]
data={'stages':stages,'wordHelp':GLOSS,'plainLanguageVersion':1,'references':{k:dict(title=v[0],url=v[1]) for k,v in SOURCES.items()},'groups':[dict(id=g[0],title=g[1],icon=g[2],color=g[3],tint=g[4],goal=g[5]) for g in GROUPS],'topics':TOPICS,'terms':terms_for_reader(TERMS),'documents':catalog,'media':media,'built':'2026-10-20'}
(OUT/'data.js').write_text('window.KB = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
manifest={'built':data['built'],'topics':len(TOPICS),'questions':len(TOPICS)*2,'chapters':sum(len(t['chapters']) for t in TOPICS),'coreCoverage':coverage,'learningFigures':sum(len(c['figures']) for t in TOPICS for c in t['chapters']),'uniqueIllustrations':len({f['src'] for t in TOPICS for c in t['chapters'] for f in c['figures']}),'courseChars':sum(t['readingChars'] for t in TOPICS),'documents':len(catalog),'terms':len(TERMS),'media':[{k:v for k,v in x.items() if k!='timing'} for x in media],'sources':[{k:d[k] for k in ('id','path','hash')} for d in catalog]}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
handout=['# 硬件小岛课程讲义\n\n主课讲解与教学案例。金额、参数和条件按文中假设理解；项目原稿保持原始版本。\n']
for stage in stages:
 handout.append('\n# '+stage['title']+'\n\n本阶段产出：'+stage['output']+'\n')
 for t in TOPICS:
  if t['group']!=stage['id']:continue
  handout.append('\n'+t['chapters'][0]['text']+'\n\n### 换你来做\n\n'+t['practice']['prompt']+'\n\n参考思路：'+t['practice']['answer']+'\n')
(OUT/'课程补充讲义.md').write_text('\n'.join(handout))
print(json.dumps({k:manifest[k] for k in ('topics','questions','documents','terms')},ensure_ascii=False))
