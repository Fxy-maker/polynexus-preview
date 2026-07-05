"""
Cross-technique validation module - v4.0 scheme section 9-10.
Provides engine-independent validation checks: phi_c triple, Tm bidirectional, L consistency.
"""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class CrossValidationResult:
    check_name: str = ""
    passed: bool = True
    severity: str = "OK"
    message: str = ""
    details: Dict[str, float] = field(default_factory=dict)


_DHM0 = {"PE":293,"HDPE":293,"LDPE":293,"iPP":207,"PP":207,"sPP":196,"PET":140,"PBT":145,"PA6":230,"PA66":255,"PTFE":82,"PEEK":130,"POM":326,"PPS":80,"PLA":93,"PVDF":105}
_TM_INF = {"PE":146,"iPP":186,"PET":280,"PA6":260,"PA66":300,"PVDF":210,"PEEK":395,"PTFE":345,"PLA":220,"PBT":245,"POM":198,"PPS":315}


def validate_triple_phi_c(phi_dsc, phi_waxs, phi_saxs, tolerance=0.05, sample_id="", weights=None):
    results = []
    weights = weights or {}
    pairs = [("DSC",phi_dsc),("WAXS",phi_waxs),("SAXS",phi_saxs)]
    available = [(n,v) for n,v in pairs if v is not None and not np.isnan(v)]
    if len(available) < 2:
        results.append(CrossValidationResult(
            check_name=f"{sample_id}/phi_c_triple" if sample_id else "phi_c_triple",
            passed=True, severity="WARN",
            message=f"phi_c check skipped: only {len(available)} technique(s)",
            details={n:v for n,v in available}))
        return results
    for i in range(len(available)):
        for j in range(i+1,len(available)):
            ni,vi=available[i]; nj,vj=available[j]
            diff=abs(vi-vj); avg=(vi+vj)/2
            rel=diff/avg if avg>0.001 else 0
            passed=rel<=tolerance
            pair_weight = min(
                float(weights.get(ni.lower(), 1.0) or 0.0),
                float(weights.get(nj.lower(), 1.0) or 0.0),
            )
            results.append(CrossValidationResult(
                check_name=f"{sample_id}/phi_c_{ni}_vs_{nj}" if sample_id else f"phi_c_{ni}_vs_{nj}",
                passed=passed, severity="OK" if passed else ("WARN" if pair_weight < 0.5 else "ERROR"),
                message=f"phi_c({ni})={vi:.3f} vs phi_c({nj})={vj:.3f} diff={diff:.3f} ({rel*100:.1f}%)",
                details={f"phi_c_{ni}":vi,f"phi_c_{nj}":vj,"abs_diff":diff,"rel_diff_pct":rel*100,"evidence_weight":pair_weight}))
    return results


def validate_tm_bidirectional(tm_dsc, L_saxs, lc_saxs, polymer_family="", sigma_e=0.093, delta_Hf=None, rho_c=1.0, tolerance=3.0, sample_id=""):
    results = []
    pfx = f"{sample_id}/" if sample_id else ""
    if tm_dsc is None or np.isnan(tm_dsc):
        results.append(CrossValidationResult(check_name=f"{pfx}Tm_GT",passed=True,severity="WARN",message="Tm check skipped: no DSC Tm"))
        return results
    if lc_saxs is None or np.isnan(lc_saxs) or lc_saxs<=0:
        results.append(CrossValidationResult(check_name=f"{pfx}Tm_GT",passed=True,severity="WARN",message="Tm check skipped: no SAXS lc"))
        return results
    if delta_Hf is None and polymer_family:
        delta_Hf = _DHM0.get(polymer_family.upper())
    if delta_Hf is None or delta_Hf<=0:
        results.append(CrossValidationResult(check_name=f"{pfx}Tm_GT",passed=True,severity="WARN",message="Tm check skipped: no delta_Hf"))
        return results
    tm_inf = _TM_INF.get(polymer_family.upper(), 300.0)
    dH_vol = delta_Hf*rho_c*1e6
    lc_m = lc_saxs*1e-9
    tm_gt = tm_inf*(1-2*sigma_e/(dH_vol*lc_m))
    diff=abs(tm_dsc-tm_gt); passed=diff<=tolerance
    results.append(CrossValidationResult(
        check_name=f"{pfx}Tm_GT",passed=passed,severity="OK" if passed else "ERROR",
        message=f"Tm(DSC)={tm_dsc:.1f}C vs Tm(GT)={tm_gt:.1f}C diff={diff:.1f}C",
        details={"Tm_DSC_C":tm_dsc,"Tm_GT_C":tm_gt,"diff_C":diff,"lc_nm":lc_saxs,"polymer":polymer_family}))
    return results


def validate_L_consistency(L_bragg, L_corr, tolerance=0.03, sample_id=""):
    pfx=f"{sample_id}/" if sample_id else ""
    if L_bragg is None or np.isnan(L_bragg):
        return CrossValidationResult(check_name=f"{pfx}L_consistency",passed=True,severity="WARN",message="L check skipped: no Bragg L")
    if L_corr is None or np.isnan(L_corr):
        return CrossValidationResult(check_name=f"{pfx}L_consistency",passed=True,severity="WARN",message="L check skipped: no corr L")
    diff=abs(L_bragg-L_corr); rel=diff/max(L_bragg,L_corr,1e-9)
    passed=rel<=tolerance
    return CrossValidationResult(check_name=f"{pfx}L_consistency",passed=passed,severity="OK" if passed else "WARN",message=f"L(Bragg)={L_bragg:.2f} vs L(corr)={L_corr:.2f} nm diff={diff:.2f} ({rel*100:.1f}%)",details={"L_bragg_nm":L_bragg,"L_corr_nm":L_corr,"diff_nm":diff,"rel_diff_pct":rel*100})


def run_all_cross_validations(sample_id="",phi_c_dsc=None,phi_c_waxs=None,phi_c_saxs=None,phi_c_weights=None,tm_dsc=None,L_saxs=None,lc_saxs=None,L_bragg=None,L_corr=None,polymer_family="",**kw):
    results={"phi_c":[],"tm":[],"L":[],"all":[]}
    pr=validate_triple_phi_c(phi_c_dsc,phi_c_waxs,phi_c_saxs,sample_id=sample_id,weights=phi_c_weights)
    results["phi_c"]=pr; results["all"].extend(pr)
    tr=validate_tm_bidirectional(tm_dsc,L_saxs,lc_saxs,polymer_family=polymer_family,sample_id=sample_id,**kw)
    results["tm"]=tr; results["all"].extend(tr)
    lr=validate_L_consistency(L_bragg,L_corr,sample_id=sample_id)
    results["L"]=[lr]; results["all"].append(lr)
    return results
