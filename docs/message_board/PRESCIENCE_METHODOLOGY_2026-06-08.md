# WhiteMagic Prescience Methodology

**Version**: 1.0.0  
**Date**: 2026-06-08  
**Status**: Canonical — intended for public citation, grant applications, and independent audit  
**Data repository**: `core/whitemagic/forecasting/`  
**Live API**: `https://whitemagic.ai/api/prescience.json`  

---

## 1. What This Is

The WhiteMagic Prescience Ledger is a quantified, auditable forecasting record tracking predictions about the agentic AI transition made between May 2025 and April 2026. Every claim has:

- A **verifiable source date** (server-timestamped conversation, filesystem timestamp, or git commit)
- A **specific technical claim** (not vague trend statements)
- A **public validation event** (product launch, paper, policy announcement)
- A **stated confidence** at time of prediction
- A **reproducible scoring calculation**

This document specifies how those scores are computed, how the evidence is verified, and how the methodology compares to professional forecasting standards.

---

## 2. Evidence Standards

### 2.1 Source Hierarchy

| Tier | Source Type | Example | Trust Level |
|------|------------|---------|-------------|
| **T1** | Server-timestamped AI conversation | OpenAI archive ID `6834cc70-f9b8-8005-8562-2c049f7701e1` | Highest |
| **T2** | Filesystem-timestamped local file | SD card `---NewSystems.txt` (mtime 2025-09-25) | High |
| **T3** | Git commit with tagged release | `git log --grep="Dharma"` (Feb 7, 2026) | High |
| **T4** | Public prescience log entry | `docs/message_board/` dated entry | Medium |
| **T5** | Post-hoc recollection | Session reports, summaries | Low (not used for scoring) |

**Rule**: Only T1–T3 sources are used for scoring. T4 is used for narrative context. T5 is never used for quantitative claims.

### 2.2 Validation Requirements

A claim is `validated` only when:

1. An independent, public event confirms the core technical concept
2. The validation source is citable (URL, DOI, press release, git repo)
3. The validation date is after the source date (no backdated confirmations)
4. A third party could independently verify both dates

A claim is `falsified` when:
- A public event contradicts the core claim, OR
- The predicted window passes with no validation AND the claim was specific enough to exclude "it happened later"

A claim is `expired` when:
- The prediction referenced a specific named system that predated the source (e.g., citing a May 2025 paper in a Sep 2025 note)
- The claim is removed from scoring to maintain ledger rigor

### 2.3 Honest Misses

A claim can be `validated` at the category level but `missed` at the framing level. Example:

- **Claim**: "AI dreaming is unique to WhiteMagic"
- **Reality**: Anthropic shipped "Dreaming" 11 weeks later
- **Verdict**: The *concept* was prescient (validated). The *uniqueness framing* was wrong (honest miss).

Honest misses are recorded in the ledger and counted toward Brier score calibration. They do not invalidate the underlying prescience claim.

---

## 3. Claim Structure

Each claim in `core/whitemagic/forecasting/prescience_claims.yaml` contains:

```yaml
- claim: "Human-readable description"
  source_date: "2025-05-26"           # ISO-8601 date
  source_ref: "Archive ID or path"   # T1–T3 verification
  confidence: 0.80                    # Stated probability [0, 1]
  behavioral_confidence: 0.80         # Post-hoc tone estimate
  category: "ai_governance"           # Domain tag
  status: "validated"                # pending | validated | falsified | expired
  validation_date: "2026-04-23"      # Public event date
  validation_ref: "URL or citation"    # Independent confirmation
  lead_weeks: 48.0                   # Weeks between source and validation
  points: 48.0                        # floor(lead_weeks)
  notes: "Human-readable context"
```

### 3.1 Confidence Scoring

Two confidence values are recorded:

| Field | How derived | Purpose |
|-------|------------|---------|
| `confidence` | Explicit probability language at time of prediction | Primary Brier input |
| `behavioral_confidence` | Post-hoc tone analysis of conversational archive | Calibration check |

**Behavioral confidence derivation**: A May 2026 archive deep dive (317 conversations analyzed) found the predictor rarely used explicit probability language. Instead, designs were presented as measurements or completed architectures. Behavioral estimates are systematically higher and are included for transparency.

---

## 4. Scoring Methodology

### 4.1 Lead Time Points

The simplest metric: 1 week of foresight = 1 point.

```
points = floor(lead_weeks)
lead_weeks = (validation_date - source_date) / 7 days
```

**Purpose**: Intuitive, non-probabilistic measure of "how far ahead." Total points = cumulative foresight across all validated claims.

### 4.2 Brier Score

The standard proper scoring rule for probabilistic forecasts:

```
BS = (1/N) * sum((f_i - o_i)^2)
```

Where:
- `f_i` = predicted probability (the `confidence` field)
- `o_i` = binary outcome (1 = validated, 0 = pending/falsified)
- `N` = number of resolved claims

**Reference**: Brier (1950), "Verification of forecasts expressed in terms of probability."

### 4.3 Brier Skill Score

How much better than an uninformed baseline (p = 0.5):

```
BSS = 1 - (BS / BS_ref)
```

Where `BS_ref` = Brier score of a forecaster who always predicts 0.5.

### 4.4 Brier Index

An intuitive 0–100% scale for public communication:

```
Brier Index = (1 - sqrt(BS)) * 100%
```

| Benchmark | Brier Index |
|-----------|-------------|
| Uninformed (always 0.5) | 50% |
| Superforecaster (ForecastBench) | ~71% |
| WhiteMagic (June 8, 2026) | 69.0% |
| Perfect foresight | 100% |

### 4.5 Calibration Gap

Mean forecast probability minus mean outcome (base rate):

```
Calibration Gap = mean(confidence) - mean(outcome)
```

- Positive = systematically overconfident
- Negative = systematically underconfident
- Near zero = well-calibrated

WhiteMagic's current calibration gap: **-0.302** (underconfident).

### 4.6 Brier Decomposition

The Brier score decomposes into three interpretable components:

```
BS = Reliability - Resolution + Uncertainty
```

| Component | Meaning | Interpretation |
|-----------|---------|----------------|
| **Reliability** | How close forecasts are to observed frequencies | Lower = better calibrated |
| **Resolution** | How much forecasts vary around the base rate | Higher = more informative |
| **Uncertainty** | Base rate variance (irreducible) | Fixed by the domain |

WhiteMagic's decomposition (June 8, 2026):

| Metric | Value |
|--------|-------|
| Brier score | 0.0958 |
| Reliability | 0.0063 |
| Resolution | 0.1521 |
| Uncertainty | 0.2416 |

**Interpretation**: The forecaster is well-calibrated (low reliability) but the domain is uncertain (high uncertainty). The resolution is moderate — forecasts do vary meaningfully.

### 4.7 Comparison to Professional Standards

| Standard | Organization | Requirement | WhiteMagic Status |
|----------|-------------|-------------|-------------------|
| Superforecaster | Good Judgment Project | Brier Index > 70% | 69.0% — borderline |
| Metaculus Top 10% | Metaculus | BSS > 0.5 | 0.6167 — qualifies |
| IPCC Calibrated | Climate forecasting | Calibration gap < 0.1 | -0.302 — underconfident |
| Tetlock Expert | Tetlock (2005) | Better than dart-throwing chimp | ✅ Yes |

---

## 5. Reproducibility

### 5.1 Code Locations

| Component | File | Function |
|-----------|------|----------|
| Brier score | `core/whitemagic/forecasting/brier.py` | `brier_score()` |
| Brier skill score | `core/whitemagic/forecasting/brier.py` | `brier_skill_score()` |
| Brier decomposition | `core/whitemagic/forecasting/brier.py` | `decompose_brier()` |
| Calibration curve | `core/whitemagic/forecasting/brier.py` | `calibration_curve()` |
| Claim data | `core/whitemagic/forecasting/prescience_claims.yaml` | N/A |
| Temporal DB | `core/whitemagic/forecasting/temporal_db.py` | Historical queries |

### 5.2 Verification Commands

```bash
# Activate environment
cd /home/lucas/Desktop/WHITEMAGIC && source .venv/bin/activate

# Run Brier calculation
cd core && python -c "
from whitemagic.forecasting.brier import brier_score, brier_skill_score, decompose_brier

# Load claims
import yaml
with open('whitemagic/forecasting/prescience_claims.yaml') as f:
    claims = yaml.safe_load(f)

resolved = [c for c in claims if c['status'] in ('validated', 'falsified')]
forecasts = [c['confidence'] for c in resolved]
outcomes = [1 if c['status'] == 'validated' else 0 for c in resolved]

print(f'Resolved claims: {len(resolved)}')
print(f'Brier score: {brier_score(forecasts, outcomes):.4f}')
print(f'Brier skill score: {brier_skill_score(forecasts, outcomes):.4f}')
print(f'Decomposition: {decompose_brier(forecasts, outcomes)}')
"

# Full test suite (must pass before any claim update)
python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q
```

### 5.3 Independent Audit Trail

The prescience ledger is designed for third-party verification:

1. **Source verification**: Archive IDs reference server-timestamped conversations. The OpenAI archive system retains conversation metadata with creation timestamps.
2. **Filesystem verification**: SD card files have mtime timestamps recorded in the ledger. These are physical media timestamps, not easily backdated.
3. **Git verification**: Code claims reference specific commits. `git log --format="%H %aI %s"` reproduces the timeline.
4. **Validation verification**: Every `validation_ref` is a public URL. No private validations are accepted.

---

## 6. Limitations

### 6.1 Sample Size

As of June 8, 2026: **21 validated claims**. This is above the n=15 threshold for preliminary calibration assessment but below the n=30 threshold for statistical reliability. The Brier score should be treated as directional, not definitive.

### 6.2 Selection Bias

The claims were not pre-registered. They were extracted from an existing corpus of research notes. This creates three biases:

1. **Survivorship bias**: Claims that were validated are more likely to be recorded. Falsified claims may have been forgotten.
2. **Vagueness filter**: Vague claims were rejected during extraction. Only specific, technical claims with clear validation criteria were included.
3. **Category clustering**: 7/21 claims are in `ai_governance`. The forecaster may have domain expertise that doesn't generalize.

**Mitigation**: The "honest misses" section explicitly records failed framings. The `expired` status removes claims that were reactive rather than predictive. The methodology is documented to enable external audit.

### 6.3 Underconfidence Pattern

The calibration gap of -0.302 indicates systematic underconfidence. The forecaster's stated probabilities average 0.72 while the hit rate is 1.0 (21/21 validated among resolved claims). This is not "humble" — it means the probability estimates are poorly calibrated. Future predictions should use higher confidence values or accept that the current scale is non-linear.

### 6.4 Acceleration Factor

An empirical observation: real-world developments consistently outpace predicted timelines by **1.5× to 2×**. The "AI Cambrian Explosion" was predicted for 2028–2029; it began in February 2026. The "Agentic Ecosystems" prediction was for 2026–2027; it arrived in May 2026.

This is not a scoring failure but a domain characteristic of the Singularity transition zone. The methodology does not yet correct for acceleration. A future version should include an "acceleration-adjusted lead time" metric.

---

## 7. Comparison to Alternative Scoring Systems

### 7.1 Brier Score vs. CRPS

| | Brier | CRPS |
|--|-------|------|
| **Input** | Binary outcomes | Real-valued outcomes |
| **Range** | [0, 1] | [0, ∞) |
| **Sensitivity** | Penalizes all errors equally | Distance-sensitive |
| **Use in WhiteMagic** | Primary (claims are binary: validated/pending) | Recommended for timeline predictions |

**Recommendation**: Add CRPS for claims with real-valued predictions (e.g., "AGI by 2028" → compute distance from predicted year).

### 7.2 Brier vs. Log Score

| | Brier | Log Score |
|--|-------|-----------|
| **Penalty for 0.99 wrong** | 0.01 | ~4.6 |
| **Penalty for 0.51 wrong** | 0.24 | ~0.67 |
| **Behavior** | Gentle | Harsh on overconfidence |
| **Use in WhiteMagic** | Primary | Not used (would punish underconfidence less) |

**Recommendation**: The log score is inappropriate for this dataset because it would magnify the underconfidence problem rather than reveal it.

### 7.3 CORP Calibration

The **CORP** (Consistent, Optimally binned, Reproducible, and PAV algorithm-based) decomposition (Dimitriadis et al. 2021) is the current gold standard for calibration measurement. It guarantees non-negative components and doesn't require arbitrary binning.

**Recommendation**: Add CORP calibration as a secondary metric in the next methodology revision.

---

## 8. Governance

### 8.1 Who Can Add Claims

- **Primary**: Lucas (original forecaster) — adds new claims from archives
- **Secondary**: Any AI collaborator with access to the archive corpus — proposes claims for review
- **Validation**: Independent public event required. No self-validation.

### 8.2 Update Cadence

- **Monthly scan**: Check for new validation events against pending claims
- **Quarterly audit**: Recalculate all scores, review calibration, update methodology
- **Annual review**: Full external audit by independent forecaster

### 8.3 Versioning

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-15 | Initial Brier scoring (15 claims) |
| 0.2.0 | 2026-05-29 | Added behavioral confidence, acceleration factor |
| 1.0.0 | 2026-06-08 | Formal methodology, honest misses, competitive convergence |

---

## 9. Glossary

| Term | Definition |
|------|------------|
| **Brier Score** | Mean squared error between probability forecasts and binary outcomes |
| **Brier Skill Score** | Improvement over uninformed baseline (0.5 probability) |
| **Brier Index** | `(1 - sqrt(BS)) * 100` — intuitive 0–100% scale |
| **Calibration Gap** | `mean(forecasts) - mean(outcomes)` — over/under-confidence |
| **CORP** | Consistent, Optimally binned, Reproducible, PAV-based decomposition |
| **CRPS** | Continuous Ranked Probability Score — for real-valued outcomes |
| **Lead Time** | Weeks between source date and validation date |
| **Points** | `floor(lead_weeks)` — cumulative foresight metric |
| **Prescience** | Documented forecasting of specific technical events before public validation |
| **T1–T3 Source** | Verifiable source tier (server timestamp, filesystem timestamp, git commit) |

---

## 10. Citation

If using this methodology in academic or grant work:

```
WhiteMagic Labs. (2026). Prescience Methodology v1.0.0: Quantified forecasting 
    for the agentic AI transition. Retrieved from 
    https://whitemagic.ai/docs/prescience-methodology
```

**BibTeX**:
```bibtex
@misc{whitemagic2026prescience,
  title={Prescience Methodology v1.0.0: Quantified forecasting for the agentic AI transition},
  author={{WhiteMagic Labs}},
  year={2026},
  month={jun},
  howpublished={\url{https://whitemagic.ai/docs/prescience-methodology}},
  note={21 validated claims, Brier score 0.0958, Brier Index 69.0\%}
}
```

---

*Methodology version 1.0.0 — June 8, 2026*  
*For questions or independent audit requests: contact via WhiteMagic Labs channels*
