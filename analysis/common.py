"""Shared paths, loading, logging and result storage for the Opus 5.5 redo analysis."""
import os, json
import numpy as np
import tifffile
from termcolor import colored

HERE = os.path.dirname(os.path.abspath(__file__))
SCANS = os.path.abspath(os.getenv("RAMEY_SCANS") or os.path.join(HERE, "..", "..", "UT Images"))
OUT = os.path.join(HERE, "out")
FIG = os.path.join(OUT, "fig")
RESULTS = os.path.join(OUT, "results.json")
os.makedirs(FIG, exist_ok=True)

EXPOSURES = ["55B", "60B", "65B", "70B"]
REF_EXPOSURE = "60B"
HALVES = ["L", "R"]
WHOLE_FILE = "All-55B 1000 dpi.tif"


def info(msg): print(colored(f"[info] {msg}", "cyan"), flush=True)
def ok(msg): print(colored(f"[ ok ] {msg}", "green"), flush=True)
def warn(msg): print(colored(f"[warn] {msg}", "yellow"), flush=True)
def err(msg): print(colored(f"[fail] {msg}", "red"), flush=True)


def half_path(half, exp): return os.path.join(SCANS, f"{half} Scanpro {exp} 800 dpi 2x.tif")


def load(path):
    """Load a scan as float32. Values are as stored: ink is bright (the film is a negative)."""
    try:
        info(f"loading {os.path.basename(path)}")
        return tifffile.imread(path).astype(np.float32)
    except Exception as e:
        err(f"could not load {path}: {e}"); raise


def load_half(half, exp): return load(half_path(half, exp))


def save_result(key, value):
    """Merge one top-level key into out/results.json."""
    try:
        data = {}
        if os.path.exists(RESULTS):
            with open(RESULTS, encoding="utf-8") as f:
                data = json.load(f)
        data[key] = value
        with open(RESULTS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, default=float)
        ok(f"results.json <- {key}")
    except Exception as e:
        err(f"could not write results key {key}: {e}"); raise


def load_results():
    with open(RESULTS, encoding="utf-8") as f:
        return json.load(f)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))
