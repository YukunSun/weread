"""Chapter 5's planned stages, distinct from the later journeys and campaigns."""
from pathlib import Path
import csv
import html
import json
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/波密三步部署核对.json'
LAYER_NAME = '波密进军三步部署｜计划目标与待考地名'


def load():
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


def source_links(config, ids):
    return '<br/>'.join('<a href="' + html.escape(config['sources'][key]['url'], quote=True) + '">' +
                       html.escape(config['sources'][key]['title']) + '</a>' for key in ids)


def overview_html(config):
    body = '<h3>钟颖所定进军波密的三步部署</h3><p>' + html.escape(config['quote']) + '</p>'
    for key in ['scope', 'sequence_note', 'timing_note', 'coordinate_note']:
        body += '<p>' + html.escape(config[key]) + '</p>'
    for stage in config['stages']:
        body += '<p><b>' + html.escape(stage['label']) + '</b><br/>' + html.escape(stage['note']) + '</p>'
    body += '<p>完整阅读图沿用03、08层已有的冬九、通麦、倾多地区点，本说明层不重复放点。'
    body += '独立补图显示同样的三个地区参照点，叠加旧图时可隐藏旧版同名点，避免重复。</p>'
    return body + '<p>' + source_links(config, ['chapter5', 'chapter6a', 'annotation35']) + '</p>'


def place_html(config, place, anchors):
    body = '<h3>' + html.escape(place['label']) + '</h3><p><b>阶段：</b>' + str(place['stage'])
    body += '<br/><b>书中名：</b>' + html.escape(place['book_name']) + '<br/><b>定位性质：</b>'
    body += html.escape(place['certainty']) + '</p><p>' + html.escape(place['note']) + '</p>'
    body += '<p>' + html.escape(config['scope']) + '</p>'
    if place.get('anchor'):
        lon, lat = anchors[place['anchor']]
        body += f'<p><b>沿用地区参照：</b>{lon:.5f}°E，{lat:.5f}°N。' + html.escape(place['coordinate_note']) + '</p>'
    else:
        body += '<p><b>未定位：</b>仅保留文字条目，不在地图上赋坐标。</p>'
    return body + '<p>' + html.escape(config['timing_note']) + '</p><p>' + source_links(config, place['source_ids']) + '</p>'


def anchor_html(anchor, anchors):
    config = load()
    place = next((p for p in config['places'] if p.get('anchor') == anchor), None)
    return place_html(config, place, anchors) if place else ''


def add_campaign_plan(doc, el, view, kcolor, anchors, bundled=False, reference_points=False):
    config = load()
    if reference_points:
        style = el(doc, 'Style', id='campaign_reference')
        iconstyle = el(style, 'IconStyle')
        el(iconstyle, 'color', 'ffffffff' if bundled else kcolor('#ffd166'))
        el(iconstyle, 'scale', 1)
        icon = el(iconstyle, 'Icon')
        el(icon, 'href', 'icons/campaign_reference.png' if bundled else 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
        label = el(style, 'LabelStyle')
        el(label, 'color', 'ffffffff'); el(label, 'scale', 0.9)
    folder = el(doc, 'Folder', id='bomi_campaign_plan')
    el(folder, 'name', LAYER_NAME); el(folder, 'open', 1)
    el(folder, 'description', overview_html(config))
    view(folder, 95.17, 29.98, 175000)
    guide = el(folder, 'Placemark', id='campaign_plan_guide')
    el(guide, 'name', '本段说明｜三步是部署，不是三天或已走完的行程')
    el(guide, 'description', overview_html(config))
    for stage in config['stages']:
        group = el(folder, 'Folder', id='campaign_stage_' + str(stage['id']))
        el(group, 'name', stage['label']); el(group, 'open', 1)
        el(group, 'description', '<p>' + html.escape(stage['note']) + '</p>')
        for place in [p for p in config['places'] if p['stage'] == stage['id']]:
            pm = el(group, 'Placemark', id='campaign_' + place['id'])
            el(pm, 'name', place['label'])
            el(pm, 'description', place_html(config, place, anchors))
            extended = el(pm, 'ExtendedData')
            for key, value in [('stage', stage['id']), ('book_name', place['book_name']),
                               ('certainty', place['certainty']), ('existing_anchor', place.get('anchor', '')),
                               ('role', '作战部署目标；不据此确认完成行军')]:
                data = el(extended, 'Data', name=key); el(data, 'value', value)
            if place.get('anchor') and reference_points:
                lon, lat = anchors[place['anchor']]
                view(pm, lon, lat, 65000)
                el(pm, 'styleUrl', '#campaign_reference')
                point = el(pm, 'Point'); el(point, 'altitudeMode', 'clampToGround')
                el(point, 'coordinates', f'{lon},{lat},0')
    return folder


def write_campaign_indexes(anchors):
    config = load()
    text = '波密进军三步部署核对\n核对日期：' + config['checked_at'] + '\n\n原句：' + config['quote'] + '\n\n'
    for key in ['scope', 'sequence_note', 'timing_note', 'coordinate_note']:
        text += config[key] + '\n\n'
    for stage in config['stages']:
        text += stage['label'] + '\n' + stage['note'] + '\n\n'
        for place in [p for p in config['places'] if p['stage'] == stage['id']]:
            text += place['label'] + '\n' + place['certainty'] + '\n' + place['note'] + '\n'
            if place.get('anchor'):
                lon, lat = anchors[place['anchor']]
                text += f'沿用地区参照：{lon}°E，{lat}°N。' + place['coordinate_note'] + '\n'
            else:
                text += '无几何坐标。\n'
            text += '\n'
    text += '完整阅读图只新增三阶段文字说明，三个现有点的弹窗补充部署角色；不增加重复点或路线。\n'
    text += '独立“艽野尘梦_波密三步部署.kmz”含3个现代地区参照点、4条未定位地名及总说明，无路线。\n\n来源与证据限度\n'
    for source in config['sources'].values():
        text += '\n' + source['title'] + '\n' + source['supports'] + '\n' + source['url'] + '\n'
    text += '\nGoogle Earth核验\n' + config['google_earth_import']['note'] + '\n'
    (output_path('docs', '波密三步部署核对说明.txt')).write_text(text, encoding='utf-8')
    with (output_path('tables', '波密三步部署地名对照.csv')).open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['id', '阶段', '书中名', '地图标签', '定位性质', '复用地点id', '经度', '纬度', '说明', '来源'])
        for place in config['places']:
            coords = anchors[place['anchor']] if place.get('anchor') else ('', '')
            writer.writerow([place['id'], place['stage'], place['book_name'], place['label'], place['certainty'],
                             place.get('anchor', ''), *coords, place['note'],
                             '；'.join(config['sources'][key]['url'] for key in place['source_ids'])])
    return text
