#!/usr/bin/env python3
"""render — 제작 패키지로 자막 영상 초안을 만듭니다.

    python3 tools/render.py EP001              무음 자막 초안
    python3 tools/render.py EP001 --audio n.wav   녹음 얹기
    python3 tools/render.py --all

produce.py 가 만든 SRT 와 샷리스트를 받아 1080x1920 영상을 조립합니다.
**완성본이 아니라 초안입니다** — 자료 화면(화석 사진, 그래프)은 사람이 얹어야 합니다.
이 도구가 보장하는 것은 브랜드 규격입니다: 자막 크기·안전영역·출처 하단바·색 규칙.

필요: ffmpeg, Pretendard Bold (~/.fonts/)
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claimctl import ROOT, SCRIPTS, parse_script  # noqa: E402

BUILD = ROOT / "build"
W, H = 1080, 1920

# docs/02-brand.md §3
INK, PAPER, EVID, CLAIM, ACCENT = "0x12151A", "0xF5F3EE", "0x2E7D6B", "0xB4472F", "0xE0A800"
# 안전영역 — docs/04-platform-playbook.md §2
TOP_SAFE, BOTTOM_SAFE = int(H * 0.12), int(H * 0.20)
SUB_SIZE = 62          # 56px 하한 + 여유
SRC_SIZE = 30


VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
# 자료 화면 위에 까는 어둠막 — 흰 자막이 밝은 사진 위에서도 읽히게 합니다.
# 자막 블록 주변만 덮습니다. 너무 높으면 자료 화면 내용을 가립니다.
SCRIM_TOP = 0.58
FADE_IN = 0.18        # 자막 페이드인 시간(초)


def load_shots(ep: str) -> list[dict]:
    """assets/<EP>/shots.yaml 에서 file 이 채워진 항목만."""
    f = ROOT / "assets" / ep / "shots.yaml"
    if not f.exists():
        return []
    doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    out = []
    for s in doc.get("shots") or []:
        if not s.get("file"):
            continue
        path = (ROOT / s["file"]).resolve()
        if not path.exists():
            print(f"  ! 자료 화면 없음: {s['file']} (큐 {s.get('cue')})", file=sys.stderr)
            continue
        out.append({**s, "path": path})
    return out


def font_path() -> str | None:
    for p in (Path.home() / ".fonts/Pretendard-Bold.otf",
              Path("/usr/share/fonts/opentype/pretendard/Pretendard-Bold.otf")):
        if p.exists():
            return str(p)
    return None


def srt_time_to_sec(s: str) -> float:
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def parse_srt(path: Path) -> list[dict]:
    out = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        a, b = lines[1].split(" --> ")
        out.append({"n": int(lines[0]), "start": srt_time_to_sec(a),
                    "end": srt_time_to_sec(b), "text": "\n".join(lines[2:])})
    return out


class TextStore:
    """drawtext 의 text= 는 콜론·따옴표·쉼표를 모두 해석해 이스케이프가 까다롭습니다.
    textfile= 로 넘기면 내용이 그대로 전달되므로 이 문제가 사라집니다."""

    def __init__(self, base: Path):
        self.dir = base / ".text"
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True)
        self.n = 0

    def put(self, s: str) -> str:
        self.n += 1
        f = self.dir / f"{self.n:04d}.txt"
        f.write_text(s, encoding="utf-8")
        return str(f)


def cue_marked(script_body: str) -> dict[int, str]:
    """큐 번호 -> **강조**가 보존된 텍스트.

    SRT 는 편집 프로그램에서 쓰라고 깨끗하게 유지하므로, 강조 정보는 대본에서 직접 읽습니다.
    """
    n, out = 0, {}
    for line in script_body.split("\n---\n")[0].split("\n"):
        s = line.strip()
        if not s or s.startswith(("#", ">", "```", "|", "-")):
            continue
        n += 1
        s = re.sub(r"\[S-[A-Z0-9\-]+\]", "", s)
        s = re.sub(r"`(.+?)`", r"\1", s)
        s = re.sub(r"\s+", " ", s).strip()
        out[n] = re.sub(r"\s+([.,!?%）\)])", r"\1", s)
    return out


def cue_sections(script_body: str) -> dict[int, str]:
    """큐 번호 -> 섹션명. 섹션에 따라 자막 색을 바꿉니다 (MYTH 는 --claim)."""
    sec, n, out = "?", 0, {}
    for line in script_body.split("\n---\n")[0].split("\n"):
        s = line.strip()
        if s.startswith("## "):
            sec = s[3:].split("(")[0].strip()
        elif s and not s.startswith(("#", ">", "```", "|", "-")):
            n += 1
            out[n] = sec
    return out


SIDE_MARGIN = 64
LINE_GAP = 16


_metrics: dict[str, float] | None = None


def _load_metrics(font: str) -> dict[str, float]:
    """폰트에서 글자별 실제 advance width 를 읽습니다 (em 단위).

    추정값으로는 강조 색을 나눠 그릴 때 위치가 어긋납니다. 한글을 1.0em 으로
    잡았더니 실제는 0.864 여서 어절 간격이 눈에 띄게 벌어졌습니다.
    """
    global _metrics
    if _metrics is not None:
        return _metrics
    try:
        from fontTools.ttLib import TTFont
        f = TTFont(font, lazy=True)
        upm = f["head"].unitsPerEm
        hmtx, cmap = f["hmtx"], f.getBestCmap()
        _metrics = {"__upm__": upm, "__cmap__": cmap, "__hmtx__": hmtx}
    except Exception:
        _metrics = {}
    return _metrics


def text_width_em(s: str, font: str | None = None) -> float:
    """글자 폭을 em 단위로. 폰트 메트릭을 읽을 수 있으면 실측, 아니면 근사."""
    s = s.replace("**", "")
    m = _load_metrics(font) if font else (_metrics or {})
    if m.get("__cmap__"):
        upm, cmap, hmtx = m["__upm__"], m["__cmap__"], m["__hmtx__"]
        total = 0.0
        for ch in s:
            g = cmap.get(ord(ch))
            total += (hmtx[g][0] / upm) if g else 0.86
        return total
    w = 0.0
    for ch in s:
        w += 1.0 if "\uac00" <= ch <= "\ud7a3" else (0.3 if ch == " " else
                                                      0.55 if ch.isascii() else 1.0)
    return w


def wrap_masked(text: str, mask: list[bool], size: int) -> list[tuple[str, list[bool]]]:
    """어절 단위로 줄을 나누되 강조 마스크도 같이 잘라 옮깁니다."""
    budget = (W - 2 * SIDE_MARGIN) / size
    lines: list[tuple[str, list[bool]]] = []
    cur, cur_mask, pos = "", [], 0
    for word in text.split(" "):
        wlen = len(word)
        wmask = mask[pos:pos + wlen]
        pos += wlen + 1          # 공백 한 칸
        if not word:
            continue
        trial = f"{cur} {word}".strip()
        if text_width_em(trial) <= budget or not cur:
            if cur:
                cur, cur_mask = cur + " " + word, cur_mask + [False] + wmask
            else:
                cur, cur_mask = word, wmask
        else:
            lines.append((cur, cur_mask))
            cur, cur_mask = word, wmask
    if cur:
        lines.append((cur, cur_mask))
    return lines or [("", [])]


def wrap(text: str, size: int) -> list[str]:
    """drawtext 는 자동 줄바꿈을 하지 않으므로 직접 끊습니다.

    한국어는 어절 단위로 끊어야 읽힙니다. 한 어절이 한 줄을 넘으면 그때만 글자로 쪼갭니다.
    """
    budget = (W - 2 * SIDE_MARGIN) / size
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if text_width_em(trial) <= budget or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def build_overlays(shots: list[dict]) -> tuple[list[str], str, str]:
    """자료 화면을 배경 위에 겹치는 필터 체인.

    반환: (ffmpeg 입력 인자, 필터 체인, 마지막 라벨)
    각 자료는 1080x1920 에 맞춰 cover(잘라내기) 또는 contain(레터박스)으로 정규화한 뒤,
    해당 큐 구간에만 overlay 합니다.
    """
    inputs, chain, last = [], [], "[bg]"
    for i, s in enumerate(shots):
        is_video = s["path"].suffix.lower() in VIDEO_EXT
        dur = float(s["until"]) - float(s["at"])
        if is_video:
            inputs += ["-i", str(s["path"])]
        else:
            inputs += ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(s["path"])]
        src = f"[{i + 2}:v]"   # 0=배경, 1=무음/오디오
        lbl = f"[a{i}]"
        # 켄번스 — 정지 이미지를 아주 천천히 확대합니다.
        # 움직임이 없으면 시청자는 "멈춘 줄" 알고 이탈합니다.
        kb = ""
        if not is_video and s.get("kenburns", True):
            frames = max(int(dur * 30), 1)
            kb = (f",zoompan=z='min(zoom+0.0006,1.10)':d={frames}"
                  f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30")
        if s.get("fit", "cover") == "contain":
            fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                   f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={EVID.replace('0x', '#')}")
        else:
            fit = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                   f"crop={W}:{H}")
        # 하단에서 위로 올라가는 어둠막 — 자막 가독성 확보
        chain.append(f"{src}{fit}{kb},setsar=1{lbl}")
        out = f"[v{i}]"
        chain.append(f"{last}{lbl}overlay=0:0:enable='between(t,{float(s['at']):.2f},"
                     f"{float(s['until']):.2f})'{out}")
        last = out
    return inputs, ";".join(chain), last


EMPH = re.compile(r"\*\*(.+?)\*\*")


def strip_emphasis(s: str) -> tuple[str, list[bool]]:
    """**강조** 표시를 떼고, 문자별 강조 여부 마스크를 함께 반환합니다.

    강조가 줄바꿈을 걸치면 한 줄 안에서 ** 짝을 찾을 수 없으므로,
    줄을 나누기 **전에** 마스크를 만들어 두고 나중에 줄별로 잘라 씁니다.
    """
    plain, mask, i, emph = [], [], 0, False
    while i < len(s):
        if s.startswith("**", i):
            emph = not emph
            i += 2
            continue
        plain.append(s[i])
        mask.append(emph)
        i += 1
    return "".join(plain), mask


def segments_from_mask(line: str, mask: list[bool]) -> list[tuple[str, bool]]:
    """(텍스트, 마스크) 를 색이 같은 구간들로 묶습니다."""
    out: list[tuple[str, bool]] = []
    for ch, em in zip(line, mask):
        if out and out[-1][1] == em:
            out[-1] = (out[-1][0] + ch, em)
        else:
            out.append((ch, em))
    return out or [(line, False)]


def build_filters(cues: list[dict], sections: dict[int, str], sources: dict[int, str],
                  font: str, store: "TextStore", marked: dict[int, str] | None = None) -> str:
    """자막 + 출처바를 drawtext 체인으로.

    아래에서부터: [하단 안전영역 384px 비움] → [자막 블록] → [출처바]
    출처바를 자막 위에 둡니다. 안전영역 안에 넣으면 플랫폼 UI 가 덮습니다.
    """
    parts = []
    for c in cues:
        between = f"between(t,{c['start']:.2f},{c['end']:.2f})"
        sec = sections.get(c["n"], "")
        # MYTH 섹션은 창조론 주장 인용이므로 --claim 색 (docs/02 §3)
        color = CLAIM if "MYTH" in sec.upper() else PAPER
        # 자막이 툭 나타나면 싸구려로 보입니다. 짧은 페이드인을 줍니다.
        fade = (f"if(lt(t,{c['start']:.2f}),0,"
                f"min(1,(t-{c['start']:.2f})/{FADE_IN}))")
        raw = (marked or {}).get(c["n"]) or c["text"]
        plain, mask = strip_emphasis(raw.replace("\n", " "))
        wrapped = wrap_masked(plain, mask, SUB_SIZE)
        block_h = len(wrapped) * SUB_SIZE + (len(wrapped) - 1) * LINE_GAP
        top = H - BOTTOM_SAFE - block_h

        for i, (line, lmask) in enumerate(wrapped):
            y = top + i * (SUB_SIZE + LINE_GAP)
            segs = segments_from_mask(line, lmask)
            total = sum(text_width_em(s) for s, _ in segs) * SUB_SIZE
            x = (W - total) / 2
            for seg, is_em in segs:
                if seg.strip():
                    parts.append(
                        f"drawtext=fontfile='{font}':textfile='{store.put(seg)}'"
                        f":fontcolor={ACCENT if is_em else color}:fontsize={SUB_SIZE}"
                        f":x={x:.0f}:y={y}:alpha='{fade}'"
                        f":borderw=6:bordercolor={INK}@0.9:enable='{between}'")
                x += text_width_em(seg) * SUB_SIZE

        if src := sources.get(c["n"]):
            parts.append(
                f"drawtext=fontfile='{font}':textfile='{store.put(src)}':fontcolor={PAPER}@0.8"
                f":fontsize={SRC_SIZE}:x=(w-text_w)/2:y={top - SRC_SIZE - 34}"
                f":box=1:boxcolor={INK}@0.55:boxborderw=14:enable='{between}'")
    return ",".join(parts)


def render(ep: str, audio: Path | None, quiet: bool = False) -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg 가 필요합니다: apt-get install ffmpeg", file=sys.stderr)
        return 1
    font = font_path()
    if not font:
        print("Pretendard Bold 를 ~/.fonts/ 에 두세요 — docs/02-brand.md §3", file=sys.stderr)
        return 1

    out = BUILD / ep
    srt = out / f"{ep}.srt"
    if not srt.exists():
        print(f"먼저 `produce.py {ep}` 를 실행하세요", file=sys.stderr)
        return 1

    matches = [p for p in SCRIPTS.glob(f"{ep}*.md") if not p.name.startswith("_")]
    fm, body = parse_script(matches[0])
    _load_metrics(font)
    cues = parse_srt(srt)
    sections = cue_sections(body)
    marked = cue_marked(body)

    # 큐별 출처 문자열 — refcheck 가 검증한 서지에서
    refs = {r["id"]: r for r in yaml.safe_load(
        (ROOT / "content" / "references.yaml").read_text(encoding="utf-8"))["references"]}
    sources: dict[int, str] = {}
    n = 0
    for line in body.split("\n---\n")[0].split("\n"):
        s = line.strip()
        if s.startswith("## ") or not s or s.startswith(("#", ">", "```", "|", "-")):
            continue
        n += 1
        if ids := re.findall(r"\[(S-[A-Z0-9\-]+)\]", s):
            r = refs.get(ids[0], {})
            v = r.get("verified") or {}
            sources[n] = (f"{v['container']} {v['year']}  {r.get('doi','')}"
                          if v.get("status") == "ok" else ids[0])

    dur = cues[-1]["end"] + 1.0 if cues else 5.0
    dst = out / f"{ep}-draft.mp4"
    store = TextStore(out)
    shots = load_shots(ep)
    shot_inputs, overlay_chain, last = build_overlays(shots)

    # 어둠막은 **자료 화면이 깔린 구간에만** 적용합니다.
    # 자료 없는 컷은 단색 배경이라 어둠막이 불필요하고, 브랜드 색을 흐립니다.
    scrim = ""
    if shots:
        cond = "+".join(f"between(t,{float(s['at']):.2f},{float(s['until']):.2f})"
                        for s in shots)
        scrim = (f";{last}drawbox=0:{int(H * SCRIM_TOP)}:{W}:{H - int(H * SCRIM_TOP)}:"
                 f"{INK}@0.6:t=fill:enable='{cond}'[s]")
        last = "[s]"

    vf = (f"[0:v]null[bg]"
          + (f";{overlay_chain}" if overlay_chain else "")
          + scrim
          + f";{last}" + build_filters(cues, sections, sources, font, store, marked) + "[out]")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", f"color=c={EVID.replace('0x','#')}:s={W}x{H}:d={dur:.2f}:r=30"]
    if audio:
        cmd += ["-i", str(audio)]
    else:
        # 무음 트랙 — 플랫폼이 오디오 없는 파일을 거르는 경우가 있음
        cmd += ["-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={dur:.2f}"]
    cmd += shot_inputs

    vf_file = out / ".filter.txt"
    vf_file.write_text(vf, encoding="utf-8")
    cmd += ["-filter_complex_script", str(vf_file),
            "-map", "[out]", "-map", "1:a",
            "-c:a", "aac", "-b:a", "384k", "-ar", "48000",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-b:v", "8M", "-g", "60", "-t", f"{dur:.2f}",
            "-movflags", "+faststart", str(dst)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ffmpeg 실패: {r.stderr.strip()[:400]}", file=sys.stderr)
        return 1
    shutil.rmtree(store.dir, ignore_errors=True)
    vf_file.unlink(missing_ok=True)
    if not quiet:
        mb = dst.stat().st_size / 1024 / 1024
        print(f"  {ep}-draft.mp4  {dur:.1f}초  {mb:.1f}MB  큐 {len(cues)}개"
              f"  자료화면 {len(shots)}컷  출처자막 {len(sources)}컷"
              + ("  (음성 포함)" if audio else "  (무음)"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--audio", type=Path, help="녹음 파일을 얹습니다")
    args = ap.parse_args()

    if args.all:
        eps = sorted({p.name.split("-")[0] for p in SCRIPTS.glob("*.md")
                      if not p.name.startswith("_")})
        print(f"자막 영상 초안 렌더 — {len(eps)}편\n")
        rc = 0
        for e in eps:
            rc |= render(e, None)
        return rc
    if not args.episode:
        ap.error("episode 를 지정하거나 --all 을 쓰세요")
    return render(args.episode, args.audio)


if __name__ == "__main__":
    sys.exit(main())
