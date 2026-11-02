"""Owned loopback service: real leave API and one lost reply."""
import argparse, json, os, re, socket, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Backend'))
import uvicorn
from fastapi.responses import JSONResponse
from hotr_backend.api import create_app

def save(path,value):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,separators=(',',':')),encoding='utf-8');temp.replace(path)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True,type=Path);p.add_argument('--run-id',required=True);args=p.parse_args();directory=args.directory.resolve()
 if not directory.is_relative_to((ROOT/'.verification-cache/Review115/RankHTTP').resolve()) or not re.fullmatch('[a-f0-9]{32}',args.run_id):p.error('ExactFreshInvite113DirectoryRequired')
 directory.mkdir(parents=True,exist_ok=True)
 if any((directory/name).exists() for name in ('authority.sqlite3','connection.json','operator.json')):p.error('FreshPrivateDatabaseRequired')
 for name in tuple(os.environ):
  if name.startswith('HOTR_'):os.environ.pop(name)
 os.environ['HOTR_BACKEND_MODE']='local'; sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sock.bind(('127.0.0.1',0));sock.listen(128);host,port=sock.getsockname()
 app=create_app(directory/'authority.sqlite3',ROOT/'Backend/config',lambda:1800000000,identity_enabled=True,social_enabled=True,replay_enabled=False,notifications_enabled=False)
 control=directory/'operator.json';save(control,{'dropLeaveCommand':''});requests=[];drops=[]
 @app.middleware('http')
 async def observe(request,call_next):
  if control.stat().st_size>4096:raise RuntimeError('BoundedControlRequired113')
  value=json.loads(control.read_text('utf-8'));selected=False
  if request.method=='POST' and request.url.path == '/v1/friends/request' and value.get('dropLeaveCommand'):
   body=json.loads((await request.body()).decode('utf-8'));selected=body.get('commandId')==value['dropLeaveCommand']
  response=await call_next(request);lose=selected and response.status_code==200
  if lose:
   drops.append(dict(afterActualCommit=True,originalStatus=200,clientStatus=503));save(directory/'DroppedLeaveResponses.json',drops);value['dropLeaveCommand']='';save(control,value)
  if len(requests)>=512:raise RuntimeError('BoundedHttpFlowRequired113')
  requests.append(dict(method=request.method,path=re.sub(r'/[a-f0-9]{32}(?=/|$)','/{id}',request.url.path),status=503 if lose else response.status_code,committedResponseSuppressed=lose));save(directory/'RequestCounts.json',requests)
  return JSONResponse({'error':'synthetic_after_friend_commit_loss115'},status_code=503) if lose else response
 save(directory/'connection.json',dict(runId=args.run_id,pid=os.getpid(),origin=f'http://{host}:{port}',clock=1800000000,actualBackend=True,replayEnabled=False,providersEnabled=False,productionEnabled=False,scope='Owned loopback real service; fixed clock for verification only.'))
 uvicorn.Server(uvicorn.Config(app,host=host,port=port,log_level='warning',access_log=False)).run(sockets=[sock])
if __name__=='__main__':main()
