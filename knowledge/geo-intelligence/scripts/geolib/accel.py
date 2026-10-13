"""GPU hand-off. `uv run` installs PyPI torch (CPU-only on Windows, CUDA 13 on Linux) and cannot pick a GPU build per
machine, so `doctor.py --gpu` builds one GPU environment in <cache>/gpu on request and the model scripts (prior, detect,
match, sweep, sat_scan) rerun themselves there. Stdlib only: it runs before the script imports torch."""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from .paths import cache_root

GPU_CMD = "uv run scripts/doctor.py --gpu"
CHILD = "GEOINT_GPU_CHILD"
NO_DEVICE = 75          # exit code of a GPU run whose torch finds no GPU: the parent reruns on the default CPU torch
AMD_WINDOWS_INDEX = "https://stable.repo.amd.com/rocm/whl-next/"     # AMD TheRock wheels: torch[device-gfxNNNN]
CUDA13_DRIVER = 580     # PyPI's Linux torch is built for CUDA 13, which needs NVIDIA driver 580+
KFD_NODES = Path("/sys/class/kfd/kfd/topology/nodes")


def gpu_dir() -> Path:
    return cache_root() / "gpu"


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path: Path, data: dict) -> None:
    """Atomic write: two scripts may cache the detection at the same time."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def profile() -> dict | None:
    """The GPU environment doctor.py --gpu built and smoke-tested: {backend, python, uv_args, torch, env, created}; env
    keeps the GPU runs on the smoke-tested device."""
    return _read(gpu_dir() / "profile.json")


def build_failed() -> str | None:
    """Why the last doctor.py --gpu build failed, if it did."""
    try:
        return (gpu_dir() / "failed.txt").read_text(encoding="utf-8").strip() or "unknown error"
    except OSError:
        return None


# ---------------------------------------------------------------- hardware

def _run(cmd: list[str], timeout: float = 20) -> str:
    """stdout of a detection tool; '' when it is missing, fails or hangs (clinfo can be slow)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout if r.returncode == 0 else ""


def kfd_arch(properties: str) -> str | None:
    """gfx target of a Linux KFD topology node: gfx_target_version 100300 → gfx1030, 90010 → gfx90a; 0 = a CPU node."""
    m = re.search(r"^gfx_target_version\s+(\d+)", properties, re.M)
    v = int(m.group(1)) if m else 0
    return f"gfx{v // 10000}{v // 100 % 100:x}{v % 100:x}" if v else None


def clinfo_gpu(text: str) -> dict | None:
    """{name, arch} of the GPU with the most compute units in clinfo's output: a Radeon, not the Ryzen iGPU next to it."""
    gpus = []
    for block in re.split(r"^\s*Device Type:", text, flags=re.M)[1:]:
        field = dict(re.findall(r"^[ \t]*(Board name|Max compute units|Name):[ \t]*(.*?)[ \t]*$", block, re.M))
        arch = re.match(r"gfx[0-9a-f]+", field.get("Name", ""))
        if arch:
            units = field.get("Max compute units", "")
            gpus.append((int(units) if units.isdigit() else 0, field.get("Board name") or None, arch.group()))
    if not gpus:
        return None
    _, name, arch = max(gpus, key=lambda g: g[0])
    return {"name": name, "arch": arch}


def detect_gpu(platform: str = sys.platform) -> dict | None:
    """The GPU a torch build can use, {vendor, name, driver | arch}, or None. NVIDIA through nvidia-smi; on Windows AMD
    and Intel Arc through Win32_VideoController (AMD's board and gfx target from clinfo); on Linux AMD through
    rocm_agent_enumerator, else the KFD topology."""
    out = _run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]).strip()
    if out:
        name, _, driver = out.splitlines()[0].rpartition(",")
        return {"vendor": "nvidia", "name": name.strip(), "driver": driver.strip()}
    if platform == "win32":
        query = "Get-CimInstance Win32_VideoController | Select-Object Name, PNPDeviceID | ConvertTo-Json -Compress"
        try:
            cards = json.loads(_run(["powershell", "-NoProfile", "-NonInteractive", "-Command", query]) or "[]")
        except ValueError:
            cards = []
        cards = cards if isinstance(cards, list) else [cards]             # one adapter comes back as an object
        amd = [c.get("Name") or "AMD GPU" for c in cards if "VEN_1002" in (c.get("PNPDeviceID") or "").upper()]
        if amd:
            best = clinfo_gpu(_run(["clinfo"])) or {}
            return {"vendor": "amd", "name": best.get("name") or amd[0], "arch": best.get("arch")}
        for c in cards:
            if "VEN_8086" in (c.get("PNPDeviceID") or "").upper() and "Arc" in (c.get("Name") or ""):
                return {"vendor": "intel", "name": c["Name"]}
    elif platform.startswith("linux"):
        archs = [a for a in _run(["rocm_agent_enumerator"]).split() if a.startswith("gfx") and a != "gfx000"]
        if not archs:
            try:
                archs = [a for p in sorted(KFD_NODES.glob("*/properties")) if (a := kfd_arch(p.read_text(encoding="utf-8")))]
            except OSError:
                archs = []
        if archs:
            return {"vendor": "amd", "name": f"AMD {archs[0]}", "arch": archs[0]}
    return None


def detected(refresh: bool = False) -> dict | None:
    """detect_gpu(), cached in <cache>/gpu/detected.json (doctor.py refreshes it)."""
    path = gpu_dir() / "detected.json"
    data = None if refresh else _read(path)
    if data is None:
        data = {"gpu": detect_gpu()}
        try:
            write_json(path, data)
        except OSError:
            pass
    return data.get("gpu")


def _plan(backend: str, args: list[str], gb: float, disk: float, extra: str = "", pre: list[str] | None = None,
          env: dict | None = None) -> dict:
    return {"backend": backend, "args": args, "gb": gb, "disk": disk, "extra": extra, "pre": pre or [], "env": env or {}}


def gpu_plan(platform: str, gpu: dict | None) -> dict | None:
    """How doctor.py --gpu installs torch for this GPU: uv arguments for every install (args), the torch/torchvision
    extra, arguments for the torchvision step only (pre), build environment, download (gb) and installed size (disk) in
    GB, rounded up from the torch 2.14 cp312 wheels and their dependencies. None when there is no GPU, its target is
    unknown, or the default environment already uses it (Apple mps, Linux NVIDIA driver 580+)."""
    if not gpu or platform == "darwin":
        return None
    linux = platform.startswith("linux")
    if gpu["vendor"] == "nvidia":
        major = re.match(r"\d+", gpu.get("driver") or "")
        if linux and major and int(major.group()) >= CUDA13_DRIVER:
            return None
        return _plan("cuda", ["--torch-backend=auto"], *((4, 7) if linux else (2.5, 4)))
    if gpu["vendor"] == "amd" and gpu.get("arch"):
        if linux:
            return _plan("rocm", ["--torch-backend=auto"], 7, 16, env={"UV_AMD_GPU_ARCHITECTURE": gpu["arch"]})
        # AMD's device packages for torchvision are pre-releases (0.29.0a0 next to torch 2.14)
        return _plan("rocm", ["--index", AMD_WINDOWS_INDEX], 1, 4, extra=f"[device-{gpu['arch']}]", pre=["--prerelease", "allow"])
    if gpu["vendor"] == "intel":
        return _plan("xpu", ["--torch-backend=xpu"], *((2.5, 7) if linux else (1.5, 4)))
    return None


def size_note(plan: dict) -> str:
    return f"~{plan['gb']:g} GB download, ~{plan['disk']:g} GB on disk"


def torchvision_spec(torch_version: str, extra: str = "") -> str:
    """The torchvision release built for a torch release: 2.N pairs with 0.(N+15). Left free, uv may pick an older one
    (torchvision::nms then does not exist); pre-releases included, as AMD ships 0.29.0a0."""
    minor = int(torch_version.split(".")[1])
    return f"torchvision{extra}>=0.{minor + 15}.0a0,<0.{minor + 16}"


# ---------------------------------------------------------------- hand-off

def requested(flag: str | None) -> str:
    """The device asked for: a script's --device unless auto, else GEOINT_DEVICE, else auto."""
    flag = (flag or "").strip().lower()
    return flag if flag not in ("", "auto") else (os.environ.get("GEOINT_DEVICE") or "auto").strip().lower()


def _device_flag(argv: list[str]) -> str | None:
    """The value of --device / --device=X in argv, the last one winning as in argparse."""
    flag = None
    for arg, nxt in zip(argv, [*argv[1:], None]):
        if arg == "--device":
            flag = nxt
        elif arg.startswith("--device="):
            flag = arg.partition("=")[2]
    return flag


def _run_child(cmd: list[str], env: dict) -> int:
    """Run the GPU child to its end, as `uv run` does. The console's Ctrl+C reaches the child too, so this process
    ignores it and waits for the child's own cleanup; on POSIX a SIGTERM (recon's timeout) is passed on so the child
    never outlives this process (on Windows taskkill /T reaches it directly)."""
    child = subprocess.Popen(cmd, env=env)       # before SIG_IGN: an ignored SIGINT would be inherited on POSIX
    handlers = {signal.SIGINT: signal.SIG_IGN}
    if os.name != "nt":
        handlers[signal.SIGTERM] = lambda signum, _frame: child.send_signal(signum)
    old = {sig: signal.signal(sig, handler) for sig, handler in handlers.items()}
    try:
        return child.wait()
    except BaseException:
        child.kill()
        raise
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler if handler is not None else signal.SIG_DFL)


def handoff(script: str) -> None:
    """Rerun this model script in the GPU environment with the same arguments and exit with its code. Returns, so the
    script runs here on the CPU, when the CPU is requested (--device cpu or GEOINT_DEVICE=cpu), inside the GPU run,
    without a GPU environment, when the environment cannot be synced, or when the GPU run finds no device (exit
    NO_DEVICE)."""
    if requested(_device_flag(sys.argv[1:])) == "cpu" or os.environ.get(CHILD):
        return
    prof = profile()
    if not prof:
        gpu = detected()
        plan = gpu_plan(sys.platform, gpu)
        if plan and not build_failed():
            print(f"GPU {gpu['name']} found: `{GPU_CMD}` builds its environment once ({size_note(plan)}); "
                  "this run uses the CPU", file=sys.stderr)
        return
    py = Path(prof.get("python") or "")
    if not py.is_file():
        print(f"GPU environment missing ({py}): rerun `{GPU_CMD}`; this run uses the CPU", file=sys.stderr)
        return
    if os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(os.path.abspath(py)):
        return                               # not samefile: POSIX venv pythons are symlinks to one base interpreter
    script = str(Path(script).resolve())
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        print("GPU environment not synced (uv not found); this run uses the CPU", file=sys.stderr)
        return
    # the script's own PEP 723 dependencies, torch and torchvision held at the tested pair (~0.1 s when nothing changed)
    sync = subprocess.run([uv, "pip", "install", "-q", "--python", str(py), *prof.get("uv_args", []),
                           "-c", str(gpu_dir() / "constraints.txt"), "-r", script],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if sync.returncode:
        why = next((ln.strip() for ln in sync.stderr.splitlines() if ln.strip()), f"uv exit {sync.returncode}")
        print(f"GPU environment out of date ({why[:200]}): rerun `{GPU_CMD}`; this run uses the CPU", file=sys.stderr)
        return
    # the operator's own HIP_/CUDA_VISIBLE_DEVICES outranks the device the smoke test chose
    rc = _run_child([str(py), script, *sys.argv[1:]], {**prof.get("env", {}), **os.environ, CHILD: "1"})
    if rc != NO_DEVICE:
        sys.exit(rc if rc >= 0 else 128 - rc)    # a GPU run killed by signal N: the shell's 128+N, as for a direct run
    print("The GPU run found no GPU device; rerunning on the CPU", file=sys.stderr)
