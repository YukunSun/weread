"""Source-labelled comparison of the quoted southern and northern post roads."""
from pathlib import Path
import csv
import html
import json
import math
from regional_ranges import insert_styles, polygons, polygon
from route_checks import CHECK, SEQUENCE, route_check_html

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/postroads'
DISTANCE_NOTE='距离为代表点间球面近似直距（km），不是历史实走或现代公路里程。主要地名间省略了中间站，分段直距和仅为所选节点的示意线长度；推定点会影响数值。'

def load():
    cfg=json.loads((DATA/'南北驿路.json').read_text())
    north=next(r for r in cfg['routes'] if r['id']=='north')
    assert north['ids'][north['ids'].index('garze'):] == SEQUENCE
    return cfg,{p['id']:p for p in cfg['places']}

def timing_endpoint(t, key, places):
    return places[t[key]]['name'] if t[key] else t.get(key+'_label','区域／事项（无单点坐标）')

def km(a,b):
    x1,y1,x2,y2=map(math.radians,[a['lon'],a['lat'],b['lon'],b['lat']])
    h=math.sin((y2-y1)/2)**2+math.cos(y1)*math.cos(y2)*math.sin((x2-x1)/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(h)))

def edge_time(cfg,a,b):
    for t in cfg['timings']:
        if t['from']==a and t['to']==b: return t['time']+'（'+t['kind']+'）'
    return '该相邻段未明记；大段约数不按距离分摊'

def place_check():
    return json.loads((ROOT/'data/place_checks/长坝春核对.json').read_text())

def add_changba_check(parent,el,view):
    check=place_check();a=check['historical_place'];b=check['modern_comparison'];distance=km(a,b)
    body='<h3>长坝春与新都桥的位置核对</h3><p>'+html.escape(check['conclusion'])+'</p>'
    body+=f'<p><b>江巴村图示点与新都桥镇代表点：直距约{distance:.0f} km。</b></p><p>'+html.escape(check['distance_note'])+'</p>'
    body+='<p>宽阔平原和G318沿线风景不能单独证明旧地名。此层新都桥点仅用于现代位置比较，不接入作者行程；相邻段耗时仍按原文保留。</p>'
    for e in check['evidence']:
        body+='<p><a href="'+html.escape(e['url'],quote=True)+'">'+html.escape(e['title'])+'</a><br/>'+html.escape(e['supports'])+'</p>'
    body+='<p><a href="'+b['source']+'">新都桥OSM地名点</a><br/>'+html.escape(check['attribution'])+'</p>'
    f=el(parent,'Folder',id='changba_comparison');el(f,'name',f'11F 长坝春／新都桥核对｜两点直距约{distance:.0f} km');el(f,'open',1);el(f,'description',body);view(f,101.57,30.12,65000)
    p=el(f,'Placemark',id='modern_xinduqiao_comparison');el(p,'name',b['name']);el(p,'description',body);view(p,101.57,30.12,65000);el(p,'styleUrl','#post_point')
    point=el(p,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{b["lon"]},{b["lat"]},0')
    p=el(f,'Placemark',id='changba_xinduqiao_distance');el(p,'name',f'位置比较直距约{distance:.0f} km〔非作者路线〕');el(p,'description',body);view(p,101.57,30.12,65000);el(p,'styleUrl','#post_line_alternative')
    mg=el(p,'MultiGeometry');count=math.ceil(distance/1.5)
    for j in range(count):
        line=el(mg,'LineString');el(line,'tessellate',1);el(line,'altitudeMode','clampToGround')
        el(line,'coordinates',' '.join(f'{a["lon"]+(b["lon"]-a["lon"])*t:.7f},{a["lat"]+(b["lat"]-a["lat"])*t:.7f},0' for t in [j/count,(j+0.45)/count]))

def add_post_routes(doc,el,view,kcolor,bundled=False,include_existing=True):
    cfg,places=load();styles=[]
    for r in cfg['routes']:
        st=el(doc,'Style',id='post_line_'+r['id']);styles.append(st)
        line=el(st,'LineStyle');el(line,'color',kcolor(r['color'],'ef'));el(line,'width',4)
    for sid,color,hollow in [('point','#8ad4ff',False),('uncertain','#ffc66d',True),('measure','#cbd5e1',False)]:
        st=el(doc,'Style',id='post_'+sid);styles.append(st)
        ic=el(st,'IconStyle');el(ic,'color','ffffffff' if bundled else kcolor(color));el(ic,'scale',0.9 if sid!='measure' else 0.25)
        icon=el(ic,'Icon');el(icon,'href',('icons/post_'+sid+'.png') if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        label=el(st,'LabelStyle');el(label,'color','ffffffff');el(label,'scale',0.9 if sid!='measure' else 0.8)
    st=el(doc,'Style',id='post_hor39');styles.append(st)
    line=el(st,'LineStyle');el(line,'color','a0d1b2f0');el(line,'width',1.4)
    poly=el(st,'PolyStyle');el(poly,'color','20d1b2f0');el(poly,'fill',1);el(poly,'outline',1)
    insert_styles(doc,styles)
    top=el(doc,'Folder',id='post_routes');el(top,'name','11 南北驿路原文对照｜距离km与已知耗时');el(top,'open',1)
    intro='<p>橙色：原文南路背景；蓝色：北路进昌都；紫色：昌都后北绕；灰色：原文另列走法。所有路线均为断续虚线示意。</p><p>'+DISTANCE_NOTE+'</p><p>原文巴、里塘按地理顺序绘理塘→巴塘；三十九族按区域处理；南路拉萨终点不表示作者亲到。</p><p>往往一二日无人烟是荒僻情形，不能拿来给各站填1—2日。点的弹窗及路线表列已知耗时，缺失日数保留未记。</p>'
    el(top,'description',intro);view(top,96.5,30.8,1200000)
    pts=el(top,'Folder',id='post_points');el(pts,'name','11A 地点｜橙色空心为对应推定／待考');el(pts,'open',0)
    for p in cfg['places']:
        if p['existing'] and not include_existing: continue
        uncertain=p['id'] in ['zengke','danda']
        pm=el(pts,'Placemark',id='post_point_'+p['id']);el(pm,'name',p['name'])
        body=f'<h3>{html.escape(p["name"])}</h3><p><b>定位性质：</b>{p["certainty"]}</p><p>{html.escape(p["note"])}</p><p>经纬度：{p["lon"]:.5f}, {p["lat"]:.5f}。存储小数位不代表古址精度。</p>'
        related=[]
        for route in cfg['routes']:
            for a,b in zip(route['ids'],route['ids'][1:]):
                if p['id'] in [a,b]: related.append((route,a,b))
        for route,a,b in related:
            body+=f'<p>{html.escape(places[a]["name"])} → {html.escape(places[b]["name"])}：<b>直线约{km(places[a],places[b]):.0f} km</b><br/>{html.escape(edge_time(cfg,a,b))}</p>'
        body+='<p>'+DISTANCE_NOTE+'</p><p><a href="'+p['source']+'">坐标参照</a>'
        if p.get('identity_source'): body+=' · <a href="'+p['identity_source']+'">地名依据</a>'
        body+='</p>'
        el(pm,'description',body);view(pm,p['lon'],p['lat'],100000);el(pm,'styleUrl','#post_uncertain' if uncertain else '#post_point')
        point=el(pm,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{p["lon"]},{p["lat"]},0')
    routes_folder=el(top,'Folder');el(routes_folder,'name','11B 路线｜点击虚线查看逐段km与耗时');el(routes_folder,'open',1)
    measures=el(top,'Folder',id='post_measures');el(measures,'name','11C 分段距离文字｜默认隐藏，可单独开启');el(measures,'visibility',0);el(measures,'open',0)
    for route in cfg['routes']:
        edges=list(zip(route['ids'],route['ids'][1:]));total=sum(km(places[a],places[b]) for a,b in edges)
        body='<h3>'+html.escape(route['name'])+'</h3><p>'+html.escape(route['note'])+'</p><p><b>耗时：</b>'+html.escape(route['timing'])+'</p>'
        if route['id']=='north': body+=route_check_html()
        body+='<h3>逐段直距与耗时</h3>'
        for a,b in edges: body+=f'<p><b>{html.escape(places[a]["name"])} → {html.escape(places[b]["name"])}：直线约{km(places[a],places[b]):.0f} km</b><br/>{html.escape(edge_time(cfg,a,b))}</p>'
        body+='<p>所选相邻点直距之和约'+f'{total:.0f}'+' km。'+DISTANCE_NOTE+'</p><p><a href="'+route['source']+'">文字依据</a></p>'
        pm=el(routes_folder,'Placemark',id='post_route_'+route['id']);el(pm,'name',route['name']+f'｜节点直距和约{total:.0f} km');el(pm,'description',body);view(pm,96.5,30.8,1200000);el(pm,'styleUrl','#post_line_'+route['id']);mg=el(pm,'MultiGeometry')
        for i,(a,b) in enumerate(edges):
            pa,pb=places[a],places[b];distance=km(pa,pb);count=max(2,math.ceil(distance/6))
            for j in range(count):
                t0=j/count;t1=(j+0.52)/count
                ls=el(mg,'LineString');el(ls,'tessellate',1);el(ls,'altitudeMode','clampToGround')
                el(ls,'coordinates',' '.join(f'{pa["lon"]+(pb["lon"]-pa["lon"])*t:.6f},{pa["lat"]+(pb["lat"]-pa["lat"])*t:.6f},0' for t in [t0,t1]))
            label=el(measures,'Placemark',id=f'post_measure_{route["id"]}_{i}');el(label,'name',f'{pa["name"].split("〔")[0]}→{pb["name"].split("〔")[0]} 直约{distance:.0f} km'+('｜1日' if (a,b)==('kangding','zheduo') else ''));el(label,'description',body);el(label,'styleUrl','#post_measure')
            pt=el(label,'Point');el(pt,'coordinates',f'{(pa["lon"]+pb["lon"])/2},{(pa["lat"]+pb["lat"])/2},0')
    region=el(top,'Folder');el(region,'name','11D 三十九族｜现代三县核心方位参照，非史界');el(region,'open',0)
    features=json.loads((DATA/'hor39_admin_reference.geojson').read_text())['features']
    pm=el(region,'Placemark',id='post_hor39_reference');el(pm,'name','三十九族〔丁青—巴青—索县核心方位参照〕')
    el(pm,'description','<p>三十九族是历史部落地区，不是单一城市。用丁青、巴青、索县现代县域作核心方位参照，非完整1909史界，亦不倒套1950年代后十宗范围。</p><p>作者逐站行迹未知，未把这些县城接入行军线；不算到三县中心的距离。恩达北进、经类乌齐到三十九族境内记20余日，起算未精确明定；恩达至拉里月余含这一段。</p><p>几何来自DataV行政数据，推定GCJ02逆算近似WGS84，不能当测绘界线。</p><p><a href="https://www.nopss.gov.cn/GB/219506/219507/15272608.html">清代三十九族研究</a> · <a href="https://dingqing.changdu.gov.cn/dqx/c105853/202005/a735ff9a141c461790b6d3402c4d5fa5.shtml">丁青历史沿革</a></p>')
    view(pm,94.6,31.8,450000);el(pm,'styleUrl','#post_hor39');mg=el(pm,'MultiGeometry')
    for f in features:
        for rings in polygons(f['geometry']): polygon(mg,rings,el)
    notes=el(top,'Folder');el(notes,'name','11E 耗时总览、原文与校注说明');el(notes,'open',0)
    for i,t in enumerate(cfg['timings']):
        pm=el(notes,'Placemark',id=f'post_time_{i}');el(pm,'name',timing_endpoint(t,'from',places)+' → '+timing_endpoint(t,'to',places)+'｜'+t['time']);el(pm,'description',f'<p>{html.escape(t["basis"])}</p><p>{html.escape(t["kind"])}</p>')
    pm=el(notes,'Placemark');el(pm,'name',cfg['historical_comparison']['label']);el(pm,'description','<p>'+cfg['historical_comparison']['text']+'</p><a href="'+cfg['historical_comparison']['source']+'">历史行旅对照来源</a>')
    add_changba_check(top,el,view)
    check=el(top,'Folder',id='annotation10_check');el(check,'name','11G 校注十｜大金寺—甑科—麦学—八邦寺—同普');el(check,'open',0)
    pm=el(check,'Placemark',id='annotation10_overview');el(pm,'name','甘孜至昌都路线核对｜卡工以西需野宿三日〔校注〕');el(pm,'description',route_check_html());view(pm,98.8,31.5,430000)
    for i,item in enumerate(CHECK['unlocated']):
        pm=el(check,'Placemark',id=f'annotation10_unlocated_{i}');el(pm,'name',item['name']+'【未定位，不造点】');el(pm,'description','<p>'+html.escape(item['note'])+'</p>'+route_check_html())
    return cfg

def write_post_indexes():
    cfg,places=load()
    check=place_check();a=check['historical_place'];b=check['modern_comparison']
    explanation='长坝春与新都桥核对\n核对日期：'+check['checked_at']+'\n\n'+check['conclusion']+f'\n\n图示长坝春/江巴村地区点：{a["lon"]}, {a["lat"]}。\n新都桥OSM镇区代表点：{b["lon"]}, {b["lat"]}。\n两点球面近似直距约{km(a,b):.0f} km。'+check['distance_note']+'\n\n11F显示现代新都桥点和位置比较虚线；比较线不接入作者行程。主图与南北驿路补充图的长坝春点均保留江巴村地区参照，更新证据与精度说明。\n\n'
    explanation+='\n\n'.join(e['title']+'\n'+e['supports']+'\n'+e['url'] for e in check['evidence'])
    explanation+='\n\n新都桥点来源：'+b['source']+'\n数据原更新时间：'+b['source_timestamp']+'\n'+check['attribution']+'\n'
    (ROOT/'长坝春新都桥核对说明.txt').write_text(explanation)
    with (ROOT/'南北驿路_地点距离耗时.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['路线','起点','终点','直距_km','相邻段耗时','整段耗时说明','距离口径'])
        for route in cfg['routes']:
            for a,b in zip(route['ids'],route['ids'][1:]): w.writerow([route['name'],places[a]['name'],places[b]['name'],round(km(places[a],places[b])),edge_time(cfg,a,b),route['timing'],DISTANCE_NOTE])
        for t in cfg['timings']: w.writerow(['耗时总览',timing_endpoint(t,'from',places),timing_endpoint(t,'to',places),round(km(places[t['from']],places[t['to']])) if t['from'] and t['to'] else '',t['time'],t['basis'],DISTANCE_NOTE])
    with (ROOT/'南北驿路_地名坐标.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['id','name','lon','lat','certainty','source','identity_source','note'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(cfg['places'])
    guide='''《艽野尘梦》本段南北驿路对照
核对日期2026-10-31。
“艽野尘梦_南北驿路对照.kmz”可单独看本段全部17个地点及三十九族方位范围；新版完整阅读地图中的11层只新增6个点，复用已有地点，避免重复标注。
橙色南路是背景对照，不表示作者亲经全程；蓝色北路经昌都，紫色为昌都后北绕；灰色为原文另列走法，不当作者本次绕过昌都。
所有路线为断续虚线，只连接主要地名，不是完整驿站、现代公路或古道轨迹。
距离为代表点间直距km，分段合计不等于实走路程。曾科/甑科对应赠科乡是推定；丹达用村域地区参照，未定位山口和旧站址。
“巴、里塘”并称按地理顺序画理塘→巴塘；南路西段不套今G318经波密林芝线。
三十九族不是一座城。图取丁青/巴青/索县现代范围作核心方位参照，不冒认1909年完整史界。区域内部路线留白；类乌齐至拉里只有起讫直距。
康定至折多塘1日；折多塘至甘孜一带20余日；炉城至昌都正文50余日被校注10质疑，校注另估常规17日、加停留约23—30日，不能合并成可靠区间。
恩达北进经类乌齐至三十九族境内20余日的精确起算未另明；恩达到拉里月余包含这一段，不能相加或按距离分配。
拉里到江达据后文行军分日约3日；南路其余逐站日数未明。荒僻“一二日无人烟”不等于各站走一二日。
有泰约两个半月到拉萨仅为另年另人行旅对照，公文接力约11日也不是军队行程。
开启11C可显示分段km文字；点击地点或路线可读距离与已知耗时。数据及逐点来源在data/postroads/南北驿路.json，CSV可直接查阅。
11F另加新都桥现代对照点及约23 km位置比较线，不属于上述17个历史站点代表点，也不接入作者路线。长坝春保留江巴村一带，详见长坝春新都桥核对说明.txt。
2026-10-31完整阅读地图已导入原Google Earth网页版项目并保存到云端。此前南北驿路版已抽查北路弹窗7 km/1日、32 km及162 km等分段文字；为适配网页版，分段内容使用逐条文字。仅Region、maxLines、textColor显示字段被忽略。
'''
    guide=guide.replace('全部17个地点',f'全部{len(places)}个地点').replace('新增6个点',f'新增{sum(not p["existing"] for p in places.values())}个点').replace('上述17个历史站点代表点','上述地点代表点')
    guide+='\n校注十路线核对\n'+CHECK['text_sequence']+'\n'+CHECK['timing_note']+'\n11G有路线核对和未定位地名文字条目；主图R1与本层北路使用同一节点顺序。详见甘孜昌都路线校对说明.txt。\n'
    (ROOT/'南北驿路说明.txt').write_text(guide+'\n原文与校注\n'+cfg['source']+'\n')
