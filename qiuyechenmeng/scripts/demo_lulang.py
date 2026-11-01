"""Source-labelled reference points for the Demo to Lulang mountain crossing."""
from pathlib import Path
import csv
import html
import json

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'


def load():
    return json.loads((ROOT/'data/route_checks/德摩鲁朗越岭.json').read_text(encoding='utf-8'))


def paragraphs(items):
    return ''.join('<p>'+html.escape(item)+'</p>' for item in items)


def source_links(cfg, keys):
    return '<p>'+'<br/>'.join(
        '<a href="'+html.escape(cfg['sources'][key]['url'], quote=True)+'">'
        +html.escape(cfg['sources'][key]['title'])+'</a>' for key in keys)+'</p>'


def overview_html(cfg):
    return ('<h3>'+html.escape(cfg['title'])+'</h3>'
            +paragraphs([cfg['summary'], '原文顺序：德摩 → 德摩大山 → 拉佐 → 鲁朗宿营。',
                         cfg['scope'], cfg['timing']])
            +'<h3>原文里数，分别保留</h3>'
            +paragraphs([d['segment']+'：'+d['original']+'。'+d['meaning'] for d in cfg['distances']])
            +source_links(cfg, ['book', 'official', 'travel_corridor']))


def point_html(cfg, point):
    return ('<h3>'+html.escape(point['name'])+'</h3>'
            +paragraphs(['定位性质：'+point['certainty'], point['note'],
                         f'现代参照坐标：{point["lon"]}°E，{point["lat"]}°N；小数位不表示历史位置精度。'])
            +source_links(cfg, point['source_keys'])+overview_html(cfg))


def add_demo_lulang(doc, el, view, reuse_endpoints=False):
    cfg = load()
    folder = el(doc, 'Folder', id='demo_lulang_crossing')
    el(folder, 'name', '16 德摩—鲁朗越岭｜七十里；拉佐待考')
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(cfg)
       +paragraphs(['蓝色点为现代两端地区参照；金色空心点为现代山口及历史对应候选。现有主图只新增山口点并复用德摩、鲁朗；独立补充包含三点。未绘古道连线。']))
    view(folder, 94.69, 29.62, 70000)
    for point in cfg['points']:
        body = point_html(cfg, point)
        marker_id = point.get('shared_marker_id')
        if reuse_endpoints and marker_id:
            existing = doc.find('.//{'+KML+'}Placemark[@id="'+marker_id+'"]')
            if existing is None:
                raise ValueError('Missing shared crossing endpoint: '+marker_id)
            coordinates = existing.find('{'+KML+'}Point/{'+KML+'}coordinates').text
            actual = tuple(float(n) for n in coordinates.split(',')[:2])
            if actual != (point['lon'], point['lat']):
                raise ValueError('Crossing endpoint differs from main map: '+point['id'])
            description = existing.find('{'+KML+'}description')
            description.text = (description.text or '')+overview_html(cfg)
            pm = el(folder, 'Placemark', id='crossing_reference_'+point['id'])
            el(pm, 'name', point['name']+'【复用主图点】')
        else:
            pm = el(folder, 'Placemark', id='crossing_point_'+point['id'])
            el(pm, 'name', point['name'])
        el(pm, 'description', body)
        view(pm, point['lon'], point['lat'], 25000)
        if not (reuse_endpoints and marker_id):
            el(pm, 'styleUrl', '#minor_reference' if point['id']=='demu_la' else '#minor_landmark')
        data = el(pm, 'ExtendedData')
        for name, value in [('certainty', point['certainty']), ('chapter', cfg['chapter']),
                            ('route_role', '现代参照点；历史越岭路线未测定')]:
            item = el(data, 'Data', name=name)
            el(item, 'value', value)
        if not (reuse_endpoints and marker_id):
            geometry = el(pm, 'Point')
            el(geometry, 'altitudeMode', 'clampToGround')
            el(geometry, 'coordinates', f'{point["lon"]},{point["lat"]},0')
    for place in cfg['unlocated']:
        pm = el(folder, 'Placemark', id='crossing_unlocated_'+place['id'])
        el(pm, 'name', place['name']+'【无坐标】')
        el(pm, 'description', paragraphs([place['note']])+overview_html(cfg))
    pm = el(folder, 'Placemark', id='crossing_original_distances')
    el(pm, 'name', '七十里全程／十余里途中／山高十五里｜不相加、不换海拔')
    el(pm, 'description', overview_html(cfg))
    return folder


def write_demo_lulang_index():
    cfg = load()
    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['quote'], '',
             cfg['summary'], cfg['scope'], '', cfg['timing'], '']
    for point in cfg['points']:
        lines += [point['name'], point['certainty'],
                  f'{point["lon"]}°E，{point["lat"]}°N', point['note'], '']
    for place in cfg['unlocated']:
        lines += [place['name']+'【无坐标】', place['note'], '']
    lines += [d['segment']+'：'+d['original']+'。'+d['meaning'] for d in cfg['distances']]
    lines += ['', cfg['coordinate_provenance'], '',
              '主图16层复用08层德摩点和03层鲁朗点，只新增现代山口参照。独立“艽野尘梦_德摩鲁朗越岭.kmz”含三点与拉佐无坐标说明；与新版完整图二选一显示。叠加旧版项目时，隐藏旧德摩、鲁朗两点以避免重复。',
              '未知古道不画插值连线；不把现代山口点当作陈部越岭确址，不接入现代公路折线。部分客户端可能省略无坐标条目，拉佐信息亦保留在文件夹说明、各点弹窗和本TXT中。',
              cfg['google_earth_import']['note'], '', '来源']
    for source in cfg['sources'].values():
        lines += [source['title'], source['url']]
    note = '\n'.join(lines)+'\n'
    (ROOT/'德摩鲁朗越岭核对说明.txt').write_text(note, encoding='utf-8')
    with (ROOT/'德摩鲁朗_地点与里数.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['类别', '名称或地段', '经度', '纬度', '性质或原文里数', '说明'])
        for point in cfg['points']:
            writer.writerow(['地点参照', point['name'], point['lon'], point['lat'], point['certainty'], point['note']])
        for place in cfg['unlocated']:
            writer.writerow(['未定位', place['name'], '', '', '旧名待考', place['note']])
        for distance in cfg['distances']:
            writer.writerow(['原文尺度', distance['segment'], '', '', distance['original'], distance['meaning']])
    return note
