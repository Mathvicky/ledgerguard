import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from . import store

ROOT=Path(__file__).resolve().parent.parent
class Handler(BaseHTTPRequestHandler):
    def respond(self,status,body):
        raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/health':
            with store.db() as c:c.execute('SELECT 1 FROM jobs LIMIT 1')
            return self.respond(200,{'status':'ready'})
        if self.path.startswith('/api/jobs/'):
            result=store.status(self.path.rsplit('/',1)[-1]);return self.respond(200 if result else 404,result or {'error':'Unknown job'})
        paths={'/':'web/index.html','/app.js':'web/app.js','/engine.js':'web/engine.js','/style.css':'web/style.css'}
        if self.path not in paths:return self.respond(404,{'error':'Not found'})
        raw=(ROOT/paths[self.path]).read_bytes();self.send_response(200);self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript','css':'text/css'}[self.path.split('.')[-1]] if '.' in self.path else 'text/html; charset=utf-8');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2000000:return self.respond(413,{'error':'Request must be 1 byte to 2 MB'})
            body=json.loads(self.rfile.read(size))
            if self.path=='/api/jobs':return self.respond(202,{'id':store.submit(body)})
            if self.path=='/api/cases':return self.respond(200,store.transition(body['job_id'],body['id'],body['status'],body['note']))
            self.respond(404,{'error':'Not found'})
        except (ValueError,KeyError,TypeError,UnicodeError) as e:self.respond(400,{'error':str(e)})
        except Exception:self.respond(503,{'error':'Service unavailable'})

def worker(stop):
    while not stop.is_set():
        try:store.tick()
        except Exception:print(json.dumps({'event':'worker_error'}),flush=True)
        stop.wait(.5)

if __name__=='__main__':
    store.initialize();stop=threading.Event();thread=threading.Thread(target=worker,args=(stop,),daemon=True);thread.start()
    server=ThreadingHTTPServer((os.getenv('HOST','127.0.0.1'),int(os.getenv('PORT','8091'))),Handler)
    print('LedgerGuard: http://localhost:'+str(server.server_port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();server.server_close();thread.join(timeout=5)
