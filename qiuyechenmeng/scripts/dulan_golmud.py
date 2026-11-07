"""Dulan/Golmud reading references, without inferred routes or area boundaries."""
from pathlib import Path
import csv
import html
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import NS, el as standalone_el, view as standalone_view, icon_png
from regional_ranges import insert_styles
from output_paths import output_path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/都兰与格尔木核对.json'
NAME = '艽野尘梦_都兰与格尔木'
LAYER_NAME = '都兰与格尔木｜旧地名候选与现代参照'
NOTE_KEYS = ['scope', 'identity_note', 'county_note', 'ethnicity_note',
             'timing_note', 'display_note']
ROLES = {
    'historical_candidate': {
        'label': '历史地点候选地区参照',
        'style': 'dulan_golmud_candidate_style',
        'icon': 'icons/annotation11_approximate.png',
        'color': '#ffb347',
        'rgb': (255, 179, 71),
    },
    'modern_reference': {
        'label': '现代地点参照',
        'style': 'dulan_golmud_modern_style',
        'icon': 'icons/minor_landmark.png',
        'color': '#89d8ff',
        'rgb': (137, 216, 255),
    },
}
GEOMETRY_NOTE = ('本层点位用于阅读地名和时代差别；坐标不是古市场、县署或作者宿营地的实测确址。'
                 '说明卡片无地理几何，不绘行军连线或历史范围边界。')


def load():
    check = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    source_ids = [source['id'] for source in check['sources']]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError('Duplicate Dulan/Golmud source id')
    source_ids = set(source_ids)
    item_ids = []
    for place in check['places']:
        item_ids.append('place_' + place['id'])
        if place['role'] not in ROLES:
            raise ValueError('Unsupported Dulan/Golmud coordinate role: ' + place['role'])
        lon, lat = place['lon'], place['lat']
        if not (math.isfinite(lon) and math.isfinite(lat) and
                -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('Invalid Dulan/Golmud coordinate: ' + place['id'])
        if not place['source_ids'] or set(place['source_ids']) - source_ids:
            raise ValueError('Missing/unknown Dulan/Golmud place source: ' + place['id'])
    item_ids.extend('card_' + card['id'] for card in check['cards'])
    if len(item_ids) != len(set(item_ids)):
        raise ValueError('Duplicate Dulan/Golmud item id')
    return check


def paragraph(text):
    return '<p>' + html.escape(str(text)) + '</p>'


def source_links(check, source_ids=None):
    selected = set(source_ids) if source_ids is not None else None
    sources = [source for source in check['sources']
               if selected is None or source['id'] in selected]
    return '<p>' + '<br/>'.join(
        '<a href="' + html.escape(source['url'], quote=True) + '">' +
        html.escape(source['title']) + '</a>：' + html.escape(str(source['supports']))
        for source in sources) + '</p>'


def overview_html(check):
    return ('<h3>' + html.escape(check['title']) + '</h3>' +
            paragraph(check['quote']) + ''.join(paragraph(check[key]) for key in NOTE_KEYS) +
            paragraph(GEOMETRY_NOTE) + source_links(check))


def place_html(check, place):
    body = '<h3>' + html.escape(place['name']) + '</h3>'
    body += paragraph('点位性质：' + ROLES[place['role']]['label'])
    for label, key in [('判断依据', 'evidence'), ('坐标方法与精度', 'coordinate_method'),
                       ('定位限制', 'limits')]:
        body += paragraph(label + '：' + str(place[key]))
    body += paragraph(check['display_note']) + paragraph(GEOMETRY_NOTE)
    return body + source_links(check, place['source_ids'])


def _add_styles(doc, el, kcolor, bundled):
    styles = []
    for role in ROLES.values():
        style = el(doc, 'Style', id=role['style'])
        styles.append(style)
        icon_style = el(style, 'IconStyle')
        el(icon_style, 'color', 'ffffffff' if bundled else kcolor(role['color']))
        el(icon_style, 'scale', 1.05)
        el(el(icon_style, 'Icon'), 'href', role['icon'] if bundled else
           'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        label = el(style, 'LabelStyle')
        el(label, 'color', 'ffffffff')
        el(label, 'scale', 0.95)
    insert_styles(doc, styles)


def _add_layer(check, doc, el, view, kcolor, bundled, include_existing):
    _add_styles(doc, el, kcolor, bundled)
    camera = check['look_at']
    folder = el(doc, 'Folder', id='dulan_golmud_context')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'visibility', 1)
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(check))
    view(folder, camera['lon'], camera['lat'], camera['range_m'])
    for place in check['places']:
        if place.get('existing_main_id') and not include_existing:
            continue
        mark = el(folder, 'Placemark', id='dulan_golmud_place_' + place['id'])
        el(mark, 'name', place['name'])
        el(mark, 'description', place_html(check, place))
        view(mark, place['lon'], place['lat'], 65000)
        el(mark, 'styleUrl', '#' + ROLES[place['role']]['style'])
        metadata = el(mark, 'ExtendedData')
        for key in ['role', 'coordinate_method', 'limits']:
            el(el(metadata, 'Data', name=key), 'value', place[key])
        point = el(mark, 'Point')
        el(point, 'altitudeMode', 'clampToGround')
        el(point, 'coordinates', f'{place["lon"]},{place["lat"]},0')
    guide = el(folder, 'Placemark', id='dulan_golmud_guide')
    el(guide, 'name', '本层说明｜都兰旧地名与格尔木现代参照')
    el(guide, 'description', overview_html(check))
    view(guide, camera['lon'], camera['lat'], camera['range_m'])
    for card in check['cards']:
        mark = el(folder, 'Placemark', id='dulan_golmud_card_' + card['id'])
        el(mark, 'name', card['name'])
        el(mark, 'description', paragraph(card['text']) + paragraph(check['display_note']) +
           paragraph(GEOMETRY_NOTE) + source_links(check))
        view(mark, camera['lon'], camera['lat'], camera['range_m'])
    return folder


def add_dulan_golmud(doc, el, view, kcolor, bundled=False):
    """Add new references and text cards; leave existing main-map places unchanged."""
    return _add_layer(load(), doc, el, view, kcolor, bundled, include_existing=False)


def make(bundled=False):
    """Build the standalone supplement, including existing main-map reference places."""
    check = load()
    root = ET.Element(f'{{{NS}}}kml')
    doc = standalone_el(root, 'Document', id='dulan_golmud_supplement')
    standalone_el(doc, 'name', check['title'])
    standalone_el(doc, 'open', 1)
    camera = check['look_at']
    standalone_view(doc, camera['lon'], camera['lat'], camera['range_m'])

    def kcolor(color, alpha='ff'):
        value = color.lstrip('#')
        return alpha + value[4:6] + value[2:4] + value[:2]

    _add_layer(check, doc, standalone_el, standalone_view, kcolor, bundled,
               include_existing=True)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_dulan_outputs():
    check = load()
    (output_path('maps', NAME + '.kml')).write_bytes(make())
    with zipfile.ZipFile(output_path('maps', NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make(True))
        for role in ROLES.values():
            archive.writestr(role['icon'], icon_png(role['rgb']))
    notes = [check['title'], '核对日期：' + check['checked_at'], check['quote']]
    notes.extend(check[key] for key in NOTE_KEYS)
    notes.append(GEOMETRY_NOTE)
    for place in check['places']:
        notes.extend([place['name'], '点位性质：' + ROLES[place['role']]['label'],
                      f'经纬度：{place["lon"]}, {place["lat"]}',
                      '判断依据：' + str(place['evidence']),
                      '坐标方法与精度：' + str(place['coordinate_method']),
                      '定位限制：' + str(place['limits']),
                      '来源编号：' + '、'.join(place['source_ids'])])
        if place.get('existing_main_id'):
            notes.append('主图复用既有地点：' + place['existing_main_id'] + '；本层不重复点标。')
    notes.extend(card['name'] + '\n' + card['text'] for card in check['cards'])
    notes.append('来源与证据限度')
    notes.extend(source['id'] + ' ' + source['title'] + '\n' + source['url'] + '\n' +
                 str(source['supports']) for source in check['sources'])
    notes.extend(['Google Earth核验：' + check['google_earth_import']['status'],
                  check['google_earth_import']['note']])
    text = '\n\n'.join(notes) + '\n'
    (output_path('docs', '都兰与格尔木核对说明.txt')).write_text(text, encoding='utf-8')
    sources = {source['id']: source['url'] for source in check['sources']}
    with (output_path('tables', '都兰与格尔木对照.csv')).open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['类型', 'id', '名称', '经度', '纬度', '依据', '坐标方法与精度',
                         '定位限制', '主图既有点', '来源'])
        for place in check['places']:
            writer.writerow([ROLES[place['role']]['label'], place['id'], place['name'],
                             place['lon'], place['lat'], place['evidence'],
                             place['coordinate_method'], place['limits'],
                             place.get('existing_main_id') or '',
                             '；'.join(sources[key] for key in place['source_ids'])])
        all_urls = '；'.join(sources.values())
        for card in check['cards']:
            writer.writerow(['无几何说明', card['id'], card['name'], '', '', card['text'],
                             check['display_note'], GEOMETRY_NOTE, '', all_urls])
    return text
