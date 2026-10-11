# Singapore Haze Observatory

Streamlit dashboard for the two supplied CSV datasets, with regional PSI trends,
daily heatmaps, PSI bands, weekly ARI associations, lag sensitivity, coverage
audits, and downloadable aligned weekly results.

## Run

Python 3.9 or newer:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Open http://localhost:8501. All timestamps are interpreted in Singapore time.

## Findings from the supplied files

- PSI: 928 rows, 1 September–11 October 2026 (partial first/last days).
- Central has the highest mean PSI (101.46); the peak is 192 in Central on
  9 October, first at 17:00 SGT. No region exceeds 200.
- At least one region exceeds 100 on 24 observed days. The strongest sustained
  deterioration occurs in early October; the ARI dataset ends on 3 October.
- ARI: six clinic weeks, 23 August–3 October. One has no PSI overlap, one has
  partial date overlap, and four fully overlapping weeks meet the primary 90%
  hourly-coverage threshold. No week has 100% coverage: every midnight is absent,
  plus 07:00 and 08:00 on 20 September.
- Across the four primary matched weeks, mean regional PSI and average daily
  ARI visits have Pearson r = 0.611, Spearman rho = 0.400, p = 0.389.
  This small positive association does not establish a reliable relationship
  or causation. Regional analyses use national visits, not regional patient data.

The dashboard includes official NEA and MOH interpretation references. Input
provenance, PSI averaging duration and PM2.5 units are unspecified; PM2.5 is not
used. The analysis cannot identify transboundary sources from PSI alone.

## Verify

```sh
.venv/bin/python -m unittest test_analysis.py
```

Tests verify calendar alignment, missing weeks, lag direction, the primary
correlation and Streamlit rendering through the main interactive controls.
