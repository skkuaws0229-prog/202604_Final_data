"""Shared drug-name normalization + alias expansion for colon Step6 external validation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

_SALT_SUFFIXES = (
    "hydrochloride",
    "hydrochloridehydrate",
    "sulfate",
    "mesylate",
    "maleate",
    "disodium",
    "sodium",
    "acetate",
    "tartrate",
    "phosphate",
    "citrate",
    "hydrate",
)


def normalize_drug_name(name: object) -> str:
    if pd.isna(name) or not isinstance(name, str):
        return ""
    s = name.strip().lower()
    s = re.sub(r"[^\w]+", "", s.replace("-", "").replace(" ", "").replace("_", ""))
    return s


def strip_salt_variants(norm: str) -> set[str]:
    out = {norm}
    if not norm:
        return out
    for suf in _SALT_SUFFIXES:
        if norm.endswith(suf) and len(norm) > len(suf) + 3:
            out.add(norm[: -len(suf)])
    return out


def load_aliases(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def expanded_norm_set(display_name: str, aliases_data: dict) -> set[str]:
    """All normalized forms to try when matching an inventory drug name."""
    n = normalize_drug_name(display_name)
    norms: set[str] = set()
    if n:
        norms.add(n)
        norms |= strip_salt_variants(n)
    ab = aliases_data.get("aliases_by_primary_name", {})
    for primary, alts in ab.items():
        if normalize_drug_name(primary) == n or primary.strip().lower() == str(display_name).strip().lower():
            for alt in alts:
                an = normalize_drug_name(alt)
                if an:
                    norms.add(an)
                    norms |= strip_salt_variants(an)
            break
    return {x for x in norms if len(x) >= 2}


def registry_put(reg: dict[str, dict], norm: str, raw_name: str, phases: list, nct_id: str) -> None:
    if norm not in reg:
        reg[norm] = {"name": raw_name, "phases": set(), "nct_ids": [], "count": 0}
    reg[norm]["phases"].update(phases)
    reg[norm]["nct_ids"].append(nct_id)
    reg[norm]["count"] += 1


CRC_DISEASE_RE = re.compile(
    r"colorectal|colon\s|cancer.*colon|rectal|large\s*intestine|\bcoad\b|\bread\b",
    re.I,
)


def match_drugs_in_cosmic_actionability_combos(
    act_df: pd.DataFrame | None,
    top_drugs: pd.DataFrame,
    name_col: str,
    aliases_data: dict,
    crc_rows_only: bool,
) -> tuple[set[str], int]:
    """Scan DRUG_COMBINATION for tokens that match Top drugs (+aliases)."""
    if act_df is None or "DRUG_COMBINATION" not in act_df.columns:
        return set(), 0
    rows = act_df
    if crc_rows_only and "DISEASE" in act_df.columns:
        mask = act_df["DISEASE"].astype(str).apply(lambda s: bool(CRC_DISEASE_RE.search(s)))
        rows = act_df[mask]

    drug_to_norms: dict[str, set[str]] = {}
    for _, row in top_drugs.iterrows():
        dn = row[name_col]
        drug_to_norms[str(dn)] = expanded_norm_set(str(dn), aliases_data)

    all_norms: set[str] = set()
    for norms in drug_to_norms.values():
        all_norms |= norms

    hits: set[str] = set()
    scanned = 0
    for _, row in rows.iterrows():
        combo = row.get("DRUG_COMBINATION", "")
        if pd.isna(combo):
            continue
        scanned += 1
        for token in str(combo).split(","):
            t = token.strip()
            if not t:
                continue
            tn = normalize_drug_name(t)
            if not tn:
                continue
            tvars = strip_salt_variants(tn) | {tn}
            if all_norms & tvars:
                for dname, dns in drug_to_norms.items():
                    if dns & tvars:
                        hits.add(dname)
                continue
            for dname, dns in drug_to_norms.items():
                for sn in dns:
                    if len(sn) < 5:
                        continue
                    if sn in tn or tn in sn:
                        hits.add(dname)

    return hits, scanned
