I'd build features in four layers. Start with parsing, since the data is messy on purpose. Then add the real performance drivers, neutralize the old panel's biases, and finish with test-only rules.

## 1. Parsing (do this first; it's the foundation)

A quick pass over train showed what needs handling:

| Column | Messy forms | Parsed feature |
|---|---|---|
| `technical_assessment` | `55`, `30.0 %`, `0.43`, `absent`, `not taken` | Score on 0–100 (values ≤1 with a decimal ×100). Add `ta_missing`; about 4% are missing. |
| `aptitude_score` | `7.3`, `5.7/10` | Float out of 10 |
| `last_rating` | `3`, `3/5`, `3.0`, "Meets Expectations", "Outstanding" | 1–5 (map the words to numbers) |
| `total_experience` | `8+ yrs`, `22 months`, `Fresher`, `20+ years` | Years as a float |
| `current_ctc`, `expected_ctc` | `58.3 LPA`, `7.53 Cr`, `₹38,33,000`, `1692000` | Annual rupees (LPA ×1e5, Cr ×1e7, lakh ×1e5) |
| `notice_period` | `1 month`, `Serving notice - 30 days`, `Immediate joiner`, `2 months` | Days as an integer |
| `institute` | `BITS Pilani` vs `bits, pilani`, stray whitespace, typos | Lowercase, strip punctuation, then rapidfuzz-map to canonical names |
| `current_city` | `Mumbai` vs `mumbai`, `Madras` for Chennai | Canonical city |
| `career_path` | `->`, `>`, `|` as separators; `[23 mo]`, `(1.6y)` | A list of (title, years) pairs |

## 2. Features for the base model (real performance drivers)

- **Assessment and aptitude:** `ta`, `ta_missing`, `aptitude`, and `ta` percentile within `applied_role`. Raw `ta` only correlates about 0.21 with `post_hire_score`, so other features matter too.
- **Performance signals:** `last_rating`, `kpi_met`, `awards` (count or binary), `overtime_history`.
- **Learning:** `trainings_last_year`, `training_hours`, `currently_enrolled`.
- **Experience shape:** `total_experience`, `num_employers`, `tenure_per_employer`, `last_job_change`, and years since graduation.
- **Seniority:** map titles to a level (Intern < Trainee < Junior < plain < Senior < Lead/Staff < Manager < Head/VP). Use the current level, promotions per year, and time in the current title.
- **Role fit:** learn each role's key skills from train (skills with high lift among high scorers within that `applied_role`), then compute `role_fit` as the fraction of those skills present. Use rapidfuzz to merge variants like "Apache Kafka" and "Kafka". Add `n_skills` and `n_certs`.
- **Recruiter note:** hand-code flags. Positive: "excellent system-design", "strong ownership", "mentored". Negative: "struggled". Ignore filler such as "plays in a local cricket league". Check that this actually helps on dev before keeping it.
- **Money:** `expected_ctc / current_ctc` and `current_ctc / experience`. These are also useful for spotting fakes.

## 3. Neutralizing the old panel's biases

The voice note says the old panel inflated scores for prestige, metro, referral, big brands, degree and gaps. Train shows this. Referrals average 52.4 vs 46.9 for walk-ins, and companies of 5000–9999 people average 52.5 vs 48.5 for 50–99.

Don't only drop these columns, because correlated features can leak the same effect. A cleaner trick: **train with them in, then at prediction time set them to a constant** (a reference category or the median). The model attributes the inflation to those columns, and you switch it off for the test set. That features list is `institute` tier, `current_city`, `recruitment_channel`, `company_size`, `company_type`, `degree`, and gaps (derived from the `career_path` timeline).

The exception is the old-boys' network. To find those colleges, compute each canonical institute's mean residual from a model trained without institute (shrink small counts, for example require n ≥ 30). Cross-check against which institutes are over-represented in `dev_winners.csv`, then boost only that handful.

## 4. Test-only and rule features (these can't be learned from train)

- **`contrib_n`:** parse `~3`, `not tracked` and blanks. Add `contrib_high` at a "dozens" cutoff. In test, about 600 rows have 24 or more and about 350 have 36 or more, so pick the cutoff deliberately and document why.
- **`notice_days`:** exclude above 60.
- **`title_inflation`:** compare seniority level (or "Head of"/VP/Director) against years since graduation and years in `career_path`. Flag things like Head of X within about 3 years.
- **`new_college`:** 1 if the canonical institute has no fuzzy match to any train institute. About 93 raw test spellings are unseen, and many will collapse to seen ones after canonicalization. Boost only when `ta` is in the top percentile and `role_fit` is high.

## 5. Fabrication and duplicate flags

Build these as consistency checks, then exclude the offenders:

- Graduation age under about 20, or `total_experience` greater than `age − 18`.
- `total_experience` vs the sum of `career_path` durations vs years since graduation.
- Current title that doesn't match the last `career_path` title or `applied_role`.
- Absurd CTC for the experience level (one train row has 17.6 years and expects 7.53 Cr).
- Perfect rating, KPIs and awards that clash with weak assessment or aptitude.

For duplicates, normalize phone to its last 10 digits and email to the local part with digits stripped. Block on phone or email, then fuzzy-match names with rapidfuzz, and keep one row per person.

## 6. Final ranking

Combine the pieces like this: `score = base_model_score (neutralized) + boost(contrib_high, new_college) − exclusions`. Rank the top 500 after dropping excluded rows and duplicates.

The base model will look slightly worse on dev, since dev follows the old rules. That's expected. Use dev to confirm the pipeline works, and rely on the voice note for the rest.

Do you want me to write `clean.py` with all these parsers now, so Person A and Person B can start from the same clean columns?
