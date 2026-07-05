from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


POLYMER_DATA_DIR = Path(__file__).resolve().parents[1] / "polynexus" / "data" / "polymers"
POLYMER_FILES = {
    "pa6": "pa6.json",
    "nylon-6": "pa6.json",
    "nylon6": "pa6.json",
    "polyamide-6": "pa6.json",
    "pe": "pe.json",
    "polyethylene": "pe.json",
    "hdpe": "pe.json",
    "ldpe": "pe.json",
    "lldpe": "pe.json",
    "pp": "pp.json",
    "ipp": "pp.json",
    "polypropylene": "pp.json",
    "pet": "pet.json",
    "polyethylene terephthalate": "pet.json",
    "pvdf": "pvdf.json",
    "polyvinylidene fluoride": "pvdf.json",
    "pom": "pom.json",
    "polyoxymethylene": "pom.json",
    "acetal": "pom.json",
    "peek": "peek.json",
    "polyether ether ketone": "peek.json",
    "pa66": "pa66.json",
    "nylon-66": "pa66.json",
    "nylon66": "pa66.json",
    "polyamide-66": "pa66.json",
}
REQUIRED_POLYMER_FILES = ["pa6.json", "pe.json", "pp.json", "pet.json", "pvdf.json", "pom.json", "peek.json", "pa66.json"]


def _ir_band(
    wavenumber: float,
    assignment: str,
    strength: str,
    *,
    role: str,
    phase: str | None = None,
) -> dict[str, Any]:
    band = {
        "wavenumber": wavenumber,
        "assignment": assignment,
        "strength": strength,
        "role": role,
    }
    if phase:
        band["phase"] = phase
    return band


IR_REFERENCE_LIBRARY: dict[str, dict[str, Any]] = {
    "pa6": {
        "characteristic_bands": [
            _ir_band(3298, "N-H stretch", "m", role="key", phase="alpha"),
            _ir_band(2931, "vas(CH2)", "s", role="secondary"),
            _ir_band(2860, "vs(CH2)", "s", role="secondary"),
            _ir_band(1637, "amide I nu(C=O)", "vs", role="key"),
            _ir_band(1541, "amide II delta(N-H)+nu(C-N)", "s", role="key"),
            _ir_band(1463, "delta(CH2)", "m", role="secondary"),
            _ir_band(1418, "delta(CH2) adjacent to NH", "w", role="secondary"),
            _ir_band(1263, "amide III nu(C-N)+delta(N-H)", "m", role="key"),
            _ir_band(1200, "amide III + omega(CH2) crystalline", "m", role="secondary"),
            _ir_band(1120, "nu(C-C) skeletal", "w", role="secondary"),
            _ir_band(1027, "amide IV", "w", role="secondary"),
            _ir_band(929, "amide V gamma(N-H)", "w", role="key"),
            _ir_band(685, "amide V gamma(N-H)", "m", role="key"),
        ],
        "key_bands": [3298, 1637, 1541, 1263, 929, 685],
        "secondary_bands": [2931, 2860, 1463, 1418, 1200, 1120, 1027],
        "overlap_risks": [
            "1200 cm^-1 附近容易与 amide III 和 CH2 twisting 肩峰叠在一起。",
            "929 cm^-1 是弱特征带，平滑过强或基线压坏时很容易消失。",
        ],
        "assignment_notes": [
            "PA6 最稳妥的归属链是 1637 / 1541 / 1263 cm^-1 的主骨架三联峰，再叠加 3298 cm^-1 N-H stretch。",
            "如果只看到单个弱峰，不要把结论硬抬成 paper-ready。",
        ],
    },
    "pa66": {
        "characteristic_bands": [
            _ir_band(3300, "N-H hydrogen bonded", "m", role="key"),
            _ir_band(2935, "vas(CH2)", "s", role="secondary"),
            _ir_band(2860, "vs(CH2)", "s", role="secondary"),
            _ir_band(1635, "amide I nu(C=O)", "vs", role="key"),
            _ir_band(1540, "amide II delta(N-H)+nu(C-N)", "s", role="key"),
            _ir_band(1470, "delta(CH2)", "m", role="secondary"),
            _ir_band(1418, "delta(CH2) adjacent to NH", "w", role="secondary"),
            _ir_band(1275, "amide III nu(C-N)+delta(N-H)", "m", role="key"),
            _ir_band(1202, "amide III + omega(CH2) crystalline", "m", role="key"),
            _ir_band(1145, "nu(C-C) skeletal", "w", role="secondary"),
            _ir_band(935, "amide V gamma(N-H) crystalline", "w", role="key"),
            _ir_band(690, "amide V gamma(N-H)", "m", role="key"),
            _ir_band(580, "amide VI delta(C=O)", "w", role="secondary"),
        ],
        "key_bands": [3300, 1635, 1540, 1275, 1202, 935, 690],
        "secondary_bands": [2935, 2860, 1470, 1418, 1145, 580],
        "overlap_risks": [
            "1202 cm^-1 区域容易与 amide III 和 CH2 twisting 叠加。",
            "935 cm^-1 是弱峰，单独出现时不要当作强证据。",
        ],
        "assignment_notes": [
            "PA66 的主归属最好看 1635 / 1540 / 1275 cm^-1，再辅以 1202 和 935 cm^-1。",
            "如果关键带只命中一半，结论应保持保守。",
        ],
    },
    "pe": {
        "characteristic_bands": [
            _ir_band(2918, "vas(CH2)", "vs", role="key"),
            _ir_band(2850, "vs(CH2)", "vs", role="key"),
            _ir_band(1472, "delta(CH2) scissoring", "s", role="secondary"),
            _ir_band(1463, "delta(CH2) crystalline", "m", role="key"),
            _ir_band(730, "rho(CH2) crystalline", "m", role="key"),
            _ir_band(720, "rho(CH2) amorphous", "m", role="secondary"),
        ],
        "key_bands": [2918, 2850, 1463, 730],
        "secondary_bands": [1472, 720],
        "overlap_risks": [
            "1463 cm^-1 和 1472 cm^-1 很容易互相贴近，不能只凭单峰就判定结晶态。",
            "730 / 720 cm^-1 这一对低波数带很接近，需结合整体 CH2 轮廓一起看。",
        ],
        "assignment_notes": [
            "PE 归属最稳妥的是 2918 / 2850 cm^-1 的 CH2 伸缩，再配合 1463 和 730 cm^-1。",
            "如果只剩 1472 cm^-1 一点点 scissoring，不应直接抬成强结晶判断。",
        ],
    },
    "pp": {
        "characteristic_bands": [
            _ir_band(2950, "vas(CH3)", "s", role="secondary", phase="alpha"),
            _ir_band(2918, "vas(CH2)", "s", role="secondary", phase="alpha"),
            _ir_band(2868, "vs(CH3)", "s", role="secondary", phase="alpha"),
            _ir_band(2840, "vs(CH2)", "s", role="secondary", phase="alpha"),
            _ir_band(1458, "deltaas(CH3)", "m", role="secondary", phase="alpha"),
            _ir_band(1377, "deltas(CH3)", "m", role="secondary", phase="alpha"),
            _ir_band(1167, "nu(C-C) + rho(CH3)", "m", role="key", phase="alpha"),
            _ir_band(998, "rho(CH3) + nu(C-CH3)", "m", role="key", phase="alpha"),
            _ir_band(973, "rho(CH3) + nu(C-C)", "m", role="key", phase="alpha"),
            _ir_band(841, "rho(CH2) + nu(C-CH3)", "m", role="key", phase="alpha"),
        ],
        "key_bands": [1167, 998, 973, 841],
        "secondary_bands": [2950, 2918, 2868, 2840, 1458, 1377],
        "overlap_risks": [
            "998 cm^-1 和 973 cm^-1 的间隔很近，分辨率不足时容易连成一团。",
            "1458 / 1377 cm^-1 更像辅助带，不宜单独作为强相别证据。",
        ],
        "assignment_notes": [
            "PP / iPP 最稳妥的是 1167 / 998 / 973 / 841 cm^-1 这一组 alpha 线索。",
            "如果只看到侧带而核心四带不齐，结论应保持候选态。",
        ],
    },
    "pet": {
        "characteristic_bands": [
            _ir_band(1715, "nu(C=O)", "vs", role="key"),
            _ir_band(1505, "nu(C=C) aromatic ring", "w", role="secondary"),
            _ir_band(1471, "delta(CH2)", "w", role="secondary"),
            _ir_band(1410, "delta(CH2) + nu(C-C) ring", "m", role="secondary"),
            _ir_band(1340, "omega(CH2) trans", "m", role="key"),
            _ir_band(1243, "nu(C-O) + delta(O-H)", "vs", role="key"),
            _ir_band(1120, "nu(C-O)", "s", role="secondary"),
            _ir_band(1098, "nu(C-O)", "s", role="secondary"),
            _ir_band(972, "omega(CH2) gauche", "w", role="secondary"),
            _ir_band(896, "gamma(C-H) ring", "w", role="secondary"),
            _ir_band(872, "gamma(C-H) ring crystalline", "m", role="key"),
            _ir_band(793, "gamma(C-H) ring", "w", role="secondary"),
            _ir_band(725, "gamma(C=O) + delta(ring)", "s", role="key"),
        ],
        "key_bands": [1715, 1340, 1243, 872, 725],
        "secondary_bands": [1505, 1471, 1410, 1120, 1098, 972, 896, 793],
        "overlap_risks": [
            "1243 cm^-1 与 1120 / 1098 cm^-1 处于相近的 C-O 区域，基线和归一化会明显影响判断。",
            "872 / 793 cm^-1 这一段更适合做辅助确认，不宜孤立使用。",
        ],
        "assignment_notes": [
            "PET 最稳妥的主链证据是 1715 cm^-1 的羰基带，再叠加 872 和 725 cm^-1。",
            "只看到单个 C-O 带时，不要把结晶度或相态抬得过满。",
        ],
    },
    "pvdf": {
        "characteristic_bands": [
            _ir_band(3025, "vas(CH2)", "w", role="secondary", phase="alpha"),
            _ir_band(2985, "vs(CH2)", "w", role="secondary", phase="alpha"),
            _ir_band(1402, "delta(CH2) + omega(CH2)", "m", role="secondary", phase="alpha"),
            _ir_band(1275, "nu(C-F) + delta(CCC)", "m", role="key", phase="beta"),
            _ir_band(1234, "nu(C-F) + delta(CCC)", "m", role="secondary", phase="gamma"),
            _ir_band(1182, "nuas(CF2)", "vs", role="secondary", phase="alpha"),
            _ir_band(1073, "nu(C-C) skeletal", "m", role="secondary", phase="alpha"),
            _ir_band(976, "omega(CH2)", "w", role="key", phase="alpha"),
            _ir_band(879, "nus(CF2) + nu(C-C)", "m", role="secondary", phase="alpha"),
            _ir_band(840, "rho(CH2) + nuas(CF2)", "s", role="key", phase="beta"),
            _ir_band(796, "rho(CH2)", "m", role="key", phase="alpha"),
            _ir_band(763, "delta(CF2) + omega(CH2)", "w", role="secondary", phase="alpha"),
            _ir_band(614, "delta(CF2) + delta(CCC)", "m", role="secondary", phase="alpha"),
            _ir_band(532, "delta(CF2)", "w", role="secondary", phase="alpha"),
            _ir_band(489, "omega(CF2)", "w", role="secondary", phase="alpha"),
        ],
        "key_bands": [1275, 840, 976, 796],
        "secondary_bands": [3025, 2985, 1402, 1234, 1182, 1073, 879, 763, 614, 532, 489],
        "overlap_risks": [
            "1275 cm^-1 和 1234 cm^-1 分别偏向 beta / gamma 线索，单峰命中不要强行定相。",
            "840 cm^-1 与 796 cm^-1 分别支持 beta / alpha，若两者同时存在，更适合写成混相或待判。",
        ],
        "assignment_notes": [
            "PVDF 要优先看 1275 + 840 cm^-1 的 beta 线索，或 976 + 796 cm^-1 的 alpha 线索。",
            "若 beta 与 alpha 的线索同时存在，结论应保留混相解释，而不是硬选一个。",
        ],
    },
    "pom": {
        "characteristic_bands": [
            _ir_band(2975, "vas(CH2)", "m", role="secondary"),
            _ir_band(2910, "vs(CH2)", "m", role="secondary"),
            _ir_band(1470, "delta(CH2)", "m", role="secondary"),
            _ir_band(1435, "delta(CH2)", "m", role="secondary"),
            _ir_band(1238, "nu(C-O-C) + omega(CH2)", "s", role="key"),
            _ir_band(1095, "nuas(C-O-C)", "vs", role="key"),
            _ir_band(935, "nus(C-O-C) + rho(CH2)", "vs", role="key"),
            _ir_band(895, "nu(C-O-C) + rho(CH2)", "m", role="key"),
            _ir_band(630, "delta(O-C-O)", "m", role="secondary"),
        ],
        "key_bands": [1238, 1095, 935, 895],
        "secondary_bands": [2975, 2910, 1470, 1435, 630],
        "overlap_risks": [
            "935 cm^-1 和 895 cm^-1 是一对非常接近的 C-O-C 线索，分辨率差时容易粘连。",
            "1238 cm^-1 与 1095 cm^-1 都很强，但更适合和低波数带组合判断，而不是单独下结论。",
        ],
        "assignment_notes": [
            "POM 的归属最好同时看到 1095 / 935 / 895 cm^-1，再看 1238 cm^-1 是否同向出现。",
            "如果只剩一条 C-O-C 强峰，建议把结论保留为候选。",
        ],
    },
    "peek": {
        "characteristic_bands": [
            _ir_band(1652, "nu(C=O) diaryl ketone", "vs", role="key"),
            _ir_band(1595, "nu(C=C) aromatic ring", "s", role="key"),
            _ir_band(1490, "nu(C=C) aromatic ring", "vs", role="key"),
            _ir_band(1310, "nu(C-O) diaryl ether", "m", role="secondary"),
            _ir_band(1225, "nuas(C-O-C) diphenyl ether", "vs", role="key"),
            _ir_band(1188, "delta(C-H) in-plane", "m", role="secondary"),
            _ir_band(1165, "nuas(C-O-C)", "s", role="secondary"),
            _ir_band(929, "nu(C-O) + delta(ring)", "w", role="secondary"),
            _ir_band(841, "gamma(C-H) 1,4-disubstituted", "s", role="key"),
            _ir_band(766, "gamma(C-H)", "m", role="key"),
        ],
        "key_bands": [1652, 1595, 1490, 1225, 841, 766],
        "secondary_bands": [1310, 1188, 1165, 929],
        "overlap_risks": [
            "1595 cm^-1 与 1490 cm^-1 都属于芳香环振动，容易在峰宽较大时相互融合。",
            "1225 cm^-1 与 1165 cm^-1 也常成对出现，单独一条带不够稳。",
        ],
        "assignment_notes": [
            "PEEK 最稳妥的骨架证据是 1652 / 1595 / 1490 / 1225 cm^-1，再看 841 / 766 cm^-1。",
            "如果芳香环带很弱，不要直接把结果抬成 paper-ready。",
        ],
    },
}


def load_polymer_knowledge(polymer: str) -> dict[str, Any]:
    filename = POLYMER_FILES.get(_key(polymer), f"{_key(polymer)}.json")
    path = POLYMER_DATA_DIR / filename
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _inject_ir_reference(payload, polymer) if _is_valid_knowledge(payload) else {}


def load_required_polymer_knowledge() -> list[dict[str, Any]]:
    items = []
    for filename in REQUIRED_POLYMER_FILES:
        path = POLYMER_DATA_DIR / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        items.append(_inject_ir_reference(payload, filename))
    return items


def format_polymer_knowledge(
    knowledge: dict[str, Any],
    current_params: dict[str, Any] | None = None,
    technique: str = "WAXS",
) -> str:
    if not knowledge:
        return f"参考知识：未找到当前聚合物的 {technique.upper()} 参考知识。"
    if technique.upper() == "DSC":
        return _format_dsc_knowledge(knowledge, current_params)
    if technique.upper() == "IR":
        return _format_ir_knowledge(knowledge, current_params)
    return _format_waxs_knowledge(knowledge, current_params)


def _format_waxs_knowledge(knowledge: dict[str, Any], current_params: dict[str, Any] | None) -> str:
    waxs = knowledge.get("waxs", {})
    peaks = waxs.get("characteristic_peaks", [])
    peak_parts = []
    for peak in peaks:
        theta = peak.get("two_theta")
        phase = peak.get("crystal_phase", "")
        if theta is None:
            continue
        suffix = f"（{phase}晶型）" if phase else ""
        peak_parts.append(f"{theta}°{suffix}")
    peak_text = "、".join(peak_parts) if peak_parts else "未提供"

    xc_range = waxs.get("xc_range")
    xc_text = f"{xc_range[0]}-{xc_range[1]}%" if isinstance(xc_range, list) and len(xc_range) == 2 else "未提供"
    comparison = _xc_comparison(current_params, xc_range)
    return f"参考知识：{knowledge.get('name', 'unknown')} 标准特征峰位于 {peak_text}；标准结晶度范围 {xc_text}{comparison}。"


def _format_dsc_knowledge(knowledge: dict[str, Any], current_params: dict[str, Any] | None) -> str:
    dsc = knowledge.get("dsc", {})
    tm = dsc.get("tm", "未提供")
    tc = dsc.get("tc", "未提供")
    dhm0 = dsc.get("delta_hm_100", "未提供")
    xc_range = dsc.get("xc_range")
    xc_text = f"{xc_range[0]}-{xc_range[1]}%" if isinstance(xc_range, list) and len(xc_range) == 2 else "未提供"
    comparison = _xc_comparison(current_params, xc_range)
    return (
        f"参考知识：{knowledge.get('name', 'unknown')} DSC 标准 Tm≈{tm}°C，"
        f"Tc≈{tc}°C，100%结晶熔融焓 ΔHm0={dhm0} J/g；"
        f"标准结晶度范围 {xc_text}{comparison}。"
    )


def _format_ir_knowledge(knowledge: dict[str, Any], current_params: dict[str, Any] | None) -> str:
    name = knowledge.get("name", "unknown")
    ir = knowledge.get("ir", {}) if isinstance(knowledge, dict) else {}
    if not isinstance(ir, dict) or not ir:
        return (
            f"参考知识：{name} 的 IR 特征吸收带参考数据尚未收录。"
            "调参时以残差分析、峰检测稳定性和聚合物匹配分数为主要依据。"
        )

    characteristic_bands = ir.get("characteristic_bands", [])
    if not isinstance(characteristic_bands, list):
        characteristic_bands = []
    key_bands = _format_ir_band_group(characteristic_bands, ir.get("key_bands"), limit=6)
    secondary_bands = _format_ir_band_group(characteristic_bands, ir.get("secondary_bands"), limit=6)
    overlap_risks = _join_text_items(ir.get("overlap_risks"))
    assignment_notes = _join_text_items(ir.get("assignment_notes"))

    parts = [f"参考知识：{name}"]
    if key_bands:
        parts.append(f"强特征带：{key_bands}")
    if secondary_bands:
        parts.append(f"辅助带：{secondary_bands}")
    if overlap_risks:
        parts.append(f"重叠风险：{overlap_risks}")
    if assignment_notes:
        parts.append(f"归属提示：{assignment_notes}")
    return "；".join(parts) + "。"


def _inject_ir_reference(payload: dict[str, Any], polymer_key: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    normalized_key = _normalize_reference_key(polymer_key)
    ir = payload.get("ir")
    if isinstance(ir, dict) and ir:
        return payload

    reference = IR_REFERENCE_LIBRARY.get(normalized_key)
    if not reference:
        return payload

    enriched = deepcopy(payload)
    enriched["ir"] = deepcopy(reference)
    return enriched


def _normalize_reference_key(value: str) -> str:
    text = str(value or "").strip().lower()
    if text.endswith(".json"):
        text = text[:-5]
    mapped = POLYMER_FILES.get(_key(text))
    if mapped:
        return Path(mapped).stem.lower()
    return _key(text)


def _format_ir_band_group(
    bands: list[dict[str, Any]],
    wavenumbers: Any,
    *,
    limit: int | None = None,
) -> str:
    if not isinstance(bands, list) or not bands:
        return ""

    targets: set[int] = set()
    if isinstance(wavenumbers, list):
        for item in wavenumbers:
            value = _clean_numeric(item)
            if value is not None:
                targets.add(int(round(value)))

    texts: list[str] = []
    for band in bands:
        if not isinstance(band, dict):
            continue
        wavenumber = _clean_numeric(band.get("wavenumber"))
        if wavenumber is None:
            continue
        if targets and int(round(wavenumber)) not in targets:
            continue
        texts.append(_format_ir_band_text(band))
        if limit is not None and len(texts) >= limit:
            break
    return "、".join(texts)


def _format_ir_band_text(band: dict[str, Any]) -> str:
    wavenumber = _clean_numeric(band.get("wavenumber"))
    if wavenumber is None:
        return ""
    label = f"{int(round(wavenumber))} cm^-1"
    details: list[str] = []
    assignment = str(band.get("assignment", "") or "").strip()
    if assignment:
        details.append(assignment)
    phase = str(band.get("phase", "") or "").strip()
    if phase:
        details.append(f"{phase} phase")
    strength = str(band.get("strength", "") or "").strip()
    if strength:
        details.append(strength)
    if details:
        label += f" ({'，'.join(details)})"
    return label


def _join_text_items(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    parts = [str(item or "").strip() for item in values if str(item or "").strip()]
    return "；".join(parts)


def _clean_numeric(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _xc_comparison(current_params: dict[str, Any] | None, xc_range: Any) -> str:
    current_xc = None
    if current_params:
        current_xc = current_params.get("Xc_pct", current_params.get("xc"))
    if current_xc is None or not (isinstance(xc_range, list) and len(xc_range) == 2):
        return ""
    try:
        value = float(current_xc)
        low, high = float(xc_range[0]), float(xc_range[1])
    except (TypeError, ValueError):
        return ""
    if value < low:
        return f"，当前 Xc={value:g}% 明显偏低"
    if value > high:
        return f"，当前 Xc={value:g}% 明显偏高"
    return f"，当前 Xc={value:g}% 在参考范围内"


def _is_valid_knowledge(payload: dict[str, Any]) -> bool:
    waxs = payload.get("waxs", {}) if isinstance(payload, dict) else {}
    dsc = payload.get("dsc", {}) if isinstance(payload, dict) else {}
    return bool(
        payload.get("name")
        and isinstance(waxs.get("xc_range"), list)
        and isinstance(waxs.get("characteristic_peaks"), list)
        and isinstance(dsc.get("xc_range"), list)
        and "delta_hm_100" in dsc
    )


def _key(polymer: str) -> str:
    return str(polymer or "").strip().lower().replace("_", "-")
