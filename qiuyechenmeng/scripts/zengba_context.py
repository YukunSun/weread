"""Zengba overnight context; reuse the existing candidate without shared-map geometry."""
from pathlib import Path
import csv
import html
import json
import xml.etree.ElementTree as ET
import zipfile

from build_jiamiqingbo import (
    NS, el as standalone_el, view as standalone_view,
    paragraph, source_links, icon_png,
)
from output_paths import output_path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/甑巴与范玉昆核对.json'
NAME = '艽野尘梦_甑巴留宿'
LAYER_NAME = '甑巴留宿｜百巴增巴候选'
STYLE_ID = 'zengba_overnight_candidate_style'
ICON_PATH = 'icons/zengba_overnight_candidate.png'
CANDIDATE_NOTE = '百巴增巴仅作本段甑巴的候选地区；古今对应、范玉昆旧宅和陈部宿营确址均未确定。'


def load():
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


def overview_html(data):
    body = '<h3>' + html.escape(data['title']) + '</h3>'
    body += paragraph('原句', data['quote'])
    for label, key in [
        ('阅读范围', 'scope'), ('对应判断', 'identity_note'),
        ('耗时与日序', 'timing_note'), ('人物背景', 'person_note'),
        ('坐标性质', 'coordinate_note'), ('显示方式', 'display_note'),
    ]:
        body += paragraph(label, data[key])
    return body + paragraph('候选限制', CANDIDATE_NOTE) + source_links(data)


def point_html(data):
    point = data['point']
    body = '<h3>' + html.escape(point['name']) + '</h3>'
    for label, value in [
        ('阅读范围', data['scope']), ('候选地区', point['note']),
        ('对应判断', data['identity_note']),
        ('耗时与日序', data['timing_note']), ('人物背景', data['person_note']),
        ('坐标性质', data['coordinate_note']), ('候选限制', CANDIDATE_NOTE),
        ('显示方式', data['display_note']),
    ]:
        body += paragraph(label, value)
    body += paragraph('地区参照坐标', f'{point["lon"]}°E，{point["lat"]}°N')
    return body + source_links(data)


def _add_context(doc, el, view, data):
    point = data['point']
    folder = el(doc, 'Folder', id='zengba_overnight_context')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(data))
    view(folder, point['lon'], point['lat'], 65000)
    guide = el(folder, 'Placemark', id='zengba_overnight_guide')
    el(guide, 'name', '本段说明｜是日留宿、翌晨离开；现代对应仍候选')
    el(guide, 'description', overview_html(data))
    view(guide, point['lon'], point['lat'], 65000)
    for card in data['cards']:
        placemark = el(folder, 'Placemark', id='zengba_overnight_card_' + card['id'])
        el(placemark, 'name', card['name'])
        body = '<h3>' + html.escape(card['name']) + '</h3>'
        body += '<p>' + html.escape(card['text']) + '</p>'
        el(placemark, 'description', body + source_links(data))
        view(placemark, point['lon'], point['lat'], 65000)
    return folder


def add_zengba_context(doc, el, view):
    """Add only explanation cards to the main map, whose layer 15 has the point."""
    return _add_context(doc, el, view, load())


def make_standalone(data, bundled=False):
    root = ET.Element(f'{{{NS}}}kml')
    doc = standalone_el(root, 'Document', id='zengba_overnight_supplement')
    standalone_el(doc, 'name', '《艽野尘梦》' + LAYER_NAME)
    standalone_el(doc, 'open', 1)
    standalone_el(doc, 'description', overview_html(data))
    point = data['point']
    standalone_view(doc, point['lon'], point['lat'], 65000)

    style = standalone_el(doc, 'Style', id=STYLE_ID)
    icon_style = standalone_el(style, 'IconStyle')
    standalone_el(icon_style, 'color', 'ffffffff' if bundled else 'ff47b3ff')
    standalone_el(icon_style, 'scale', 1.1)
    icon = standalone_el(icon_style, 'Icon')
    standalone_el(icon, 'href', ICON_PATH if bundled else
                  'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    label_style = standalone_el(style, 'LabelStyle')
    standalone_el(label_style, 'color', 'ffffffff')
    standalone_el(label_style, 'scale', 0.9)

    placemark = standalone_el(doc, 'Placemark', id='zengba_overnight_point_' + point['id'])
    standalone_el(placemark, 'name', point['name'])
    standalone_el(placemark, 'visibility', 1)
    standalone_el(placemark, 'description', point_html(data))
    standalone_view(placemark, point['lon'], point['lat'], 65000)
    standalone_el(placemark, 'styleUrl', '#' + STYLE_ID)
    metadata = standalone_el(placemark, 'ExtendedData')
    for key, value in [
        ('point_record_id', point['id']),
        ('existing_candidate_id', 'gongbu_zengba_baiba_candidate'),
        ('coordinate_role', '15层同坐标候选地区；非范玉昆旧宅或清末宿营确址'),
        ('identity_note', data['identity_note']),
        ('timing_note', data['timing_note']),
    ]:
        standalone_el(standalone_el(metadata, 'Data', name=key), 'value', value)
    geometry = standalone_el(placemark, 'Point')
    standalone_el(geometry, 'altitudeMode', 'clampToGround')
    standalone_el(geometry, 'coordinates', f'{point["lon"]},{point["lat"]},0')
    _add_context(doc, standalone_el, standalone_view, data)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_zengba_outputs():
    data = load()
    (output_path('maps', NAME + '.kml')).write_bytes(make_standalone(data))
    with zipfile.ZipFile(output_path('maps', NAME + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', make_standalone(data, True))
        archive.writestr(ICON_PATH, icon_png())

    point = data['point']
    sections = [data['title'], '原句：' + data['quote']]
    sections.extend(data[key] for key in [
        'scope', 'identity_note', 'timing_note', 'person_note', 'coordinate_note',
        'display_note',
    ])
    sections.extend([
        CANDIDATE_NOTE,
        point['name'] + '\n' + point['note'] +
        f'\n地区参照坐标：{point["lon"]}°E，{point["lat"]}°N。',
        '主图仅新增无几何说明，复用15层已有候选点；独立图显示同一候选地区。'
        '完整图、工布安抚图与本独立图叠加时，只选择一份同名候选点显示。'
        '本独立图只有1个候选点，无路线、范围面和Region。',
    ])
    sections.extend(card['name'] + '\n' + card['text'] for card in data['cards'])
    sections.append('来源与证据限度')
    sections.extend(source['title'] + '\n' + source['url'] + '\n' + source['supports']
                    for source in data['sources'])
    sections.append('Google Earth核验\n' + data['google_earth_import']['status'] +
                    '\n' + data['google_earth_import']['note'])
    text = '\n\n'.join(sections) + '\n'
    (output_path('docs', '甑巴留宿核对说明.txt')).write_text(text, encoding='utf-8')

    urls = '；'.join(source['url'] for source in data['sources'])
    with (output_path('tables', '甑巴留宿对照.csv')).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['类型', 'id', '地图标签', '经度', '纬度', '说明', '耗时与日序', '来源'])
        writer.writerow(['候选地区', point['id'], point['name'], point['lon'], point['lat'],
                         point['note'] + ' ' + data['coordinate_note'], data['timing_note'], urls])
        for card in data['cards']:
            writer.writerow(['无几何说明', card['id'], card['name'], '', '', card['text'], '', urls])
    return text
