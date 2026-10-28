"""Run only after independent reference labels have been finalized."""
from pathlib import Path
import argparse,csv,json,importlib.util
import numpy as np
import pandas as pd
CLASSES=['stable_cropland','gain','loss','stable_other']

def read(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
 p=argparse.ArgumentParser()
 for k in ['labels','key','design','team-sampling']:p.add_argument('--'+k,required=True,type=Path)
 p.add_argument('--out',required=True,type=Path);args=p.parse_args()
 labels=read(args.labels);keys=read(args.key);design=json.loads(args.design.read_text())
 ids=[r['sample_id'] for r in labels];kid=[r['sample_id'] for r in keys]
 if len(ids)!=len(set(ids)) or len(kid)!=len(set(kid)) or set(ids)!=set(kid):raise ValueError('Sample IDs are duplicated or do not match')
 byid={r['sample_id']:r for r in keys};counts=pd.DataFrame(0,index=CLASSES,columns=CLASSES)
 for r in labels:
  if r.get('status')!='final':raise ValueError('All labels must be final; no accuracy has been calculated')
  required=['reference_source_1992','reference_date_1992','reference_source_2022','reference_date_2022','reviewer_id']
  if any(not r.get(k,'').strip() for k in required):raise ValueError('Reference evidence fields are incomplete')
  a,b=r['reference_cropland_1992'],r['reference_cropland_2022']
  if a not in ['0','1'] or b not in ['0','1']:raise ValueError('Each reference label must be 0 or 1')
  ref={('1','1'):'stable_cropland',('0','1'):'gain',('1','0'):'loss',('0','0'):'stable_other'}[(a,b)]
  counts.loc[byid[r['sample_id']]['mapped_stratum'],ref]+=1
 W=design['stratum_area_weights'];n=counts.sum(axis=1).to_numpy(float)
 if any(n<2):raise ValueError('Insufficient labels per stratum')
 if any(int(n[i])!=design['allocation'][c] for i,c in enumerate(CLASSES)):raise ValueError('Allocation differs from the frozen design')
 spec=importlib.util.spec_from_file_location('team_sampling',args.team_sampling);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 result=mod.estimate(counts,W);result['status']='Computed from finalized supplied reference labels'
 weights=np.array([W[c] for c in CLASSES]);share=counts.to_numpy(float)/n[:,None]
 # A reference draw has value +1 for gain, -1 for loss, else 0.
 values=np.array([0,1,-1,0]);means=share@values;second=share@(values**2)
 net=float(weights@means);variance=float(np.sum(weights**2*(second-means**2)/(n-1)))
 area=design['mapped_area_km2'];se=float(np.sqrt(max(variance,0)))
 result['corrected_area_km2']={k:float(v*area) for k,v in result['area_proportion'].items()}
 result['corrected_net_change_km2']=net*area;result['corrected_net_se_km2']=se*area
 result['corrected_net_ci95_normal_km2']=[(net-1.96*se)*area,(net+1.96*se)*area]
 result['overall_accuracy_ci95_normal']=[result['overall_accuracy']-1.96*result['overall_accuracy_se'],result['overall_accuracy']+1.96*result['overall_accuracy_se']]
 args.out.mkdir(parents=True,exist_ok=True);counts.to_csv(args.out/'reference_confusion_matrix.csv')
 (args.out/'accuracy_results.json').write_text(json.dumps(result,indent=2,default=lambda x:float(x)))
 print('Reference accuracy calculated:',args.out)

if __name__=='__main__':main()
