"""Text-only context for the first northbound overnight stop and muster at Ningduo."""
from pathlib import Path
import csv
import html
import json
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'
NAME = '艽野尘梦_凝多首宿清点'


def load():
    return json.loads((ROOT/'data/route_checks/凝多首宿清点.json').read_text(encoding='utf-8'))


def paragraphs(items):
    return ''.join('<p>'+html.escape(item)+'</p>' for item in items)


def source_links(cfg, keys=None):
    keys = cfg['sources'] if keys is None else keys
    return '<p>'+'<br/>'.join(
        '<a href="'+html.escape(cfg['sources'][key]['url'], quote=True)+'">'
        +html.escape(cfg['sources'][key]['title'])+'</a>' for key in keys)+'</p>'


def overview_html(cfg):
    return ('<h3>'+html.escape(cfg['title'])+'</h3>'
            +paragraphs([cfg['chapter'], cfg['quote'], cfg['summary'], cfg['scope']])
            +''.join('<h3>'+html.escape(card['name'])+'</h3>'+paragraphs([card['text']])
                     for card in cfg['cards'])
            +paragraphs([cfg['source_note']])+source_links(cfg))


def add_ningduo_muster(doc, el):
    """Add three explanation cards, deliberately without geometry or camera views."""
    cfg = load()
    folder = el(doc, 'Folder', id='ningduo_first_overnight_muster')
    el(folder, 'name', cfg['layer_name'])
    el(folder, 'open', 1)
    el(folder, 'description', overview_html(cfg))
    for card in cfg['cards']:
        placemark = el(folder, 'Placemark', id='ningduo_muster_'+card['id'])
        el(placemark, 'name', card['name'])
        el(placemark, 'description', '<h3>'+html.escape(card['name'])+'</h3>'
           +paragraphs([card['text'], cfg['scope']])+source_links(cfg, card['source_keys']))
        metadata = el(placemark, 'ExtendedData')
        for name, value in [('chapter', cfg['chapter']), ('location_status', '凝多现代位置待考；暂不标宿营点')]:
            item = el(metadata, 'Data', name=name)
            el(item, 'value', value)
    return folder


def make_ningduo_muster():
    cfg = load()
    root = ET.Element('{'+KML+'}kml')

    def el(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, '{'+KML+'}'+tag, attrs)
        if text is not None:
            node.text = str(text)
        return node

    doc = el(root, 'Document', id='ningduo_first_overnight_supplement')
    el(doc, 'name', '《艽野尘梦》凝多首宿清点｜地点待考')
    el(doc, 'open', 1)
    el(doc, 'description', overview_html(cfg))
    add_ningduo_muster(doc, el)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_ningduo_outputs():
    cfg = load()
    ET.register_namespace('', KML)
    raw = make_ningduo_muster()
    (ROOT/(NAME+'.kml')).write_bytes(raw)
    with zipfile.ZipFile(ROOT/(NAME+'.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw)

    lines = [cfg['title'], '核对日期：'+cfg['checked_at'], '', cfg['chapter'],
             cfg['quote'], '', cfg['summary'], cfg['scope'], '']
    for card in cfg['cards']:
        lines += [card['name'], card['text'], '']
    lines += [cfg['source_note'], '',
              '完整阅读地图17层与独立KMZ包含同样三条无坐标说明，可选择一份阅读。部分客户端可能省略无几何条目，完整文字也保留在文件夹说明和本TXT。凝多未落点，未设置相机视角，未改变其他地点或路线。',
              '', '来源与证据限度']
    for source in cfg['sources'].values():
        lines += [source['title'], source['url'], source['supports'], '']
    lines += ['Google Earth核验：'+cfg['google_earth_import']['status'],
              cfg['google_earth_import']['note']]
    note = '\n'.join(lines)+'\n'
    (ROOT/'凝多首宿清点说明.txt').write_text(note, encoding='utf-8')
    with (ROOT/'凝多首宿清点.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['条目', '章节', '说明', '定位性质', '来源'])
        for card in cfg['cards']:
            urls = '；'.join(cfg['sources'][key]['url'] for key in card['source_keys'])
            writer.writerow([card['name'], cfg['chapter'], card['text'], '无几何说明；凝多今址待考', urls])
    return note


if __name__ == '__main__':
    write_ningduo_outputs()
