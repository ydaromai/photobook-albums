"""Localhost helper (127.0.0.1 only) to move data between the Mixbook editor page and disk.
Usage: python3 -I helper_server.py <dir> <port>
  GET  /<name> -> serves <dir>/<name>   (files to upload, put.json)
  POST /<name> -> writes <dir>/<name>   (content.json, results)
CORS is limited to ORIGIN (default https://www.mixbook.com)."""
import http.server, os, sys, re, urllib.parse
OUT = sys.argv[1]
class H(http.server.BaseHTTPRequestHandler):
    def cors(self):
        self.send_header('Access-Control-Allow-Origin', os.environ.get('ORIGIN','https://www.mixbook.com'))
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.end_headers()
    def do_POST(self):
        name = os.path.basename(urllib.parse.unquote(self.path.split('?')[0])) or 'blob.txt'   # decoded, no directories
        n = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(n)
        with open(os.path.join(OUT, name), 'wb') as f: f.write(data)
        self.send_response(200); self.cors(); self.end_headers(); self.wfile.write(b'ok %d' % len(data))
    def do_GET(self):
        name = os.path.basename(urllib.parse.unquote(self.path.split('?')[0]))   # decoded, no directories
        p = os.path.join(OUT, name)
        if not name or not os.path.isfile(p):
            self.send_response(404); self.cors(); self.end_headers(); return
        self.send_response(200); self.cors(); self.send_header('Content-Type','image/jpeg' if name.lower().endswith('.jpg') else 'application/json'); self.end_headers()
        self.wfile.write(open(p,'rb').read())
    def log_message(self, *a): pass
http.server.HTTPServer(('127.0.0.1', int(sys.argv[2])), H).serve_forever()
