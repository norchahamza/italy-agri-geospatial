"""Fetch exact-grid Italy class subsets from Microsoft Planetary Computer.
HTTPS is certificate-verified by urllib. A loopback-only range proxy provides
these same bytes to GDAL and avoids dependency-specific TLS trust differences.
SAS URLs are temporary, retained only in memory and never written to the manifest.
Large rasters belong outside git. The 1992 bridge MUST match the original CDS file.
"""
from pathlib import Path
import argparse,datetime,json,urllib.request,urllib.parse,time,threading
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
REMOTE={}
class Proxy(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_HEAD(self):self.relay(True)
 def do_GET(self):self.relay(False)
 def relay(self,head):
  try:
   url=REMOTE[self.path.split("?")[0]]
   headers={"Range":self.headers["Range"]} if self.headers.get("Range") else {}
   req=urllib.request.Request(url,headers=headers,method="HEAD" if head else "GET")
   with urllib.request.urlopen(req,timeout=90) as response:
    self.send_response(response.status)
    for key in ["Content-Length","Content-Type","Content-Range","Accept-Ranges"]:
     if response.headers.get(key):self.send_header(key,response.headers[key])
    self.end_headers()
    if not head:
     while True:
      data=response.read(1024*1024)
      if not data:break
      self.wfile.write(data)
  except Exception as e:
   self.send_error(502,str(type(e).__name__))
server=ThreadingHTTPServer(("127.0.0.1",0),Proxy)
threading.Thread(target=server.serve_forever,daemon=True).start()
import numpy as np,rasterio,xarray as xr
from rasterio.merge import merge
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cds-1992',type=Path,required=True);args=parser.parse_args();D=args.out;D.mkdir(exist_ok=True,parents=True)
log=[]
for year in [1992,1997,2002,2007,2012,2017]:
 out=D/f'landcover_{year}.tif'
 url='https://planetarycomputer.microsoft.com/api/stac/v1/search?'+urllib.parse.urlencode({'collections':'esa-cci-lc','bbox':'6,35,19,48','datetime':f'{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z','limit':20})
 data=json.load(urllib.request.urlopen(url,timeout=45));items=data['features'];assert len(items)==2
 sources=[];entry={'year':year,'accessed':datetime.date.today().isoformat(),'items':[]}
 try:
  with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_TIMEOUT='90'):
   for item in items:
    href=item['assets']['lccs_class']['href'];entry['items'].append({'id':item['id'],'version':item['properties'].get('esa_cci_lc:version'),'href':href})
    signurl='https://planetarycomputer.microsoft.com/api/sas/v1/sign?'+urllib.parse.urlencode({'href':href})
    signed=json.load(urllib.request.urlopen(signurl,timeout=30))['href']
    local='/'+item['id']+'.tif';REMOTE[local]=signed
    sources.append(rasterio.open('http://127.0.0.1:'+str(server.server_port)+local))
   arr,t=merge(sources,bounds=(6,35,19,48),res=1/360,nodata=0)
   assert arr.shape==(1,4680,4680),arr.shape
   with rasterio.open(out,'w',driver='GTiff',height=4680,width=4680,count=1,dtype='uint8',crs='EPSG:4326',transform=t,nodata=0,compress='deflate') as f:f.write(arr)
   if year==1992:
    old=xr.open_dataset(args.cds_1992).lccs_class.values.squeeze()
    mismatch=int(np.count_nonzero(arr[0]!=old));entry['comparison_with_CDS_1992_mismatch_pixels']=mismatch
    assert mismatch==0,mismatch
   print(year,'downloaded Italy subset',out.stat().st_size,'bytes',flush=True)
   log.append(entry);(D/'source_manifest.json').write_text(json.dumps(log,indent=2))
 finally:
  for f in sources:f.close()
