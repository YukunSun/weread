"""Geometry-free reading cards for annotation 44 and the unlocated Hala Wusu stop."""
from pathlib import Path
import html
import json
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_哈喇乌苏校注44'


def load():
    return json.loads((ROOT/'data/place_checks/哈喇乌苏校注44核对.json').read_text(encoding='utf-8'))


def source_links(cfg, keys):
    return '<p>'+'<br/>'.join(
        '<a href="'+html.escape(cfg['sources'][key]['url'], quote=True)+'">'
        +html.escape(cfg['sources'][key]['title'])+'</a>' for key in keys)+'</p>'


def card_html(cfg, card):
    return ('<h3>'+html.escape(card['name'])+'</h3>'
            +''.join('<p>'+html.escape(p)+'</p>' for p in card['paragraphs'])
            +'<p><b>镜头与定位：</b>'+html.escape(cfg['overview']['note'])+'</p>'
            +source_links(cfg, card['source_keys']))


def add_hala_wusu(doc, el, view):
    cfg = load()
    folder = el(doc, 'Folder', id='hala_wusu_annotation44')
    el(folder, 'name', cfg['layer_name'])
    el(folder, 'open', 1)
    el(folder, 'description', cfg['summary'])
    camera = cfg['overview']
    view(folder, camera['lon'], camera['lat'], camera['range_m'])
    for card in cfg['cards']:
        placemark = el(folder, 'Placemark', id='hala_wusu_'+card['id'])
        el(placemark, 'name', card['name'])
        el(placemark, 'description', card_html(cfg, card))
        view(placemark, camera['lon'], camera['lat'], camera['range_m'])
    return folder


def make_hala_wusu_supplement():
    cfg = load()
    root = ET.Element('{'+KML+'}kml')

    def el(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, '{'+KML+'}'+tag, attrs)
        if text is not None:
            node.text = str(text)
        return node

    def view(node, lon, lat, range_m):
        camera = el(node, 'LookAt')
        for name, value in [('longitude', lon), ('latitude', lat), ('altitude', 0),
                            ('heading', 0), ('tilt', 0), ('range', range_m),
                            ('altitudeMode', 'clampToGround')]:
            el(camera, name, value)

    doc = el(root, 'Document', id='hala_wusu_annotation44_supplement')
    el(doc, 'name', '《艽野尘梦》'+cfg['title'])
    el(doc, 'open', 1)
    el(doc, 'description', cfg['summary'])
    camera = cfg['overview']
    view(doc, camera['lon'], camera['lat'], camera['range_m'])
    add_hala_wusu(doc, el, view)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_index():
    cfg = load()
    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['chapter'],
             cfg['quote'], '', cfg['summary'], '']
    for card in cfg['cards']:
        lines += [card['name'], *card['paragraphs'], '']
    lines += ['镜头与定位', cfg['overview']['note'], '',
              '完整阅读地图的校注44层与独立KMZ含相同五张无几何说明卡，选择一份显示。'
              '本层不新增地点、河线、路线、边界或搜索圈，既有行程距离与耗时统计保持原口径。',
              '', '行程与考订限度', *cfg['limits'], '', '来源与证据限度']
    for source in cfg['sources'].values():
        lines += [source['title'], source['url'], source['supports'], '']
    if cfg.get('google_earth_import'):
        record = cfg['google_earth_import']
        lines += ['Google Earth核验', record['note']]
        if record.get('screenshot'):
            lines += ['核验截图：'+record['screenshot']]
    note = '\n'.join(lines).rstrip()+'\n'
    (ROOT/'哈喇乌苏校注44核对说明.txt').write_text(note, encoding='utf-8')
    return note


def write_hala_wusu_outputs():
    ET.register_namespace('', KML)
    raw = make_hala_wusu_supplement()
    (ROOT/(NAME+'.kml')).write_bytes(raw)
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw)
    return write_index()


if __name__ == '__main__':
    write_hala_wusu_outputs()
