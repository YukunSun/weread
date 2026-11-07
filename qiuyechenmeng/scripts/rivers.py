"""Modern river centerlines and separately qualified literary crossings."""
from collections import defaultdict
from pathlib import Path
import csv
import html
import json
import math
from regional_ranges import insert_styles, polygon
from post_routes import km
from output_paths import output_path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/rivers'
BACKGROUND={'nu','tongtian','tuotuo','yarlung'}

def load():
    config=json.loads((DATA/'河流与渡河.json').read_text())
    detailed=defaultdict(list);overview=defaultdict(list)
    for path in sorted((DATA/'sichuan').glob('*.geojson'))+sorted((DATA/'tibet').glob('*.geojson')):
        for f in json.loads(path.read_text())['features']: detailed[f['properties']['river_id']].append(f)
    for f in json.loads((DATA/'overview.geojson').read_text())['features']: overview[f['properties']['river_id']].append(f)
    return config,detailed,overview

def lines(feature):
    g=feature['geometry']
    if g['type']=='LineString': return [g['coordinates']]
    if g['type']=='MultiLineString': return g['coordinates']
    raise ValueError('Unexpected river geometry '+g['type'])

def line_km(features):
    return sum(km({'lon':a[0],'lat':a[1]},{'lon':b[0],'lat':b[1]}) for f in features for line in lines(f) for a,b in zip(line,line[1:]))

def nearest_vertex(features,seed):
    candidates=[p for f in features for line in lines(f) for p in line]
    return min(candidates,key=lambda p:(p[0]-seed[0])**2*math.cos(math.radians(seed[1]))**2+(p[1]-seed[1])**2)

def circle(center,radius):
    lon,lat=map(math.radians,center);angle=radius/6371.0088;ring=[]
    for n in range(49):
        bearing=2*math.pi*n/48
        y=math.asin(math.sin(lat)*math.cos(angle)+math.cos(lat)*math.sin(angle)*math.cos(bearing))
        x=lon+math.atan2(math.sin(bearing)*math.sin(angle)*math.cos(lat),math.cos(angle)-math.sin(lat)*math.sin(y))
        ring.append([math.degrees(x),math.degrees(y)])
    return ring

def river_body(r,config,features,overview=False):
    body='<h3>'+html.escape(r['name'])+'</h3><p><b>书中依据：</b>'+html.escape(r['chapter']+'；'+r['basis'])+'</p><p>'+html.escape(r['note'])+'</p>'
    quality='Natural Earth小比例尺概化中心线；放大后不能作河岸、古渡点或工程定位。' if overview else 'OpenStreetMap现代中心线片段，保持源数据分段，不补接未下载的中段；并非1909年前后河道复原。'
    body+='<p><b>河线性质：</b>'+quality+'</p><p>本层所选片段线长合计约'+f'{line_km(features):.1f}'+' km，只说明下载覆盖长度，不是整条河长、渡河宽度或作者行走距离。</p>'
    body+='<p>'+html.escape(config['scope'])+'</p><p><a href="'+config['book_url']+'">原书与校注</a></p>'
    urls=sorted({f['properties'].get('source_url') or f['properties'].get('source') for f in features})
    body+='<p>'+' · '.join('<a href="'+html.escape(u,quote=True)+'">河道数据'+str(i+1)+'</a>' for i,u in enumerate(urls) if isinstance(u,str) and u.startswith('http'))+'</p>'
    body+='<p>'+' · '.join('<a href="'+u+'">'+html.escape(k)+'</a>' for k,u in config['sources'].items())+'</p>'
    return body

def add_rivers(doc,el,view,kcolor,bundled=False):
    config,detailed,overview=load();styles=[]
    for r in config['rivers']:
        for macro in [False,True]:
            st=el(doc,'Style',id='river_'+r['id']+('_overview' if macro else ''));styles.append(st)
            line=el(st,'LineStyle');el(line,'color',kcolor(r['color'],'9a' if macro else 'ff'));el(line,'width',2.2 if macro else 4.0)
    st=el(doc,'Style',id='river_label');styles.append(st)
    ic=el(st,'IconStyle');el(ic,'scale',0.35);icon=el(ic,'Icon');el(icon,'href','icons/river_label.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    label=el(st,'LabelStyle');el(label,'color','ffffffff');el(label,'scale',1.05)
    st=el(doc,'Style',id='river_crossing');styles.append(st)
    ic=el(st,'IconStyle');el(ic,'scale',1.1);icon=el(ic,'Icon');el(icon,'href','icons/river_crossing.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/open-diamond.png')
    label=el(st,'LabelStyle');el(label,'color','ffffffff');el(label,'scale',0.95)
    line=el(st,'LineStyle');el(line,'color','d87bdcff');el(line,'width',2)
    poly=el(st,'PolyStyle');el(poly,'color','147bdcff');el(poly,'fill',1);el(poly,'outline',1)
    insert_styles(doc,styles)
    top=el(doc,'Folder',id='river_layers');el(top,'name','13 沿途主要河流与渡河地区');el(top,'open',1);el(top,'description','<p>'+config['scope']+'</p><p>校注十的两次皮船渡河专指北道入昌都一段：甘孜雅砻江、岗拖金沙江。不是全书只渡两条河。</p>');view(top,96.5,32,1900000)
    detail=el(top,'Folder');el(detail,'name','13A 主要河段｜现代河道实线，可单独开关');el(detail,'open',0)
    crossings=el(top,'Folder');el(crossings,'name','13B 书中渡河｜甘孜雅砻江、岗拖金沙江等');el(crossings,'open',1)
    background=el(top,'Folder');el(background,'name','13C 北返及雅鲁藏布背景｜概化河线，非古渡点');el(background,'open',0)
    comparison=el(top,'Folder');el(comparison,'name','13D 大范围水系补充｜概化，默认隐藏');el(comparison,'visibility',0);el(comparison,'open',0)
    el(comparison,'description','<p>用于远景查看主要河流方向。与13A对应的高精度片段有概化偏移，近景请关闭本层。未下载中段可用概化河线理解大致走向，但不是补接的精确河道。</p>')
    for r in config['rivers']:
        rid=r['id']
        for macro,features in [(False,detailed.get(rid,[])),(True,overview.get(rid,[]))]:
            if not features: continue
            parent=detail if not macro else background if rid in BACKGROUND else comparison
            suffix='_overview' if macro else '';f=el(parent,'Folder',id='river_group_'+rid+suffix);el(f,'name',r['name']+('｜概化水系' if macro else '｜已取现代河段'));el(f,'open',0)
            body=river_body(r,config,features,macro);el(f,'description',body)
            at=nearest_vertex(features,r['label']);view(f,*at,550000 if macro else 95000)
            p=el(f,'Placemark',id='river_line_'+rid+suffix);el(p,'name',r['name']+('〔概化中心线〕' if macro else '〔现代河道片段〕'));el(p,'description',body);view(p,*at,550000 if macro else 95000);el(p,'styleUrl','#river_'+rid+suffix);mg=el(p,'MultiGeometry')
            for feat in features:
                for points in lines(feat):
                    ls=el(mg,'LineString');el(ls,'tessellate',1);el(ls,'altitudeMode','clampToGround');el(ls,'coordinates',' '.join(f'{x:.7f},{y:.7f},0' for x,y,*_ in points))
            p=el(f,'Placemark',id='river_text_'+rid+suffix);el(p,'name',r['name']);el(p,'description',body);view(p,*at,550000 if macro else 95000);el(p,'styleUrl','#river_label');point=el(p,'Point');el(point,'coordinates',f'{at[0]},{at[1]},0')
    for c in config['crossings']:
        body='<h3>'+html.escape(c['name'])+'</h3>'
        for title,key in [('依据','chapter'),('过河方式','method'),('耗时与口径','time'),('定位性质','certainty'),('限制','note')]: body+='<p><b>'+title+'：</b>'+html.escape(c[key])+'</p>'
        body+='<p><a href="'+config['book_url']+'">原书及任乃强校注</a></p><p>渡水的日数与全程行军约数互有包含，不重复累加。</p>'
        p=el(crossings,'Placemark',id='river_crossing_'+c['id']);el(p,'name',c['name']);el(p,'description',body);view(p,*c['center'],max(35000,c['radius_km']*7000));el(p,'styleUrl','#river_crossing');mg=el(p,'MultiGeometry')
        point=el(mg,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{c["center"][0]},{c["center"][1]},0')
        if c['radius_km']: polygon(mg,[circle(c['center'],c['radius_km'])],el)
    notes=el(top,'Folder');el(notes,'name','13E 河名／渡点待考｜不造坐标');el(notes,'open',0)
    for n,u in enumerate(config['unlocated']):
        p=el(notes,'Placemark',id='river_unlocated_'+str(n));el(p,'name',u['name']+'〔未设古渡点〕');el(p,'description','<p>'+html.escape(u['chapter']+'；'+u['note'])+'</p><p>本条无几何；完整版说明和CSV也保留相同内容。</p>')
    return config

def write_river_index():
    config,detailed,overview=load()
    with (output_path('tables', '河流与渡河对照.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['类别','河流／事项','章节','依据／方法','耗时','定位与限制','已绘河段线长km','数据性质'])
        for r in config['rivers']:
            features=detailed.get(r['id']) or overview.get(r['id'],[])
            w.writerow(['河流',r['name'],r['chapter'],r['basis'],'',r['note'],round(line_km(features),1),'OSM现代片段' if r['id'] in detailed else 'Natural Earth概化水系'])
        for c in config['crossings']: w.writerow(['渡河地区',c['name'],c['chapter'],c['method'],c['time'],c['certainty']+'；'+c['note'],'','桥位地标' if not c['radius_km'] else '方位示意圈，非古渡址'])
        for u in config['unlocated']: w.writerow(['未定位',u['name'],u['chapter'],'','',u['note'],'','不设坐标'])
    text='《艽野尘梦》沿途主要河流与渡河地区\n核对日期：'+config['checked_at']+'\n\n'+config['scope']+'\n\n'
    text+='13A：OSM现代河道片段；13B：有文本依据的过桥／渡河地区；13C：北返和雅鲁藏布背景水系；13D：默认隐藏的大范围概化水系；13E：待考条目。\n概化河线取Natural Earth，近景有偏移，不用于古渡或河岸对位。\n\n'
    for c in config['crossings']: text+=c['name']+'：'+c['chapter']+'；'+c['method']+'。'+c['time']+' '+c['note']+'\n'
    text+='\n'+'\n'.join(u['name']+'：'+u['note'] for u in config['unlocated'])+'\n\n'
    text+='雅鲁藏布江作为地理背景；书中夥惹桥叙事不作陈渠珍亲渡。尼洋河、昂曲、扎曲、澜沧江可帮助理解附近地理，未据此虚构作者渡干流事件。汤买薄藏布古藤桥不套现代通麦三桥。\n\n'
    text+='已有地图只需叠加“艽野尘梦_沿途河流.kmz”；新版完整阅读地图已含13层，二选一避免重复。河线片段km不是整条河长、历史实走或河宽；地区示意圈半径不是历史范围测定。\n\n'
    text+='2026-10-31已将河流补充KMZ导入原Google Earth网页版项目，确认导入完成并保存到云端硬盘。已抽查甘孜雅砻江、岗拖金沙江的现代河线、地区示意圈及皮船/约3日估算弹窗。\n\n'
    text+='数据 © OpenStreetMap contributors，ODbL 1.0；Natural Earth为公有领域制图数据。逐段OSM IDs、时间戳、来源、覆盖缺口在data/rivers/的manifest中。\n\n'+config['book_url']+'\n'+'\n'.join(config['sources'].values())+'\n'
    (output_path('docs', '沿途河流说明.txt')).write_text(text)
