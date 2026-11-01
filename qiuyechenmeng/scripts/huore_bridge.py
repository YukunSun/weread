"""Geometry-free reading cards for the unlocated Huore bridge."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]


def load():
    return json.loads((ROOT / 'data/place_checks/夥惹桥核对.json').read_text(encoding='utf-8'))


def card_html(cfg, card):
    body = '<h3>' + html.escape(card['name']) + '</h3>'
    body += ''.join('<p>' + html.escape(p) + '</p>' for p in card['paragraphs'])
    body += '<p><b>镜头与定位：</b>' + html.escape(card['look_at']['note']) + '</p>'
    return body + '<p>' + '<br/>'.join(
        '<a href="' + html.escape(s['url'], quote=True) + '">' + html.escape(s['title']) + '</a>'
        for s in cfg['sources']) + '</p>'


def add_folder(doc, el, view):
    cfg = load()
    folder = el(doc, 'Folder', id='huore_bridge_check')
    el(folder, 'name', '20 夥惹／夥若桥｜未准过桥与地望待考')
    el(folder, 'open', 1)
    el(folder, 'description', cfg['summary'])
    camera = cfg['overview']
    view(folder, camera['lon'], camera['lat'], camera['range_m'])
    for card in cfg['cards']:
        pm = el(folder, 'Placemark', id='huore_bridge_' + card['id'])
        el(pm, 'name', card['name'])
        el(pm, 'description', card_html(cfg, card))
        camera = card['look_at']
        view(pm, camera['lon'], camera['lat'], camera['range_m'])
    return cfg


def write_index():
    cfg = load()
    note = ('夥惹／夥若桥｜未准过桥与地望待考\n核对日期：' + cfg['checked_at'] + '\n\n'
            + cfg['summary'] + '\n\n')
    for card in cfg['cards']:
        note += card['name'] + '\n' + '\n'.join(card['paragraphs']) + '\n'
        note += '镜头与定位：' + card['look_at']['note'] + '\n\n'
    note += ('完整阅读地图20层与独立“艽野尘梦_夥惹桥.kmz”均有两张可点击说明卡，选择一份显示。'
             '本层只移动镜头到编辑选取的波密—墨脱地区概览，不含地点、路线、范围或搜索圈几何；'
             '没有桥址坐标、岸别或边界推定，不参与陈渠珍个人行程距离和耗时合计。\n\n来源及限度\n')
    for source in cfg['sources']:
        note += '\n' + source['title'] + '\n' + source['supports'] + '\n' + source['url'] + '\n'
    if cfg.get('google_earth_import'):
        note += '\nGoogle Earth核验\n' + cfg['google_earth_import']['note'] + '\n'
        if cfg['google_earth_import'].get('screenshot'):
            note += '核验截图：' + cfg['google_earth_import']['screenshot'] + '\n'
    (ROOT / '夥惹桥核对说明.txt').write_text(note, encoding='utf-8')
    return note
