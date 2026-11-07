"""Annotation 11: known geographic references and a separate, non-metric topology."""
from pathlib import Path
import csv
import html
import json
import math
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/annotation11'
APPROX_IDS = ('suoluoba', 'jiamuqiao', 'nagongtang')
APPROX_NOTE = '橙色空心点是按旧地名相对顺序与现代谷地方位设置的阅读示意中心，古今对应及旧址仍未考定。参考圈仅提示查找尺度，不是历史边界、统计误差范围或旧址必在圈内的保证。'


def load():
    cfg=json.loads((DATA/'校注十一地图核对.json').read_text())
    text=json.loads((DATA/'探险文字核对.json').read_text())
    scan=json.loads((DATA/'书图识读.json').read_text())
    return cfg,text,scan,{p['id']:p for p in cfg['places']}


def km(a,b):
    x1,y1,x2,y2=map(math.radians,[a['lon'],a['lat'],b['lon'],b['lat']])
    h=math.sin((y2-y1)/2)**2+math.cos(y1)*math.cos(y2)*math.sin((x2-x1)/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(h)))


def label(value,places):
    if value in places: return places[value]['name']
    for key in sorted(places,key=len,reverse=True):
        value=value.replace(key,places[key]['name'])
    return value


def paragraph(text):
    return '<p>'+html.escape(text)+'</p>'


def approximate_body(item):
    body=(paragraph('大概位置／推定，非旧址确点。')
            +paragraph(item['placement_basis'])
            +paragraph(f'阅读示意中心：{item["lon"]}°E，{item["lat"]}°N。')
            +paragraph(APPROX_NOTE)
            +paragraph(f'可开关参考圈半径约{item["reference_radius_km"]:g} km，按阅读展示选定，不参与古道里程或耗时计算。'))
    body+=paragraph('依据：任乃强校注十一给出的地名顺序与方位；现代G214/G317走廊仅辅助判断谷地方向，不代表旧道。')
    if item['id']=='nagongtang':
        body+='<p><a href="https://www.tibetcul.com/zhuanti/whzt/48256.html">柔克义路线研究</a>：下拉位于滨达以东约2公里的线索，不能单独证明纳贡塘＝下拉。</p>'
    return body


def approximate_style(p,el,bundled):
    style=el(p,'Style');icon=el(style,'IconStyle')
    if not bundled: el(icon,'color','ff47b3ff')
    el(icon,'scale',1.25)
    image=el(icon,'Icon');el(image,'href','icons/annotation11_approximate.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/open-diamond.png')
    labels=el(style,'LabelStyle');el(labels,'scale',1.0)


def add_approximate_ranges(parent,el,view,places):
    folder=el(parent,'Folder',id='annotation11_approximate_ranges')
    el(folder,'name','14G 三处大概位置参考圈｜可开关，非考定边界');el(folder,'visibility',0);el(folder,'open',0)
    el(folder,'description',paragraph(APPROX_NOTE))
    view(folder,96.766,31.12,45000)
    for key in APPROX_IDS:
        item=places[key]
        p=el(folder,'Placemark',id='annotation11_range_'+key)
        el(p,'name',item['name']+'〔方位参考圈，约3km〕');el(p,'description',approximate_body(item))
        style=el(p,'Style');line=el(style,'LineStyle');el(line,'color','b347b3ff');el(line,'width',1.5)
        poly=el(style,'PolyStyle');el(poly,'color','1247b3ff')
        polygon=el(p,'Polygon');el(polygon,'tessellate',1);el(polygon,'altitudeMode','clampToGround')
        ring=el(el(polygon,'outerBoundaryIs'),'LinearRing')
        lon,lat=map(math.radians,[item['lon'],item['lat']]);distance=item['reference_radius_km']/6371.0088
        coords=[]
        for index in range(73):
            bearing=-2*math.pi*index/72
            y=math.asin(math.sin(lat)*math.cos(distance)+math.cos(lat)*math.sin(distance)*math.cos(bearing))
            x=lon+math.atan2(math.sin(bearing)*math.sin(distance)*math.cos(lat),math.cos(distance)-math.sin(lat)*math.sin(y))
            coords.append(f'{math.degrees(x):.6f},{math.degrees(y):.6f},0')
        coords[-1]=coords[0]
        el(ring,'coordinates',' '.join(coords))
    return folder


def add_approximate_places(doc,el,view,bundled=False):
    _,_,_,places=load()
    for key in APPROX_IDS:
        item=places[key]
        p=el(doc,'Placemark',id='annotation11_place_'+key)
        el(p,'name',item['map_label']);el(p,'description',approximate_body(item)+paragraph('别名／正文原名：'+'、'.join(item['aliases'])))
        view(p,item['lon'],item['lat'],30000);approximate_style(p,el,bundled)
        point=el(p,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{item["lon"]},{item["lat"]},0')
    add_approximate_ranges(doc,el,view,places)


def distance_body(cfg,text,places):
    body='<h3>距离：原书里数与现代直距分栏</h3>'+paragraph(cfg['distance_policy'])
    for claim in text['distance_claims']:
        via=('（经'+'、'.join(label(v,places) for v in claim['via'])+'）') if claim['via'] else ''
        body+=paragraph(claim['source']+'：'+label(claim['from'],places)+' → '+label(claim['to'],places)+via+'｜'+claim['original_li']+'。'+claim['note'])
    body+='<h3>现代地区代表点间直距（km）</h3>'
    for a,b in cfg['known_distance_pairs']:
        body+=paragraph(places[a]['name']+' → '+places[b]['name']+f'：约{km(places[a],places[b]):.0f} km。')
    return body+paragraph('这些km只用于位置比较，不是古道里程，不计入全书实走总程。三个大概位置只显示示意中心，不加入距离表；其他未定位旧地名的经纬度与km留空。')


def overview(cfg,text,scan,places):
    body='<h3>校注十一与书中略图：昌都—恩达</h3>'+paragraph(cfg['claim'])
    body+=paragraph('书图地点顺序：'+' → '.join(places[p]['name'] for p in cfg['main_sequence']))
    body+=paragraph('腊左塘＝浪荡沟；腊左＝纳贡塘；腊左山／腊左大山＝纳贡山。三者分别处理，不放在同一坐标。')
    body+=paragraph(cfg['method'])
    body+=paragraph(cfg['map_point_policy'])
    body+=paragraph(APPROX_NOTE)
    body+='<h3>桥名图文差异</h3>'+paragraph(cfg['bridge_conflict'])
    total=next(t for t in text['timing_claims'] if t['id']=='outing_total_inferred')
    body+='<h3>耗时</h3>'+paragraph(total['time']+'〔推算〕。'+total['basis'])
    body+=paragraph('第三日午前十时到恩达，午后一时启返，晚十二时回昌都；时刻差不是连续行走的实测用时。堪布“三日撤兵”承诺与此处推算、校注十“野宿三日”是三个不同事项。')
    body+='<h3>书图与现代地图的关系</h3>'+paragraph(cfg['first_map_note'])
    body+=paragraph('14B保留其他无坐标旧地名的文字条目；梭罗坝、甲木桥、纳贡塘已按用户要求补大概位置。离开昂曲翻山进入恩达河谷的方向关系，不用今日G317代替旧道。')
    body+='<h3>依据</h3>'
    for s in cfg['sources']:
        name=html.escape(s['title'])
        if s['url']: name='<a href="'+html.escape(s['url'],quote=True)+'">'+name+'</a>'
        body+='<p>'+name+'<br/>'+html.escape(s['use'])+'</p>'
    return body


def unlocated_entries():
    cfg,_,_,_=load()
    return [('第2章；校注十一及书图',p['name']+('／'+'／'.join(p['aliases']) if p['aliases'] else ''),p['status']+'。'+p['role']) for p in cfg['places'] if not p['mapped']]


def add_annotation11(doc,el,view,bundled=False,include_anchors=False):
    cfg,text,scan,places=load();body=overview(cfg,text,scan,places)
    top=el(doc,'Folder',id='annotation11');el(top,'name','14 腊左探险｜校注十一与书中略图');el(top,'open',1);el(top,'description',body)
    view(top,96.92,31.16,155000)
    intro=el(top,'Folder',id='annotation11_intro');el(intro,'name','14A 核对总览｜确曾抵达恩达，桥名保留图文差异');el(intro,'open',1)
    p=el(intro,'Placemark',id='annotation11_overview');el(p,'name','昌都—恩达探险｜约3日2夜〔分日推算〕');el(p,'description',body);view(p,96.92,31.16,155000)
    count=sum(p['mapped'] and not p.get('approximate') for p in cfg['places'])
    approx_count=sum(bool(p.get('approximate')) for p in cfg['places'])
    ordered=el(top,'Folder',id='annotation11_places');el(ordered,'name',f'14B 地点顺序｜{count}处地区参照＋{approx_count}处大概位置');el(ordered,'open',1)
    el(ordered,'description',paragraph(cfg['map_point_policy']))
    extras=el(top,'Folder',id='annotation11_context');el(extras,'name','14C 书图旁支、事件与山河背景｜不强接主链');el(extras,'open',0)
    order={key:i+1 for i,key in enumerate(cfg['main_sequence'])}
    for item in cfg['places']:
        key=item['id'];parent=ordered if key in order else extras
        p=el(parent,'Placemark',id='annotation11_place_'+key)
        prefix=f'{order[key]:02d} ' if key in order else ''
        el(p,'name',prefix+(item.get('map_label',item['name']) if item['mapped'] else item['name']+'【无坐标】'))
        detail='<h3>'+html.escape(item['name'])+'</h3>'
        if item['aliases']: detail+=paragraph('别名／正文原名：'+'、'.join(item['aliases']))
        detail+=paragraph('定位性质：'+item['status'])+paragraph(item['role'])
        if item.get('identity_basis'): detail+=paragraph(item['identity_basis'])
        if item.get('approximate'):
            detail+=approximate_body(item)
        elif item['mapped']:
            detail+=paragraph('沿用的现代定位对象：'+item['modern']+f'。经度{item["lon"]}，纬度{item["lat"]}；不是旧桥、营地或汛署确址。')
            detail+='<p><a href="'+html.escape(item['coordinate_source'],quote=True)+'">现代坐标来源</a></p>'
            detail+='<h3>与本段其他已定位点的直距（km）</h3>'
            for a,b in cfg['known_distance_pairs']:
                if key in (a,b):
                    other=places[b if key==a else a]
                    detail+=paragraph('至'+other['name']+f'代表点：约{km(item,other):.0f} km；非古道实走里程。')
        else:
            detail+=paragraph('没有赋予经纬度或测距。打开此文字条目只查看全段方位，不代表已定位到该旧站。')
        for claim in text['distance_claims']:
            if key in [claim['from'],claim['to'],*claim['via']]:
                detail+=paragraph(claim['source']+'：'+label(claim['from'],places)+' → '+label(claim['to'],places)+'｜'+claim['original_li']+'。'+claim['note'])
        detail+=body
        el(p,'description',detail)
        view(p,item['lon'] if item['mapped'] else 96.92,item['lat'] if item['mapped'] else 31.16,70000 if item['mapped'] else 155000)
        if item['mapped'] and include_anchors:
            el(p,'visibility',1)
            # KML Feature order puts visibility before description and view.
            visibility=p[-1];p.remove(visibility);p.insert(1,visibility)
            if item.get('approximate'): approximate_style(p,el,bundled)
            else: el(p,'styleUrl','#minor_reference')
            point=el(p,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{item["lon"]},{item["lat"]},0')
            # In the full map, keep the original chapter entry as a text card,
            # and put the only physical marker in the ordered expedition layer.
            ns=doc.tag.rsplit('}',1)[0]+'}'
            legacy=doc.find('.//'+ns+'Placemark[@id="'+item['legacy_placemark_id']+'"]') if item.get('legacy_placemark_id') else None
            if legacy is not None:
                old_point=legacy.find(ns+'Point')
                if old_point is None:
                    raise ValueError('Missing existing reference point: '+item['id'])
                old_coords=old_point.findtext(ns+'coordinates').split(',')
                assert abs(float(old_coords[0])-item['lon'])<0.00001 and abs(float(old_coords[1])-item['lat'])<0.00001
                legacy.remove(old_point)
                old_description=legacy.find(ns+'description')
                p.find(ns+'description').text+='<h3>原章节条目的耗时、距离与依据</h3>'+old_description.text
                old_description.text=paragraph('本地点的地图点已集中至「14B 地点顺序」。本条保留原章节说明；双击仍可定位到同一现代参照地区。')+old_description.text
                legacy.find(ns+'name').text+='〔点标见14B〕'
    notes=el(top,'Folder');el(notes,'name','14D 原书里数、直距km与行程分日');el(notes,'open',0)
    p=el(notes,'Placemark',id='annotation11_distances');el(p,'name','里数分源保留；现代起讫直距约'+f'{km(places["chamdo"],places["enda"]):.0f}'+' km');el(p,'description',distance_body(cfg,text,places));view(p,96.92,31.16,155000)
    for i,event in enumerate(text['chronology']):
        p=el(notes,'Placemark',id='annotation11_time_'+str(i));el(p,'name',f'{i+1:02d} '+event['relative_day']+'｜'+event['phase']);el(p,'description',paragraph(event['event'])+paragraph(event['evidence_status']))
    p=el(notes,'Placemark');el(p,'name','“旧作两站”及“三日撤兵”不能当行军用时');el(p,'description',paragraph(text['timing_claims'][-1]['basis'])+paragraph(next(t['basis'] for t in text['timing_claims'] if t['id']=='tibetan_troop_withdrawal_promise')))
    evidence=el(top,'Folder');el(evidence,'name','14E 两张书图原件与识读限制');el(evidence,'open',0)
    for i,source in enumerate(cfg['scans']):
        p=el(evidence,'Placemark',id='annotation11_scan_'+str(i));el(p,'name',source['title'])
        src=source['external_url']
        text_body=paragraph(cfg['first_map_note'] if i==0 else '原照片侧置，已另附可转正阅读的HTML对读页。两图无可靠经纬网及比例尺，均未作地理配准。')
        text_body+='<p><img style="max-width:100%;height:auto" src="'+src+'" alt="'+html.escape(source['title'],quote=True)+'"/></p>'
        text_body+=paragraph('Google Earth网页版原图需联网。图片无法显示时，可查看本地昌都恩达_校注十一对读.html及data/annotation11/scans/原图。')
        el(p,'description',text_body+body);view(p,96.92,31.16,155000)
    add_deep_research(top,el,view,False)
    add_approximate_ranges(top,el,view,places)
    return cfg


def add_deep_research(parent,el,view,include_langda=False):
    research=json.loads((DATA/'三地深查.json').read_text())
    folder=el(parent,'Folder',id='annotation11_deep_research');el(folder,'name','14F 三地深查｜浪荡沟落实，纳贡山候选，纳贡塘旧址待考');el(folder,'open',1)
    el(folder,'description',paragraph(research['summary'])+paragraph('金色点为现代地区参照，橙色较大空心点为候选山口；二者证据等级不同。'))
    view(folder,96.91,31.16,110000)
    refs='<h3>核对资料</h3>'+''.join('<p><a href="'+html.escape(s['url'],quote=True)+'">'+html.escape(s['title'])+'</a>：'+html.escape(s['use'])+'</p>' for s in research['sources'])
    if include_langda:
        item=research['langdanggou']
        p=el(folder,'Placemark',id='deep_langdanggou');el(p,'name','浪荡沟〔今朗达村地区参照〕');el(p,'description',paragraph(item['certainty'])+paragraph(item['conclusion'])+refs);view(p,item['lon'],item['lat'],55000);el(p,'styleUrl','#minor_reference')
        point=el(p,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{item["lon"]},{item["lat"]},0')
    item=research['nagongshan']
    p=el(folder,'Placemark',id='deep_nagongshan_candidate');el(p,'name',item['label']);el(p,'description',paragraph(item['certainty'])+''.join(paragraph(s) for s in item['basis'])+paragraph(item['limit'])+refs);view(p,item['lon'],item['lat'],80000)
    style=el(p,'Style')
    icon=el(style,'IconStyle');el(icon,'color','ff00a5ff');el(icon,'scale',1.35);image=el(icon,'Icon');el(image,'href','https://maps.google.com/mapfiles/kml/shapes/open-diamond.png')
    labels=el(style,'LabelStyle');el(labels,'scale',1.0)
    point=el(p,'Point');el(point,'altitudeMode','clampToGround');el(point,'coordinates',f'{item["lon"]},{item["lat"]},0')
    item=research['nagongtang']
    p=el(folder,'Placemark',id='deep_nagongtang_research');el(p,'name','纳贡塘｜旧址待考，另附大概位置');el(p,'description',paragraph(item['certainty'])+''.join(paragraph(s) for s in item['basis'])+paragraph(item['limit'])+paragraph('大概位置点见新版14B，或独立“恩达河谷三处约位”补充图；本研究卡片不另造重复点。')+refs);view(p,96.825,31.113,45000)
    report='三地深查：浪荡沟、纳贡山、纳贡塘\n核对日期：'+research['checked_at']+'\n\n'+research['summary']+'\n\n'
    report+='浪荡沟\n'+research['langdanggou']['conclusion']+'\n\n'
    for key in ['nagongshan','nagongtang']:
        item=research[key];report+=key+'｜'+item['certainty']+'\n'+'\n'.join(item['basis'])+'\n'+item['limit']+'\n\n'
    report+='来源\n'+'\n\n'.join(s['title']+'\n'+s['url']+'\n'+s['use'] for s in research['sources'])+'\n'
    (output_path('docs', '浪荡沟纳贡三地深查说明.txt')).write_text(report)
    return folder


def write_annotation11_indexes():
    cfg,text,scan,places=load()
    with (output_path('tables', '昌都恩达_校注十一地名.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['ID','书图主链顺序','名称','别名／正文原名','定位性质','地图显示经度','地图显示纬度','人物／路径性质','坐标来源','是否大概位置','展示参考圈半径_km','约位依据'])
        for p in cfg['places']:
            writer.writerow([p['id'],cfg['main_sequence'].index(p['id'])+1 if p['id'] in cfg['main_sequence'] else '',p['name'],'；'.join(p['aliases']),p['status'],p.get('lon',''),p.get('lat',''),p['role'],p.get('coordinate_source',''),'是，阅读示意中心' if p.get('approximate') else '',p.get('reference_radius_km',''),p.get('placement_basis','')])
    with (output_path('tables', '昌都恩达_校注十一距离耗时.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['类别','依据','起点','终点','经由','原书里数','现代直距_km','耗时或时刻','性质与限制'])
        for d in text['distance_claims']:
            writer.writerow(['原书距离',d['source'],label(d['from'],places),label(d['to'],places),'；'.join(label(v,places) for v in d['via']),d['original_li'],'','',d['note']])
        for a,b in cfg['known_distance_pairs']:
            writer.writerow(['现代代表点直距','既有地区坐标',places[a]['name'],places[b]['name'],'','',round(km(places[a],places[b])),'',cfg['distance_policy']])
        for t in text['timing_claims']:
            writer.writerow(['耗时／时刻',t['source'],label(t.get('from') or t.get('place',''),places),label(t.get('to') or '',places),'','','',t.get('time') or t.get('original_post_stages'),t['status']+'；'+t['basis']])
    notes='校注十一与书图地图校对\n核对日期：'+cfg['checked_at']+'\n\n'+cfg['claim']+'\n\n'
    notes+='主链（书图顺序，不编码地理距离）\n'+' → '.join(places[p]['name'] for p in cfg['main_sequence'])+'\n\n'
    notes+=cfg['method']+'\n\n'+cfg['bridge_conflict']+'\n\n'+cfg['first_map_note']+'\n\n'+cfg['distance_policy']+'\n\n'
    for p in cfg['places']: notes+=p['name']+'｜'+p['status']+'\n'+p['role']+'\n\n'
    notes+='行程分日\n'+'\n'.join(t['relative_day']+'｜'+t['phase']+'：'+t['event']+' '+t['evidence_status'] for t in text['chronology'])+'\n\n'
    notes+=cfg['map_point_policy']+'\n'+APPROX_NOTE+'\n完整阅读地图与独立艽野尘梦_腊左探险校对.kmz均在14B显示四处地区参照与三处大概位置，14G有默认关闭的三个参考圈；二者选一导入。旧云端地图可仅叠加“艽野尘梦_恩达河谷三处约位.kmz”，勿与新版完整图重复显示。\n昌都恩达_校注十一顺序图.svg与对读HTML为非地理配准的顺序图；原书照片原字节保存在data/annotation11/scans/。\n\n'
    notes+=cfg['scan_display_note']+'\n\n'
    notes+='来源\n'+'\n\n'.join(s['title']+'\n'+s['use']+'\n'+s['url'] for s in cfg['sources'])+'\n'
    (output_path('docs', '校注十一地图校对说明.txt')).write_text(notes)
