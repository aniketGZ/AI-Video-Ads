"""Probe a downloaded ad video, pull hook + scene-change frames, and transcribe if possible.

Usage:
    python tools/competitor_ad_agent/video_frames.py <video.mp4> <frames_dir> [--transcript <out.txt>]

Prints a JSON summary to stdout. Works without a system ffmpeg by falling back
to the binary bundled with the `imageio-ffmpeg` pip package.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOOK_TIMES = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
MAX_SCENE_FRAMES = 12
SCENE_THRESHOLD = 0.3


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(ffmpeg, video):
    # `ffmpeg -i` with no output exits non-zero but prints stream info to stderr.
    err = run([ffmpeg, "-hide_banner", "-i", str(video)]).stderr
    info = {"duration_s": None, "width": None, "height": None, "aspect_ratio": None, "has_audio": "Audio:" in err}
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if m:
        info["duration_s"] = round(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), 2)
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    if m:
        w, h = int(m[1]), int(m[2])
        info.update(width=w, height=h, aspect_ratio=nearest_ratio(w, h))
    return info


def nearest_ratio(w, h):
    ratios = {"9:16": 9 / 16, "4:5": 4 / 5, "1:1": 1.0, "16:9": 16 / 9, "2:3": 2 / 3, "3:4": 3 / 4}
    r = w / h
    return min(ratios, key=lambda k: abs(ratios[k] - r))


def hook_frames(ffmpeg, video, out_dir, duration):
    saved = []
    for t in HOOK_TIMES:
        if duration is not None and t >= duration:
            break
        name = f"hook_{t:04.1f}s.jpg".replace(".", "_", 1)
        dest = out_dir / name
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(video),
             "-frames:v", "1", "-q:v", "3", str(dest)])
        if dest.exists():
            saved.append({"t": t, "file": dest.name})
    return saved


def scene_frames(ffmpeg, video, out_dir):
    pattern = out_dir / "scene_%02d.jpg"
    res = run([ffmpeg, "-hide_banner", "-y", "-ss", "3", "-i", str(video),
               "-vf", f"select='gt(scene,{SCENE_THRESHOLD})',showinfo", "-vsync", "vfr",
               "-frames:v", str(MAX_SCENE_FRAMES), "-q:v", "3", str(pattern)])
    times = [round(float(t) + 3, 2) for t in re.findall(r"pts_time:([\d.]+)", res.stderr)]
    files = sorted(out_dir.glob("scene_*.jpg"))
    return [{"t": times[i] if i < len(times) else None, "file": f.name} for i, f in enumerate(files)]


def transcribe(video, out_path):
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", compute_type="int8")
        segments, _ = model.transcribe(str(video))
        lines = [f"[{s.start:05.1f}-{s.end:05.1f}] {s.text.strip()}" for s in segments]
        engine = "faster-whisper"
    except ImportError:
        try:
            import whisper
            result = whisper.load_model("small").transcribe(str(video))
            lines = [f"[{s['start']:05.1f}-{s['end']:05.1f}] {s['text'].strip()}" for s in result["segments"]]
            engine = "openai-whisper"
        except ImportError:
            return {"status": "no transcript", "reason": "no whisper package installed"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) or "(no speech detected)", encoding="utf-8")
    return {"status": "ok", "engine": engine, "file": str(out_path)}


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)
    video, out_dir = Path(args[0]), Path(args[1])
    transcript = Path(args[args.index("--transcript") + 1]) if "--transcript" in args else None

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print(json.dumps({"error": "ffmpeg not found; pip install imageio-ffmpeg"}))
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    info = probe(ffmpeg, video)
    summary = {
        "video": str(video),
        **info,
        "hook_frames": hook_frames(ffmpeg, video, out_dir, info["duration_s"]),
        "scene_frames": scene_frames(ffmpeg, video, out_dir),
        "frames_dir": str(out_dir),
    }
    if transcript:
        summary["transcript"] = transcribe(video, transcript) if info["has_audio"] else {"status": "no audio track"}
    (out_dir / "meta.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
