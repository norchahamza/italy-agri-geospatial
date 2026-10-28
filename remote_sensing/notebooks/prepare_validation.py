"""Generate an area-proportional stratified reference-labelling sample.
The frame is the strict 1992-2022 cropland change map, not ground truth.
"""
from pathlib import Path
import argparse,csv,json,importlib.util,random,math,hashlib
import numpy as np,xarray as xr,shapefile
from pyproj import Transformer,CRS,Geod
from shapely.geometry import shape,mapping
from shapely.ops import transform
from rasterio.features import rasterize
from rasterio.transform import from_origin
parser=argparse.ArgumentParser();parser.add_argument('--input-root',type=Path,default=Path('province_work'));parser.add_argument('--out',type=Path,default=Path('revision_work/validation'));parser.add_argument('--sampling-module',type=Path,default=Path('province_work/repo/italy-agri-geospatial/src/sampling.py'));args=parser.parse_args();P=args.input_root;O=args.out;O.mkdir(exist_ok=True,parents=True)
with xr.open_dataset(next((P/'lc1992').glob('*.nc'))) as d:a=d.lccs_class.values.squeeze();lat=d.lat.values;lon=d.lon.values
with xr.open_dataset(next((P/'lc2022').glob('*.nc'))) as d:b=d.lccs_class.values.squeeze();assert np.array_equal(lat,d.lat.values) and np.array_equal(lon,d.lon.values)
existing=O/'reference_labels_blind.csv'
if existing.exists():
 with existing.open(encoding='utf-8-sig') as stream:
  for row in csv.DictReader(stream):
   if row.get('reference_cropland_1992') or row.get('reference_cropland_2022') or row.get('status','unlabelled')!='unlabelled':raise ValueError('Existing reference annotations must not be overwritten; select a new output directory')
s=abs(float(lon[1]-lon[0]));T=from_origin(lon.min()-s/2,lat.max()+s/2,s,s)
f=P/'bounds/ProvCM01012026/ProvCM01012026_WGS84.shp';rr=shapefile.Reader(str(f));tr=Transformer.from_crs(CRS.from_wkt(f.with_suffix('.prj').read_text()),4326,always_xy=True)
recs=[];geoms=[]
for i,sr in enumerate(rr.iterShapeRecords(),1):recs.append(sr.record.as_dict());geoms.append((mapping(transform(tr.transform,shape(sr.shape.__geo_interface__))),i))
z=rasterize(geoms,out_shape=a.shape,transform=T,dtype='uint8');valid=(z>0)&(a>0)&(b>0)
g=Geod(ellps='WGS84');areas=np.array([abs(g.polygon_area_perimeter([0,s,s,0],[c-s/2,c-s/2,c+s/2,c+s/2])[0])/1e6 for c in lat]);w=np.broadcast_to(areas[:,None],a.shape)
ca=np.isin(a,[10,11,12,20]);cb=np.isin(b,[10,11,12,20]);strata={'stable_cropland':ca&cb,'gain':~ca&cb,'loss':ca&~cb,'stable_other':~ca&~cb};total=float(w[valid].sum());weights={k:float(w[m&valid].sum())/total for k,m in strata.items()}
# Reuse the team's sample-size and allocation functions unchanged.
spec=importlib.util.spec_from_file_location('team_sampling',args.sampling_module);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
expected={'stable_cropland':.90,'gain':.80,'loss':.80,'stable_other':.95};n=mod.sample_size(weights,expected,target_se=.02);alloc=mod.allocate(n,weights,min_per_stratum=50)
rng=np.random.default_rng(20261028);draws=[]
for k,m in strata.items():
 idx=np.flatnonzero((m&valid).ravel());prob=areas[idx//a.shape[1]];prob=prob/prob.sum()
 # With-replacement PPS draws make each draw area-representative within stratum.
 # Repeated cells, if any, are retained and reported, not silently discarded.
 chosen=rng.choice(idx,size=alloc[k],replace=True,p=prob)
 for ix in chosen:draws.append((k,int(ix)))
rng.shuffle(draws);blind=[];key=[];features=[]
for i,(k,ix) in enumerate(draws,1):
 r,c=divmod(ix,a.shape[1]);pr=recs[int(z[r,c])-1];id=f'V{i:04d}'
 row={'sample_id':id,'longitude':f'{lon[c]:.10f}','latitude':f'{lat[r]:.10f}',
 'west':f'{lon[c]-s/2:.10f}','south':f'{lat[r]-s/2:.10f}','east':f'{lon[c]+s/2:.10f}','north':f'{lat[r]+s/2:.10f}',
 'province_id':str(pr['COD_PROV']).zfill(3),'region_id':str(pr['COD_REG']).zfill(2),
 'reference_cropland_1992':'','reference_cropland_2022':'','reference_source_1992':'','reference_date_1992':'','reference_source_2022':'','reference_date_2022':'',
 'reviewer_id':'','confidence':'','second_reviewer_id':'','adjudication_note':'','status':'unlabelled'}
 blind.append(row);key.append({'sample_id':id,'mapped_stratum':k,'row_index':r,'column_index':c,'map_class_1992':int(a[r,c]),'map_class_2022':int(b[r,c]),'cell_area_km2':areas[r],'within_stratum_draw_probability':areas[r]/float(w[strata[k]&valid].sum())})
 features.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[lon[c]-s/2,lat[r]-s/2],[lon[c]+s/2,lat[r]-s/2],[lon[c]+s/2,lat[r]+s/2],[lon[c]-s/2,lat[r]+s/2],[lon[c]-s/2,lat[r]-s/2]]]},'properties':{'sample_id':id,'status':'unlabelled'}})
def save(name,rows):
 with (O/name).open('w',newline='',encoding='utf8') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
save('reference_labels_blind.csv',blind);save('coordinator_map_key.csv',key)
change_ids={row['sample_id'] for row in key if row['mapped_stratum'] in ['gain','loss']}
stable_ids=[row['sample_id'] for row in key if row['sample_id'] not in change_ids]
random.Random(20261028).shuffle(stable_ids);secondary_ids=change_ids|set(stable_ids[:math.ceil(.2*len(stable_ids))])
save('secondary_reference_labels_blind.csv',[row for row in blind if row['sample_id'] in secondary_ids])
(O/'sample_cells_blind.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
forecast_se=float(np.sqrt(sum(weights[k]**2*expected[k]*(1-expected[k])/alloc[k] for k in weights)))
info={'status':'UNLABELLED; no observed accuracy available','seed':20261028,'target_se_overall_accuracy':.02,'planning_expected_users_accuracy':expected,'nominal_n':n,'allocation':alloc,'actual_draws':len(blind),'duplicate_cell_draws':len(draws)-len(set(ix for k,ix in draws)),'mapped_area_km2':total,'stratum_area_weights':weights,'forecast_se_using_planning_assumptions':forecast_se,'sampling_design':'Independent with-replacement PPS by geodesic pixel area within each of four mapped strata; all draws retained','precision_scope':'National strict 1992-2022 change only; not province-level accuracy or accuracy for the other cropland definitions','pixel_support':'Entire original approximately 300m cell; footprints supplied'}
info['team_sampling_module_sha256']=hashlib.sha256(args.sampling_module.read_bytes()).hexdigest()
info['team_base_commit']='465de099e878a198b2df9cec04050221f39f41ce' if info['team_sampling_module_sha256']=='252f7214f67c0354956c5a205353fe477da6d90c7aeab859a7cb92ef849a0914' else 'not verified; record the actual team source commit'
(O/'sample_design.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2))
