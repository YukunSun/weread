# -*- coding: utf-8 -*-
"""Build a non-geographic reading diagram for chapter two; standard library only."""
from pathlib import Path
import html
import json
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/annotation11'
SVG_NAME = '昌都恩达_校注十一顺序图.svg'
HTML_NAME = '昌都恩达_校注十一对读.html'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
COLORS = {
    'scout': ('#215d83', '#edf4f7', '自行侦探'),
    'capture': ('#965513', '#fff4df', '纳贡塘附近被俘'),
    'escort': ('#694e85', '#f3eff7', '押送至恩达'),
    'return': ('#346d58', '#edf5ef', '获释返程'),
    'maponly': ('#657269', '#f0f1ec', '仅据书图'),
}
IDS = ['chamdo', 'xizangqiao', 'eluoqiao', 'jialingtang', 'langdanggou',
       'nagongshan', 'nagongtang', 'jiamuqiao', 'suoluoba', 'riyuwa', 'enda']
PHASES = ['scout']*6 + ['capture'] + ['escort']*4
BRIEF = {
    'chamdo': '出发地；第三日午夜返抵。',
    'xizangqiao': '正文、书图均另列；与俄洛桥的称名关系未定。',
    'eluoqiao': '首晚留宿边军哨营；次晨再行。',
    'jialingtang': '仅据书图；“令”字识读仍待复核。',
    'langdanggou': '原书“腊左塘”；次晨经过塘房。',
    'nagongshan': '翻山进入另一谷地；具体山口未定位。',
    'nagongtang': '原书“腊左”；投宿后遭俘。',
    'jiamuqiao': '原书“并达桥”；被俘后押送途中经过。',
    'suoluoba': '原书“林多坝”；夜半到达，天明后再行。',
    'riyuwa': '仅据书图；地名识读及今地对应待核。',
    'enda': '本人实际到达；第三日约10时抵、13时启返。',
}


def load():
    scan = json.loads((DATA/'书图识读.json').read_text())
    text = json.loads((DATA/'探险文字核对.json').read_text())
    nodes = scan['photo2_main_sequence_from_chamdo']
    assert len(nodes) == len(IDS) == 11
    canonical_file = DATA/'校注十一地图核对.json'
    if canonical_file.exists():
        assert json.loads(canonical_file.read_text())['main_sequence'] == IDS
    for item, key, phase in zip(nodes, IDS, PHASES):
        item['id'] = key
        item['phase'] = phase
        item['brief'] = BRIEF[key]
        item['map_only'] = key in ['jialingtang', 'riyuwa']
    return scan, text, nodes


def wrap(value, limit):
    """Wrap CJK and Latin without assuming that stored characters have equal width."""
    result, line, width = [], '', 0
    for char in value:
        unit = 2 if unicodedata.east_asian_width(char) in 'WF' else 1
        if char == '\n' or width+unit > limit:
            result.append(line)
            line, width = '', 0
            if char == '\n':
                continue
        line += char
        width += unit
    if line:
        result.append(line)
    return result


def node(parent, tag, attrs=None, text=None):
    el = ET.SubElement(parent, f'{{{NS}}}{tag}', attrs or {})
    if text is not None:
        el.text = str(text)
    return el


def svg_text(parent, x, y, value, size=24, color='#26332f', weight='400', limit=None, line_height=None):
    el = node(parent, 'text', {'x': str(x), 'y': str(y), 'font-size': str(size), 'fill': color,
                             'font-weight': weight})
    lines = wrap(value, limit) if limit else [value]
    for index, line in enumerate(lines):
        node(el, 'tspan', {'x': str(x), 'dy': '0' if index == 0 else str(line_height or size*1.48)}, line)
    return y+(len(lines)-1)*(line_height or size*1.48)+size*.4


def panel(parent, y, title, paragraphs, color='#26332f', fill='#fffef9'):
    x, width = 850, 474
    rendered = [wrap(p, 34) for p in paragraphs]
    height = 82 + sum(len(lines)*33+21 for lines in rendered)
    node(parent, 'rect', {'x': str(x), 'y': str(y), 'width': str(width), 'height': str(height),
                          'rx': '14', 'fill': fill, 'stroke': '#d7dbd3', 'stroke-width': '1.4'})
    svg_text(parent, x+26, y+44, title, 27, color, '650')
    cursor = y+88
    for lines in rendered:
        for line in lines:
            svg_text(parent, x+26, cursor, line, 22, '#3e4a45')
            cursor += 33
        cursor += 21
    return y+height+24


def build_svg(scan, text, nodes):
    root = ET.Element(f'{{{NS}}}svg', {'width': '1400', 'height': '2640', 'viewBox': '0 0 1400 2640',
                                    'role': 'img', 'aria-labelledby': 'figure-title figure-desc'})
    node(root, 'title', {'id': 'figure-title'}, '昌都至恩达：校注十一地名顺序与探险经过')
    node(root, 'desc', {'id': 'figure-desc'}, '纵向十一节点示意，无比例尺、无经纬度。蓝色为自行侦探，橙色为纳贡塘附近被俘，紫色为押送至恩达。另列获释返程、里数差异和书图限制。')
    defs = node(root, 'defs')
    style = node(defs, 'style')
    style.text = 'text{font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif}a:focus rect{stroke:#142b40;stroke-width:4}'
    for key, (color, _, _) in COLORS.items():
        marker = node(defs, 'marker', {'id': 'arrow-'+key, 'viewBox': '0 0 10 10', 'refX': '5', 'refY': '5',
                                      'markerWidth': '7', 'markerHeight': '7', 'orient': 'auto-start-reverse'})
        node(marker, 'path', {'d': 'M 0 0 L 10 5 L 0 10 z', 'fill': color})
    node(root, 'rect', {'width': '1400', 'height': '2640', 'fill': '#f5f3ed'})
    svg_text(root, 76, 94, '昌都—恩达：探险、被俘与押送', 43, '#26332f', '700')
    svg_text(root, 78, 146, '按正文与校注十一订正地名；陈渠珍实际抵达恩达，后获释返回昌都。', 26)
    svg_text(root, 78, 189, '顺序示意  ·  无比例尺  ·  无经纬度  ·  原述里数不换算 km', 25, '#6d5743', '600')
    cursor = 78
    for key in ['scout', 'capture', 'escort', 'return']:
        color, fill, label = COLORS[key]
        node(root, 'rect', {'x': str(cursor), 'y': '222', 'width': '20', 'height': '20', 'rx': '4', 'fill': color})
        svg_text(root, cursor+31, 240, label, 21, color, '600')
        cursor += 300 if key == 'capture' else 260
    node(root, 'rect', {'x': str(cursor), 'y': '222', 'width': '20', 'height': '20', 'rx': '4', 'fill': '#657269'})
    svg_text(root, cursor+31, 240, '仅据书图', 21, '#657269', '600')
    start_y, step, card_h = 294, 198, 148
    for index, item in enumerate(nodes):
        x, y, width = 76, start_y+index*step, 704
        color, fill, phase = COLORS[item['phase']]
        if item['map_only']:
            color, fill = '#657269', '#f0f1ec'
        if index:
            node(root, 'path', {'d': f'M 428 {y-step+card_h+4} V {y-16}', 'stroke': color,
                               'stroke-width': '3', 'fill': 'none', 'marker-end': 'url(#arrow-'+('maponly' if item['map_only'] else item['phase'])+')'})
        link = node(root, 'a', {'href': HTML_NAME+'#detail-'+item['id'], 'aria-label': '查看'+item['name']+'明细'})
        node(link, 'rect', {'x': str(x), 'y': str(y), 'width': str(width), 'height': str(card_h),
                           'rx': '15', 'fill': fill, 'stroke': color, 'stroke-width': '1.8'})
        svg_text(link, x+24, y+42, f'{index+1:02d}  '+item['name'], 31, color, '700')
        tag = '仅据书图' if item['map_only'] else phase
        svg_text(link, x+width-190, y+40, tag, 20, color, '600')
        aliases = '／'.join(a['name'] for a in item.get('aliases', []) if a['name'] != '伴达桥')
        if item['id'] == 'nagongshan': aliases='腊左大山；藏名安初拉〔识读中高〕'
        alias_line = '别名：'+aliases if aliases else '识读：'+item['confidence']
        svg_text(link, x+25, y+83, alias_line, 22, '#44524b')
        svg_text(link, x+25, y+122, item['brief'], 22, '#26332f')
    side_y = 294
    side_y = panel(root, side_y, '先看这条时间线', [
        '首晚：俄洛桥边军哨营留宿。',
        '第二夜：纳贡塘遭俘，押经甲木桥，夜半到梭罗坝并短暂休息。',
        '第三日：约10时到恩达；约13时启返；午夜回到昌都。',
        '往返约3日、2夜，是相对分日推算；原书未自计全程三日。'], '#215d83', '#edf4f7')
    side_y = panel(root, side_y, '到恩达之后：获释返程', [
        '正文返程明确复经纳贡塘、纳贡山、浪荡沟、俄洛桥，至昌都。',
        '返程没有逐名重述梭罗坝、甲木桥；不把同路可能性写成逐站已证实。'], '#346d58', '#edf5ef')
    side_y = panel(root, side_y, '两座图上桥名，保留差异', [
        '书图把近城西藏桥与较西的俄洛桥分列。校注却称俄洛桥番名西藏桥。',
        '这里只保留称名矛盾，不确定它们是同一古桥或两座不同古桥。'], '#6d5743', '#fff6e7')
    side_y = panel(root, side_y, '原述里数：组合段不拆分', [
        '恩达→梭罗坝：十余里；再至甲木桥：数里；再至纳贡塘：十里。',
        '纳贡塘翻山至浪荡沟：约四十里；浪荡沟经俄洛桥至昌都：六十里。',
        '这些是校注原述；正文另有异说，详见对读页。旧作两站，不等于两日。'], '#694e85', '#f3eff7')
    side_y = panel(root, side_y, '旁注地点，不强插主链', [
        '果角塘：浪荡沟至纳贡山之间的谷地标签，是否为停驻节点未明。',
        '陈渠珍被擒处：纳贡塘附近事件位置，营房／民居确址未定。',
        '云南桥：图中位于昌都南侧，另属澜沧江方向。',
        '瓦合大山：校注背景，不据此认定此行另翻该山。'], '#44524b', '#fffef9')
    assert side_y < 2510, f'Right notes exceed reserved bounds: {side_y}'
    node(root, 'line', {'x1':'76','y1':'2518','x2':'1324','y2':'2518','stroke':'#c9cfc5'})
    svg_text(root, 78, 2562, '依据：用户书影、第二章正文与任乃强校注十一。甲令塘、日雨娃等保留识读置信度。', 22, '#4c5b53')
    svg_text(root, 78, 2601, '本图只表达文字顺序和叙事阶段，不是古道轨迹、导航图或可量取距离的地理图。', 22, '#4c5b53')
    return ET.tostring(root, encoding='unicode', xml_declaration=False)


def esc(value):
    return html.escape(str(value), quote=True)


def build_html(scan, text, nodes, svg):
    by_id = {n['id']: n['name'] for n in nodes}
    def place(key):
        value = key or '未指定单点'
        for place_id in sorted(by_id, key=len, reverse=True):
            value = value.replace(place_id, by_id[place_id])
        return value
    outline, details = [], []
    for index, item in enumerate(nodes):
        color, fill, phase = COLORS[item['phase']]
        if item['map_only']:
            color, fill, phase = '#657269', '#f0f1ec', '仅据书图；经过细节未记'
        map_tag = ' <span class="map-tag">仅据书图</span>' if item['map_only'] else ''
        outline.append(f'<li style="--phase:{color};--tint:{fill}"><a href="#detail-{item["id"]}"><span class="order">{index+1:02d}</span><span><strong>{esc(item["name"])}</strong>{map_tag}<small>{esc(item["brief"])}</small></span><span aria-hidden="true">↘</span></a></li>')
        aliases = ''.join(f'<li>{esc(a["name"])} <span class="muted">{esc(a["source"])}；{esc(a["confidence"])}</span></li>' for a in item.get('aliases', []))
        chronological = [c for c in text['chronology'] if item['id'] in [c.get('from'), c.get('to'), *c.get('via', [])]]
        events = ''.join(f'<li><b>{esc(c["relative_day"])} · {esc(c["phase"])}</b><p>{esc(c["event"])}</p><small>{esc(c["evidence_status"])}</small></li>' for c in chronological)
        distances = [d for d in text['distance_claims'] if item['id'] in [d.get('from'), d.get('to'), *d.get('via', [])]]
        distance_rows = ''.join(f'<tr><td>{esc(d["source"])}</td><td>{esc(place(d["from"]))} → {esc(place(d["to"]))}</td><td>{esc(d["original_li"])}</td><td>{esc(d["note"])}</td></tr>' for d in distances)
        timing_rows = [t for t in text['timing_claims'] if t.get('place') == item['id']]
        timings = ''.join(f'<li><b>{esc(t["time"])}〔{esc(t["status"])}〕</b><p>{esc(t["basis"])}</p></li>' for t in timing_rows)
        details.append(f'''<details class="node-detail" id="detail-{item['id']}" style="--phase:{color};--tint:{fill}">
<summary><span class="order">{index+1:02d}</span><span>{esc(item['name'])}{map_tag}<small>{esc(phase)} · 识读置信度：{esc(item['confidence'])}</small></span></summary>
<div class="detail-body"><p class="lead">{esc(item['note'])}</p>
{('<h4>名称对读</h4><ul>'+aliases+'</ul>') if aliases else ''}
{('<h4>正文经过与事件</h4><ol class="event-list">'+events+'</ol>') if events else '<p class="notice">仅据书图补充此名；正文未逐站叙述此处，不能为它增造停驻日期、经过事件或坐标。</p>'}
{('<h4>已知时刻与停驻</h4><ul>'+timings+'</ul>') if timings else ''}
{('<h4>原述里数</h4><div class="table-scroll"><table><thead><tr><th>来源</th><th>段落</th><th>原述</th><th>限制</th></tr></thead><tbody>'+distance_rows+'</tbody></table></div>') if distance_rows else '<p class="muted">没有可独立分配到此点的原述里数；不按图距或相邻段分摊。</p>'}
<p class="precision">无经纬度。此条目的顺序／别名不能直接证明现代点位。</p><a class="back" href="#route">回到节点目录 ↑</a></div></details>''')
    timing = ''.join(f'<li><b>{esc(t["time"] or t.get("original_post_stages", "未给日数"))}</b><span>{esc(t["status"])}</span><p>{esc(t["basis"])}</p></li>' for t in text['timing_claims'])
    distance_table = ''.join(f'<tr><td>{esc(d["source"])}</td><td>{esc(place(d["from"]))} → {esc(place(d["to"]))}'+('（经'+esc('、'.join(place(p) for p in d['via']))+'）' if d.get('via') else '')+f'</td><td>{esc(d["original_li"])}</td><td>{esc(d["note"])}</td></tr>' for d in text['distance_claims'])
    extras = ''.join(f'<article><h3>{esc(p["name"])}</h3><p>{esc(p["relative_position"])}</p><p>{esc(p["note"])}</p><small>识读置信度：{esc(p["confidence"])}</small></article>' for p in scan['photo2_additional_features'])
    conflicts = ''.join(f'<article><h3>{esc(c["topic"])}</h3><p><b>文字：</b>{esc(c["text"])}</p><p><b>书图：</b>{esc(c["map"])}</p><p class="notice">{esc(c["handling"])}</p></article>' for c in scan['text_map_discrepancies'])
    rivers = ''.join(f'<li><b>{esc(r["name"])}'+('（'+esc(r['alias'])+'）' if r.get('alias') else '')+f'</b>：{esc(r["relative_position"])} {esc(r["label_detail"])} <small>识读：{esc(r["confidence"])}</small></li>' for r in scan['photo2_rivers'])
    sources = ''.join(f'<li><a href="{esc(s["url"])}">{esc(s["title"])}</a></li>' for s in text['sources'])
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>昌都—恩达｜校注十一对读</title>
<style>
:root{color-scheme:light;--ink:#26332f;--muted:#65716a;--paper:#f5f3ed;--line:#d7dbd3;--accent:#215d83}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:22px}body{margin:0;background:var(--paper);color:var(--ink);font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.75}a{color:#19577d;text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #bf721f;outline-offset:5px}header,main,footer{max-width:1240px;margin:auto;padding:32px 30px}header{padding-top:55px}.eyebrow{font-size:14px;letter-spacing:.13em;color:var(--muted)}h1{font-size:clamp(29px,4.2vw,48px);line-height:1.22;margin:16px 0}h2{font-size:27px;line-height:1.4;margin:0 0 18px}h3{font-size:19px;margin:0 0 12px}h4{font-size:17px;margin:22px 0 9px}p{margin:.6em 0}strong,b{font-weight:650}.intro{max-width:880px;font-size:18px}.warning{display:inline-block;background:#fff2d9;border-left:4px solid #965513;padding:12px 18px;margin:18px 0}.toolbar,.jump{display:flex;flex-wrap:wrap;gap:9px;margin:18px 0}.toolbar a,.jump a{border:1px solid #b9c4bc;border-radius:8px;padding:9px 13px;min-height:44px;background:#fffef9;text-decoration:none;font-size:15px}.legend{display:flex;flex-wrap:wrap;gap:14px 24px;margin:24px 0}.legend span{display:flex;align-items:center;gap:9px}.swatch{height:14px;width:14px;border-radius:4px;background:var(--phase)}.layout{display:grid;grid-template-columns:340px minmax(0,1fr);gap:32px;align-items:start}.outline{position:sticky;top:18px}.route{padding:0;margin:0;list-style:none}.route li{position:relative;margin-bottom:15px}.route li:not(:last-child):after{content:"↓";position:absolute;bottom:-20px;left:29px;font-size:18px;color:#69746e}.route a{display:flex;align-items:start;gap:12px;border:1px solid #c3d0c6;border-left:4px solid var(--phase);border-radius:9px;padding:13px 14px;background:var(--tint);text-decoration:none;color:var(--ink);min-height:66px}.route small{display:block;color:#58665e;line-height:1.5;margin-top:3px;font-size:12px}.route strong{font-size:16px}.order{color:var(--phase);font-size:15px;font-variant-numeric:tabular-nums;white-space:nowrap}.route a>span:nth-child(2){flex:1}.map-tag{display:inline-block;border:1px solid #b7b2a4;border-radius:4px;background:#f2eee3;padding:0 5px;margin-left:6px;color:#655d4b;font-size:12px;white-space:nowrap}.node-detail{border:1px solid var(--line);border-left:4px solid var(--phase);border-radius:10px;background:#fffef9;margin:0 0 17px;overflow:hidden;scroll-margin-top:20px}.node-detail summary{cursor:pointer;display:flex;align-items:center;gap:17px;min-height:76px;padding:16px 21px;font-size:21px;font-weight:650;list-style:none}.node-detail summary:after{content:"＋";margin-left:auto;color:var(--phase);font-size:24px}.node-detail[open] summary:after{content:"−"}.node-detail summary small{display:block;font-size:12px;font-weight:400;color:var(--muted);margin-top:3px}.node-detail[open] summary{background:var(--tint);border-bottom:1px solid var(--line)}.detail-body{padding:18px 24px 24px;font-size:15px}.detail-body ul,.detail-body ol{padding-left:22px}.event-list>li{padding-bottom:15px}.event-list p{margin:.3em 0}.muted,small{color:var(--muted)}small{font-size:12px}.notice{padding:12px 15px;background:#f7f2e7;border-left:3px solid #aa874d}.precision{font-size:13px;color:#626e66;border-top:1px solid var(--line);padding-top:14px;margin-top:20px}.back{font-size:13px}.section{padding-top:48px;margin-top:15px;border-top:1px solid var(--line)}.section>p{max-width:880px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:19px}.cards article{padding:24px;background:#fffef9;border:1px solid var(--line);border-radius:11px}.timing-grid{list-style:none;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.timing-grid li{padding:20px;background:#fffef9;border:1px solid var(--line);border-radius:10px}.timing-grid b{display:block;font-size:21px}.timing-grid span{display:inline-block;font-size:12px;margin:6px 0;color:#6b5b41}.timing-grid p{font-size:14px}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;background:#fffef9}td,th{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{background:#e9eee7;white-space:nowrap}td:nth-child(3){white-space:nowrap;font-weight:650}.image-card{padding:20px;background:#fffef9;border:1px solid var(--line);border-radius:11px;margin:20px 0}.image-card img{display:block;width:100%;height:auto}.rotated-frame{position:relative;aspect-ratio:913/571;background:#fff;overflow:hidden}.rotated-frame img{position:absolute;width:62.541%;max-width:none;left:50%;top:50%;transform:translate(-50%,-50%) rotate(90deg)}figcaption{font-size:13px;color:var(--muted);margin-top:13px}.overview>summary{cursor:pointer;min-height:48px;font-size:17px;font-weight:650}.overview-frame{overflow:auto;max-height:1100px;border:1px solid var(--line);margin:16px 0}.overview-frame svg{display:block;width:100%;height:auto;min-width:840px}footer{font-size:13px;color:var(--muted);padding-bottom:50px}.screenreader{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
@media(max-width:850px){header,main,footer{padding-left:20px;padding-right:20px}.layout{grid-template-columns:1fr;gap:32px}.outline{position:static}.route{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.route li{margin:0}.route li:not(:last-child):after{display:none}.route a{height:100%;padding:13px 10px;gap:8px}.route a>span:last-child{display:none}.route small{font-size:11px}.cards{grid-template-columns:1fr}.timing-grid{grid-template-columns:1fr}.intro{font-size:16px}.detail-body{padding:17px}.node-detail summary{font-size:20px;padding:15px}.section{padding-top:33px}.image-card{padding:10px}}
@media(max-width:420px){.route{grid-template-columns:1fr}.route small{font-size:12px}.route a{min-height:67px}.legend{gap:8px 16px;font-size:13px}.toolbar a,.jump a{font-size:13px;padding:9px 11px}h2{font-size:24px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{.toolbar,.jump,.back{display:none}.layout{display:block}.outline{position:static}.node-detail{break-inside:avoid}.node-detail>.detail-body{display:block}.section{break-before:auto}.image-card{break-inside:avoid}}
</style></head><body><header><div class="eyebrow">《艽野尘梦》第二章 · 校注十一 · 2026-10-31</div><h1>昌都—恩达：把旧名、书图与经历对起来</h1><p class="intro">陈渠珍由昌都出发侦探，在纳贡塘附近被俘，后被带到恩达，与堪布交涉后获释，返抵昌都。下面把十一处主链地名与正文分日、原述里数并列，避免把地名订正误当作已经定位的古道。</p><p class="warning"><b>顺序示意，无比例尺、无经纬度。</b>原述“里”保留原样，不换算 km；图上的地名顺序不能直接证明现代点位。</p><div class="toolbar"><a href="'''+esc(SVG_NAME)+'''">打开完整 SVG 顺序图</a><a href="data/annotation11/书图识读.json">书图识读数据</a><a href="data/annotation11/探险文字核对.json">正文核对数据</a></div><nav class="jump" aria-label="页内目录"><a href="#route">地点顺序</a><a href="#time">耗时与时刻</a><a href="#distances">原述里数</a><a href="#differences">图文差异</a><a href="#scans">原书图</a></nav><div class="legend">'''+''.join(f'<span><i class="swatch" style="--phase:{v[0]}"></i>{v[2]}</span>' for v in COLORS.values())+'''</div></header><main>
<div class="layout"><nav class="outline" id="route" aria-label="十一处地点顺序"><h2>地点顺序</h2><p class="muted">点击地点展开对应明细；编号只表达顺序。</p><ol class="route">'''+''.join(outline)+'''</ol></nav><section aria-label="节点明细"><h2>逐点对读</h2>'''+''.join(details)+'''</section></div>
<section class="section" id="time"><h2>约三日、两夜：推算与明记分开</h2><p>首晚俄洛桥留宿，第二夜被俘后至梭罗坝，第三日上午到恩达并在同日午夜返抵昌都。约3日、2夜来自这些相对分日，不能与堪布承诺的“三日撤兵”、校注十“卡工以西野宿三日”混为一项。</p><ol class="timing-grid">'''+timing+'''</ol></section>
<section class="section" id="distances"><h2>原述里数：保留范围与异说</h2><p>下表来源不同的约数分别保留，不取平均、不用固定现代里制换算，也不据这些里数给未知地名插值坐标。现代已核实代表点直距属于另一口径。</p><div class="table-scroll"><table><thead><tr><th>来源</th><th>原述段落</th><th>里数</th><th>说明</th></tr></thead><tbody>'''+distance_table+'''</tbody></table></div></section>
<section class="section" id="differences"><h2>书图与文字的差异</h2><div class="cards">'''+conflicts+'''</div></section>
<section class="section" id="extras"><h2>旁注地点与河名</h2><p>以下地点参与理解相对地形或事件背景，未被强插为主链中的独立停驻站。</p><div class="cards">'''+extras+'''</div><h3 style="margin-top:27px">河名识读</h3><ul>'''+rivers+'''</ul></section>
<section class="section" id="figure"><h2>完整顺序图</h2><details class="overview"><summary>展开 SVG 全图（可横向滚动；点击节点进入明细）</summary><div class="overview-frame">'''+svg.replace('href="'+HTML_NAME+'#', 'href="#')+'''</div></details></section>
<section class="section" id="scans"><h2>回看两张原书图</h2><p>原始书影保持不变。第二张仅通过页面样式旋转以便阅读；它们不是可量距或配准的地理底图。</p><figure class="image-card"><h3>照片2：昌都至恩达略图</h3><div class="rotated-frame"><img src="data/annotation11/scans/昌都恩达略图.jpg" alt="用户提供的昌都至恩达略图，按阅读方向转正。标示西藏桥、俄洛桥、浪荡沟、纳贡山、纳贡塘、甲木桥、梭罗坝及恩达等地名。"></div><figcaption>书图的西藏桥与俄洛桥是两个标位；主名和括注应与上面的差异记录一起读。</figcaption></figure><figure class="image-card"><h3>照片1：陈渠珍出藏路线图</h3><img loading="lazy" src="data/annotation11/scans/出藏路线图.jpg" alt="用户提供的陈渠珍出藏路线图，含旧西康省、青海省及甘肃省等区域标签，表示北返背景。"><figcaption>这张是出藏／北返全局背景图，不用来给昌都—恩达细部赋坐标，也不直接倒套现代省界。</figcaption></figure></section>
<section class="section" id="sources"><h2>依据与边界</h2><ul>'''+sources+'''<li>用户提供的校注十一及两张书影；图中字形未读清处保留置信度，不自行改定。</li></ul><p>已核实的现代地区参照点仍需在阅读地图中与旧桥、旧营地、被擒处等未定位条目分开。没有新增古道轨迹或虚构逐站耗时。</p></section></main><footer>文字与图片来源分项记录在 data/annotation11。此页的节点目录使用 URL 片段保留位置；不向外发送数据，不使用外部字体、地图或脚本。</footer>
<script>
(function(){function reveal(){var id=decodeURIComponent(location.hash.slice(1));var el=document.getElementById(id);if(el&&el.tagName==='DETAILS')el.open=true;}window.addEventListener('hashchange',reveal);document.addEventListener('click',function(event){var a=event.target.closest('a[href^="#detail-"]');if(a){var el=document.getElementById(a.hash.slice(1));if(el)el.open=true;}});reveal();})();
</script></body></html>'''


def write_figure():
    scan, text, nodes = load()
    svg = build_svg(scan, text, nodes)
    ET.fromstring(svg)
    (ROOT/SVG_NAME).write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+svg+'\n', encoding='utf-8')
    (ROOT/HTML_NAME).write_text(build_html(scan, text, nodes, svg), encoding='utf-8')
    return [ROOT/SVG_NAME, ROOT/HTML_NAME]


if __name__ == '__main__':
    for path in write_figure():
        print(path)
