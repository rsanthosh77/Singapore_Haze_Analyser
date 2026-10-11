import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from analysis import REGIONS, load_data, regional_summary, align_weeks, correlations

st.set_page_config(page_title='Singapore Haze Observatory', page_icon='🌏', layout='wide')
st.markdown('''<style>.stApp {background:#f5f8fa;} h1,h2,h3 {color:#123c43;}
div[data-testid="stMetric"] {background:white;padding:18px;border-radius:12px;border:1px solid #dce7e8;}
</style>''', unsafe_allow_html=True)
st.title('Singapore Haze Observatory')
st.caption('Regional air quality and acute respiratory infection polyclinic attendances • September–October 2026')
try:
    psi, visits = load_data()
except Exception as error:
    st.error(f'Dataset could not be loaded: {error}')
    st.stop()

st.sidebar.header('Explore the evidence')
selected = st.sidebar.multiselect('Singapore regions', REGIONS, default=REGIONS, format_func=str.title)
dates = st.sidebar.date_input('PSI display period', value=(psi.date.min().date(), psi.date.max().date()),
                             min_value=psi.date.min().date(), max_value=psi.date.max().date())
st.sidebar.caption('Region and date filters affect the PSI views. Correlations use the full supplied datasets, aligned to clinic weeks.')
shown = psi
if isinstance(dates, (tuple, list)) and len(dates) == 2:
    shown = psi.loc[psi.date.between(pd.Timestamp(dates[0]), pd.Timestamp(dates[1]))]
if shown.empty or not selected:
    st.info('Select at least one region and a period containing readings.')
    st.stop()
cols = [f'{r}_psi' for r in selected]
area_max = shown[cols].max(axis=1)
peak_index = shown[cols].stack().idxmax()
a,b,c,d = st.columns(4)
a.metric('Mean across selected regions', f'{shown[cols].mean().mean():.1f} PSI')
b.metric('Highest regional reading', f'{shown[cols].max().max():.0f} PSI')
c.metric('Readings with any region >100', f'{area_max.gt(100).mean():.1%}')
d.metric('Days with any region >100', str(shown.loc[area_max.gt(100), 'date'].nunique()))
st.caption(f'Observed PSI: {psi.timestamp.min():%d %b %Y %H:%M} to {psi.timestamp.max():%d %b %Y %H:%M} SGT. '
           f'ARI weeks: {visits.week_start.min():%d %b}–{visits.week_end.max():%d %b %Y}. '
           '“Mean across regions” is an unweighted analytical measure, not an official national PSI.')

regional, health, quality = st.tabs(['Regional haze', 'Polyclinic association', 'Data & methodology'])
with regional:
    summary = regional_summary(shown)
    summary = summary.loc[summary.Region.str.lower().isin(selected)].sort_values('Mean PSI', ascending=False)
    worst = summary.iloc[0]
    st.subheader('What the PSI indicates')
    st.caption('Full-period pattern: short rises in early/mid September, a late-September increase, and sustained deterioration from 5–10 October. Clinic data ends on 3 October, so the strongest later episode has no matched visit data.')
    st.write(f'{worst.Region} has the highest average PSI in the selected period ({worst["Mean PSI"]:.1f}). '
             f'The peak is {shown[cols].max().max():.0f} in {peak_index[1].replace("_psi", "").title()} '
             f'on {shown.loc[peak_index[0], "timestamp"]:%d %b at %H:%M} SGT. '
             f'At least one selected region exceeds PSI 100 on {shown.loc[area_max.gt(100), "date"].nunique()} observed days.')
    st.write('Concurrent rises across Singapore’s regions indicate an island-wide pollution episode; differences in magnitude show uneven exposure. '
             'PSI alone cannot establish a transboundary haze source, fire location, wind direction or pollutant responsible. Those require meteorology, satellite hotspots and pollutant measurements.')
    granularity = st.radio('Time resolution', ['Hourly readings', 'Daily averages'], horizontal=True)
    chart_data = shown[['timestamp']+cols]
    if granularity == 'Daily averages':
        chart_data = shown.groupby('date')[cols].mean().reset_index().rename(columns={'date':'timestamp'})
    long = chart_data.melt('timestamp', var_name='Region', value_name='PSI')
    long.Region = long.Region.str.replace('_psi','').str.title()
    fig = px.line(long, x='timestamp', y='PSI', color='Region', color_discrete_sequence=px.colors.qualitative.Safe)
    for low, high, color in [(0,50,'#d9f0df'),(51,100,'#fff3bf'),(101,200,'#ffddd0'),(201,300,'#ecd5ee')]:
        fig.add_hrect(y0=low,y1=high,fillcolor=color,opacity=.25,line_width=0,layer='below')
    fig.add_hline(y=100,line_dash='dash',annotation_text='Unhealthy above 100')
    fig.update_layout(height=430, yaxis_range=[0,max(210,long.PSI.max()*1.08)], xaxis_title='Singapore time')
    st.plotly_chart(fig, use_container_width=True)
    st.caption('NEA bands: 0–50 Good • 51–100 Moderate • 101–200 Unhealthy • 201–300 Very unhealthy • >300 Hazardous. Daily averages are computed here and are not new official PSI readings.')
    left,right = st.columns([1.2,1])
    with left:
        st.subheader('Daily regional pattern')
        daily = shown.groupby('date')[cols].mean().T
        daily.index = [r.title() for r in selected]
        st.plotly_chart(px.imshow(daily, aspect='auto', color_continuous_scale='YlOrRd', labels={'color':'Mean PSI','x':'Date','y':'Region'}), use_container_width=True)
    with right:
        st.subheader('Regional exposure summary')
        st.dataframe(summary.round(1), hide_index=True, width='stretch')
    bands = pd.DataFrame({r.title():pd.cut(shown[f'{r}_psi'],[-1,50,100,200,300,float('inf')],labels=['Good','Moderate','Unhealthy','Very unhealthy','Hazardous']).value_counts(sort=False,normalize=True)*100 for r in selected})
    band_long = bands.rename_axis('Band').reset_index().melt('Band',var_name='Region',value_name='Readings (%)')
    st.plotly_chart(px.bar(band_long,x='Region',y='Readings (%)',color='Band',category_orders={'Band':list(bands.index)},color_discrete_sequence=['#55a879','#e9c46a','#f08c56','#ab6ba7','#73334d']),use_container_width=True)

with health:
    st.subheader('Does regional PSI move with ARI visits?')
    st.info('Six clinic weeks are supplied, but only four fully overlapping calendar weeks have at least 90% hourly PSI coverage. ARI attendances are average daily visits, not weekly totals or all polyclinic visits. This is a small ecological comparison, not evidence of causation.')
    lag = st.selectbox('Exposure timing', [0,1], format_func=lambda x:'Same week' if x==0 else 'Previous week PSI → current week visits')
    partial = st.checkbox('Sensitivity check: include partially observed exposure weeks', value=False)
    weekly = align_weeks(psi,visits,lag)
    stats = correlations(weekly,partial)
    matched = weekly.loc[weekly.mean_psi.notna() if partial else weekly.eligible]
    main = stats.iloc[0]
    a,b,c = st.columns(3)
    a.metric('Matched weeks',int(main.Weeks))
    b.metric('Pearson r · mean regional PSI',f'{main["Pearson r"]:.3f}' if pd.notna(main['Pearson r']) else 'Unavailable')
    c.metric('Spearman rank correlation',f'{main["Spearman rho"]:.3f}' if pd.notna(main['Spearman rho']) else 'Unavailable')
    if pd.notna(main['Pearson r']):
        direction = 'positive' if main['Pearson r']>0 else 'negative'
        st.write(f'The {len(matched)} matched weeks show a {direction} association (Pearson r = {main["Pearson r"]:.3f}; '
                 f'two-sided p = {main["p-value"]:.3f}). With so few observations, the estimate is unstable and highly sensitive to individual weeks. '
                 'Respiratory infections, seasonality, holidays, care-seeking and other exposures can affect visits. A one-week lag is exploratory and cannot resolve these confounders.')
    if partial:
        st.warning('Partial exposure weeks compare a subset of PSI readings with a full clinic week and can bias correlations. Weeks with zero PSI readings remain excluded.')
    fig = make_subplots(specs=[[{'secondary_y':True}]])
    fig.add_trace(go.Bar(x=weekly.week_start,y=weekly.visits,name='Average daily ARI visits',marker_color='#26848b'),secondary_y=False)
    fig.add_trace(go.Scatter(x=weekly.week_start,y=weekly.mean_psi,name='Weekly mean regional PSI',mode='lines+markers',line_color='#e88644'),secondary_y=True)
    fig.update_yaxes(title_text='Average daily visits',secondary_y=False)
    fig.update_yaxes(title_text='Mean regional PSI',secondary_y=True)
    fig.update_layout(height=350,xaxis_title='Clinic week starting (exposure timing as selected)')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('Separate vertical scales: visual alignment of these series does not measure association. Missing exposure weeks have no PSI point; weeks below the primary coverage rule appear here but are excluded from the default statistics.')
    if len(matched):
        scatter = px.scatter(matched,x='mean_psi',y='visits',text='epi_week',hover_data=['exposure_start','coverage_pct'],labels={'mean_psi':'Weekly mean across five regions (PSI)','visits':'Average daily ARI visits','epi_week':'Epi week'})
        scatter.update_traces(marker_size=13,textposition='top center')
        st.plotly_chart(scatter,use_container_width=True)
    st.subheader('Regional and exposure sensitivity')
    st.dataframe(stats.round(3),hide_index=True,width='stretch')
    st.caption('Regional PSI averages are compared with the same national ARI series; these are not regional patient correlations. Multiple exploratory tests are unadjusted; p-values assume independent pairs, which time series may violate.')
    st.subheader('Week alignment audit')
    st.dataframe(weekly.round(2),hide_index=True,width='stretch')
    st.download_button('Download weekly analysis',weekly.to_csv(index=False),'weekly_haze_ari_analysis.csv','text/csv')

with quality:
    expected = pd.date_range(psi.timestamp.min(),psi.timestamp.max(),freq='h')
    missing = expected.difference(pd.DatetimeIndex(psi.timestamp))
    st.subheader('Coverage and provenance')
    st.write(f'{len(psi):,} timestamped PSI rows, {len(missing)} missing hourly timestamps within the observed span, '
             f'{psi.date.nunique()} observed calendar days; {len(visits)} ARI weekly rows. '
             'File names and columns do not establish source authenticity, PSI averaging duration or PM2.5 units. '
             'Results describe the supplied files; their provenance has not been independently verified. PM2.5 columns are not used in this PSI-only exposure analysis.')
    if len(missing):
        st.dataframe(pd.DataFrame({'Missing timestamp (SGT)':missing}),hide_index=True)
    st.markdown('''- Each row is a timestamped regional PSI observation. Percentages count observed readings, not independent hours of exposure; successive rolling PSI values may overlap.
- Primary exposure is the unweighted average of the five regional PSI series, aggregated over each supplied clinic week. Weekly peak and the percentage of observations with any region above 100 are sensitivity measures.
- Primary eligible weeks must fall entirely within the observed calendar-date span and have at least 90% of the 168 expected hourly timestamps. This pragmatic coverage rule retains four weeks despite systematic midnight omissions; complete indicates strict 100% coverage (none qualify). No missing observations are imputed. Prior-week exposure is matched by calendar dates, not by shifting available rows.
- Pearson measures linear association; Spearman measures rank association. Only matched weeks are counted, avoiding replication of one weekly visit value across hourly observations.
- The short period, aggregate patient data and missing exposure weeks prevent causal attribution or reliable estimation of a haze-related visit burden.
''')
    st.subheader('Authoritative interpretation references')
    st.markdown('''[NEA: PSI computation](https://www.haze.gov.sg/docs/default-source/faq/computation-of-the-pollutant-standards-index-%28psi%29.pdf) explains that PSI is based on pollutant sub-indices, so it does not identify a pollution source.

[NEA: Managing haze](https://www.nea.gov.sg/our-services/pollution-control/air-pollution/managing-haze) provides PSI bands and health advisories.

[MOH: National infection prevention guidelines for primary care](https://www.moh.gov.sg/docs/librariesprovider4/default-document-library/national-ipc-guidelines-for-primary-care_on-moh-website_finalcfeeec720d8e48c88e26b91118c6736f.pdf) describes weekly surveillance of average daily polyclinic attendances for common infections.
''')
    st.subheader('Input datasets')
    st.dataframe(psi.drop(columns=['date','mean_psi','max_psi']),hide_index=True,width='stretch')
    st.dataframe(visits,hide_index=True,width='stretch')
