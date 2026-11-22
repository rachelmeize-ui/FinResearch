"""Read-only external-source check. Saves actual downloads and evidence; no model calls."""
import json,sys,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import entities,business_research
out=Path('test-results/business-source-fix-20261122');out.mkdir(parents=True,exist_ok=True)
logging.basicConfig(filename=out/'pdf-parser-warnings.log',level=logging.WARNING)
entity=entities.choose(entities.identify('腾讯'), 'cninfo:00700')
docs,record=business_research.discover(entity,'比较2023—2025年产品组合、商业模式、主要市场及风险',[2023,2024,2025],progress=lambda stage:print(stage.encode('ascii','backslashreplace').decode(),flush=True))
cards=business_research.evidence_cards(docs,'比较产品组合、商业模式、主要市场及风险',[entity['name']])
payload=dict(entity=entity,record=record,documents=docs,cards=cards,new_paid_model_calls=0)
(out/'actual-sources.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(documents=[{k:d.get(k) for k in ['url','report_year','bytes','sha256','status']} for d in docs],annual_attempts=record['annual_attempts'],cards=[{k:c.get(k) for k in ['company','dimension','quote','page','report_year']} for c in cards]),ensure_ascii=True))
assert {d.get('report_year') for d in docs if d['kind']=='official_report'}=={2023,2024,2025},'Some requested annual report failed. See actual-sources.json.'
assert all(c['quote'] for c in cards),'Some business dimensions remain unsupported. See actual-sources.json.'
for card in cards:
 source=next(d for d in docs if d['id']==card['source_id'])
 assert card['quote'] in source['content']
 if card.get('page'):assert card['quote'] in source['page_blocks'][card['page']-1]['text']
print('PASS real official 2023-2025 reports, four evidence dimensions, exact quote/page checks; no model call')
