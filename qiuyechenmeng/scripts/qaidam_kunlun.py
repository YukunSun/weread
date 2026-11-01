"""Qaidam basin context and a separately identified modern Kunlun Pass."""
from pathlib import Path
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from regional_ranges import insert_styles
from build_jiamiqingbo import icon_png

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_柴达木盆地与昆仑山口参照'
CONFIG = ROOT/'data/regions/柴达木盆地口径.json'
PASS = ROOT/'data/place_checks/冈天削与昆仑山口核对.json'


def load():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    mountain = json.loads(PASS.read_text(encoding='utf-8'))
    feature = json.loads((ROOT/cfg['geometry_file']).read_text(encoding='utf-8'))
    if feature['type'] == 'FeatureCollection':
        if len(feature['features']) != 1:
            raise ValueError('Expected one preserved basin feature')
        geometry = feature['features'][0]['geometry']
    elif feature['type'] == 'Feature':
        geometry = feature['geometry']
    else:
        raise ValueError('Expected a traceable basin feature')
    if geometry['type'] not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Expected a basin polygon')
    groups = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    for rings in groups:
        for ring in rings:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError('Basin rings must already be closed')
            for lon, lat, *_ in ring:
                if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError('Invalid basin coordinate')
    return cfg, mountain, groups


def p(text):
    return '<p>'+html.escape(str(text))+'</p>'


def links(data):
    return '<p>'+'<br/>'.join('<a href="'+html.escape(s['url'], quote=True)+'">'+html.escape(s['title'])+'</a>'
                             for s in data['sources'])+'</p>'


def basin_description(cfg):
    return ('<h3>'+html.escape(cfg['range_name'])+'</h3>'
            +''.join(p(cfg[key]) for key in ('scope', 'area_note', 'boundary_note', 'book_note', 'attribution_note'))
            +links(cfg))


def mountain_description(data):
    return ('<h3>'+html.escape(data['title'])+'</h3>'+p(data['quote'])
            +p(data['scope'])+p(data['reading_note'])
            +p(data['modern_reference']['coordinate_role'])
            +p(data['modern_reference']['source_coordinate'])
            +p(data['modern_reference']['attribution']+'；现代山口坐标数据遵循ODbL 1.0。')+links(data))


def add_qaidam_kunlun(doc, el, view, kcolor, bundled=False):
    cfg, mountain, groups = load()
    styles = []
    style = el(doc, 'Style', id='qaidam_basin_area_style'); styles.append(style)
    line = el(style, 'LineStyle'); el(line, 'color', kcolor(cfg['color'], 'd0')); el(line, 'width', 2.2)
    poly = el(style, 'PolyStyle'); el(poly, 'color', kcolor(cfg['color'], '38')); el(poly, 'fill', 1); el(poly, 'outline', 1)
    for identity, color, scale in [('qaidam_basin_label_style', cfg['color'], 0.4),
                                   ('kunlun_modern_reference_style', '#bcc9d6', 0.8)]:
        style = el(doc, 'Style', id=identity); styles.append(style)
        icon = el(style, 'IconStyle'); el(icon, 'color', kcolor(color)); el(icon, 'scale', scale)
        el(el(icon, 'Icon'), 'href', 'icons/region_label.png' if bundled else
           'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        label = el(style, 'LabelStyle'); el(label, 'color', 'ffffffff'); el(label, 'scale', 1.0)
    insert_styles(doc, styles)
    folder = el(doc, 'Folder', id='qaidam_kunlun_context')
    el(folder, 'name', cfg['title']); el(folder, 'visibility', 1); el(folder, 'open', 1)
    el(folder, 'description', basin_description(cfg)+mountain_description(mountain))
    view(folder, cfg['view']['lon'], cfg['view']['lat'], cfg['view']['range'])
    area = el(folder, 'Placemark', id='qaidam_basin_reference_area')
    el(area, 'name', cfg['range_name']); el(area, 'visibility', 1)
    el(area, 'description', basin_description(cfg))
    view(area, cfg['view']['lon'], cfg['view']['lat'], cfg['view']['range'])
    el(area, 'styleUrl', '#qaidam_basin_area_style')
    meta = el(area, 'ExtendedData')
    for key, value in [('geometry_role', cfg['geometry_role']), ('source_crs', cfg['source_crs']),
                       ('coordinate_transform', cfg['coordinate_transform']), ('attribution', cfg['attribution_note'])]:
        el(el(meta, 'Data', name=key), 'value', value)
    container = area if len(groups) == 1 else el(area, 'MultiGeometry')
    for rings in groups:
        polygon = el(container, 'Polygon'); el(polygon, 'tessellate', 1); el(polygon, 'altitudeMode', 'clampToGround')
        for i, ring in enumerate(rings):
            points = [list(point[:2]) for point in ring]
            signed = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]))
            if signed == 0:
                raise ValueError('Degenerate basin ring')
            if (signed > 0) != (i == 0):
                points.reverse()
            boundary = el(polygon, 'outerBoundaryIs' if i == 0 else 'innerBoundaryIs')
            el(el(boundary, 'LinearRing'), 'coordinates', ' '.join(f'{lon},{lat},0' for lon, lat in points))
    label = el(folder, 'Placemark', id='qaidam_basin_text_label')
    el(label, 'name', cfg['label']['name']); el(label, 'visibility', 1)
    el(label, 'description', basin_description(cfg)+p(cfg['label']['role']))
    el(label, 'styleUrl', '#qaidam_basin_label_style')
    point = el(label, 'Point'); el(point, 'altitudeMode', 'clampToGround')
    el(point, 'coordinates', f'{cfg["label"]["lon"]},{cfg["label"]["lat"]},0')
    card = el(folder, 'Placemark', id='gangtianxiao_unlocated_note')
    el(card, 'name', '冈天削｜校注指昆仑山口，确址待考')
    el(card, 'description', mountain_description(mountain))
    meta = el(card, 'ExtendedData')
    el(el(meta, 'Data', name='geometry_role'), 'value', '无几何说明卡；不为冈天削分配坐标')
    modern = mountain['modern_reference']
    mark = el(folder, 'Placemark', id='kunlun_pass_modern_reference')
    el(mark, 'name', modern['name']); el(mark, 'visibility', 1)
    el(mark, 'description', mountain_description(mountain))
    view(mark, modern['lon'], modern['lat'], 90000)
    el(mark, 'styleUrl', '#kunlun_modern_reference_style')
    meta = el(mark, 'ExtendedData')
    el(el(meta, 'Data', name='coordinate_role'), 'value', modern['coordinate_role'])
    point = el(mark, 'Point'); el(point, 'altitudeMode', 'clampToGround')
    el(point, 'coordinates', f'{modern["lon"]},{modern["lat"]},0')
    return cfg


def make(bundled=False):
    cfg, _, _ = load()
    ET.register_namespace('', KML)
    root = ET.Element('{'+KML+'}kml')

    def el(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, '{'+KML+'}'+tag, attrs)
        if text is not None:
            node.text = str(text)
        return node

    def view(parent, lon, lat, distance):
        node = el(parent, 'LookAt')
        for key, value in [('longitude', lon), ('latitude', lat), ('altitude', 0), ('heading', 0),
                           ('tilt', 0), ('range', distance), ('altitudeMode', 'clampToGround')]:
            el(node, key, value)

    def kcolor(color, alpha='ff'):
        value = color.lstrip('#')
        return alpha+value[4:6]+value[2:4]+value[:2]

    doc = el(root, 'Document', id='qaidam_kunlun_reference_document')
    el(doc, 'name', cfg['title']); el(doc, 'open', 1)
    view(doc, cfg['view']['lon'], cfg['view']['lat'], cfg['view']['range'])
    add_qaidam_kunlun(doc, el, view, kcolor, bundled)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_outputs():
    cfg, mountain, groups = load()
    (ROOT/(NAME+'.kml')).write_bytes(make())
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make(True))
        archive.writestr('icons/region_label.png', icon_png((255, 255, 255)))
    note = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['range_name'], cfg['scope'], cfg['area_note'],
            cfg['boundary_note'], cfg['book_note'], cfg['attribution_note'], cfg['label']['role'], '',
            mountain['title'], mountain['quote'], mountain['scope'], mountain['reading_note'],
            mountain['modern_reference']['name'], mountain['modern_reference']['coordinate_role'],
            mountain['modern_reference']['source_coordinate'], '',
            '本层包含一个盆地范围、一个区域名称标签、一个现代山口参照点及一条无几何旧地名说明。',
            '盆地范围不代表陈渠珍的具体行迹；未新增历史路线、宿营点、距离或耗时。',
            '完整阅读地图和独立增量KMZ均含本层，选择一份显示，避免重复。', '', '来源与证据限度']
    for source in cfg['sources']+mountain['sources']:
        note.extend([source['title'], source['url'], source['supports'], ''])
    note.extend(['Google Earth核验：'+cfg['google_earth_import']['status'], cfg['google_earth_import']['note']])
    text = '\n'.join(note)+'\n'
    (ROOT/'柴达木盆地与昆仑山口说明.txt').write_text(text, encoding='utf-8')
    return text


if __name__ == '__main__':
    write_outputs()
