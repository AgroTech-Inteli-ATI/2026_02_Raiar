"""Backend de mentira para testar o sync: aceita tudo e confirma os IDs recebidos."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ids = [a["analise_id"] for a in corpo["analyses"]]
        print(f"[backend] recebi {len(ids)} análise(s); token={self.headers.get('Authorization')}", flush=True)
        resp = json.dumps({"accepted_analysis_ids": ids}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp))); self.end_headers(); self.wfile.write(resp)
    def log_message(self, *a): pass

HTTPServer(("127.0.0.1", 8081), H).serve_forever()
