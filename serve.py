#!/usr/bin/env python3
"""Dev server with no-cache headers."""
from http.server import SimpleHTTPRequestHandler, HTTPServer

class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 3456), NoCacheHandler)
    print("Serving at http://127.0.0.1:3456")
    server.serve_forever()
