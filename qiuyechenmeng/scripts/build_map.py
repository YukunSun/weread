"""Build a source-labelled literary reading map; Python standard library only."""
from pathlib import Path
import csv
import html
import json
import math
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
ET.register_namespace('', KML)
BOOK = 'https://weread.qq.com/web/reader/c04325905e47adc0457d4a9'
TEXT = 'https://github.com/chaimol/chaimol.github.com/blob/master/book/%E8%89%BD%E9%87%8E%E5%B0%98%E6%A2%A6.txt'
SOURCES = {
    '原文与任乃强校注': TEXT,
    '原文在线对读': 'https://www.yenke.net/wiki/index.php?title=%E8%89%BD%E9%87%8E%E5%B0%98%E6%A2%A6',
    '微信读书版本与目录': BOOK,
    '旧驿道与长坝春考证': 'https://www.tibetology.ac.cn/2023-05/03/content_42353852.htm',
    '江达与太昭考证': 'https://www.cass.cn/xueshuchengguo/xscg_lsyjy/202303/t20230317_5608287.shtml',
    '鲁朗镇治迁移': 'https://www.xzdw.gov.cn/dsdt/lz/201805/t20180528_57143.html',
    '江巴村地理参照': 'https://files.gzz.gov.cn/upload/file/zhengwen/f97d93545fb34a3bb6138fa6901b7116.pdf',
    '恩达与瓦合山旧驿道': 'https://www.xzxw.com/lyrw/2015-03/21/content_1286490.html',
    'KML格式规范': 'https://developers.google.com/kml/documentation/kmlreference',
}

def wiki(title):
    return 'https://zh.wikipedia.org/wiki/' + title

# Coordinates are longitude, latitude. Modern representative points are not campsites.
# chapter, phase, certainty, coordinate source, notes are retained in all outputs.
ROWS = [
('chengdu','01 成都','成都',104.0644,30.6583,'第1章','in','对应较明确',wiki('成都市'),'行程起点。城市代表点，不指认出师营址。'),
('yaan','02 雅州 → 雅安','雅安市',103.0128,29.9805,'第1章','in','对应较明确',wiki('雅安市'),'旧府城的现代城市参照。雅安至泸定之间的大相岭、飞越岭旧道未逐段复原，连线不代表现代川藏公路。'),
('luding','03 沪定桥 → 泸定桥','泸定桥',102.2302,29.9145,'第1章','in','对应较明确',wiki('泸定桥'),'书中大渡河渡桥地点。使用现桥地标坐标；不据原文估计桥长、宽度。'),
('kangding','04 打箭炉 → 康定','康定老城区一带',101.9550,30.0015,'第1章','in','对应较明确',wiki('康定市'),'北路入藏的整备地点。现代城区代表点。'),
('zheduo','05 折多塘','折多塘一带',101.8860,29.9949,'第1章','in','对应较明确','https://www.fallingrain.com/world/CH/32/Zheduotang.html','离开打箭炉后的首站；使用地名代表点，非宿营遗址。'),
('changba','06 长坝春 → 江巴村一带','康定江巴村一带',101.65,30.20,'第1章；校注6','in','区域参照',SOURCES['江巴村地理参照'],'长坝春又作长霸冲、长坝仲。中国藏学研究中心论文对应为江巴村。坐标取官方报告江巴村监测点并舍入至0.01°；报告未注明坐标系，故只作村域阅读定位，不作精确坐标。'),
('daofu','07 道坞 → 道孚','道孚鲜水镇',101.1254,30.9777,'第1章','in','对应较明确',wiki('鲜水镇'),'旧称道坞，对应今道孚。使用现代县城聚落代表点。'),
('luhuo','08 霍尔章谷 → 炉霍','炉霍新都镇',100.6803,31.3937,'第1章；校注8','in','对应较明确',wiki('新都镇_(炉霍县)'),'按校注对应炉霍；现代聚落代表点。'),
('garze','09 甘孜','甘孜镇',99.9886,31.6273,'第1章；校注10','in','对应较明确',wiki('甘孜镇'),'校注记后续经打火沟、甑科、麦学、八邦寺，不走雀儿山大道。地图不把德格县城增列为作者亲经站。'),
('maisux','10 麦削／麦学 → 麦宿一带','德格麦宿一带',98.9914,31.6329,'第1章；校注10','in','区域参照',wiki('麦宿镇'),'校注作麦学。使用现代麦宿聚落点概略定位，非旧驿站遗址；甘孜至此之间的曾科／甑科另列待考。'),
('palpung','11 八邦寺','八邦寺／八蚌寺',98.7960,31.6483,'第1章；校注10','in','对应较明确',wiki('八邦寺'),'原文行程的补充节点来自校注10；与作者正文亲记地点作来源区分。'),
('gangtuo','12 岗拖 → 岗托','金沙江岗托一带',98.5853,31.6326,'第1章','in','对应较明确',wiki('岗托镇'),'金沙江渡口地区。标的是现代岗托聚落，非确定的历史皮船下水点。'),
('chamdo','13 察木多 → 昌都','昌都老城、强巴林寺一带',97.1779,31.1435,'第1—3章','in','对应较明确',wiki('强巴林寺'),'用强巴林寺定位昌都老城，非作者营房遗址。第2章腊左探险支线未精确复原。'),
('riwoche','14 类乌齐','类乌齐旧寺镇',96.5036,31.3716,'第3章','west','对应较明确',wiki('类乌齐镇'),'选用旧寺镇，区分今县城桑多镇。恩达、三十九族等中间节点未强行定位。'),
('lhari','15 拉里 → 嘉黎旧镇','嘉黎镇一带',93.3458,30.7423,'第3章','west','区域参照',wiki('嘉黎镇'),'旧粮台所在地区的镇区参照；不是今日阿扎县城。原文回忆与部分史事在校注中有订正。'),
('taizhao','16 江达 → 太昭古城一带','工布江达县江达村、太昭一带',93.08,30.00,'第3、7、8章','west','区域参照','https://www.fallingrain.com/world/a/T/a/i/z/h/index.html','依据社科院实地考察对应太昭／江达村。采用地名表及太昭大桥附近区域的粗略坐标；不是昌都市江达县，也不是工布江达现代县城。'),
('lulang','17 鲁朗','鲁朗地区',94.7332,29.7257,'第5—7章','pome','区域参照','https://mapcarta.com/N12238762005','使用现代镇驻地作地区参照。镇治曾由东久迁移，旅游小镇与书中驻营地不能直接等同；未确认作者每次驻地。'),
('tongmai','18 汤买／汤木 → 通麦一带','通麦、易贡藏布渡河地区',95.0646,30.0976,'第6章；校注33','pome','区域参照','https://www.upc.pbs.bridgemeister.com/bridge.php?bid=6161','现代通麦桥坐标仅用于定位渡河地区，不认定旧藤桥与今桥重合。'),
('yigong','19 彝贡 → 易贡地区','易贡乡一带',94.8162,30.2699,'第6章','pome','区域参照','https://mapcarta.com/29837964','现代易贡乡聚落代表点，用于查看易贡河谷；不等同书中的军营、登岸点或具体战场。'),
('qundo','20 春多寺 → 倾多寺一带','倾多镇、倾多寺地区',95.6022,30.0577,'第6—7章；校注35','pome','事件区域','https://mapcarta.com/N3017464360','校注将春多寺、春倾寺对应倾多寺。坐标取现代倾多聚落点，非寺院测绘坐标；主要作为书中部队和人物活动的事件地点，不认定作者本人亲到，未接入个人行程连线。'),
('golmud','21 柴达木 → 格尔木一带（推定）','格尔木地区',94.9042,36.4028,'第11章；校注55','return','校注推定',wiki('格尔木市'),'任乃强按程站推为格尔木一带，不是作者明确写出的今名。使用现代城市代表点；不是当时城市已建成的断言，也不能据此反推羌塘精确轨迹。'),
('qinghai','22 青海 → 青海湖（区域）','青海湖',100.2,36.9,'第11章；校注57','return','区域参照','https://en.wikipedia.org/wiki/Qinghai_Lake','湖面代表点，仅定位整湖。原文及校注记行海南路；不代表到湖心，也不是确定的岸边营地。书中另有“青盐海”，与青海湖分开处理。'),
('riyue','23 日月山','日月山一带',101.0939,36.4431,'第11章；校注58','return','区域参照','https://mapcarta.com/W1425740804','使用日月山景区代表点，未确认旧道具体翻越位置。'),
('huangyuan','24 丹噶尔厅 → 湟源','丹噶尔古城一带',101.2643,36.6890,'第11—12章；校注59','return','对应较明确',wiki('城隍庙_(湟源县)'),'用古城内城隍庙定位丹噶尔老城，非作者旅店。书中到达日期为农历六月二十四，本图未换算为公历。'),
('xining','25 西宁','西宁城区',101.7781,36.6169,'第12章','return','对应较明确',wiki('西宁市'),'现代城市代表点，不指认张镇军衙署或作者所住旅店。'),
('lanzhou','26 兰州','兰州城区',103.8320,36.0610,'第12章','return','对应较明确',wiki('兰州市'),'现代城市代表点；旧炭市街旅店位置未核。'),
('xian','27 长安 → 西安','西安老城一带',108.9453,34.2592,'第12章','return','对应较明确',wiki('西安市'),'全书叙事终点。使用老城范围代表点；洪铺街寓所及墓葬均未精确定位。'),
('gongbo','参照 工布江达现代县城','工布江达县城',93.2462,29.8868,'地理对照','context','背景参照',wiki('工布江达县'),'供辨认今地名。与西北方向的太昭／江达村分开；本图不把现代县城当书中“江达”。'),
('bomi','参照 波密现代县城','波密扎木镇一带',95.7694,29.8585,'地理对照','context','背景参照',wiki('波密县'),'现代地理参照。历史波密是区域，不把今县城自动等同卡拖或春多寺。'),
]

UNLOCATED = [
('第1章','曾科／甑科','校注10指白玉县甑科。与今赠科乡对应尚需进一步核实，暂不赋坐标。'),
('第1章','大相岭、飞越岭','旧道与山口未逐段核定。成都—雅安—泸定连线只是地点顺序。'),
('第2—3章','腊左塘、腊左、并达桥、林多坝','校注11订为浪荡沟、纳贡塘、甲木桥、梭罗坝等。不同旧名不可混作同一个点，支线暂不画。'),
('第2—3章','恩达','可考至类乌齐桑多镇恩达村、瓦合山东侧一带；未核得可靠点位，未用俄洛镇代替。'),
('第3章','三十九族','区域名称，不能当一座城镇。未知作者在该区域的逐站行迹。'),
('第3—4章','牙披、脚木宗、窝冗噶伽','工布活动中的重要旧名，校注可提供相对方位，尚不足以确认现代精确点。'),
('第5—7章','德摩、纳衣当噶、八浪登、京中、树枝、央噶','旧山名、聚落名与现代点位未逐一核准，保留原名供对读，未冒用现代公路折线。'),
('第6—7章','卡拖、八阶、夥若桥','具体地点未核实，不把卡拖自动放在波密县城，也不把夥若桥直接等同今某座大桥。'),
('第8章','凝多／凝多塘','北返起初的重要节点，现代点位未核；北行避开拉里的记载不等于再次经过拉里。'),
('第8章','哈喇乌苏','按校注44指怒江南源阿克河谷；具体聚落、河段存疑，未用今日那曲城区代替。'),
('第8—10章','酱通／绛通（羌塘）','高原区域名称，并非一个可定位的沙漠景区。迷路行迹缺少足够空间约束，本图不复原其折线。'),
('第9章','通天河渡点','跨河本身有文本依据；校注联系穆鲁乌苏水系，但渡点不详，未用现代沱沱河桥或通天河大桥充作历史渡口。'),
('第8—10章','冈天削','校注48推测与昆仑山口有关，此说不作为精确定位依据；不把现代公路山口写成已证实途经点。'),
('第10章','遇蒙古喇嘛、遇猎户地点','事件有原文，地点无可靠坐标，不另造营地。'),
('第11章','盐淖、青盐海','盐沼及盐湖的具体范围未定。青盐海不同于随后到达的青海湖，不直接对应察尔汗、茶卡或柯柯盐湖。'),
('第11章','都兰','校注56作地理推定，未核当时市场位置，不使用今日察汗乌苏县城作为旧市镇的确点。'),
('第12章','分州、洪铺街寓所、西原墓','旧名或具体地点尚待考；地图止于西安，不另画一条书中未叙述的回凤凰路线。'),
]

PHASES = {
 'in': ('01 川西入藏｜第1章', '#49a7ff', True),
 'west': ('02 昌都至工布｜第2—4章', '#b692ff', True),
 'pome': ('03 工布与波密｜第5—7章', '#35c5a0', True),
 'wilderness': ('04 北返荒原｜第8—10章：路线待考', '#ffb347', True),
 'return': ('05 柴达木至西安｜第11—12章', '#ff7868', True),
 'context': ('06 现代地理参照｜默认隐藏', '#aaaaaa', False),
}

def el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, f'{{{KML}}}{tag}', attrs)
    if text is not None:
        node.text = str(text)
    return node

def view(parent, lon, lat, distance=70000):
    v=el(parent,'LookAt')
    for tag,value in [('longitude',lon),('latitude',lat),('altitude',0),('heading',0),('tilt',0),('range',distance),('altitudeMode','clampToGround')]:
        el(v,tag,value)

def links(items):
    return '<br/>'.join(f'<a href="{html.escape(u, quote=True)}">{html.escape(n)}</a>' for n,u in items)

def kcolor(hexrgb, alpha='ff'):
    s=hexrgb.lstrip('#')
    return alpha+s[4:6]+s[2:4]+s[:2]

def png(color, hollow=False):
    # Small original vector-like dot raster, with no external asset dependency.
    n=48; rgb=bytes.fromhex(color.lstrip('#')); rows=[]
    for y in range(n):
        row=bytearray([0])
        for x in range(n):
            r=math.hypot(x-23.5,y-23.5)
            if r>17: px=(0,0,0,0)
            elif r>14: px=(255,255,255,255)
            elif hollow and r<9: px=(35,40,48,255)
            else: px=(*rgb,255)
            row.extend(px)
        rows.append(row)
    def chunk(t,b): return struct.pack('!I',len(b))+t+b+struct.pack('!I',zlib.crc32(t+b)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')

def make_map(bundled=False):
    root=ET.Element(f'{{{KML}}}kml'); doc=el(root,'Document',id='qiuyechenmeng')
    el(doc,'name','《艽野尘梦》阅读地图｜主要地点与行程示意')
    el(doc,'open',1)
    el(doc,'description','<h2>《艽野尘梦》阅读地图</h2><p>按十二章整理的主要地点；不是全地名索引，也不是历史测绘复原。</p><p>蓝：川西入藏；紫：昌都至工布；绿：波密；橙：存疑；红：青海至西安。虚线只连接地点顺序，不表示道路或GPS轨迹；北返荒原段不画推测轨迹。</p><p>点击点位查看书中名、今名、章节、定位依据和资料。现代聚落点不等于营地、旧桥、墓地或战场。</p><p>资料核对：2026-10-30。微信读书参考：北方文艺出版社2018年版，ISBN 9787531738671；不是对用户当前所读版本的断言。正文地名参照原文及任乃强校注。</p>'+links(SOURCES.items()))
    view(doc,100.5,33.6,2000000)
    for key,(_,color,_) in PHASES.items():
        for uncertain in [False, True]:
            sid=key+('_uncertain' if uncertain else '')
            st=el(doc,'Style',id=sid)
            ic=el(st,'IconStyle');el(ic,'scale',1.05 if not uncertain else 1.15)
            icon=el(ic,'Icon')
            href=f'icons/{sid}.png' if bundled else ('https://maps.google.com/mapfiles/kml/shapes/open-diamond.png' if uncertain else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
            el(icon,'href',href)
            if not bundled:
                ic.insert(0,ET.Element(f'{{{KML}}}color'))
                ic[0].text=kcolor('#ffb347' if uncertain else color)
            lab=el(st,'LabelStyle');el(lab,'color','ffffffff');el(lab,'scale',0.85)
            line=el(st,'LineStyle');el(line,'color',kcolor(color,'d8'));el(line,'width',3)
            balloon=el(st,'BalloonStyle');el(balloon,'bgColor','fffafafa');el(balloon,'textColor','ff222222')
    guide=el(doc,'Folder');el(guide,'name','00 先读说明与图例');el(guide,'open',0)
    pm=el(guide,'Placemark');el(pm,'name','地图用法、精度与来源');el(pm,'description',doc.find(f'{{{KML}}}description').text)
    folders={}
    for key,(name,_,visible) in PHASES.items():
        f=el(doc,'Folder',id='folder_'+key);el(f,'name',name);el(f,'visibility',int(visible));el(f,'open',0);folders[key]=f
        if key=='wilderness':
            el(f,'description','<p>太昭北行后经凝多、哈喇乌苏、酱通、通天河，再至柴达木。旧名、渡点和迷路行迹尚不足以恢复。本层保留文献条目，不赋假坐标；请配合其他图层观察西藏至青海的大尺度地形。</p>')
            view(f,94,33.1,1000000)
    points={}
    for rid,label,modern,lon,lat,chapter,phase,certainty,coordsource,note in ROWS:
        uncertain=certainty=='校注推定'
        pm=el(folders[phase],'Placemark',id='place_'+rid);el(pm,'name',label)
        el(pm,'visibility',int(PHASES[phase][2]));el(pm,'Snippet',chapter+' · '+certainty,maxLines='1')
        extra=[('地名与行程：原文、校注',TEXT),('坐标参照',coordsource)]
        if rid=='taizhao': extra.append(('江达与太昭：社科院考察',SOURCES['江达与太昭考证']))
        if rid=='changba': extra.append(('长坝春今名考证',SOURCES['旧驿道与长坝春考证']))
        if rid=='lulang': extra.append(('鲁朗镇治迁移',SOURCES['鲁朗镇治迁移']))
        body=f'<h3>{html.escape(label)}</h3><p><b>今名／定位对象：</b>{html.escape(modern)}<br/><b>对应章节：</b>{html.escape(chapter)}<br/><b>定位性质：</b>{certainty}<br/><b>经纬度：</b>{lon:.4f}°E, {lat:.4f}°N</p><p>{html.escape(note)}</p><p>坐标的小数位仅为存储格式，不代表历史位置已精确到米。除特别说明外，使用WGS84兼容地名／地标坐标；定位性质比显示位数更重要。</p><p>'+links(extra)+'</p>'
        el(pm,'description',body);view(pm,lon,lat,180000 if rid in ['golmud','qinghai'] else 65000)
        el(pm,'styleUrl','#'+phase+('_uncertain' if uncertain else ''))
        ed=el(pm,'ExtendedData')
        for name,value in [('book_name',label),('modern_name',modern),('chapter',chapter),('certainty',certainty),('coordinate_reference',coordsource),('literary_source',TEXT),('note',note)]:
            d=el(ed,'Data',name=name);el(d,'value',value)
        pt=el(pm,'Point');el(pt,'altitudeMode','clampToGround');el(pt,'coordinates',f'{lon},{lat},0');points[rid]=(lon,lat)
    # Geometry-free entries are deliberately not dropped: available in the Places tree.
    other=el(doc,'Folder');el(other,'name','07 待考旧地名｜无坐标，不在地球上造点');el(other,'open',0)
    for n,(chapter,name,note) in enumerate(UNLOCATED,1):
        target=folders['wilderness'] if chapter in ['第8章','第9章','第8—10章','第10章'] else other
        p=el(target,'Placemark',id=f'unlocated_{n}');el(p,'name',name+'【未定位】')
        refs=[('原文与校注',TEXT)]
        if name=='恩达': refs.append(('恩达与瓦合山旧驿道实地报道',SOURCES['恩达与瓦合山旧驿道']))
        el(p,'description',f'<h3>{html.escape(name)}</h3><p>{chapter}。{html.escape(note)}</p><p>本条无几何坐标；不会在地球上显示点标。</p>'+links(refs))
    routes=[
        ('in','R1 入藏地点顺序示意（虚线，非道路）',['chengdu','yaan','luding','kangding','zheduo','changba','daofu','luhuo','garze','maisux','palpung','gangtuo','chamdo']),
        ('west','R2 昌都—类乌齐—嘉黎—江达（虚线，省略若干未定站）',['chamdo','riwoche','lhari','taizhao']),
        ('pome','R3 鲁朗—通麦—易贡方向（虚线，反攻阶段简化）',['lulang','tongmai','yigong']),
        ('return','R4 日月山—丹噶尔—西宁—兰州—西安（虚线）',['riyue','huangyuan','xining','lanzhou','xian']),
    ]
    for n,(phase,name,ids) in enumerate(routes,1):
        p=el(folders[phase],'Placemark',id=f'route_{n}');el(p,'name',name)
        el(p,'description','<p>只显示主要地点的先后及大致方向。每两点间为人为直线插值的虚线；未按山谷、旧驿道、现代公路或卫星地形拟合，不可用于测量历史里程或导航。</p><p>第二章探险、第四章工布驻防、第五至七章反复进退均未完整复原。太昭至鲁朗、北返荒原、格尔木至青海湖等证据不足的连接处留白。</p>')
        el(p,'styleUrl','#'+phase);mg=el(p,'MultiGeometry')
        for a,b in zip(ids,ids[1:]):
            ax,ay=points[a];bx,by=points[b]
            km=111*math.hypot((bx-ax)*math.cos(math.radians((ay+by)/2)),by-ay)
            count=max(2,math.ceil(km/8))
            for seg in range(count):
                t0=seg/count;t1=(seg+0.58)/count
                ls=el(mg,'LineString');el(ls,'tessellate',1);el(ls,'altitudeMode','clampToGround')
                el(ls,'coordinates',f'{ax+(bx-ax)*t0:.6f},{ay+(by-ay)*t0:.6f},0 {ax+(bx-ax)*t1:.6f},{ay+(by-ay)*t1:.6f},0')
    ET.indent(root,space='  ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def main():
    name='艽野尘梦_阅读地图'
    (ROOT/(name+'.kml')).write_bytes(make_map())
    with zipfile.ZipFile(ROOT/(name+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_map(True))
        for phase,(_,color,_) in PHASES.items():
            z.writestr('icons/'+phase+'.png',png(color))
            z.writestr('icons/'+phase+'_uncertain.png',png('#ffb347',True))
    headers=['id','地图标签','现代定位对象','经度','纬度','章节','图层','定位性质','坐标来源','说明']
    with (ROOT/'地名对照与坐标.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(ROWS)
    (ROOT/'data'/'未定位地名.json').write_text(json.dumps(UNLOCATED,ensure_ascii=False,indent=2)+'\n')
    readme='''《艽野尘梦》阅读地图
制作与核对日期：2026-10-30

一、打开方式
推荐使用“艽野尘梦_阅读地图.kmz”：与KML包含相同地点和连线，并内置全部点标图标。
Google Earth Pro：文件 → 打开，选择KML或KMZ；在左侧展开各章图层。
Google Earth网页版：使用导入KML/KMZ功能选择本地文件；不同版本入口文字可能不同。
只导入其中一个文件即可，以免出现重复点标。
点击地点可以查看旧名、今名、章节、位置性质和来源。双击地点或文件夹可缩放到相应区域。
“06 现代地理参照”默认隐藏，需要辨认现代县城时可勾选。
“04 北返荒原”和“07 待考旧地名”包含无坐标的文字条目；网页版可能省略这些条目，完整内容亦在本说明下文。

二、内容和图例
29个地图点：27个书中地点或区域的代表点，2个默认隐藏的现代县城对照点。
4组虚线：蓝色川西入藏，紫色昌都至工布，绿色波密方向，红色青海至西安。
虚线人为连接主要地点，只表示先后与大致方向，不是古道、现代公路或实测轨迹。
橙色空心点：柴达木对应格尔木一带，为校注推定。
第2章探险支线、第4章工布活动、第5—7章反复进退未逐段完整复原。
北返荒原，以及太昭至鲁朗、格尔木至青海湖等证据不足的路段，保留空白。
书中江达对应今太昭／江达村一带，不是昌都江达县，也不是工布江达现代县城。
书中哈喇乌苏未径套今日那曲；通天河未用现代桥位作渡点；青盐海与青海湖分开。
不增画西安至凤凰路线，因为正文并未叙述这段归途。

三、精度
这是“主要地点阅读地图”，不是全地名索引或历史GIS精确复原。
现代城市、村镇、寺院或桥梁的代表坐标，不代表历史宿营点、旅店、旧桥、战场或墓地。
坐标采用WGS84兼容地理来源；江巴村官方监测点未注明坐标系，特意舍入至0.01°，只用于粗略定位。
显示四位小数仅是统一存储格式，不能理解成历史位置精确到米。
没有给未知行程编造日期或经纬度；农历日期未冒作公历。

四、文本依据
微信读书已核对陈渠珍、任乃强《艽野尘梦》北方文艺出版社2018年版目录（ISBN 9787531738671）。
此版用于目录参照，不代表已确认用户当前阅读版本。
地名和顺序结合公开原文、任乃强校注及下列地名研究；地图弹窗逐点列坐标来源。
部分地点为校注补足或他人活动相关地点，并非作者正文逐站亲记，均在说明内区分。

'''
    readme+='资料入口\n'+'\n'.join(n+'\n'+u for n,u in SOURCES.items())
    readme+='\n\n五、待考旧地名（17条，不赋坐标）\n'
    for chapter,name,note in UNLOCATED:
        readme+=f'\n{chapter}｜{name}\n{note}\n'
    readme+='''
六、附带文件
地名对照与坐标.csv：可用表格软件查看29个点的坐标、章节和来源。
data/未定位地名.json：17条待考条目。
scripts/build_map.py：可复现构建脚本，只使用Python标准库。

七、验证范围
KML及KMZ内doc.kml均已通过OGC KML 2.2官方XSD校验。
已检查坐标顺序和范围、样式引用、ID唯一性、KMZ完整性与内置图标引用。
未在Google Earth客户端实际导入或检验卫星底图的对位效果。
'''
    (ROOT/'地图使用说明.txt').write_text(readme,encoding='utf-8')
    print(f'Created: {len(ROWS)} point markers, {len(UNLOCATED)} unlocated entries, 4 schematic routes.')

if __name__=='__main__':
    main()
