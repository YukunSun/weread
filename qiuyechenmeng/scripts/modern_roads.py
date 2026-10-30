"""Modern road comparison layer, sourced from cached OpenStreetMap geometry."""
from pathlib import Path
import csv
import html
import json
import math
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
OSM = 'https://www.openstreetmap.org/copyright'
NATIONAL = 'https://www.ndrc.gov.cn/xxgk/zcfb/ghwb/202207/P020220712348051707026.pdf'
NOTE = ('现代道路仅供与历史行进方向对照。实线来自OpenStreetMap已有道路几何，'
        '采用WGS84，经裁剪及约30米容差简化；数据缺口保留，不直连补路。'
        '路号结合交通部门资料核对；地图收录、规划编号不等于当前全部通车。'
        '历史虚线仅为地点顺序示意，不能据两线接近认定古今同道。')

# Bounding boxes are south, west, north, east. Targets only choose label anchors
# from the road's actual coordinates; they never supply line geometry.
ROADS = [
    dict(ref='G317', title='炉霍—甘孜—德格—江达—昌都—类乌齐', color='#ffce54',
         box=[30.75,96.2,32.5,100.85], targets=[[100.25,31.58],[98.9,31.9],[97.8,31.3],[97.05,31.18],[96.55,31.15]],
         note='今川藏北线。作者甘孜之后经麦宿、八邦寺一带，并非自动沿今日雀儿山隧道—德格县城段。昌都—类乌齐走廊有G214并行或共线标识；俄洛桥的历史桥址仍待考。',
         sources=[NATIONAL,'https://lyfz.changdu.gov.cn/cdslyj4/c101252/202503/085ff666427c4c8ebe6de8e1f19a5197.shtml']),
    dict(ref='G350', title='八美—道孚—炉霍', color='#fa81e5',
         box=[30.35,100.55,31.5,101.75], targets=[[101.45,30.55],[101.12,30.97],[100.8,31.28]],
         note='八美—道孚—炉霍的现行国道编号为G350。道孚县规划记旧S303升级为G350，此段不统标为G317。',
         sources=['https://www.gzdf.gov.cn/fzgh/article/520915','https://www.gzdf.gov.cn/fzgh/article/520470']),
    dict(ref='G248', title='新都桥—塔公—八美', color='#65dbff',
         box=[29.95,101.2,30.6,101.85], targets=[[101.5,30.06],[101.5,30.3],[101.5,30.46]],
         note='现代新都桥—八美通道，旧S215升级编号。与康定出发、途经折多塘和长坝春的旧程不能直接等同。',
         sources=['https://www.gzdf.gov.cn/fzgh/article/520915','https://www.gzdf.gov.cn/fzgh/article/520470']),
    dict(ref='S434', title='康定—木格措—红海子—塔公', color='#b5fa74',
         box=[29.85,101.35,30.5,102.15], targets=[[101.91,30.12],[101.69,30.31]],
         note='塔北路，经木格措、红海子及康定机场分路口，是现代方向参照；与G318折多山路线分别显示。',
         sources=['https://wlt.xizang.gov.cn/xwzx_69/xydt/202206/t20220627_305027.html']),
    dict(ref='G108', title='雅安—荥经—汉源方向', color='#d8d8d8',
         box=[29.2,102.45,30.1,103.15], targets=[[102.85,29.8],[102.6,29.5]],
         note='供对照雅安经荥经、清溪的南向走廊。现代泥巴山道路不等于作者所越的大相岭旧山口。S435飞越岭新建段2026仍列续建，不据规划补画已通实线。',
         sources=[NATIONAL,'https://www.yaan.gov.cn/gongkai/show/66e81e11d2770308c603ad0a9e7e5d8c.html']),
    dict(ref='G318', title='雅安—康定—芒康—邦达—波密—工布江达', color='#ff964a',
         box=[28.8,92.8,31.0,103.15], targets=[[102.7,30.0],[102.2,29.95],[101.65,30.02],[97.0,30.0],[96.5,29.5],[95.75,29.85],[95.06,30.09],[94.73,29.73],[93.3,29.9]],
         note='东段雅安经天全、二郎山到泸定，与书中经清溪、飞越岭的古道明显不同。西段是波密—通麦—鲁朗—林芝—太昭周边的现代对照，非作者完整个人行程。',
         sources=[NATIONAL,'https://wlj.linzhi.gov.cn/lzslyfzwyh/c103820/202401/1e7571fb9481402b876fcf2bcb42fdef.shtml','https://jtt.xizang.gov.cn/bsfw/xyfw/202401/t20240104_396606.html']),
    dict(ref='G214', title='类乌齐／昌都—邦达', color='#66e3bb',
         box=[30.0,96.25,31.65,97.85], targets=[[96.65,31.2],[97.05,31.18],[97.25,30.7],[97.25,30.3]],
         note='连接昌都G317与邦达G318。俄洛桥至昌都的现代道路工程沿昂曲；新旧桥位置不认定相同。2025年开工的加卡—机场新通道不作为既有道路补画。',
         sources=['https://leiwuqi.changdu.gov.cn/lwqxrmzf/c102126/201905/81837f0bcc83487da0c376a7bd0da5e0.shtml','https://www.xizang.gov.cn/zwgk/xxgk_424/zxxxgk/201902/W020190223643737803015.pdf','https://jtj.changdu.gov.cn/cdsjtysj/c102827/202506/77aef0442df34d80a6851085602bc81a.shtml']),
    dict(ref='G349', title='边坝—尼屋—嘉黎周边', color='#8bb0ff',
         box=[30.1,92.8,31.25,95.3], targets=[[94.7,30.8],[93.8,30.7],[93.2,30.7]],
         note='现代嘉黎周边东西通道，不能替代书中类乌齐至拉里的未知逐站旧路。书中拉里使用嘉黎旧镇参照，与现代阿扎县城有别。',
         sources=['https://jtt.xizang.gov.cn/xxgk/fdzdgknr/zbgg/202207/t20220705_309421.html','https://jtt.xizang.gov.cn/xxgk/tzgg/202510/t20251024_505920.html']),
    dict(ref='S303', title='易贡—八盖—尼屋方向（已有数据段）', color='#b5fa74',
         box=[29.95,94.35,30.9,95.2], targets=[[94.83,30.25],[94.7,30.5]],
         note='现行S303易贡茶厂—八盖段有2026养护公告。旧资料曾将嘉黎—通麦走廊称S305，不能整体照抄旧编号。未建段及OSM空白不连接。',
         sources=['https://jtt.xizang.gov.cn/xxgk/fdzdgknr/zbgg_4482/202605/t20260520_541055.html','https://epaper.ceic.com/pc/content/202407/17/content_5673.html']),
    dict(ref='S205', title='太昭—娘蒲方向（已有数据段）', color='#b5fa74',
         box=[29.95,92.8,30.58,93.5], targets=[[93.08,30.05],[93.05,30.3]],
         note='娘蒲—太昭接G318段有2026养护公告。OSM该走廊仍有S303旧编号，未确认可采用的独立S205几何时仅保留说明，不改号拼接。完整嘉黎—娘蒲—太昭方向曾列升级储备，不凭规划连成全线已通；与拉里退路仅作方向比较。',
         sources=['https://jtt.xizang.gov.cn/xxgk/fdzdgknr/zbgg/202605/t20260529_542775.html','https://jtt.xizang.gov.cn/xxgk/fdzdgknr/rdjyzxtadf/202212/t20221217_333876.html']),
    dict(ref='G109', title='格尔木—都兰—青海湖南—湟源—西宁—兰州', color='#ffb5b9',
         box=[35.65,94.3,37.3,104.05], targets=[[95.4,36.3],[98.0,36.2],[99.9,36.55],[101.15,36.65],[102.4,36.4],[103.4,36.15]],
         note='仅作为柴达木、青海湖南缘至兰州的现代方向参照。陈渠珍荒原段行迹不明，绝不沿G109反画北返轨迹。此图不补画太昭至格尔木现代线路。',
         sources=['https://jtyst.qinghai.gov.cn/jtyst/2026-02/10/baad3a10ce0448359e6dc329c855c519/2026021018083742135.pdf','https://jtys.gansu.gov.cn/jtys/c106393/202303/136380537/files/cf711357f69447de87be8d552a4dcf39.pdf']),
]

def refs(properties):
    values = [properties.get('ref', ''), properties.get('source_relation_refs', properties.get('relation_refs', ''))]
    if isinstance(values[1], list): values[1] = ';'.join(values[1])
    return set(re.findall(r'[GS]\d{3}', ';'.join(str(v) for v in values)))

def clip_segment(a, b, box):
    south, west, north, east = box
    dx, dy = b[0]-a[0], b[1]-a[1]
    lo, hi = 0., 1.
    for p, q in [(-dx,a[0]-west),(dx,east-a[0]),(-dy,a[1]-south),(dy,north-a[1])]:
        if p == 0:
            if q < 0: return None
        else:
            t = q/p
            if p < 0: lo = max(lo,t)
            else: hi = min(hi,t)
            if lo > hi: return None
    return [[round(a[0]+dx*t,7),round(a[1]+dy*t,7)] for t in [lo,hi]]

def clipped_lines(coords, box):
    lines, current = [], []
    for a,b in zip(coords,coords[1:]):
        part = clip_segment(a,b,box)
        if not part:
            if len(current)>1: lines.append(current)
            current=[]
        elif not current or current[-1]==part[0]:
            if not current: current.append(part[0])
            current.append(part[1])
        else:
            if len(current)>1: lines.append(current)
            current=part
    if len(current)>1: lines.append(current)
    return lines

def simplify(coords, tolerance=0.00027):
    """Douglas-Peucker in locally scaled degrees, about 30 m at this latitude."""
    if len(coords)<3: return coords
    scale=math.cos(math.radians(coords[0][1])); a,b=coords[0],coords[-1]
    dx,dy=(b[0]-a[0])*scale,b[1]-a[1]; den=dx*dx+dy*dy
    best,index=0,0
    for i,p in enumerate(coords[1:-1],1):
        px,py=(p[0]-a[0])*scale,p[1]-a[1]
        t=max(0,min(1,(px*dx+py*dy)/den)) if den else 0
        d=math.hypot(px-dx*t,py-dy*t)
        if d>best: best,index=d,i
    if best<=tolerance: return [a,b]
    return simplify(coords[:index+1],tolerance)[:-1]+simplify(coords[index:],tolerance)

def km(a,b):
    x1,y1,x2,y2=map(math.radians,[*a,*b])
    h=math.sin((y2-y1)/2)**2+math.cos(y1)*math.cos(y2)*math.sin((x2-x1)/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(h)))

def load_roads():
    raw=json.loads((ROOT/'data/roads/osm_roads.geojson').read_text())
    output=[]
    for road in ROADS:
        pieces=[]; ids=[]
        for f in raw['features']:
            p=f['properties']
            if road['ref'] not in refs(p): continue
            if p.get('highway') in ['construction','proposed']: continue
            lines=clipped_lines(f['geometry']['coordinates'],road['box'])
            if lines:
                ids.append(p.get('osm_id',f.get('id')))
                pieces.extend(simplify(c) for c in lines)
        output.append(dict(road,lines=pieces,osm_ids=ids))
    return output

def add_roads(doc, el, view, kcolor):
    roads=load_roads()
    styles=[]
    for r in roads:
        st=el(doc,'Style',id='road_'+r['ref']);styles.append(st);line=el(st,'LineStyle')
        el(line,'color',kcolor(r['color']));el(line,'width',4)
        st=el(doc,'Style',id='label_'+r['ref']);styles.append(st);ic=el(st,'IconStyle')
        el(ic,'color',kcolor(r['color']));el(ic,'scale',0.45)
        icon=el(ic,'Icon');el(icon,'href','https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        lab=el(st,'LabelStyle');el(lab,'color',kcolor(r['color']));el(lab,'scale',0.95)
    # Shared styles belong before the Document's child Features in KML 2.2.
    for st in styles: doc.remove(st)
    index=next((i for i,c in enumerate(doc) if c.tag in [f'{{{KML}}}Folder',f'{{{KML}}}Placemark']),len(doc))
    for i,st in enumerate(styles): doc.insert(index+i,st)
    folder=el(doc,'Folder',id='modern_road_folder');el(folder,'name','09 现代国道省道对照｜实线，可单独开关');el(folder,'open',1)
    el(folder,'description','<p>'+NOTE+'</p><p>黄色G317，橙色G318；其余国道分别着色，省道浅绿。点击各路号可看路段和编号依据。</p><p>© OpenStreetMap contributors，ODbL 1.0。核对日期2026-10-30。</p>')
    view(folder,97.07,31.18,160000)
    for r in roads:
        f=el(folder,'Folder',id='modern_'+r['ref']);el(f,'name',r['ref']+' '+r['title']+('〔几何缺失，见说明〕' if not r['lines'] else ''));el(f,'open',0)
        body='<h3>'+r['ref']+' '+html.escape(r['title'])+'</h3><p>'+html.escape(r['note'])+'</p><p>'+NOTE+'</p>'
        body+='<p>路号核实：'+' · '.join(f'<a href="{html.escape(u,quote=True)}">依据{i+1}</a>' for i,u in enumerate(r['sources']))+'</p>'
        body+=f'<p>几何：© <a href="{OSM}">OpenStreetMap contributors</a>，ODbL 1.0；数据提取日期2026-10-30。</p>'
        el(f,'description',body)
        if not r['lines']: continue
        p=el(f,'Placemark',id='modern_line_'+r['ref']);el(p,'name',r['ref']+'｜现代道路实线');el(p,'description',body)
        lon,lat=r['lines'][0][0];view(p,lon,lat,160000);el(p,'styleUrl','#road_'+r['ref']);mg=el(p,'MultiGeometry')
        for coords in r['lines']:
            ls=el(mg,'LineString');el(ls,'tessellate',1);el(ls,'altitudeMode','clampToGround')
            el(ls,'coordinates',' '.join(f'{x:.7f},{y:.7f},0' for x,y in coords))
        used=[]
        allpoints=[c for line in r['lines'] for c in line]
        for i,target in enumerate(r['targets']):
            chosen=min(allpoints,key=lambda c:km(c,target))
            if km(chosen,target)>80 or any(km(chosen,old)<20 for old in used): continue
            used.append(chosen)
            p=el(f,'Placemark',id=f'modern_label_{r["ref"]}_{i}');el(p,'name',r['ref']);el(p,'description',body)
            view(p,*chosen,100000);el(p,'styleUrl','#label_'+r['ref'])
            pt=el(p,'Point');el(pt,'altitudeMode','clampToGround');el(pt,'coordinates',f'{chosen[0]},{chosen[1]},0')
    return roads

def write_road_index(roads):
    with (ROOT/'现代道路对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['路号','所选方向','数据状态','OSM道路段数','所绘线段长度合计_km','限制说明','路号依据','几何来源'])
        for r in roads:
            length=sum(km(a,b) for line in r['lines'] for a,b in zip(line,line[1:]))
            w.writerow([r['ref'],r['title'],'有几何' if r['lines'] else '无几何，仅有说明',len(r['osm_ids']),round(length,1),r['note']+' 线长仅为所绘OSM片段之和，可能含分离路幅、旧线或缺段，非该路全长或导航里程。','；'.join(r['sources']),OSM])
