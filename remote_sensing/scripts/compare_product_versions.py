"""Diagnostic of the 2015/2016 version boundary, not a causal version-effect estimate."""
import argparse,csv,json,hashlib,datetime
from pathlib import Path
import numpy as np,rasterio,shapefile
from rasterio.features import rasterize
from pyproj import CRS,Transformer
from shapely.geometry import shape,mapping
from shapely.ops import transform
p=argparse.ArgumentParser();p.add_argument('--rasters',required=True,type=Path);p.add_argument('--boundaries',required=True,type=Path);p.add_argument('--existing-outputs',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
years=[2012,2014,2015,2016,2017];versions={y:('v2.0.7cds' if y<=2015 else 'v2.1.1') for y in years};arrays={}
manifest=json.loads((a.rasters/'source_manifest.json').read_text())
for y in years:
 entry=next(e for e in manifest if e['year']==y)
 assert len(entry['items'])==2 and all(i['version']==versions[y] for i in entry['items'])
 with rasterio.open(a.rasters/f'landcover_{y}.tif') as f:
  assert f.shape==(4680,4680) and f.crs.to_epsg()==4326
  if y==years[0]:T=f.transform
  else:assert f.transform==T
  arrays[y]=f.read(1)
 entry['subset_sha256']=hashlib.sha256((a.rasters/f'landcover_{y}.tif').read_bytes()).hexdigest()
checks=json.loads((a.existing_outputs/'panel_checks.json').read_text());assert np.allclose(list(T),checks['transform'],atol=1e-10,rtol=0)
with (a.existing_outputs/'Cell_Area_By_Latitude.csv').open(encoding='utf-8-sig') as f:area_rows=list(csv.DictReader(f))
w=np.broadcast_to(np.array([float(r['cell_area_km2']) for r in area_rows])[:,None],(4680,4680))
assert max(abs(float(r['latitude_center'])-(T.f+(i+.5)*T.e)) for i,r in enumerate(area_rows))<1e-8
zones={};records={}
for kind,part in [('province','ProvCM01012026'),('region','Reg01012026')]:
 f=next(a.boundaries.rglob(part+'_WGS84.shp'));reader=shapefile.Reader(str(f),encoding='utf8');tr=Transformer.from_crs(CRS.from_wkt(f.with_suffix('.prj').read_text()),4326,always_xy=True);polys=[];records[kind]=[]
 for i,sr in enumerate(reader.iterShapeRecords(),1):
  records[kind].append(sr.record.as_dict());polys.append((mapping(transform(tr.transform,shape(sr.shape.__geo_interface__))),i))
 zones[kind]=rasterize(polys,out_shape=(4680,4680),transform=T,dtype='uint8',all_touched=False)
assert len(records['province'])==110 and len(records['region'])==20
assert np.array_equal(zones['province']>0,zones['region']>0)
valid=zones['province']>0
for im in arrays.values():assert np.count_nonzero(valid&(im==0))==0
assert abs(float(w[valid].sum())-checks['valid_area_km2'])<1e-6
rules={'strict_10_11_12_20':[10,11,12,20],'strict_plus_mosaic_30':[10,11,12,20,30],'strict_plus_mosaic_30_40':[10,11,12,20,30,40]}
def write(name,rows):
 with (a.out/name).open('w',newline='',encoding='utf-8-sig') as f:
  q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
def group(mask,z):
 keep=valid&mask;return np.bincount(z[keep],weights=w[keep],minlength=int(z.max())+1)[1:]
rows=[];national=[];snapshots=[];pairs=[(2012,2015),(2014,2015),(2015,2016),(2016,2017),(2012,2017)]
for rule,codes in rules.items():
 m={y:np.isin(im,codes) for y,im in arrays.items()}
 for y in years:
  total=float(w[valid&m[y]].sum());snapshots.append({'year':y,'class_definition':rule,'cropland_area_km2':total,'product_version':versions[y]})
 for y0,y1 in pairs:
  masks={'persistence':m[y0]&m[y1],'gain':~m[y0]&m[y1],'loss':m[y0]&~m[y1],'cropland_t0':m[y0],'cropland_t1':m[y1]}
  n={k:float(w[valid&v].sum()) for k,v in masks.items()};n['net_change']=n['gain']-n['loss'];assert abs(n['net_change']-(n['cropland_t1']-n['cropland_t0']))<1e-6
  national.append({'period_start':y0,'period_end':y1,'class_definition':rule,**n,'annualized_net_change_km2':n['net_change']/(y1-y0),'net_change_percent':100*n['net_change']/n['cropland_t0'],'product_version':f'{y0}:{versions[y0]};{y1}:{versions[y1]}'})
  if (y0,y1)!=(2015,2016):continue
  for kind,z in zones.items():
   vals={k:group(v,z) for k,v in masks.items()};vals['net_change']=vals['gain']-vals['loss']
   for k,v in vals.items():
    assert abs(float(v.sum())-n[k])<1e-6
    for i,value in enumerate(v):
     r=records[kind][i];rows.append({'geography_id':str(r['COD_PROV'] if kind=='province' else r['COD_REG']).zfill(3 if kind=='province' else 2),'geography_type':kind,'period_start':y0,'period_end':y1,'variable':k,'value':f'{value:.10f}','unit':'km2','source_product':'ESA CCI / Copernicus C3S land cover','product_version':f'{y0}:{versions[y0]};{y1}:{versions[y1]}','class_definition':rule,'quality_note':'Version-boundary diagnostic; fixed 2026 boundaries; no causal version-effect estimate or independent accuracy validation','region_id':str(r['COD_REG']).zfill(2)})
# Check archive 2012 and 2017 totals against the previously verified production panel.
with (a.existing_outputs/'Italy_National_Cropland_Seven_Years.csv').open(encoding='utf-8-sig') as f:old=list(csv.DictReader(f))
for r in snapshots:
 if r['year'] in [2012,2017]:
  q=next(v for v in old if int(v['year'])==r['year'] and v['class_definition']==r['class_definition']);assert abs(r['cropland_area_km2']-float(q['cropland_area_km2']))<1e-6
# Full class-to-class transition table for independent follow-up of suspicious conversions.
pair=arrays[2015].astype(np.int32)*256+arrays[2016];c=np.bincount(pair[valid],weights=w[valid],minlength=65536);trans=[{'class_2015':i//256,'class_2016':i%256,'area_km2':float(v),'unit':'km2'} for i,v in enumerate(c) if v>0]
write('version_boundary_geographic_changes.csv',rows);write('version_boundary_national_changes.csv',national);write('version_boundary_national_snapshots.csv',snapshots);write('version_boundary_class_transitions_2015_2016.csv',trans)
(a.out/'version_boundary_source_manifest.json').write_text(json.dumps(manifest,indent=2))
import importlib.metadata
(a.out/'version_boundary_software_versions.json').write_text(json.dumps({name:importlib.metadata.version(name) for name in ['numpy','rasterio','pyproj','pyshp','shapely']},indent=2))
(a.out/'version_boundary_checks.json').write_text(json.dumps({'accessed':datetime.date.today().isoformat(),'years':years,'geographic_rows':len(rows),'valid_area_km2':float(w[valid].sum()),'grid_matches_production':True,'2012_2017_national_totals_match_production':True,'no_missing_Italy_cells':True,'province_region_national_reconciliation':True,'limitations':'Time and product version are confounded. No same-year dual-version maps or independent reference labels are available; this is not an estimate of the causal version effect.'},indent=2))
print(json.dumps(national,indent=2))
