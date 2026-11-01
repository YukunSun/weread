"""Modern roads over the north-return hypothesis, preserving separate road fragments."""
from pathlib import Path
import csv
import html
import json
import re
import xml.etree.ElementTree as ET
import zipfile

from modern_roads import km
from build_jiamiqingbo import el as standalone_el, view as standalone_view, icon_png

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_北返现代道路对照'
LABEL_ICON = 'icons/north_return_road_label.png'


def load():
    return json.loads((ROOT/'data/road_checks/北返现代道路对照.json').read_text(encoding='utf-8'))


def kcolor(color):
    value = color.lstrip('#')
    return 'ff'+value[4:6]+value[2:4]+value[0:2]


def paragraphs(items):
    return ''.join('<p>'+html.escape(str(text))+'</p>' for text in items)


def links(cfg, keys):
    return '<p>'+'<br/>'.join('<a href="'+html.escape(cfg['sources'][key]['url'], quote=True)+'">'
                            +html.escape(cfg['sources'][key]['title'])+'</a>' for key in keys)+'</p>'


def read_geometry(cfg):
    raw = json.loads((ROOT/cfg['geometry_file']).read_text(encoding='utf-8'))
    manifest = json.loads((ROOT/cfg['manifest_file']).read_text(encoding='utf-8'))
    result = []
    for road in cfg['roads']:
        pieces, features, dates = [], [], set()
        for feature in raw['features']:
            props = feature.get('properties', {})
            road_ref = props.get('road_ref')
            if road_ref is not None:
                matched = road_ref == road['ref'] or (isinstance(road_ref, list) and road['ref'] in road_ref)
            else:
                refs = str(props.get('ref', ''))+';'+str(props.get('source_relation_refs', ''))
                matched = road['ref'] in re.findall(r'[GS]\d+', refs)
            if not matched or props.get('highway') in ['construction', 'proposed']:
                continue
            geometry = feature.get('geometry', {})
            if geometry.get('type') == 'LineString':
                lines = [geometry['coordinates']]
            elif geometry.get('type') == 'MultiLineString':
                lines = geometry['coordinates']
            else:
                continue
            for coords in lines:
                if len(coords) >= 2:
                    pieces.append([[float(p[0]), float(p[1])] for p in coords])
            features.append(props)
            if props.get('retrieved_at'):
                dates.add(str(props['retrieved_at']))
        entry = dict(road, pieces=pieces, features=features, dates=sorted(dates))
        entry['manifest'] = manifest.get('per_road', {}).get(road['ref'], {})
        result.append(entry)
    return result, manifest


def data_text(road):
    dates = '、'.join(sorted({date[:10] for date in road['dates']})) or '见数据清单'
    text = f'几何采集日期：{dates}；现有OSM道路要素{len(road["features"])}个，分离片段{len(road["pieces"])}段。'
    if not road['pieces']:
        text += '当前没有可采用的几何，保留说明，不补画道路。'
    return text


def road_html(cfg, road):
    return ('<h3>'+html.escape(road['name'])+'</h3>'+paragraphs(
        [road['note'], data_text(road), cfg['geometry_note'], cfg['comparison_note'], cfg['attribution']])
        +links(cfg, road['source_keys']))


def inline_line(placemark, el, road):
    style = el(placemark, 'Style')
    line = el(style, 'LineStyle')
    el(line, 'color', kcolor(road['color']))
    el(line, 'width', road['width'])


def inline_label(placemark, el, road):
    style = el(placemark, 'Style')
    icon = el(style, 'IconStyle')
    el(icon, 'color', kcolor(road['color']))
    el(icon, 'scale', 0.32)
    el(el(icon, 'Icon'), 'href', LABEL_ICON)
    label = el(style, 'LabelStyle')
    el(label, 'color', kcolor(road['color']))
    el(label, 'scale', 1.05)


def overview_html(cfg, roads, manifest):
    dates = sorted({date for road in roads for date in road['dates']})
    notes = [cfg['summary'], cfg['geometry_note'], cfg['comparison_note'], cfg['attribution'],
             '采集日期：'+('、'.join(dates) if dates else '见逐路号数据状态')]
    limitations = manifest.get('limitations', [])
    notes.extend(limitations if isinstance(limitations, list) else [limitations])
    return '<h3>'+html.escape(cfg['title'])+'</h3>'+paragraphs(notes)


def add_north_return_roads(doc, el, view):
    cfg = load(); roads, manifest = read_geometry(cfg)
    folder = el(doc, 'Folder', id='north_return_modern_roads')
    el(folder, 'name', cfg['title']); el(folder, 'visibility', 1); el(folder, 'open', 1)
    el(folder, 'description', overview_html(cfg, roads, manifest))
    camera = cfg['overview']; view(folder, camera['lon'], camera['lat'], camera['range_m'])
    for road in roads:
        code = road['ref']
        road_folder = el(folder, 'Folder', id='north_road_folder_'+code)
        el(road_folder, 'name', road['name']+('〔暂无几何〕' if not road['pieces'] else ''))
        el(road_folder, 'visibility', road.get('visibility', 1)); el(road_folder, 'open', 0)
        el(road_folder, 'description', road_html(cfg, road))
        if not road['pieces']:
            continue
        placemark = el(road_folder, 'Placemark', id='north_road_line_'+code)
        el(placemark, 'name', road['name']+'｜现代道路实线')
        el(placemark, 'description', road_html(cfg, road))
        view(placemark, camera['lon'], camera['lat'], camera['range_m'])
        inline_line(placemark, el, road)
        metadata = el(placemark, 'ExtendedData')
        for key, value in [('road_ref', code), ('geometry_role', '现代OSM道路片段；非历史路线'),
                           ('data_status', data_text(road)), ('source', '© OpenStreetMap contributors；ODbL 1.0')]:
            el(el(metadata, 'Data', name=key), 'value', value)
        geometry = el(placemark, 'MultiGeometry')
        for coords in road['pieces']:
            line = el(geometry, 'LineString'); el(line, 'tessellate', 1)
            el(line, 'altitudeMode', 'clampToGround')
            el(line, 'coordinates', ' '.join(f'{p[0]:.7f},{p[1]:.7f},0' for p in coords))
        vertices = [p for coords in road['pieces'] for p in coords]
        used = []
        for index, target in enumerate(road.get('label_targets', [])):
            chosen = min(vertices, key=lambda p: km(p, target))
            if km(chosen, target) > 100 or any(km(chosen, old) < 65 for old in used):
                continue
            used.append(chosen)
            placemark = el(road_folder, 'Placemark', id=f'north_road_label_{code}_{index}')
            el(placemark, 'name', road.get('label', code)); el(placemark, 'description', road_html(cfg, road))
            view(placemark, *chosen, 160000); inline_label(placemark, el, road)
            geometry = el(placemark, 'Point'); el(geometry, 'altitudeMode', 'clampToGround')
            el(geometry, 'coordinates', f'{chosen[0]:.7f},{chosen[1]:.7f},0')
    for card in cfg['cards']:
        placemark = el(folder, 'Placemark', id='north_road_card_'+card['id'])
        el(placemark, 'name', card['name'])
        el(placemark, 'description', '<h3>'+html.escape(card['name'])+'</h3>'
           +paragraphs(card['paragraphs'])+links(cfg, card['source_keys']))
        view(placemark, camera['lon'], camera['lat'], camera['range_m'])
    status = el(folder, 'Placemark', id='north_road_data_status')
    el(status, 'name', '数据日期与缺口〔不补画规划或缺段〕')
    el(status, 'description', overview_html(cfg, roads, manifest)
       +paragraphs([road['name']+'：'+data_text(road) for road in roads]))
    view(status, camera['lon'], camera['lat'], camera['range_m'])
    return folder


def make_supplement():
    cfg = load(); root = ET.Element('{'+KML+'}kml')
    doc = standalone_el(root, 'Document', id='north_return_modern_roads_supplement')
    standalone_el(doc, 'name', '《艽野尘梦》'+cfg['title']); standalone_el(doc, 'open', 1)
    standalone_el(doc, 'description', cfg['summary'])
    camera = cfg['overview']; standalone_view(doc, camera['lon'], camera['lat'], camera['range_m'])
    add_north_return_roads(doc, standalone_el, standalone_view)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_index():
    cfg = load(); roads, manifest = read_geometry(cfg)
    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['summary'], cfg['geometry_note'],
             cfg['comparison_note'], cfg['attribution'], '', '逐路号显示与数据状态']
    for road in roads:
        lines += [road['name'], road['note'], data_text(road), '']
    for card in cfg['cards']:
        lines += [card['name'], *card['paragraphs'], '']
    limitations = manifest.get('limitations', [])
    lines += ['数据缺口与限度']+(limitations if isinstance(limitations, list) else [str(limitations)])
    lines += ['', '道路几何清单：'+cfg['manifest_file'], '来源与限度']
    for key, source in cfg['sources'].items():
        lines += [key+'｜'+source['title'], source['url'], source['supports'], '']
    if cfg.get('google_earth_import'):
        record = cfg['google_earth_import']; lines += ['Google Earth核验', record['note']]
        if record.get('screenshot'): lines += ['核验截图：'+record['screenshot']]
    note = '\n'.join(lines).rstrip()+'\n'
    (ROOT/'北返现代道路对照说明.txt').write_text(note, encoding='utf-8')
    with (ROOT/'北返现代道路对照.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['路号', '显示名称', 'OSM要素数', '所绘分离片段数', '采集日期', '比较与编号限度', '来源键', '来源链接', '几何许可'])
        for road in roads:
            writer.writerow([road['ref'], road['name'], len(road['features']), len(road['pieces']), '；'.join(road['dates']), road['note'],
                             '；'.join(road['source_keys']), '；'.join(cfg['sources'][key]['url'] for key in road['source_keys']), cfg['attribution']])
    return note


def write_north_return_road_outputs():
    ET.register_namespace('', KML); raw = make_supplement()
    (ROOT/(NAME+'.kml')).write_bytes(raw)
    icon = icon_png((255, 255, 255)); (ROOT/LABEL_ICON).parent.mkdir(exist_ok=True)
    (ROOT/LABEL_ICON).write_bytes(icon)
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw); archive.writestr(LABEL_ICON, icon)
    return write_index()


if __name__ == '__main__':
    write_north_return_road_outputs()
