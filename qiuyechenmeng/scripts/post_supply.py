"""Explain the poor/rich eight post stages without inventing station coordinates."""
from pathlib import Path
import csv
import html
import json
import xml.etree.ElementTree as ET
import zipfile
from poor_rich_posts import add_poor_rich_posts, write_poor_rich_files
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
KML = 'http://www.opengis.net/kml/2.2'


def load():
    return json.loads((ROOT/'data/postroads/穷富八站.json').read_text(encoding='utf-8'))


def paragraphs(items):
    return ''.join('<p>'+html.escape(item)+'</p>' for item in items)


def source_links(cfg, keys=None):
    keys = cfg['sources'] if keys is None else keys
    return '<p>'+'<br/>'.join(
        '<a href="'+html.escape(cfg['sources'][key]['url'], quote=True)+'">'
        +html.escape(cfg['sources'][key]['title'])+'</a>' for key in keys)+'</p>'


def segment_html(segment):
    return ('<h3>'+html.escape(segment['name'])+'</h3>'
            +paragraphs([segment['from']+' → '+segment['to'], segment['via'],
                         segment['description'], segment['time']]))


def overview_html(cfg):
    return ('<h3>'+html.escape(cfg['title'])+'</h3>'
            +paragraphs([cfg['source_label'], cfg['summary'], *cfg['limits']])
            +''.join(segment_html(segment) for segment in cfg['segments'])
            +paragraphs([place['name']+'：'+place['note'] for place in cfg['place_checks']])
            +paragraphs([cfg['author_route'], cfg['later_comparison']['text']])
            +source_links(cfg))


def add_post_supply(parent, el, view, kcolor, bundled=False, reuse_ids=None):
    return add_poor_rich_posts(parent, el, view, kcolor, bundled, reuse_ids=reuse_ids)


def _add_supply_text(parent, el, view):
    cfg = load()
    folder = el(parent, 'Folder', id='post_supply_eight_stages')
    el(folder, 'name', '11H 穷八站／富八站｜凝多分界，范围与站址待核')
    el(folder, 'open', 0)
    el(folder, 'description', overview_html(cfg))
    # A camera view only; no Point, line, polygon or asserted boundary is added.
    view(folder, 93.0, 30.2, 550000)
    for segment in cfg['segments']:
        pm = el(folder, 'Placemark', id='post_supply_'+segment['id'])
        el(pm, 'name', segment['name']+'｜'+segment['from']+' → '+segment['to'])
        el(pm, 'description', segment_html(segment)
           +paragraphs(cfg['limits']+[cfg['author_route']])+source_links(cfg, ['annotation21']))
    for place in cfg['place_checks']:
        pm = el(folder, 'Placemark', id='post_supply_'+place['id'])
        el(pm, 'name', place['name']+'【未定位】')
        el(pm, 'description', paragraphs([place['certainty'], place['note']])
           +source_links(cfg, place['sources']))
    pm = el(folder, 'Placemark', id='post_supply_later_comparison')
    el(pm, 'name', cfg['later_comparison']['label'])
    el(pm, 'description', paragraphs([cfg['later_comparison']['text']])
       +source_links(cfg, ['later_account']))
    return folder


def write_supply_outputs():
    cfg = load()
    ET.register_namespace('', KML)

    def el(parent, tag, text=None, **attrs):
        node = ET.SubElement(parent, '{'+KML+'}'+tag, attrs)
        if text is not None:
            node.text = str(text)
        return node

    def view(parent, lon, lat, distance):
        camera = el(parent, 'LookAt')
        for tag, value in [('longitude', lon), ('latitude', lat), ('altitude', 0),
                           ('range', distance), ('altitudeMode', 'clampToGround')]:
            el(camera, tag, value)

    root = ET.Element('{'+KML+'}kml')
    doc = el(root, 'Document', id='post_supply_supplement')
    el(doc, 'name', '《艽野尘梦》穷八站与富八站｜说明，无精确分界')
    el(doc, 'open', 1)
    el(doc, 'description', overview_html(cfg))
    _add_supply_text(doc, el, view)
    ET.indent(root, space='  ')
    raw = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    name = '艽野尘梦_穷富八站说明'
    (output_path('maps', name + '.kml')).write_bytes(raw)
    with zipfile.ZipFile(output_path('maps', name + '.kmz'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('doc.kml', raw)

    lines = [cfg['title'], '核对日期：'+cfg['reviewed'], '', cfg['source_label'],
             cfg['quote'], '', cfg['summary'], '', *cfg['limits'], '']
    for segment in cfg['segments']:
        lines += [segment['name']+'：'+segment['from']+' → '+segment['to'],
                  segment['via'], segment['description'], segment['time'], '']
    for place in cfg['place_checks']:
        lines += [place['name'], place['certainty'], place['note'], '']
    lines += [cfg['author_route'], '', cfg['later_comparison']['label'],
              cfg['later_comparison']['text'], '',
              '完整阅读地图与南北驿路对照的11H均含本说明；独立KMZ只含文字文件夹和无坐标条目，未画路线或分界。部分客户端可能省略无坐标条目，可读文件夹说明或本TXT。',
              cfg['publication'], '', '来源']
    for source in cfg['sources'].values():
        lines += [source['title'], source['url']]
    (output_path('docs', '穷富八站核对说明.txt')).write_text('\n'.join(lines)+'\n', encoding='utf-8')
    with (output_path('tables', '穷富八站_分段对照.csv')).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['分段', '起点', '终点', '已知中间节点', '供应条件', '耗时口径', '定位限制', '来源'])
        for segment in cfg['segments']:
            writer.writerow([segment['name'], segment['from'], segment['to'], segment['via'],
                             segment['description'], segment['time'], cfg['limits'][-1], cfg['source']])
    write_poor_rich_files()


if __name__ == '__main__':
    write_supply_outputs()
