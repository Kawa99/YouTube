# Niche Channel Collection Summary - 2026-05-15

Source document:

```text
/home/kawa/Downloads/YouTube Niche Research Report.md
```

Collection method:

- Used the local Flask/RQ web app collection pipeline.
- Kept the existing YouTube API key unchanged.
- Collected up to 50 recent videos per channel.
- Queued all unique YouTube channel URLs explicitly listed in the report.
- Added 12 extra channel candidates from YouTube channel search for the report's top three recommended niches:
  - Corporate Fraud / Forensic Accounting
  - B2B AI Workflow Tutorials
  - Cybersecurity Incident Post-Mortems

## Results

```text
Collection runs completed: 38
Channels with videos collected: 37
Zero-video runs: 1
Videos found in this pass: 1,584
Videos saved in this pass: 1,584
Run-level failed saves: 0
Estimated YouTube API quota used by channel jobs: 150
Total channels currently in DB: 42
Total videos currently in DB: 1,684
Derived metrics rows after recompute: 1,587
```

Route checks after collection:

```text
/dashboard           200
/analysis            200
/operations          200
/data?view=videos    200
/exports             200
```

## Report Channels Collected

| Channel | Channel ID | Videos saved |
| --- | --- | ---: |
| AI Search candidate resolved as `UCT-MtBP187x-9h6phP0AA_A` | `UCT-MtBP187x-9h6phP0AA_A` | 0 |
| J.D. Houvener / Bold Patents Law Firm | `UCBQzvW6rh3Vv1YvEA9b9_uA` | 50 |
| Brick Immortar | `UCjw9YUv4UoA3d0V_Pc6zLTQ` | 50 |
| City Beautiful | `UCGc8ZVCsrR3dAuhvUbkbToQ` | 50 |
| ColdFusion | `UC4QZ_LsYcvcq7qOsOhpAX4A` | 50 |
| companyman | `UCb4xHi3i7upzKMaLrauVFtg` | 11 |
| Economics Explained | `UCZ4AMrDcNrfy3X6nsU8-rPg` | 50 |
| Fascinating Horror | `UCFXad0mx4WxY1fXdbvtg0CQ` | 50 |
| Infosec Institute | `UC4TAjYDpNggDwictUA180LA` | 50 |
| LegalEagle | `UCpa-Zb0ZcQjTCPP1Dx_1M8Q` | 50 |
| Logically Answered | `UCZRoNJu1OszFqABP8AuJIuw` | 50 |
| MagnatesMedia | `UCE4Gn00XZbpWvGUfIslT-tA` | 50 |
| Modern MBA | `UCbzVRTkX3bzNZuBd9In4XyA` | 50 |
| Patrick Boyle | `UCASM0cgfkJxQ1ICmRilfHLw` | 50 |
| Plainly Difficult | `UCb0MyY46T9ZYOzDHkYnIoXg` | 50 |
| PolyMatter | `UCgNg3vwj3xt7QOrcIDaHdFg` | 50 |
| Practical Engineering | `UCMOqf8ab-42UUQIdVoKwjlQ` | 50 |
| Real Engineering | `UCR1IuLEqb6UEA_zQ81kwXfg` | 50 |
| RealLifeLore | `UCP5tjEmvPItGyLhmjdwP7Ww` | 50 |
| Simply Cyber - Gerald Auger, PhD | `UCG-48Ki-b6W_siaUkukJOSw` | 50 |
| Talbert Law Office | `UCfB2ZoZJ-x8DCPrkDOO6Qsg` | 50 |
| TheAIGRID | `UCbY9xX3_jW5c2fjlZVBI4cg` | 50 |
| Wall Street Millennial | `UCUyH4QfXX-5NOT0bULqG6lQ` | 50 |
| WorldofAI | `UC2WmuBuFq6gL08QYG-JjXKw` | 50 |
| John Hammond | `UCVeW9qkBjo3zosnqUbG7CFw` | 50 |
| Wendover Productions | `UC9RM-iSvTu1uPJb8X5yp3EQ` | 50 |

## Additional Channels Found And Collected

| Niche | Channel | Channel ID | Videos saved |
| --- | --- | --- | ---: |
| Corporate Fraud / Forensic Accounting | LEXSPHERE FORENSICS | `UCe6VKYtGlNUb0vbH3rVxpww` | 1 |
| Corporate Fraud / Forensic Accounting | Sequence Inc. Forensic Accounting | `UCq84yRgfN7JU813CH0_7ioQ` | 50 |
| Corporate Fraud / Forensic Accounting | Workman Forensics | `UC_LtUJp2ODqiSqdYHwAAgqQ` | 50 |
| Corporate Fraud / Forensic Accounting | Brian Forensics | `UCdVWNglzGcqI88aX5FpFa-w` | 39 |
| B2B AI Workflow Tutorials | Nate Herk / AI Automation | `UC2ojq-nuP8ceeHqiroeKhBA` | 50 |
| B2B AI Workflow Tutorials | n8n | `UCiHVTkJtWSdc9N3h0nUGWLg` | 50 |
| B2B AI Workflow Tutorials | Automation Lab - n8n | `UCiM77A0IRNJ0MpPAFjL99Rg` | 11 |
| B2B AI Workflow Tutorials | N8Nitro | `UCMdQeCL4JZBfsf5_7NQhRDg` | 1 |
| Cybersecurity Incident Post-Mortems | Cyber Nash | `UC655gAo41nqlPIhi9FgNKvg` | 33 |
| Cybersecurity Incident Post-Mortems | Alfalah Studio | `UC1jn0NWTy1-SFvzTP3yB-YQ` | 50 |
| Cybersecurity Incident Post-Mortems | Cybersecurity Breach Files | `UCzDqXO1u-KYvucTYuHXS7pw` | 30 |
| Cybersecurity Incident Post-Mortems | Quick Breach | `UC7io5rmz5G-L6Jic6D0f5TQ` | 8 |

## Derived Metrics Snapshot

Performance tier counts after recomputing metrics:

| Tier | Count |
| --- | ---: |
| normal | 836 |
| outlier | 294 |
| underperformer | 280 |
| breakout | 177 |

Top relative-performance videos in the current database are currently dominated by `Brick Immortar` disaster videos. That is useful signal for documentary retention and packaging, but it also means manual niche labeling is needed before comparing the top three target niches fairly.

## Notes And Caveats

- The report's `@AISearch` URL resolved to a channel ID, but the app saved 0 videos. The worker logged a YouTube `playlistNotFound` response for that run. This may be a handle mismatch, unavailable uploads playlist, or an API resolution edge case.
- A worker log showed one `ISO8601Error` for an empty video duration during collection, but the relevant job completed and no run-level save failures were recorded.
- No manual labels were created during this pass. The database currently has 1,684 unlabeled videos.
- The additional channel candidates came from YouTube channel search and should be manually reviewed before treating them as high-quality competitors.

## Suggested Next Step

Open:

```text
http://localhost:5000/labeling
```

Prioritize labeling the newly collected videos for:

- niche
- format
- faceless status
- packaging pattern
- title pattern
- topic type
- production complexity
- policy risk

Then use:

```text
http://localhost:5000/analysis
```

to compare outliers after the labels separate cybersecurity, AI workflow, forensic accounting, legal, logistics, and disaster-documentary content.
