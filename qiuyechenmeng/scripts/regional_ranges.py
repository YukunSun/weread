"""Area overlays for the linked article; administrative proxies are explicit."""
from pathlib import Path
import csv
import html
import json
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
DATA = ROOT/'data/regions'
METHOD = ('本色块为阅读范围参照。行政外缘取DataV公开地理数据，原文件未声明CRS；'
          '按其文档常用GCJ-02口径逆算为近似WGS84，存在来源与转换误差。'
          '数据含旧名旧码，行政时点未明。文化、历史分区没有统一精确边界，'
          '不能把现代行政数据的细轮廓理解为史界、方言界或人口分布界。')

def load():
    config=json.loads((DATA/'分区口径.json').read_text())
    raw=json.loads((DATA/'admin_regions_wgs84.geojson').read_text())
    admin={str(f['id']):f for f in raw['features']}
    return config,admin

def polygons(geometry):
    if geometry['type']=='Polygon': return [geometry['coordinates']]
    if geometry['type']=='MultiPolygon': return geometry['coordinates']
    raise ValueError('Unsupported area geometry: '+geometry['type'])

def oriented(ring,ccw=True):
    result=[[round(x,5),round(y,5)] for x,y,*_ in ring]
    if result[0]!=result[-1]: result.append(result[0])
    signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(result,result[1:]))
    if (signed>0)!=ccw: result.reverse()
    return result

def polygon(parent,rings,el):
    p=el(parent,'Polygon');el(p,'tessellate',1);el(p,'altitudeMode','clampToGround')
    for i,ring in enumerate(rings):
        if len(ring)<4: raise ValueError('Ring too short')
        b=el(p,'outerBoundaryIs' if i==0 else 'innerBoundaryIs');lr=el(b,'LinearRing')
        coords=oriented(ring,i==0)
        el(lr,'coordinates',' '.join(f'{x:.5f},{y:.5f},0' for x,y in coords))

def insert_styles(doc,styles):
    for s in styles: doc.remove(s)
    index=next((i for i,c in enumerate(doc) if c.tag in [f'{{{KML}}}Folder',f'{{{KML}}}Placemark']),len(doc))
    for i,s in enumerate(styles): doc.insert(index+i,s)

def add_ranges(doc,el,view,kcolor,bundled=False):
    config,admin=load();article=config['article'];styles=[]
    for r in config['ranges']:
        st=el(doc,'Style',id='range_'+r['id']);styles.append(st)
        line=el(st,'LineStyle');el(line,'color',kcolor(r['color'],'95'));el(line,'width',1.3)
        poly=el(st,'PolyStyle');el(poly,'color',kcolor(r['color'],r.get('alpha','36')));el(poly,'fill',1);el(poly,'outline',1)
        st=el(doc,'Style',id='range_label_'+r['id']);styles.append(st)
        ic=el(st,'IconStyle');el(ic,'color',kcolor(r['color']));el(ic,'scale',0.4)
        icon=el(ic,'Icon');el(icon,'href','icons/region_label.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        ls=el(st,'LabelStyle');el(ls,'color','ffffffff');el(ls,'scale',1.0)
    st=el(doc,'Style',id='range_admin');styles.append(st)
    line=el(st,'LineStyle');el(line,'color','b0dddddd');el(line,'width',1.0)
    poly=el(st,'PolyStyle');el(poly,'fill',0);el(poly,'outline',1)
    insert_styles(doc,styles)
    top=el(doc,'Folder',id='regional_ranges');el(top,'name','10 藏区地理范围｜据知乎分区说明，概略参照');el(top,'open',1)
    el(top,'description',f'<h3>按范围阅读西藏地理称谓</h3><p>资料：{html.escape(article["author"])}的<a href="{article["url"]}">{html.escape(article["title"])}</a>。核对日期2026-10-31。</p><p>{html.escape(article["scope"])}</p><p>{METHOD}</p><p>建议每次只开启一套分区。默认显示10A，10B至10F隐藏。半透明色块表示范围参照；边界数据来源与文化名称性质不同。工布使用三县区核心，阿坝单列交错区，羌塘单列自然地理。</p>')
    view(top,92.0,32.7,2300000)
    groups={}
    for g in config['groups']:
        f=el(top,'Folder',id='range_group_'+g['id']);el(f,'name',g['name']);el(f,'visibility',int(g['visible']));el(f,'open',0)
        el(f,'description','<p>'+html.escape(g['note'])+'</p><p>'+METHOD+'</p>');view(f,92,32.5,2300000);groups[g['id']]=f
    for r in config['ranges']:
        group=next(g for g in config['groups'] if g['id']==r['group']);f=groups[r['group']]
        members=[admin[c] for c in r.get('members',[])]
        names='、'.join(m['properties']['name'] for m in members)
        body=f'<h3>{html.escape(r["name"])}</h3><p><b>文章概括：</b>{html.escape(r["article"])}</p><p><b>本图范围口径：</b>{html.escape(r["note"])}</p>'
        if members:
            body+='<p><b>实际绘图组合（数据源名称）：</b>'+html.escape(names)+'</p><p>'+METHOD+'</p>'
        else:
            body+='<p><b>几何性质：手工示意外缘，无精确地理边界依据。</b></p>'
        body+=f'<p><a href="{article["url"]}">指定知乎回答</a> · '+' · '.join(f'<a href="{config["sources"][k]}">核查资料{i+1}</a>' for i,k in enumerate(r['sources']))+'</p>'
        body+='<p>几何来源：'+' · '.join(f'<a href="{m["properties"]["source_url"]}">{html.escape(m["properties"]["name"])}</a>' for m in members)+'</p>' if members else ''
        p=el(f,'Placemark',id='range_area_'+r['id']);el(p,'name',r['name']+'〔范围参照〕');el(p,'visibility',1);el(p,'description',body)
        view(p,*r['label'],850000);el(p,'styleUrl','#range_'+r['id'])
        ed=el(p,'ExtendedData')
        for key,value in [('range_kind','schematic' if not members else 'modern administrative proxy'),('coordinate_method','schematic WGS84' if not members else 'inferred GCJ02 to approximate WGS84'),('article_url',article['url']),('note',r['note'])]:
            d=el(ed,'Data',name=key);el(d,'value',value)
        mg=el(p,'MultiGeometry')
        if members:
            for m in members:
                for rings in polygons(m['geometry']): polygon(mg,rings,el)
        else: polygon(mg,[r['schematic_ring']],el)
        label=el(f,'Placemark',id='range_text_'+r['id']);el(label,'name',r['name']);el(label,'visibility',1);el(label,'description',body);view(label,*r['label'],850000);el(label,'styleUrl','#range_label_'+r['id'])
        pt=el(label,'Point');el(pt,'altitudeMode','clampToGround');el(pt,'coordinates',f'{r["label"][0]},{r["label"][1]},0')
    for code in ['540100','540200','540300','540400','540500','540600','542500','630000','513300','513200','533400','623000']:
        m=admin[code];p=el(groups['admin'],'Placemark',id='range_admin_'+code);el(p,'name',m['properties']['name']+'〔行政数据参照〕');el(p,'visibility',1)
        el(p,'description',f'<p>{METHOD}</p><p><a href="{m["properties"]["source_url"]}">原始数据</a>；旧名称按数据保留。</p>')
        el(p,'styleUrl','#range_admin')
        mg=el(p,'MultiGeometry')
        for rings in polygons(m['geometry']): polygon(mg,rings,el)
    return config,admin

def write_range_index():
    config,admin=load()
    with (output_path('tables', '藏区范围对照.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['图层','范围名','几何性质','实际绘图组合','文章概括','本图口径与限制','文章链接','核查链接'])
        for r in config['ranges']:
            names='、'.join(admin[c]['properties']['name'] for c in r.get('members',[]))
            w.writerow([r['group'],r['name'],'手工示意外缘' if 'schematic_ring' in r else '现代行政数据代理范围',names,r['article'],r['note'],config['article']['url'],'；'.join(config['sources'][k] for k in r['sources'])])
    text='''知乎回答地理分区：范围地图
核对日期：2026-10-31

打开“艽野尘梦_藏区地理范围.kmz”可叠加到已有地图，不重复地点、耗时、距离或现代道路。
新版“艽野尘梦_阅读地图.kmz”也包含10范围层；两者二选一加载本层。
默认显示10A文化地理参照；先关闭10A，再打开10B前后藏、10C东西方向、10D元明称谓、10E羌塘或10F行政轮廓比较。
单击色块或名称可查看文章说法、具体绘图政区、核查来源与边界限制。双击可定位。

所有半透明色块都是阅读范围参照：文化地理的边缘没有统一测定线。
行政数据虽有细轮廓，只说明绘图取了哪些现代政区，绝不是已复原的历史疆界。
阿坝整州不归入康或安多，单列文化交错地区。
工布只取巴宜、工布江达、米林核心，未把整个林芝一并涂入。
羌塘单列自然地理方向范围；其外缘手工概括，不是保护区界、文化界或历史行军轨迹。
广义前后藏只表达文章的东西方向，不沿拉萨经线切分；北部部分地区留白。
元明称谓层只是文章主要地名的现代参照，不是宣慰司、都司及各年代政权疆界。

数据来源与坐标：
行政几何来自阿里云DataV公开地理数据服务，数据时点不明且有旧名旧码。
源文件未声明CRS；依DataV文档常用GCJ-02口径作迭代逆变换，得到近似WGS84，不能当作测绘级界线。
数据源独立开放再分发许可未明确，详情见data/regions/NOTICE.txt。
原始JSON、转换结果、来源、获取日期保留在data/regions/；分区口径与逐块来源见data/regions/分区口径.json。
藏区范围对照.csv可逐项核对“文章怎么说”与“地图实际怎么画”。

本次验证与导入状态：
KML通过OGC KML 2.2官方XSD校验；KMZ完整性、图标引用、坐标范围、闭合环与ID已检查。
2026-10-31已将含10范围层、11南北驿路层的完整阅读地图导入原Google Earth网页版项目，确认处理完成并保存到Google云端硬盘。
网页版仅提示忽略Region、maxLines、textColor显示字段；已抽查10层目录和北路弹窗逐段km、耗时。行政及历史范围的逐边界精确对位、桌面客户端仍未逐项验收。
'''
    text+='\n指定文章\n'+config['article']['url']+'\n\n核查资料\n'+'\n'.join(config['sources'].values())+'\n'
    (output_path('docs', '藏区地理范围说明.txt')).write_text(text)
