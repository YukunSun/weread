"""Shared reading of annotation 10, including places that cannot yet be mapped."""
from pathlib import Path
import html
import json
from output_paths import output_path

ROOT = Path(__file__).resolve().parents[1]
CHECK = json.loads((ROOT/'data/route_checks/甘孜昌都校注十.json').read_text())
SEQUENCE = CHECK['mapped_sequence']


def route_check_html():
    body = '<h3>校注十：甘孜至昌都路线校对</h3>'
    body += '<p><b>文字顺序：</b>'+html.escape(CHECK['text_sequence'])+'</p>'
    body += '<p>'+html.escape(CHECK['interpretation'])+'</p>'
    for item in CHECK['unlocated']:
        body += '<p><b>'+html.escape(item['name'])+'：</b>'+html.escape(item['note'])+'</p>'
    body += '<p><b>耗时：</b>'+html.escape(CHECK['timing_note'])+'</p>'
    body += '<p>'+html.escape(CHECK['distance_note'])+'</p>'
    for e in CHECK['evidence']:
        body += '<p><a href="'+html.escape(e['url'], quote=True)+'">'+html.escape(e['title'])+'</a><br/>'+html.escape(e['supports'])+'</p>'
    return body


def check_shared_places(main_places, post_places):
    """Fail the build if the two maps disagree about this corrected corridor."""
    for key in SEQUENCE:
        assert main_places[key][3:5] == (post_places[key]['lon'], post_places[key]['lat']), key
        assert post_places[key]['existing'], key


def write_route_check(places, distance):
    text = '甘孜至昌都路线校对\n核对日期：'+CHECK['checked_at']+'\n\n'
    text += '依据：用户提供的任乃强校注十；不能改称陈渠珍正文逐站亲记。\n\n'
    text += CHECK['text_sequence']+'\n\n'+CHECK['interpretation']+'\n\n'
    for item in CHECK['unlocated']:
        text += item['name']+'：'+item['note']+'\n\n'
    text += '耗时：'+CHECK['timing_note']+'\n\n'+CHECK['distance_note']+'\n\n'
    text += '可定位代表点间的直距（km，四舍五入）\n'
    for a,b in zip(SEQUENCE, SEQUENCE[1:]):
        text += places[a][2]+' → '+places[b][2]+f'：约{distance(a,b):.0f} km\n'
    text += '\n打火沟通行口、卡工和纳夺土司辖境尚未定位，不给它们填直距；上列直连代表点之间仍可能省略旧站。\n'
    text += '\n逐点参照\n'
    for key in SEQUENCE:
        row = places[key]
        text += f'\n{row[1]}｜{row[3]}, {row[4]}｜{row[7]}\n{row[9]}\n{row[8]}\n'
    text += '\n证据及适用范围\n'
    for e in CHECK['evidence']:
        text += '\n'+e['title']+'\n'+e['supports']+'\n'+e['url']+'\n'
    text += '\n同普点使用OpenStreetMap地名点，© OpenStreetMap contributors，ODbL 1.0。原始响应保存在data/route_checks/tongpu_osm_node.json。\n'
    text += '\n云端验收（2026-10-31）\n完整KMZ已导入原Google Earth项目，新根目录为“《艽野尘梦》阅读地图｜校注十路线校对版”，界面显示已保存到Google云端硬盘。旧完整地图及旧河流、历史背景补充包已隐藏；新版内置这些内容。\n已打开大金寺点及R1路线弹窗，核对新节点顺序、46／33／19 km直距，以及卡工以西野宿三日的校注限定。Google Earth仅提示忽略Region、maxLines、textColor三种显示字段。未逐段复原历史旧道，未逐点测绘验收。\n'
    (output_path('docs', '甘孜昌都路线校对说明.txt')).write_text(text)
