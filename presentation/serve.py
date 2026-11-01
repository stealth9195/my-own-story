"""발표 자료 편집용 로컬 서버 (내 PC 안에서만 열림).

python presentation/serve.py   → http://127.0.0.1:4321/deck.html

- presentation 폴더를 그대로 보여 준다.
- 편집 모드(E)에서 Ctrl+S → deck.html 에 바로 저장. 저장 전 판은 backups/ 에 남긴다.
- 그림 바꾸기 목록은 앱 그림(frontend/public/img)에서 가져오고, 고른 그림만 assets/img 로 복사한다.
"""

import json
import re
import shutil
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECK = HERE / "deck.html"
BACKUPS = HERE / "backups"
DECK_IMG = HERE / "assets" / "img"
APP_IMG = HERE.parent / "frontend" / "public" / "img"
HOST, PORT = "127.0.0.1", 4321
MAX_SAVE = 5 * 1024 * 1024  # deck.html 은 100KB 안팎. 이보다 크면 잘못된 요청으로 본다
IMG_NAME = re.compile(r"^[a-z0-9_]+\.webp$")


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # 고친 뒤 새로고침하면 바로 보이게
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _same_origin(self) -> bool:
        # 다른 사이트가 브라우저를 시켜 저장 요청을 보내는 것을 막는다
        origin = self.headers.get("Origin")
        return origin in (None, f"http://{HOST}:{PORT}", f"http://localhost:{PORT}")

    def do_GET(self):
        if self.path == "/__ping":
            return self._json(200, {"ok": True})
        if self.path == "/__images":
            names = sorted(p.name for p in APP_IMG.glob("*.webp")) if APP_IMG.exists() else []
            return self._json(200, {"images": names})
        if self.path.startswith("/__appimg/"):
            # 그림 바꾸기 목록의 미리보기 (아직 assets/img 에 없는 그림도 보여 주려고)
            name = self.path.removeprefix("/__appimg/")
            src = APP_IMG / name
            if not IMG_NAME.match(name) or not src.exists():
                return self._json(404, {"error": "name"})
            data = src.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/webp")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self):
        if not self._same_origin():
            return self._json(403, {"error": "origin"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_SAVE:
            return self._json(400, {"error": "size"})
        body = self.rfile.read(length)

        if self.path == "/__save":
            html = body.decode("utf-8")
            if "<html" not in html[:500].lower() or 'id="deck-stage"' not in html:
                return self._json(400, {"error": "not_deck"})
            BACKUPS.mkdir(exist_ok=True)
            backup = BACKUPS / f"deck-{datetime.now():%Y%m%d-%H%M%S}.html"
            shutil.copyfile(DECK, backup)
            tmp = DECK.with_suffix(".tmp")
            tmp.write_text(html, encoding="utf-8")
            tmp.replace(DECK)
            return self._json(200, {"ok": True, "backup": backup.name})

        if self.path == "/__use-image":
            name = json.loads(body).get("name", "")
            src = APP_IMG / name
            if not IMG_NAME.match(name) or not src.exists():
                return self._json(400, {"error": "name"})
            DECK_IMG.mkdir(parents=True, exist_ok=True)
            if not (DECK_IMG / name).exists():
                shutil.copyfile(src, DECK_IMG / name)
            return self._json(200, {"ok": True, "src": f"assets/img/{name}"})

        return self._json(404, {"error": "path"})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), partial(Handler, directory=str(HERE)))
    print(f"발표 자료: http://{HOST}:{PORT}/deck.html  (끄기: Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
