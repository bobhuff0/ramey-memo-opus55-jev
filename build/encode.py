import json, subprocess, sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "manifest.json")))
OUT = os.path.join(HERE, "scenes"); os.makedirs(OUT, exist_ok=True)
FPS = 30
MOTION = {  # (kind, z0, z1) or ("pan", zoom, yfrac); zoom 1.0 shows the whole 2112x1188 still
    "title": ("zoom", 1.00, 1.06), "files": ("zoom", 1.00, 1.04), "exposures": ("zoom", 1.00, 1.03),
    "scale": ("zoom", 1.00, 1.05), "denoise": ("zoom", 1.00, 1.07), "dewarp": ("zoom", 1.00, 1.04),
    "straightened": ("panbox", 1.02, (90, 250, 1830, 850), "straightened.png"),   # text static; slight pan; all nine lines stay in the box
    "estimate": ("zoom", 1.00, 1.03), "victims": ("zoom", 1.00, 1.05),
    "tools": ("zoom", 1.00, 1.03), "readers": ("zoom", 1.00, 1.03),
    "calibration": ("zoom", 1.00, 1.03), "synthetic": ("zoom", 1.00, 1.03), "disputed": ("zoom", 1.00, 1.04),
    "expect": ("zoom", 1.00, 1.03),
    "verdict": ("zoom", 1.00, 1.09), "end": ("zoomout", 1.06, 1.00),
}


def encode(sc):
    N = int(round(sc["duration"] * FPS)); D = sc["duration"]
    m = MOTION[sc["layout"]]; kind = m[0]
    still = os.path.join(HERE, "stills", f"{sc['id']}.png"); audio = os.path.join(HERE, "audio", f"{sc['id']}.wav")
    fades = f"fade=t=in:st=0:d=0.6,fade=t=out:st={D-0.6:.3f}:d=0.6,format=yuv420p"
    afilter = f"[1:a]afade=t=in:st=0:d=0.3,afade=t=out:st={D-0.4:.3f}:d=0.4[a]"
    if kind == "panbox":
        # static slide; the asset pans left->right inside box (1920-coords) at the given zoom
        _, zoom, (x0, y0, x1, y1), asset = m
        from PIL import Image
        apath = os.path.join(HERE, "assets", asset); aw, ah = Image.open(apath).size
        bw, bh = x1 - x0, y1 - y0
        sw = int(round(bw * zoom)); sh = int(round(ah * sw / aw))
        if sh < bh:
            sh = int(round(bh * zoom)); sw = int(round(aw * sh / ah))
        sw += sw % 2; sh += sh % 2
        # image2 demuxer defaults to 25 fps: force 30 so crop's frame counter n matches N; N-1 so the last frame reaches the edge
        vf = (f"[0:v]scale=1920:1080[bg];"
              f"[2:v]scale={sw}:{sh},crop={bw}:{bh}:'(iw-ow)*min(n/{N-1}\\,1)':'(ih-oh)/2'[pan];"
              f"[bg][pan]overlay={x0}:{y0},{fades}[v]")
        inputs = ["-framerate", str(FPS), "-loop", "1", "-i", still, "-i", audio,
                  "-framerate", str(FPS), "-loop", "1", "-i", apath]
    else:
        kind, a, b = m
        if kind in ("zoom", "zoomout"):
            z = f"{a}+({b}-{a})*on/{N}"
            x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
        else:  # pan left->right at fixed zoom, vertical centre at yfrac
            z = f"{a}"; x = f"(iw-iw/zoom)*on/{N}"; y = f"ih*{b}-(ih/zoom/2)"
        vf = (f"[0:v]scale=2112:1188,zoompan=z='{z}':x='{x}':y='{y}':d={N}:s=1920x1080:fps={FPS},{fades}[v]")
        inputs = ["-i", still, "-i", audio]
    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", f"{vf};{afilter}",
           "-map", "[v]", "-map", "[a]", "-t", f"{D:.3f}", "-r", str(FPS),
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
           "-movflags", "+faststart", f"{OUT}/{sc['id']}.mp4"]
    t0 = time.time(); subprocess.run(cmd, check=True); return time.time() - t0


if __name__ == "__main__":
    ids = sys.argv[1:] or [s["id"] for s in M]
    for sc in M:
        if sc["id"] in ids:
            print(f"{sc['id']:14s} {sc['duration']:5.1f}s  encoded in {encode(sc):5.1f}s", flush=True)
