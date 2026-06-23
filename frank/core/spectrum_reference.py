"""Experimental IR reference spectra — NIST WebBook + built-in cache."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReferencePeak:
    frequency: float  # cm-1
    intensity: float = 1.0
    assignment: str = ""


@dataclass
class ReferenceSpectrum:
    name: str
    source: str
    peaks: list[ReferencePeak] = field(default_factory=list)
    formula: str = ""


# Built-in reference peaks (major bands, cm-1) for offline comparison
_BUILTIN_IR: dict[str, list[tuple[float, str]]] = {
    "h2o": [(3657, "O-H stretch"), (1595, "H-O-H bend")],
    "ch4": [(2917, "C-H stretch"), (1534, "H-C-H bend")],
    "nh3": [(3337, "N-H stretch"), (1627, "H-N-H bend")],
    "c2h4": [(3024, "C-H stretch"), (1654, "C=C stretch")],
    "c6h6": [(3037, "C-H stretch"), (1478, "C=C ring")],
    "ch3oh": [(3681, "O-H stretch"), (2843, "C-H stretch"), (1033, "C-O stretch")],
    "ch3cho": [(2720, "aldehyde C-H"), (1740, "C=O stretch"), (1395, "CH3 bend")],
    "ch3coch3": [(1715, "C=O stretch"), (1362, "CH3 bend")],
    "ch3ch2oh": [(3340, "O-H stretch"), (1045, "C-O stretch")],
    "co2": [(2349, "C=O asymmetric"), (667, "O-C-O bend")],
}


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def get_builtin_reference(name: str) -> Optional[ReferenceSpectrum]:
    key = _normalize_name(name)
    aliases = {
        "water": "h2o", "ammonia": "nh3", "benzene": "c6h6",
        "methanol": "ch3oh", "ethanol": "ch3ch2oh", "ethene": "c2h4",
        "acetaldehyde": "ch3cho", "acetone": "ch3coch3",
    }
    key = aliases.get(key, key)
    peaks_data = _BUILTIN_IR.get(key)
    if not peaks_data:
        return None
    peaks = [ReferencePeak(frequency=f, assignment=a) for f, a in peaks_data]
    return ReferenceSpectrum(name=name, source="Frank built-in cache", peaks=peaks)


def fetch_nist_ir(name: str, timeout: int = 10) -> Optional[ReferenceSpectrum]:
    """Try to fetch IR peak data from NIST Chemistry WebBook (best-effort)."""
    encoded = urllib.parse.quote(name.strip())
    url = (
        f"https://webbook.nist.gov/cgi/cbook.cgi?"
        f"Name={encoded}&Units=SI&cIR=on"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Frank/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None

    peaks = []
    for match in re.finditer(
        r"(\d{3,4}(?:\.\d+)?)\s*\(\s*([svmw]?)\s*\)", html, re.IGNORECASE
    ):
        freq = float(match.group(1))
        strength_map = {"s": 1.0, "m": 0.6, "w": 0.3, "v": 0.8}
        intensity = strength_map.get(match.group(2).lower(), 0.5)
        peaks.append(ReferencePeak(frequency=freq, intensity=intensity))

    if not peaks:
        return None
    return ReferenceSpectrum(name=name, source="NIST Chemistry WebBook", peaks=peaks[:30])


def get_reference_spectrum(name: str, prefer_nist: bool = False) -> Optional[ReferenceSpectrum]:
    """Get experimental IR reference, trying NIST then built-in cache."""
    if prefer_nist:
        ref = fetch_nist_ir(name)
        if ref:
            return ref
    ref = get_builtin_reference(name)
    if ref:
        return ref
    if not prefer_nist:
        return fetch_nist_ir(name)
    return None


def compare_with_reference(
    calc_freqs: list[float],
    reference: ReferenceSpectrum,
    tolerance: float = 50.0,
) -> dict:
    """Compare calculated frequencies with reference peaks."""
    real_freqs = sorted(f for f in calc_freqs if f > 0)
    matches = []
    unmatched_ref = []

    used = set()
    for peak in reference.peaks:
        best_match = None
        best_diff = tolerance + 1
        for i, f in enumerate(real_freqs):
            if i in used:
                continue
            diff = abs(f - peak.frequency)
            if diff <= tolerance and diff < best_diff:
                best_diff = diff
                best_match = (i, f, diff)
        if best_match:
            used.add(best_match[0])
            matches.append({
                "reference": peak.frequency,
                "calculated": best_match[1],
                "delta": best_match[2],
                "assignment": peak.assignment,
            })
        else:
            unmatched_ref.append(peak.frequency)

    return {
        "source": reference.source,
        "n_matches": len(matches),
        "n_reference_peaks": len(reference.peaks),
        "matches": matches,
        "unmatched_reference": unmatched_ref,
        "match_rate": len(matches) / max(len(reference.peaks), 1),
    }


def format_comparison_report(comparison: dict) -> str:
    lines = [
        f"  参考来源: {comparison['source']}",
        f"  匹配峰: {comparison['n_matches']}/{comparison['n_reference_peaks']} "
        f"({comparison['match_rate']:.0%})",
    ]
    for m in comparison.get("matches", []):
        assign = f" ({m['assignment']})" if m.get("assignment") else ""
        lines.append(
            f"    {m['reference']:.0f} → {m['calculated']:.0f} cm⁻¹ "
            f"(Δ={m['delta']:.0f}){assign}"
        )
    if comparison.get("unmatched_reference"):
        lines.append(f"  未匹配参考峰: {', '.join(f'{f:.0f}' for f in comparison['unmatched_reference'])} cm⁻¹")
    return "\n".join(lines)
