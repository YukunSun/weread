"""Historical background areas kept separate from the author's itinerary."""
from pathlib import Path
import copy
import hashlib
import html
import json
from fetch_regions import convert_coords, inverse_gcj
from regional_ranges import insert_styles, polygons, polygon

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/historical_context'

def load():
    config=json.loads((DATA/'瞻对史地.json').read_text())
    raw=json.loads((DATA/config['geometry']['file']).read_text())
    feature=copy.deepcopy(raw['features'][0])
    assert feature['properties']['adcode']==513329
    feature['geometry']['coordinates']=convert_coords(feature['geometry']['coordinates'])
    center=inverse_gcj(feature['properties']['centroid'])
    return config,feature,center

def description(config):
    body='<h3>瞻对／三瞻的地理与事件背景</h3>'
    for key in ['scope','book_context','chronology_correction']:
        body+='<p>'+html.escape(config[key])+'</p>'
    for t in config['timeline']:
        source=config['sources'][t['source']]
        body+='<p><b>'+html.escape(t['date'])+'</b>：'+html.escape(t['event'])+' <a href="'+html.escape(source['url'],quote=True)+'">依据</a></p>'
    body+='<p><b>县名沿革年份的异说：</b>'+html.escape(config['name_date_variants'])+'</p>'
    body+='<p><b>距离与耗时：</b>本层是背景地区，不接入陈渠珍行程，不给它补个人行程距离或耗时。</p>'
    body+='<p><b>范围数据：</b>'+html.escape(config['geometry']['method'])+' '+html.escape(config['geometry']['license_note'])+'</p>'
    body+='<p><a href="'+config['geometry']['source']+'">现代新龙县行政轮廓来源</a></p>'
    body+='<p>'+' · '.join('<a href="'+html.escape(s['url'],quote=True)+'">'+html.escape(s['title'])+'</a>' for s in config['sources'].values())+'</p>'
    return body

def add_historical_context(doc,el,view,kcolor,bundled=False):
    config,feature,center=load();body=description(config)
    area=el(doc,'Style',id='zhandui_admin_reference')
    line=el(area,'LineStyle');el(line,'color',kcolor('#ffcc72','dd'));el(line,'width',2)
    poly=el(area,'PolyStyle');el(poly,'color',kcolor('#ffcc72','38'));el(poly,'fill',1);el(poly,'outline',1)
    label=el(doc,'Style',id='zhandui_label')
    icon=el(label,'IconStyle');el(icon,'scale',0.4);ic=el(icon,'Icon');el(ic,'href','icons/region_label.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    ls=el(label,'LabelStyle');el(ls,'color','ffffffff');el(ls,'scale',1.0)
    insert_styles(doc,[area,label])
    folder=el(doc,'Folder',id='zhandui_context');el(folder,'name','12 瞻对／三瞻历史背景｜今新龙县范围参照');el(folder,'open',1);el(folder,'description',body);view(folder,*center,230000)
    p=el(folder,'Placemark',id='zhandui_reference_area');el(p,'name','瞻对／三瞻〔今新龙县方位参照，非史界〕');el(p,'description',body);view(p,*center,230000);el(p,'styleUrl','#zhandui_admin_reference')
    mg=el(p,'MultiGeometry')
    for rings in polygons(feature['geometry']): polygon(mg,rings,el)
    p=el(folder,'Placemark',id='zhandui_reference_label');el(p,'name','瞻对／三瞻〔今新龙一带〕');el(p,'description',body);view(p,*center,230000);el(p,'styleUrl','#zhandui_label')
    point=el(p,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{center[0]},{center[1]},0')

def write_historical_index():
    config,_,_=load()
    text='瞻对／三瞻历史背景\n核对日期：'+config['checked_at']+'\n\n'
    text+='\n\n'.join(config[k] for k in ['scope','book_context','chronology_correction'])+'\n\n'
    text+='\n'.join(t['date']+'：'+t['event'] for t in config['timeline'])+'\n\n'+config['name_date_variants']+'\n\n'
    text+='本层不接入作者路线，不为瞻对另造个人行程距离、耗时或战场精确点。\n已有云端地图时可叠加“艽野尘梦_瞻对历史背景.kmz”；新版完整阅读地图已包含12层，二选一以免重复显示。\n\n'
    text+='2026-10-31已将独立背景KMZ叠加到原Google Earth网页版项目，显示导入完成并保存到云端硬盘；已抽查半透明新龙县轮廓、雅砻江附近标签、历史背景与1896—1897年代说明。\n\n'
    text+='\n'.join(s['title']+'\n'+s['url'] for s in config['sources'].values())+'\n\n'+config['geometry']['source']+'\n'+config['geometry']['method']+'\n'+config['geometry']['license_note']+'\n'
    (ROOT/'瞻对历史背景说明.txt').write_text(text)
    manifest={'retrieved_at':'2026-10-31','source_url':config['geometry']['source'],'raw_sha256':hashlib.sha256((DATA/config['geometry']['file']).read_bytes()).hexdigest(),'use':'Modern Xinlong administrative reference, not historical Zhandui or three-tusi boundaries','coordinate_method':config['geometry']['method']}
    (DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
