"""Real 1992–2022 snapshot and interval panel on constant ISTAT 2026 geography."""
from pathlib import Path
import argparse,csv,json,hashlib
import numpy as np,xarray as xr,rasterio,shapefile
from rasterio.features import rasterize
from rasterio.transform import from_origin
from pyproj import Geod,CRS,Transformer
from shapely.geometry import shape,mapping
from shapely.ops import transform
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--input-root',type=Path,default=Path('province_work'));p.add_argument('--intermediate',type=Path,default=Path('revision_work/intermediate'));p.add_argument('--out',type=Path,default=Path('revision_work/panel'));args=p.parse_args();P=args.input_root;O=args.out;O.mkdir(exist_ok=True,parents=True)
arrays={};versions={1992:'v2.0.7cds',1997:'v2.0.7cds',2002:'v2.0.7cds',2007:'v2.0.7cds',2012:'v2.0.7cds',2017:'v2.1.1',2022:'v2.1.1'}
for y in [1992,2022]:
 with xr.open_dataset(next((P/f'lc{y}').glob('*.nc'))) as d:
  arrays[y]=d.lccs_class.values.squeeze()
  if y==1992:lat=d.lat.values;lon=d.lon.values
  else:assert np.array_equal(lat,d.lat.values) and np.array_equal(lon,d.lon.values)
s=abs(float(lon[1]-lon[0]));T=from_origin(lon.min()-s/2,lat.max()+s/2,s,s)
for y in [1997,2002,2007,2012,2017]:
 with rasterio.open(args.intermediate/f'landcover_{y}.tif') as f:
  assert f.shape==arrays[1992].shape and f.crs.to_epsg()==4326
  assert np.allclose(tuple(f.transform),tuple(T),rtol=0,atol=1e-10)
  arrays[y]=f.read(1)
# Mirror bridge verification is mandatory; never silently mix unverified sources.
with rasterio.open(args.intermediate/'landcover_1992.tif') as f:assert np.array_equal(f.read(1),arrays[1992])
manifest=json.loads((args.intermediate/'source_manifest.json').read_text())
for item in manifest:
 for tile in item['items']:assert tile['version'].lstrip('v')==versions[item['year']].lstrip('v')
def boundaries(part,codekey):
 f=P/'bounds'/part/(part+'_WGS84.shp');r=shapefile.Reader(str(f));tr=Transformer.from_crs(CRS.from_wkt(f.with_suffix('.prj').read_text()),4326,always_xy=True);polys=[];records=[]
 for i,item in enumerate(r.iterShapeRecords(),1):records.append(item.record.as_dict());polys.append((mapping(transform(tr.transform,shape(item.shape.__geo_interface__))),i))
 return records,rasterize(polys,out_shape=arrays[1992].shape,transform=T,dtype='uint8')
provs,pz=boundaries('ProvCM01012026','COD_PROV');regs,rz=boundaries('Reg01012026','COD_REG');assert np.array_equal(pz>0,rz>0)
g=Geod(ellps='WGS84');area_row=np.array([abs(g.polygon_area_perimeter([0,s,s,0],[c-s/2,c-s/2,c+s/2,c+s/2])[0])/1e6 for c in lat]);w=np.broadcast_to(area_row[:,None],pz.shape)
valid=pz>0
for arr in arrays.values():valid&=arr>0
missing=int(np.count_nonzero((pz>0)&~valid));assert missing==0,'Investigate incomplete temporal support before comparing endpoint benchmarks'
def grouped(mask,z):
 keep=valid&mask
 return np.bincount(z[keep],weights=w[keep],minlength=int(z.max())+1)[1:]
def write(name,rows):
 with (O/name).open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
defs={'strict_10_11_12_20':[10,11,12,20],'strict_plus_mosaic_30':[10,11,12,20,30],'strict_plus_mosaic_30_40':[10,11,12,20,30,40]}
snapshots=[];changes=[];national=[]
def entries(vals,kind,records,name,ys,ye,variable):
 rows=[]
 for i,val in enumerate(vals):
  info=records[i];id=str(info['COD_PROV']).zfill(3) if kind=='province' else str(info['COD_REG']).zfill(2)
  rows.append({'geography_id':id,'geography_type':kind,'period_start':ys,'period_end':ye,'variable':variable,'value':f'{val:.10f}','unit':'km2','source_product':'ESA CCI / Copernicus C3S land cover','product_version':versions[ys] if ys==ye else f'{ys}:{versions[ys]};{ye}:{versions[ye]}','class_definition':name,'quality_note':'Common seven-year valid footprint; 2026 ISTAT pixel-center boundaries; geodesic cell area; no independent accuracy validation','region_id':str(info['COD_REG']).zfill(2)})
 return rows
for name,codes in defs.items():
 masks={y:np.isin(arr,codes) for y,arr in arrays.items()};years=sorted(arrays)
 for y in years:
  pv=grouped(masks[y],pz);rv=grouped(masks[y],rz);total=float(pv.sum());assert abs(total-rv.sum())<1e-6
  for i,r in enumerate(regs):assert abs(sum(pv[j] for j,pr in enumerate(provs) if pr['COD_REG']==r['COD_REG'])-rv[i])<1e-6
  snapshots+=entries(pv,'province',provs,name,y,y,'cropland_area')
  snapshots+=entries(rv,'region',regs,name,y,y,'cropland_area')
  national.append({'year':y,'class_definition':name,'cropland_area_km2':total,'product_version':versions[y]})
 for y0,y1 in zip(years[:-1],years[1:]):
  a,b=masks[y0],masks[y1];ms={'persistence':a&b,'gain':~a&b,'loss':a&~b,'cropland_t0':a,'cropland_t1':b}
  for kind,records,z in [('province',provs,pz),('region',regs,rz)]:
   values={k:grouped(m,z) for k,m in ms.items()};values['net_change']=values['gain']-values['loss'];assert np.allclose(values['net_change'],values['cropland_t1']-values['cropland_t0'],atol=1e-7,rtol=0)
   for variable,vals in values.items():changes+=entries(vals,kind,records,name,y0,y1,variable)
write('Italy_Cropland_Snapshot_Panel_1992_2022.csv',snapshots);write('Italy_Cropland_Interval_Changes_1992_2022.csv',changes);write('Italy_National_Cropland_Seven_Years.csv',national)
write('Cell_Area_By_Latitude.csv',[{'row_index':i,'latitude_center':f'{c:.12f}','cell_area_km2':f'{area_row[i]:.15f}'} for i,c in enumerate(lat)])
checks={'years':sorted(arrays),'province_count':len(provs),'region_count':len(regs),'snapshot_rows':len(snapshots),'interval_rows':len(changes),'all_years_missing_Italy_cells':missing,'CDS_PC_1992_mismatch_pixels':0,'valid_area_km2':float(w[valid].sum()),'grid_shape':list(pz.shape),'grid_step_degrees':s,'transform':list(T),'area_formula':'abs(Geod(ellps=WGS84).polygon_area_perimeter([0,s,s,0],[c-s/2,c-s/2,c+s/2,c+s/2])[0])/1e6','checks_passed':['mirror bridge equality','grid coordinates and transform','full common valid footprint','province-region-national sums','interval accounting']}
strict=[r for r in national if r['class_definition']=='strict_10_11_12_20'];assert abs(strict[0]['cropland_area_km2']-140149.33632058)<1e-6;assert abs(strict[-1]['cropland_area_km2']-139192.06590187)<1e-6
(O/'panel_checks.json').write_text(json.dumps(checks,indent=2))
fig,ax=plt.subplots(figsize=(7,3));ax.plot([r['year'] for r in strict],[r['cropland_area_km2'] for r in strict],'o-',color='#267b85');ax.set_xticks(sorted(arrays));ax.set_ylabel('Mapped strict cropland km²');ax.ticklabel_format(axis='y',style='plain',useOffset=False);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(O/'national_intermediate_years.png',dpi=180);plt.close(fig)
print(json.dumps(checks,indent=2));print(json.dumps(strict,indent=2))
