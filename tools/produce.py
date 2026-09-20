#!/usr/bin/env python3
"""produce — 검증된 대본을 영상 제작 패키지로 빌드.

    python3 tools/produce.py EP001        build/EP001/ 생성
    python3 tools/produce.py --all

생성물:
    narration.txt      TTS/녹음용 낭독 원고 (큐 번호 + 예상 시각)
    <EP>.srt           번인 자막 타이밍 초안
    shotlist.md        화면 지시 + 컷별 출처 자막 (편집자용)
    metadata.md        유튜브/틱톡 업로드 메타데이터
    pinned_comment.txt 고정 댓글 (출처 전문)
    checklist.md       발행 전 확인 목록

빌드 전 `claimctl validate` 를 통과해야 합니다. 검수 안 된 대본은 빌드되지 않습니다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claimctl import (ROOT, SCRIPTS, estimate_seconds, load_claims,  # noqa: E402
                      load_fallacies, narration_of, parse_script)

BUILD = ROOT / "build"
SECTION = re.compile(r"^##\s+(.+?)\s*(?:\((.+?)\))?\s*$")


def srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def walk(body: str):
    """대본 본문을 (종류, 내용, 섹션) 흐름으로 분해.

    종류: 'cue'(낭독) | 'screen'(화면 지시). 제작 메모('---' 이후)는 제외.
    """
    section = "?"
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("---"):
            return
        if not s:
            continue
        if m := SECTION.match(s):
            section = m.group(1)
            continue
        if s.startswith(">"):
            yield "screen", re.sub(r"^화면\s*[:：]\s*", "", s.lstrip("> ").strip()), section
            continue
        if s.startswith(("#", "```", "|")):
            continue
        yield "cue", s, section


def strip_md(s: str) -> str:
    """낭독 원고에서 마크다운 강조와 출처 마커를 제거."""
    s = re.sub(r"\[S-[A-Z0-9\-]+\]", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 출처 마커를 지운 자리에 남는 공백 정리 ("틱타알릭 ." -> "틱타알릭.")
    return re.sub(r"\s+([.,!?%）\)])", r"\1", s)


def build_one(ep_id: str, quiet: bool = False) -> int:
    matches = [p for p in SCRIPTS.glob(f"{ep_id}*.md") if not p.name.startswith("_")]
    if not matches:
        print(f"대본 없음: {ep_id}", file=sys.stderr)
        return 1
    path = matches[0]
    fm, body = parse_script(path)
    claims = {c["id"]: c for c in load_claims()["claims"]}
    fams = {f["id"]: f for f in load_fallacies()["families"]}
    # 일반 편은 claims.yaml, 접종 편은 fallacies.yaml 에서 설명 문구를 가져옵니다.
    if fid := fm.get("fallacy_id"):
        fam = fams.get(fid, {})
        claim = {"rebuttal": (fam.get("why_it_works") or "").strip(),
                 "fallacy": fam.get("test", "")}
    else:
        claim = claims.get(fm.get("claim_id"), {})
    refs = {r["id"]: r for r in
            yaml.safe_load((ROOT / "content" / "references.yaml").read_text(encoding="utf-8"))["references"]}

    out = BUILD / fm["id"]
    out.mkdir(parents=True, exist_ok=True)

    # ── 큐 분해 + 타이밍 ──
    cues: list[dict] = []
    pending_screen: list[str] = []
    t = 0.0
    for kind, text, section in walk(body):
        if kind == "screen":
            pending_screen.append(text)
            continue
        spoken = strip_md(text)
        if not spoken:
            continue
        dur = estimate_seconds(spoken)
        cues.append({
            "n": len(cues) + 1, "start": t, "end": t + dur, "dur": dur,
            "text": spoken, "raw": text, "section": section,
            "screen": pending_screen[:],
            "sources": re.findall(r"\[(S-[A-Z0-9\-]+)\]", text),
        })
        pending_screen = []
        t += dur
    total = round(t, 1)

    # ── narration.txt ──
    N = [f"# {fm['id']} 낭독 원고", f"# {fm['title']}",
         f"# 예상 {total}초 · 큐 {len(cues)}개",
         "#",
         "# 숫자와 학명은 의도적으로 느리게 읽을 것 (docs/05 ⑦).",
         "# TTS 사용 시 회차 간 보이스를 절대 바꾸지 마세요 — 일관성이 신뢰도입니다.",
         ""]
    cur = None
    for c in cues:
        if c["section"] != cur:
            cur = c["section"]
            N.append(f"\n## {cur}")
        N.append(f"\n[{c['n']:02d}] ({c['start']:05.1f}s ~ {c['end']:05.1f}s)")
        N.append(c["text"])
    (out / "narration.txt").write_text("\n".join(N) + "\n", encoding="utf-8")

    # ── SRT ──
    S = []
    for c in cues:
        S += [str(c["n"]), f"{srt_time(c['start'])} --> {srt_time(c['end'])}", c["text"], ""]
    (out / f"{fm['id']}.srt").write_text("\n".join(S), encoding="utf-8")

    # ── shotlist.md ──
    H = [f"# {fm['id']} 샷 리스트", "", f"**{fm['title']}**", "",
         f"예상 {total}초 · 큐 {len(cues)}개 · confidence `{fm['confidence']}`", "",
         "> 편집 규칙 — docs/02-brand.md §3",
         "> - 창조론 주장 인용 = `--claim` (#B4472F) / 검증된 사실 = `--evidence` (#2E7D6B)",
         "> - **출처 자막 없는 증거 컷은 반려.** 아래 '출처 자막' 열이 채워진 큐는 반드시 표기",
         "> - 안전영역: 상단 12% / 하단 20%", "",
         "| 큐 | 시각 | 화면 | 낭독 | 출처 자막 |", "|---|---|---|---|---|"]
    for c in cues:
        screen = "<br>".join(c["screen"]) if c["screen"] else "—"
        src = "—"
        if c["sources"]:
            parts = []
            for sid in c["sources"]:
                r = refs.get(sid, {})
                v = r.get("verified") or {}
                if v.get("status") == "ok":
                    parts.append(f"**{v['container']} {v['year']}**, {r.get('doi','')}")
                else:
                    parts.append(f"**{sid}** (서지 미검증 — 확인 필요)")
            src = "<br>".join(parts)
        H.append(f"| {c['n']:02d} | {c['start']:.1f}–{c['end']:.1f}s | {screen} | "
                 f"{c['text'][:44]}{'…' if len(c['text']) > 44 else ''} | {src} |")
    cited = sorted({s for c in cues for s in c["sources"]})
    H += ["", f"## 이 편에서 화면에 표기할 출처 {len(cited)}건", ""]
    for sid in cited:
        r = refs.get(sid, {})
        v = r.get("verified") or {}
        mark = "✅" if v.get("status") == "ok" else "☐ 사람 확인 필요"
        cite = (f"{v['authors']} ({v['year']}). {v['title']}. {v['container']}."
                if v.get("status") == "ok" else r.get("citation", "(서지사항 없음)"))
        H.append(f"- {mark} `{sid}` — {cite}")
    (out / "shotlist.md").write_text("\n".join(H) + "\n", encoding="utf-8")

    # ── metadata.md ──
    tags = fm.get("hashtags") or []
    cap = f"{fm['title']} {' '.join(tags[:4])}"
    M = [f"# {fm['id']} 업로드 메타데이터", "",
         "## YouTube Shorts", "",
         "**제목** (검색어 중심)", "```", fm["title"], "```", "",
         "**설명**", "```", (claim.get("rebuttal") or "").strip(), "",
         " ".join(tags) + " #Shorts", "```", "",
         "## TikTok", "",
         f"**캡션** ({len(cap)}자{' — ⚠ 150자 초과, 잘립니다' if len(cap) > 150 else ''})",
         "```", cap, "```", "",
         "> 틱톡에서 내려받은 워터마크 파일을 쇼츠에 올리지 마세요.",
         "> 항상 원본에서 각각 내보내기 — docs/04-platform-playbook.md §3", ""]
    if fm.get("named_target"):
        M += ["## ⚠ 실명 대상 편", "",
              f"대상: **{fm['named_target']}**", "",
              "발행 전 확인 — docs/11-format-confrontation.md",
              "- [ ] 인용문이 원문 그대로인가 (요약이면 인용부호 제거 + `요약` 표기)",
              "- [ ] 출처가 0~5초 화면에 노출되는가",
              "- [ ] 원문 아카이브와 앞뒤 문맥을 보관했는가",
              "- [ ] 동기 추정 표현이 없는가 ('알면서도', '돈 때문에')", ""]
    (out / "metadata.md").write_text("\n".join(M), encoding="utf-8")

    # ── pinned_comment.txt ──
    if m := re.search(r"## 고정 댓글.*?```\n(.*?)```", body, re.S):
        pinned = m.group(1).rstrip()
    else:
        lines = ["출처"]
        for sid in cited:
            r = refs.get(sid, {})
            v = r.get("verified") or {}
            lines.append(f"[{sid}] " + (f"{v['authors']} ({v['year']}). {v['title']}. "
                                        f"{v['container']}. doi:{r.get('doi','')}"
                                        if v.get("status") == "ok"
                                        else r.get("citation", "")))
        lines += ["", "이 채널은 종교를 비판하지 않습니다. 검증 가능한 주장만 다룹니다."]
        pinned = "\n".join(lines)
    (out / "pinned_comment.txt").write_text(pinned + "\n", encoding="utf-8")

    # ── checklist.md ──
    unverified = [s for s in cited
                  if (refs.get(s, {}).get("verified") or {}).get("status") != "ok"]
    C = [f"# {fm['id']} 발행 전 확인", "",
         f"예상 길이 **{total}초**" + ("  ⚠ 60초 초과" if total > 60 else ""), "",
         "## 게이트 (docs/05-production-pipeline.md)", "",
         "- [ ] ④ `claimctl validate` 통과",
         "- [ ] ⑤ 인용문을 **원문에서** 확인 (2차 인용 금지)",
         "- [ ] ⑥ '예상 재반박' 각 항목에 답이 준비됨", "",
         "## 편집", "",
         "- [ ] 번인 자막 (56px+, 외곽선). 자동자막 의존 금지",
         "- [ ] 출처 자막이 모든 증거 컷 하단에 고정",
         "- [ ] 색 규칙: 주장=`--claim` / 사실=`--evidence`",
         "- [ ] 안전영역 상단 12% / 하단 20%",
         "- [ ] 음량 -14 LUFS, 트루피크 -1dBTP", "",
         "## 최종", "",
         "- [ ] **음소거로 재생** — 소리 없이 이해되면 통과",
         "- [ ] 아무 프레임을 캡처해도 오해 소지 없음",
         "- [ ] 두 플랫폼에 원본에서 각각 내보내기",
         "- [ ] 발행 즉시 고정 댓글 게시",
         "- [ ] `claims.yaml` / 대본 front matter `status: published` 갱신", ""]
    if unverified:
        C += ["## ⚠ 서지 미검증 출처", "",
              "아래 출처는 기계 검증되지 않았습니다. **원문 확인 후 인용하세요.**", ""]
        C += [f"- `{s}`" for s in unverified] + [""]
    if fid := fm.get("fallacy_id"):
        fam = fams.get(fid, {})
        C += ["## 접종 편 확인", "",
              f"시험법: **{fam.get('test', '')}**", "",
              "- [ ] 이 문장이 화면에 **두 번** 나오는가 (도입·마무리)",
              "- [ ] 특정 주장이 아니라 **논법**을 다루고 있는가",
              "- [ ] 우리 자신도 이 시험을 통과하는가", ""]
    if fm["confidence"] == "active":
        C += ["## ⚠ confidence: active", "",
              "단정 어조 금지. '현재로서는', '아직 모릅니다' 같은 유보 표현 확인.",
              "→ docs/03-editorial-policy.md §3", ""]
    (out / "checklist.md").write_text("\n".join(C), encoding="utf-8")

    if not quiet:
        warn = "  ⚠ 60초 초과" if total > 60 else ""
        print(f"  {fm['id']}  {total:>5.1f}초  큐 {len(cues):>2}개  출처 {len(cited)}건"
              f"{'  ⚠ 미검증 ' + str(len(unverified)) if unverified else ''}{warn}")
    return 0


# ────────────────────── WhisperX 실측 정렬 (Phase 1) ──────────────────────

# 한국어는 WhisperX 기본 정렬 모델 목록(en, fr, de, es, it)에 없습니다.
# HuggingFace 의 한국어 wav2vec2 모델을 지정해야 합니다.
# → docs/13-external-tools.md §3
KO_ALIGN_MODEL = "kresnik/wav2vec2-large-xlsr-korean"


def align_with_whisperx(ep_id: str, audio: Path, model: str) -> int:
    """녹음 파일로 실측 자막 타이밍을 만듭니다.

    기본 SRT 는 한글 음절 수 기반 **추정치**라 실제 녹음과 어긋납니다.
    이 함수는 추정 SRT 를 지우지 않고 `<EP>.aligned.srt` 를 따로 만들어
    둘의 차이(드리프트)를 보고합니다 — 추정 계수를 보정하는 데 씁니다.
    """
    if not shutil.which("whisperx"):
        print("whisperx 가 설치되어 있지 않습니다.\n"
              "  pip install whisperx\n"
              "설치 후 다시 실행하세요. → docs/13-external-tools.md §3", file=sys.stderr)
        return 1
    if not audio.exists():
        print(f"오디오 파일 없음: {audio}", file=sys.stderr)
        return 1

    out = BUILD / ep_id
    if not (out / f"{ep_id}.srt").exists():
        print(f"먼저 `produce.py {ep_id}` 로 제작 패키지를 만드세요", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["whisperx", str(audio), "--language", "ko",
               "--align_model", model, "--output_format", "json", "--output_dir", tmp]
        print(f"  실행: {' '.join(cmd)}")
        if subprocess.run(cmd).returncode != 0:
            print("whisperx 실행 실패", file=sys.stderr)
            return 1
        files = list(Path(tmp).glob("*.json"))
        if not files:
            print("whisperx 출력을 찾을 수 없습니다", file=sys.stderr)
            return 1
        data = json.loads(files[0].read_text(encoding="utf-8"))

    words = [w for seg in data.get("segments", []) for w in seg.get("words", [])
             if w.get("start") is not None]
    if not words:
        print("단어 단위 타임스탬프가 없습니다 — 정렬 모델이 한국어를 지원하는지 확인하세요\n"
              f"  현재 모델: {model}", file=sys.stderr)
        return 1

    # 추정 SRT 의 큐 텍스트를 실측 단어열에 순서대로 매칭
    est = (out / f"{ep_id}.srt").read_text(encoding="utf-8").strip().split("\n\n")
    cue_texts = [b.split("\n", 2)[2] for b in est if len(b.split("\n", 2)) > 2]

    def squash(s: str) -> str:
        return re.sub(r"[^가-힣0-9a-zA-Z]", "", s)

    lines, idx, drift = [], 0, []
    for n, text in enumerate(cue_texts, 1):
        target = squash(text)
        if not target or idx >= len(words):
            continue
        start = words[idx]["start"]
        acc = ""
        while idx < len(words) and len(acc) < len(target):
            acc += squash(words[idx].get("word", ""))
            idx += 1
        end = words[min(idx, len(words)) - 1].get("end", start)
        lines += [str(n), f"{srt_time(start)} --> {srt_time(end)}", text, ""]
        est_start = float(est[n - 1].split("\n")[1].split(" --> ")[0]
                          .replace(",", ".").split(":")[-1]) if n <= len(est) else 0
        drift.append(abs(start - est_start))

    (out / f"{ep_id}.aligned.srt").write_text("\n".join(lines), encoding="utf-8")
    total_est = estimate_seconds(" ".join(cue_texts))
    total_real = words[-1].get("end", 0)
    ratio = total_real / total_est if total_est else 0
    print(f"\n  {ep_id}.aligned.srt 생성 — 큐 {len(lines)//4}개")
    print(f"  추정 {total_est:.1f}초 vs 실측 {total_real:.1f}초  (비율 {ratio:.3f})")
    if abs(ratio - 1) > 0.08:
        suggested = round(355 / ratio)
        print(f"\n  ⚠ 추정과 실측이 {abs(ratio-1)*100:.0f}% 어긋납니다.")
        print(f"    tools/claimctl.py 의 SYLLABLES_PER_MIN 을 355 → {suggested} 로 보정하세요.")
        print(f"    이 값 하나가 길이 검수와 SRT 타이밍 전체를 좌우합니다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?", help="예: EP001, PB01")
    ap.add_argument("--all", action="store_true", help="전체 대본 빌드")
    ap.add_argument("--align", metavar="AUDIO",
                    help="녹음 파일로 실측 자막 타이밍 생성 (WhisperX 필요)")
    ap.add_argument("--align-model", default=KO_ALIGN_MODEL,
                    help=f"한국어 정렬 모델 (기본 {KO_ALIGN_MODEL})")
    args = ap.parse_args()

    if args.align:
        if not args.episode:
            ap.error("--align 은 episode 지정이 필요합니다")
        return align_with_whisperx(args.episode, Path(args.align), args.align_model)

    if args.all:
        eps = sorted({p.name.split("-")[0] for p in SCRIPTS.glob("*.md")
                      if not p.name.startswith("_")})
        print(f"제작 패키지 빌드 — {len(eps)}편\n")
        rc = 0
        for e in eps:
            rc |= build_one(e)
        print(f"\nbuild/ 에 생성 완료")
        return rc
    if not args.episode:
        ap.error("episode 를 지정하거나 --all 을 쓰세요")
    rc = build_one(args.episode)
    if rc == 0:
        print(f"\nbuild/{args.episode}/ 생성 완료")
    return rc


if __name__ == "__main__":
    sys.exit(main())
