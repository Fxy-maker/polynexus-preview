# SAXS AI prompt protection contract design

The prompt builder already receives the active preprocessing policy, but its
intent example substitutes the protected-feature field with the vague phrase
`policy-approved feature names`. That is insufficient for the SAXS bridge,
whose validator requires a complete seven-feature set.

The prompt will render `policy.allowed_protected_features` as a JSON array.
For SAXS it will additionally state that every listed feature is mandatory;
for other techniques it will retain generic policy wording. The core validator
remains authoritative, so prompt changes cannot grant model output any extra
authority.
