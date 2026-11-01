"""Hehuang reading context: modern river segments and an approximate Shibao site."""
from collections import defaultdict
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import NS, el as standalone_el, view as standalone_view, icon_png
from regional_ranges import insert_styles


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/河湟谷地与石堡城核对.json'
NAME = '艽野尘梦_河湟谷地与石堡城'
LAYER_NAME = '河湟谷地与石堡城｜现代水系与遗址地区参照'
NOTE_KEYS = ['scope', 'region_note', 'stone_note', 'coordinate_note', 'history_note',
             'visit_note', 'timing_note', 'display_note']
COLORS = {'yellow': '#399fff', 'huangshui': '#60d4ff', 'datong': '#2aaec5'}
STONE_STYLE = 'hehuang_shibao_stone_style'
LABEL_STYLE = 'hehuang_river_label_style'


def load():
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


def paragraph(text):
    return '<p>' + html.escape(str(text)) + '</p>'


def source_links(check):
    return '<p>' + '<br/>'.join(
        '<a href="' + html.escape(source['url'], quote=True) + '">' +
        html.escape(source['title']) + '</a>' for source in check['sources']) + '</p>'


def feature_lines(feature):
    geometry = feature['geometry']
    if geometry['type'] == 'LineString':
        lines = [geometry['coordinates']]
    elif geometry['type'] == 'MultiLineString':
        lines = geometry['coordinates']
    else:
        raise ValueError('Expected river LineString/MultiLineString')
    for points in lines:
        if len(points) < 2:
            raise ValueError('River segment needs at least two coordinates')
        for lon, lat, *_ in points:
            if not (math.isfinite(lon) and math.isfinite(lat) and
                    -180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError('Invalid river coordinate')
    return lines


def load_rivers(check):
    path = ROOT / check['river_file']
    collection = json.loads(path.read_text(encoding='utf-8'))
    if collection['type'] != 'FeatureCollection':
        raise ValueError('Expected river FeatureCollection')
    groups = defaultdict(list)
    for feature in collection['features']:
        if feature_lines(feature):
            groups[feature['properties']['river_id']].append(feature)
    manifest_path = path.with_name('manifest.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    return groups, manifest, manifest_path


def nearest_vertex(features, seed):
    points = [point for feature in features for line in feature_lines(feature) for point in line]
    cos2 = math.cos(math.radians(seed[1])) ** 2
    nearest = min(points, key=lambda p: (p[0] - seed[0]) ** 2 * cos2 + (p[1] - seed[1]) ** 2)
    return nearest[:2]


def overview_html(check):
    return '<h3>' + html.escape(check['title']) + '</h3>' + ''.join(
        paragraph(check[key]) for key in NOTE_KEYS) + source_links(check)


def _manifest_records(manifest, river_id):
    records = [manifest]
    for key in ['rivers', 'features', 'segments']:
        entries = manifest.get(key, [])
        if isinstance(entries, dict):
            entry = entries.get(river_id)
            if isinstance(entry, dict):
                records.append(entry)
        elif isinstance(entries, list):
            records.extend(entry for entry in entries if isinstance(entry, dict) and
                           entry.get('river_id', entry.get('id')) == river_id)
    return records


def river_html(check, river, features, manifest, manifest_path):
    body = '<h3>' + html.escape(river['name']) + '</h3>' + paragraph(river['note'])
    body += paragraph('本层只显示已取得的现代河道源线，保持原数据分段，不补接缺口。'
                      '河线和名称标签用于理解水系，不是河湟谷地边界、古代河岸、陈渠珍路线或渡点。')
    if any(feature['properties'].get('tunnel') not in (None, 'no') for feature in features):
        body += paragraph('含源数据标注隧道或涵洞的现代河段；本层统一贴地显示，不全是地表明渠，不能解释为历史河道。')
    if not features:
        body += paragraph('本次数据没有该河的可用线段，故只保留说明，不补画直线或标签点。')
    records = _manifest_records(manifest, river['id']) + [f['properties'] for f in features]
    notes = []
    urls = set()
    for record in records:
        for key in ['dataset', 'license', 'license_note', 'attribution', 'attribution_note',
                    'processing_note', 'method', 'coordinate_note', 'scope_note', 'limitations']:
            value = record.get(key)
            if isinstance(value, list):
                value = '；'.join(str(item) for item in value)
            if isinstance(value, str) and value and value not in notes:
                notes.append(value)
        for key in ['source_url', 'source', 'url', 'license_url']:
            value = record.get(key)
            if isinstance(value, str) and value.startswith(('https://', 'http://')):
                urls.add(value)
    body += ''.join(paragraph(note) for note in notes)
    try:
        manifest_name = str(manifest_path.relative_to(ROOT))
    except ValueError:
        manifest_name = manifest_path.name
    body += paragraph('逐段来源、许可与处理口径见数据清单：' + manifest_name + '。')
    body += '<p>' + '<br/>'.join('<a href="' + html.escape(url, quote=True) +
                               '">现代河道数据／许可来源</a>' for url in sorted(urls)) + '</p>'
    return body + source_links(check)


def _add_styles(doc, el, kcolor, bundled):
    styles = []
    style = el(doc, 'Style', id=STONE_STYLE)
    styles.append(style)
    icon_style = el(style, 'IconStyle')
    # Tint the reused gold hollow icon to orange without adding another image resource.
    el(icon_style, 'color', kcolor('#ffdab2' if bundled else '#ffb347'))
    el(icon_style, 'scale', 1.05)
    el(el(icon_style, 'Icon'), 'href', 'icons/minor_reference.png' if bundled else
       'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    label = el(style, 'LabelStyle')
    el(label, 'color', 'ffffffff')
    el(label, 'scale', 0.95)
    for river_id, color in COLORS.items():
        style = el(doc, 'Style', id='hehuang_river_' + river_id)
        styles.append(style)
        line = el(style, 'LineStyle')
        el(line, 'color', kcolor(color))
        el(line, 'width', 3.0)
    style = el(doc, 'Style', id=LABEL_STYLE)
    styles.append(style)
    icon_style = el(style, 'IconStyle')
    el(icon_style, 'color', 'ffffffff' if bundled else kcolor('#60d4ff'))
    el(icon_style, 'scale', 0.35)
    el(el(icon_style, 'Icon'), 'href', 'icons/river_label.png' if bundled else
       'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    label = el(style, 'LabelStyle')
    el(label, 'color', 'ffffffff')
    el(label, 'scale', 1.05)
    insert_styles(doc, styles)


def add_hehuang_shibao(doc, el, view, kcolor, bundled=False):
    check = load()
    groups, manifest, manifest_path = load_rivers(check)
    _add_styles(doc, el, kcolor, bundled)
    folder = el(doc, 'Folder', id='hehuang_shibao_context')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'visibility', 1)
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(check))
    camera = check['look_at']
    view(folder, camera['lon'], camera['lat'], camera['range_m'])
    stone = check['stone']
    mark = el(folder, 'Placemark', id='hehuang_' + stone['id'])
    el(mark, 'name', stone['name'])
    el(mark, 'description', paragraph(stone['note']) + ''.join(
        paragraph(check[key]) for key in ['stone_note', 'coordinate_note', 'history_note',
                                          'visit_note', 'timing_note']) + source_links(check))
    view(mark, stone['lon'], stone['lat'], 45000)
    el(mark, 'styleUrl', '#' + STONE_STYLE)
    point = el(mark, 'Point')
    el(point, 'altitudeMode', 'clampToGround')
    el(point, 'coordinates', f'{stone["lon"]},{stone["lat"]},0')
    for river in check['rivers']:
        features = groups.get(river['id'], [])
        body = river_html(check, river, features, manifest, manifest_path)
        if not features:
            mark = el(folder, 'Placemark', id='hehuang_missing_' + river['id'])
            el(mark, 'name', river['name'] + '〔本次未取得河线〕')
            el(mark, 'description', body)
            continue
        at = nearest_vertex(features, river['label_seed'])
        mark = el(folder, 'Placemark', id='hehuang_river_line_' + river['id'])
        el(mark, 'name', river['name'] + '〔现代河道分段参照〕')
        el(mark, 'description', body)
        view(mark, at[0], at[1], camera['range_m'])
        el(mark, 'styleUrl', '#hehuang_river_' + river['id'])
        multi = el(mark, 'MultiGeometry')
        for feature in features:
            for points in feature_lines(feature):
                line = el(multi, 'LineString')
                el(line, 'tessellate', 1)
                el(line, 'altitudeMode', 'clampToGround')
                el(line, 'coordinates', ' '.join(f'{lon},{lat},0' for lon, lat, *_ in points))
        mark = el(folder, 'Placemark', id='hehuang_river_label_' + river['id'])
        el(mark, 'name', river['name'])
        el(mark, 'description', body + paragraph('名称标签取已载河线中最接近预设位置的顶点。'))
        view(mark, at[0], at[1], camera['range_m'])
        el(mark, 'styleUrl', '#' + LABEL_STYLE)
        point = el(mark, 'Point')
        el(point, 'altitudeMode', 'clampToGround')
        el(point, 'coordinates', f'{at[0]},{at[1]},0')
    guide = el(folder, 'Placemark', id='hehuang_shibao_guide')
    el(guide, 'name', '本层说明｜水系背景与石堡城近位；不表示亲历')
    el(guide, 'description', overview_html(check))
    view(guide, camera['lon'], camera['lat'], camera['range_m'])
    for card in check['cards']:
        mark = el(folder, 'Placemark', id='hehuang_card_' + card['id'])
        el(mark, 'name', card['name'])
        el(mark, 'description', paragraph(card['text']) + source_links(check))
        view(mark, camera['lon'], camera['lat'], camera['range_m'])
    return folder


def make(bundled=False):
    check = load()
    root = ET.Element(f'{{{NS}}}kml')
    doc = standalone_el(root, 'Document', id='hehuang_shibao_supplement')
    standalone_el(doc, 'name', check['title'])
    standalone_el(doc, 'open', 1)
    camera = check['look_at']
    standalone_view(doc, camera['lon'], camera['lat'], camera['range_m'])

    def kcolor(color, alpha='ff'):
        value = color.lstrip('#')
        return alpha + value[4:6] + value[2:4] + value[:2]

    add_hehuang_shibao(doc, standalone_el, standalone_view, kcolor, bundled)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_hehuang_outputs():
    check = load()
    groups, manifest, manifest_path = load_rivers(check)
    (ROOT / (NAME + '.kml')).write_bytes(make())
    with zipfile.ZipFile(ROOT / (NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make(True))
        archive.writestr('icons/minor_reference.png', icon_png((255, 209, 102)))
        archive.writestr('icons/river_label.png', icon_png((96, 212, 255)))
        for filename in ['manifest.json', 'NOTICE']:
            source = (ROOT / check['river_file']).with_name(filename)
            if source.is_file():
                archive.writestr('sources/hehuang_' + filename, source.read_bytes())
    notes = [check['title'], '核对日期：' + check['checked_at']]
    notes.extend(check[key] for key in NOTE_KEYS)
    notes.extend([check['stone']['name'], check['stone']['note']])
    for river in check['rivers']:
        features = groups.get(river['id'], [])
        status = '保留源线分段；名称标签落在已载源线顶点。' if features else '本次未取得河线，不补画。'
        notes.extend([river['name'], river['note'], status])
    notes.extend(card['name'] + '\n' + card['text'] for card in check['cards'])
    notes.append('来源与证据限度')
    notes.extend(source['title'] + '\n' + source['url'] + '\n' + source['supports']
                 for source in check['sources'])
    notes.extend(['河线数据清单：' + str(manifest_path.relative_to(ROOT)),
                  json.dumps(manifest, ensure_ascii=False, indent=2),
                  'Google Earth核验：' + check['google_earth_import']['status'],
                  check['google_earth_import']['note']])
    text = '\n\n'.join(notes) + '\n'
    (ROOT / '河湟谷地与石堡城核对说明.txt').write_text(text, encoding='utf-8')
    urls = '；'.join(source['url'] for source in check['sources'])
    with (ROOT / '河湟谷地与石堡城对照.csv').open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['类型', 'id', '名称', '经度', '纬度', '说明', '来源'])
        stone = check['stone']
        writer.writerow(['遗址地区参照', stone['id'], stone['name'], stone['lon'], stone['lat'],
                         stone['note'] + ' ' + check['coordinate_note'], urls])
        for river in check['rivers']:
            features = groups.get(river['id'], [])
            at = nearest_vertex(features, river['label_seed']) if features else ('', '')
            status = '已载现代源线分段及源线名称标签；非谷地边界。' if features else '无河线，不补画。'
            writer.writerow(['现代水系参照', river['id'], river['name'], *at,
                             river['note'] + ' ' + status, urls + '；' + str(manifest_path.relative_to(ROOT))])
        for card in check['cards']:
            writer.writerow(['无几何说明', card['id'], card['name'], '', '', card['text'], urls])
    return text
