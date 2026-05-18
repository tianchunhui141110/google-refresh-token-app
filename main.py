"""
Google Refresh Token 生成器 - 桌面版
HTML + Python 本地服务器，全自动授权 + 换取 Token

打包命令：
  pip install pyinstaller
  pyinstaller --onefile --windowed --name "GoogleRefreshToken" main.py
"""

import webbrowser
import urllib.parse
import urllib.request
import json
import threading
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============ 常量 ============
DEFAULT_PORT = 19527
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# ============ 嵌入的 HTML 页面（从 index.html 加载）============
HTML_PAGE = None  # 延迟加载


def get_html_page():
    """加载嵌入的 HTML 页面，优先从同目录 index.html 读取，否则使用内置版本"""
    global HTML_PAGE
    if HTML_PAGE is not None:
        return HTML_PAGE

    # 优先从同目录的 index.html 文件读取（方便更新）
    try:
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            HTML_PAGE = f.read()
            return HTML_PAGE
    except Exception:
        pass

    # PyInstaller 打包后从临时目录读取
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_path, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            HTML_PAGE = f.read()
            return HTML_PAGE
    except Exception:
        pass

    # 最终回退：内置简易版
    HTML_PAGE = """<!DOCTYPE html><html><body><h1>Error</h1><p>index.html not found</p></body></html>"""
    return HTML_PAGE


# ============ 服务器状态 ============
ACTUAL_PORT = DEFAULT_PORT  # 运行时更新为实际端口


class ServerState:
    """存储授权回调结果"""
    callback_result = None  # None=等待, ("code", code), ("error", msg)


# ============ HTTP 请求处理器 ============
class RequestHandler(BaseHTTPRequestHandler):
    """处理所有 HTTP 请求"""

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_html()
        elif self.path.startswith("/callback"):
            self._handle_callback()
        elif self.path == "/api/ping":
            self._json_response(200, {"status": "ok"})
        elif self.path == "/api/config":
            self._json_response(200, {"port": ACTUAL_PORT})
        elif self.path == "/api/callback-result":
            self._api_callback_result()
        elif self.path == "/shutdown":
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/auth-url":
            self._api_auth_url()
        elif self.path == "/api/exchange":
            self._api_exchange()
        else:
            self.send_response(404)
            self.end_headers()

    # ---------- 页面 ----------
    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(get_html_page().encode("utf-8"))

    # ---------- 授权回调 ----------
    def _handle_callback(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            code = params["code"][0]
            ServerState.callback_result = ("code", code)
            self._respond_page(
                200, "#e8f5e9", "#34a853", "&#10004; 授权成功！",
                "请回到工具页面查看结果，此页面可以关闭"
            )
        elif "error" in params:
            error = params["error"][0]
            desc = params.get("error_description", [""])[0]
            ServerState.callback_result = ("error", f"{error}: {desc}")
            self._respond_page(
                400, "#fce8e6", "#c62828", "&#10008; 授权失败",
                f"{error}: {desc}"
            )
        else:
            self.send_response(400)
            self.end_headers()

    def _respond_page(self, code, bg, color, title, msg):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"""
        <html><body style="font-family:-apple-system,sans-serif;
        display:flex;justify-content:center;align-items:center;height:100vh;
        background:{bg};margin:0;">
        <div style="text-align:center">
        <h1 style="color:{color};font-size:32px;">{title}</h1>
        <p style="font-size:16px;color:#555;">{msg}</p>
        </div></body></html>
        """.encode("utf-8"))

    # ---------- API: 获取授权回调结果 ----------
    def _api_callback_result(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if ServerState.callback_result is None:
            self.wfile.write(json.dumps({"status": "pending"}).encode())
        elif ServerState.callback_result[0] == "code":
            code = ServerState.callback_result[1]
            ServerState.callback_result = None  # 重置
            self.wfile.write(json.dumps({"status": "code", "code": code}).encode())
        else:
            msg = ServerState.callback_result[1]
            ServerState.callback_result = None
            self.wfile.write(json.dumps({"status": "error", "message": msg}).encode())

    # ---------- API: 生成授权 URL ----------
    def _api_auth_url(self):
        body = self._read_json()
        client_id = body.get("client_id", "")
        client_secret = body.get("client_secret", "")
        redirect_uri = body.get("redirect_uri", "")

        if not client_id or not client_secret or not redirect_uri:
            self._json_response(400, {"error": "缺少必要参数"})
            return

        # 重置回调状态
        ServerState.callback_result = None

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "scope": SCOPE,
        }
        url = AUTH_URL + "?" + urllib.parse.urlencode(params)
        self._json_response(200, {"url": url})

    # ---------- API: 换取 Token ----------
    def _api_exchange(self):
        body = self._read_json()
        code = body.get("code", "")
        client_id = body.get("client_id", "")
        client_secret = body.get("client_secret", "")
        redirect_uri = body.get("redirect_uri", "")

        if not code or not client_id or not client_secret or not redirect_uri:
            self._json_response(400, {"error": "invalid_request", "error_description": "缺少必要参数"})
            return

        try:
            data = urllib.parse.urlencode({
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }).encode("utf-8")

            req = urllib.request.Request(TOKEN_URL, data=data)
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            self._json_response(200, result)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_data = json.loads(err_body)
            except Exception:
                err_data = {"error": "server_error", "error_description": err_body}
            self._json_response(200, err_data)

        except Exception as e:
            self._json_response(200, {"error": "request_failed", "error_description": str(e)})

    # ---------- 工具方法 ----------
    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # 抑制服务器日志


# ============ 入口 ============
def find_available_port(start_port, max_tries=20):
    """从 start_port 开始，寻找可用端口"""
    import socket
    for port in range(start_port, start_port + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
    return start_port  # 都被占用则返回默认值


def main():
    global ACTUAL_PORT
    port = find_available_port(DEFAULT_PORT)
    ACTUAL_PORT = port

    server = HTTPServer(("127.0.0.1", port), RequestHandler)
    print(f"本地服务器已启动: http://localhost:{port}")

    # 在后台线程运行服务器
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # 打开浏览器
    url = f"http://localhost:{port}/"
    print(f"正在打开浏览器: {url}")
    webbrowser.open(url)

    # 保持主线程运行
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.shutdown()


if __name__ == "__main__":
    main()
