import re
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple
from clean import clean_data

REFERENCE_YEAR = 2026

ROLE_SKILLS_TAXONOMY: Dict[str, List[str]] = {
    'Data Engineer': ['python', 'spark', 'pyspark', 'airflow', 'apache airflow', 'aws', 'kafka', 'sql', 'etl', 'data pipeline', 'hadoop', 'redshift', 'snowflake', 'bigquery', 'hive', 't-sql'],
    'Frontend Engineer': ['react', 'react.js', 'react js', 'javascript', 'typescript', 'html', 'css', 'html5', 'graphql', 'vue', 'angular', 'redux', 'webpack', 'tailwind', 'next.js', 'es6'],
    'Backend Engineer': ['java', 'spring', 'springboot', 'microservices', 'python', 'sql', 'postgresql', 'postgres', 'psql', 'django', 'flask', 'fastapi', 'rest', 'api design', 'redis', 'kafka'],
    'Product Analyst': ['sql', 'tableau', 'excel', 'advanced excel', 'python', 'stats', 'statistics', 'hypothesis testing', 'a/b testing', 'split testing', 'powerbi', 'data visualization', 'metrics'],
    'DevOps / SRE': ['docker', 'kubernetes', 'k8s', 'terraform', 'aws', 'linux', 'ci-cd', 'jenkins', 'ansible', 'helm', 'cloud', 'gcp', 'azure', 'bash', 'monitoring', 'prometheus'],
    'Data Scientist': ['python', 'pandas', 'scikit-learn', 'numpy', 'machine learning', 'sql', 'stats', 'hypothesis testing', 'a/b testing', 'split testing', 'xgboost', 'nlp', 'r'],
    'QA Automation Engineer': ['selenium', 'cypress', 'cypress.io', 'python', 'java', 'test automation', 'ci-cd', 'junit', 'pytest', 'api testing', 'postman', 'appium', 'qa', 'bdd'],
    'Full Stack Engineer': ['react', 'node.js', 'nodejs', 'javascript', 'typescript', 'python', 'sql', 'docker', 'rest', 'html', 'css', 'mongodb', 'express', 'full stack', 'vuejs'],
    'Mobile Engineer': ['android', 'android sdk', 'ios', 'kotlin', 'swift', 'swiftui', 'flutter', 'dart', 'react native', 'mobile', 'xcode'],
    'ML Engineer': ['python', 'pytorch', 'torch', 'tensorflow', 'keras', 'scikit-learn', 'docker', 'kubernetes', 'k8s', 'mlops', 'mlflow', 'deep learning', 'model deployment', 'nlp']
}

ROLE_TITLE_KEYWORDS: Dict[str, List[str]] = {
    'Data Engineer': ['data engineer', 'big data', 'data platform', 'etl'],
    'Frontend Engineer': ['frontend', 'ui', 'web developer'],
    'Backend Engineer': ['backend', 'software engineer', 'java developer', 'api'],
    'Product Analyst': ['product analyst', 'data analyst', 'business analyst', 'analytics'],
    'DevOps / SRE': ['devops', 'sre', 'site reliability', 'infrastructure', 'cloud engineer'],
    'Data Scientist': ['data scientist', 'machine learning scientist'],
    'QA Automation Engineer': ['qa', 'test', 'quality', 'sdet', 'automation engineer'],
    'Full Stack Engineer': ['full stack', 'software developer'],
    'Mobile Engineer': ['mobile', 'android', 'ios', 'flutter'],
    'ML Engineer': ['ml engineer', 'machine learning engineer', 'ai engineer']
}

LEADERSHIP_COLLEGES = [
    'iit delhi', 'iitd', 'iit-d', 'i.i.t. delhi', 'iit bombay', 'iitb', 'i.i.t. bombay',
    'iit kharagpur', 'i.i.t. kharagpur', 'iit roorkee', 'i.i.t. roorkee', 'nsut', 'nsit',
    'netaji subhas university of technology', 'iit kanpur', 'iitk', 'iit hyderabad'
]

METRO_CITIES = ['bengaluru', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune', 'chennai', 'gurgaon', 'gurugram', 'noida', 'kolkata']


def identify_duplicates(clean_df: pd.DataFrame) -> pd.Series:
    clean_phones = clean_df['clean_phone']
    clean_emails = clean_df['clean_email']
    name_grad = clean_df['clean_name'] + '_' + clean_df['graduation_year'].astype(str)
    
    dup_mask = pd.Series(False, index=clean_df.index)
    seen_indices: Set[int] = set()

    for srs in [clean_phones[clean_phones != ''], clean_emails[clean_emails != ''], name_grad[clean_df['clean_name'] != '']]:
        groups = srs[srs.duplicated(keep=False)].groupby(srs).groups
        for _, indices in groups.items():
            idx_list = list(indices)
            best_idx = clean_df.loc[idx_list].isna().sum(axis=1).idxmin()
            for idx in idx_list:
                if idx != best_idx and idx not in seen_indices:
                    dup_mask.loc[idx] = True
                    seen_indices.add(idx)
    return dup_mask


def compute_role_skill_alignment(skills_series: pd.Series, applied_role_series: pd.Series) -> Tuple[pd.Series, pd.Series]:
    counts, ratios = [], []
    for s_val, role in zip(skills_series, applied_role_series):
        tokens = [t.strip() for t in re.split(r'[,;|/]+', str(s_val).lower()) if t.strip()] if pd.notna(s_val) else []
        target = ROLE_SKILLS_TAXONOMY.get(role, [])
        if not tokens or not target:
            counts.append(0); ratios.append(0.0); continue
        matched = sum(1 for tok in tokens if any(ts in tok or tok in ts for ts in target))
        counts.append(matched)
        ratios.append(matched / len(tokens))
    return pd.Series(counts, index=skills_series.index), pd.Series(ratios, index=skills_series.index)


def compute_role_title_alignment(current_title_series: pd.Series, applied_role_series: pd.Series) -> pd.Series:
    matches = []
    for title, role in zip(current_title_series, applied_role_series):
        if pd.isna(title) or pd.isna(role):
            matches.append(0)
        else:
            matches.append(int(any(kw in str(title).lower() for kw in ROLE_TITLE_KEYWORDS.get(role, []))))
    return pd.Series(matches, index=current_title_series.index)


def evaluate_integrity_and_exclusions(clean_df: pd.DataFrame) -> pd.DataFrame:
    res = pd.DataFrame(index=clean_df.index)
    years_since_grad = REFERENCE_YEAR - clean_df['graduation_year']
    age = clean_df['age']
    exp = clean_df['clean_experience']
    path_dur = clean_df['clean_career_path_duration']
    notice = clean_df['clean_notice_period']

    # 1. Fabrication anomalies
    res['is_fab_grad_age'] = ((age - years_since_grad) < 18).astype(int)
    res['is_fab_working_age'] = ((age - exp) < 18).astype(int)
    res['is_fab_exp_grad'] = ((exp - years_since_grad) > 1.5).astype(int)
    res['is_fab_path_grad'] = ((path_dur - years_since_grad) > 1.5).astype(int)
    res['is_fabricated'] = ((res['is_fab_grad_age'] == 1) | (res['is_fab_working_age'] == 1) | (res['is_fab_exp_grad'] == 1) | (res['is_fab_path_grad'] == 1)).astype(int)

    # 2. Rapid title climbers
    exec_titles = ['head of', 'director', 'vp', 'vice president', 'chief', 'manager', 'lead', 'principal']
    title_str = clean_df['current_title'].fillna('').astype(str).str.lower()
    has_exec = title_str.apply(lambda t: any(et in str(t) for et in exec_titles))
    res['is_rapid_climb'] = (has_exec & ((exp <= 3.0) | (years_since_grad <= 3))).astype(int)

    # 3. Long notice period cutoff (> 60 days)
    res['is_long_notice'] = (notice > 60.0).astype(int)

    # 4. Duplicate entries
    res['is_duplicate'] = identify_duplicates(clean_df).astype(int)

    # Master exclusion indicator
    res['is_excluded'] = ((res['is_fabricated'] == 1) | (res['is_rapid_climb'] == 1) | (res['is_long_notice'] == 1) | (res['is_duplicate'] == 1)).astype(int)
    return res


def extract_features(df: pd.DataFrame, is_test: bool = False) -> pd.DataFrame:
    """
    Computes domain-engineered features, interaction ratios, and debrief signals
    from the cleaned dataset.
    """
    clean_df = clean_data(df)
    X = pd.DataFrame(index=clean_df.index)
    X['candidate_id'] = clean_df['candidate_id']

    # Experience & Timelines
    X['age'] = clean_df['age']
    X['graduation_year'] = clean_df['graduation_year']
    X['years_since_grad'] = REFERENCE_YEAR - clean_df['graduation_year']
    X['total_experience'] = clean_df['clean_experience'].fillna(X['years_since_grad'].clip(lower=0))

    # Assessments & Ratings
    X['technical_assessment'] = clean_df['clean_technical_assessment']
    X['is_tech_missing'] = clean_df['is_tech_missing']
    X['aptitude_score'] = clean_df['clean_aptitude_score']
    X['is_aptitude_missing'] = clean_df['is_aptitude_missing']
    X['last_rating'] = clean_df['clean_last_rating']
    X['is_rating_missing'] = clean_df['is_rating_missing']
    X['kpi_met'] = clean_df['clean_kpi_met']
    X['awards'] = clean_df['clean_awards']
    X['overtime_history'] = clean_df['clean_overtime_history']

    # Notice Period & Financial Features
    X['notice_period'] = clean_df['clean_notice_period']
    X['current_ctc'] = clean_df['clean_current_ctc']
    X['expected_ctc'] = clean_df['clean_expected_ctc']
    X['ctc_hike_ratio'] = (X['expected_ctc'] - X['current_ctc']) / (X['current_ctc'].replace(0, np.nan))
    X['ctc_per_exp_year'] = X['current_ctc'] / (X['total_experience'] + 1.0)

    # Employer & Trainings
    X['num_employers'] = clean_df['num_employers']
    X['tenure_per_employer'] = X['total_experience'] / (X['num_employers'] + 1.0)
    X['company_size_ordinal'] = clean_df['clean_company_size']
    X['last_job_change'] = clean_df['clean_last_job_change']
    X['trainings_last_year'] = clean_df['trainings_last_year']
    X['training_hours'] = clean_df['training_hours']
    X['training_hours_per_session'] = X['training_hours'] / (X['trainings_last_year'] + 1.0)

    # Role & Skills Alignment Features
    skill_counts, skill_ratios = compute_role_skill_alignment(clean_df['skills'], clean_df['applied_role'])
    X['role_skill_overlap_count'] = skill_counts
    X['role_skill_overlap_ratio'] = skill_ratios
    X['role_title_match'] = compute_role_title_alignment(clean_df['current_title'], clean_df['applied_role'])

    # Colleges & Reorg Shift Features
    inst_lower = clean_df['institute'].fillna('').astype(str).str.lower()
    X['is_old_boys_college'] = inst_lower.apply(lambda s: int(any(kw in str(s) for kw in LEADERSHIP_COLLEGES)))
    tech_filled = X['technical_assessment'].fillna(0)
    X['is_non_pedigree_star'] = ((tech_filled >= 80.0) & (X['is_old_boys_college'] == 0)).astype(int)

    city_lower = clean_df['current_city'].fillna('').astype(str).str.lower()
    X['is_metro_city'] = city_lower.apply(lambda c: int(any(m in str(c) for m in METRO_CITIES)))
    X['is_referral'] = clean_df['recruitment_channel'].fillna('').astype(str).str.contains('Referral', case=False, na=False).astype(int)

    # Recruiter Note Features
    note_str = clean_df['recruiter_note'].fillna('').astype(str).str.lower()
    X['note_has_negative'] = note_str.apply(lambda n: int(any(k in str(n) for k in ['struggled with the debugging', 'lukewarm', 'missed two sprint', 'frequent guidance', 'unclear'])))
    X['note_has_positive'] = note_str.apply(lambda n: int(any(k in str(n) for k in ['strong communicator', 'primary on-call owner', 'esops', 'incident post-mortems'])))
    X['note_has_exaggeration'] = note_str.apply(lambda n: int(any(k in str(n) for k in ['shipped a feature used by 1m+', 'migration of a legacy monolith', 'ahead of sprint commitments'])))

    # Public Code Contributions (Vault only)
    X['pcc_count'] = clean_df['clean_pcc_count']
    X['pcc_sustained'] = clean_df['pcc_sustained']
    X['pcc_moderate'] = clean_df['pcc_moderate']

    # Integrity, Exclusions & Flags
    excl_df = evaluate_integrity_and_exclusions(clean_df)
    for col in excl_df.columns:
        X[col] = excl_df[col]

    # Composite & Interaction Signals
    tech_safe = X['technical_assessment'].fillna(tech_filled.median())
    apt_safe = X['aptitude_score'].fillna(5.5) * 10.0
    X['assessment_composite'] = 0.75 * tech_safe + 0.25 * apt_safe
    X['performance_index'] = 0.5 * (X['last_rating'].fillna(3.0) / 5.0) + 0.3 * X['kpi_met'] + 0.2 * X['awards']
    X['experience_efficiency'] = tech_safe / (X['total_experience'] + 1.0)
    X['applied_role'] = clean_df['applied_role']

    return X
