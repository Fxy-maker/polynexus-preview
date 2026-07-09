"""NMR output module: SCI-quality figures."""

import csv
import os
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any
from .core import NMRResult
from .config import NMRConfig
from ..figure_document import save_generated_figure_document
from ..plot_edits import savefig_with_edits


from ...plotting.sci_style import (
    set_sci_style as _global_set_sci_style,
    WONG_COLORS,
)


C = {'blue':WONG_COLORS[5],'red':WONG_COLORS[6],'green':WONG_COLORS[3],
     'orange':WONG_COLORS[1],'purple':WONG_COLORS[7],'cyan':'#00A896',
     'grey':'#666666','dark':'#222222'}
PAL = [C['blue'],C['red'],C['green'],C['orange'],C['purple'],C['cyan']]


def set_sci_style(fig, ax, xl='', yl='', title='', fs=10):
    _global_set_sci_style(font_size=fs - 1)
    if xl: ax.set_xlabel(xl,fontsize=fs)
    if yl: ax.set_ylabel(yl,fontsize=fs)
    if title: ax.set_title(title,fontsize=fs+1,fontweight='bold')
    ax.tick_params(labelsize=fs-1,direction='in',top=True,right=True)
    for s in ax.spines.values(): s.set_linewidth(0.8); s.set_color('#333')
    ax.grid(True,alpha=0.2,linestyle='--',linewidth=0.5)

def _dirs(d):
    fd=os.path.join(d,'figures'); dd=os.path.join(d,'data')
    os.makedirs(fd,exist_ok=True); os.makedirs(dd,exist_ok=True)
    return fd,dd

def _safe_token(text):
    token = ''.join(ch if (ch.isalnum() or ch in ('-', '_')) else '_' for ch in str(text or ''))
    token = '_'.join(token.split('_')).strip('_')
    return token[:80]

def _fig_name(base, tag=''):
    tag = _safe_token(tag)
    return f'{base}_{tag}' if tag else base

def _save(fig,n,fd,f='svg',dpi=300):
    p=os.path.join(fd,f'{n}.{f}')
    savefig_with_edits(fig,p,dpi=dpi,bbox_inches='tight',
                       facecolor='white',edgecolor='none')
    plt.close(fig); return p


def _axis_object(axis_id, *, orientation, label, reversed_axis):
    return {
        "id": axis_id,
        "type": "axis",
        "name": f"{orientation.title()} Axis",
        "orientation": orientation,
        "label": label,
        "reversed": bool(reversed_axis),
        "scale": "linear",
        "style": {"color": C["dark"], "line_width": 0.8},
    }


def _text_object(text_id, *, text, x, y, color, rotation=0.0, font_size=6):
    return {
        "id": text_id,
        "type": "text",
        "name": "Annotation",
        "text": text,
        "x": float(x),
        "y": float(y),
        "rotation": float(rotation),
        "anchor": "center",
        "style": {"color": color, "font_size": font_size},
    }


def _save_nmr1_spectrum_document(path, result, tag=''):
    data_path = _write_nmr1_spectrum_data(path, result)
    data_ref = "nmr-spectrum-data"
    figure_id = Path(path).stem
    objects = [
        {
            "id": "series-spectrum",
            "type": "plot_series",
            "name": "NMR Spectrum",
            "data_ref": data_ref,
            "x_column": "ppm",
            "y_column": "intensity",
            "style": {"color": C["dark"], "line_width": 0.8},
        }
    ]
    for index, peak in enumerate(result.peaks):
        ppm = _json_number(peak.get("ppm"))
        if ppm is None:
            continue
        assignment = str(peak.get("assignment") or "")
        objects.append(
            {
                "id": f"line-peak-{index + 1}",
                "type": "line",
                "name": f"Peak {index + 1}",
                "orientation": "vertical",
                "x": ppm,
                "label": f"{ppm:.1f}",
                "assignment": assignment,
                "style": {"color": PAL[index % len(PAL)], "line_width": 0.5, "alpha": 0.5},
            }
        )
        label = f"{ppm:.1f}"
        if assignment and assignment != "unknown":
            label = f"{label}\n{assignment[:15]}"
        objects.append(
            _text_object(
                f"text-peak-{index + 1}",
                text=label,
                x=ppm,
                y=float(peak.get("height", 0.0) or 0.0),
                color=PAL[index % len(PAL)],
                rotation=90.0,
                font_size=6,
            )
        )
    objects.extend(
        [
            _axis_object(
                "axis-x",
                orientation="horizontal",
                label=f"{result.nucleus} Chemical Shift (ppm)",
                reversed_axis=True,
            ),
            _axis_object(
                "axis-y",
                orientation="vertical",
                label="Intensity (a.u.)",
                reversed_axis=False,
            ),
        ]
    )
    save_generated_figure_document(
        path,
        technique="nmr",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": __name__,
            "function": "fig_nmr1_spectrum",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "tag": str(tag or ""),
                "nucleus": str(result.nucleus or ""),
                "sample_state": str(result.sample_state or ""),
            },
        },
        style={
            "xlabel": f"{result.nucleus} Chemical Shift (ppm)",
            "ylabel": "Intensity (a.u.)",
            "x_axis": "reversed",
        },
        objects=objects,
    )


def _save_nmr2_deconvolution_document(path, result, tag=''):
    data_path = _write_nmr2_deconvolution_data(path, result)
    data_ref = "nmr-deconvolution-data"
    fit_color = C["orange"] if np.isfinite(result.r_squared) and result.r_squared < 0.5 else C["red"]
    figure_id = Path(path).stem
    objects = [
        {
            "id": "series-data",
            "type": "plot_series",
            "name": "Data",
            "data_ref": data_ref,
            "x_column": "ppm",
            "y_column": "intensity",
            "style": {"color": C["dark"], "line_width": 0.8},
        },
        {
            "id": "series-fit",
            "type": "plot_series",
            "name": "Fit",
            "data_ref": data_ref,
            "x_column": "ppm",
            "y_column": "fit",
            "style": {"color": fit_color, "line_width": 1.2},
        },
    ]
    for index, peak in enumerate(result.peaks):
        ppm = _json_number(peak.get("ppm"))
        if ppm is None:
            continue
        assignment = str(peak.get("assignment") or "")
        objects.append(
            {
                "id": f"line-peak-{index + 1}",
                "type": "line",
                "name": f"Peak {index + 1}",
                "orientation": "vertical",
                "x": ppm,
                "assignment": assignment,
                "style": {"color": C["blue"], "line_width": 0.4, "alpha": 0.35},
            }
        )
        label = f"{ppm:.1f}"
        if assignment and assignment != "unknown":
            label = assignment
        objects.append(
            _text_object(
                f"text-peak-{index + 1}",
                text=label,
                x=ppm,
                y=float(peak.get("height", np.interp(ppm, result.ppm, result.intensity)) or 0.0),
                color=C["blue"],
                rotation=90.0,
                font_size=6,
            )
        )
    objects.extend(
        [
            _axis_object(
                "axis-x",
                orientation="horizontal",
                label=f"{result.nucleus} Chemical Shift (ppm)",
                reversed_axis=True,
            ),
            _axis_object(
                "axis-y",
                orientation="vertical",
                label="Intensity",
                reversed_axis=False,
            ),
        ]
    )
    save_generated_figure_document(
        path,
        technique="nmr",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": __name__,
            "function": "fig_nmr2_deconvolution",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "tag": str(tag or ""),
                "nucleus": str(result.nucleus or ""),
                "sample_state": str(result.sample_state or ""),
                "r_squared": _json_number(result.r_squared),
            },
        },
        style={
            "xlabel": f"{result.nucleus} Chemical Shift (ppm)",
            "ylabel": "Intensity",
            "x_axis": "reversed",
        },
        objects=objects,
    )


def _save_nmr3_comparison_document(path, result, tag='', lo=None, hi=None, tolerance_ppm=2.0):
    exp_ppm = [_json_number(match.get("exp_ppm")) for match in result.matches]
    calc_ppm = [_json_number(match.get("calc_ppm")) for match in result.matches]
    values = [
        value
        for value in exp_ppm + calc_ppm
        if value is not None
    ]
    if lo is None:
        lo = min(values) - 5 if values else 0.0
    if hi is None:
        hi = max(values) + 5 if values else 1.0
    lo = float(lo)
    hi = float(hi)
    tolerance_ppm = float(tolerance_ppm)
    data_path = _write_nmr3_comparison_data(path, result, lo, hi, tolerance_ppm)
    data_ref = "nmr-comparison-data"
    save_generated_figure_document(
        path,
        technique="nmr",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.nmr_engine.nmr_output",
            "function": "fig_nmr3_comparison",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "tag": str(tag or ""),
                "match_count": len(result.matches),
                "tolerance_ppm": tolerance_ppm,
            },
        },
        style={
            "xlabel": "Experimental shift (ppm)",
            "ylabel": "Computed shift (ppm)",
            "x_axis": "reversed",
            "y_axis": "reversed",
            "aspect": "equal",
        },
        objects=[
            {
                "id": "tolerance-band",
                "type": "highlight",
                "name": "+/-2 ppm Band",
                "data_ref": data_ref,
                "x_column": "reference_exp_ppm",
                "lower_y_column": "band_lower_ppm",
                "upper_y_column": "band_upper_ppm",
                "bounds": {
                    "x": lo,
                    "y": lo - tolerance_ppm,
                    "width": hi - lo,
                    "height": (hi + tolerance_ppm) - (lo - tolerance_ppm),
                },
                "style": {"fill": C["green"], "alpha": 0.1},
            },
            {
                "id": "series-comparison",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Experimental vs Computed",
                "data_ref": data_ref,
                "x_column": "exp_ppm",
                "y_column": "calc_ppm",
                "label_column": "assignment",
                "style": {
                    "color": C["blue"],
                    "marker_size": 50,
                    "stroke": "#FFFFFF",
                    "line_width": 0.8,
                },
            },
            {
                "id": "series-reference",
                "type": "plot_series",
                "name": "y=x",
                "data_ref": data_ref,
                "x_column": "reference_exp_ppm",
                "y_column": "reference_calc_ppm",
                "style": {"color": C["grey"], "line_width": 0.8, "line_style": "--"},
            },
        ],
    )


def _save_nmr4_crystallinity_document(path, results):
    data_path = _write_nmr4_crystallinity_data(path, results)
    data_ref = "nmr-crystallinity-data"
    save_generated_figure_document(
        path,
        technique="nmr",
        figure_id="Fig-NMR4_crystallinity",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.nmr_engine.nmr_output",
            "function": "fig_nmr4_crystallinity",
            "inputs": {"result_labels": [str(result.label or "") for result in results]},
            "parameters": {"sample_count": len(results)},
        },
        style={
            "xlabel": "Sample",
            "ylabel": "Crystallinity (%)",
            "x_tick_rotation": 30,
        },
        objects=[
            {
                "id": "series-crystallinity",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "NMR Crystallinity",
                "data_ref": data_ref,
                "x_column": "label",
                "y_column": "Xc_pct",
                "style": {"palette": PAL, "line_width": 0.5, "stroke": "#FFFFFF"},
            }
        ],
    )


def _save_nmr5_region_integrals_document(path, result, tag=''):
    data_path = _write_nmr5_region_integrals_data(path, result)
    data_ref = "nmr-region-integrals-data"
    save_generated_figure_document(
        path,
        technique="nmr",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.nmr_engine.nmr_output",
            "function": "fig_nmr5_region_integrals",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "tag": str(tag or ""),
                "region_count": len(result.region_integrals),
            },
        },
        style={
            "xlabel": "Positive integral fraction (%)",
            "ylabel": "Region",
            "x_limit_min": 0.0,
        },
        objects=[
            {
                "id": "series-region-integrals",
                "type": "plot_series",
                "chart_kind": "barh",
                "name": "Region Integrals",
                "data_ref": data_ref,
                "x_column": "fraction_pct",
                "y_column": "region",
                "style": {"palette": PAL, "line_width": 0.5, "stroke": "#FFFFFF"},
            }
        ],
    )


def _write_nmr1_spectrum_data(path, result):
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ppm", "intensity"])
        writer.writeheader()
        for ppm, intensity in zip(result.ppm, result.intensity):
            writer.writerow(
                {
                    "ppm": _csv_number(ppm),
                    "intensity": _csv_number(intensity),
                }
            )
    return data_path


def _write_nmr2_deconvolution_data(path, result):
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ppm", "intensity", "fit"])
        writer.writeheader()
        for index, ppm in enumerate(result.ppm):
            writer.writerow(
                {
                    "ppm": _csv_number(ppm),
                    "intensity": _csv_number(result.intensity[index]),
                    "fit": _csv_number(result.intensity_fit[index]),
                }
            )
    return data_path


def _write_nmr3_comparison_data(path, result, lo, hi, tolerance_ppm):
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    reference_points = [
        (lo, lo, lo - tolerance_ppm, lo + tolerance_ppm),
        (hi, hi, hi - tolerance_ppm, hi + tolerance_ppm),
    ]
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "exp_ppm",
                "calc_ppm",
                "assignment",
                "reference_exp_ppm",
                "reference_calc_ppm",
                "band_lower_ppm",
                "band_upper_ppm",
            ],
        )
        writer.writeheader()
        rows = max(len(result.matches), len(reference_points))
        for index in range(rows):
            match = result.matches[index] if index < len(result.matches) else {}
            ref = reference_points[index] if index < len(reference_points) else ("", "", "", "")
            writer.writerow(
                {
                    "exp_ppm": _csv_number(match.get("exp_ppm")) if match else "",
                    "calc_ppm": _csv_number(match.get("calc_ppm")) if match else "",
                    "assignment": str(match.get("exp_assignment") or "") if match else "",
                    "reference_exp_ppm": _csv_number(ref[0]) if ref[0] != "" else "",
                    "reference_calc_ppm": _csv_number(ref[1]) if ref[1] != "" else "",
                    "band_lower_ppm": _csv_number(ref[2]) if ref[2] != "" else "",
                    "band_upper_ppm": _csv_number(ref[3]) if ref[3] != "" else "",
                }
            )
    return data_path


def _write_nmr4_crystallinity_data(path, results):
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "label",
                "Xc_pct",
                "Xc_method",
                "Xc_assignment_status",
                "nucleus",
                "sample_state",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "label": str(result.label or ""),
                    "Xc_pct": _csv_number(result.Xc_pct)
                    if np.isfinite(result.Xc_pct)
                    else "",
                    "Xc_method": str(result.Xc_method or ""),
                    "Xc_assignment_status": str(result.Xc_assignment_status or ""),
                    "nucleus": str(result.nucleus or ""),
                    "sample_state": str(result.sample_state or ""),
                }
            )
    return data_path


def _write_nmr5_region_integrals_data(path, result):
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["region", "fraction_pct", "label"])
        writer.writeheader()
        for region, value in result.region_integrals.items():
            writer.writerow(
                {
                    "region": str(region or "").replace("_", " "),
                    "fraction_pct": _csv_number(value),
                    "label": str(result.label or ""),
                }
            )
    return data_path


def _csv_number(value):
    return round(float(value), 10)


def _json_number(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def fig_nmr1_spectrum(result, out_dir, config=None, tag=''):
    fmt=config.fig_format if config else 'svg'; dpi=config.fig_dpi if config else 300
    fd,_=_dirs(out_dir)
    if len(result.ppm)==0: return ""
    fig,ax=plt.subplots(figsize=(7,3.8))
    ax.plot(result.ppm,result.intensity,color=C['dark'],linewidth=0.8)
    for i,pk in enumerate(result.peaks):
        cl=PAL[i%len(PAL)]
        ax.axvline(pk['ppm'],color=cl,linestyle=':',linewidth=0.5,alpha=0.5)
        y_text = 0.96 - (i % 3) * 0.06
        ax.text(pk['ppm'], y_text, f"{pk['ppm']:.1f}",
                fontsize=6, color=cl, ha='center', va='top',
                rotation=90, transform=ax.get_xaxis_transform())
    ax.invert_xaxis()
    set_sci_style(fig,ax,xl=f'{result.nucleus} Chemical Shift (ppm)',
                  yl='Intensity (a.u.)',title=f'NMR Spectrum \u2014 {result.label}')
    path = _save(fig,_fig_name('Fig-NMR1_spectrum', tag),fd,fmt,dpi)
    _save_nmr1_spectrum_document(path, result, tag=tag)
    return path


def fig_nmr2_deconvolution(result, out_dir, config=None, tag=''):
    fmt=config.fig_format if config else 'svg'; dpi=config.fig_dpi if config else 300
    fd,_=_dirs(out_dir)
    if len(result.intensity_fit)==0: return ""
    fig,ax=plt.subplots(figsize=(6.5,3.8))
    ax.plot(result.ppm,result.intensity,color=C['dark'],linewidth=0.8,label='Data')
    fit_label = f"Fit ($R^2$={result.r_squared:.3f})"
    fit_color = C['red']
    if np.isfinite(result.r_squared) and result.r_squared < 0.5:
        fit_label = f"Diagnostic fit ($R^2$={result.r_squared:.3f})"
        fit_color = C['orange']
    ax.plot(result.ppm,result.intensity_fit,color=fit_color,linewidth=1.2,
            linestyle='--',label=fit_label)
    for pk in result.peaks:
        ax.axvline(pk['ppm'],color=C['blue'],linestyle=':',linewidth=0.4,alpha=0.35)
    ax.invert_xaxis(); ax.legend(fontsize=8,framealpha=0.9)
    set_sci_style(fig,ax,xl=f'{result.nucleus} Chemical Shift (ppm)',
                  yl='Intensity',title=f'Peak Deconvolution \u2014 {result.label}')
    path = _save(fig,_fig_name('Fig-NMR2_deconv', tag),fd,fmt,dpi)
    _save_nmr2_deconvolution_document(path, result, tag=tag)
    return path


def fig_nmr3_comparison(result, out_dir, config=None, tag=''):
    fmt=config.fig_format if config else 'svg'; dpi=config.fig_dpi if config else 300
    fd,_=_dirs(out_dir)
    if not result.matches: return ""
    exp_ppm=[m['exp_ppm'] for m in result.matches]
    calc_ppm=[m['calc_ppm'] for m in result.matches]
    fig,ax=plt.subplots(figsize=(5.5,5.5))
    ax.scatter(exp_ppm, calc_ppm, c=C['blue'], s=50, edgecolors='white',linewidth=0.8,zorder=5)
    lo,hi=min(exp_ppm+calc_ppm)-5,max(exp_ppm+calc_ppm)+5
    ax.plot([lo,hi],[lo,hi],'--',color=C['grey'],linewidth=0.8,label='y=x')
    ax.fill_between([lo,hi],[lo-2,hi-2],[lo+2,hi+2],alpha=0.1,color=C['green'],label='+/-2 ppm')
    for m in result.matches:
        ax.annotate(m.get('exp_assignment','')[:12],(m['exp_ppm'],m['calc_ppm']),
                    textcoords='offset points',xytext=(5,5),fontsize=6)
    ax.legend(fontsize=8); ax.invert_xaxis(); ax.invert_yaxis()
    set_sci_style(fig,ax,xl='Experimental shift (ppm)',
                  yl='Computed shift (ppm)',title='Exp vs Computed')
    path = _save(fig,_fig_name('Fig-NMR3_comparison', tag),fd,fmt,dpi)
    _save_nmr3_comparison_document(path, result, tag=tag, lo=lo, hi=hi)
    return path


def fig_nmr4_crystallinity(results, out_dir, config=None):
    fmt=config.fig_format if config else 'svg'; dpi=config.fig_dpi if config else 300
    fd,_=_dirs(out_dir)
    labels=[r.label for r in results]; xc=[r.Xc_pct for r in results]
    if all(np.isnan(v) for v in xc): return ""
    fig,ax=plt.subplots(figsize=(5,3.2))
    clrs=[PAL[i%len(PAL)] for i in range(len(labels))]
    bars=ax.bar(range(len(labels)),xc,color=clrs,edgecolor='white',linewidth=0.5)
    for bar,val in zip(bars,xc):
        if not np.isnan(val):
            ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,
                    f'{val:.1f}',ha='center',va='bottom',fontsize=8,fontweight='bold')
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels,rotation=30,ha='right',fontsize=8)
    ax.set_ylabel('Crystallinity (%)')
    path = _save(fig,'Fig-NMR4_crystallinity',fd,fmt,dpi)
    _save_nmr4_crystallinity_document(path, results)
    return path


def fig_nmr5_region_integrals(result, out_dir, config=None, tag=''):
    fmt=config.fig_format if config else 'svg'; dpi=config.fig_dpi if config else 300
    fd,_=_dirs(out_dir)
    if not result.region_integrals:
        return ""
    labels=list(result.region_integrals.keys())
    values=[result.region_integrals[k] for k in labels]
    fig,ax=plt.subplots(figsize=(6.4,3.6))
    clrs=[PAL[i%len(PAL)] for i in range(len(labels))]
    bars=ax.barh(range(len(labels)), values, color=clrs, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([s.replace('_',' ') for s in labels], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, max(100.0, max(values)*1.15 if values else 100.0))
    for bar,val in zip(bars,values):
        ax.text(bar.get_width()+1.0, bar.get_y()+bar.get_height()/2,
                f'{val:.1f}%', va='center', fontsize=7)
    set_sci_style(fig,ax,xl='Positive integral fraction (%)',
                  yl='',title=f'Region Integrals - {result.label}')
    path = _save(fig,_fig_name('Fig-NMR5_region_integrals', tag),fd,fmt,dpi)
    _save_nmr5_region_integrals_document(path, result, tag=tag)
    return path


def export_parameters_csv(results, out_dir):
    import pandas as pd
    _,dd=_dirs(out_dir)
    rows=[r.parameters for r in results]
    df=pd.DataFrame(rows)
    p=os.path.join(dd,'nmr_parameters.csv'); df.to_csv(p,index=False)
    return p


def export_peaks_csv(results, out_dir):
    import pandas as pd
    _,dd=_dirs(out_dir)
    rows=[]
    for r in results:
        for pk in r.peaks:
            rows.append({
                'label': r.label,
                'nucleus': r.nucleus,
                'sample_state': r.sample_state,
                'peak_index': pk.get('index'),
                'ppm': pk.get('ppm'),
                'height': pk.get('height'),
                'fwhm_ppm': pk.get('fwhm_ppm'),
                'area': pk.get('area'),
                'integral_norm': pk.get('integral_norm'),
                'snr': pk.get('snr'),
                'region': pk.get('region'),
                'assignment': pk.get('assignment'),
                'phase': pk.get('phase'),
                'possible_solvent': pk.get('possible_solvent'),
                'prominence': pk.get('prominence'),
                'area_observed': pk.get('area_observed'),
                'fit_area': pk.get('fit_area'),
            })
    p=os.path.join(dd,'nmr_peaks.csv')
    pd.DataFrame(rows).to_csv(p,index=False)
    return p


def generate_all_figures(results, out_dir, config=None):
    figs={}
    if not results:
        return figs
    if all(len(r.ppm) == 0 for r in results):
        return figs
    multi = len(results) > 1
    for r in results:
        pf=r.label.replace(' ','_').replace('/','_')
        tag = pf if multi else ''
        p=fig_nmr1_spectrum(r,out_dir,config,tag=tag)
        if p: figs[f'{pf}_spectrum']=p
        p=fig_nmr2_deconvolution(r,out_dir,config,tag=tag)
        if p: figs[f'{pf}_deconv']=p
        p=fig_nmr3_comparison(r,out_dir,config,tag=tag)
        if p: figs[f'{pf}_comparison']=p
        p=fig_nmr5_region_integrals(r,out_dir,config,tag=tag)
        if p: figs[f'{pf}_region_integrals']=p
    if len(results)>1:
        p=fig_nmr4_crystallinity(results,out_dir,config)
        if p: figs['crystallinity']=p
    export_parameters_csv(results,out_dir)
    export_peaks_csv(results,out_dir)
    return figs
