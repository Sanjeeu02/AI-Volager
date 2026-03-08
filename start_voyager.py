import socket
import os
import subprocess
import time
import sys
import webbrowser
import threading
from http.server import SimpleHTTPRequestHandler
import socketserver

# CONFIG
LANDING_PORT = 8000
STREAMLIT_PORT = 8501
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
APP_DIR = os.path.join(BASE_DIR, "helloworld", "travel_agent")

def get_ip():
    """Get the actual local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def update_index_ip(ip):
    """Automatically patch index.html with the current detected IP."""
    if not os.path.exists(INDEX_FILE):
        print(f"❌ Error: index.html not found at {INDEX_FILE}")
        return False
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We look for the APP_URL assignment in the script block
    import re
    # Patterns for both the JS variable and the hardcoded href in the launch button
    new_content = re.sub(r'const APP_URL = "http://.*:8501"', f'const APP_URL = "http://{ip}:8501"', content)
    new_content = re.sub(r'href="http://.*:8501"', f'href="http://{ip}:8501"', new_content)
    # Also update any example tooltips
    new_content = re.sub(r'e\.g\. http://.*:8501', f'e.g. http://{ip}:8501', new_content)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ index.html patched with current IP: {ip}")
    return True

def run_streamlit():
    """Start the Streamlit app on the AI engine."""
    print("🚀 Starting AI Voyager Engine...")
    cmd = [
        "streamlit", "run", "app.py",
        "--server.address", "0.0.0.0",
        "--server.port", str(STREAMLIT_PORT),
        "--browser.gatherUsageStats", "false"
    ]
    subprocess.Popen(cmd, cwd=APP_DIR)

def start_landing_server():
    """Serve the landing page in a background thread."""
    os.chdir(BASE_DIR)
    Handler = SimpleHTTPRequestHandler
    # Allow port reuse to avoid 'address already in use' errors
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", LANDING_PORT), Handler) as httpd:
        print(f"🌍 Landing Page ready at http://localhost:{LANDING_PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    current_ip = get_ip()
    print(f"🔍 Detected Network IP: {current_ip}")
    
    # 1. Update HTML so mobile links always work
    update_index_ip(current_ip)
    
    # 2. Start AI Engine (Streamlit)
    run_streamlit()
    
    # 3. Start Landing Page Server in a separate thread
    threading.Thread(target=start_landing_server, daemon=True).start()
    
    # 4. Give it a moment then open browser locally
    time.sleep(3)
    print("\n" + "="*50)
    print(f"✨ AI VOYAGER IS NOW LIVE! ✨")
    print(f"💻 On this computer: http://localhost:{LANDING_PORT}")
    print(f"📱 On your mobile:   http://{current_ip}:{LANDING_PORT}")
    print("="*50 + "\n")
    
    webbrowser.open(f"http://localhost:{LANDING_PORT}")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping AI Voyager...")
        sys.exit(0)
