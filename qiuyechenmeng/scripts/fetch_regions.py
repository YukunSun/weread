"""Cache DataV administrative polygons and an approximate WGS84 derivative.

These present-day administrative units are reference substrates, not verified
historical or cultural-region borders. Only the files in data/regions are edited.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'regions'
RAW = OUT / 'raw'
BASE = 'https://geo.datav.aliyun.com/areas_v3/bound/'
FILES = ['540000_full', '630000_full', '540000', '630000',
         '513300', '513200', '533400', '623000', '540400_full', '542522']
CRS_DOC = 'https://help.aliyun.com/en/datav/datav-7-0/user-guide/map-data-format-1'
API_DOC = 'https://help.aliyun.com/zh/datav/datav-6-0/user-guide/choropleth-layer-of-v3-x'


def forward_gcj(lon, lat):
    """Common approximate WGS84-to-GCJ02 offset model; not an official service."""
    if not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271):
        return lon, lat
    x, y = lon - 105.0, lat - 35.0
    dlat = -100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*math.sqrt(abs(x))
    dlat += (20*math.sin(6*x*math.pi) + 20*math.sin(2*x*math.pi))*2/3
    dlat += (20*math.sin(y*math.pi) + 40*math.sin(y*math.pi/3))*2/3
    dlat += (160*math.sin(y*math.pi/12) + 320*math.sin(y*math.pi/30))*2/3
    dlon = 300 + x + 2*y + .1*x*x + .1*x*y + .1*math.sqrt(abs(x))
    dlon += (20*math.sin(6*x*math.pi) + 20*math.sin(2*x*math.pi))*2/3
    dlon += (20*math.sin(x*math.pi) + 40*math.sin(x*math.pi/3))*2/3
    dlon += (150*math.sin(x*math.pi/12) + 300*math.sin(x*math.pi/30))*2/3
    rad = math.radians(lat)
    ellipsoid_a, eccentricity_sq = 6378245.0, 0.006693421622965943
    magic = 1 - eccentricity_sq*math.sin(rad)**2
    dlat = dlat*180 / ((ellipsoid_a*(1-eccentricity_sq)/(magic**1.5))*math.pi)
    dlon = dlon*180 / ((ellipsoid_a/math.sqrt(magic))*math.cos(rad)*math.pi)
    return lon+dlon, lat+dlat


def inverse_gcj(point):
    """Solve the forward model iteratively, retaining about 0.1 m precision."""
    lon, lat = point[:2]
    guess_lon, guess_lat = lon, lat
    for _ in range(10):
        actual_lon, actual_lat = forward_gcj(guess_lon, guess_lat)
        dx, dy = actual_lon-lon, actual_lat-lat
        guess_lon -= dx
        guess_lat -= dy
        if max(abs(dx), abs(dy)) < 1e-9:
            break
    return [round(guess_lon, 7), round(guess_lat, 7), *point[2:]]


def convert_coords(coords):
    if isinstance(coords[0], (float, int)):
        return inverse_gcj(coords)
    return [convert_coords(c) for c in coords]


def download(stem, refresh=False):
    url = BASE + stem + '.json'
    path = RAW / (stem + '.json')
    if refresh or not path.exists():
        temp = path.with_suffix('.download')
        subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                        '--max-time', '45', '--retry', '1', '--output', str(temp), url], check=True)
        json.loads(temp.read_text())
        temp.replace(path)
    body = path.read_bytes()
    doc = json.loads(body)
    print(stem, len(doc['features']), 'features', flush=True)
    return stem, url, path, body, doc


def all_points(coords):
    if isinstance(coords[0], (float, int)):
        yield coords
    else:
        for c in coords:
            yield from all_points(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true', help='Download again instead of using raw cache')
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda s: download(s, args.refresh), FILES))
    features, sources = [], []
    for stem, url, path, body, doc in results:
        sources.append({'file': str(path.relative_to(ROOT)), 'url': url,
                        'sha256': hashlib.sha256(body).hexdigest(),
                        'feature_count': len(doc['features'])})
        for original in doc['features']:
            # Gongbo is not all of today's Nyingchi. Keep only its three
            # core reference counties/districts from the provider snapshot.
            if stem == '540400_full' and original['properties']['adcode'] not in {540402, 540421, 540422, 540481}:
                continue
            feature = copy.deepcopy(original)
            properties = feature['properties']
            feature['id'] = str(properties['adcode'])
            properties['source_url'] = url
            properties['source_assumed_crs'] = 'GCJ-02; based on DataV documentation, raw file contains no CRS field'
            properties['coordinate_method'] = 'Approximate iterative GCJ-02 to WGS84 inverse; not official coordinate transformation'
            properties['use_limit'] = 'Present-day administrative reference only, not historical or cultural boundary'
            feature['geometry']['coordinates'] = convert_coords(feature['geometry']['coordinates'])
            for key in ['center', 'centroid']:
                if key in properties:
                    properties['source_'+key+'_gcj02'] = properties[key]
                    properties[key] = inverse_gcj(properties[key])
            features.append(feature)
    assert len(features) == len({f['id'] for f in features})
    for feature in features:
        assert feature['geometry']['type'] in ['Polygon', 'MultiPolygon']
        for point in all_points(feature['geometry']['coordinates']):
            assert 70 < point[0] < 115 and 20 < point[1] < 42
    now = datetime.now(timezone.utc).isoformat()
    result = {'type': 'FeatureCollection', 'name': 'Administrative references for Tibet regional reading map',
              'attribution': 'Administrative geometry © Alibaba Cloud DataV.GeoAtlas; individual data license not stated in inspected documentation',
              'retrieved_at_utc': now, 'coordinate_reference': 'Approximate WGS84 longitude, latitude',
              'features': features}
    (OUT/'admin_regions_wgs84.geojson').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n')
    manifest = {
        'retrieved_at_utc': now, 'provider': 'Alibaba Cloud DataV.GeoAtlas',
        'api_documentation': API_DOC, 'coordinate_documentation': CRS_DOC,
        'raw_crs_assumption': 'GCJ-02, inferred from provider documentation; raw GeoJSON does not declare CRS',
        'output_crs': 'Approximate WGS84 longitude, latitude',
        'conversion': 'Iterative inverse of a common approximate GCJ02 forward offset formula; 10 iteration limit and 1e-9 degree residual target, rounded to 7 decimals',
        'precision_limit': 'Numerical residual is not survey accuracy. Source boundaries are generalized; historical/cultural-region proxy error dominates and may be many kilometres.',
        'license_status': 'No explicit standalone redistribution license found in inspected provider pages. Retain provider attribution; do not label these data as CC0, ODbL or public domain.',
        'attribution': result['attribution'], 'administrative_version': 'Not specified by raw endpoint; retrieved snapshot is not guaranteed to reflect all 2026 changes',
        'feature_count': len(features), 'sources': sources,
        'limits': ['Administrative units are convenient modern reference extents, not reconstructed historical borders.',
                   'Ali, Qiangtang, Gongbo, Kham and Amdo are historical/cultural/natural geographical concepts whose limits do not generally follow whole modern prefectures.',
                   'No simplification or smoothing is applied here; only coordinate conversion. Source polygons may already be generalized.',
                   'Current international boundaries in these data may reflect the provider cartographic convention; no sovereignty inference is added.'],
    }
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print('Wrote', len(features), 'administrative-reference features', flush=True)


if __name__ == '__main__':
    main()
