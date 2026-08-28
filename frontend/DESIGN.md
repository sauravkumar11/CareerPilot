# CareerPilot AI — Design Notes

**Subject:** a copilot instrument panel for a job search — the product's job is to turn
a noisy stream of postings into a small number of high-signal decisions.

**Palette**
- `#0B0E14` bg — deep instrument-panel navy (not pure black)
- `#12161F` surface / `#1A2030` surface-raised
- `#242B3D` border
- `#E7EAF0` text-primary / `#8891A6` text-secondary / `#5B6478` text-muted
- `#5B8CFF` signal — the one accent, used for primary actions and focus states only
- `#3DDC97` high / `#F5A623` medium / `#FF5C7A` low — reserved exclusively for match-score
  tiers, never used decoratively, so color always carries the same meaning

**Type**
- Space Grotesk (display) — geometric, slightly technical, used sparingly for headings
- Inter (body) — neutral workhorse for UI copy
- JetBrains Mono (data) — match scores, salary figures, tags read like instrument readouts

**Signature element**
Each job card carries a **signal ring** — a radial gauge (not a percentage bar) around
the match score, styled like a radar sweep. It's the one recurring motif that ties the
"pilot" metaphor to the product's actual job: turning a listing into a single legible
signal strength at a glance.

**Restraint**
No numbered-step markers (nothing here is a sequence). No gradient hero. Motion is
limited to a card entrance stagger and the signal ring's sweep on load — no ambient
decoration.
