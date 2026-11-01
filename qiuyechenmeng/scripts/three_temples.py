"""Geometry-free cards for the border army's three parallel temple captures."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]


def load():
    return json.loads((ROOT / 'data/place_checks/边军攻取上波密三寺核对.json').read_text(encoding='utf-8'))


def card_html(cfg, card):
    body = '<h3>' + html.escape(card['name']) + '</h3>'
    body += ''.join('<p>' + html.escape(p) + '</p>' for p in card['paragraphs'])
    body += '<p><b>镜头与定位：</b>' + html.escape(card['look_at']['note']) + '</p>'
    return body + '<p>' + '<br/>'.join(
        '<a href="' + html.escape(s['url'], quote=True) + '">' + html.escape(s['title']) + '</a>'
        for s in cfg['sources']) + '</p>'


def add_folder(doc, el, view):
    cfg = load()
    folder = el(doc, 'Folder', id='three_temples_check')
    el(folder, 'name', '18 边军攻取上波密三寺｜并列战果')
    el(folder, 'open', 1)
    el(folder, 'description', cfg['summary'])
    camera = cfg['overview']
    view(folder, camera['lon'], camera['lat'], camera['range_m'])
    for card in cfg['cards']:
        pm = el(folder, 'Placemark', id='three_temples_' + card['id'])
        el(pm, 'name', card['name'])
        el(pm, 'description', card_html(cfg, card))
        camera = card['look_at']
        view(pm, camera['lon'], camera['lat'], camera['range_m'])
    return cfg


def write_index():
    cfg = load()
    note = ('边军攻取上波密三寺｜并列战果\n核对日期：' + cfg['checked_at'] + '\n\n'
            + cfg['summary'] + '\n\n')
    for card in cfg['cards']:
        note += card['name'] + '\n' + '\n'.join(card['paragraphs']) + '\n'
        note += '镜头与定位：' + card['look_at']['note'] + '\n\n'
    note += ('完整阅读地图18层与独立“艽野尘梦_边军攻取三寺.kmz”均有四张可点击说明卡，选择一份显示。'
             '本层只移动镜头到既有地区参照或概览视图，不新增寺院点、路线、范围或搜索圈；'
             '春多与松宗复用已有点的地区方位，薄宗没有坐标，主要点及小地名数量不增加。\n\n来源及限度\n')
    for source in cfg['sources']:
        note += '\n' + source['title'] + '\n' + source['supports'] + '\n' + source['url'] + '\n'
    if cfg.get('google_earth_import'):
        note += '\nGoogle Earth核验\n' + cfg['google_earth_import']['note'] + '\n'
        if cfg['google_earth_import'].get('screenshot'):
            note += '核验截图：' + cfg['google_earth_import']['screenshot'] + '\n'
    (ROOT / '边军攻取上波密三寺核对说明.txt').write_text(note, encoding='utf-8')
    return note
