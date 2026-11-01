"""Regional comparison of the three Qinghai–Tibet routes in annotation 54."""
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import el as standalone_el, view as standalone_view, icon_png

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_校注54青藏三道'
CONFIG = ROOT/'data/route_checks/校注54青藏三道.json'
ICON = 'icons/qingzang_three_routes_reference.png'


def load():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def paragraphs(items):
    return ''.join('<p>'+html.escape(str(text))+'</p>' for text in items)


def links(cfg, keys):
    return '<p>'+'<br/>'.join('<a href="'+html.escape(cfg['sources'][key]['url'], quote=True)+'">'
                            +html.escape(cfg['sources'][key]['title'])+'</a>' for key in keys)+'</p>'


def kcolor(color):
    value = color.lstrip('#')
    return 'ff'+value[4:6]+value[2:4]+value[0:2]


def overview_html(cfg):
    return '<h3>'+html.escape(cfg['title'])+'</h3>'+paragraphs(
        [cfg['summary'], cfg['legend'], cfg['methodology'], cfg['scope']])+links(cfg, ['annotation54'])


def line_style(placemark, el, color, width):
    style = el(placemark, 'Style')
    line = el(style, 'LineStyle')
    el(line, 'color', kcolor(color)); el(line, 'width', width)


def point_style(placemark, el, color):
    # Per-feature styles survive Google Earth's nested-folder map-item import.
    style = el(placemark, 'Style')
    icon = el(style, 'IconStyle')
    el(icon, 'color', kcolor(color)); el(icon, 'scale', 0.72)
    el(el(icon, 'Icon'), 'href', ICON)
    label = el(style, 'LabelStyle')
    el(label, 'color', 'ffffffff'); el(label, 'scale', 0.88)


def add_metadata(placemark, el, values):
    metadata = el(placemark, 'ExtendedData')
    for key, value in values:
        el(el(metadata, 'Data', name=key), 'value', value)


def node_html(cfg, node):
    return '<h3>'+html.escape(node['name'])+'</h3>'+paragraphs(
        [node['basis'], node['coordinate_note'], '把握程度：'+node['certainty'], cfg['scope']])\
        +links(cfg, node['source_keys'])


def add_node(folder, el, view, cfg, node):
    point = el(folder, 'Placemark', id='qingzang54_node_'+node['id'])
    el(point, 'name', node['name']); el(point, 'visibility', node.get('visibility', 1))
    el(point, 'description', node_html(cfg, node))
    view(point, node['lon'], node['lat'], node.get('range_m', 250000))
    point_style(point, el, node.get('color', '#f4f1e8'))
    add_metadata(point, el, [('certainty', node['certainty']), ('coordinate_role', node['coordinate_note']),
                             ('basis', node['basis']), ('source_keys', ';'.join(node['source_keys']))])
    geom = el(point, 'Point'); el(geom, 'altitudeMode', 'clampToGround')
    el(geom, 'coordinates', f'{node["lon"]:.6f},{node["lat"]:.6f},0')


def display_distance(a, b):
    """Only controls on-screen dash spacing; never exported as travel mileage."""
    latitude = math.radians((a[1]+b[1])/2)
    return 111*math.hypot((b[0]-a[0])*math.cos(latitude), b[1]-a[1])


def add_geometry(placemark, el, path, dashed):
    geometry = el(placemark, 'MultiGeometry')
    for start, end in zip(path, path[1:]):
        count = max(1, math.ceil(display_distance(start, end)/18)) if dashed else 1
        for index in range(count):
            t0 = index/count
            t1 = (index+0.62)/count if dashed else 1
            points = [[start[0]+(end[0]-start[0])*t, start[1]+(end[1]-start[1])*t] for t in [t0, t1]]
            line = el(geometry, 'LineString'); el(line, 'tessellate', 1)
            el(line, 'altitudeMode', 'clampToGround')
            el(line, 'coordinates', ' '.join(f'{p[0]:.6f},{p[1]:.6f},0' for p in points))


def add_segment(folder, el, view, cfg, group, segment, nodes):
    point = el(folder, 'Placemark', id='qingzang54_segment_'+segment['id'])
    el(point, 'name', segment['name']); el(point, 'visibility', 1)
    el(point, 'description', '<h3>'+html.escape(segment['name'])+'</h3>'+paragraphs(
        [segment['basis'], '把握程度：'+segment['certainty'],
         '虚线只表达校注中的地区先后与联系；河流渡点、山口及合路地点未逐段考定。', cfg['scope']])
        +links(cfg, segment['source_keys']))
    camera = segment.get('camera', cfg['overview'])
    view(point, camera['lon'], camera['lat'], camera['range_m'])
    line_style(point, el, group['color'], group.get('width', 4))
    add_metadata(point, el, [('route_group', group['name']), ('certainty', segment['certainty']),
                             ('geometry_role', '校注54地区关系示意；非精确古道或陈氏行迹'),
                             ('node_order', ' → '.join(nodes[key]['name'] for key in segment['path'])),
                             ('basis', segment['basis'])])
    path = [[nodes[key]['lon'], nodes[key]['lat']] for key in segment['path']]
    add_geometry(point, el, path, segment.get('dashed', True))


def add_qingzang_three_routes(doc, el, view):
    cfg = load(); nodes = {node['id']: node for node in cfg['nodes']}
    folder = el(doc, 'Folder', id='qingzang_annotation54_three_routes')
    el(folder, 'name', cfg['title']); el(folder, 'visibility', 1); el(folder, 'open', 1)
    el(folder, 'description', overview_html(cfg))
    camera = cfg['overview']; view(folder, camera['lon'], camera['lat'], camera['range_m'])
    guide = el(folder, 'Placemark', id='qingzang54_overview')
    el(guide, 'name', '三道总览〔任注路线关系，非陈氏实走线〕')
    el(guide, 'description', overview_html(cfg))
    view(guide, camera['lon'], camera['lat'], camera['range_m'])
    references = el(folder, 'Folder', id='qingzang54_references')
    el(references, 'name', '地区参照〔空心点；旧渡口、山口和合路待考〕')
    el(references, 'visibility', 1); el(references, 'open', 0)
    for node in cfg['nodes']:
        if node.get('display', True):
            add_node(references, el, view, cfg, node)
    for group in cfg['groups']:
        group_folder = el(folder, 'Folder', id='qingzang54_group_'+group['id'])
        el(group_folder, 'name', group['name']); el(group_folder, 'visibility', group.get('visibility', 1))
        el(group_folder, 'open', 0)
        el(group_folder, 'description', paragraphs([group['summary'], cfg['methodology']])
           +links(cfg, group['source_keys']))
        view(group_folder, camera['lon'], camera['lat'], camera['range_m'])
        for segment in cfg['segments']:
            if segment['group'] == group['id']:
                add_segment(group_folder, el, view, cfg, group, segment, nodes)
    for card in cfg['cards']:
        point = el(folder, 'Placemark', id='qingzang54_card_'+card['id'])
        el(point, 'name', card['name'])
        el(point, 'description', '<h3>'+html.escape(card['name'])+'</h3>'
           +paragraphs(card['paragraphs'])+links(cfg, card['source_keys']))
        camera = card.get('camera', cfg['overview'])
        view(point, camera['lon'], camera['lat'], camera['range_m'])
    return folder


def make_supplement():
    cfg = load(); root = ET.Element('{'+KML+'}kml')
    doc = standalone_el(root, 'Document', id='qingzang54_three_routes_supplement')
    standalone_el(doc, 'name', '《艽野尘梦》'+cfg['title']); standalone_el(doc, 'open', 1)
    standalone_el(doc, 'description', overview_html(cfg))
    camera = cfg['overview']; standalone_view(doc, camera['lon'], camera['lat'], camera['range_m'])
    add_qingzang_three_routes(doc, standalone_el, standalone_view)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_index():
    cfg = load(); nodes = {node['id']: node for node in cfg['nodes']}
    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['summary'],
                          cfg['legend'], cfg['methodology'], cfg['scope'], '', '路线分组']
    for group in cfg['groups']:
        lines += [group['name'], group['summary'], '默认显示：'+('是' if group.get('visibility', 1) else '否'), '']
    lines += ['地区工作锚；非旧址坐标']
    for node in cfg['nodes']:
        lines += [node['name'], f'工作锚：{node["lon"]}°E，{node["lat"]}°N；'+node['certainty'],
                  node['basis'], node['coordinate_note'], '']
    lines += ['地区关系示意线；不计算历史实走距离']
    for segment in cfg['segments']:
        lines += [segment['name'], '地区顺序：'+' → '.join(nodes[key]['name'] for key in segment['path']),
                  segment['basis'], '']
    for card in cfg['cards']:
        lines += [card['name'], *card['paragraphs'], '']
    lines += ['来源与限度']
    for key, source in cfg['sources'].items():
        lines += [key+'｜'+source['title'], source['url'], source['supports'], '']
    if cfg.get('google_earth_import'):
        record = cfg['google_earth_import']; lines += ['Google Earth核验', record['note']]
        if record.get('screenshot'): lines += ['核验截图：'+record['screenshot']]
    note = '\n'.join(lines).rstrip()+'\n'
    (ROOT/'校注54青藏三道说明.txt').write_text(note, encoding='utf-8')
    with (ROOT/'校注54青藏三道证据表.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['类型', 'id', '名称', '经度', '纬度', '分组', '节点序列', '把握程度', '依据与限度', '来源键', '来源链接'])
        for node in cfg['nodes']:
            writer.writerow(['地区锚', node['id'], node['name'], node['lon'], node['lat'], '', '', node['certainty'],
                             node['basis']+'；'+node['coordinate_note'], ';'.join(node['source_keys']),
                             ';'.join(cfg['sources'][key]['url'] for key in node['source_keys'])])
        for segment in cfg['segments']:
            writer.writerow(['地区关系线', segment['id'], segment['name'], '', '', segment['group'],
                             ';'.join(segment['path']), segment['certainty'], segment['basis'],
                             ';'.join(segment['source_keys']), ';'.join(cfg['sources'][key]['url'] for key in segment['source_keys'])])
    return note


def write_qingzang_three_route_outputs():
    ET.register_namespace('', KML); raw = make_supplement()
    (ROOT/(NAME+'.kml')).write_bytes(raw)
    icon = icon_png((255, 255, 255)); (ROOT/ICON).parent.mkdir(exist_ok=True)
    (ROOT/ICON).write_bytes(icon)
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw); archive.writestr(ICON, icon)
    return write_index()


if __name__ == '__main__':
    write_qingzang_three_route_outputs()
