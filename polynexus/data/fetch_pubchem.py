"""Bulk-download helper for polymer databases.

Run:  python -m polynexus.data.fetch_pubchem PE iPP PET
Fetches molecular properties from PubChem for each polymer monomer.

Also supports:
    python -m polynexus.data.fetch_pubchem --all
    python -m polynexus.data.fetch_pubchem --search "polyethylene"
"""

import logging
logger = logging.getLogger(__name__)

import sys, json

PUBMED_REST = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Monomer SMILES for common polymers (used as PubChem search keys)
MONOMER_NAMES = {
    "PE": "ethylene",
    "iPP": "propylene",
    "PET": "ethylene terephthalate",
    "PA6": "caprolactam",
    "PCL": "epsilon-caprolactone",
    "PLLA": "lactic acid",
    "PVDF": "vinylidene fluoride",
    "POM": "formaldehyde",
    "PS": "styrene",
    "PMMA": "methyl methacrylate",
    "PTFE": "tetrafluoroethylene",
    "PEEK": "4,4-difluorobenzophenone hydroquinone",
}


def fetch_pubchem(compound_name):
    """Fetch PubChem data for a compound."""
    import urllib.request, urllib.error

    url = (
        f"{PUBMED_REST}/compound/name/{compound_name}/property/"
        f"MolecularWeight,MolecularFormula,CanonicalSMILES,IUPACName/JSON"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PolyNexus/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
        return {
            "name": compound_name,
            "formula": props.get("MolecularFormula", ""),
            "mw": props.get("MolecularWeight", ""),
            "smiles": props.get("CanonicalSMILES", ""),
            "iupac": props.get("IUPACName", ""),
            "error": None,
        }
    except urllib.error.HTTPError as e:
        return {"name": compound_name, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"name": compound_name, "error": str(e)}
        logger.warning("异常已处理", exc_info=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m polynexus.data.fetch_pubchem <polymer_keys...>")
        print("  e.g.: python -m polynexus.data.fetch_pubchem PE iPP PET PA6")
        print()
        print("Available keys:", ", ".join(MONOMER_NAMES.keys()))
        return

    if sys.argv[1] == "--all":
        keys = list(MONOMER_NAMES.keys())
    else:
        keys = [k.upper() for k in sys.argv[1:]]

    results = {}
    for key in keys:
        if key not in MONOMER_NAMES:
            print(f"Unknown polymer: {key}")
            continue
        name = MONOMER_NAMES[key]
        print(f"Fetching {key} ({name})...")
        data = fetch_pubchem(name)
        results[key] = data
        if data.get("error"):
            print(f"  ERROR: {data['error']}")
        else:
            print(f"  {data.get('formula','?')}  MW={data.get('mw','?')}")

    # Save results
    if results:
        out_path = "pubchem_polymers.json"
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()