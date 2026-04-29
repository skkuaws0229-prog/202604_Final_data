#!/usr/bin/env python3
"""
Device helper for STAD Step 4 scripts.

Selection priority:
1) FORCE_CPU=1 -> cpu
2) MPS available -> mps
3) CUDA available -> cuda
4) fallback -> cpu
"""

from __future__ import annotations

from datetime import datetime
from typing import Tuple
import os

import torch


def log(msg: str) -> None:
    """Print timestamped log line."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def resolve_torch_device() -> Tuple[torch.device, str]:
    """Resolve torch device with explicit CPU fallback."""
    force_cpu: bool = os.getenv("FORCE_CPU", "0") == "1"
    if force_cpu:
        device = torch.device("cpu")
        reason = "FORCE_CPU=1"
        log(f"Using device: {device} ({reason})")
        return device, reason

    if torch.backends.mps.is_available():
        device = torch.device("mps")
        reason = "torch.backends.mps.is_available=True"
        log(f"Using device: {device} ({reason})")
        return device, reason

    if torch.cuda.is_available():
        device = torch.device("cuda")
        reason = "torch.cuda.is_available=True"
        log(f"Using device: {device} ({reason})")
        return device, reason

    device = torch.device("cpu")
    reason = "no accelerator available"
    log(f"Using device: {device} ({reason})")
    return device, reason

