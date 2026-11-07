"""Yushu annotation context with modern river fragments, never a historical route."""
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import (
    NS, el as standalone_el, view as standalone_view,
    paragraph, source_links, icon_png,
)
from output_paths import output_path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/玉树草原与穆鲁乌苏核对.json'
RIVER_FILE = ROOT / 'data/rivers/overview.geojson'
NAME = '艽野尘梦_玉树草原与穆鲁乌苏'
LAYER_NAME = '玉树草原与穆鲁乌苏｜校注区域判断；现代河流参照'
NOTE_FIELDS = [
    ('阅读范围', 'scope'), ('古今河名', 'identity_note'),
    ('玉树族与今地名', 'tribe_note'), ('地域限制', 'geography_note'),
    ('校注判断', 'interpretation_note'), ('时间口径', 'timing_note'),
    ('显示方式', 'display_note'),
]
RIVER_COLORS = {'tongtian': (99, 182, 255), 'tuotuo': (73, 211, 216)}
GEOMETRY_NOTE = ('这里只显示现代水系概化片段，标签是现代河名的显示位置，'
                 '不是陈渠珍渡点、营地、行军线或历史部族边界。')
RIVER_QUALITY = ('Natural Earth 1:10,000,000概化中心线，放大后存在偏移，'
                 '不用于河岸、支汊、古渡或营地对位；不是清末河道复原。'
                 '保留原线坐标及分段，不补接缺口，不计算历史里程。')


def load():
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


def value_text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def ledger_html(data):
    labels = {
        'layer': '图层', 'source': '来源', 'time': '时间', 'status': '证据性质',
        'geometry': '定位方式', 'limitation': '限制',
        'coordinate_reference': '坐标口径', 'method': '处理方法',
        'coverage': '覆盖范围', 'license': '数据许可', 'fallback': '缺失处理',
    }
    body = '<h4>来源与判断方法</h4><ul>'
    for item in data['source_method_ledger']:
        body += '<li>' + '<br/>'.join(
            '<b>' + html.escape(labels.get(key, str(key))) + '：</b>' + html.escape(value_text(value))
            for key, value in item.items()) + '</li>'
    return body + '</ul>'


def overview_html(data):
    body = '<h3>' + html.escape(data['title']) + '</h3>'
    body += paragraph('原句', data['quote'])
    body += ''.join(paragraph(label, data[key]) for label, key in NOTE_FIELDS)
    return body + ledger_html(data) + source_links(data)


def context_view(node, view, data):
    look = data['look_at']
    view(node, look['lon'], look['lat'], look['range_m'])


def _add_context(doc, el, view, data):
    folder = el(doc, 'Folder', id='yushu_annotation_context')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(data))
    context_view(folder, view, data)
    guide = el(folder, 'Placemark', id='yushu_context_guide')
    el(guide, 'name', '本段说明｜玉树草原、季节游牧与河名范围')
    el(guide, 'description', overview_html(data))
    context_view(guide, view, data)
    for card in data['cards']:
        placemark = el(folder, 'Placemark', id='yushu_context_card_' + card['id'])
        el(placemark, 'name', card['name'])
        body = '<h3>' + html.escape(card['name']) + '</h3>'
        body += '<p>' + html.escape(card['text']) + '</p>' + source_links(data)
        el(placemark, 'description', body)
        context_view(placemark, view, data)
    return folder


def add_yushu_context(doc, el, view):
    """The main map already has 13C river geometry; add only textual context."""
    return _add_context(doc, el, view, load())


def river_features(data):
    contexts = data['river_contexts']
    if len(contexts) != 2 or {r['id'] for r in contexts} != set(RIVER_COLORS):
        raise ValueError('Yushu context must contain exactly tongtian and tuotuo')
    source = json.loads(RIVER_FILE.read_text(encoding='utf-8'))
    selected = {rid: [] for rid in RIVER_COLORS}
    for feature in source['features']:
        rid = feature['properties'].get('river_id')
        if rid in selected:
            selected[rid].append(feature)
    if any(not features for features in selected.values()):
        raise ValueError('Missing Natural Earth river fragment for Yushu context')
    return selected


def source_lines(feature):
    geometry = feature['geometry']
    if geometry['type'] == 'LineString':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiLineString':
        return geometry['coordinates']
    raise ValueError('Expected source river line geometry: ' + geometry['type'])


def label_vertex(features, seed):
    vertices = [p for f in features for line in source_lines(f) for p in line]
    if not vertices:
        raise ValueError('Cannot place a river label without source vertices')
    factor = math.cos(math.radians(seed[1])) ** 2
    return min(vertices, key=lambda p: (p[0] - seed[0]) ** 2 * factor +
               (p[1] - seed[1]) ** 2)


def river_html(data, river, features):
    body = '<h3>' + html.escape(river['name']) + '</h3>'
    body += paragraph('现代水系参照', river['note'])
    body += paragraph('河名范围', data['identity_note'])
    body += paragraph('几何性质', GEOMETRY_NOTE)
    body += paragraph('数据精度', RIVER_QUALITY)
    urls = sorted({f['properties'].get('source_url', '') for f in features})
    body += '<p>' + '<br/>'.join(
        '<a href="' + html.escape(url, quote=True) + '">Natural Earth原始河线数据</a>'
        for url in urls if url) + '</p>'
    return body + source_links(data)


def add_river_styles(doc, bundled):
    for rid, color in RIVER_COLORS.items():
        style = standalone_el(doc, 'Style', id='yushu_context_' + rid + '_style')
        rgba = 'ff' + ''.join(f'{v:02x}' for v in reversed(color))
        icon_style = standalone_el(style, 'IconStyle')
        standalone_el(icon_style, 'color', 'ffffffff' if bundled else rgba)
        standalone_el(icon_style, 'scale', 0.7)
        icon = standalone_el(icon_style, 'Icon')
        standalone_el(icon, 'href', 'icons/yushu_' + rid + '.png' if bundled else
                      'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        label_style = standalone_el(style, 'LabelStyle')
        standalone_el(label_style, 'color', 'ffffffff')
        standalone_el(label_style, 'scale', 1)
        line_style = standalone_el(style, 'LineStyle')
        standalone_el(line_style, 'color', rgba)
        standalone_el(line_style, 'width', 3)


def make_standalone(data, bundled=False):
    features_by_id = river_features(data)
    root = ET.Element(f'{{{NS}}}kml')
    doc = standalone_el(root, 'Document', id='yushu_river_context_supplement')
    standalone_el(doc, 'name', '《艽野尘梦》玉树草原与穆鲁乌苏｜现代概化水系参照')
    standalone_el(doc, 'open', 1)
    standalone_el(doc, 'description', overview_html(data))
    context_view(doc, standalone_view, data)
    add_river_styles(doc, bundled)
    folder = standalone_el(doc, 'Folder', id='yushu_modern_rivers')
    standalone_el(folder, 'name', '现代通天河、沱沱河概化片段｜非陈氏渡点或营地')
    standalone_el(folder, 'open', 1)
    standalone_el(folder, 'description', paragraph('几何性质', GEOMETRY_NOTE) +
                  paragraph('数据精度', RIVER_QUALITY) + source_links(data))
    context_view(folder, standalone_view, data)
    for river in data['river_contexts']:
        rid = river['id']
        features = features_by_id[rid]
        at = label_vertex(features, river['label_seed'])
        body = river_html(data, river, features)
        for is_label in [False, True]:
            item_id = 'yushu_modern_' + rid + ('_label' if is_label else '_line')
            placemark = standalone_el(folder, 'Placemark', id=item_id)
            label_name = {'tongtian': '今通天河〔现代概化参照；非古渡〕',
                          'tuotuo': '今沱沱河〔现代水系背景〕'}
            standalone_el(placemark, 'name', label_name[rid] if is_label else river['name'])
            standalone_el(placemark, 'visibility', 1)
            standalone_el(placemark, 'description', body)
            standalone_view(placemark, at[0], at[1], data['look_at']['range_m'])
            standalone_el(placemark, 'styleUrl', '#yushu_context_' + rid + '_style')
            if is_label:
                point = standalone_el(placemark, 'Point')
                standalone_el(point, 'altitudeMode', 'clampToGround')
                standalone_el(point, 'coordinates', f'{at[0]},{at[1]},0')
            else:
                geometry = standalone_el(placemark, 'MultiGeometry')
                for feature in features:
                    for points in source_lines(feature):
                        line = standalone_el(geometry, 'LineString')
                        standalone_el(line, 'tessellate', 1)
                        standalone_el(line, 'altitudeMode', 'clampToGround')
                        standalone_el(line, 'coordinates', ' '.join(
                            f'{p[0]},{p[1]},0' for p in points))
    _add_context(doc, standalone_el, standalone_view, data)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_yushu_outputs():
    data = load()
    (output_path('maps', NAME + '.kml')).write_bytes(make_standalone(data))
    with zipfile.ZipFile(output_path('maps', NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make_standalone(data, True))
        for rid, color in RIVER_COLORS.items():
            archive.writestr('icons/yushu_' + rid + '.png', icon_png(color))

    sections = [data['title'], '核对日期：' + data['checked_at'], '原句：' + data['quote']]
    sections.extend(label + '\n' + data[key] for label, key in NOTE_FIELDS)
    sections.extend([GEOMETRY_NOTE, RIVER_QUALITY])
    sections.extend(card['name'] + '\n' + card['text'] for card in data['cards'])
    sections.append('来源与判断方法')
    sections.extend('\n'.join(str(key) + ': ' + value_text(value)
                              for key, value in item.items())
                    for item in data['source_method_ledger'])
    sections.append('来源与证据限度')
    sections.extend(source['title'] + '\n' + source['url'] + '\n' + source['supports']
                    for source in data['sources'])
    sections.append('Google Earth核验\n' + data['google_earth_import']['status'] +
                    '\n' + data['google_earth_import']['note'])
    text = '\n\n'.join(sections) + '\n'
    (output_path('docs', '玉树草原与穆鲁乌苏核对说明.txt')).write_text(text, encoding='utf-8')

    features_by_id = river_features(data)
    urls = '；'.join(source['url'] for source in data['sources'])
    with (output_path('tables', '玉树草原与穆鲁乌苏对照.csv')).open(
            'w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['类型', 'id', '名称', '标签经度', '标签纬度', '性质与限制', '来源'])
        for river in data['river_contexts']:
            at = label_vertex(features_by_id[river['id']], river['label_seed'])
            writer.writerow(['现代概化河线及河名标签', river['id'], river['name'], at[0], at[1],
                             river['note'] + ' ' + GEOMETRY_NOTE + ' ' + RIVER_QUALITY, urls])
        for card in data['cards']:
            writer.writerow(['无几何说明', card['id'], card['name'], '', '', card['text'], urls])
    return text
