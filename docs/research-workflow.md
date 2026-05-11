# Research Workflow

This guide describes the repeatable workflow for using Baroo to find and validate long-form YouTube channel opportunities.

## 1. Choose Seed Channels

Start with channels that are close to the market you may enter.

Good seed channels:

- publish mostly long-form videos
- have at least 20 recent uploads
- show repeated viewer demand, not one accidental viral video
- have a visible format you could plausibly produce
- are monetizable without depending on risky reused content

Avoid overfitting to:

- celebrity-driven channels
- Shorts-first channels
- channels with impossible production budgets
- channels built on copyrighted clips or unclear rights
- channels where the creator personality is the product

Record why each seed channel was included. Sampling notes matter later when interpreting results.

## 2. Collect Public Data

Open `/collect`.

For each seed channel:

1. Paste the channel URL.
2. Start with 50 to 200 videos.
3. Wait for the job to complete.
4. Check `/operations` for failures or partial runs.
5. Open `/data?view=channels` and `/data?view=videos` to confirm records exist.

Recommended first-pass sample:

- 10 to 30 channels per niche.
- 50 to 100 videos per channel.
- At least two collection snapshots over time if you care about velocity.

Keep transcript collection off unless scripts are part of the research question.

## 3. Label Videos and Channels

Open `/labeling?mode=unlabeled`.

Prioritize labels that affect launch decisions:

- niche
- format
- faceless status
- visual style
- packaging pattern
- title pattern
- thumbnail pattern
- viewer promise
- curiosity type
- topic type
- production complexity
- policy risk
- monetization signals
- confidence

Use confidence honestly. Low-confidence labels are still useful if they are visibly uncertain.

Label channels when channel-level patterns are clear:

- primary niche
- primary format
- faceless status
- sponsor fit
- policy risk
- production complexity

## 4. Compute Derived Metrics

Open `/analysis`, then run **Recompute Metrics**.

Derived metrics help answer:

- Which videos outperform the channel baseline?
- Which formats repeat among outliers?
- Which topics work across more than one channel?
- Which videos have strong views per subscriber?
- Which channels look structurally strong rather than randomly lucky?

Core fields:

- `views_per_day`
- `views_per_subscriber`
- `channel_recent_median_views`
- `relative_performance`
- `performance_tier`
- `outlier_flag`
- `like_rate`
- `comment_rate`
- `engagement_rate`

Treat derived metrics as ranking aids, not final proof.

## 5. Build Candidate Theses

Open `/theses`.

Create one thesis per launchable idea. A thesis should include:

- target viewer
- viewer promise
- format
- topic universe
- production edge
- packaging edge
- monetization path
- policy-risk argument

Add evidence:

- outlier videos
- competitor channels
- repeated comment themes
- visible sponsor density
- source availability
- forum/search questions
- manual notes

Then add topics and score factors. Keep weak evidence visible.

## 6. Map Monetization

For each serious thesis, add a monetization map:

- primary revenue path
- secondary revenue path
- conservative/base/upside ad RPM
- sponsor RPM equivalent
- affiliate RPM equivalent
- membership/product/service assumptions
- break-even view count
- meaningful-income view count
- main monetization risk

Add sponsor and affiliate/product evidence when visible.

Do not move a thesis to launch until monetization has been explicitly modeled.

## 7. Red-Team the Decision

Before production, run the red-team review in `/theses`.

Answer:

- Why would better existing channels win?
- Why might monetization be weaker than expected?
- What is the failure premortem?
- What early warning signs matter?
- What preventive actions will be taken?
- What kill criteria will stop the thesis?

The goal is not to be negative. The goal is to make the decision harder to fool.

## 8. Test Packaging

Open `/packaging`.

Use the packaging lab to study:

- title patterns linked to outliers
- thumbnail patterns linked to outliers
- viewer promises
- curiosity mechanisms
- readability and specificity scores

Create packaging experiments for pilot videos before upload.

## 9. Check Rights and Disclosures

Open `/rights`.

Before uploading a pilot:

- register every asset
- mark unclear assets as blocked
- capture attribution
- record synthetic/altered content status
- confirm monetization is allowed
- write sponsor, affiliate, synthetic-media, and music disclosures where needed

Do not treat rights checks as paperwork. A monetized channel needs clean asset provenance.

## 10. Track Owned Pilots

Open `/owned`.

For owned channels only, record:

- OAuth credential metadata or token secret reference
- daily owned metrics
- retention diagnostics
- experiments
- 24h, 7d, and 30d checkpoints

Owned metrics include private Studio data such as impressions, CTR, AVD, APV, revenue, and traffic source. These fields must never be used for competitor assumptions.

## 11. Export to the Research Repo

Open `/exports`.

Recommended export for findings:

- `/export/research.zip`

Place the exported ZIP or extracted CSVs in the research repo location you choose for dataset snapshots. When writing findings, cite:

- export date
- collection date range
- channel count
- video count
- sampling method
- filters used
- known biases

Use `docs/data-dictionary.md` and the generated `data_dictionary.md` inside the ZIP to interpret fields.

## Decision Standard

A channel idea is launchable only when it has:

- public market evidence
- repeated demand signal
- plausible production edge
- strong packaging path
- modeled monetization
- acceptable rights/policy risk
- red-team review
- pilot result or defined pilot plan

The app supports the decision; it does not replace judgment.
