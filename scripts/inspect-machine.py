"""Read-only Windows prerequisite inventory; never reads credential values."""
import ctypes
import json
import os
import platform
import shutil
import subprocess

class MemoryStatus(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
        (name, ctypes.c_ulonglong) for name in
        ("total_phys", "avail_phys", "total_page", "avail_page", "total_virtual", "avail_virtual", "avail_extended")
    ]

mem = MemoryStatus()
mem.length = ctypes.sizeof(mem)
ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
result = {
    "platform": platform.platform(), "windows_version": platform.win32_ver(),
    "architecture": platform.machine(), "cpu": platform.processor(),
    "logical_cpus": os.cpu_count(),
    "ram_gib": round(mem.total_phys / 2**30, 2) if ok else None,
    "available_ram_gib": round(mem.avail_phys / 2**30, 2) if ok else None,
    "disk_free_gib": {d: round(shutil.disk_usage(d).free / 2**30, 2) for d in ("C:\\", "D:\\")},
    "tools": {},
    "zetaris_env_names_present": sorted(k for k in os.environ if k.startswith("ZETARIS_")),
}
for name, args in {"python": ["--version"], "node": ["--version"], "npm.cmd": ["--version"],
                   "git": ["--version"], "docker": ["--version"], "nvidia-smi": ["--version"]}.items():
    exe = shutil.which(name)
    item = {"path": exe}
    if exe:
        proc = subprocess.run([exe, *args], capture_output=True, text=True, timeout=20)
        item.update(exit_code=proc.returncode, output=(proc.stdout + proc.stderr).strip())
    result["tools"][name] = item
print(json.dumps(result, indent=2))
