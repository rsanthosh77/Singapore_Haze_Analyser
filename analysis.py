"""Reproducible regional PSI summaries and weekly ecological correlations."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

REGIONS = ['north', 'south', 'east', 'west', 'central']
ROOT = Path(__file__).resolve().parent

def load_data():
    psi = pd.read_csv(ROOT / 'data/singapore_psi_sep_oct_2026.csv')
    visits = pd.read_csv(ROOT / 'data/singapore_ari_polyclinic_sep_oct_2026.csv')
    psi['timestamp'] = pd.to_datetime(psi['timestamp'], utc=True).dt.tz_convert('Asia/Singapore')
    for col in ['week_start', 'week_end']:
        visits[col] = pd.to_datetime(visits[col])
    cols = [f'{r}_psi' for r in REGIONS]
    if psi['timestamp'].duplicated().any():
        raise ValueError('Duplicate timestamps: resolve before analysis.')
    if psi[cols].isna().any().any() or (psi[cols] < 0).any().any():
        raise ValueError('Missing or negative regional PSI values.')
    psi = psi.sort_values('timestamp').reset_index(drop=True)
    psi['date'] = psi['timestamp'].dt.tz_localize(None).dt.normalize()
    psi['mean_psi'] = psi[cols].mean(axis=1)
    psi['max_psi'] = psi[cols].max(axis=1)
    return psi, visits

def regional_summary(psi):
    rows = []
    for region in REGIONS:
        s = psi[f'{region}_psi']
        rows.append({'Region': region.title(), 'Mean PSI': s.mean(), 'Peak PSI': s.max(),
                     'Unhealthy readings (%)': s.gt(100).mean()*100,
                     'Very unhealthy or worse (%)': s.gt(200).mean()*100,
                     'Days with PSI >100': psi.loc[s.gt(100), 'date'].nunique()})
    return pd.DataFrame(rows)

def align_weeks(psi, visits, lag=0):
    rows = []
    for _, v in visits.iterrows():
        start = v.week_start - pd.Timedelta(weeks=lag)
        end = v.week_end - pd.Timedelta(weeks=lag)
        sample = psi.loc[psi['date'].between(start, end)]
        expected = pd.date_range(start.tz_localize('Asia/Singapore'),
                                 (end + pd.Timedelta(days=1)).tz_localize('Asia/Singapore'),
                                 freq='h', inclusive='left')
        coverage = sample['timestamp'].isin(expected).sum() / len(expected)
        row = {'epi_week': int(v.epi_week), 'week_start': v.week_start, 'week_end': v.week_end,
               'exposure_start': start, 'exposure_end': end,
               'visits': v.avg_daily_ari_polyclinic, 'observations': len(sample),
               'coverage_pct': coverage * 100, 'complete': coverage == 1,
               'eligible': start >= psi.date.min() and end <= psi.date.max() and coverage >= .9,
               'mean_psi': sample.mean_psi.mean(), 'max_psi': sample.max_psi.max(),
               'unhealthy_pct': sample.max_psi.gt(100).mean()*100 if len(sample) else np.nan}
        for region in REGIONS:
            row[f'{region}_psi'] = sample[f'{region}_psi'].mean()
        rows.append(row)
    return pd.DataFrame(rows)

def correlations(weekly, include_partial=False):
    sample = weekly if include_partial else weekly.loc[weekly.eligible]
    rows = []
    for col in ['mean_psi', 'max_psi', 'unhealthy_pct'] + [f'{r}_psi' for r in REGIONS]:
        data = sample[[col, 'visits']].dropna()
        n = len(data)
        r = p = rho = np.nan
        if n >= 3 and data[col].nunique() > 1 and data.visits.nunique() > 1:
            r, p = pearsonr(data[col], data.visits)
            rho = spearmanr(data[col], data.visits).statistic
        rows.append({'Exposure': col, 'Weeks': n, 'Pearson r': r, 'Spearman rho': rho, 'p-value': p})
    return pd.DataFrame(rows)
