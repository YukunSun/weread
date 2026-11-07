"""Modern Qiangtang reference overlay from a preserved OSM community outline."""
from pathlib import Path
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from regional_ranges import insert_styles
from build_jiamiqingbo import icon_png
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_现代羌塘无人区范围'
CONFIG = ROOT/'data/regions/当前羌塘无人区口径.json'


def load():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    data = json.loads((ROOT/cfg['geometry_file']).read_text(encoding='utf-8'))
    if data.get('type') != 'FeatureCollection' or len(data['features']) != 1:
        raise ValueError('Expected one preserved Qiangtang outline feature')
    geometry = data['features'][0]['geometry']
    if geometry['type'] != 'Polygon' or len(geometry['coordinates']) != 1:
        raise ValueError('Expected one exterior ring without invented subzones')
    ring = geometry['coordinates'][0]
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError('Qiangtang outline must be a closed ring')
    for lon, lat, *_ in ring:
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('Invalid outline coordinate')
    if not isinstance(cfg['drawing_area_km2'], (int, float)) or cfg['drawing_area_km2'] <= 0:
        raise ValueError('Verified ellipsoidal drawing area is required before export')
    return cfg, ring


def paragraph(text):
    return '<p>'+html.escape(text)+'</p>'


def area_text(cfg):
    difference = (cfg['official_area_km2']-cfg['drawing_area_km2'])/cfg['official_area_km2']*100
    return (f'官方公布保护区面积约{cfg["official_area_km2"]/10000:.1f}万km²。'
            f'本图OSM轮廓计算约{cfg["drawing_area_km2"]/10000:.2f}万km²'
            f'（较公布面积小约{difference:.1f}%，未调整拟合；WGS84椭球面积）。')


def source_links(cfg):
    return '<p>'+'<br/>'.join('<a href="'+html.escape(s['url'], quote=True)+'">'
                             +html.escape(s['title'])+'</a>' for s in cfg['sources'])+'</p>'


def description(cfg):
    return ('<h3>'+html.escape(cfg['title'])+'</h3>'
            +paragraph(cfg['scope']+' '+area_text(cfg))
            +''.join(paragraph(cfg[key]) for key in ['area_note', 'boundary_note', 'park_note', 'book_note'])
            +paragraph(cfg['data_attribution']+'；'+cfg['data_license'])+source_links(cfg))


def oriented_ring(ring):
    """Preserve all source vertices, reversing only to match KML exterior winding."""
    result = [list(p[:2]) for p in ring]
    signed = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(result,result[1:]))
    if signed == 0:
        raise ValueError('Degenerate Qiangtang ring')
    if signed < 0:
        result.reverse()
    return result


def add_current_qiangtang(doc, el, view, kcolor, bundled=False):
    cfg, ring = load()
    styles = []
    style = el(doc, 'Style', id='current_qiangtang_area_style'); styles.append(style)
    line = el(style, 'LineStyle'); el(line, 'color', kcolor(cfg['color'], 'd0')); el(line, 'width', cfg['line_width'])
    poly = el(style, 'PolyStyle'); el(poly, 'color', kcolor(cfg['color'], cfg['fill_alpha']))
    el(poly, 'fill', 1); el(poly, 'outline', 1)
    style = el(doc, 'Style', id='current_qiangtang_label_style'); styles.append(style)
    iconstyle = el(style, 'IconStyle'); el(iconstyle, 'color', kcolor(cfg['color'])); el(iconstyle, 'scale', 0.4)
    icon = el(iconstyle, 'Icon')
    el(icon, 'href', 'icons/region_label.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    labelstyle = el(style, 'LabelStyle'); el(labelstyle, 'color', 'ffffffff'); el(labelstyle, 'scale', 1.05)
    insert_styles(doc, styles)
    folder = el(doc, 'Folder', id='current_qiangtang_range')
    el(folder, 'name', cfg['title']); el(folder, 'visibility', 1); el(folder, 'open', 1)
    el(folder, 'description', description(cfg))
    view(folder, cfg['view']['lon'], cfg['view']['lat'], cfg['view']['range'])
    area = el(folder, 'Placemark', id='current_qiangtang_osm_outline')
    el(area, 'name', cfg['area_name']); el(area, 'visibility', 1); el(area, 'description', description(cfg))
    view(area, cfg['view']['lon'], cfg['view']['lat'], cfg['view']['range'])
    el(area, 'styleUrl', '#current_qiangtang_area_style')
    metadata = el(area, 'ExtendedData')
    for key, value in [('geometry_role', '保护区社区公开轮廓参照；非官方勘界'),
                       ('source_relation', 'OpenStreetMap relation/8590456 version 10'),
                       ('official_reported_area_km2', cfg['official_area_km2']),
                       ('rendered_ellipsoidal_area_km2', cfg['drawing_area_km2']),
                       ('attribution', cfg['data_attribution']), ('data_license', 'ODbL 1.0')]:
        el(el(metadata, 'Data', name=key), 'value', value)
    polygon = el(area, 'Polygon'); el(polygon, 'tessellate', 1); el(polygon, 'altitudeMode', 'clampToGround')
    boundary = el(polygon, 'outerBoundaryIs'); linear = el(boundary, 'LinearRing')
    el(linear, 'coordinates', ' '.join(f'{lon:.7f},{lat:.7f},0' for lon,lat in oriented_ring(ring)))
    label = el(folder, 'Placemark', id='current_qiangtang_text_label')
    el(label, 'name', cfg['label']['name']); el(label, 'visibility', 1); el(label, 'description', description(cfg))
    el(label, 'styleUrl', '#current_qiangtang_label_style')
    metadata = el(label, 'ExtendedData')
    el(el(metadata, 'Data', name='geometry_role'), 'value', cfg['label']['role'])
    point = el(label, 'Point'); el(point, 'altitudeMode', 'clampToGround')
    el(point, 'coordinates', f'{cfg["label"]["lon"]},{cfg["label"]["lat"]},0')
    return cfg


def make_current_qiangtang(bundled=False):
    cfg, _ = load()
    ET.register_namespace('', KML)
    root = ET.Element('{'+KML+'}kml')

    def el(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, '{'+KML+'}'+tag, attrs)
        if text is not None:
            node.text = str(text)
        return node

    def view(parent, lon, lat, distance):
        node = el(parent, 'LookAt')
        for key, value in [('longitude', lon), ('latitude', lat), ('altitude', 0),
                           ('heading', 0), ('tilt', 0), ('range', distance), ('altitudeMode', 'clampToGround')]:
            el(node, key, value)

    def kcolor(color, alpha='ff'):
        value = color.lstrip('#')
        return alpha+value[4:6]+value[2:4]+value[:2]

    doc = el(root, 'Document', id='current_qiangtang_reference_document')
    el(doc, 'name', cfg['title']); el(doc, 'open', 1); el(doc, 'description', description(cfg))
    view(doc, cfg['view']['lon'], cfg['view']['lat'], cfg['view']['range'])
    add_current_qiangtang(doc, el, view, kcolor, bundled)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_current_qiangtang_outputs():
    cfg, ring = load()
    (output_path('maps', NAME + '.kml')).write_bytes(make_current_qiangtang())
    with zipfile.ZipFile(output_path('maps', NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make_current_qiangtang(True))
        archive.writestr('icons/region_label.png', icon_png((255, 255, 255)))
    note = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['scope'], area_text(cfg),
            cfg['area_note'], cfg['drawing_area_method'], '', cfg['boundary_note'], cfg['park_note'],
            cfg['book_note'], '', '图示与坐标', cfg['coordinate_note'], cfg['label']['role'],
            f'绘制一个保护区公开轮廓面、一个范围文字标签；源环含闭合末点共{len(ring)}个顶点。',
            '蓝青色填充约22%，边线宽2.4；面名保留“OSM轮廓参照，非官方勘界”，画布标签保留© OpenStreetMap署名。',
            '完整阅读地图与独立“'+NAME+'.kmz”均含本层，选择一份显示，避免重复。原10E广义羌塘示意与本层不同，可分别开关对读。',
            '', '数据归属与许可', cfg['data_attribution'], cfg['data_license'], '', '来源与证据限度']
    for source in cfg['sources']:
        note.extend([source['title'], source['url'], source['supports'], ''])
    note.extend(['Google Earth核验：'+cfg['google_earth_import']['status'], cfg['google_earth_import']['note']])
    text = '\n'.join(note)+'\n'
    (output_path('docs', '现代羌塘无人区范围说明.txt')).write_text(text, encoding='utf-8')
    return text


if __name__ == '__main__':
    write_current_qiangtang_outputs()
