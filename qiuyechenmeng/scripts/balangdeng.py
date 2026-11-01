"""Geometry-free reading cards for Balangdeng and the four mountain barriers."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]


def load():
    return json.loads((ROOT / 'data/place_checks/八浪登核对.json').read_text(encoding='utf-8'))


def _sources(cfg):
    return '<p>' + '<br/>'.join(
        '<a href="' + html.escape(s['url'], quote=True) + '">' + html.escape(s['title']) + '</a>'
        for s in cfg['sources']) + '</p>'


def card_html(cfg, card):
    return ('<h3>' + html.escape(card['name']) + '</h3>'
            + ''.join('<p>' + html.escape(p) + '</p>' for p in card['paragraphs'])
            + '<p><b>镜头与定位：</b>' + html.escape(cfg['look_at']['note']) + '</p>'
            + _sources(cfg))


def add_folder(doc, el, view):
    cfg = load()
    folder = el(doc, 'Folder', id='balangdeng_check')
    el(folder, 'name', '17 八浪登与四重山核对｜确址待考')
    el(folder, 'open', 1)
    el(folder, 'description', cfg['summary'] + ' ' + cfg['look_at']['note'])
    camera = cfg['look_at']
    view(folder, camera['lon'], camera['lat'], camera['range_m'])
    for card in cfg['cards']:
        pm = el(folder, 'Placemark', id='balangdeng_' + card['id'])
        el(pm, 'name', card['name'])
        el(pm, 'description', card_html(cfg, card))
        view(pm, camera['lon'], camera['lat'], camera['range_m'])
    return cfg


def write_index():
    cfg = load()
    note = ('八浪登与四重山核对｜确址待考\n核对日期：' + cfg['checked_at'] + '\n\n'
            + cfg['summary'] + '\n\n')
    for card in cfg['cards']:
        note += card['name'] + '\n' + '\n'.join(card['paragraphs']) + '\n\n'
    note += '镜头参照\n' + cfg['look_at']['note'] + '\n\n'
    note += (f'完整阅读地图17层与独立“艽野尘梦_八浪登山路核对.kmz”均有{len(cfg["cards"])}张可点击说明卡，选择一份显示。'
             '卡片只移动镜头，不含地点、路线、范围或搜索圈几何；没有新增物理点，不参与路线距离及耗时合计。\n\n来源及限度\n')
    for source in cfg['sources']:
        note += '\n' + source['title'] + '\n' + source['supports'] + '\n' + source['url'] + '\n'
    if cfg.get('google_earth_import'):
        note += '\nGoogle Earth核验\n' + cfg['google_earth_import']['note'] + '\n'
        if cfg['google_earth_import'].get('screenshot'):
            note += '核验截图：' + cfg['google_earth_import']['screenshot'] + '\n'
    (ROOT / '八浪登核对说明.txt').write_text(note, encoding='utf-8')
    return note
