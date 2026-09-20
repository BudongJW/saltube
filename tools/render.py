#!/usr/bin/env python3
"""render — 제작 패키지로 자막 영상 초안을 만듭니다.

    python3 tools/render.py EP001              tts.py 음성이 있으면 자동으로 얹음
    python3 tools/render.py EP001 --audio n.wav   다른 녹음을 대신 얹기
    python3 tools/render.py --all

produce.py 가 만든 SRT 와 샷리스트를 받아 1080x1920 영상을 조립합니다.
**완성본이 아니라 초안입니다** — 자료 화면(화석 사진, 그래프)은 사람이 얹어야 합니다.
이 도구가 보장하는 것은 브랜드 규격입니다: 자막 크기·안전영역·출처 하단바·색 규칙.

필요: ffmpeg, Pretendard Bold (~/.fonts/)
"""
from __future__ import annotations

import argparse
import json
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
# 라우드니스 — docs/04-platform-playbook.md §2
# 플랫폼은 초과분만 낮추고 미달분은 올려주지 않습니다. 조용하면 조용한 채로 나갑니다.
LOUDNESS_I, LOUDNESS_TP, LOUDNESS_LRA = -14, -1, 11


def measured_loudness(video: Path) -> float | None:
    """완성된 파일의 실제 라우드니스. 지정값과 결과는 자주 어긋납니다."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", str(video),
             "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300)
        m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", r.stderr)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def loudnorm_filter(audio: Path, quiet: bool = False) -> str:
    """loudnorm 을 2패스로 씁니다 — 1패스로 재고, 그 측정값을 넣어 보정합니다.

    1패스(동적 모드)는 실시간으로 눌러가며 맞추는 방식이라 목표에서 몇 dB 씩
    빗나갑니다. CN01 은 -14 를 지정했는데 실제 결과가 -17.3 LUFS 였습니다.
    3dB 낮으면 다른 채널 영상 사이에서 확연히 작게 들립니다 —
    플랫폼은 초과분만 낮추고 **미달분은 올려주지 않습니다**.

    측정에 실패하면 1패스 필터로 조용히 되돌아갑니다 (없는 것보단 낫습니다).
    """
    # 크레스트 팩터를 먼저 낮춥니다.
    # 진성 피크가 -1 dBTP 로 묶여 있으면 도달 가능한 최대 라우드니스는
    # (피크 - 크레스트) 입니다. CN01 원본은 -26.08 LUFS 에 피크 -2.41 dBTP,
    # 크레스트가 23.7dB 라서 아무리 올려도 -24.7 LUFS 가 한계였습니다.
    # 임계값은 신호 본체(-26 LUFS 근처)보다 아래에 둬야 실제로 걸립니다 —
    # -20dB 로 잡았더니 본체가 임계 아래라 컴프레서가 거의 동작하지 않았습니다.
    comp = "acompressor=threshold=-30dB:ratio=4:attack=5:release=80"
    base = f"{comp},loudnorm=I={LOUDNESS_I}:TP={LOUDNESS_TP}:LRA={LOUDNESS_LRA}"
    try:
        r = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", str(audio),
             "-af", f"{base}:print_format=json", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300)
        blob = r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1]
        m = json.loads(blob)
        measured = ":".join(
            f"measured_{k}={m[f'input_{k}']}" for k in ("i", "tp", "lra", "thresh"))
        if not quiet:
            print(f"  음량: {m['input_i']} LUFS → 목표 {LOUDNESS_I} LUFS "
                  f"(2패스, 피크 {m['input_tp']} dBTP)")
        # linear=true 로 전체를 같은 양만큼 올립니다. 목표에 못 미치면
        # ffmpeg 가 알아서 동적 모드로 내려갑니다.
        return f"{base}:{measured}:offset={m['target_offset']}:linear=true"
    except Exception as e:
        print(f"  ! 음량 측정 실패({type(e).__name__}) — 1패스로 진행합니다",
              file=sys.stderr)
        return base


def load_shots(ep: str, cues: list[dict]) -> list[dict]:
    """assets/<EP>/shots.yaml 에서 file 이 채워진 항목만.

    **타이밍은 shots.yaml 이 아니라 현재 SRT 에서 큐 번호로 찾습니다.**
    shots.yaml 의 at/until 은 produce.py 가 음절 추정으로 쓴 값이라,
    tts.py 가 SRT 를 실측으로 다시 쓰고 나면 최대 몇 초씩 어긋납니다.
    실제로 EP001 에서 2.6초 어긋나 자료 화면이 엉뚱한 자막에 붙었습니다.
    """
    f = ROOT / "assets" / ep / "shots.yaml"
    if not f.exists():
        return []
    by_cue = {c["n"]: c for c in cues}
    doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    out = []
    for s in doc.get("shots") or []:
        if not s.get("file"):
            continue
        path = (ROOT / s["file"]).resolve()
        if not path.exists():
            print(f"  ! 자료 화면 없음: {s['file']} (큐 {s.get('cue')})", file=sys.stderr)
            continue
        cue = by_cue.get(s.get("cue"))
        if not cue:
            print(f"  ! 큐 {s.get('cue')} 가 현재 대본에 없습니다 — "
                  f"대본이 바뀌었다면 shots.yaml 을 다시 만드세요", file=sys.stderr)
            continue
        # 큐 번호는 살아 있는데 그 자리의 자막이 바뀐 경우.
        # 번호만 보면 멀쩡해 보여서 엉뚱한 자막 위에 그림이 깔립니다.
        # CN01 에서 Nature 도식이 교육부 대사 위에 깔린 걸 이 검사로 잡았습니다.
        pinned = (s.get("line") or "").strip()
        if pinned and pinned != cue["text"].strip():
            moved = next((n for n, c in by_cue.items()
                          if c["text"].strip() == pinned), None)
            where = f"지금은 큐 {moved} 에 있습니다" if moved else "지금 대본에 없습니다"
            print(f"  ! 큐 {s['cue']} 의 자막이 바뀌었습니다 — 이 컷은 "
                  f"\"{pinned[:24]}\" 에 붙어 있었고 {where}.\n"
                  f"    (화면: {s.get('screen', '')[:40]}) "
                  f"shots.yaml 의 cue 를 고치세요", file=sys.stderr)
        out.append({**s, "path": path, "at": cue["start"], "until": cue["end"]})
    return out


# 언어별 폰트. Pretendard 는 한자를 전혀 커버하지 못합니다.
FONT_BY_LANG = {
    "ko-KR": ["Pretendard-Bold.otf"],
    "zh-CN": ["NotoSansSC-Bold.otf"],
}


def font_path(lang: str = "ko-KR") -> str | None:
    names = FONT_BY_LANG.get(lang, FONT_BY_LANG["ko-KR"])
    for n in names:
        for base in (Path.home() / ".fonts", Path("/usr/share/fonts/opentype")):
            p = base / n
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
        w += 1.0 if ("\uac00" <= ch <= "\ud7a3" or "\u4e00" <= ch <= "\u9fff") else (
            0.3 if ch == " " else 0.55 if ch.isascii() else 1.0)
    return w


# 줄 끝에 올 수 없는 문장부호 — 중국어/일본어 금칙문자(禁則文字).
NO_LINE_START = "。，、；：？！）】》」』%…·"
# 금칙문자를 여백 쪽으로 내밀 수 있는 한도. 좌우 여백(64px)보다 작게 잡아
# 화면 밖으로 잘리는 일이 없게 합니다.
HANG_EM = 0.6


def _chunk_word(word: str, mask: list[bool], budget: float,
                room: float) -> list[tuple[str, list[bool]]]:
    """한 줄보다 긴 덩어리를 글자 단위로 쪼갭니다.

    중국어에는 띄어쓰기가 없어서 문장 하나가 통째로 한 '어절'이 됩니다.
    예전에는 이걸 그대로 한 줄에 넣어서 화면 밖으로 흘러넘쳤습니다.
    room 은 현재 줄에 남은 폭이고, 두 번째 조각부터는 budget 을 다 씁니다.
    """
    out: list[tuple[str, list[bool]]] = []
    cur, cur_mask, avail = "", [], room
    for i, ch in enumerate(word):
        trial = cur + ch
        if cur and text_width_em(trial) > avail:
            if ch in NO_LINE_START:
                # 금칙문자는 다음 줄 첫 글자로 보내지 않습니다.
                # 여백 안쪽(HANG)으로 조금 내밀 수 있으면 그대로 매달고,
                # 그것도 넘치면 앞 글자를 같이 내려서 둘이 함께 줄을 바꿉니다.
                if text_width_em(trial) <= avail + HANG_EM:
                    cur, cur_mask = trial, cur_mask + [mask[i]]
                    continue
                out.append((cur[:-1], cur_mask[:-1]))
                cur, cur_mask, avail = cur[-1] + ch, cur_mask[-1:] + [mask[i]], budget
                continue
            out.append((cur, cur_mask))
            cur, cur_mask, avail = ch, [mask[i]], budget
        else:
            cur, cur_mask = trial, cur_mask + [mask[i]]
    if cur:
        out.append((cur, cur_mask))
    return out


def wrap_masked(text: str, mask: list[bool], size: int) -> list[tuple[str, list[bool]]]:
    """어절 단위로 줄을 나누되 강조 마스크도 같이 잘라 옮깁니다.

    한 어절이 한 줄에 안 들어가면 그때만 글자 단위로 쪼갭니다 (_chunk_word).
    """
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
        if text_width_em(trial) <= budget:
            if cur:
                cur, cur_mask = cur + " " + word, cur_mask + [False] + wmask
            else:
                cur, cur_mask = word, wmask
        elif text_width_em(word) > budget:
            # 어절 자체가 한 줄보다 김 — 현재 줄 남은 자리부터 이어 쪼갭니다.
            sep = 1 if cur else 0
            room = budget - text_width_em(cur) - (text_width_em(" ") if sep else 0)
            pieces = _chunk_word(word, wmask, budget, max(room, 0.0))
            head, head_mask = pieces[0]
            if cur and room > 0 and head:
                lines.append((cur + " " + head, cur_mask + [False] + head_mask))
            else:
                if cur:
                    lines.append((cur, cur_mask))
                lines.append((head, head_mask))
            for piece, pmask in pieces[1:-1]:
                lines.append((piece, pmask))
            cur, cur_mask = pieces[-1] if len(pieces) > 1 else ("", [])
        else:
            lines.append((cur, cur_mask))
            cur, cur_mask = word, wmask
    if cur:
        lines.append((cur, cur_mask))
    return lines or [("", [])]


def wrap(text: str, size: int) -> list[str]:
    """drawtext 는 자동 줄바꿈을 하지 않으므로 직접 끊습니다."""
    return [ln for ln, _ in wrap_masked(text, [False] * len(text), size)]


def coalesce_shots(shots: list[dict]) -> list[dict]:
    """같은 파일이 연달아 붙은 큐를 한 컷으로 합칩니다.

    한 도식을 여러 줄에 걸쳐 보여줄 때 큐마다 따로 overlay 하면 경계에서
    켄번스 확대가 처음으로 되감겨 화면이 튑니다. 이어 붙여야 한 번에
    천천히 확대됩니다.
    """
    out: list[dict] = []
    for s in sorted(shots, key=lambda x: float(x["at"])):
        prev = out[-1] if out else None
        same = (prev and prev["path"] == s["path"]
                and prev.get("fit", "cover") == s.get("fit", "cover")
                and abs(float(prev["until"]) - float(s["at"])) < 0.25)
        if same:
            prev["until"] = s["until"]
        else:
            out.append(dict(s))
    return out


def build_overlays(shots: list[dict]) -> tuple[list[str], str, str]:
    """자료 화면을 배경 위에 겹치는 필터 체인.

    반환: (ffmpeg 입력 인자, 필터 체인, 마지막 라벨)
    각 자료는 1080x1920 에 맞춰 cover(잘라내기) 또는 contain(레터박스)으로 정규화한 뒤,
    해당 큐 구간에만 overlay 합니다.
    """
    shots = coalesce_shots(shots)
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
    matches0 = [p for p in SCRIPTS.glob(f"{ep}*.md") if not p.name.startswith("_")]
    lang = (parse_script(matches0[0])[0].get("lang") if matches0 else None) or "ko-KR"
    font = font_path(lang)
    if not font:
        need = ", ".join(FONT_BY_LANG.get(lang, []))
        print(f"{lang} 용 폰트({need})를 ~/.fonts/ 에 두세요 — docs/02-brand.md §3",
              file=sys.stderr)
        return 1

    out = BUILD / ep
    # tts.py 가 만들어 둔 음성을 자동으로 얹습니다.
    # --audio 를 빼먹어서 무음 영상을 완성본으로 착각한 적이 있습니다.
    if audio is None:
        tts_mp3 = out / f"{ep}.mp3"
        if tts_mp3.exists():
            audio = tts_mp3
            if not quiet:
                print(f"  음성: {tts_mp3.relative_to(ROOT)} (자동)")
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
    shots = load_shots(ep, cues)
    shot_inputs, overlay_chain, last = build_overlays(shots)

    # 어둠막은 **항상** 깝니다. 예전엔 자료 화면이 있는 구간에만 깔았는데,
    # 두 가지가 깨졌습니다:
    #  1) MYTH 컷의 `--claim` 빨강이 브랜드 초록 위에 얹히면 거의 안 읽힙니다.
    #     (EP001 17초 "이런 요구를 떠받치는…" — 빨강 #B4472F 에 초록 #2E7D6B)
    #  2) 자막 배경이 컷마다 초록↔어두움으로 깜빡여 싸구려로 보입니다.
    # 자료 화면은 어차피 어둠막 윗쪽(SCRIM_TOP 위)에 있으므로 가려지지 않습니다.
    scrim = (f";{last}drawbox=0:{int(H * SCRIM_TOP)}:{W}:{H - int(H * SCRIM_TOP)}:"
             f"{INK}@0.6:t=fill[s]")
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
    # 음성 정규화 + 스테레오. 모노로 내보내면 일부 플레이어에서 한쪽으로 치우칩니다.
    af = (f"{loudnorm_filter(audio, quiet)},"
          f"aformat=channel_layouts=stereo,aresample=48000")
    cmd += ["-filter_complex_script", str(vf_file),
            "-map", "[out]", "-map", "1:a", "-af", af,
            "-c:a", "aac", "-b:a", "384k", "-ar", "48000", "-ac", "2",
            # CRF + 상한. 예전엔 -b:v 8M 고정이었는데, 이 채널 화면은 대부분
            # 단색 도식이라 그 비트레이트가 통째로 낭비됐습니다 (41초에 37MB).
            # CRF 18 은 이런 화면에선 사실상 무손실이고 용량은 몇 배 작습니다.
            # maxrate 는 유튜브 권장(1080p ~8Mbps) 안쪽으로 피크를 묶어 둡니다.
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-crf", "18", "-preset", "medium",
            "-maxrate", "8M", "-bufsize", "16M",
            "-g", "60", "-t", f"{dur:.2f}",
            "-movflags", "+faststart", str(dst)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ffmpeg 실패: {r.stderr.strip()[:400]}", file=sys.stderr)
        return 1
    shutil.rmtree(store.dir, ignore_errors=True)
    vf_file.unlink(missing_ok=True)
    # 지정한 라우드니스와 실제 결과는 어긋납니다 — 반드시 재서 확인합니다.
    # 진성 피크 상한에 걸리면 loudnorm 은 조용히 목표에 못 미친 채 끝납니다.
    loud = measured_loudness(dst) if audio else None
    if not quiet:
        mb = dst.stat().st_size / 1024 / 1024
        tail = "  (무음)"
        if audio:
            tail = f"  음량 {loud:.1f} LUFS" if loud is not None else "  (음성 포함)"
        print(f"  {ep}-draft.mp4  {dur:.1f}초  {mb:.1f}MB  큐 {len(cues)}개"
              f"  자료화면 {len(shots)}컷  출처자막 {len(sources)}컷" + tail)
    if loud is not None and loud < LOUDNESS_I - 2:
        print(f"  ! 음량이 목표보다 {LOUDNESS_I - loud:.1f}dB 낮습니다 "
              f"({loud:.1f} vs {LOUDNESS_I} LUFS).\n"
              f"    원본의 크레스트(피크 - 본체)가 커서 진성 피크 상한에 먼저 걸립니다.\n"
              f"    단순히 볼륨을 올려도 피크가 같이 올라가 소용없습니다 — "
              f"압축을 더 걸거나 목표를 낮추세요.", file=sys.stderr)
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
