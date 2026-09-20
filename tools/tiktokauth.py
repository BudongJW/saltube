#!/usr/bin/env python3
"""tiktokauth — 틱톡 액세스 토큰 발급·갱신.

    python3 tools/tiktokauth.py login     브라우저로 인가 → 토큰 저장
    python3 tools/tiktokauth.py token     유효한 액세스 토큰 출력 (필요시 자동 갱신)
    python3 tools/tiktokauth.py status    만료까지 남은 시간

**본인 PC 에서 돌리세요.** 브라우저가 열려야 합니다.

틱톡에는 "키" 하나가 있는 게 아니라 셋이 따로 있습니다:

  Client Key / Secret   개발자 포털에서 복사합니다. 앱의 신분증입니다.
  Access Token          **포털에 없습니다.** 아래 login 으로 발급받습니다.
                        24시간 만료. uploadtiktok.py 가 쓰는 게 이겁니다.
  Refresh Token         액세스 토큰을 갱신하는 열쇠. 365일.

준비 (한 번만):
  1. https://developers.tiktok.com 에서 앱 생성
  2. **앱 종류를 Desktop 으로** 고르세요.
     Web 으로 고르면 리디렉션 URI 가 https 여야 해서 localhost 를 못 씁니다.
  3. Products 에 **Content Posting API** 추가, 스코프 `video.upload`
  4. Redirect URI 에 정확히 이걸 등록: http://localhost:8080/callback
  5. 포털의 Client key / Client secret 을 환경변수로:

     export TIKTOK_CLIENT_KEY='...'
     export TIKTOK_CLIENT_SECRET='...'
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / ".tiktok_token.json"

AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
REDIRECT = "http://localhost:8080/callback"
PORT = 8080
SCOPE = "video.upload"


def creds() -> tuple[str, str]:
    k = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
    s = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
    if not (k and s):
        print("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET 이 없습니다.\n"
              "개발자 포털 → 앱 → Basic information 에서 복사하세요.\n"
              "자세한 절차: python3 tools/tiktokauth.py --help", file=sys.stderr)
        sys.exit(1)
    return k, s


def form_post(body: dict) -> dict:
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(
        TOKEN, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} — "
                           f"{e.read().decode(errors='replace')[:500]}") from None


def save(tok: dict) -> None:
    tok["obtained_at"] = int(time.time())
    STORE.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    STORE.chmod(0o600)        # 계정 접근 권한입니다


def load() -> dict:
    if not STORE.exists():
        print("토큰이 없습니다 — python3 tools/tiktokauth.py login", file=sys.stderr)
        sys.exit(1)
    return json.loads(STORE.read_text(encoding="utf-8"))


def login() -> int:
    key, secret = creds()

    # PKCE. 틱톡은 code_challenge 를 **hex 인코딩** SHA256 으로 받습니다.
    # 표준(base64url)과 달라서, 표준대로 만들면 invalid_grant 가 납니다.
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = hashlib.sha256(verifier.encode()).hexdigest()
    state = secrets.token_urlsafe(16)

    url = AUTHORIZE + "?" + urllib.parse.urlencode({
        "client_key": key, "response_type": "code", "scope": SCOPE,
        "redirect_uri": REDIRECT, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})

    caught: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):                      # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            caught.update({k: v[0] for k, v in q.items()})
            ok = "code" in caught and caught.get("state") == state
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                ("<h2>인가 완료. 터미널로 돌아가세요.</h2>" if ok
                 else f"<h2>실패</h2><pre>{caught}</pre>").encode())

        def log_message(self, *a):             # 접속 로그 끄기
            pass

    srv = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=srv.handle_request, daemon=True).start()

    print(f"\n브라우저에서 이 주소를 여세요 (자동으로 안 열리면 복사해서):\n\n{url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    for _ in range(300):                       # 5분 대기
        if caught:
            break
        time.sleep(1)
    srv.server_close()

    if "code" not in caught:
        print(f"인가 코드를 못 받았습니다: {caught or '시간 초과'}", file=sys.stderr)
        return 1
    if caught.get("state") != state:
        print("state 불일치 — 요청을 버립니다 (CSRF 방지)", file=sys.stderr)
        return 1

    r = form_post({"client_key": key, "client_secret": secret,
                   "code": urllib.parse.unquote(caught["code"]),
                   "grant_type": "authorization_code",
                   "redirect_uri": REDIRECT, "code_verifier": verifier})
    if "access_token" not in r:
        print(f"토큰 교환 실패: {r}", file=sys.stderr)
        return 1
    save(r)
    print(f"\n토큰을 {STORE.name} 에 저장했습니다 (액세스 24시간 / 갱신 365일).")
    print("이제 바로 쓸 수 있습니다:\n  python3 tools/uploadtiktok.py TW01")
    return 0


def fresh_token() -> str:
    """유효한 액세스 토큰. 만료가 가까우면 알아서 갱신합니다."""
    tok = load()
    age = int(time.time()) - tok.get("obtained_at", 0)
    if age < tok.get("expires_in", 86400) - 300:
        return tok["access_token"]

    key, secret = creds()
    r = form_post({"client_key": key, "client_secret": secret,
                   "grant_type": "refresh_token",
                   "refresh_token": tok["refresh_token"]})
    if "access_token" not in r:
        raise RuntimeError(f"갱신 실패 — 다시 login 하세요: {r}")
    # 새 refresh_token 이 오면 반드시 그걸로 바꿔야 합니다 (공식 문서).
    save(r)
    return r["access_token"]


def status() -> int:
    tok = load()
    left = tok.get("expires_in", 86400) - (int(time.time()) - tok.get("obtained_at", 0))
    r_left = tok.get("refresh_expires_in", 0) - (int(time.time()) - tok.get("obtained_at", 0))
    print(f"  액세스 토큰: {'만료됨' if left <= 0 else f'{left // 3600}시간 {left % 3600 // 60}분 남음'}")
    print(f"  갱신 토큰:   {max(r_left, 0) // 86400}일 남음")
    print(f"  스코프:      {tok.get('scope', '?')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["login", "token", "status"])
    a = ap.parse_args()
    if a.action == "login":
        return login()
    if a.action == "status":
        return status()
    print(fresh_token())
    return 0


if __name__ == "__main__":
    sys.exit(main())
