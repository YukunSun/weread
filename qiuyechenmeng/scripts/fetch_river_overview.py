"""Extract selected small-scale river references from Natural Earth."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
URL='https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_rivers_lake_centerlines.geojson'
SPECS={
 'Dadu':('dadu',[101,29,103,32]),'Yalong':('yalong',[98.8,29.3,101.2,32.3]),
 'Jinsha':('jinsha',[97.8,30.5,99.2,32.4]),'Lancang':('lancang',[96.1,30.3,97.8,32]),
 'Za':('zaqu',[96.1,30.3,97.8,32]),'Nu':('nu',[90.5,29.5,97.1,33.1]),
 'Tongtian':('tongtian',[89.5,32.2,97,35.5]),'Tuotuo':('tuotuo',[89.5,33.4,93.5,35.5]),
 'Yarlung':('yarlung',[92.2,28.5,96.1,30.3]),'Dihang':('yarlung',[92.2,28.5,96.1,30.3])}

def extract(source):
    raw=source.read_bytes();doc=json.loads(raw);features=[]
    for f in doc['features']:
        p=f['properties'];name=p.get('name')
        if name not in SPECS or p.get('featurecla')!='River': continue
        rid,b=SPECS[name];lines=f['geometry']['coordinates']
        if f['geometry']['type']=='LineString': lines=[lines]
        parts=[]
        for line in lines:
            part=[]
            for x,y,*_ in line:
                if b[0]<=x<=b[2] and b[1]<=y<=b[3]: part.append([round(x,5),round(y,5)])
                else:
                    if len(part)>1: parts.append(part)
                    part=[]
            if len(part)>1: parts.append(part)
        if not parts: continue
        features.append({'type':'Feature','properties':{'river_id':rid,'source_name':name,'rivernum':p.get('rivernum'),'source_url':URL,'resolution':'Natural Earth 1:10 million generalized centerline; not local-bank accuracy'},'geometry':{'type':'MultiLineString','coordinates':parts}})
    out=ROOT/'data/rivers';out.mkdir(parents=True,exist_ok=True)
    (out/'overview.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,separators=(',',':'))+'\n')
    (out/'overview_manifest.json').write_text(json.dumps({'source_url':URL,'retrieved_at':'2026-10-31','source_sha256':hashlib.sha256(raw).hexdigest(),'license':'Natural Earth public domain','license_url':'https://www.naturalearthdata.com/about/terms-of-use/','method':'Keep consecutive source vertices within selected boxes, never join separated parts; only featurecla River, excluding artificial lake centerlines','feature_count':len(features),'scope':SPECS,'limitations':'Cartographic generalized reference. Not historical river reconstruction, bank survey, route or crossing identification.'},ensure_ascii=False,indent=2)+'\n')
    print('Natural Earth reference features:',len(features))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path);args=parser.parse_args()
    if args.source: extract(args.source)
    else:
        with tempfile.TemporaryDirectory(prefix='qiuye-river-overview-') as d:
            p=Path(d)/'rivers.geojson';subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','60',URL,'--output',str(p)],check=True);extract(p)
