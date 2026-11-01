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
from historical_context import add_historical_context, write_historical_index
from rivers import add_rivers, write_river_index
from route_checks import SEQUENCE, CHECK, route_check_html, check_shared_places, write_route_check
from post_routes import load as load_post_routes
from annotation_eleven import add_annotation11, add_deep_research, add_approximate_places, write_annotation11_indexes, unlocated_entries, load as load_annotation11
from annotation11_figure import write_figure
from gongbu_pacification import add_gongbu_pacification, write_gongbu_indexes, unlocated_entries as gongbu_unlocated_entries
from demo_lulang import add_demo_lulang, write_demo_lulang_index
from bomi_campaign_plan import add_campaign_plan, anchor_html as campaign_anchor_html, write_campaign_indexes
from katuo_context import add_katuo_context, write_katuo_index
from mountain_defence import add_mountain_defence, write_mountain_index
from zengba_context import add_zengba_context, write_zengba_outputs
from ningduo_muster import add_ningduo_muster, write_ningduo_outputs
from build_three_mountains import add_horse_retrospective, main as write_three_mountains_outputs
from current_qiangtang import add_current_qiangtang, write_current_qiangtang_outputs
from qaidam_kunlun import add_qaidam_kunlun, write_outputs as write_qaidam_kunlun_outputs

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
    '江巴村现行政归属核查': 'https://www.kangding.gov.cn/gsgg/article/569153',
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
('changba','06 长坝春〔江巴村一带，考证参照〕','康定市塔公镇江巴村一带',101.65,30.20,'第1章；校注6','in','考证对应，旧站确址未定',SOURCES['江巴村地理参照'],'长坝春又作长霸冲、长坝仲。张钦旧驿道研究对应江巴村；论文写瓦泽乡，但现官方资料列塔公镇，已区分历史地名考证与现行政归属。尚无充分证据直接等同新都桥镇中心，两处代表点直距约23 km，见11F对照层。坐标取2021年度官方生态报告PDF第52页表8-2江巴村监测点101.6525、30.20108并舍入至0.01°；原表未注明坐标系，只作地区参照，不指认古驿站或营地。'),
('daofu','07 道坞 → 道孚','道孚鲜水镇',101.1254,30.9777,'第1章','in','对应较明确',wiki('鲜水镇'),'旧称道坞，对应今道孚。使用现代县城聚落代表点。'),
('luhuo','08 霍尔章谷 → 炉霍','炉霍新都镇',100.6803,31.3937,'第1章；校注8','in','对应较明确',wiki('新都镇_(炉霍县)'),'按校注对应炉霍；现代聚落代表点。'),
('garze','09 甘孜','甘孜镇',99.9886,31.6273,'第1章；校注10','in','对应较明确',wiki('甘孜镇'),'校注记后续经打火沟、甑科、麦学、八邦寺，不走雀儿山大道。地图不把德格县城增列为作者亲经站。'),
('dajin','09a 大金寺〔扎西大金寺现代寺区参照〕','甘孜县卡攻乡扎西大金寺一带',99.73,31.67,'第1章；校注10','in','地区参照，坐标基准未明','https://treasuryoflives.org/en/institution/Dargye-Monastery','校注记自甘孜大金寺进打火沟。大金寺与甘孜寺是不同寺院；用Dargye机构条目坐标舍入至0.01°，只作现代寺区参照，不认定1909年具体建筑和营地。打火沟具体支沟、山口未定位，至甑科虚线仅示方向。'),
('zengke','09b 甑科／曾科〔赠科乡地区候选，推定〕','白玉县赠科乡扎马村一带（候选）',99.2955,31.48291,'第1章；校注10','in','古今对应推定','https://www.openstreetmap.org/node/1755809586','校注订曾科为甑科、属白玉县。现代赠科乡扎马村一带与路线方位相合，保留既有候选点；官方水源地坐标可印证现代地区位置，不能证明旧名对应或旧驿站确址。前接大金寺经打火沟方向，后接德格麦宿，均为代表点顺序示意。'),
('maisux','10 麦削／麦学 → 麦宿一带','德格麦宿一带',98.9914,31.6329,'第1章；校注10','in','区域参照',wiki('麦宿镇'),'校注订麦削为麦学、属德格县；交通史研究联系德格麦宿地区。沿用现代麦宿聚落代表点，非旧驿站遗址，不误取白玉另一同名麦学村；前接甑科候选、后接八邦寺，不接德格县城或雀儿山大道。'),
('palpung','11 八邦寺','八邦寺／八蚌寺',98.7960,31.6483,'第1章；校注10','in','对应较明确',wiki('八邦寺'),'原文行程的补充节点来自校注10；与作者正文亲记地点作来源区分。'),
('gangtuo','12 岗拖 → 岗托','金沙江岗托一带',98.5853,31.6326,'第1章','in','对应较明确',wiki('岗托镇'),'金沙江渡口地区。标的是现代岗托聚落，非确定的历史皮船下水点。'),
('tongpu','12a 同普〔同普大路地区参照〕','昌都市江达县同普乡地区',98.3873484,31.5929238,'第1章；校注10','in','现代地区参照','https://www.openstreetmap.org/node/3171594661','校注记岗拖至昌都循同普大路。以今同普乡地名点表示走廊方向，不认定清末旧站或营地。卡工旧名对应尚待考，不直接等同卡贡乡，也不强并同普；卡工以西野宿三日不标作本点至昌都耗时。'),
('chamdo','13 察木多 → 昌都','昌都老城、强巴林寺一带',97.1779,31.1435,'第1—3章','in','对应较明确',wiki('强巴林寺'),'用强巴林寺定位昌都老城，非作者营房遗址。第2章腊左探险确曾抵达恩达；14层按校注十一与书图补地点顺序和被俘、押送、获释过程，中间旧地名确址仍待考。'),
('riwoche','14 类乌齐','类乌齐旧寺镇',96.5036,31.3716,'第3章','west','对应较明确',wiki('类乌齐镇'),'选用旧寺镇，区分今县城桑多镇。恩达、三十九族等中间节点未强行定位。'),
('lhari','15 拉里 → 嘉黎旧镇','嘉黎镇一带',93.3458,30.7423,'第3章','west','区域参照',wiki('嘉黎镇'),'旧粮台所在地区的镇区参照；不是今日阿扎县城。原文回忆与部分史事在校注中有订正。'),
('taizhao','16 江达〔今太昭／江达村一带〕','工布江达县江达村、太昭一带',93.08,30.00,'第3、7、8章','west','区域参照','https://www.fallingrain.com/world/a/T/a/i/z/h/index.html','社科院实地考察将书中江达对应今林芝市工布江达县江达村、太昭古城一带，记述从现代县城沿318国道向西约20公里抵达。此处为北返青海的出发地；不是昌都市江达县，也不是工布江达现代县城。沿用地名表及太昭大桥附近区域的粗略坐标，旧驿站、陈部驻地及出发确址未定。'),
('lulang','17 鲁朗','鲁朗地区',94.7332,29.7257,'第5—7章','pome','区域参照','https://mapcarta.com/N12238762005','使用现代镇驻地作地区参照。镇治曾由东久迁移，旅游小镇与书中驻营地不能直接等同；未确认作者每次驻地。'),
('tongmai','18 汤买／汤木 → 通麦一带','通麦、易贡藏布渡河地区',95.0646,30.0976,'第6章；校注33','pome','区域参照','https://www.upc.pbs.bridgemeister.com/bridge.php?bid=6161','现代通麦桥坐标仅用于定位渡河地区，不认定旧藤桥与今桥重合。'),
('yigong','19 彝贡 → 易贡地区','易贡乡一带',94.8162,30.2699,'第6章','pome','区域参照','https://mapcarta.com/29837964','现代易贡乡聚落代表点，用于查看易贡河谷；不等同书中的军营、登岸点或具体战场。'),
('qundo','20 春多寺 → 倾多寺一带','倾多镇、倾多寺地区',95.6022,30.0577,'第5—7章；校注35','pome','地区参照；作者后来亲到，旧寺确址未定','https://mapcarta.com/N3017464360','校注35将春多寺对应倾多寺，解释春倾寺为混写。第5章为钟颖部署中的第二步目标，不等于已完成行程。第7章另记罗长裿急召陈渠珍至春多寺，陈见密函后辞归卡拖，可认定作者后来到过该地区；不能反推陈参与边军先行攻取或与边军同行。本点取现代倾多聚落代表坐标，非旧寺建筑、会见内室或营地确址；往返卡拖的逐站路线未定，未新增连线。'),
('golmud','21 柴达木 → 格尔木一带（推定）','格尔木地区',94.9042,36.4028,'第11章；校注55','return','校注推定',wiki('格尔木市'),'任乃强按程站推为格尔木一带，不是作者明确写出的今名。使用现代城市代表点；不是当时城市已建成的断言，也不能据此反推羌塘精确轨迹。'),
('qinghai','22 青海 → 青海湖（区域）','青海湖',100.2,36.9,'第11章；校注57','return','区域参照','https://en.wikipedia.org/wiki/Qinghai_Lake','湖面代表点，仅定位整湖。原文及校注记行海南路；不代表到湖心，也不是确定的岸边营地。书中另有“青盐海”，与青海湖分开处理。'),
('riyue','23 日月山','日月山一带',101.0939,36.4431,'第11章；校注58','return','区域参照','https://mapcarta.com/W1425740804','使用日月山景区代表点，未确认旧道具体翻越位置。'),
('huangyuan','24 丹噶尔厅 → 湟源','丹噶尔古城一带',101.2643,36.6890,'第11—12章；校注59','return','对应较明确',wiki('城隍庙_(湟源县)'),'用古城内城隍庙定位丹噶尔老城，非作者旅店。书中到达日期为农历六月二十四，本图未换算为公历。'),
('xining','25 西宁','西宁城区',101.7781,36.6169,'第12章','return','对应较明确',wiki('西宁市'),'现代城市代表点，不指认张镇军衙署或作者所住旅店。'),
('lanzhou','26 兰州','兰州城区',103.8320,36.0610,'第12章','return','对应较明确',wiki('兰州市'),'现代城市代表点；旧炭市街旅店位置未核。'),
('xian','27 长安 → 西安','西安老城一带',108.9453,34.2592,'第12章','return','对应较明确',wiki('西安市'),'全书叙事终点。使用老城范围代表点；洪铺街寓所及墓葬均未精确定位。'),
('gongbo','参照 工布江达现代县城','工布江达县城',93.2462,29.8868,'地理对照','context','背景参照',wiki('工布江达县'),'供辨认今地名。与西北方向的太昭／江达村分开；本图不把现代县城当书中“江达”。'),
('bomi','波密〔历史地区；今扎木镇方位参照〕','今波密县扎木镇，仅作历史波密地区的现代方位参照',95.77055556,29.85916667,'第5—7章；校注33','context','现代镇区方位参照；历史地区范围未复原','https://arhiiv.eki.ee/knab/valik/cn54ny.htm','任乃强校注33区分东北上波（波堆）与西南下波（波密），并说明波部常被汉文统称波密；这是对书中历史地区的地理解释，不将历史范围直接套成今县界。现代波密县1959年设县，县政府驻扎木镇。本点以KNAB扎木镇代表坐标辨认地区方位，不是卡拖、春多寺、嘎朗王宫或具体战场，也不接入作者行军线。第5—7章含多地进退、驻防与等待，不能合并成该点的一次到站或统一用时。'),
]

# Distances are between representative points, never reconstructed walking miles.
PLACE_BY_ID = {r[0]: r for r in ROWS}
CAMPAIGN_ANCHORS = {**{r[0]: r[3:5] for r in ROWS}, **{p['id']: (p['lon'], p['lat']) for p in MINOR_PLACES}}
check_shared_places(PLACE_BY_ID, load_post_routes()[1])
ROUTES = [
    ('in','R1 入藏地点顺序示意',['chengdu','yaan','luding','kangding','zheduo','changba','daofu','luhuo',*SEQUENCE]),
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

UNLOCATED = [('第1章；校注10',i['name'],i['note']) for i in CHECK['unlocated']] + [
('第1章','曾科／甑科旧驿站确址','校注10指白玉县甑科。主图与11层以赠科乡扎马村一带作候选区域参照，古今对应未获直接史证，旧驿站确址仍未定位。'),
('第1章','大相岭旧山口、果亲王摩崖诗','已补大相岭古道的路桥碑地区参照及飞越岭垭口；作者登岭顶与摩崖诗的具体位置仍待考。'),
('第2—3章','恩达汛署／堪布营地','已补今桑多镇恩达村代表点，但汛署及堪布大营遗址未定位。'),
('第3章','三十九族','区域名称，不能当一座城镇。未知作者在该区域的逐站行迹。'),
('第4章；校注27','百马岗召询现场及绕行路线','08层以现代墨脱镇、墨脱村地区点参照校注所指百马岗／白马岗。该点不是召询现场或陈部驻地，历史地区不直接等同现代县界，不能据此断言作者到今县城；正文从窝冗绕行六日、后行四日至德摩与受访者自述路程分别保留，具体路线未定位。'),
('第5—7章','纳衣当噶、八浪登、京中、树枝、央噶','德摩、冬九已补地区参照；此处其余旧山名、聚落仍未逐一核准，未冒用现代公路折线。'),
('第6—7章','卡拖旧驻所、八阶、夥若桥','卡拖另以Kata／Kardag作地区候选；古今对应及罗、陈驻所、喇嘛寺等确址仍未核实，不自动放在波密县城。八阶及夥若桥亦未核定，不把夥若桥直接等同今某座大桥。'),
('第8章','凝多／凝多塘','北返离江达当晚首宿并清点官兵111人，完整段另述作者等4人、全队115人及120余头驮牛。仅明记当晚宿营，不固定驻留24小时或只有一夜；凝多塘／宁多塘对应为旧站序线索，今址仍未核，不赋坐标。后由凝多北行避过拉里，不等于再次经过拉里；详见17层首宿清点说明。'),
('第8章','哈喇乌苏','按校注44指怒江南源阿克河谷；具体聚落、河段存疑，未用今日那曲城区代替。'),
('第8—10章','酱通／绛通（羌塘）','高原区域名称，并非一个可定位的沙漠景区。迷路行迹缺少足够空间约束，本图不复原其折线。'),
('第9章','通天河渡点','跨河本身有文本依据；校注联系穆鲁乌苏水系，但渡点不详，未用现代沱沱河桥或通天河大桥充作历史渡口。'),
('第8—10章','冈天削','向导所述前路地名，正文反复寻找而无明确抵达记录。校注48以巴颜喀喇山脉中的昆仑山口解释，后句仍用“应即”推断两峰间通道；这一解释保留，但尚无独立旧今桥接可定现代确址。G109现代昆仑山口仅作方位参照，不能据此等同冈天削或认定陈部确经，不赋冈天削坐标，也不据后段格尔木推定点复原荒原路线。'),
('第10章','遇蒙古喇嘛、遇猎户地点','事件有原文，地点无可靠坐标，不另造营地。'),
('第11章','盐淖、青盐海','盐沼及盐湖的具体范围未定。青盐海不同于随后到达的青海湖，不直接对应察尔汗、茶卡或柯柯盐湖。'),
('第11章','都兰','校注56作地理推定，未核当时市场位置，不使用今日察汗乌苏县城作为旧市镇的确点。'),
('第12章','分州、洪铺街寓所、西原墓','旧名或具体地点尚待考；地图止于西安，不另画一条书中未叙述的回凤凰路线。'),
]
UNLOCATED += unlocated_entries() + gongbu_unlocated_entries()
UNLOCATED += [('第6章','八噶山、其南大雪山与金珠山旧驻兵地','八噶山未与今八卡村、巴卡寺闭合，大雪山未具专名，均无坐标。金珠山另以金珠拉山口作地形候选，旧驻兵地未定；八百余里的承接对象仍待核，不赋现代km，不绘作者亲到或该队撤退路线。')]
UNLOCATED += [('第7章','甑巴旧宿处与范玉昆住宅','百巴镇增巴村为本段行程较相容候选，甑巴与增巴异写及古今对应仍待考；不指认清末住宅、宿营点或后来遇害处。新增留宿说明，复用15层村落参照，不按一日行程造点或复原古道。')]

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

def minor_folder(doc,places=None):
    places=MINOR_PLACES if places is None else places
    folder=el(doc,'Folder',id='minor_folder');el(folder,'name',f'08 小地名补充｜{len(places)}处（含区域参照）');el(folder,'open',1)
    el(folder,'description','蓝点：现代山口参照；金色空心点：村域、旧名或事件地区参照。支持Region的客户端按缩放显示小地名；Google Earth网页版会忽略此显示条件，可手动开关本层或从列表点击定位。俄洛桥不冒作已测定旧桥位；校注十一与书图的完整旧地名顺序及桥名差异见14层，不按里数给中间旧站造点。')
    view(folder,places[0]['lon'] if len(places)==1 else 97.07278,places[0]['lat'] if len(places)==1 else 31.18528,places[0].get('view_range',160000) if len(places)==1 else 160000)
    groups={}
    minor_by_id={p['id']:p for p in MINOR_PLACES}
    for p in places:
        if p['group'] not in groups:
            f=el(folder,'Folder');el(f,'name',p['group']);el(f,'open',0);groups[p['group']]=f
        pm=el(groups[p['group']],'Placemark',id='minor_'+p['id']);el(pm,'name',p['name'])
        lon,lat=p['lon'],p['lat']
        if p['reference'] in PLACE_BY_ID:
            anchor=PLACE_BY_ID[p['reference']]
            anchor_name=anchor[2];ax,ay=anchor[3:5]
        elif p['reference'] in minor_by_id:
            anchor=minor_by_id[p['reference']]
            anchor_name=anchor['modern'];ax,ay=anchor['lon'],anchor['lat']
        else:
            anchor=load_post_routes()[1][p['reference']]
            anchor_name=anchor['name'];ax,ay=anchor['lon'],anchor['lat']
        phi1,phi2=map(math.radians,[lat,ay]);dphi=phi2-phi1;dl=math.radians(ax-lon)
        h=math.sin(dphi/2)**2+math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
        km=6371.0088*2*math.asin(math.sqrt(min(1,max(0,h))))
        info=(f'<h3>{html.escape(p["name"])}</h3><p><b>书中名：</b>{html.escape(p["old_names"])}<br/>'
              f'<b>现代参照：</b>{html.escape(p["modern"])}<br/><b>章节：</b>{html.escape(p["chapter"])}<br/>'
              f'<b>定位性质：</b>{html.escape(p["certainty"])}</p><p>{html.escape(p["note"])}</p>'
              f'<p><b>耗时：</b>{html.escape(p["timing"])}</p>'
              f'<p><b>距{html.escape(anchor_name)}代表点：直线约{km:.0f} km。</b>只是两代表点间的距离，非书中两站路程；不与全书总里程累加。</p>'
              f'<p><b>经纬度：</b>{lon:.5f}°E, {lat:.5f}°N。小数位不代表古址精度。</p>'+links([
                  ('今名／历史依据',p['identity_source']),('坐标参照',p['coordinate_source']),('原文及任乃强校注',TEXT)]))
        if p.get('literary_quote'): info+='<p><b>书中节引：</b>'+html.escape(p['literary_quote'])+'</p>'
        if p.get('additional_sources'): info+='<p>'+links((s['title'],s['url']) for s in p['additional_sources'])+'</p>'
        if p['id']=='dongjiu': info+=campaign_anchor_html('dongjiu',CAMPAIGN_ANCHORS)
        el(pm,'description',info);view(pm,lon,lat,p.get('view_range',45000))
        el(pm,'styleUrl','#'+('minor_landmark' if p['certainty']=='现代地形点参照' else 'minor_reference'))
        # A display window, not an asserted historical territory or error ellipse.
        reg=el(pm,'Region');box=el(reg,'LatLonAltBox')
        for tag,value in [('north',lat+0.10),('south',lat-0.10),('east',lon+0.12),('west',lon-0.12)]: el(box,tag,value)
        lod=el(reg,'Lod');el(lod,'minLodPixels',32);el(lod,'maxLodPixels',-1)
        ed=el(pm,'ExtendedData')
        for name,value in [('old_names',p['old_names']),('modern_reference',p['modern']),('chapter',p['chapter']),('certainty',p['certainty']),('timing',p['timing']),('reference_distance',f'距{anchor_name}代表点直线约{km:.0f} km'),('note',p['note'])]:
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

def make_gengqing_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='gengqing')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='gengqing_supplement')
    el(doc,'name','《艽野尘梦》更庆｜赵尔丰驻地背景');el(doc,'open',1)
    el(doc,'description','仅新增更庆一处背景点，可叠加到校注十路线校对版。更庆用今德格更庆镇地区参照，赵尔丰驻营确址未定，不接入陈渠珍行军线。')
    view(doc,p['lon'],p['lat'],95000)
    minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)

def make_wusijiang_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='wusijiang')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='wusijiang_supplement')
    el(doc,'name','《艽野尘梦》乌斯江｜拉萨东侧藏军防线背景');el(doc,'open',1)
    el(doc,'description','乌斯江现代聚落地区参照，清末防线确址未定。正文七十里、校注二站及现代直距约99km分列；此处是敌情消息，未接入陈渠珍个人路线。')
    view(doc,91.65,29.68,300000);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)

def make_bianba_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='bianba')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='bianba_supplement')
    el(doc,'name','《艽野尘梦》边坝｜旧宗驻地与战事背景');el(doc,'open',1)
    el(doc,'description','今边坝镇夏林村地区参照，旧宗署及战场确址未定。校注16所述边军战事背景，不接入陈渠珍个人行军线。完整阅读地图与小地名补充版已含此点，选择一份显示。')
    view(doc,p['lon'],p['lat'],65000);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)

def make_worang_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='worang_kaga')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='worang_supplement')
    el(doc,'name','《艽野尘梦》窝冗噶伽｜卧龙—嘎加地区参照');el(doc,'open',1)
    el(doc,'description','用现代卧龙镇村地名点参照窝冗噶伽所在地区，旧庄园、藏经密室及陈营确址未定。从脚木宗行四日与本地办事两个月分开，不画推定行军路线。完整阅读图、小地名补充图与本文件选择一份显示。')
    view(doc,p['lon'],p['lat'],70000);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)


def write_worang_index():
    p=next(p for p in MINOR_PLACES if p['id']=='worang_kaga')
    check=json.loads((ROOT/'data/place_checks/窝冗噶伽核对.json').read_text(encoding='utf-8'))
    note=('窝冗噶伽｜卧龙—嘎加地区参照\n核对日期：'+check['checked_at']+'\n\n'
          +p['note']+'\n\n耗时：'+p['timing']+'\n\n'
          +f'现代地区参照：{p["lon"]}°E，{p["lat"]}°N。\n'+check['coordinate_note']+'\n\n'
          +'完整阅读地图08层、小地名补充版和独立“艽野尘梦_窝冗噶伽.kmz”均包含本点，选择一份显示。新增金色空心地区点，不增画历史路线。\n\n来源及限度\n')
    for source in check['sources']:
        note+='\n'+source['title']+'\n'+source['supports']+'\n'+source['url']+'\n'
    if check.get('pending_sources'):
        note+='\n待核资料\n'
        for source in check['pending_sources']:
            note+='\n'+source['title']+'\n'+source['status']+'\n'+source['url']+'\n'
    if check.get('google_earth_import'):
        note+='\nGoogle Earth核验\n'+check['google_earth_import']['note']+'\n'
        if check['google_earth_import'].get('screenshot'):
            note+='核验截图：'+check['google_earth_import']['screenshot']+'\n'
    (ROOT/'窝冗噶伽核对说明.txt').write_text(note,encoding='utf-8')
    return note


def make_baimagang_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='baimagang')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='baimagang_supplement')
    el(doc,'name','《艽野尘梦》百马岗／白马岗｜墨脱地区参照');el(doc,'open',1)
    el(doc,'description','校注27的地望背景；以现代墨脱镇村地区点帮助辨认百马岗／白马岗所指地区，不是召询现场或作者到今县城的证据。历史地区不直接套现代县界，不画绕行路线。完整阅读图、小地名补充图和本文件选择一份显示。')
    view(doc,p['lon'],p['lat'],p['view_range']);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)


def write_baimagang_index():
    p=next(p for p in MINOR_PLACES if p['id']=='baimagang')
    check=json.loads((ROOT/'data/place_checks/百马岗墨脱核对.json').read_text(encoding='utf-8'))
    note=('百马岗／白马岗｜墨脱地区参照\n核对日期：'+check['checked_at']+'\n\n'
          +p['note']+'\n\n耗时：'+p['timing']+'\n\n'
          +f'现代地区参照：{p["lon"]}°E，{p["lat"]}°N。\n'+check['coordinate_note']+'\n\n'
          +'完整阅读地图08层、小地名补充版和独立“艽野尘梦_百马岗墨脱.kmz”均包含本点，选择一份显示。金色空心点仅作地区背景，不绘县界、召询现场或作者到此路线。\n\n来源及限度\n')
    for source in check['sources']:
        note+='\n'+source['title']+'\n'+source['supports']+'\n'+source['url']+'\n'
    if check.get('google_earth_import'):
        note+='\nGoogle Earth核验\n'+check['google_earth_import']['note']+'\n'
        if check['google_earth_import'].get('screenshot'):
            note+='核验截图：'+check['google_earth_import']['screenshot']+'\n'
    (ROOT/'百马岗墨脱核对说明.txt').write_text(note,encoding='utf-8')
    return note


def make_demo_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='demo')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='demo_supplement')
    el(doc,'name','《艽野尘梦》德摩｜赴此4日；驻月余');el(doc,'open',1)
    el(doc,'description','沿用现代德木寺代表点参照林芝市巴宜区米瑞乡德摩地区，旧寺原址、第巴住宅与陈部驻地确址未定。正文从未定位的访野番处赴此四日、驻月余；此前绕行六日及校注27的四日程另列，不画未知出发点或古道。完整阅读图、小地名补充图和本文件选择一份显示；叠加旧图时隐藏旧08层德摩点，避免重复。')
    view(doc,p['lon'],p['lat'],65000);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)


def write_demo_index():
    p=next(p for p in MINOR_PLACES if p['id']=='demo')
    check=json.loads((ROOT/'data/place_checks/德摩核对.json').read_text(encoding='utf-8'))
    note=('德摩｜赴此4日；驻月余\n核对日期：'+check['checked_at']+'\n\n'
          +p['note']+'\n\n耗时：'+p['timing']+'\n\n'
          +f'现代寺院代表点：{p["lon"]}°E，{p["lat"]}°N。\n'+check['coordinate_note']+'\n\n'
          +'原有08层德摩点已强化标签，不新增重复点。完整阅读地图、小地名补充图、独立“艽野尘梦_德摩定位.kmz”三者选择一份显示；叠加旧图时隐藏原08层德摩点。没有补画未定位的访野番处或历史行军线。\n\n耗时分别列示\n')
    for item in check['timing_distinctions']:
        note+='\n'+item['segment']+'：'+item['duration']+'\n'+item['basis']+'；'+item['scope']+'\n'
    note+='\n来源及限度\n'
    for source in check['sources']:
        note+='\n'+source['title']+'\n'+source['supports']+'\n'+source['url']+'\n'
    if check.get('pending_sources'):
        note+='\n待核资料\n'
        for source in check['pending_sources']:
            note+='\n'+source['title']+'\n'+source['status']+'\n'+source['url']+'\n'
    note+='\nGoogle Earth核验\n'+check['google_earth_import']['note']+'\n'
    (ROOT/'德摩核对说明.txt').write_text(note,encoding='utf-8')
    return note


def make_gongjue_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='gongjue')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='gongjue_supplement')
    el(doc,'name','《艽野尘梦》贡觉｜米瑞广久一带候选');el(doc,'open',1)
    el(doc,'description','书中德摩附近加瓜彭错所在贡觉的地区对应候选；用米瑞乡广久村地名点粗舍入帮助辨认，不是营官旧宅或西原故居坐标，与昌都市贡觉县分开。不画德摩连线、赴宴小路或旧渡点。完整阅读图、小地名补充图和本文件选择一份显示，避免重复。')
    view(doc,p['lon'],p['lat'],p['view_range']);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)


def write_gongjue_index():
    p=next(p for p in MINOR_PLACES if p['id']=='gongjue')
    check=json.loads((ROOT/'data/place_checks/贡觉核对.json').read_text(encoding='utf-8'))
    note=('贡觉｜米瑞广久一带候选；旧宅未定\n核对日期：'+check['checked_at']+'\n\n'
          +p['note']+'\n\n赴宴与返营：'+p['timing']+'\n\n'
          +f'地图粗地区参照：{p["lon"]}°E，{p["lat"]}°N。\n'+check['coordinate_note']+'\n\n'
          +'08层新增金色空心候选点，独立“艽野尘梦_贡觉定位.kmz”、完整阅读图、小地名补充图选择一份显示。德摩参照距离仅为现代两地区代表点直距，未新增相连古道、渡点或私人房屋位置。\n\n地名差异与待核关系\n')
    for item in check['name_ambiguities']:
        note+='\n'+item['name']+'\n'+item['note']+'\n'
        if item.get('source'): note+=item['source']+'\n'
    note+='\n来源及限度\n'
    for source in check['sources']:
        note+='\n'+source['title']+'\n'+source['supports']+'\n'+source['url']+'\n'
    note+='\n原始坐标记录\n'+check['coordinate_record']['local_snapshot']+'\n'
    note+='\nGoogle Earth核验\n'+check['google_earth_import']['note']+'\n'
    (ROOT/'贡觉核对说明.txt').write_text(note,encoding='utf-8')
    return note


def write_bomi_index():
    row=PLACE_BY_ID['bomi']
    check=json.loads((ROOT/'data/place_checks/波密核对.json').read_text(encoding='utf-8'))
    note=('波密｜历史地区；今扎木镇方位参照\n核对日期：'+check['checked_at']+'\n\n'
          +row[9]+'\n\n'
          +f'现代镇区代表点：{row[3]}°E，{row[4]}°N。\n'+check['coordinate_record']['note']+'\n\n'
          +'复用完整阅读地图06现代地理参照层的既有bomi点，主要点数仍为32；本层默认隐藏，需要时从列表显示。旧图可用独立“艽野尘梦_波密地区参照.kmz”补充同一点，须隐藏旧版06层波密点，或与新版主图二选一显示。这是同一地点的独立呈现文件，不是新增历史站点；不绘历史地区边界、王宫点或作者行军线。\n\n'
          +'耗时：'+check['timing_note']+'\n\n来源及限度\n')
    for source in check['sources']:
        note+='\n'+source['title']+'\n'+source['supports']+'\n'+source['url']+'\n'
    if check.get('google_earth_import'):
        note+='\nGoogle Earth核验\n'+check['google_earth_import']['note']+'\n'
        if check['google_earth_import'].get('screenshot'):
            note+='核验截图：'+check['google_earth_import']['screenshot']+'\n'
    (ROOT/'波密核对说明.txt').write_text(note,encoding='utf-8')
    return note


def make_darjeeling_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='darjeeling')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='darjeeling_supplement')
    el(doc,'name','《艽野尘梦》大吉岭｜达赖、夏扎赴印背景');el(doc,'open',1)
    el(doc,'description','印度西孟加拉邦大吉岭城市代表点，说明十三世达赖与夏扎1910年赴英属印度的背景；不是陈渠珍亲到地点，不接入其路线，不标人物住所或同名district边界。具体到达日的记录时序有差异，1910—1912并非在此连续驻留。完整阅读图、小地名补充图和本文件选择一份显示，避免重复。')
    view(doc,p['lon'],p['lat'],p['view_range']);minor_styles(doc,bundled);minor_folder(doc,[p])
    return serialize(root)


def write_darjeeling_index():
    p=next(p for p in MINOR_PLACES if p['id']=='darjeeling')
    check=json.loads((ROOT/'data/place_checks/大吉岭核对.json').read_text(encoding='utf-8'))
    note=('大吉岭｜达赖、夏扎赴印背景\n核对日期：'+check['checked_at']+'\n\n'
          +p['note']+'\n\n时间口径：'+p['timing']+'\n\n'
          +f'现代城市代表点：{p["lon"]}°E，{p["lat"]}°N。\n'+check['coordinate_note']+'\n\n'
          +'08层人物事件背景组中的金色空心点可点击查看。完整阅读地图、小地名补充图、独立“艽野尘梦_大吉岭背景.kmz”选择一份显示；未添加任何出走路线或人物住所。与拉萨仅作现代两城市代表点直距对照，不是出走或陈渠珍行军的距离。\n\n城市与同名地区\n')
    for value in check['city_district_distinction'].values(): note+=value+'\n'
    note+='\n人物身份\n'
    for person in check['people']: note+=person['book_name']+'：'+person['identity']+'\n'+person['scope']+'\n'
    note+='\n日期记录与限度\n'
    for item in check['timing_records']: note+=item['source']+'\n'+item['record']+'\n'+item['limit']+'\n\n'
    note+='资料出处\n'+check['source_provenance']+'\n\n来源及限度\n'
    for source in check['sources']:
        note+='\n'+source['title']+'\n'+source['supports']+'\n'+source['url']+'\n'
        if source.get('access_note'): note+='读取说明：'+source['access_note']+'\n'
    note+='\nGoogle Earth核验\n'+check['google_earth_import']['note']+'\n'
    (ROOT/'大吉岭核对说明.txt').write_text(note,encoding='utf-8')
    return note


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

def jiangda_style(doc,bundled):
    st=el(doc,'Style',id='jiangda')
    ic=el(st,'IconStyle')
    el(ic,'color','ffffffff' if bundled else kcolor(PHASES['west'][1]))
    el(ic,'scale',1.35)
    icon=el(ic,'Icon');el(icon,'href','icons/west.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    lab=el(st,'LabelStyle');el(lab,'color','ffffffff');el(lab,'scale',1.05)
    balloon=el(st,'BalloonStyle');el(balloon,'bgColor','fffafafa');el(balloon,'textColor','ff222222')

def major_place(parent,row):
    rid,label,modern,lon,lat,chapter,phase,certainty,coordsource,note=row
    uncertain='推定' in certainty
    entries=[t for t in TIMINGS if t['anchor']==rid]
    summary_entries=[t for t in entries if t.get('summary',True) and not t['kind'].startswith('校注路程与宿营条件')]
    pm=el(parent,'Placemark',id='place_'+rid);el(pm,'name',display_label(rid,label))
    el(pm,'visibility',int(PHASES[phase][2]));el(pm,'Snippet',(summary_entries[-1]['duration']+' · ' if summary_entries else '')+chapter+' · '+certainty,maxLines='2')
    extra=[('地名与行程：原文、校注',TEXT),('坐标参照',coordsource)]
    if rid=='taizhao': extra.append(('江达与太昭：社科院考察',SOURCES['江达与太昭考证']))
    if rid=='changba': extra.extend([('长坝春今名考证',SOURCES['旧驿道与长坝春考证']),('江巴村现行政归属',SOURCES['江巴村现行政归属核查'])])
    if rid=='lulang': extra.append(('鲁朗镇治迁移',SOURCES['鲁朗镇治迁移']))
    if rid=='bomi': extra.extend([('校注33：波部、上波与下波','https://www.xuges.com/xdwx/qycm/17.htm'),('波密县历史沿革','https://bomi.gov.cn/bmx/zjbm/201901/6e18ca202e204e23a572f56f2b17dfd4.shtml'),('县政府驻扎木镇：官方简介','https://www.bomi.gov.cn/bmx/newxz/202012/ee7bcc2e5e7143c59d7f4725fa059033.shtml')])
    coordinate_note=('KNAB原表为29°51′33″N、95°46′14″E，未明确坐标基准；本点仅为现代扎木镇代表点，显示位数不代表历史地区中心或古址精度。' if rid=='bomi' else '坐标的小数位仅为存储格式，不代表历史位置已精确到米。除特别说明外，使用WGS84兼容地名／地标坐标；定位性质比显示位数更重要。')
    body=f'<h3>{html.escape(label)}</h3><p><b>今名／定位对象：</b>{html.escape(modern)}<br/><b>对应章节：</b>{html.escape(chapter)}<br/><b>定位性质：</b>{certainty}<br/><b>经纬度：</b>{lon:.4f}°E, {lat:.4f}°N</p><p>{html.escape(note)}</p><p>{coordinate_note}</p><p>'+links(extra)+'</p>'
    if rid in ['tongmai','qundo']: body+=campaign_anchor_html(rid,CAMPAIGN_ANCHORS)
    related_distances=[d for d in DISTANCE_ROWS if d[1]==rid or d[2]==rid]
    travel=time_html(entries)+(distance_html(related_distances) if related_distances else '')
    el(pm,'description',body+travel if rid in ['taizhao','bomi'] else travel+body)
    view(pm,lon,lat,240000 if rid=='bomi' else 180000 if rid in ['golmud','qinghai'] else 45000 if rid=='taizhao' else 65000)
    el(pm,'styleUrl','#jiangda' if rid=='taizhao' else '#'+phase+('_uncertain' if uncertain else ''))
    ed=el(pm,'ExtendedData')
    for name,value in [('book_name',label),('modern_name',modern),('chapter',chapter),('certainty',certainty),('coordinate_reference',coordsource),('literary_source',TEXT),('note',note),('travel_time','；'.join(t['segment']+'：'+t['duration'] for t in entries)),('timing_basis','；'.join(t['kind']+'：'+t['basis'] for t in entries))]:
        d=el(ed,'Data',name=name);el(d,'value',value)
    if related_distances:
        d=el(ed,'Data',name='distance_km');el(d,'value','；'.join(PLACE_BY_ID[a][2]+'→'+PLACE_BY_ID[b][2]+f' 直线约{km:.0f} km' for _,a,b,_,km in related_distances))
    pt=el(pm,'Point');el(pt,'altitudeMode','clampToGround');el(pt,'coordinates',f'{lon},{lat},0')

def make_jiangda_supplement(bundled=False):
    row=PLACE_BY_ID['taizhao']
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='jiangda_supplement')
    el(doc,'name','《艽野尘梦》江达｜今太昭／江达村一带');el(doc,'open',1)
    el(doc,'description','仅含江达一处区域参照点，点击查看今名、定位依据及北返耗时。可供旧版地图单独导入；请隐藏旧版02层中的江达点，或与新版完整阅读地图二选一，避免同地点重复显示。旧驿站、陈部驻地及出发确址未定。')
    view(doc,row[3],row[4],45000)
    jiangda_style(doc,bundled);major_place(doc,row)
    return serialize(root)

def make_bomi_supplement(bundled=False):
    row=PLACE_BY_ID['bomi']
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='bomi_supplement')
    el(doc,'name','《艽野尘梦》波密｜历史地区；今扎木镇方位参照');el(doc,'open',1)
    el(doc,'description','同一波密地区参照点的独立呈现文件，以现代扎木镇帮助辨认历史地区；不是卡拖、春多寺、王宫或战场，不绘古界与行军线。可补充旧版地图，请隐藏旧版06层波密点，或与新版完整阅读地图二选一显示。')
    view(doc,row[3],row[4],240000)
    st=el(doc,'Style',id='context');ic=el(st,'IconStyle')
    el(ic,'color','ffffffff' if bundled else kcolor(PHASES['context'][1]));el(ic,'scale',1.05)
    icon=el(ic,'Icon');el(icon,'href','icons/context.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    lab=el(st,'LabelStyle');el(lab,'color','ffffffff');el(lab,'scale',0.85)
    major_place(doc,row)
    doc.find(f'{{{KML}}}Placemark/{{{KML}}}visibility').text='1'
    return serialize(root)

def make_map(bundled=False):
    root=ET.Element(f'{{{KML}}}kml'); doc=el(root,'Document',id='qiuyechenmeng')
    el(doc,'name','《艽野尘梦》阅读地图｜边坝背景补充版')
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
    jiangda_style(doc,bundled)
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
    for row in ROWS:
        major_place(folders[row[6]],row)
        points[row[0]]=row[3:5]
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
        el(p,'description',(route_check_html() if n==1 else '')+distance_html(distance_entries)+f'<p>各相邻点直距相加约{total:.0f} km。不是首尾直距，也不是古道实走总里程。此合计按未取整数值计算后取整；分段四舍五入数相加可能相差少量km。</p>'+time_html([t for t in TIMINGS if t['phase']==phase])+'<p>只显示主要地点先后及大致方向。虚线人为插值，未按旧道或公路拟合，不可测量历史里程。部分时间是内部子段或驻留，不能全部累加。未知路段留白。</p>')
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
    add_historical_context(doc,el,view,kcolor,bundled)
    add_rivers(doc,el,view,kcolor,bundled)
    add_annotation11(doc,el,view,bundled,True)
    add_gongbu_pacification(doc,el,view,kcolor,bundled)
    add_demo_lulang(doc,el,view,reuse_endpoints=True)
    add_campaign_plan(doc,el,view,kcolor,CAMPAIGN_ANCHORS,bundled)
    add_katuo_context(doc,el,view,CAMPAIGN_ANCHORS,bundled)
    add_mountain_defence(doc,el,view,CAMPAIGN_ANCHORS)
    add_zengba_context(doc,el,view)
    add_ningduo_muster(doc,el)
    add_horse_retrospective(doc,el)
    add_current_qiangtang(doc,el,view,kcolor,bundled)
    add_qaidam_kunlun(doc,el,view,kcolor,bundled)
    return serialize(root)

def make_history_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='historical_background_supplement')
    el(doc,'name','《艽野尘梦》瞻对历史背景｜今新龙范围参照');el(doc,'open',1)
    el(doc,'description','历史背景范围，不接入作者个人行程。今县界只作方位参照，三瞻旧界未复原。')
    add_historical_context(doc,el,view,kcolor,bundled)
    return serialize(root)

def make_river_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='river_supplement')
    el(doc,'name','《艽野尘梦》沿途河流｜甘孜雅砻江、岗拖金沙江等');el(doc,'open',1)
    el(doc,'description','河流中心线与渡河地区分别显示；没有给未定位古渡点造坐标。')
    add_rivers(doc,el,view,kcolor,bundled)
    return serialize(root)

def make_annotation11_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='annotation11_supplement')
    el(doc,'name','《艽野尘梦》腊左探险｜可定位地点落点版');el(doc,'open',1)
    el(doc,'description','14B显示四处现代地区参照与梭罗坝、甲木桥、纳贡塘三处大概位置。橙色空心点为推定阅读中心；14G参考圈可开关，不是考定边界。14F另有纳贡山候选；原述里数不固定换算。')
    view(doc,96.92,31.16,155000);minor_styles(doc,bundled)
    add_annotation11(doc,el,view,bundled,True)
    return serialize(root)

def make_enda_approximate_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='enda_approximate_supplement')
    el(doc,'name','《艽野尘梦》恩达河谷三处｜大概位置·推定');el(doc,'open',1)
    el(doc,'description','梭罗坝／林多坝、甲木桥／并达桥、纳贡塘／腊左的阅读约位。橙色空心点按恩达以东的相对顺序与谷地方向设置；旧址未考定。参考圈默认关闭，半径3km仅为查找尺度。新版完整阅读地图已包含三点，二选一显示。')
    view(doc,96.766,31.12,45000)
    add_approximate_places(doc,el,view,bundled)
    return serialize(root)

def make_deep_research_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='annotation11_deep_supplement')
    el(doc,'name','《艽野尘梦》三地深查｜浪荡沟与纳贡候选');el(doc,'open',1)
    el(doc,'description','供叠加旧阅读地图：仅增加浪荡沟地区点、纳贡山候选山口和纳贡塘研究说明。候选不视为确证；已导入本次新版完整图时不必另加此补充图。')
    view(doc,96.91,31.16,110000);minor_styles(doc,bundled)
    add_deep_research(doc,el,view,True)
    return serialize(root)

def make_gongbu_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='gongbu_pacification_supplement')
    el(doc,'name','《艽野尘梦》工布安抚｜曲巴、增巴、脚木宗');el(doc,'open',1)
    el(doc,'description','脚木宗为觉木地区候选；两个增巴均为现代同名候选，尚未选定书中对应。曲巴无坐标，牙披背景参照默认隐藏。整段安抚约2月，脚木宗驻半月不自动相加；未画地理路线。')
    view(doc,93.98,29.73,190000)
    add_gongbu_pacification(doc,el,view,kcolor,bundled)
    return serialize(root)

def make_demo_lulang_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='demo_lulang_supplement')
    el(doc,'name','《艽野尘梦》德摩—鲁朗越岭｜七十里与宿营');el(doc,'open',1)
    el(doc,'description','德摩、现代德木拉山口、鲁朗三处参照点；拉佐仍未定位。山口为德摩大山的对应候选，旧越岭确点及古道未测定，不画插值路线。独立文件含两端点，若叠加旧图请隐藏原德摩与鲁朗点；新版完整图已复用两端点，二选一显示。')
    minor_styles(doc,bundled)
    add_demo_lulang(doc,el,view)
    return serialize(root)

def pack_annotation11_sources(archive):
    for scan in load_annotation11()[0]['scans']:
        relative='data/annotation11/'+scan['file']
        archive.write(ROOT/relative,relative)

def make_campaign_supplement(bundled=False):
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='bomi_campaign_plan_supplement')
    el(doc,'name','《艽野尘梦》波密进军三步部署｜计划与待考')
    el(doc,'open',1)
    el(doc,'description','第5章的三阶段计划：复用冬九、通麦、倾多三个现代地区点，纳衣当噶、八浪登、卡拖及酋长所在地保留无坐标条目。不是三天或已完成的全程，无路线；叠加旧图时隐藏旧版同名点。')
    view(doc,95.17,29.98,175000)
    add_campaign_plan(doc,el,view,kcolor,CAMPAIGN_ANCHORS,bundled,True)
    return serialize(root)

def make_katuo_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='katuo_candidate')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='katuo_consultation_supplement')
    el(doc,'name','《艽野尘梦》卡拖召议与野人山｜休1日；赴此2日')
    el(doc,'open',1)
    el(doc,'description','卡拖以旧图Kata所对应Kardag地区作候选，汉名对应与旧营地仍未确定。陈本人赴卡拖行2日，出发前休息1日；野人山、格布沟保留无坐标背景说明，不画陈追入的路线。完整图、小地名图与独立补图选择一份显示。')
    view(doc,p['lon'],p['lat'],150000)
    minor_styles(doc,bundled);minor_folder(doc,[p])
    add_katuo_context(doc,el,view,CAMPAIGN_ANCHORS,bundled,True)
    return serialize(root)

def make_mountain_defence_supplement(bundled=False):
    p=next(p for p in MINOR_PLACES if p['id']=='jinzhu_la_candidate')
    root=ET.Element(f'{{{KML}}}kml');doc=el(root,'Document',id='baga_jinzhu_supplement')
    el(doc,'name','《艽野尘梦》八噶山与金珠山｜山地候选与八百余里')
    el(doc,'open',1)
    el(doc,'description','金珠山以现代金珠拉山口为候选；八噶山、其南大雪山及驻兵确址未定位。春多仅作原文距离参照地，八百余里承接关系保留待核，不换km或画半径，不画陈本人或驻兵队的路线。完整图、小地名图与独立补图选择一份显示。')
    view(doc,95.70,29.85,200000)
    minor_styles(doc,bundled);folder=minor_folder(doc,[p])
    # Earth web ignores Region; the standalone cloud supplement needs no zoom filter.
    for pm in folder.findall('.//{'+KML+'}Placemark'):
        region=pm.find('{'+KML+'}Region')
        if region is not None: pm.remove(region)
    add_mountain_defence(doc,el,view,CAMPAIGN_ANCHORS,True)
    return serialize(root)

def main():
    # ElementTree has one process-wide default namespace; inline HTML needs unprefixed SVG tags.
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    write_figure()
    ET.register_namespace('', KML)
    name='艽野尘梦_阅读地图'
    (ROOT/(name+'.kml')).write_bytes(make_map())
    with zipfile.ZipFile(ROOT/(name+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_map(True))
        for phase,(_,color,_) in PHASES.items():
            z.writestr('icons/'+phase+'.png',png(color))
            z.writestr('icons/'+phase+'_uncertain.png',png('#ffb347',True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
        z.writestr('icons/annotation11_approximate.png',png('#ffb347',True))
        z.writestr('icons/gongbu_candidate.png',png('#ffb347',True))
        z.writestr('icons/gongbu_reference.png',png('#89d8ff'))
        z.writestr('icons/region_label.png',png('#ffffff'))
        z.writestr('icons/river_label.png',png('#60d4ff'))
        z.writestr('icons/river_crossing.png',png('#ffdc7b',True))
        for sid,color,hollow in [('point','#8ad4ff',False),('uncertain','#ffc66d',True),('measure','#cbd5e1',False)]:
            z.writestr('icons/post_'+sid+'.png',png(color,hollow))
        pack_annotation11_sources(z)
    crossing='艽野尘梦_德摩鲁朗越岭'
    (ROOT/(crossing+'.kml')).write_bytes(make_demo_lulang_supplement())
    with zipfile.ZipFile(ROOT/(crossing+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_demo_lulang_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    crossing_note=write_demo_lulang_index()
    gongbu='艽野尘梦_工布安抚三地'
    (ROOT/(gongbu+'.kml')).write_bytes(make_gongbu_supplement())
    with zipfile.ZipFile(ROOT/(gongbu+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_gongbu_supplement(True))
        z.writestr('icons/gongbu_candidate.png',png('#ffb347',True))
        z.writestr('icons/gongbu_reference.png',png('#89d8ff'))
    gongbu_note=write_gongbu_indexes()
    campaign='艽野尘梦_波密三步部署'
    (ROOT/(campaign+'.kml')).write_bytes(make_campaign_supplement())
    with zipfile.ZipFile(ROOT/(campaign+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_campaign_supplement(True))
        z.writestr('icons/campaign_reference.png',png('#ffd166',True))
    campaign_note=write_campaign_indexes(CAMPAIGN_ANCHORS)
    katuo='艽野尘梦_卡拖与野人山'
    (ROOT/(katuo+'.kml')).write_bytes(make_katuo_supplement())
    with zipfile.ZipFile(ROOT/(katuo+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_katuo_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    katuo_note=write_katuo_index()
    mountain_defence='艽野尘梦_八噶山与金珠山'
    (ROOT/(mountain_defence+'.kml')).write_bytes(make_mountain_defence_supplement())
    with zipfile.ZipFile(ROOT/(mountain_defence+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_mountain_defence_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    mountain_defence_note=write_mountain_index()
    zengba_note=write_zengba_outputs()
    ningduo_note=write_ningduo_outputs()
    horse_note=write_three_mountains_outputs()
    current_qiangtang_note=write_current_qiangtang_outputs()
    qaidam_kunlun_note=write_qaidam_kunlun_outputs()
    annotation11='艽野尘梦_腊左探险校对'
    (ROOT/(annotation11+'.kml')).write_bytes(make_annotation11_supplement())
    with zipfile.ZipFile(ROOT/(annotation11+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_annotation11_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
        z.writestr('icons/annotation11_approximate.png',png('#ffb347',True))
        pack_annotation11_sources(z)
    write_annotation11_indexes()
    approximate='艽野尘梦_恩达河谷三处约位'
    (ROOT/(approximate+'.kml')).write_bytes(make_enda_approximate_supplement())
    with zipfile.ZipFile(ROOT/(approximate+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_enda_approximate_supplement(True))
        z.writestr('icons/annotation11_approximate.png',png('#ffb347',True))
    deep='艽野尘梦_浪荡沟与纳贡深查'
    (ROOT/(deep+'.kml')).write_bytes(make_deep_research_supplement())
    with zipfile.ZipFile(ROOT/(deep+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_deep_research_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    supplement='艽野尘梦_小地名补充'
    (ROOT/(supplement+'.kml')).write_bytes(make_supplement())
    with zipfile.ZipFile(ROOT/(supplement+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    gengqing='艽野尘梦_更庆驻地'
    (ROOT/(gengqing+'.kml')).write_bytes(make_gengqing_supplement())
    with zipfile.ZipFile(ROOT/(gengqing+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_gengqing_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    wusijiang='艽野尘梦_乌斯江防线背景'
    (ROOT/(wusijiang+'.kml')).write_bytes(make_wusijiang_supplement())
    with zipfile.ZipFile(ROOT/(wusijiang+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_wusijiang_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    bianba='艽野尘梦_边坝历史背景'
    (ROOT/(bianba+'.kml')).write_bytes(make_bianba_supplement())
    with zipfile.ZipFile(ROOT/(bianba+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_bianba_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    worang='艽野尘梦_窝冗噶伽'
    (ROOT/(worang+'.kml')).write_bytes(make_worang_supplement())
    with zipfile.ZipFile(ROOT/(worang+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_worang_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    worang_note=write_worang_index()
    baimagang='艽野尘梦_百马岗墨脱'
    (ROOT/(baimagang+'.kml')).write_bytes(make_baimagang_supplement())
    with zipfile.ZipFile(ROOT/(baimagang+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_baimagang_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    baimagang_note=write_baimagang_index()
    demo='艽野尘梦_德摩定位'
    (ROOT/(demo+'.kml')).write_bytes(make_demo_supplement())
    with zipfile.ZipFile(ROOT/(demo+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_demo_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    demo_note=write_demo_index()
    gongjue='艽野尘梦_贡觉定位'
    (ROOT/(gongjue+'.kml')).write_bytes(make_gongjue_supplement())
    with zipfile.ZipFile(ROOT/(gongjue+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_gongjue_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    gongjue_note=write_gongjue_index()
    bomi_note=write_bomi_index()
    bomi='艽野尘梦_波密地区参照'
    (ROOT/(bomi+'.kml')).write_bytes(make_bomi_supplement())
    with zipfile.ZipFile(ROOT/(bomi+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_bomi_supplement(True))
        z.writestr('icons/context.png',png(PHASES['context'][1]))
    darjeeling='艽野尘梦_大吉岭背景'
    (ROOT/(darjeeling+'.kml')).write_bytes(make_darjeeling_supplement())
    with zipfile.ZipFile(ROOT/(darjeeling+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_darjeeling_supplement(True))
        z.writestr('icons/minor_landmark.png',png('#89d8ff'))
        z.writestr('icons/minor_reference.png',png('#ffd166',True))
    darjeeling_note=write_darjeeling_index()
    jiangda='艽野尘梦_江达定位'
    (ROOT/(jiangda+'.kml')).write_bytes(make_jiangda_supplement())
    with zipfile.ZipFile(ROOT/(jiangda+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_jiangda_supplement(True))
        z.writestr('icons/west.png',png(PHASES['west'][1]))
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
    history='艽野尘梦_瞻对历史背景'
    (ROOT/(history+'.kml')).write_bytes(make_history_supplement())
    with zipfile.ZipFile(ROOT/(history+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_history_supplement(True))
        z.writestr('icons/region_label.png',png('#ffffff'))
    write_historical_index()
    rivers='艽野尘梦_沿途河流'
    (ROOT/(rivers+'.kml')).write_bytes(make_river_supplement())
    with zipfile.ZipFile(ROOT/(rivers+'.kmz'),'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',make_river_supplement(True))
        z.writestr('icons/river_label.png',png('#60d4ff'))
        z.writestr('icons/river_crossing.png',png('#ffdc7b',True))
    write_river_index()
    write_route_check(PLACE_BY_ID,distance_km)
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
主要地图点：MAJOR_COUNT个，含书中地点、校注补充地区及2个默认隐藏的现代县城对照点。
另加9处小地名：俄洛桥、恩达、牙披／阿丕、德摩、贡觉（米瑞广久地区候选）、冬九、松宗寺、飞越岭、大相岭古道、上八美、更庆（赵尔丰驻地背景）、大吉岭（达赖、夏扎赴印背景）、边坝（旧宗驻地与战事背景）、乌斯江（藏军防线背景）、窝冗噶伽（卧龙—嘎加地区参照）、百马岗／白马岗（墨脱地区背景参照）。
08小地名层可在左侧列表点击，放大后更易读；金色空心点是村域或地区参照，不是确认古址。
支持Region的客户端会按缩放显示小地名；网页版忽略Region，可手动开关08图层控制全景标注数量。
俄洛桥用现代俄洛村参照，未认定清末桥位；西藏桥与俄洛桥的正文、校注和书图差异在弹窗及14层说明。
4组虚线：蓝色川西入藏，紫色昌都至工布，绿色波密方向，红色青海至西安。
虚线人为连接主要地点，只表示先后与大致方向，不是古道、现代公路或实测轨迹。
橙色空心点：柴达木对应格尔木、甑科对应赠科乡候选等，属于推定。
第2章探险支线、第4章工布活动、第5—7章反复进退未逐段完整复原。
北返荒原，以及太昭至鲁朗、格尔木至青海湖等证据不足的路段，保留空白。
书中江达对应今太昭／江达村一带，不是昌都江达县，也不是工布江达现代县城。
书中哈喇乌苏未径套今日那曲；通天河未用现代桥位作渡点；青盐海与青海湖分开。
不增画西安至凤凰路线，因为正文并未叙述这段归途。

三、精度
这是“主要地点阅读地图”，不是全地名索引或历史GIS精确复原。
现代城市、村镇、寺院或桥梁的代表坐标，不代表历史宿营点、旅店、旧桥、战场或墓地。
坐标采用WGS84兼容地理来源；江巴村官方监测点、大金寺资料未注明坐标系，特意舍入至0.01°，只用于粗略定位。
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
地名对照与坐标.csv：可用表格软件查看MAJOR_COUNT个点的坐标、章节和来源。
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
    readme=readme.replace('MAJOR_COUNT',str(len(ROWS))).replace('17条',f'{len(UNLOCATED)}条').replace('另加9处',f'另加{len(MINOR_PLACES)}处')
    (ROOT/'地图使用说明.txt').write_text(readme,encoding='utf-8')
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n九、知乎回答的藏区地理范围\n核对日期2026-10-31。新增10范围层，以半透明色块表达文章地理称谓的概略范围。\n现代行政数据只是范围参照；文化地理、元明称谓、自然羌塘与现代政区分套，可单独开关。\n已导入旧版时，可单独叠加“艽野尘梦_藏区地理范围.kmz”，不重复地点或道路。\n2026-10-31已将含10、11层的完整阅读地图导入原Google Earth网页版项目，确认处理完成并保存到云端硬盘。当时显示“南北驿路、分区与耗时距离（长坝春核对版）”根目录，旧版根目录已隐藏。\n详细口径、坐标与来源见“藏区地理范围说明.txt”和“藏区范围对照.csv”。\n')
        f.write('\n十、本段南北驿路对照\n新增11层，南路背景、北路进昌都、昌都后北绕及原文另列走法分色显示。\n11层新增理塘、巴塘、硕督、丹达地区、拉萨对照共5点；甑科候选已并入主图，三十九族按核心方位区域显示。\n距离仍用代表点直距km；完整阅读图复用原有地点，单独南北驿路KMZ包含22个地点代表点。\n已知耗时按原文与校注保留，未记日数不分摊，南路不套现代G318。详见“南北驿路说明.txt”及两个南北驿路CSV。\n')
        f.write('\n十一、长坝春与新都桥核对\n2026-10-31复核：现有史地研究支持江巴村一带，不能直接等同新都桥镇中心。现官方资料称塔公镇江巴村。\n历史点保留原地区参照坐标，旧驿站与营地确址未定；11F新增新都桥现代对照点及约23 km直距比较线，该线不属于作者行程。\n详见“长坝春新都桥核对说明.txt”与data/place_checks/长坝春核对.json。\n')
        f.write('\n十二、瞻对／三瞻历史背景\n12层以现代新龙县轮廓作瞻对方位参照，非三瞻旧界，不接入陈渠珍此次个人路线。\n校注八所述鹿传霖事件对应1896—1897年，光绪初的年代表述有误；各次瞻对战事不合并。\n县名沿革年份存在资料异说，详见“瞻对历史背景说明.txt”。已有云端地图可单独叠加“艽野尘梦_瞻对历史背景.kmz”。\n')
        f.write('\n十三、沿途主要河流\n13层显示现代真实河道片段和书中渡河地区，突出甘孜雅砻江、岗拖金沙江，另含泸定桥及通麦易贡相关渡水。\n北返通天河渡点不明，不以今桥定位；怒江南源阿克的河段对应、薄藏布古藤桥位置保留待考。\nOSM河道片段与Natural Earth概化背景分层，缺口不补直线。详见“沿途河流说明.txt”和“河流与渡河对照.csv”。已有云端地图可单独叠加“艽野尘梦_沿途河流.kmz”。\n')
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n十四、校注十甘孜至昌都路线校对\n主图R1与11B北路统一补入大金寺、甑科候选、麦学、八邦寺和同普方向；不经雀儿山大道／德格县城。\n11G有本次校注核对及打火沟、卡工、纳夺的待考说明；卡工以西野宿三日与作者逐段实测耗时分开，距离留空。\n详见“甘孜昌都路线校对说明.txt”及data/route_checks/甘孜昌都校注十.json。\n2026-10-31本校对版完整KMZ已导入原Google Earth项目并显示已保存到云端硬盘，当时启用“《艽野尘梦》阅读地图｜校注十路线校对版”根目录；上一版完整图及旧河流、历史背景补充根目录已隐藏。已抽查大金寺点及R1弹窗的路线顺序、46／33／19 km和卡工以西野宿三日限定。仅Region、maxLines、textColor显示字段被忽略。\n')
        f.write('\n十五、更庆｜赵尔丰驻地背景\n第2章“赵尔丰驻更庆”对应今德格县更庆镇、德格旧城一带。08层新增更庆点，用现代镇区地名点作参照，不指认赵营、衙署或更庆寺内的具体建筑。\n钟颖未应邀前往，更庆不接入作者行军线，不给邀请虚构耗时；与岗拖代表点的距离只作直距比较。\n已有校注十云端图时，仅叠加“艽野尘梦_更庆驻地.kmz”即可。完整图、小地名补充图均含此点，三种文件中只显示一份更庆，避免重复。\n定位依据和原始OSM响应见data/小地名.json及data/place_checks/gengqing_osm_node.json。\n')
        f.write('\n十六、校注十一与书图对读\n新增14层，按第二张书图逐项补昌都、近城西藏桥、俄洛桥、甲令塘、浪荡沟、纳贡山、纳贡塘、甲木桥、梭罗坝、日雨娃、恩达的顺序。果角塘、被擒处、云南桥、瓦合山及恩达河另列背景。\n陈确至恩达，被俘押送与自行侦探分开；约3日2夜为相对分日推算，不把撤兵三日期限当作行程。\n四个现代地区参照继续显示；2026-11-01按用户要求，14B另补梭罗坝、甲木桥、纳贡塘三个橙色空心大概位置。14G的3km参考圈默认关闭，只表示查找尺度；三点不计入古道距离或耗时，其他未知旧站仍留文字条目。纳贡山候选在14F单列，顺序图不编码地理距离。\n校注浪荡沟经俄洛桥至昌都六十里是组合段；正文和校注里数分源列示，不乘0.5换km。\n第一张是出藏全局图；第二张为昌都恩达略图，均不据像素配准。详见“校注十一地图校对说明.txt”、两个“昌都恩达_校注十一”CSV与SVG／HTML对读页。\n独立“艽野尘梦_腊左探险校对.kmz”和完整版均在14B显示四处地区参照与三处大概位置，二选一导入。已有旧云端图时，仅叠加“艽野尘梦_恩达河谷三处约位.kmz”即可；旧图中三处原为无坐标文字条目，不会重复点标。\n')
    wusijiang=next(p for p in MINOR_PLACES if p['id']=='wusijiang')
    check=json.loads((ROOT/'data/place_checks/乌斯江核对.json').read_text())
    note=('乌斯江／乌苏江核对\n\n'+wusijiang['note']+'\n\n耗时：'+wusijiang['timing']+'\n\n'
          f'现代地区参照：{wusijiang["lon"]}°E，{wusijiang["lat"]}°N。\n'
          f'距项目拉萨代表点直线约{check["modern_straight_distance_km"]:.0f} km；非古道或公路里程。\n\n'
          '原文七十里、校注23二站、现代直距km分别保留；不换算出作者行走日数。\n'
          '完整版08小地名层和独立乌斯江补充图均含本点，选择一份显示。背景点不接入作者行军线。\n\n来源\n'
          +wusijiang['coordinate_source']+'\n'+wusijiang['identity_source']+'\n'
          +'\n'.join(s['title']+'\n'+s['url'] for s in wusijiang['additional_sources'])+'\n'
          +'\n2026-11-01已在原Google Earth网页版项目中核验“《艽野尘梦》乌斯江｜拉萨东侧藏军防线背景”图层与乌斯江点标，点位为92.15611111°E、29.70972222°N。地图实际显示金色空心标记，弹窗保留现代地区参照、旧阵地确址未定、七十里与约99 km直距的区别。页面显示“已保存到Google云端硬盘”。本次复用已有标记，未重复导入。核验截图：data/place_checks/wusijiang_google_earth.jpg。\n')
    (ROOT/'乌斯江核对说明.txt').write_text(note)
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n十七、乌斯江／乌苏江藏军防线背景\n'+note)
        f.write('\n十八、江达｜今太昭／江达村一带\n2026-11-01核对。主图02层的16号江达点已突出显示，标签为“江达〔今太昭／江达村一带〕”，点击先显示古今定位和精度说明，再显示耗时与距离。\n社科院考察记从工布江达现代县城沿318国道向西约20公里到江达村、太昭古城。此为书中北返青海的出发地区，与昌都市江达县、现代工布江达县城分别标识。\n沿用约93.08°E、30.00°N区域参照坐标，不指认旧驿站、陈部驻地或出发确址。\n完整阅读地图已包含此点；单独“艽野尘梦_江达定位.kmz”仅含江达，适合旧图补充。导入独立文件时隐藏旧版02层中的江达点；与新版完整图二选一显示，避免重复。\n定位依据：https://www.cass.cn/xueshuchengguo/xscg_lsyjy/202303/t20230317_5608287.shtml\n')
        f.write('2026-11-01已将独立江达KMZ导入原Google Earth网页版项目，确认“江达｜今太昭／江达村一带”根目录与点标出现，旧版“校注十一地点落点版”02层中的江达点已隐藏。已抽查地标坐标、今名、区域参照和旧址未定说明，页面显示已保存到Google云端硬盘。\n')
    bianba=next(p for p in MINOR_PLACES if p['id']=='bianba')
    bianba_check=json.loads((ROOT/'data/place_checks/边坝核对.json').read_text(encoding='utf-8'))
    bianba_note=('边坝｜旧宗驻地与战事背景\n核对日期：2026-11-01\n\n'+bianba['note']+'\n\n'
                 f'图示镇村代表点：{bianba["lon"]}°E，{bianba["lat"]}°N。\n'
                 'KNAB原表30°49′45″N、94°50′46″E，镇中心为Xarling／夏林村；未注明坐标基准，非宗署遗址测绘点。\n'
                 '耗时：'+bianba['timing']+'\n\n'
                 '08小地名层新增金色空心背景点。完整阅读地图、小地名补充图、独立“艽野尘梦_边坝历史背景.kmz”三者选择一份显示，避免重复。\n'
                 'Google Earth核验：'+bianba_check['google_earth_import']['note']+'\n\n来源\n'
                 +bianba['identity_source']+'\n'+bianba['coordinate_source']+'\n'
                 +'\n'.join(s['title']+'\n'+s['url'] for s in bianba['additional_sources'])+'\n')
    (ROOT/'边坝核对说明.txt').write_text(bianba_note,encoding='utf-8')
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n十九、边坝｜旧宗驻地与战事背景\n'+bianba_note)
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n二十、工布安抚｜曲巴、增巴、脚木宗\n'+gongbu_note)
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n二十一、窝冗噶伽｜卧龙—嘎加地区参照\n'+worang_note)
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n二十二、百马岗／白马岗｜墨脱地区参照\n'+baimagang_note)
        f.write('\n二十三、德摩｜赴此4日；驻月余\n'+demo_note)
        f.write('\n二十四、贡觉｜米瑞广久一带候选；旧宅未定\n'+gongjue_note)
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n二十五、波密｜历史地区；今扎木镇方位参照\n'+bomi_note)
        f.write('\n二十六、大吉岭｜达赖、夏扎赴印背景\n'+darjeeling_note)
        f.write('\n波密进军三步部署｜计划与待考\n'+campaign_note)
    with (ROOT/'地图使用说明.txt').open('a',encoding='utf-8') as f:
        f.write('\n德摩—鲁朗越岭｜16层\n'+crossing_note)
        f.write('\n卡拖召议与野人山｜休息1日；赴此2日\n'+katuo_note)
        f.write('\n八噶山与金珠山｜八百余里指代待核\n'+mountain_defence_note)
        f.write('\n甑巴留宿｜百巴增巴候选；范玉昆居留处未定\n'+zengba_note)
        f.write('\n北返首宿凝多｜17层；官兵111、全队115，地点待考\n'+ningduo_note)
        f.write('\n枣骝马与三山｜第8章追叙；山址待考\n'+horse_note)
        f.write('\n现代羌塘无人区｜保护区公开轮廓参照\n'+current_qiangtang_note)
        f.write('\n柴达木盆地与昆仑山口｜现代地理参照\n'+qaidam_kunlun_note)
    print(f'Created: {len(ROWS)} major + {len(MINOR_PLACES)} minor point markers, {len(UNLOCATED)} unlocated entries, 4 schematic routes; Demo–Lulang crossing reference layer and Bomi campaign plan.')

if __name__=='__main__':
    main()
