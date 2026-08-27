# WAXS Configuration and Context Design

WAXS defaults remain generic numerical defaults. A caller-provided WAXSConfig must be preserved, because replacing it makes both human edits and AI proposals ineffective. An optional project context may supply techniques.waxs.polymer_type as an explicit crystal-form hint; it is applied only when the config has no value. No hint is inferred from filenames or material names.
