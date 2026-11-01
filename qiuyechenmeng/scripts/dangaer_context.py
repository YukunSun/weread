"""Dangaer arrival context and one existing Huangyuan old-town reference point."""
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
DATA_FILE = ROOT / 'data/place_checks/丹噶尔厅与223日核对.json'
NAME = '艽野尘梦_丹噶尔厅与223日'
LAYER_NAME = '丹噶尔厅与223日｜古城参照与抵达日序'
POINT_LABEL = '丹噶尔厅〔今湟源古城｜农历六月廿四｜所读本记223日〕'
NOTE_KEYS = ['identity_note', 'coordinate_note', 'timing_note', 'calendar_note',
             'variant_note', 'stay_note', 'display_note']
STYLE_ID = 'dangaer_reference_style'
ICON_PATH = 'icons/dangaer.png'
ICON_RGB = (255, 141, 122)
CAMERA_RANGE_M = 24000
GEOMETRY_NOTE = ('地图只用现存古城内的地标作地区参照，不能据此确定作者住宿旅店、'
                 '当年厅署范围或行走路线；日期与停留说明卡不含地理几何。')


def load():
    check = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    point = check['point']
    lon, lat = point['lon'], point['lat']
    if not (math.isfinite(lon) and math.isfinite(lat) and
            -180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError('Invalid Dangaer reference coordinate')
    card_ids = [card['id'] for card in check['cards']]
    if len(card_ids) != len(set(card_ids)):
        raise ValueError('Duplicate Dangaer context card id')
    return check


def paragraph(text):
    return '<p>' + html.escape(str(text)) + '</p>'


def source_links(check):
    return '<p>' + '<br/>'.join(
        '<a href="' + html.escape(source['url'], quote=True) + '">' +
        html.escape(source['title']) + '</a>：' + html.escape(str(source['supports']))
        for source in check['sources']) + '</p>'


def point_html(check=None):
    """Return the context to append to the main map's existing Huangyuan popup."""
    if check is None:
        check = load()
    return ('<h3>丹噶尔厅与抵达日序</h3>' +
            ''.join(paragraph(check[key]) for key in NOTE_KEYS) +
            paragraph(GEOMETRY_NOTE) + source_links(check))


def overview_html(check):
    return ('<h3>' + html.escape(check['title']) + '</h3>' +
            paragraph(check['quote']) + point_html(check))


def _add_text_layer(check, doc, el, view):
    point = check['point']
    folder = el(doc, 'Folder', id='dangaer_context')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'visibility', 1)
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(check))
    view(folder, point['lon'], point['lat'], CAMERA_RANGE_M)
    guide = el(folder, 'Placemark', id='dangaer_guide')
    el(guide, 'name', '抵达丹噶尔厅｜农历六月廿四；所读本记223日')
    el(guide, 'description', overview_html(check))
    view(guide, point['lon'], point['lat'], CAMERA_RANGE_M)
    for card in check['cards']:
        mark = el(folder, 'Placemark', id='dangaer_card_' + card['id'])
        el(mark, 'name', card['name'])
        el(mark, 'description', paragraph(card['text']) + paragraph(check['coordinate_note']) +
           paragraph(check['display_note']) + paragraph(GEOMETRY_NOTE) + source_links(check))
        view(mark, point['lon'], point['lat'], CAMERA_RANGE_M)
    return folder


def add_dangaer_context(doc, el, view):
    """Add only text cards; the main map retains its existing Huangyuan point."""
    return _add_text_layer(load(), doc, el, view)


def make(bundled=False):
    """Return a standalone KML containing exactly one old-town reference Point."""
    check = load()
    point = check['point']
    root = ET.Element(f'{{{NS}}}kml')
    doc = standalone_el(root, 'Document', id='dangaer_supplement')
    standalone_el(doc, 'name', check['title'])
    standalone_el(doc, 'open', 1)
    standalone_view(doc, point['lon'], point['lat'], CAMERA_RANGE_M)
    style = standalone_el(doc, 'Style', id=STYLE_ID)
    icon_style = standalone_el(style, 'IconStyle')
    standalone_el(icon_style, 'color', 'ffffffff' if bundled else 'ff7a8dff')
    standalone_el(icon_style, 'scale', 1.05)
    standalone_el(standalone_el(icon_style, 'Icon'), 'href', ICON_PATH if bundled else
                  'https://maps.google.com/mapfiles/kml/shapes/open-diamond.png')
    label_style = standalone_el(style, 'LabelStyle')
    standalone_el(label_style, 'color', 'ffffffff')
    standalone_el(label_style, 'scale', 0.95)
    insert_styles(doc, [style])
    mark = standalone_el(doc, 'Placemark', id='place_huangyuan')
    standalone_el(mark, 'name', POINT_LABEL)
    standalone_el(mark, 'description', point_html(check))
    standalone_view(mark, point['lon'], point['lat'], CAMERA_RANGE_M)
    standalone_el(mark, 'styleUrl', '#' + STYLE_ID)
    metadata = standalone_el(mark, 'ExtendedData')
    for key, value in [('coordinate_role', '现存古城地标的地区代表点；非作者旅店确址'),
                       ('coordinate_note', check['coordinate_note'])]:
        standalone_el(standalone_el(metadata, 'Data', name=key), 'value', value)
    geometry = standalone_el(mark, 'Point')
    standalone_el(geometry, 'altitudeMode', 'clampToGround')
    standalone_el(geometry, 'coordinates', f'{point["lon"]},{point["lat"]},0')
    _add_text_layer(check, doc, standalone_el, standalone_view)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_dangaer_outputs():
    check = load()
    point = check['point']
    (ROOT / (NAME + '.kml')).write_bytes(make())
    with zipfile.ZipFile(ROOT / (NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make(True))
        archive.writestr(ICON_PATH, icon_png(ICON_RGB))
        for name in ['1937_p133.jpg', 'manifest.json']:
            source = ROOT / 'data/place_checks/丹噶尔厅研究' / name
            archive.writestr('sources/dangaer_' + name, source.read_bytes())
    notes = [check['title'], '核对日期：' + check['checked_at'], check['quote']]
    notes.extend(check[key] for key in NOTE_KEYS)
    notes.extend([GEOMETRY_NOTE, POINT_LABEL,
                  f'经纬度：{point["lon"]}, {point["lat"]}',
                  '主图复用既有huangyuan点；本层不重复点标。'])
    notes.extend(card['name'] + '\n' + card['text'] for card in check['cards'])
    notes.append('来源与证据限度')
    notes.extend(source['title'] + '\n' + source['url'] + '\n' + str(source['supports'])
                 for source in check['sources'])
    notes.extend(['Google Earth核验：' + check['google_earth_import']['status'],
                  check['google_earth_import']['note']])
    text = '\n\n'.join(notes) + '\n'
    (ROOT / '丹噶尔厅与223日核对说明.txt').write_text(text, encoding='utf-8')
    urls = '；'.join(source['url'] for source in check['sources'])
    with (ROOT / '丹噶尔厅与223日对照.csv').open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['类型', 'id', '名称', '经度', '纬度', '说明', '精度与限制', '来源'])
        writer.writerow(['古城地区参照', point['id'], POINT_LABEL, point['lon'], point['lat'],
                         check['identity_note'] + ' ' + check['timing_note'],
                         check['coordinate_note'] + ' ' + GEOMETRY_NOTE, urls])
        for card in check['cards']:
            writer.writerow(['无几何说明', card['id'], card['name'], '', '', card['text'],
                             check['coordinate_note'] + ' ' + check['display_note'], urls])
    return text
