"""Text-only context for the summons to Katuo and the unlocated mountain region."""
from pathlib import Path
import html
import json


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/place_checks/卡拖与野人山核对.json'
LAYER_NAME = '卡拖召议与野人山｜休息1日；赴此2日'


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
                   ['scope', 'sequence_note', 'timing_note', 'geography_note'])


def card_html(check, card):
    body = '<p>' + html.escape(card['text']) + '</p>'
    links = source_links(check, card['source_ids'])
    return body + ('<p>' + links + '</p>' if links else '')


def add_katuo_context(doc, el, view, anchors, bundled=False, standalone=False):
    check = load()
    body = overview_html(check)
    folder = el(doc, 'Folder', id='katuo_consultation')
    el(folder, 'name', LAYER_NAME)
    el(folder, 'open', 1)
    el(folder, 'description', body)
    guide = el(folder, 'Placemark', id='katuo_consultation_guide')
    el(guide, 'name', '本段说明｜卡拖召议与野人山的地域限度')
    el(guide, 'description', body)
    for card in check['cards']:
        placemark = el(folder, 'Placemark', id='katuo_context_' + card['id'])
        el(placemark, 'name', card['name'])
        el(placemark, 'description', card_html(check, card))
    return folder


def write_katuo_index():
    check = load()
    sections = ['卡拖与野人山核对', '原句：' + check['quote']]
    sections.extend(check[key] for key in
                    ['scope', 'sequence_note', 'timing_note', 'geography_note',
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
        sections.append(source['title'] + '\n' + source['supports'] + '\n' +
                        source['url'])
    sections.append('Google Earth核验\n' + check['google_earth_import']['note'])
    text = '\n\n'.join(sections) + '\n'
    (ROOT / '卡拖与野人山核对说明.txt').write_text(text, encoding='utf-8')
    return text
