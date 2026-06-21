#!/usr/bin/env python3
"""
ParkIQ — Video Builder v7 (HD quality + real FK logo + MetaBot team)
  • NO Ken Burns — frames displayed at pixel-perfect 1920×980 (no zoom, no pan, no crop)
  • Subtitle strip: dedicated 1920×100 dark bar below content
  • vstack (980+100=1080) → true 1920×1080 Full HD output
  • xfade transitions only (content appears sharp edge-to-edge)
  • Progress bar + corrected data
"""
import subprocess, os, re
from PIL import Image, ImageDraw, ImageFont

BASE   = "/Users/bhuwanss/Downloads/flipkart_hackathon/parkiq"
FRAMES = f"{BASE}/assets/frames"
AUDIO  = f"{BASE}/assets/audio"
CLIPS  = "/tmp/pkv6_clips"
OUT    = f"{BASE}/assets/ParkIQ_Demo_Final.mp4"  # v7: higher quality
SUBDIR = "/tmp/pkv6_subs"

os.makedirs(CLIPS,  exist_ok=True)
os.makedirs(SUBDIR, exist_ok=True)

# ── Timing ──────────────────────────────────────────────────────────────────
DURS  = [20.6, 24.5, 25.1, 20.5, 27.4, 23.9, 25.7, 21.9, 22.5, 23.7, 30.0, 32.0]
PAD   = 1.5
LEAD  = 0.5
XFADE = 0.7
APAD  = PAD - XFADE  # 0.8s

slide_durs = [d + PAD for d in DURS]
slide_durs[-1] += 2.0

video_starts = []
cumul = 0.0
for k in range(12):
    video_starts.append(cumul - k * XFADE)
    cumul += slide_durs[k]

actual_dur = cumul - 11 * XFADE
print(f"Total video: {actual_dur:.1f}s = {actual_dur/60:.1f} min")

# ── Narration scripts ────────────────────────────────────────────────────────
SCRIPTS = [
    "Welcome to ParkIQ — an AI-powered parking enforcement intelligence platform "
    "built for Bengaluru Traffic Police. We analyzed 298,450 BTP violations and "
    "8,173 ASTRAM incidents to deliver data-driven patrol recommendations.",
    "Bengaluru's traffic police face four critical gaps: no visibility into illegal "
    "parking hotspots, reactive deployment, no congestion impact measurement, "
    "and missed peak enforcement windows.",
    "Our analysis uses two real datasets: 115,400 approved BTP parking violation "
    "records with GPS coordinates, and 8,173 ASTRAM traffic incidents. Both cover "
    "the same 54 police stations from November 2023 to April 2024.",
    "The Live Heatmap shows violation density across all 54 police station "
    "jurisdictions in Bengaluru. The top hotspot is BTP-051, Safina Plaza "
    "Junction, with 15,449 total submitted violations.",
    "Hotspot Analysis ranks all named junctions by a composite priority score "
    "combining violation frequency, peak-hour density, incident correlation, "
    "and severity. Top junctions are concentrated within 2 km of Bengaluru CBD.",
    "Temporal analysis reveals violations peak between 9 and 11 AM IST — "
    "the morning rush. Sunday is the busiest day and January sees the "
    "highest monthly volume. Resources should concentrate in the 8-to-11 AM window.",
    "Cross-correlating violations with ASTRAM incidents gives a Pearson r of "
    "negative 0.113 — a directional negative trend suggesting enforcement "
    "suppresses incidents, though a larger dataset is needed for statistical significance.",
    "The Enforcement Optimizer recommends 3 officers during morning rush, "
    "two during midday, three for evening rush, and one for night patrol. "
    "Smart scheduling increases peak-hour coverage from 40 to 87 percent.",
    "Vehicle Intelligence: two-wheelers — scooters plus motorcycles — account "
    "for 44% of violations. Wrong Parking is the most common type at 52%, "
    "followed by No Parking at 50%. This guides vehicle-specific enforcement.",
    "The priority scoring model combines four factors: 40% violation frequency, "
    "30% peak-hour density, 20% incident correlation, and 10% severity. "
    "This produces a zero-to-one score for every junction.",
    "The system architecture flows across four layers: data ingestion, "
    "processing and priority scoring, the intelligence engine with HCM capacity "
    "modeling, and the dashboard and officer deployment output layer.",
    "To summarize: ParkIQ delivers hotspot detection across 54 stations, "
    "temporal intelligence, quantified enforcement-incident linkage, and a "
    "shift-based patrol optimizer. Next steps: real-time BTP feed integration, "
    "LSTM hotspot prediction, and a mobile officer dispatch app.",
]

# ── Subtitle cues ───────────────────────────────────────────────────────────
cues = []
for k, (script, dur) in enumerate(zip(SCRIPTS, DURS)):
    a_start = video_starts[k] + LEAD
    a_end   = a_start + dur - 0.3
    sentences = re.split(r'(?<=[.!?]) +', script.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 4]
    total_chars = sum(len(s) for s in sentences)
    t = a_start + 0.15
    for s in sentences:
        s_dur = (len(s) / max(total_chars, 1)) * (dur * 0.93)
        s_end = min(t + s_dur, a_end)
        if len(s) > 70:
            words = s.split()
            mid   = max(1, len(words) // 2)
            wrapped = ' '.join(words[:mid]) + '\n' + ' '.join(words[mid:])
        else:
            wrapped = s
        cues.append((t, s_end, wrapped))
        t = s_end + 0.12
        if t >= a_end:
            break
print(f"Subtitle cues: {len(cues)}")

# ── Subtitle strip PNGs (1920×100 dark bg) ─────────────────────────────────
print("\n── Generating subtitle strips ──")
STRIP_W, STRIP_H = 1920, 100
BG  = (6, 6, 20)       # matches frame bg
SEP = (35, 35, 70)     # subtle top separator

FONT_PATHS = ["/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/Supplemental/Arial.ttf"]
fnt = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        try: fnt = ImageFont.truetype(fp, 38); break
        except: continue
if fnt is None: fnt = ImageFont.load_default()

def make_strip(text, path):
    img  = Image.new("RGB", (STRIP_W, STRIP_H), BG)
    draw = ImageDraw.Draw(img)
    draw.line([(0, 0), (STRIP_W, 0)], fill=SEP, width=1)
    if text:
        lines    = text.split('\n')
        LINE_GAP = 8
        bboxes   = [draw.textbbox((0,0), ln, font=fnt) for ln in lines]
        heights  = [bb[3]-bb[1] for bb in bboxes]
        widths   = [bb[2]-bb[0] for bb in bboxes]
        total_h  = sum(heights) + LINE_GAP*(len(lines)-1)
        ty = (STRIP_H - total_h) // 2 + 3
        for i, (ln, lw, lh) in enumerate(zip(lines, widths, heights)):
            tx = (STRIP_W - lw)//2 - bboxes[i][0]
            draw.text((tx+1, ty+1), ln, font=fnt, fill=(0,0,0))        # shadow
            draw.text((tx,   ty),   ln, font=fnt, fill=(255,255,255))  # text
            ty += lh + LINE_GAP
    img.save(path)

blank_path = f"{SUBDIR}/blank.png"
make_strip("", blank_path)

sub_paths = []
for idx, (t_s, t_e, text) in enumerate(cues):
    p = f"{SUBDIR}/sub_{idx:04d}.png"
    make_strip(text, p)
    sub_paths.append(p)
print(f"  {len(sub_paths)} strips ✓")

# ── Build subtitle track (concat, low fps) ──────────────────────────────────
concat_lines = []
t = 0.0
for idx, (t_s, t_e, _) in enumerate(cues):
    gap = t_s - t
    if gap > 0.001:
        concat_lines += [f"file '{blank_path}'", f"duration {gap:.4f}"]
    concat_lines += [f"file '{sub_paths[idx]}'", f"duration {(t_e-t_s):.4f}"]
    t = t_e
if t < actual_dur:
    concat_lines += [f"file '{blank_path}'", f"duration {actual_dur-t:.4f}"]
concat_lines.append(f"file '{blank_path}'")

concat_path = f"{SUBDIR}/sub_concat.txt"
with open(concat_path, "w") as f:
    f.write('\n'.join(concat_lines)+'\n')

sub_track = f"{SUBDIR}/sub_track.mp4"
r = subprocess.run([
    "ffmpeg", "-y", "-f","concat","-safe","0","-i", concat_path,
    "-vf", f"fps=5,scale={STRIP_W}:{STRIP_H}:flags=fast_bilinear,format=yuv420p",
    "-c:v","libx264","-preset","ultrafast","-crf","28", sub_track
], capture_output=True, timeout=120)
if r.returncode != 0:
    print("  subtitle track error:", r.stderr.decode()[-100:]); raise SystemExit(1)
print(f"  subtitle_track: {os.path.getsize(sub_track)//1024} KB ✓")

# ── TRANSITIONS ─────────────────────────────────────────────────────────────
TRANSITIONS = [
    "fadeblack","slideleft","dissolve","wiperight",
    "smoothleft","fadeblack","wipeleft","wiperight",
    "dissolve","smoothleft","fadeblack",
]

# ── Step 1: Static clips (NO Ken Burns — full 1920×980 pixel-perfect) ───────
print("\n── Step 1: Static clips (1920×980 no zoom/pan) ──")
for i in range(12):
    dur  = slide_durs[i]
    clip = f"{CLIPS}/clip_{i+1:02d}.mp4"
    r = subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", f"{FRAMES}/frame_{i+1:02d}.png",
        "-t", str(dur),
        "-vf", "scale=1920:980:flags=lanczos,setsar=1",
        "-c:v","libx264","-preset","medium","-crf","14",
        "-r","30","-pix_fmt","yuv420p", clip
    ], capture_output=True, timeout=120)
    sz = os.path.getsize(clip)//1024 if os.path.exists(clip) else 0
    st = "✓" if r.returncode==0 else f"✗ {r.stderr.decode()[-50:]}"
    print(f"  clip_{i+1:02d}  {dur:.1f}s  {sz}KB  {st}")

# ── Step 2: xfade chain ──────────────────────────────────────────────────────
print("\n── Step 2: xfade transitions ──")
inputs_args = []
for i in range(12):
    inputs_args += ["-i", f"{CLIPS}/clip_{i+1:02d}.mp4"]

fparts = []
cumul2 = slide_durs[0]
lbl    = "[0:v]"
for k in range(11):
    offset  = cumul2 - (k+1)*XFADE
    lbl_out = "[vout]" if k==10 else f"[v{k+1:02d}]"
    fparts.append(
        f"{lbl}[{k+1}:v]xfade=transition={TRANSITIONS[k]}:"
        f"duration={XFADE:.2f}:offset={offset:.3f}{lbl_out}"
    )
    lbl    = lbl_out
    cumul2 += slide_durs[k+1]

r = subprocess.run(
    ["ffmpeg","-y"] + inputs_args + [
        "-filter_complex", ";".join(fparts),
        "-map","[vout]",
        "-c:v","libx264","-preset","medium","-crf","14",
        "-pix_fmt","yuv420p","/tmp/pkv6_base.mp4"
    ], capture_output=True, timeout=600
)
if r.returncode != 0:
    print("xfade ERROR:", r.stderr.decode()[-300:]); raise SystemExit(1)

measured = float(subprocess.run(
    ["ffprobe","-v","quiet","-show_entries","format=duration",
     "-of","csv=p=0","/tmp/pkv6_base.mp4"],
    capture_output=True, text=True
).stdout.strip())
print(f"  base (980px): {measured:.1f}s ✓")

# ── Step 3: Progress bar ─────────────────────────────────────────────────────
print("\n── Step 3: Progress bar ──")
vf_bar = f"drawbox=x=0:y=972:w='iw*t/{measured:.1f}':h=6:color=0xE94560:t=fill"
r = subprocess.run([
    "ffmpeg","-y","-i","/tmp/pkv6_base.mp4",
    "-vf",vf_bar,"-c:v","libx264","-preset","medium","-crf","14",
    "-pix_fmt","yuv420p","/tmp/pkv6_content.mp4"
], capture_output=True, timeout=600)
if r.returncode != 0:
    import shutil; shutil.copy("/tmp/pkv6_base.mp4","/tmp/pkv6_content.mp4")
    print("  (skipped)")
else:
    print("  done ✓")

# ── Step 4: vstack content(980) + subtitle(100) = 1080p ─────────────────────
print("\n── Step 4: vstack → 1920×1080 ──")
r = subprocess.run([
    "ffmpeg","-y",
    "-i","/tmp/pkv6_content.mp4",
    "-i", sub_track,
    "-filter_complex",
    "[0:v]setpts=PTS-STARTPTS[v0];"
    "[1:v]setpts=PTS-STARTPTS,scale=1920:100:flags=fast_bilinear[v1];"
    "[v0][v1]vstack=inputs=2[vout]",
    "-map","[vout]",
    "-c:v","libx264","-preset","medium","-crf","14",
    "-pix_fmt","yuv420p","/tmp/pkv6_stacked.mp4"
], capture_output=True, timeout=600)
if r.returncode != 0:
    print("  vstack error:", r.stderr.decode()[-150:]); raise SystemExit(1)
print(f"  1080p: {os.path.getsize('/tmp/pkv6_stacked.mp4')//(1024*1024)} MB ✓")

# ── Step 5: Audio ────────────────────────────────────────────────────────────
print("\n── Step 5: Audio ──")
for path, dur in [("/tmp/sl_lead.mp3",LEAD), ("/tmp/sl_gap.mp3",APAD)]:
    subprocess.run([
        "ffmpeg","-y","-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
        "-t",str(dur),"-c:a","libmp3lame","-q:a","2",path
    ], check=True, capture_output=True)
with open("/tmp/pkv6_audio.txt","w") as f:
    f.write("file '/tmp/sl_lead.mp3'\n")
    for i in range(1,13):
        f.write(f"file '{AUDIO}/narration_{i:02d}.mp3'\n")
        f.write("file '/tmp/sl_gap.mp3'\n")
subprocess.run([
    "ffmpeg","-y","-f","concat","-safe","0","-i","/tmp/pkv6_audio.txt",
    "-c:a","aac","-b:a","256k","/tmp/pkv6_audio.aac"
], check=True, capture_output=True)
print("  done ✓")

# ── Step 6: Final merge ───────────────────────────────────────────────────────
print("\n── Step 6: Final merge ──")
subprocess.run([
    "ffmpeg","-y",
    "-i","/tmp/pkv6_stacked.mp4","-i","/tmp/pkv6_audio.aac",
    "-c:v","copy","-c:a","copy","-shortest", OUT
], check=True, capture_output=True, timeout=120)

sz = os.path.getsize(OUT)//(1024*1024)
print(f"\n✅  {OUT}")
print(f"   {sz} MB  ·  {measured/60:.1f} min  ·  1920×1080  ·  H.264+AAC")
print(f"   Static frames (no Ken Burns)  ·  {len(cues)} subtitles in dedicated strip")
