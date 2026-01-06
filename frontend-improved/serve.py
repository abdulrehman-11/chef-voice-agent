"""
Simple HTTP Server for Frontend
Serves the frontend on http://localhost:8000
"""
import http.server
import socketserver
import os

PORT = 8000

# Change to frontend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print("=" * 60)
        print(f"   Frontend Server Running")
        print("=" * 60)
        print(f"\n🌐 Server: http://localhost:{PORT}")
        print(f"📂 Serving: {os.getcwd()}")
        print(f"\n✅ Open http://localhost:{PORT} in your browser")
        print("\nPress Ctrl+C to stop\n")
        httpd.serve_forever()
