"""NMR output module: SCI-quality figures."""

import os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any
from .core import NMRResult
from .config import NMRConfig
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
    return _save(fig,_fig_name('Fig-NMR1_spectrum', tag),fd,fmt,dpi)


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
    return _save(fig,_fig_name('Fig-NMR2_deconv', tag),fd,fmt,dpi)


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
    return _save(fig,_fig_name('Fig-NMR3_comparison', tag),fd,fmt,dpi)


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
    return _save(fig,'Fig-NMR4_crystallinity',fd,fmt,dpi)


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
    return _save(fig,_fig_name('Fig-NMR5_region_integrals', tag),fd,fmt,dpi)


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
