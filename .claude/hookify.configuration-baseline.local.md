---
name: warn-configuration-baseline
enabled: true
event: bash
action: warn
pattern: (?i)\b(?:pip3?\s+install|dnf\s+install|yum\s+install|apt(?:-get)?\s+install|docker\s+run|docker\s+compose\s+up|docker-compose\s+up|helm\s+install|initdb|systemctl\s+enable|CREATE\s+EXTENSION)\b
---

**Rule R1 — Configuration Baseline Verification.**

You are installing or provisioning a component. Before it is configured:

**1. Does `docs/baselines/<object>.md` already exist for it?**
   - Yes, and the version matches → proceed.
   - Yes, but the version differs → the version bump is a re-review trigger. Update the baseline.
   - No → produce one first. Invoke the `configure-baseline` skill.

**2. Consult current authoritative guidance for that object *at that version*.** In order, most
authoritative last:

```
1. Vendor official documentation for the pinned version
2. Vendor security / hardening guide
3. CIS Benchmark, where one exists (PostgreSQL, RHEL, Docker, Kubernetes all have them)
4. Derayah internal standards — these override all of the above wherever stricter
```

**Documentation recalled from memory is not a valid source.** If nothing could be retrieved, record
that gap in the baseline rather than writing it from memory.

**3. Record deviations with a named Derayah approver.** A deviation with a blank approver is an
open finding, not a decision. Never infer, assume, or predict an approval.

Insecure defaults are how systems actually get compromised — not through exotic bugs, but through a
component installed and left as it shipped. This is the moment that gets skipped.

Template: `docs/baselines/_TEMPLATE.md`

*(CLAUDE.md rule 10)*
