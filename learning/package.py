"""Create the portable learner package without source media, QA, or PNG originals."""
from pathlib import Path
import subprocess,sys,json,zipfile
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(root/'qa/finalize_artwork.py')],check=True)
subprocess.run([sys.executable,str(root/'qa/validate.py')],check=True)
files=[root/n for n in ('index.html','style.css','reading.css','app.js','widgets.js','diagrams.js','journey.js','data.js','manifest.json','README.md','课程补充讲义.md')]
files+=list((root/'assets').glob('*.svg'))
files+=list((root/'assets/image2').glob('*.webp'))
files+=list((root/'sources').glob('*.md'))
files+=list((root/'research').glob('*.md'))
files+=list((root/'artwork/prompts').glob('*.txt'))
target=root.parent/'硬件小岛-学习版.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
 for path in files:
  archive.write(path,'learning/'+path.relative_to(root).as_posix())
 artwork=json.loads((root/'artwork/manifest.json').read_text())
 portable=[{k:j[k] for k in ('id','topic','kind','status','backend','requestedModel','webPath','webSHA256','width','height','promptFile','editPromptFile','revision') if k in j} for j in artwork]
 archive.writestr('learning/artwork/manifest.json',json.dumps(portable,ensure_ascii=False,indent=2))
with zipfile.ZipFile(target) as archive:
 assert archive.testzip() is None
 assert len([n for n in archive.namelist() if n.endswith('.webp')])==120
 assert not any('/media/' in n or '/qa/' in n or n.endswith('.next.js') for n in archive.namelist())
print(f'{target}: {target.stat().st_size/1048576:.2f} MB; {len(files)+1} files')
