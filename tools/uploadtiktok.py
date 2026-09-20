#!/usr/bin/env python3
"""uploadtiktok — 완성된 영상을 틱톡 초안함(inbox)으로 보냅니다.

    python3 tools/uploadtiktok.py CN01 --check      네트워크 없이 규격만 검사
    python3 tools/uploadtiktok.py CN01              초안함으로 전송
    python3 tools/uploadtiktok.py CN01 --status <publish_id>

**자동 게시가 아닙니다. 초안까지입니다.**
틱톡 앱 알림을 눌러 사람이 마무리해야 실제로 올라갑니다.

왜 초안까지만인가 — 틱톡 Content Posting API 는 두 갈래입니다:

  video.publish (Direct Post)  바로 공개 게시. 단, **심사를 통과하지 못한 앱이
                               올린 건 전부 SELF_ONLY(비공개)로 강제**됩니다.
                               심사는 몇 주 걸리고 동작 영상 제출이 필요합니다.
  video.upload  (Inbox)        크리에이터 초안함으로 보냄. 사람이 앱에서 마무리.
                               **심사 제한을 받지 않습니다.**

즉 심사 전에 Direct Post 를 쓰면 아무도 못 보는 비공개 영상만 쌓입니다.
그래서 이 도구는 video.upload 를 씁니다. 심사를 통과하면 그때
Direct Post 로 바꾸는 게 맞습니다.

토큰: tools/tiktokauth.py 가 발급·갱신하고 이 도구가 알아서 읽습니다.
    python3 tools/tiktokauth.py login    (최초 1회)
환경변수 TIKTOK_ACCESS_TOKEN 이 있으면 그걸 우선합니다.

제약 (공식 문서 기준):
  - 액세스 토큰당 분당 6요청
  - 24시간 내 대기 중인 공유 5건까지
  - upload_url 은 발급 후 1시간 유효
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claimctl import ROOT  # noqa: E402

API = "https://open.tiktokapis.com/v2"
BUILD = ROOT / "build"

# 단일 청크로 보낼 수 있는 상한. 이보다 크면 쪼개야 합니다.
MAX_SINGLE_CHUNK = 64 * 1024 * 1024
MIN_CHUNK = 5 * 1024 * 1024

# 틱톡이 받는 컨테이너 — 공식 문서: video/mp4, video/quicktime, video/webm
CONTENT_TYPE = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}


def probe(path: Path) -> dict:
    """ffprobe 로 영상 규격을 읽습니다."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,codec_name,r_frame_rate",
         "-show_entries", "format=duration,size", "-of", "json", str(path)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe 실패: {r.stderr.strip()[:200]}")
    d = json.loads(r.stdout)
    st, fmt = d["streams"][0], d["format"]
    num, den = (st.get("r_frame_rate") or "30/1").split("/")
    return {
        "w": st["width"], "h": st["height"], "codec": st["codec_name"],
        "fps": round(int(num) / max(int(den), 1), 2),
        "dur": float(fmt["duration"]), "size": int(fmt["size"]),
    }


def check(ep: str) -> tuple[Path, dict, list[str]]:
    """전송 전에 로컬에서 확인할 수 있는 것을 전부 확인합니다.

    네트워크를 타기 전에 걸러야 합니다 — 24시간에 5건 제한이 있어서
    잘못된 파일로 시도를 낭비하면 그날 다시 못 올립니다.
    """
    path = BUILD / ep / f"{ep}-draft.mp4"
    problems = []
    if not path.exists():
        return path, {}, [f"영상이 없습니다: {path.relative_to(ROOT)} "
                         f"— tools/render.py {ep} 를 먼저 돌리세요"]

    v = probe(path)
    if path.suffix.lower() not in CONTENT_TYPE:
        problems.append(f"지원하지 않는 컨테이너: {path.suffix}")
    if v["codec"] != "h264":
        problems.append(f"코덱이 h264 가 아닙니다: {v['codec']}")
    if v["h"] <= v["w"]:
        problems.append(f"세로 영상이 아닙니다: {v['w']}x{v['h']}")
    if v["dur"] > 600:
        problems.append(f"10분을 넘습니다: {v['dur']:.0f}초")

    meta = BUILD / ep / "metadata.md"
    if not meta.exists():
        problems.append("metadata.md 가 없습니다 — tools/produce.py 를 돌리세요")
    return path, v, problems


def caption(ep: str) -> str:
    """metadata.md 의 틱톡 캡션 블록을 읽습니다."""
    text = (BUILD / ep / "metadata.md").read_text(encoding="utf-8")
    after = text.split("## TikTok", 1)[-1]
    blocks = after.split("```")
    return blocks[1].strip() if len(blocks) > 1 else ""


def post(url: str, token: str, body: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        raise RuntimeError(f"HTTP {e.code} — {detail}") from None


def explain(err: dict) -> str:
    """틱톡 에러 코드를 사람 말로. 코드만 보고는 뭘 고쳐야 할지 모릅니다."""
    code = (err or {}).get("code", "")
    hints = {
        "spam_risk_too_many_posts": "24시간 내 대기 공유 5건 한도에 걸렸습니다.",
        "spam_risk_user_banned_from_posting": "계정이 게시 제한 상태입니다.",
        "reached_active_user_cap": "심사 전 앱은 24시간에 5명까지만 올릴 수 있습니다.",
        "unaudited_client_can_only_post_to_private_accounts":
            "심사를 통과하지 못한 앱입니다. 이 도구는 초안함(video.upload)을 쓰므로 "
            "이 오류가 나면 스코프가 video.publish 로 잘못 잡힌 것입니다.",
        "access_token_invalid": "토큰이 만료됐거나 잘못됐습니다. 다시 발급하세요.",
        "scope_not_authorized": "video.upload 스코프가 승인되지 않았습니다.",
        "rate_limit_exceeded": "분당 6요청 한도입니다. 잠시 후 다시.",
    }
    return hints.get(code, "")


def upload(ep: str, token: str) -> int:
    path, v, problems = check(ep)
    if problems:
        for p in problems:
            print(f"  ! {p}", file=sys.stderr)
        return 1

    size = v["size"]
    if size <= MAX_SINGLE_CHUNK:
        chunk, count = size, 1        # 한 덩어리로 보냅니다
    else:
        chunk = MAX_SINGLE_CHUNK
        count = (size + chunk - 1) // chunk
        if chunk < MIN_CHUNK:
            print("  ! 청크가 5MB 미만입니다", file=sys.stderr)
            return 1

    print(f"  {path.name}  {size / 1024 / 1024:.1f}MB  {v['dur']:.1f}초  "
          f"{v['w']}x{v['h']}  청크 {count}개")

    r = post(f"{API}/post/publish/inbox/video/init/", token,
             {"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                              "chunk_size": chunk, "total_chunk_count": count}})
    err = r.get("error") or {}
    if err.get("code") not in (None, "ok"):
        print(f"  ! init 실패: {err.get('code')} — {err.get('message')}", file=sys.stderr)
        if (h := explain(err)):
            print(f"    {h}", file=sys.stderr)
        return 1

    data = r["data"]
    publish_id, upload_url = data["publish_id"], data["upload_url"]
    print(f"  publish_id: {publish_id}")

    blob = path.read_bytes()
    ctype = CONTENT_TYPE[path.suffix.lower()]
    for i in range(count):
        lo = i * chunk
        hi = min(lo + chunk, size) - 1
        part = blob[lo:hi + 1]
        req = urllib.request.Request(
            upload_url, data=part, method="PUT",
            headers={"Content-Range": f"bytes {lo}-{hi}/{size}",
                     "Content-Length": str(len(part)),
                     "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            print(f"  ! 청크 {i + 1}/{count} 전송 실패: HTTP {e.code} "
                  f"{e.read().decode(errors='replace')[:300]}", file=sys.stderr)
            return 1
        print(f"  전송 {i + 1}/{count}")

    print(f"\n  초안함으로 보냈습니다.")
    print(f"  **틱톡 앱 알림을 눌러 직접 마무리해야 올라갑니다.**")
    print(f"\n  캡션(앱에 붙여 넣으세요):\n  {caption(ep)}")
    print(f"\n  상태 확인: python3 tools/uploadtiktok.py {ep} --status {publish_id}")
    return 0


def status(token: str, publish_id: str) -> int:
    r = post(f"{API}/post/publish/status/fetch/", token, {"publish_id": publish_id})
    err = r.get("error") or {}
    if err.get("code") not in (None, "ok"):
        print(f"  ! {err.get('code')} — {err.get('message')}", file=sys.stderr)
        return 1
    d = r.get("data", {})
    print(f"  상태: {d.get('status')}")
    if d.get("fail_reason"):
        print(f"  실패 사유: {d['fail_reason']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--check", action="store_true",
                    help="네트워크 없이 규격·메타데이터만 검사")
    ap.add_argument("--status", metavar="PUBLISH_ID")
    a = ap.parse_args()

    if a.check:
        path, v, problems = check(a.episode)
        if problems:
            for p in problems:
                print(f"  ! {p}", file=sys.stderr)
            return 1
        print(f"  {path.relative_to(ROOT)}")
        print(f"  {v['w']}x{v['h']}  {v['codec']}  {v['fps']}fps  "
              f"{v['dur']:.1f}초  {v['size'] / 1024 / 1024:.1f}MB")
        print(f"  캡션: {caption(a.episode)}")
        print(f"\n  규격 통과. 전송하려면 --check 를 빼고 다시 돌리세요.")
        return 0

    # 저장된 토큰을 먼저 봅니다 — 만료가 가까우면 알아서 갱신합니다.
    # 액세스 토큰은 24시간이라 환경변수에 박아 두면 매일 끊깁니다.
    token = os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
    if not token:
        try:
            from tiktokauth import fresh_token
            token = fresh_token()
        except SystemExit:
            return 1
        except Exception as e:
            print(f"토큰을 얻지 못했습니다: {e}\n"
                  "  python3 tools/tiktokauth.py login\n"
                  "  자세한 절차: docs/15-upload-automation.md", file=sys.stderr)
            return 1
    if a.status:
        return status(token, a.status)
    return upload(a.episode, token)


if __name__ == "__main__":
    sys.exit(main())
