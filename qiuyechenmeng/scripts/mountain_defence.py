"""Mountain-defence context with one optional modern settlement reference."""
from pathlib import Path
import html
import json


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/八噶山金珠山核对.json'
LAYER_NAME = '八噶山与金珠山｜八百余里指代待核'


def load():
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


def source_links(check, source_ids):
    links = []
    for source_id in source_ids:
        source = check['sources'][source_id]
        links.append('<a href="' + html.escape(source['url'], quote=True) + '">' +
                     html.escape(source['title']) + '</a>')
    return '<br/>'.join(links)


def overview_html(check):
    return ''.join('<p>' + html.escape(check[key]) + '</p>' for key in
                   ['scope', 'geography_note', 'distance_note', 'timing_note'])


def card_html(check, card):
    body = '<p>' + html.escape(card['text']) + '</p>'
    links = source_links(check, card['source_ids'])
    return body + ('<p>' + links + '</p>' if links else '')


def add_mountain_defence(doc, el, view, anchors, standalone=False):
    check = load()
    body = overview_html(check)
    folder = el(doc, 'Folder', id='baga_jinzhu_defence')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'open', 1)
    el(folder, 'description', body)
    guide = el(folder, 'Placemark', id='mountain_defence_guide')
    el(guide, 'name', '本段说明｜山名、八百余里与派兵结局')
    el(guide, 'description', body)
    for card in check['cards']:
        placemark = el(folder, 'Placemark', id='mountain_defence_' + card['id'])
        el(placemark, 'name', card['name'])
        el(placemark, 'description', card_html(check, card))
    if standalone:
        lon, lat = anchors['qundo']
        placemark = el(folder, 'Placemark', id='mountain_defence_qundo_reference')
        el(placemark, 'name', '春多寺／倾多寺〔原文距离参照；默认隐藏〕')
        el(placemark, 'visibility', 0)
        description = '<p>此点为现代倾多聚落的方位参照，不是旧寺建筑确址。</p>'
        description += '<p>原文“八百余里”的修饰对象仍待核，不能解释为此点至金珠拉的直线距离；'
        description += '也不是陈渠珍本人行程的距离。</p>'
        description += f'<p>现代聚落参照坐标：{lon}°E、{lat}°N。</p>'
        description += '<p>' + source_links(check, ['chapter6', 'qundo', 'qundo_coordinate']) + '</p>'
        el(placemark, 'description', description)
        view(placemark, lon, lat, 150000)
        el(placemark, 'styleUrl', '#minor_landmark')
        point = el(placemark, 'Point')
        el(point, 'altitudeMode', 'clampToGround')
        el(point, 'coordinates', f'{lon},{lat},0')
    return folder


def write_mountain_index():
    check = load()
    sections = ['八噶山金珠山核对', '核对日期：' + check['checked_at'],
                '原句：' + check['quote']]
    sections.extend(check[key] for key in
                    ['scope', 'geography_note', 'distance_note', 'timing_note',
                     'coordinate_note'])
    for card in check['cards']:
        section = card['name'] + '\n' + card['text']
        if card['source_ids']:
            section += '\n依据：' + '；'.join(
                check['sources'][source_id]['title']
                for source_id in card['source_ids'])
        sections.append(section)
    sections.append('来源与证据限度')
    for source in check['sources'].values():
        sections.append(source['title'] + '\n' + source['url'] + '\n' +
                        source['supports'])
    sections.append('Google Earth核验\n' + check['google_earth_import']['note'])
    text = '\n\n'.join(sections) + '\n'
    (ROOT / '八噶山金珠山核对说明.txt').write_text(text, encoding='utf-8')
    return text
