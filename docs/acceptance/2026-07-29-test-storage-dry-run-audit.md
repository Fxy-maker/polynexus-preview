# Test-storage dry-run audit

The completed report ran in `dry-run` mode with empty stderr:

```text
total: 556 artifacts, 236 eligible, 320 protected
total eligible bytes: 90,330,056,419 (~90.33 GB)
removed: 0

C: paths: 306 artifacts, 212 eligible, 94 protected
C: eligible bytes: 76,691,802,567 (~76.69 GB)
C: removed: 0
```

No `--apply` operation was performed. The eligible list is a candidate list,
not proof that every path is safe for deletion without the explicit cleanup
command's final protections and user authorization.
