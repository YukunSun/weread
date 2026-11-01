"""A revisable regional route hypothesis, separate from the recorded travel totals."""
from pathlib import Path
import csv
import html
import json
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import el as standalone_el, view as standalone_view, icon_png
from hala_wusu_approx import add_hala_wusu_approx, reference_icon, ICON_PATH

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_北返推测路线'
REFERENCE_ICON = 'icons/north_return_reference.png'


def load():
    return json.loads((ROOT/'data/route_checks/北返推测路线.json').read_text(encoding='utf-8'))


def links(cfg, keys):
    return '<p>'+'<br/>'.join('<a href="'+html.escape(cfg['sources'][k]['url'], quote=True)+'">'
                            +html.escape(cfg['sources'][k]['title'])+'</a>' for k in keys)+'</p>'


def paragraphs(items):
    return ''.join('<p>'+html.escape(text)+'</p>' for text in items)


def overview_html(cfg):
    return '<h3>'+html.escape(cfg['title'])+'</h3>'+paragraphs(
        [cfg['summary'], cfg['legend'], cfg['methodology'], cfg['scope']])


def add_point_style(placemark, el, modern):
    # Inline styles survive Google Earth's map-item import for nested folders.
    style = el(placemark, 'Style')
    iconstyle = el(style, 'IconStyle')
    el(iconstyle, 'color', 'ffffffff'); el(iconstyle, 'scale', 1.05)
    el(el(iconstyle, 'Icon'), 'href', REFERENCE_ICON if modern else ICON_PATH)
    label = el(style, 'LabelStyle')
    el(label, 'color', 'ffffffff'); el(label, 'scale', 0.8)


def add_line_style(placemark, el):
    style = el(placemark, 'Style')
    line = el(style, 'LineStyle')
    el(line, 'color', 'c03399ff'); el(line, 'width', 2)


def add_node(folder, el, view, cfg, node, alternative=False):
    point = el(folder, 'Placemark', id='north_return_'+node['id'])
    el(point, 'name', node['name']); el(point, 'visibility', 1)
    el(point, 'description', '<h3>'+html.escape(node['name'])+'</h3>'
       +paragraphs(['把握程度：'+node['certainty'], node['basis'], cfg['scope']])
       +links(cfg, node['source_keys']))
    view(point, node['lon'], node['lat'], 200000)
    modern = node.get('role') == 'reference' or node['id'] in ['taizhao', 'riyue', 'huangyuan']
    add_point_style(point, el, modern)
    metadata = el(point, 'ExtendedData')
    for name, value in [('certainty', node['certainty']), ('basis', node['basis']),
                        ('source_keys', ','.join(node['source_keys'])),
                        ('coordinate_role', '备选地区；默认关闭' if alternative else '阅读工作锚；非历史确址')]:
        el(el(metadata, 'Data', name=name), 'value', value)
    geometry = el(point, 'Point')
    el(geometry, 'altitudeMode', 'clampToGround')
    el(geometry, 'coordinates', f'{node["lon"]:.6f},{node["lat"]:.6f},0')


def add_segment(folder, el, view, cfg, segment, nodes):
    placemark = el(folder, 'Placemark', id='north_return_segment_'+segment['id'])
    el(placemark, 'name', segment['name']); el(placemark, 'visibility', 1)
    el(placemark, 'description', '<h3>'+html.escape(segment['name'])+'</h3>'
       +paragraphs([segment['certainty'], segment['basis'], '时日：'+segment['duration'],
                    '细虚线为地区间推测连接，省略实际绕折；未恢复古道，未计历史实走公里数。'])
       +links(cfg, segment['source_keys']))
    camera = cfg['overview']; view(placemark, camera['lon'], camera['lat'], camera['range_m'])
    add_line_style(placemark, el)
    metadata = el(placemark, 'ExtendedData')
    for name, value in [('from', segment['from']), ('to', segment['to']),
                        ('certainty', segment['certainty']), ('basis', segment['basis']),
                        ('duration', segment['duration']), ('source_keys', ','.join(segment['source_keys']))]:
        el(el(metadata, 'Data', name=name), 'value', value)
    geometry = el(placemark, 'MultiGeometry')
    a, b = nodes[segment['from']], nodes[segment['to']]
    path = [[a['lon'], a['lat']], *segment.get('via', []), [b['lon'], b['lat']]]
    for start, end in zip(path, path[1:]):
        for n in range(12):
            coords = [f'{start[0]+(end[0]-start[0])*t:.6f},{start[1]+(end[1]-start[1])*t:.6f},0'
                      for t in [n/12, (n+0.50)/12]]
            line = el(geometry, 'LineString'); el(line, 'tessellate', 1)
            el(line, 'altitudeMode', 'clampToGround'); el(line, 'coordinates', ' '.join(coords))


def add_north_return_hypothesis(doc, el, view, standalone=False):
    cfg = load(); folder = el(doc, 'Folder', id='north_return_hypothesis')
    el(folder, 'name', cfg['title']); el(folder, 'visibility', 1); el(folder, 'open', 1)
    el(folder, 'description', overview_html(cfg))
    camera = cfg['overview']; view(folder, camera['lon'], camera['lat'], camera['range_m'])
    guide = el(folder, 'Placemark', id='north_return_overview')
    el(guide, 'name', cfg['route_name']); el(guide, 'description', overview_html(cfg))
    view(guide, camera['lon'], camera['lat'], camera['range_m'])
    nodes = {n['id']: n for n in cfg['nodes']}
    for node in cfg['nodes']:
        if node['role'] in ['shared_hala', 'control'] or (node['role'] == 'existing' and not standalone):
            continue
        add_node(folder, el, view, cfg, node)
    for segment in cfg['segments']:
        add_segment(folder, el, view, cfg, segment, nodes)
    alternatives = el(folder, 'Folder', id='north_return_alternatives')
    el(alternatives, 'name', '备选与未到目标〔默认关闭；不接主线〕'); el(alternatives, 'visibility', 0)
    for node in cfg['alternatives']:
        add_node(alternatives, el, view, cfg, node, True)
    for card in cfg['cards']:
        placemark = el(folder, 'Placemark', id='north_return_card_'+card['id'])
        el(placemark, 'name', card['name'])
        el(placemark, 'description', '<h3>'+html.escape(card['name'])+'</h3>'
           +paragraphs(card['paragraphs'])+links(cfg, card['source_keys']))
        view(placemark, camera['lon'], camera['lat'], camera['range_m'])
    return folder


def make_supplement():
    cfg = load(); root = ET.Element('{'+KML+'}kml')
    doc = standalone_el(root, 'Document', id='north_return_hypothesis_supplement')
    standalone_el(doc, 'name', '《艽野尘梦》'+cfg['title']); standalone_el(doc, 'open', 1)
    standalone_el(doc, 'description', overview_html(cfg))
    camera = cfg['overview']; standalone_view(doc, camera['lon'], camera['lat'], camera['range_m'])
    add_north_return_hypothesis(doc, standalone_el, standalone_view, True)
    add_hala_wusu_approx(doc, standalone_el, standalone_view)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_index():
    cfg = load()
    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['summary'], cfg['legend'],
             cfg['methodology'], cfg['scope'], '', '节点与证据']
    for node in cfg['nodes']:
        lines += [node['id']+'｜'+node['name'], f'工作锚：{node["lon"]}°E，{node["lat"]}°N；'+node['certainty'],
                  node['basis'], '来源键：'+', '.join(node['source_keys']), '']
    lines += ['主候选推测段；所有线均非已核实走路线']
    for segment in cfg['segments']:
        lines += [segment['id']+'｜'+segment['name'], segment['basis'], segment['duration'], '']
    lines += ['备选；默认关闭']
    for node in cfg['alternatives']:
        lines += [node['name'], node['basis'], '']
    for card in cfg['cards']:
        lines += [card['name'], *card['paragraphs'], '']
    lines += ['完整地图复用江达、格尔木、日月山、丹噶尔及哈喇约位点；独立综合包显示终点地区参照，'
              '并通过原模块复用哈喇乌苏点，不重复原校注44五卡。原个人行程统计不变。', '', '来源与限度']
    for key, source in cfg['sources'].items():
        lines += [key+'｜'+source['title'], source['url'], source['supports'], '']
    if cfg.get('google_earth_import'):
        record = cfg['google_earth_import']; lines += ['Google Earth核验', record['note']]
        if record.get('screenshot'): lines += ['核验截图：'+record['screenshot']]
    note = '\n'.join(lines).rstrip()+'\n'
    (ROOT/'北返推测路线说明.txt').write_text(note, encoding='utf-8')
    with (ROOT/'北返推测路线证据表.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['类型', 'id', '名称', '经度', '纬度', '起点', '终点', '把握程度', '依据与限度', '时日口径', '来源键', '来源链接'])
        for kind, items in [('节点', cfg['nodes']), ('备选；默认关闭', cfg['alternatives'])]:
            for node in items:
                writer.writerow([kind, node['id'], node['name'], node['lon'], node['lat'], '', '', node['certainty'], node['basis'], '',
                                 ';'.join(node['source_keys']), ';'.join(cfg['sources'][k]['url'] for k in node['source_keys'])])
        for segment in cfg['segments']:
            writer.writerow(['推测段', segment['id'], segment['name'], '', '', segment['from'], segment['to'], segment['certainty'],
                             segment['basis'], segment['duration'], ';'.join(segment['source_keys']),
                             ';'.join(cfg['sources'][k]['url'] for k in segment['source_keys'])])
    return note


def write_north_return_outputs():
    ET.register_namespace('', KML); raw = make_supplement()
    (ROOT/(NAME+'.kml')).write_bytes(raw)
    icon = icon_png((96, 180, 255)); (ROOT/REFERENCE_ICON).parent.mkdir(exist_ok=True)
    (ROOT/REFERENCE_ICON).write_bytes(icon)
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw); archive.writestr(ICON_PATH, reference_icon())
        archive.writestr(REFERENCE_ICON, icon)
    return write_index()


if __name__ == '__main__':
    write_north_return_outputs()
