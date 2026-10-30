import argparse,csv,json
# Python dependencies: numpy xarray netCDF4 rasterio pyshp pyproj shapely
from pathlib import Path
import numpy as np,xarray as xr,shapefile
from pyproj import CRS,Transformer,Geod
from shapely.geometry import shape,mapping
from shapely.ops import transform
from rasterio.features import rasterize
from rasterio.transform import from_origin
parser=argparse.ArgumentParser()
parser.add_argument('--input-root',required=True,type=Path,help='Directory containing lc1992, lc2022, and bounds folders')
parser.add_argument('--output-dir',required=True,type=Path)
args=parser.parse_args(); P=args.input_root; OUT=args.output_dir; OUT.mkdir(parents=True,exist_ok=True)
n1=next((P/'lc1992').glob('*.nc'));n2=next((P/'lc2022').glob('*.nc'))
with xr.open_dataset(n1,mask_and_scale=False) as ds:a=ds.lccs_class.values.squeeze();lat=ds.lat.values;lon=ds.lon.values
with xr.open_dataset(n2,mask_and_scale=False) as ds:b=ds.lccs_class.values.squeeze();assert np.array_equal(lat,ds.lat.values) and np.array_equal(lon,ds.lon.values)
s=abs(float(lon[1]-lon[0])); assert lat[0]>lat[-1] and a.shape==b.shape
T=from_origin(lon.min()-s/2,lat.max()+s/2,s,s)
def read_boundaries(part):
 f=P/'bounds'/part/(part+'_WGS84.shp');r=shapefile.Reader(str(f),encoding='utf8')
 tr=Transformer.from_crs(CRS.from_wkt(f.with_suffix('.prj').read_text()),4326,always_xy=True)
 data=[];geoms=[]
 for k,sr in enumerate(r.iterShapeRecords(),1):
  data.append(sr.record.as_dict());geoms.append((mapping(transform(tr.transform,shape(sr.shape.__geo_interface__))),k))
 return data,rasterize(geoms,out_shape=a.shape,transform=T,dtype='uint8',all_touched=False)
prov,p=read_boundaries('ProvCM01012026');regs,r=read_boundaries('Reg01012026')
g=Geod(ellps='WGS84');row=np.array([abs(g.polygon_area_perimeter([0,s,s,0],[v-s/2,v-s/2,v+s/2,v+s/2])[0])/1e6 for v in lat]);w=np.broadcast_to(row[:,None],a.shape)
valid=(a>0)&(b>0);vp=(p>0)&valid;vr=(r>0)&valid
print('Boundary discrepancy pixels',np.count_nonzero((p>0)!=(r>0)),'provincecodes',len(prov))
# Reconcile both independently rasterized masks, including the known national benchmark.
area=lambda mask:float(w[mask].sum())
print('valid province area',area(vp),'region area',area(vr))
defs={'strict_10_11_12_20':[10,11,12,20],'strict_plus_mosaic_30':[10,11,12,20,30],'strict_plus_mosaic_30_40':[10,11,12,20,30,40]}
rows=[];summary=[];regional=[]
for name,codes in defs.items():
 ca=np.isin(a,codes);cb=np.isin(b,codes)
 tests={'persistence':ca&cb,'loss':ca&~cb,'gain':~ca&cb,'cropland_1992':ca,'cropland_2022':cb}
 for idx,pr in enumerate(prov,1):
  m=(p==idx)&valid
  vals={key:area(m&im) for key,im in tests.items()};vals['net_change']=vals['gain']-vals['loss']
  assert abs(vals['cropland_2022']-vals['cropland_1992']-vals['net_change'])<1e-7
  for metric,val in vals.items():
   rows.append({'geography_id':str(pr['COD_PROV']).zfill(3),'geography_type':'province','period_start':1992,'period_end':2022,'variable':metric,'value':f'{val:.10f}','unit':'km2','source_product':'ESA CCI and Copernicus C3S land cover','product_version':'1992:v2.0.7cds;2022:v2.1.1','class_definition':name,'quality_note':'1992 and 2022 endpoints; pixel-center inclusion; 2026 boundaries; no independent accuracy validation; area km2 = abs(WGS84 geodesic polygon area(lon=[0,s,s,0], lat=[c-s/2,c-s/2,c+s/2,c+s/2]))/1e6; s=1/360 degree, c=pixel latitude', 'region_id':str(pr['COD_REG']).zfill(2),'istat_uts_id':str(pr['COD_UTS']).zfill(3),'province_name':pr['DEN_UTS']})
 allvals={key:area(vp&im) for key,im in tests.items()};allvals['net_change']=allvals['gain']-allvals['loss'];summary.append({'class_definition':name,**allvals})
 for key in allvals:
  total=sum(float(row['value']) for row in rows if row['class_definition']==name and row['variable']==key)
  assert abs(total-allvals[key])<1e-5,(name,key,total,allvals[key])
 for idx,reg in enumerate(regs,1):
  regionmask=(r==idx)&valid
  for key,im in tests.items():
   regional.append((name,reg['COD_REG'],key,area(regionmask&im),sum(float(z['value']) for z in rows if z['class_definition']==name and z['variable']==key and z['region_id']==str(reg['COD_REG']).zfill(2))))
print(json.dumps(summary,indent=2))
print('max province-regional difference km2',max(abs(x[3]-x[4]) for x in regional))
assert abs(summary[0]['cropland_1992']-140149.33632058)<0.01
assert abs(summary[0]['cropland_2022']-139192.06590187)<0.01
outfile=OUT/'Italy_Province_Land_Cover_1992_2022.csv'
with outfile.open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
(OUT/'province_checks.json').write_text(json.dumps({'national':summary,'count_provinces':len(prov),'number_of_rows':len(rows),'province_region_mask_disagreement_pixels':int(np.count_nonzero((p>0)!=(r>0))),'max_regional_reconciliation_difference_km2':max(abs(x[3]-x[4]) for x in regional),'area_formula':'WGS84 ellipsoidal geodesic polygon area between longitude 0 and grid spacing and latitudes center +/- half grid spacing, divided by 1e6; constant across longitude in each row','grid_step_degrees':s},indent=2))
print('CSV',outfile,len(rows),'rows')
