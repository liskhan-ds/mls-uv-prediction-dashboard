import os
import json
import sqlite3
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mls_data.db")

# -----------------------------------------------------------------------------
# 1. Page Configuration & Top Navigation Bar
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MLS AI Match Prediction (2026 Season)",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Unified Top Navigation Bar (7 Sports: NBA, MLB, EPL, La Liga, NHL, NFL, MLS)
nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6, nav_col7 = st.columns(7)
with nav_col1:
    st.link_button(
        "🏀 NBA ↗", 
        "https://nba-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col2:
    st.link_button(
        "⚾ MLB ↗", 
        "https://mlb-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col3:
    st.link_button(
        "⚽ EPL ↗", 
        "https://epl-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col4:
    st.link_button(
        "⚽ La Liga ↗", 
        "https://llg-uv-prediction.streamlit.app/",
        use_container_width=True
    )
with nav_col5:
    st.link_button(
        "🏒 NHL ↗", 
        "https://nhl-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col6:
    st.link_button(
        "🏈 NFL ↗", 
        "https://nfl-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col7:
    st.button(
        "⚽ MLS (Current)", 
        disabled=True,
        use_container_width=True
    )

st.divider()

# Main Title & Subtitle
st.title("⚽ 2026 MLS AI Match Prediction Dashboard")
st.caption("Player Unit Value (UV) & Position/Starter Weighted Unit Value (WUV) 3-Way Prediction Model")

# -----------------------------------------------------------------------------
# 2. Database Loader
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_predictions_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame([])
    try:
        conn = sqlite3.connect(DB_PATH)
        df_db = pd.read_sql_query("SELECT * FROM predictions ORDER BY id ASC", conn)
        conn.close()
        return df_db
    except Exception as e:
        st.error(f"Database loading error: {e}")
        return pd.DataFrame([])

df = load_predictions_data()

if not df.empty and "actual_winner" in df.columns:
    df["total_no"] = range(1, len(df) + 1)
    stats_df = df[df["actual_winner"].notna() & (df["actual_winner"] != "") & (~df["actual_winner"].isin(["Postponed", "Canceled", "Postponed/Canceled"]))].copy()
else:
    stats_df = pd.DataFrame([])

# -----------------------------------------------------------------------------
# 3. Cumulative Prediction Performance
# -----------------------------------------------------------------------------
st.header("📊 2026 Season Cumulative Prediction Performance")

total_stats = len(stats_df)
correct_total = stats_df['is_correct'].sum() if (total_stats > 0 and 'is_correct' in stats_df.columns) else 0

col_acc, col_track = st.columns([2, 1])

if total_stats > 0:
    total_acc = (correct_total / total_stats) * 100
    status_suffix = " (⚡ God Tier)" if total_acc >= 55 else (" (🔥 Master/AI)" if total_acc >= 50 else "")
    
    with col_acc:
        st.subheader(f"Overall Completed Matches Accuracy: `{total_acc:.2f}%`{status_suffix}")
        st.markdown(f"**Correct Matches:** {int(correct_total)} / **Completed Matches:** {total_stats} (2026 Season Total Scheduled: {len(df)} Matches)")
    
    with col_track:
        remaining = 100 - total_stats
        if remaining > 0:
            st.metric("Until 100-Game System Validation", f"{remaining} Matches Remaining")
        else:
            st.metric("System Validation Status", "System Validated")
else:
    with col_acc:
        st.subheader(f"2026 Season Total Prediction Matches: `{len(df)} Matches`")
        st.markdown(f"**Total Scheduled Matches:** {len(df)} Matches (Real-time accuracy aggregation in progress)")
    with col_track:
        st.metric("System Status", "2026 Regular Season Pipeline Active")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. Weekly (Gameweek) Prediction Performance Chart
# -----------------------------------------------------------------------------
st.header("📈 Gameweek Prediction Performance")

def extract_week_num(text):
    import re
    m = re.search(r'Round\s*(\d+)|Week\s*(\d+)', str(text))
    if m:
        return int(m.group(1) or m.group(2))
    return 0

if not stats_df.empty:
    group_col = 'round_name' if 'round_name' in stats_df.columns else 'match_date'
    round_stats = stats_df.groupby(group_col, sort=False).agg(
        total_games=('home_team', 'count'),
        correct_games=('is_correct', 'sum')
    ).reset_index()

    round_stats['week_num'] = round_stats[group_col].apply(extract_week_num)
    round_stats = round_stats.sort_values('week_num').reset_index(drop=True)

    round_stats['accuracy'] = (round_stats['correct_games'] / round_stats['total_games']) * 100
    
    def get_bar_color(acc):
        if acc >= 55: return '#A020F0'      # Purple (God Tier)
        elif acc >= 50: return '#FF0000'    # Red (Master/AI)
        elif acc >= 45: return '#FFA500'    # Orange (Pro/Expert)
        elif acc >= 38: return '#1E90FF'    # Blue (Intermediate)
        elif acc >= 30: return '#008000'    # Green (Average)
        else: return '#808080'             # Gray (Below Average)

    round_stats['bar_color'] = round_stats['accuracy'].apply(get_bar_color)
    round_stats['label_text'] = round_stats.apply(
        lambda x: f"{int(x['correct_games'])}/{int(x['total_games'])}", 
        axis=1
    )

    round_stats_chart = round_stats.tail(12)

    base = alt.Chart(round_stats_chart).encode(
        x=alt.X(group_col, title='MLS Gameweek', sort=list(round_stats_chart[group_col]))
    )
    bars = base.mark_bar().encode(
        y=alt.Y('accuracy', title='Accuracy (%)', scale=alt.Scale(domain=[0, 110])),
        color=alt.Color('bar_color', scale=None),
        tooltip=[group_col, 'accuracy', 'total_games', 'correct_games']
    )
    text = base.mark_text(align='center', baseline='bottom', dy=-5, fontSize=13, fontWeight='bold').encode(
        y='accuracy', text='label_text'
    )
    st.altair_chart((bars + text).properties(height=320), use_container_width=True)
else:
    st.info("💡 2026 season full schedule built in database. Gameweek accuracy will aggregate as match results complete.")

st.markdown("""
<div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 8px; line-height: 1.5; font-size: 14px;">
    <span style="color: #A020F0;">●</span> <b>God Tier</b> (55%↑) &nbsp;&nbsp;
    <span style="color: #FF0000;">●</span> <b>Master/AI</b> (50%~55%) &nbsp;&nbsp;
    <span style="color: #FFA500;">●</span> <b>Pro/Expert</b> (45%~50%) &nbsp;&nbsp;
    <span style="color: #1E90FF;">●</span> <b>Intermediate</b> (38%~45%) &nbsp;&nbsp;
    <span style="color: #008000;">●</span> <b>Average</b> (30%~38%) &nbsp;&nbsp;
    <span style="color: #808080;">●</span> <b>Below Average</b> (30%↓)
    <br><small>* Due to 3-Way (Win/Draw/Loss) characteristics, statistical breakeven is achieved from ~46%-48% accuracy.</small>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Gameweek Report & Prediction Results Table (Matching La Liga Layout)
# -----------------------------------------------------------------------------
st.header("📋 2026 Season Gameweek Report & Prediction Results")

if not df.empty and 'round_name' in df.columns:
    unique_rounds = sorted(df['round_name'].unique(), key=extract_week_num, reverse=False)
    
    pending_df = df[df['actual_winner'].isna() | (df['actual_winner'] == '')]
    default_idx = 0
    if not pending_df.empty:
        pending_rounds = sorted(pending_df['round_name'].unique(), key=extract_week_num, reverse=False)
        target_round = pending_rounds[0]
        if target_round in unique_rounds:
            default_idx = unique_rounds.index(target_round)
            
    selected_round = st.selectbox("Select Gameweek:", unique_rounds, index=default_idx)
    filtered_df = df[df['round_name'] == selected_round].copy().reset_index(drop=True)
else:
    filtered_df = pd.DataFrame([])

if not filtered_df.empty:
    filtered_df['day_no'] = range(1, len(filtered_df) + 1)
    
    completed_in_round = filtered_df[filtered_df['actual_winner'].notna() & (filtered_df['actual_winner'] != '') & (~filtered_df['actual_winner'].isin(['Postponed', 'Canceled', 'Postponed/Canceled']))]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gameweek Total Matches", f"{len(filtered_df)} Matches")
    col2.metric("Completed Matches", f"{len(completed_in_round)} Matches")
    
    if not completed_in_round.empty:
        corr_cnt = int(completed_in_round['is_correct'].sum())
        acc = (corr_cnt / len(completed_in_round)) * 100
        col3.metric("Gameweek Accuracy", f"{acc:.1f}% ({corr_cnt}/{len(completed_in_round)})")
    else:
        col3.metric("Gameweek Accuracy", "⏳ Scheduled")

    def get_status_tag(r):
        act = r['actual_winner']
        if not act or pd.isna(act) or act == '':
            return "⏳ Pending"
        if act in ['Postponed', 'Canceled']:
            return "🚫 Postponed"
        return "✅ Correct" if r['is_correct'] == 1 else "❌ Incorrect"

    display_df = pd.DataFrame()
    display_df['No.'] = filtered_df['day_no']
    display_df['Match Time (US Eastern)'] = filtered_df.apply(
        lambda r: r['match_date_et'] if ('match_date_et' in r and pd.notna(r['match_date_et']) and r['match_date_et'] != '') else r['match_date'], axis=1
    )
    display_df['Match Time (KST)'] = filtered_df.apply(
        lambda r: r['match_date_kst'] if ('match_date_kst' in r and pd.notna(r['match_date_kst']) and r['match_date_kst'] != '') else r['match_date'], axis=1
    )
    display_df['Home Team'] = filtered_df.apply(
        lambda r: f"{r['home_team']} ({r['home_total_wuv']:.2f} WUV)" if pd.notna(r.get('home_total_wuv')) else r['home_team'], axis=1
    )
    display_df['Away Team'] = filtered_df.apply(
        lambda r: f"{r['away_team']} ({r['away_total_wuv']:.2f} WUV)" if pd.notna(r.get('away_total_wuv')) else r['away_team'], axis=1
    )
    display_df['Predicted Outcome'] = filtered_df['predicted_winner']
    display_df['3-Way Probability [Home% | Draw% | Away%]'] = filtered_df.apply(
        lambda r: f"[{r['prob_home']:.1f}% | {r['prob_draw']:.1f}% | {r['prob_away']:.1f}%]", axis=1
    )
    display_df['Predicted Gap (ΔUV)'] = filtered_df['gap'].apply(lambda x: f"{x:+.2f}")
    display_df['Actual Result'] = filtered_df.apply(
        lambda r: f"{int(r['actual_score_home'])} : {int(r['actual_score_away'])} ({r['actual_winner']})" 
        if (pd.notna(r.get('actual_score_home')) and pd.notna(r.get('actual_winner')) and r['actual_winner'] not in ['', 'Postponed', 'Canceled']) 
        else (r['actual_winner'] if (pd.notna(r.get('actual_winner')) and r['actual_winner'] != '') else "Pending"), axis=1
    )
    display_df['Accuracy Status'] = filtered_df.apply(get_status_tag, axis=1)

    # Set dynamic height to prevent inner vertical scrollbar
    calc_height = int((len(display_df) + 1) * 36 + 15)
    
    col_config = {
        "No.": st.column_config.Column(width="small"),
        "Match Time (US Eastern)": st.column_config.Column(width="medium"),
        "Match Time (KST)": st.column_config.Column(width="medium"),
        "Home Team": st.column_config.Column(width="medium"),
        "Away Team": st.column_config.Column(width="medium"),
        "Predicted Outcome": st.column_config.Column(width="medium"),
        "3-Way Probability [Home% | Draw% | Away%]": st.column_config.Column(width="medium"),
        "Predicted Gap (ΔUV)": st.column_config.Column(width="small"),
        "Actual Result": st.column_config.Column(width="medium"),
        "Accuracy Status": st.column_config.Column(width="small"),
    }
    
    st.dataframe(display_df, height=calc_height, column_config=col_config, hide_index=True, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; padding-top: 15px;">
        <p>ⓒ DROPSHOT (Business Reg: 578-81-03214)</p>
        <p>Contact us: liskhan@gmail.com</p>
    </div>
    """,
    unsafe_allow_html=True
)
