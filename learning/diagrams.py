"""Image2 raster illustrations with authored reading cues; never map source tables."""
from deep_lessons import LESSONS
from plain_language import simple

# The first generation briefs were written before the remaining deep lessons.
# Keep artwork cues faithful to those briefs, rather than miscaptioning a scene.
AUTHORED_CASE_BRIEFS={'role','architecture','pilot','tco','roadmap','interfaces','connectivity','power','security','firmware','dfm','sourcing','reliability','fmea','spc','inventory','metrics'}
READING_NOTES={
 'moscow':'图里的设施是一个比喻。什么必须做，要看这一次准备完成什么，不能只照着图分类。',
 'rice':'可以数客户、设备或任务，但比较时要数同一种对象，也要按同样长的时间来算。',
 'tco':'钱币只表示费用高低，具体多少钱请按正文计算。两个方案要比较相同的使用年限和费用项目。',
 'economics':'图里先分开前期投入和每多做一台就增加的费用。每台剩的钱、最终利润和手里现金，需要分别计算。',
 'pricing':'扣完折扣后的价格，还没有减去生产和服务等全部费用，因此不是利润。金额计算保留到分。',
 'spc':'曲线帮助你理解变化，不是实测数据。产品要求的合格范围，与生产平时的波动范围，要分开看。',
 'power':'既要算平时耗多少电，也要检查最忙的一瞬间电源撑不撑得住。设备外形和比例只是示意。'
}
CASE_NOTES={
 'spc':'左图的勾表示测量值暂未超过产品上限，不表示过程稳定。连续趋势仍需按预定规则调查；曲线为教学示意。',
 'rootcause':'底部四组用于说明对照设计。绿色联网图标只示意恢复状态，不能据此认定哪一项是根因。'
}

def illustrate(topics):
 for t in topics:
  d=LESSONS[t['id']]
  for c in t['chapters']:
   case_nodes=[dict(label=label,detail=body,origin='教学案例') for label,body in zip(['发生了什么','一步步怎么办','结果和适用条件'],d['case'][1:])] if t['id'] in AUTHORED_CASE_BRIEFS else [
    dict(label='理解场景',detail=t['cards'][1],origin='教学案例'),
    dict(label='思考选择',detail=t['scenario']['prompt'],origin='教学案例'),
    dict(label='查看分析',detail=t['scenario']['feedback']+' '+t['practice']['answer'],origin='教学案例')]
   case_title=d['case'][0] if t['id'] in AUTHORED_CASE_BRIEFS else t['scenario']['prompt']
   c['figures']=[
    dict(id=c['id']+'-concept',title=t['title'],src=f"assets/image2/{t['id']}-concept.webp",
     alt=t['title']+'的概念插画；文字解释见图后。',
     nodes=[dict(label=label,detail=body,origin='课程讲解') for label,body in zip(['理解概念','对照场景','哪些情况要留意'],t['cards'])],
     caption=simple(READING_NOTES.get(t['id'],'')),kind='概念'),
    dict(id=c['id']+'-case',title=case_title,src=f"assets/image2/{t['id']}-case.webp",
     alt=t['title']+'的场景插画；分析过程见图后。',
     nodes=case_nodes,
     caption=simple(CASE_NOTES.get(t['id'],'这是一幅教学插画。点下面的步骤看分析，图中示意不代表实际测量结果。')),kind='案例')
   ]
   c['searchText']=c.get('readingText',c['text'])+' '+(' '.join(c['practice'].values()) if c.get('practice') else '')+' '+' '.join(n['label']+' '+n['detail'] for f in c['figures'] for n in f['nodes'])
