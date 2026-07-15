# Niche Analysis Findings - 2026-05-15

This is the first-pass interpretation of the channel/video data collected from the niche research report and the additional YouTube channel-search candidates.

The labels are Codex-inferred from channel identity, title patterns, and the source report's niche mapping. They are useful for sorting and prioritizing, but should be spot-checked before final strategic decisions.

## What Was Done

- Labeled all `1,684` videos in the database.
- Added label audit rows with reviewer `codex_first_pass` or `codex_first_pass_cleanup`.
- Recomputed derived metrics from the container CLI.
- Verified these app pages still load:

```text
/dashboard             200
/analysis              200
/labeling              200
/data?view=videos      200
```

Note: `POST /analysis/compute` timed out under Gunicorn for this dataset size, but `compute_derived_metrics()` succeeded from the container CLI:

```text
videos_computed: 1,587
channels_computed: 38
```

That suggests the recompute work should be moved to a background job or the web worker timeout should be increased.

## Fast Read

The strongest practical opportunity is still **B2B AI workflow tutorials**, but with a narrower angle than generic AI tools:

```text
AI workflow implementation for specific business jobs.
```

The data supports this because:

- B2B AI workflow videos have meaningful absolute demand, not just tiny-channel relative spikes.
- The production burden is low: screen recording, clear voiceover, templates, and workflow diagrams.
- The monetization path is direct: SaaS affiliate, templates, consulting, sponsorships.
- The successful titles are concrete implementation promises, not generic tool news.

The second-best opportunity is **cybersecurity technical/tutorial content**, but it needs careful framing because some high-relative-performance examples are very small channels or offensive-security topics that may have policy and advertiser concerns.

The third-best opportunity is **forensic accounting/corporate fraud**, but not as accountant talking-head videos. The current small forensic-accounting channels show relative outliers, yet low absolute views. The better angle is to combine that domain with the packaging style of `Modern MBA`, `MagnatesMedia`, and `Wall Street Millennial`.

## Subniche Summary

| Subniche | Videos | Channels | Median views | Avg relative performance | Outlier/breakout videos | Outlier rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| forensic accounting | 140 | 4 | 79 | 3.37 | 49 | 35.0% |
| B2B AI workflow tutorials | 112 | 4 | 11,716 | 4.20 | 28 | 25.0% |
| AI tools and workflows | 100 | 2 | 19,089 | 1.41 | 19 | 19.0% |
| cybersecurity technical tutorials | 83 | 2 | 3,891 | 5.86 | 35 | 42.2% |
| cybersecurity incident post-mortems | 38 | 2 | 112 | 6.43 | 14 | 36.8% |
| cybersecurity training | 50 | 1 | 486 | 1.80 | 14 | 28.0% |
| business strategy case studies | 50 | 1 | 583,414 | 2.14 | 22 | 44.0% |
| business documentary | 50 | 1 | 366,844 | 7.82 | 30 | 60.0% |
| corporate finance case studies | 50 | 1 | 103,546 | 1.29 | 8 | 16.0% |
| macroeconomics explainers | 50 | 1 | 466,887 | 1.58 | 7 | 14.0% |
| patent law and IP | 50 | 1 | 26 | 4.76 | 19 | 38.0% |
| logistics and systems explainers | 50 | 1 | 1,277,497 | 1.51 | 10 | 20.0% |
| industrial disaster documentary | 50 | 1 | 644,502 | 81.32 | 37 | 74.0% |

Interpretation caution: very low median views plus high relative performance usually means the channel is small and volatile. It is useful as an underserved-search signal, not proof of broad demand.

## Ranked Opportunities

### 1. B2B AI Workflow Tutorials

Verdict: **best first test**

Representative outliers:

| Channel | Video | Views | Relative performance | Pattern |
| --- | --- | ---: | ---: | --- |
| n8n | One Click Connect n8n to AI Tools | 590,267 | 116.75 | how-to / transformation |
| n8n | How to use skills in n8n agents | 319,590 | 74.89 | how-to / specific question |
| n8n | n8n Quick Start Tutorial: Build Your First AI Agent | 274,746 | 64.38 | how-to / transformation |
| Automation Lab - n8n | Build an AI Restaurant Booking System with WhatsApp, ChatGPT & Google Sheets | 1,760 | 31.15 | how-to / transformation |
| Automation Lab - n8n | Automate Invoice Data Entry with n8n, ChatGPT & Google Sheets | 1,193 | 21.12 | how-to / specific question |

What the data says:

- Specific workflow builds outperform vague AI commentary.
- `n8n` and implementation-heavy channels validate demand for hands-on tutorials.
- Small channels can still produce relative outliers when the title maps to a concrete business task.

Recommended positioning:

```text
AI automation tutorials for one business role at a time.
```

Better than:

```text
Generic AI tools, AI news, or top-10 lists.
```

Good first angles:

- `Automate invoice data entry with n8n, Gmail, Google Sheets, and GPT`
- `Build a lead qualification bot for a small agency`
- `Turn client emails into CRM tasks automatically`
- `Create a support-ticket triage workflow with n8n`
- `Automate weekly KPI reports from Google Sheets`

Production fit:

- Low production burden.
- Strong faceless fit.
- Easy to monetize with templates, consulting, and SaaS affiliates.

### 2. Cybersecurity Technical Tutorials

Verdict: **promising, but needs safer packaging**

Representative outliers:

| Channel | Video | Views | Relative performance | Pattern |
| --- | --- | ---: | ---: | --- |
| Cyber Nash | CTF: Hacking Sau | 17,332 | 150.71 | case-study |
| Cyber Nash | How to scan for vulnerabilities using nmap | 9,223 | 66.59 | how-to / specific question |
| Cyber Nash | How to solve the M57Biz Forensics Case | 6,374 | 55.43 | how-to / specific question |
| John Hammond | Clawdbot Malware | 115,038 | 16.33 | case-study |

What the data says:

- Technical specificity wins.
- CTF, malware, vulnerability scanning, and forensic walkthroughs have strong relative pull.
- Absolute views are smaller than mainstream documentaries, but the audience has high B2B value.

Risk:

- Some offensive-security topics can look advertiser-sensitive if framed as hacking rather than defense.

Safer angle:

```text
Defensive incident reconstruction and blue-team forensics.
```

Good first angles:

- `How attackers used one leaked password to breach a company`
- `The 30-minute incident response checklist after a phishing breach`
- `How to read a ransomware incident report`
- `What a SOC analyst actually does during an alert`
- `How to investigate suspicious login activity`

### 3. Corporate Fraud / Forensic Accounting

Verdict: **high-value niche, but the current competitor sample is too small-channel**

Representative outliers:

| Channel | Video | Views | Relative performance | Pattern |
| --- | --- | ---: | ---: | --- |
| Sequence Inc. Forensic Accounting | What is Fraud? 4 Legal Elements | 13,883 | 65.03 | warning / consequence |
| Sequence Inc. Forensic Accounting | Why Audits Don't Find Fraud | 6,817 | 31.93 | warning / consequence |
| Brian Forensics | How to detect fraud in financial statements | 743 | 27.52 | how-to / specific question |
| Sequence Inc. Forensic Accounting | Fraudulent Financial Reporting | 4,470 | 20.94 | warning / consequence |

What the data says:

- Pure forensic-accounting channels show strong relative outliers but low absolute reach.
- The topic is underserved, but current small channels often lack packaging and cinematic storytelling.
- The best commercial version is probably not a small CPA-style explainer channel.

Recommended format:

```text
Modern MBA / MagnatesMedia style, but with forensic-accounting mechanics.
```

Good first angles:

- `Why audits miss fraud: the accounting trick behind major scandals`
- `How companies hide losses without technically lying`
- `The balance-sheet trick that fooled investors`
- `How one missing footnote revealed a fraud`
- `How fake revenue actually appears in financial statements`

### 4. Business Strategy / Business Documentary

Verdict: **proven demand, harder to enter**

Representative outliers:

| Channel | Video | Views | Relative performance |
| --- | --- | ---: | ---: |
| Modern MBA | Why Crumbl Cookies Can't Survive | 2,221,265 | 7.17 |
| Modern MBA | The Secret Business of Nightclubs | 1,872,861 | 6.05 |
| Modern MBA | The Rigged Economics of Airlines | 1,864,343 | 6.02 |
| MagnatesMedia | Rockefeller: The World's First Billionaire | 7,565,022 | 77.71 |

What the data says:

- Huge audience.
- Strong packaging patterns: business model, rigged economics, secret business, downfall.
- Production/research burden is much higher than AI workflows.

This is better as a later expansion after proving research, pacing, and thumbnails.

### 5. Supply Chain / Logistics / Systems Explainers

Verdict: **excellent audience, high production burden**

Representative outliers:

| Channel | Video | Views | Relative performance |
| --- | --- | ---: | ---: |
| Wendover Productions | Why Budget Airlines are Suddenly Failing | 3,725,148 | 3.90 |
| Wendover Productions | How the Trucking Industry Got So Terrible | 3,687,980 | 3.86 |
| Wendover Productions | How Arenas Transform Overnight | 3,065,132 | 3.21 |

What the data says:

- Very strong absolute demand.
- Harder for a solo operator because viewers expect maps, motion graphics, and polished editing.
- Better fit if the channel has a map-animation workflow or outsourced editing.

## Packaging Patterns That Repeatedly Worked

Across target niches, these patterns produced many outliers:

| Pattern | Why it works |
| --- | --- |
| `how_to` + `transformation` | Strong for B2B AI workflows because it promises implementation and a tangible before/after. |
| `how_to` + `specific_question` | Strong for tutorials and high-intent search. |
| `warning` + `consequence` | Strong for fraud, cybersecurity, and disaster narratives because stakes are immediately clear. |
| `curiosity_gap` + `hidden_system` | Strong for business documentaries and systems explainers. |
| `case_study` + `strong_claim` | Works broadly, but can become generic unless the claim is specific. |

Avoid overusing generic strong claims without a specific mechanism. The stronger titles usually answer:

```text
What exactly happened?
Why did it happen?
What hidden system caused it?
How do I implement/fix/avoid it?
```

## What To Do Next

Start with one test sprint in **B2B AI workflows**.

Create 5 videos, all screen-recorded and template-driven:

1. `I Built an AI Client Onboarding System with n8n`
2. `Automate Invoice Data Entry with Gmail, Sheets, and GPT`
3. `Build a Lead Qualification Bot for a Small Agency`
4. `Turn Customer Emails into Support Tickets Automatically`
5. `Create a Weekly KPI Report Agent for Your Business`

Success criteria:

- At least one video reaches 2x to 5x the channel median once the channel has enough uploads.
- Comments ask for templates, workflows, or exact setup help.
- Viewers ask for niche variants, such as real estate, agencies, ecommerce, or accountants.

If the sprint works, double down on one vertical:

```text
AI workflows for agencies
AI workflows for accountants
AI workflows for real estate operators
AI workflows for ecommerce teams
```

Second sprint option:

```text
Cybersecurity incident response for small businesses.
```

Third sprint option:

```text
Forensic accounting documentaries with animated ledgers.
```

## App/Data Notes

- All videos are now labeled, but labels are first-pass inferred labels, not manually verified ground truth.
- The `subniche` value is currently stored in `video_labels.notes`, not a dedicated schema field.
- `POST /analysis/compute` timed out through Gunicorn, but the CLI recompute worked. Consider moving metric recompute to RQ.
- One collected channel, `Alfalah Studio`, was an off-niche YouTube search result and should be excluded from target-niche decisions.
