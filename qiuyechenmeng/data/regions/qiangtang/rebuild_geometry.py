import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description='Reassemble the cached OSM relation without simplifying its geometry.')
parser.add_argument('--allow-spherical', action='store_true',
                    help='Allow explicitly preliminary spherical area and built-in checks when optional geometry packages are missing.')
args = parser.parse_args()
RAW = ROOT / 'raw_osm_relation_8590456_full.json'
doc = json.loads(RAW.read_text())
nodes = {e['id']: e for e in doc['elements'] if e['type'] == 'node'}
ways = {e['id']: e for e in doc['elements'] if e['type'] == 'way'}
rel = next(e for e in doc['elements'] if e['type'] == 'relation' and e['id'] == 8590456)
assert rel['version'] == 10
assert all(m['type'] == 'way' and m['role'] == 'outer' for m in rel['members'])
remaining = [(m['ref'], ways[m['ref']]['nodes'][:]) for m in rel['members']]
degrees = collections.Counter(n for _, seq in remaining for n in (seq[0], seq[-1]))
assert set(degrees.values()) == {2}
rings, way_orders = [], []
while remaining:
    wid, ring = remaining.pop()
    order = [wid]
    while ring[-1] != ring[0]:
        matches = [(i, seq if seq[0] == ring[-1] else list(reversed(seq)))
                   for i, (_, seq) in enumerate(remaining)
                   if ring[-1] in (seq[0], seq[-1])]
        assert len(matches) == 1, (ring[-1], len(matches))
        i, seq = matches[0]
        wid, _ = remaining.pop(i)
        order.append(wid)
        ring.extend(seq[1:])
    coords = [[nodes[n]['lon'], nodes[n]['lat']] for n in ring]
    assert all(a != b for a, b in zip(coords, coords[1:]))
    signed = sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(coords, coords[1:]))
    if signed < 0:
        coords.reverse()
    rings.append(coords)
    way_orders.append(order)
assert len(rings) == 1
ring = rings[0]

# Scan-line midpoint supplies an interior label position without assuming that
# the bounding-box midpoint lies in a concave polygon.
latitude = (min(x[1] for x in ring) + max(x[1] for x in ring)) / 2
xs = sorted(a[0] + (latitude-a[1])*(b[0]-a[0])/(b[1]-a[1])
            for a, b in zip(ring, ring[1:])
            if (a[1] <= latitude < b[1]) or (b[1] <= latitude < a[1]))
assert len(xs) % 2 == 0
left, right = max(zip(xs[::2], xs[1::2]), key=lambda pair: pair[1]-pair[0])
label = [(left+right)/2, latitude]

spherical_area = abs(sum(math.radians(b[0]-a[0]) *
                      (2+math.sin(math.radians(a[1]))+math.sin(math.radians(b[1])))
                      for a, b in zip(ring, ring[1:]))) * 6371008.8**2 / 2 / 1e6
area = spherical_area
area_method = 'Spherical surface area, mean Earth radius 6371008.8 m; preliminary'
validation = {'closed': True, 'outer_orientation': 'counterclockwise',
              'endpoint_degree': 2, 'no_consecutive_duplicate_coordinates': True}
try:
    import shapely
    from shapely.geometry import Polygon, Point
    from shapely.validation import explain_validity
    polygon = Polygon(ring)
    assert polygon.is_valid, explain_validity(polygon)
    assert polygon.contains(Point(label))
    validation.update({'shapely_version': shapely.__version__,
                       'shapely_is_valid': polygon.is_valid,
                       'shapely_validity_reason': explain_validity(polygon),
                       'label_point_strictly_inside': True})
except ImportError:
    pass
try:
    import pyproj
    geod = pyproj.Geod(ellps='WGS84')
    signed_area, perimeter = geod.polygon_area_perimeter(
        [c[0] for c in ring], [c[1] for c in ring])
    area = abs(signed_area) / 1e6
    area_method = 'pyproj.Geod.polygon_area_perimeter; WGS84 ellipsoid; geodesic segments'
    validation.update({'pyproj_version': pyproj.__version__, 'perimeter_km': perimeter/1000})
except ImportError:
    pass

if not args.allow_spherical and ('preliminary' in area_method or not validation.get('shapely_is_valid')):
    raise SystemExit('Final rebuild requires shapely and pyproj. Install them or explicitly request --allow-spherical for a preliminary result; no dataset has been overwritten.')

properties = {
    'name': rel['tags']['name'],
    'name:en': rel['tags']['name:en'],
    'display_label': '羌塘保护区公开地图轮廓〔现代范围参照〕',
    'source': 'OpenStreetMap contributors',
    'source_url': 'https://www.openstreetmap.org/relation/8590456',
    'source_api_url': 'https://www.openstreetmap.org/api/0.6/relation/8590456/full.json',
    'osm_relation_id': 8590456,
    'osm_relation_version': rel['version'],
    'osm_relation_timestamp': rel['timestamp'],
    'retrieved_on': '2026-11-01',
    'coordinate_reference': 'WGS84 longitude, latitude; OSM source coordinates',
    'boundary_role': 'Community-mapped protected-area outline for modern geographic reference',
    'not_official_demarcation': True,
    'not_an_uninhabited_area_boundary': True,
    'computed_area_km2': round(area, 3),
    'official_reported_area_km2': 298000,
    'difference_from_reported_area_percent': round((area-298000)/298000*100, 3),
    'area_method': area_method,
    'area_limit': 'Computed geometry area and official reported area are separate values; the outline is not resized to match the report.',
    'attribution': '© OpenStreetMap contributors',
    'license': 'ODbL-1.0',
    'license_url': 'https://www.openstreetmap.org/copyright',
}
feature = {'type': 'Feature', 'id': 'osm_relation_8590456', 'properties': properties,
           'geometry': {'type': 'Polygon', 'coordinates': rings}}
collection = {'type': 'FeatureCollection',
              'name': 'Qiangtang reserve community outline, not official demarcation',
              'attribution': properties['attribution'], 'license': 'ODbL-1.0',
              'features': [feature]}
out = ROOT / 'derived_osm_8590456.geojson'
out.write_text(json.dumps(collection, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
manifest = {
    'retrieved_on': '2026-11-01',
    'source_url': properties['source_url'], 'source_api_url': properties['source_api_url'],
    'raw_file': RAW.name, 'raw_sha256': hashlib.sha256(RAW.read_bytes()).hexdigest(),
    'raw_preservation': 'Original full API response bytes retained, including public OSM element attribution metadata.',
    'derived_file': out.name, 'derived_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'relation_id': 8590456, 'relation_version': rel['version'],
    'relation_timestamp': rel['timestamp'],
    'latest_element_timestamp': max(e['timestamp'] for e in doc['elements']),
    'source_crs': 'OSM WGS84 longitude, latitude', 'output_crs': 'RFC 7946 WGS84 longitude, latitude',
    'coordinate_transform': 'None',
    'assembly_method': 'Join relation outer ways by matching terminal node IDs; reverse individual way traversal as needed, then reverse completed ring to counterclockwise orientation.',
    'all_member_ways_used_once': True, 'outer_way_count': len(rel['members']),
    'outer_ring_count': len(rings), 'inner_ring_count': 0,
    'ring_coordinate_count_including_closure': len(ring),
    'simplification': 'None; every source boundary coordinate retained. Repeated way-junction node occurrences merged.',
    'closed_way_order': way_orders,
    'bounds_west_south_east_north': [min(c[0] for c in ring), min(c[1] for c in ring),
                                    max(c[0] for c in ring), max(c[1] for c in ring)],
    'label_position': label, 'label_role': 'Strictly interior display label; not a locality, station or historical event coordinate',
    'spherical_area_km2': spherical_area, 'computed_area_km2': area, 'area_method': area_method,
    'official_reported_area_km2': 298000,
    'official_area_source': 'https://xsbgs.al.gov.cn/info/1008/51091.htm',
    'area_difference_km2': area-298000,
    'area_difference_percent': (area-298000)/298000*100,
    'validation': validation,
    'source_license': 'ODbL-1.0', 'license_url': properties['license_url'],
    'attribution': properties['attribution'],
    'boundary_status': 'OSM community outline, not a verified current official demarcation or legally authoritative protected-area boundary.',
    'limitations': [
        'A recent relation timestamp is an OSM editing timestamp, not proof of official boundary currency.',
        'Official reported area 298000 km2 is not the computed area of this outline; neither value is altered to force agreement.',
        'The reserve footprint is not identical to a universally defined uninhabited-area boundary, to the broad Qiangtang Plateau, or to the historical Jiangtong region in the book.',
        'No official post-2018 demarcation-vector verification is asserted. No reserve core, buffer or experimental zones are inferred.',
        'This dataset is not a route, navigation corridor, administrative border or international boundary statement.'
    ]
}
(ROOT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'file': str(out), 'area_km2': area, 'method': area_method,
                  'difference_percent': manifest['area_difference_percent'],
                  'label': label, 'validation': validation}, ensure_ascii=False))
