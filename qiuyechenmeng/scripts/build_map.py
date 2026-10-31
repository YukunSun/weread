"""Build a source-labelled literary reading map; Python standard library only."""
from pathlib import Path
import csv
import html
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from modern_roads import add_roads, write_road_index
from regional_ranges import add_ranges, write_range_index
from post_routes import add_post_routes, write_post_indexes

ROOT = Path(__file__).resolve().parents[1]
TIMINGS = json.loads((ROOT/'data'/'行程耗时.json').read_text(encoding='utf-8'))
MINOR_PLACES = json.loads((ROOT/'data'/'小地名.json').read_text(encoding='utf-8'))
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
('maisux','10 麦削／麦学 → 麦宿一带','德格麦宿一带',98.9914,31.6329,'第1章；校注10','in','区域参照',wiki('麦宿镇'),'校注作麦学。使用现代麦宿聚落点概略定位，非旧驿站遗址；曾科／甑科在11层补赠科乡候选参照，古今对应与旧站确址仍待考。'),
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

# Distances are between representative points, never reconstructed walking miles.
PLACE_BY_ID = {r[0]: r for r in ROWS}
ROUTES = [
    ('in','R1 入藏地点顺序示意',['chengdu','yaan','luding','kangding','zheduo','changba','daofu','luhuo','garze','maisux','palpung','gangtuo','chamdo']),
    ('west','R2 昌都—类乌齐—嘉黎—江达',['chamdo','riwoche','lhari','taizhao']),
    ('pome','R3 鲁朗—通麦—易贡方向',['lulang','tongmai','yigong']),
    ('return','R4 日月山—丹噶尔—西宁—兰州—西安',['riyue','huangyuan','xining','lanzhou','xian']),
]
DISTANCE_NOTE = '代表点之间的球面近似直线距离，按平均地球半径6371.0088 km计算，取整。不是历史实走里程、现代公路里程或虚线短笔画长度；不确定位置会影响距离，不能当导航数据。'

def distance_km(a,b):
    ax,ay=PLACE_BY_ID[a][3:5]; bx,by=PLACE_BY_ID[b][3:5]
    p1,p2=map(math.radians,[ay,by]); dp=p2-p1; dl=math.radians(bx-ax)
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,h))))

DISTANCE_ROWS = []
for phase,route,ids in ROUTES:
    for a,b in zip(ids,ids[1:]):
        DISTANCE_ROWS.append((route,a,b,'相邻示意节点',distance_km(a,b)))
DISTANCE_ROWS += [
    ('补充起讫对照','kangding','chamdo','康定至昌都起讫直线，不含绕行',distance_km('kangding','chamdo')),
    ('补充起讫对照','taizhao','huangyuan','北返223日全段起讫直线，不是荒原轨迹',distance_km('taizhao','huangyuan')),
]

UNLOCATED = [
('第1章','曾科／甑科旧驿站确址','校注10指白玉县甑科。11层补赠科乡现代点作候选区域参照，古今对应未获直接史证，旧驿站确址仍未定位。'),
('第1章','大相岭旧山口、果亲王摩崖诗','已补大相岭古道的路桥碑地区参照及飞越岭垭口；作者登岭顶与摩崖诗的具体位置仍待考。'),
('第2—3章','腊左塘 → 浪荡沟','校注11订正今旧称。位于俄洛桥与纳贡山之间，未查到可靠独立坐标，不按书中里数插值造点。'),
('第2—3章','腊左 → 纳贡塘','校注11订正，与腊左塘／浪荡沟是不同地点；暂不赋假坐标。'),
('第2—3章','并达桥／井达桥 → 甲木桥','校注11订正，位于纳贡塘与梭罗坝之间；未确认旧桥具体桥址。'),
('第2—3章','林多坝 → 梭罗坝','校注11订正，在恩达与甲木桥之间；未查到可直接使用的现代点位。'),
('第2—3章','西藏桥','正文出昌都先过西藏桥，再到俄洛桥；校注11将两者相联，存在称名差异。本图只补俄洛桥地区参照，不将两座桥直接合并。'),
('第2—3章','恩达汛署／堪布营地','已补今桑多镇恩达村代表点，但汛署及堪布大营遗址未定位。'),
('第3章','三十九族','区域名称，不能当一座城镇。未知作者在该区域的逐站行迹。'),
('第3—4章','脚木宗、窝冗噶伽','牙披已补阿沛村地区参照；脚木宗和窝冗噶伽仍只有相对方位，不能共用牙披坐标。'),
('第5—7章','纳衣当噶、八浪登、京中、树枝、央噶','德摩、冬九已补地区参照；此处其余旧山名、聚落仍未逐一核准，未冒用现代公路折线。'),
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
 'in': ('01 川西入藏｜成都至康定行约12日；炉城至昌都记50余日＊', '#49a7ff', True),
 'west': ('02 昌都至工布｜恩达至嘉黎月余；工布安抚约2月', '#b692ff', True),
 'pome': ('03 工布与波密｜含驻防、等待和往返，未计统一总日数', '#35c5a0', True),
 'wilderness': ('04 北返荒原｜江达到丹噶尔223日大段的一部分', '#ffb347', True),
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

def time_html(entries):
    if not entries:
        return '<p>本地点单独耗时未明确记载，不按里程分摊。</p>'
    return '<h3>行程与耗时</h3>'+''.join(
        f'<p><b>{html.escape(t["segment"])}：{html.escape(t["duration"])}</b><br/>'
        f'{html.escape(t["kind"])}。{html.escape(t["basis"])}</p>' for t in entries)

def distance_html(entries):
    return '<h3>距离（km）</h3>'+''.join(
        f'<p><b>{html.escape(PLACE_BY_ID[a][2])} → {html.escape(PLACE_BY_ID[b][2])}：直线约 {km:.0f} km</b><br/>{html.escape(kind)}</p>'
        for _,a,b,kind,km in entries)+f'<p>{DISTANCE_NOTE}</p>'

def display_label(rid,label):
    labels=[t['label'] for t in TIMINGS if t['anchor']==rid and t.get('label')]
    incoming=[d for d in DISTANCE_ROWS if d[2]==rid and d[3]=='相邻示意节点']
    # A few major labels also show distance; all segments remain in balloons/CSV.
    if rid in ['yaan','luding','kangding','lanzhou','xian'] and incoming:
        a=incoming[-1][1]; labels.append(f'{PLACE_BY_ID[a][2]}直距约{incoming[-1][4]:.0f} km')
    if rid=='chamdo': labels.append(f'康定直距约{distance_km("kangding","chamdo"):.0f} km')
    if rid=='huangyuan': labels.append(f'北返起讫直距约{distance_km("taizhao","huangyuan"):.0f} km')
    return label+('｜'+'；'.join(labels) if labels else '')

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

def minor_styles(doc,bundled):
    for style_id,color,hollow in [('minor_landmark','#89d8ff',False),('minor_reference','#ffd166',True)]:
        st=el(doc,'Style',id=style_id)
        iconstyle=el(st,'IconStyle');el(iconstyle,'color','ffffffff' if bundled else kcolor(color));el(iconstyle,'scale',0.85)
        icon=el(iconstyle,'Icon');el(icon,'href',f'icons/{style_id}.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        lab=el(st,'LabelStyle');el(lab,'color','ffffffff');el(lab,'scale',0.85)

def minor_folder(doc):
    folder=el(doc,'Folder',id='minor_folder');el(folder,'name',f'08 小地名补充｜{len(MINOR_PLACES)}处（含区域参照）');el(folder,'open',1)
    el(folder,'description','蓝点：现代山口参照；金色空心点：村域、旧名或事件地区参照。支持Region的客户端按缩放显示小地名；Google Earth网页版会忽略此显示条件，可手动开关本层或从列表点击定位。俄洛桥不冒作已测定旧桥位。腊左探险中间地名仍待考，不按里数造点。')
    view(folder,97.07278,31.18528,160000)
    groups={}
    for p in MINOR_PLACES:
        if p['group'] not in groups:
            f=el(folder,'Folder');el(f,'name',p['group']);el(f,'open',0);groups[p['group']]=f
        pm=el(groups[p['group']],'Placemark',id='minor_'+p['id']);el(pm,'name',p['name'])
        lon,lat=p['lon'],p['lat']
        anchor=PLACE_BY_ID[p['reference']]
        ax,ay=anchor[3:5]
        phi1,phi2=map(math.radians,[lat,ay]);dphi=phi2-phi1;dl=math.radians(ax-lon)
        h=math.sin(dphi/2)**2+math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
        km=6371.0088*2*math.asin(math.sqrt(min(1,max(0,h))))
        info=(f'<h3>{html.escape(p["name"])}</h3><p><b>书中名：</b>{html.escape(p["old_names"])}<br/>'
              f'<b>现代参照：</b>{html.escape(p["modern"])}<br/><b>章节：</b>{html.escape(p["chapter"])}<br/>'
              f'<b>定位性质：</b>{html.escape(p["certainty"])}</p><p>{html.escape(p["note"])}</p>'
              f'<p><b>耗时：</b>{html.escape(p["timing"])}</p>'
              f'<p><b>距{html.escape(anchor[2])}代表点：直线约{km:.0f} km。</b>只是两代表点间的距离，非书中两站路程；不与全书总里程累加。</p>'
              f'<p><b>经纬度：</b>{lon:.5f}°E, {lat:.5f}°N。小数位不代表古址精度。</p>'+links([
                  ('今名／历史依据',p['identity_source']),('坐标参照',p['coordinate_source']),('原文及任乃强校注',TEXT)]))
        el(pm,'description',info);view(pm,lon,lat,45000)
        el(pm,'styleUrl','#'+('minor_landmark' if p['certainty']=='现代地形点参照' else 'minor_reference'))
        # A display window, not an asserted historical territory or error ellipse.
        reg=el(pm,'Region');box=el(reg,'LatLonAltBox')
        for tag,value in [('north',lat+0.10),('south',lat-0.10),('east',lon+0.12),('west',lon-0.12)]: el(box,tag,value)
        lod=el(reg,'Lod');el(lod,'minLodPixels',32);el(lod,'maxLodPixels',-1)
        ed=el(pm,'ExtendedData')
        for name,value in [('old_names',p['old_names']),('modern_reference',p['modern']),('chapter',p['chapter']),('certainty',p['certainty']),('timing',p['timing']),('reference_distance',f'距{anchor[2]}代表点直线约{km:.0f} km'),('note',p['note'])]:
            d=el(ed,'Data',name=name);el(d,'value',value)
        pt=el(pm,'Point');el(pt,'altitudeMode','clampToGround');el(pt,'coordinates',f'{lon},{lat},0')
    return folder

def serialize(root):
    ET.indent(root,space='  ')
    serialized=ET.tostring(root,encoding='utf-8',xml_declaration=True).decode('utf-8')
    serialized=re.sub(r'<description>(.*?)</description>',lambda m:'<description><![CDATA['+html.unescape(m.group(1)).replace(']]>',']]]]><![CDATA[>')+']]></description>',serialized,flags=re.S)
    return serialized.encode('utf-8')

def make_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='minor_supplement')
    el(doc,'name','《艽野尘梦》小地名补充｜俄洛桥等');el(doc,'open',1)
    el(doc,'description',f'新增{len(MINOR_PLACES)}处小地名，可叠加到已导入的耗时与距离版。村域、地区参照均有说明，旧桥、旧营地不冒作确点。')
    view(doc,97.07278,31.18528,160000)
    minor_styles(doc,bundled);minor_folder(doc)
    return serialize(root)

def make_road_supplement():
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='modern_road_supplement')
    el(doc,'name','《艽野尘梦》现代道路对照｜G317等国道省道');el(doc,'open',1)
    el(doc,'description','现代道路为实线，历史行程仍为原图虚线。只需叠加本文件即可对照，不重复导入历史地点。道路数据缺失不人为补齐，点击路号查看范围与来源。')
    view(doc,97.07,31.18,160000)
    roads=add_roads(doc,el,view,kcolor);write_road_index(roads)
    return serialize(root)

def make_range_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='regional_range_supplement')
    el(doc,'name','《艽野尘梦》藏区地理范围｜据知乎分区说明');el(doc,'open',1)
    el(doc,'description','半透明范围层：前后藏、卫藏康安多、工布阿里及元明地域称谓。以现代政区作概略阅读参照，非精确史界。默认显示10A，其余套别可在左侧切换。')
    view(doc,92,32.7,2300000)
    add_ranges(doc,el,view,kcolor,bundled);write_range_index()
    return serialize(root)

def make_post_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='post_road_supplement')
    el(doc,'name','《艽野尘梦》南北驿路原文对照｜直距km与已知耗时');el(doc,'open',1)
    el(doc,'description','按本段主要地名分南北路线。南路是背景，北路为作者进军主线；三十九族按区域，曾科为推定，丹达不冒认精确山口。距离是节点直距，非实走；耗时未记处不估填。')
    view(doc,96.5,30.8,1200000)
    add_post_routes(doc,el,view,kcolor,bundled,True);write_post_indexes()
    return serialize(root)

def make_map(bundled=False):
    root=ET.Element(f'{{{KML}}}kml'); doc=el(root,'Document',id='qiuyechenmeng')
    el(doc,'name','《艽野尘梦》阅读地图｜南北驿路、分区与耗时距离（已校核）')
    el(doc,'open',1)
    el(doc,'description',f'{len(ROWS)}个主要地点及参照点，另补{len(MINOR_PLACES)}处小地名；含耗时、驻留和直线距离（km）。北返江达到丹噶尔：作者自计223日。\n小地名可从08图层点击定位，放大后更易读。虚线仅为示意；距离不是历史实走里程。＊炉城至昌都50余日被校注质疑。农历未换算公历，交叠段不相加。')
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
    minor_styles(doc,bundled)
    guide=el(doc,'Folder');el(guide,'name','00 耗时、距离总览与图例');el(guide,'open',0)
    pm=el(guide,'Placemark');el(pm,'name','地图用法、精度与来源');el(pm,'description',doc.find(f'{{{KML}}}description').text)
    pm=el(guide,'Placemark');el(pm,'name','各段耗时总览｜不能全部相加')
    el(pm,'description','<p>原文日期保留农历；约数、推算和正文与校注分歧分别标明。北返223日是江达到丹噶尔全段，不等于连续断粮或全在无人区。内部16日、5日等均包含在总段内。时间未明的地点不按距离猜测。</p>'+time_html(TIMINGS)+'<h3>资料</h3>'+links(SOURCES.items()))
    pm=el(guide,'Placemark');el(pm,'name','距离总览｜km，直线近似，非实走')
    el(pm,'description',distance_html(DISTANCE_ROWS))
    folders={}
    for key,(name,_,visible) in PHASES.items():
        f=el(doc,'Folder',id='folder_'+key);el(f,'name',name);el(f,'visibility',int(visible));el(f,'open',0);folders[key]=f
        phase_timing=time_html([t for t in TIMINGS if t['phase']==key])
        if key=='wilderness':
            el(f,'description','<p>北返江达到丹噶尔223日；本层只涉及其中荒原段，不能给荒原段单独套用223日。旧名、渡点和迷路行迹不足以复原，不赋假坐标。</p>'+phase_timing)
            view(f,94,33.1,1000000)
        else:
            el(f,'description',phase_timing)
    points={}
    for rid,label,modern,lon,lat,chapter,phase,certainty,coordsource,note in ROWS:
        uncertain=certainty=='校注推定'
        entries=[t for t in TIMINGS if t['anchor']==rid]
        pm=el(folders[phase],'Placemark',id='place_'+rid);el(pm,'name',display_label(rid,label))
        el(pm,'visibility',int(PHASES[phase][2]));el(pm,'Snippet',(entries[-1]['duration']+' · ' if entries else '')+chapter+' · '+certainty,maxLines='2')
        extra=[('地名与行程：原文、校注',TEXT),('坐标参照',coordsource)]
        if rid=='taizhao': extra.append(('江达与太昭：社科院考察',SOURCES['江达与太昭考证']))
        if rid=='changba': extra.append(('长坝春今名考证',SOURCES['旧驿道与长坝春考证']))
        if rid=='lulang': extra.append(('鲁朗镇治迁移',SOURCES['鲁朗镇治迁移']))
        body=f'<h3>{html.escape(label)}</h3><p><b>今名／定位对象：</b>{html.escape(modern)}<br/><b>对应章节：</b>{html.escape(chapter)}<br/><b>定位性质：</b>{certainty}<br/><b>经纬度：</b>{lon:.4f}°E, {lat:.4f}°N</p><p>{html.escape(note)}</p><p>坐标的小数位仅为存储格式，不代表历史位置已精确到米。除特别说明外，使用WGS84兼容地名／地标坐标；定位性质比显示位数更重要。</p><p>'+links(extra)+'</p>'
        related_distances=[d for d in DISTANCE_ROWS if d[1]==rid or d[2]==rid]
        el(pm,'description',time_html(entries)+(distance_html(related_distances) if related_distances else '')+body);view(pm,lon,lat,180000 if rid in ['golmud','qinghai'] else 65000)
        el(pm,'styleUrl','#'+phase+('_uncertain' if uncertain else ''))
        ed=el(pm,'ExtendedData')
        for name,value in [('book_name',label),('modern_name',modern),('chapter',chapter),('certainty',certainty),('coordinate_reference',coordsource),('literary_source',TEXT),('note',note),('travel_time','；'.join(t['segment']+'：'+t['duration'] for t in entries)),('timing_basis','；'.join(t['kind']+'：'+t['basis'] for t in entries))]:
            d=el(ed,'Data',name=name);el(d,'value',value)
        if related_distances:
            d=el(ed,'Data',name='distance_km');el(d,'value','；'.join(PLACE_BY_ID[a][2]+'→'+PLACE_BY_ID[b][2]+f' 直线约{km:.0f} km' for _,a,b,_,km in related_distances))
        pt=el(pm,'Point');el(pt,'altitudeMode','clampToGround');el(pt,'coordinates',f'{lon},{lat},0');points[rid]=(lon,lat)
    # Geometry-free entries are deliberately not dropped: available in the Places tree.
    other=el(doc,'Folder');el(other,'name','07 待考旧地名｜无坐标，不在地球上造点');el(other,'open',0)
    for n,(chapter,name,note) in enumerate(UNLOCATED,1):
        target=folders['wilderness'] if chapter in ['第8章','第9章','第8—10章','第10章'] else other
        p=el(target,'Placemark',id=f'unlocated_{n}');el(p,'name',name+'【未定位】')
        refs=[('原文与校注',TEXT)]
        if name=='恩达': refs.append(('恩达与瓦合山旧驿道实地报道',SOURCES['恩达与瓦合山旧驿道']))
        el(p,'description',f'<h3>{html.escape(name)}</h3><p>{chapter}。{html.escape(note)}</p><p>本条无几何坐标；不会在地球上显示点标。</p>'+links(refs))
    for n,(phase,name,ids) in enumerate(ROUTES,1):
        distance_entries=[d for d in DISTANCE_ROWS if d[0]==name]
        total=sum(d[4] for d in distance_entries)
        p=el(folders[phase],'Placemark',id=f'route_{n}');el(p,'name',name+f'｜示意连线合计约{total:.0f} km')
        el(p,'description',distance_html(distance_entries)+f'<p>各相邻点直距相加约{total:.0f} km。不是首尾直距，也不是古道实走总里程。此合计按未取整数值计算后取整；分段四舍五入数相加可能相差少量km。</p>'+time_html([t for t in TIMINGS if t['phase']==phase])+'<p>只显示主要地点先后及大致方向。虚线人为插值，未按旧道或公路拟合，不可测量历史里程。部分时间是内部子段或驻留，不能全部累加。未知路段留白。</p>')
        el(p,'styleUrl','#'+phase);mg=el(p,'MultiGeometry')
        for a,b in zip(ids,ids[1:]):
            ax,ay=points[a];bx,by=points[b]
            km=111*math.hypot((bx-ax)*math.cos(math.radians((ay+by)/2)),by-ay)
            count=max(2,math.ceil(km/8))
            for seg in range(count):
                t0=seg/count;t1=(seg+0.58)/count
                ls=el(mg,'LineString');el(ls,'tessellate',1);el(ls,'altitudeMode','clampToGround')
                el(ls,'coordinates',f'{ax+(bx-ax)*t0:.6f},{ay+(by-ay)*t0:.6f},0 {ax+(bx-ax)*t1:.6f},{ay+(by-ay)*t1:.6f},0')
    minor_folder(doc)
    add_roads(doc,el,view,kcolor)
    add_ranges(doc,el,view,kcolor,bundled)
    add_post_routes(doc,el,view,kcolor,bundled,False)
    return serialize(root)

def main():
    name='艽野尘梦_阅读地图'
    (ROOT/(name+'.kml')).write_bytes(make_map())
    with zipfile.ZipFile(ROOT/(name+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_map(True))
        for phase,(_,color,_) in PHASES.items():
            z.writestr('icons/'+phase+'.png',png(color))
            z.writestr('icons/'+phase+'_uncertain.png',png('#ffb347',True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
        z.writestr('icons/region_label.png',png('#ffffff'))
        for sid,color,hollow in [('point','#8ad4ff',False),('uncertain','#ffc66d',True),('measure','#cbd5e1',False)]:
            z.writestr('icons/post_'+sid+'.png',png(color,hollow))
    supplement='艽野尘梦_小地名补充'
    (ROOT/(supplement+'.kml')).write_bytes(make_supplement())
    with zipfile.ZipFile(ROOT/(supplement+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    roads='艽野尘梦_现代道路对照'
    road_kml=make_road_supplement()
    (ROOT/(roads+'.kml')).write_bytes(road_kml)
    with zipfile.ZipFile(ROOT/(roads+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',road_kml)
    ranges='艽野尘梦_藏区地理范围'
    (ROOT/(ranges+'.kml')).write_bytes(make_range_supplement())
    with zipfile.ZipFile(ROOT/(ranges+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_range_supplement(True))
        z.writestr('icons/region_label.png',png('#ffffff'))
    post='艽野尘梦_南北驿路对照'
    (ROOT/(post+'.kml')).write_bytes(make_post_supplement())
    with zipfile.ZipFile(ROOT/(post+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_post_supplement(True))
        for sid,color,hollow in [('point','#8ad4ff',False),('uncertain','#ffc66d',True),('measure','#cbd5e1',False)]:
            z.writestr('icons/post_'+sid+'.png',png(color,hollow))
    with (ROOT/'小地名对照与坐标.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['id','name','old_names','modern','lon','lat','chapter','group','certainty','coordinate_source','identity_source','note','timing']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(MINOR_PLACES)
    headers=['id','地图标签','现代定位对象','经度','纬度','章节','图层','定位性质','坐标来源','说明','耗时','耗时依据']
    with (ROOT/'地名对照与坐标.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(headers)
        for row in ROWS:
            entries=[t for t in TIMINGS if t['anchor']==row[0]]
            w.writerow([*row,'；'.join(t['segment']+'：'+t['duration'] for t in entries),'；'.join(t['kind']+'：'+t['basis'] for t in entries)])
    with (ROOT/'行程耗时对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['地点ID','图层','地段／事项','耗时','性质','依据与限制'])
        for t in TIMINGS: w.writerow([t[k] for k in ['anchor','phase','segment','duration','kind','basis']])
    with (ROOT/'行程距离对照_km.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['示意段','起点','终点','口径','直线距离_km','限制'])
        for route,a,b,kind,km in DISTANCE_ROWS: w.writerow([route,PLACE_BY_ID[a][2],PLACE_BY_ID[b][2],kind,round(km),DISTANCE_NOTE])
    (ROOT/'data'/'未定位地名.json').write_text(json.dumps(UNLOCATED,ensure_ascii=False,indent=2)+'\n')
    readme='''《艽野尘梦》阅读地图
制作与核对日期：2026-10-30

一、打开方式
推荐使用“艽野尘梦_阅读地图.kmz”：与KML包含相同地点和连线，并内置全部点标图标。
若先前已导入耗时与距离版，仅导入“艽野尘梦_小地名补充.kmz”即可增加俄洛桥等小地名，避免重复主要地点。
完整版和小地名补充版二选一；不要同时加载两者中的08小地名图层。
Google Earth Pro：文件 → 打开，选择KML或KMZ；在左侧展开各章图层。
Google Earth网页版：使用导入KML/KMZ功能选择本地文件；不同版本入口文字可能不同。
只导入其中一个文件即可，以免出现重复点标。
点击地点可以查看旧名、今名、章节、位置性质和来源。双击地点或文件夹可缩放到相应区域。
“06 现代地理参照”默认隐藏，需要辨认现代县城时可勾选。
“04 北返荒原”和“07 待考旧地名”包含无坐标的文字条目；网页版可能省略这些条目，完整内容亦在本说明下文。

二、内容和图例
29个主要地图点：27个书中地点或区域的代表点，2个默认隐藏的现代县城对照点。
另加9处小地名：俄洛桥、恩达、牙披／阿丕、德摩、冬九、松宗寺、飞越岭、大相岭古道、上八美。
08小地名层可在左侧列表点击，放大后更易读；金色空心点是村域或地区参照，不是确认古址。
支持Region的客户端会按缩放显示小地名；网页版忽略Region，可手动开关08图层控制全景标注数量。
俄洛桥用现代俄洛村参照，未认定清末桥位；西藏桥与俄洛桥的正文／校注差异在弹窗说明。
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
已补行程和驻留耗时：直接显示于主要点标标签、弹窗、图层和耗时总览。
江达至丹噶尔223日是整个北返大段；猎户处至柴达木16日等是子段，不重复相加。
康定至昌都正文50余日被校注质疑，保留分歧；分州至长安7日不误写为兰州至西安7日。
西安停留约2—3个月为叙事粗略推算；其余未明记的时间不按现代距离猜测。
距离统一用km：按代表点的球面近似直线计算，取整，不是历史实际步行或公路里程。
示意线的合计为各相邻点直距之和，既不是首尾直距，也不是全书完整行程。
北返只给江达至丹噶尔起讫直距，不补画未知轨迹，不用223日反推实走距离。

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
行程耗时对照.csv：可核查各段行程、驻留与推算性质。
行程距离对照_km.csv：相邻节点直距及补充起讫直距，单位km。
data/行程耗时.json：耗时原始结构化数据。
data/小地名.json：小地名、坐标、今旧名依据和耗时。
小地名对照与坐标.csv：小地名定位来源；补充KML/KMZ可单独叠加。
data/未定位地名.json：17条待考条目。
scripts/build_map.py：可复现构建脚本，只使用Python标准库。

七、验证范围
KML及KMZ内doc.kml均已通过OGC KML 2.2官方XSD校验。
已检查坐标顺序和范围、样式引用、ID唯一性、KMZ完整性与内置图标引用。
2026-10-30已在Google Earth网页版现有项目中实际导入，抽查丹噶尔标签、弹窗的223日、驻7日与1063 km直距，确认显示并保存到云端硬盘。
网页版提示忽略maxLines和textColor两种样式字段；地点、时间、距离与弹窗可查看，底图精确对位和桌面客户端尚未逐点验收。
同日已将九处小地名补充层叠加导入现有项目，抽查俄洛桥点、定位性质与弹窗并保存到云端硬盘。
小地名层导入提示忽略Region缩放显示条件；九处地名及说明保留，可在地图和图层列表中查看。

八、现代国道省道对照
新增09现代道路层。现代道路为实线，历史行程仍为虚线，可在左侧单独开关。
已导入旧版地图时，只需叠加“艽野尘梦_现代道路对照.kmz”，不必重复导入历史地点。
新版完整阅读地图已包含09层，与现代道路补充版二选一加载，避免重叠。
现代道路路号：G317、G350、G248、G318、G108、G214、G349、G109及S434、S303；S205另留编号核对说明，缺独立几何不冒画。
路号依据交通部门、国家公路网规划及地方政府资料；各路线弹窗列出来源和历史对照限制。
道路实际曲线来自OpenStreetMap，WGS84，2026-10-30提取；按阅读范围裁剪，约30米容差简化。
不是逐点实测或实时路况；缺段不补连，OSM编号与官方编号有差异时在数据来源说明中保留。
G317画炉霍—甘孜—德格—江达—昌都—类乌齐走廊，八美—道孚—炉霍现编号是G350。
G318雅安—二郎山—泸定与书中清溪—飞越岭古道分开；甘孜—德格G317也不等同作者麦宿—八邦寺支线。
S205官方确认娘蒲—太昭路段，但OSM该走廊仍有S303编号；独立几何缺失时仅作说明。完整嘉黎—太昭的规划升级不等于全线已通。S435飞越岭在建新线不画为已通。
G109仅作柴达木及青海湖至兰州的现代方向参照，不据此复原北返荒原轨迹。
现代道路对照.csv：各路号所选方向、数据状态、所绘片段长度km及核实依据；片段线长不是国省道全长、历史里程或导航里程。
data/roads/osm_roads.geojson及manifest.json保留道路几何、提取口径、数据缺口和来源。
道路数据 © OpenStreetMap contributors，Open Database License 1.0（ODbL）。
https://www.openstreetmap.org/copyright
https://opendatacommons.org/licenses/odbl/1-0/
2026-10-30已将现代道路补充KMZ导入现有Google Earth项目，显示处理成功并保存到云端硬盘。
已在俄洛桥—昌都视图抽查G317、G214实线与路号标签，以及历史行程虚线、小地名的同时显示。
'''
    readme=readme.replace('17条',f'{len(UNLOCATED)}条').replace('另加9处',f'另加{len(MINOR_PLACES)}处')
    (ROOT/'地图使用说明.txt').write_text(readme,encoding='utf-8')
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n九、知乎回答的藏区地理范围\n核对日期2026-10-31。新增10范围层，以半透明色块表达文章地理称谓的概略范围。\n现代行政数据只是范围参照；文化地理、元明称谓、自然羌塘与现代政区分套，可单独开关。\n已导入旧版时，可单独叠加“艽野尘梦_藏区地理范围.kmz”，不重复地点或道路。\n2026-10-31已将含10、11层的完整阅读地图导入原Google Earth网页版项目，确认处理完成并保存到云端硬盘。当前显示“南北驿路、分区与耗时距离（已校核）”根目录，旧版根目录已隐藏。\n详细口径、坐标与来源见“藏区地理范围说明.txt”和“藏区范围对照.csv”。\n')
        f.write('\n十、本段南北驿路对照\n新增11层，南路背景、北路进昌都、昌都后北绕及原文另列走法分色显示。\n新增理塘、巴塘、硕督、丹达地区、拉萨对照及曾科候选共6点，三十九族按核心方位区域显示。\n距离仍用代表点直距km；完整阅读图复用原有地点，单独南北驿路KMZ包含17个站点代表点。\n已知耗时按原文与校注保留，未记日数不分摊，南路不套现代G318。详见“南北驿路说明.txt”及两个南北驿路CSV。\n')
    print(f'Created: {len(ROWS)} major + {len(MINOR_PLACES)} minor point markers, {len(UNLOCATED)} unlocated entries, 4 schematic routes.')

if __name__=='__main__':
    main()
