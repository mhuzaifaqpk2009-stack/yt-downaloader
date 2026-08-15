import sys, struct, json, socket, time, os, subprocess

IPC_HOST = '127.0.0.1'
IPC_PORT = 49876

# Native messaging protocol: 4-byte little-endian length, then JSON
def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return None
    if len(raw_length) < 4:
        return None
    length = struct.unpack('<I', raw_length)[0]
    data = sys.stdin.buffer.read(length).decode('utf-8')
    return json.loads(data)

def send_ipc_message(msg):
    try:
        with socket.create_connection((IPC_HOST, IPC_PORT), timeout=1) as s:
            s.sendall(json.dumps(msg).encode('utf-8'))
        return True
    except Exception:
        return False

def launch_app_with_url(url):
    # Assume native_host.exe is installed in the same folder as the app
    try:
        this_path = os.path.abspath(sys.executable)
        folder = os.path.dirname(this_path)
        exe_path = os.path.join(folder, 'YT_Downloader.exe')
        if os.path.exists(exe_path):
            subprocess.Popen([exe_path, url], close_fds=True)
            return True
    except Exception:
        pass
    return False

if __name__ == '__main__':
    msg = read_message()
    if not msg:
        sys.exit(0)
    url = None
    fetch = True
    if isinstance(msg, dict):
        url = msg.get('url')
        fetch = msg.get('fetch', True)
    if not url:
        sys.exit(0)
    payload = {"url": url, "fetch": bool(fetch)}
    # Try to send to running app via local IPC
    if send_ipc_message(payload):
        sys.exit(0)
    # If not running, try to launch the app and retry
    if launch_app_with_url(url):
        # give the app a moment to start and its IPC server to begin
        for i in range(10):
            time.sleep(0.5)
            if send_ipc_message(payload):
                sys.exit(0)
    sys.exit(1)
