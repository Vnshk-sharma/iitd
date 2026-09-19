
### 1. Role & Skill Alignment Features
- **Skill Overlap Count & Ratio**: Matches the candidate’s listed skills against specific skill taxonomies for all 10 applied roles to measure role relevance.
- **Title Alignment**: Checks if the candidate’s current job title matches the role they applied for (`role_title_match`).

---

### 2. Debrief & Reorg Signals (The New Hiring Rules)
- **Public Code Contributions Fast-Track**: Flags candidates with sustained open-source contributions (`pcc_sustained = 1` for $\ge 24$ PRs, `pcc_moderate = 1` for $\ge 12$ PRs).
- **Old-Boys' Network**: Detects candidates from Nightingale leadership alma maters (IIT Delhi, IIT Bombay, IIT Kharagpur, IIT Roorkee, NSUT) that still get an institutional boost.
- **Non-Pedigree Stars**: Identifies top technical assessment scorers ($\ge 80$) who come from non-pedigree / newly seen colleges (*"No pedigree, no problem. They love those"*).
- **Old Panel Preferences**: Flags metro locations and referrals separately so models/heuristics can down-weight obsolete preferences.

---

### 3. Integrity & Exclusion Engine
- **Fabrication Detection (`is_fabricated`)**: Catches impossible profiles (e.g. college graduation before age 18, total experience exceeding working age, experience exceeding years since graduation).
- **Rapid Title Climbers (`is_rapid_climb`)**: Flags junior profiles holding executive titles (*"Head of"*, *"Director"*, *"VP"*, *"Chief"*) with $\le 3$ years of experience (*"go straight to the bin"*).
- **Notice Period Disqualification (`is_long_notice`)**: Identifies anyone with notice period $> 60$ days (*"dead to them this cycle"*).
- **Duplicate Identification (`is_duplicate`)**: Finds candidates entered multiple times under different IDs by grouping on phone, email, and name tokens.
- **Master Filter (`is_excluded`)**: A single flag combining all the above to disqualify invalid profiles from the top 500.

---

### 4. Recruiter Note Sentiment Signals
- **Negative Notes**: Flags red flags in screening notes (*"struggled with debugging"*, *"lukewarm about teamwork"*, *"missed sprint commitments"*).
- **Positive Notes**: Flags strong operational signals (*"strong communicator"*, *"primary on-call owner"*).
- **Exaggeration Indicators**: Flags exaggerated buzzwords commonly found in fabricated profiles.

---

### 5. Composite & Interaction Features
- **`assessment_composite`**: Blended score putting 75% weight on the technical assessment and 25% on general aptitude.
- **`performance_index`**: Weighted signal combining past employer rating (50%), KPI achievement (30%), and awards won (20%).
- **`experience_efficiency`**: Ratio of technical score to years of experience (identifying fast learners).
- **`ctc_hike_ratio`**: Expected salary hike percentage over current compensation.
- **`tenure_per_employer`**: Average time spent per company (job stability indicator).
