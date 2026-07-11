"""External polymer database download sources and instructions.

All databases listed below contain polymer-relevant data.
Some are free/open-access; others require institutional access.
"""

SOURCES = {
    "ATHAS (Advanced Thermal Analysis System)": {
        "url": "https://web.utk.edu/~athas/",
        "type": "DSC / Thermodynamics",
        "access": "Free (web interface)",
        "description": "Comprehensive thermodynamic database: Tg, Tm, dHm, Cp for >200 polymers. Wunderlich group at U. Tennessee.",
    },
    "SDBS": {
        "url": "https://sdbs.db.aist.go.jp/",
        "type": "IR / NMR / MS",
        "access": "Free (registration)",
        "description": "Japanese spectral database: IR, 1H/13C NMR, Raman for >34,000 compounds.",
    },
    "NIST Chemistry WebBook": {
        "url": "https://webbook.nist.gov/chemistry/",
        "type": "IR / Thermodynamics",
        "access": "Free",
        "description": "IR spectra, thermochemical data. Good for monomers and oligomers.",
    },
    "NMRShiftDB": {
        "url": "https://nmrshiftdb.nmr.uni-koeln.de/",
        "type": "NMR",
        "access": "Free (open-source)",
        "description": "Open-source 1H/13C NMR database with REST API.",
    },
    "BMRB": {
        "url": "https://bmrb.io/",
        "type": "NMR",
        "access": "Free",
        "description": "Biological NMR data bank. Contains 13C CP/MAS for biopolymers.",
    },
    "COD (Crystallography Open Database)": {
        "url": "https://www.crystallography.net/cod/",
        "type": "WAXS / XRD",
        "access": "Free (open-access)",
        "description": "Crystal structures with CIF files. Contains polymer crystal data.",
        "howto": "1. Visit cod/cod/search.html\n2. Search polymer name\n3. Download CIF\n4. Use mercury/VESTA to get peak positions",
    },
    "ICDD PDF": {
        "url": "https://www.icdd.com/pdfsearch/",
        "type": "WAXS / XRD",
        "access": "Institutional / Paid",
        "description": "Definitive powder diffraction database for crystalline polymers.",
    },
    "PubChem": {
        "url": "https://pubchem.ncbi.nlm.nih.gov/",
        "type": "All",
        "access": "Free",
        "description": "NIH database: IR, computed properties, REST API for monomers.",
        "howto": "API: https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/<name>/record/JSON",
    },
    "KnowItAll / SpectraBase": {
        "url": "https://spectrabase.com/",
        "type": "IR / NMR / Raman",
        "access": "Free (limited) / Paid",
        "description": "Large commercial spectral database. Free tier for basic searches.",
    },
    "CROW Polymer Database": {
        "url": "https://polymerdatabase.com/",
        "type": "Thermal / Mechanical",
        "access": "Free",
        "description": "Tg, Tm, dielectric properties, solubility parameters.",
    },
    "MatWeb": {
        "url": "https://www.matweb.com/",
        "type": "Mechanical / Thermal",
        "access": "Free (registration)",
        "description": "Engineering material properties: Tg, Tm, density, modulus.",
    },
    "Polymer Handbook (Brandrup & Immergut)": {
        "url": "https://onlinelibrary.wiley.com/doi/book/10.1002/0471532053",
        "type": "All properties",
        "access": "Institutional / Paid",
        "description": "The definitive polymer reference: crystallinity, IR, NMR, X-ray for virtually all polymers.",
    },
}

def print_all_sources():
    for name, info in SOURCES.items():
        print(f"\n  [{info['type']}] {name}")
        print(f"  URL: {info['url']}")
        print(f"  Access: {info['access']}")
        print(f"  {info['description']}")
        if "howto" in info:
            print(f"  How to: {info['howto']}")
