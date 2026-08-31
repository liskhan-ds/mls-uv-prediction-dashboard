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
# 1. 페이지 기본 설정 및 통일된 상단 네비게이션
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MLS AI 승부예측 (2026 시즌)",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 상단 탭 네비게이션 (NBA, MLB, EPL, NHL, NFL, MLS 통합 배치)
nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6 = st.columns(6)
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
        "🏒 NHL ↗", 
        "https://nhl-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col5:
    st.link_button(
        "🏈 NFL ↗", 
        "https://nfl-uv-prediction-dashboard.streamlit.app/",
        use_container_width=True
    )
with nav_col6:
    st.button(
        "⚽ MLS (현재)", 
        disabled=True,
        use_container_width=True
    )

st.divider()

# 메인 타이틀 및 시즌 정보
st.title("⚽ 2026 MLS AI 승부예측 대시보드")
st.caption("선수별 Unit Value (UV) 및 포지션/주전 가중치 기반 팀 Weighted Unit Value (WUV) 3-Way 승부예측 모델")

# -----------------------------------------------------------------------------
# 2. 데이터 베이스 로딩 함수
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
        st.error(f"데이터베이스 로딩 오류: {e}")
        return pd.DataFrame([])

df = load_predictions_data()

if not df.empty and "actual_winner" in df.columns:
    df["total_no"] = range(1, len(df) + 1)
    stats_df = df[df["actual_winner"].notna() & (df["actual_winner"] != "") & (~df["actual_winner"].isin(["경기 연기", "경기 취소", "연기됨", "취소됨"]))].copy()
else:
    stats_df = pd.DataFrame([])

# -----------------------------------------------------------------------------
# 3. 누적 예측 성적표
# -----------------------------------------------------------------------------
st.header("📊 2026 시즌 누적 예측 성적표")

total_stats = len(stats_df)
correct_total = stats_df['is_correct'].sum() if (total_stats > 0 and 'is_correct' in stats_df.columns) else 0

col_acc, col_track = st.columns([2, 1])

if total_stats > 0:
    total_acc = (correct_total / total_stats) * 100
    status_suffix = " (⚡ 신계, 시장 왜곡급)" if total_acc >= 55 else (" (🔥 AI 초고수)" if total_acc >= 50 else "")
    
    with col_acc:
        st.subheader(f"전체 완료 경기 적중률: `{total_acc:.2f}%`{status_suffix}")
        st.markdown(f"**적중 경기 수:** {int(correct_total)} / **완료 경기 수:** {total_stats} (2026 시즌 총 예정: {len(df)}경기)")
    
    with col_track:
        remaining = 100 - total_stats
        if remaining > 0:
            st.metric("100경기 시스템 검증까지", f"{remaining}경기 남음")
        else:
            st.metric("시스템 검증 상태", "검증 완료 (신계 등급)")
else:
    with col_acc:
        st.subheader(f"2026 시즌 전체 예측 대상: `{len(df)} 경기`")
        st.markdown(f"**전체 예정 경기:** {len(df)} 경기 (실시간 적중률 집계 준비 중)")
    with col_track:
        st.metric("시스템 상태", "2026 정규시즌 파이프라인 가동 중")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. 주차별(Matchweek) 예측 성적표 (Altair 바 차트)
# -----------------------------------------------------------------------------
st.header("📈 주차별(Matchweek) 예측 성적표")

def extract_week_num(text):
    import re
    m = re.search(r'Week\s*(\d+)', str(text))
    return int(m.group(1)) if m else 0

if not stats_df.empty:
    group_col = 'round_name' if 'round_name' in stats_df.columns else 'match_date'
    round_stats = stats_df.groupby(group_col, sort=False).agg(
        total_games=('home_team', 'count'),
        correct_games=('is_correct', 'sum')
    ).reset_index()

    round_stats['accuracy'] = (round_stats['correct_games'] / round_stats['total_games']) * 100
    
    def get_bar_color(acc):
        if acc >= 55: return '#A020F0'      # 보라 (신계)
        elif acc >= 50: return '#FF0000'    # 빨강 (초고수/AI)
        elif acc >= 45: return '#FFA500'    # 주황 (프로/고수)
        elif acc >= 38: return '#1E90FF'    # 파랑 (일반인)
        elif acc >= 30: return '#008000'    # 녹색 (정상인)
        else: return '#808080'             # 회색 (예측 금지)

    round_stats['bar_color'] = round_stats['accuracy'].apply(get_bar_color)
    round_stats['label_text'] = round_stats.apply(
        lambda x: f"{int(x['correct_games'])}/{int(x['total_games'])}", 
        axis=1
    )

    round_stats_7d = round_stats.tail(10)

    base = alt.Chart(round_stats_7d).encode(x=alt.X(group_col, title='2026 MLS 주차 (Matchweek)', sort=None))
    bars = base.mark_bar().encode(
        y=alt.Y('accuracy', title='적중률(%)', scale=alt.Scale(domain=[0, 110])),
        color=alt.Color('bar_color', scale=None),
        tooltip=[group_col, 'accuracy', 'total_games', 'correct_games']
    )
    text = base.mark_text(align='center', baseline='bottom', dy=-5, fontSize=13, fontWeight='bold').encode(
        y='accuracy', text='label_text'
    )
    st.altair_chart((bars + text).properties(height=320), use_container_width=True)
else:
    st.info("💡 2026 시즌 전체 일정이 데이터베이스에 구축되었습니다. 경기 결과 입력 시 주차별 적중률이 집계됩니다.")

st.markdown("""
<div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 8px; line-height: 1.5; font-size: 14px;">
    <span style="color: #A020F0;">●</span> <b>신계</b> (55%↑) &nbsp;&nbsp;
    <span style="color: #FF0000;">●</span> <b>초고수/AI</b> (50%~55%) &nbsp;&nbsp;
    <span style="color: #FFA500;">●</span> <b>프로/고수</b> (45%~50%) &nbsp;&nbsp;
    <span style="color: #1E90FF;">●</span> <b>일반인</b> (38%~45%) &nbsp;&nbsp;
    <span style="color: #008000;">●</span> <b>정상인</b> (30%~38%) &nbsp;&nbsp;
    <span style="color: #808080;">●</span> <b>예측 금지</b> (30%↓)
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. 주차별 경기 리포트 (Week 단위 일정 및 예측 결과 카드/테이블)
# -----------------------------------------------------------------------------
st.header("📋 2026 시즌 주차별 경기 리포트 & 예측 결과")

if not df.empty and 'round_name' in df.columns:
    unique_rounds = sorted(df['round_name'].unique(), key=extract_week_num, reverse=False)
    
    # Auto-select upcoming or latest round
    pending_df = df[df['actual_winner'].isna() | (df['actual_winner'] == '')]
    default_idx = 0
    if not pending_df.empty:
        pending_rounds = sorted(pending_df['round_name'].unique(), key=extract_week_num, reverse=False)
        target_round = pending_rounds[0]
        if target_round in unique_rounds:
            default_idx = unique_rounds.index(target_round)
            
    selected_round = st.selectbox("확인하고 싶은 2026 시즌 주차(Week)를 선택하세요:", unique_rounds, index=default_idx)
    filtered_df = df[df['round_name'] == selected_round].copy().reset_index(drop=True)
else:
    filtered_df = pd.DataFrame([])

if not filtered_df.empty:
    filtered_df['day_no'] = range(1, len(filtered_df) + 1)
    
    completed_in_round = filtered_df[filtered_df['actual_winner'].notna() & (filtered_df['actual_winner'] != '') & (~filtered_df['actual_winner'].isin(['경기 연기', '경기 취소', '연기됨', '취소됨']))]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("해당 주차 총 경기 수", f"{len(filtered_df)} 경기")
    col2.metric("경기 완료 수", f"{len(completed_in_round)} 경기")
    
    if not completed_in_round.empty:
        corr_cnt = int(completed_in_round['is_correct'].sum())
        acc = (corr_cnt / len(completed_in_round)) * 100
        col3.metric("주차 적중률", f"{acc:.1f}% ({corr_cnt}/{len(completed_in_round)})")
    else:
        col3.metric("주차 적중률", "⏳ 진행 예정")

    display_df = pd.DataFrame()
    display_df['No.'] = filtered_df['day_no']
    display_df['경기 일자'] = filtered_df['match_date']
    display_df['홈 팀'] = filtered_df.apply(lambda r: f"{r['home_team']} ({r['home_total_wuv']:.2f} WUV)" if pd.notna(r.get('home_total_wuv')) else r['home_team'], axis=1)
    display_df['원정 팀'] = filtered_df.apply(lambda r: f"{r['away_team']} ({r['away_total_wuv']:.2f} WUV)" if pd.notna(r.get('away_total_wuv')) else r['away_team'], axis=1)
    display_df['예측 결과'] = filtered_df['predicted_winner']
    display_df['3-Way 확률 [홈%|무%|원정%]'] = filtered_df.apply(
        lambda r: f"[{r['prob_home']:.1f}% | {r['prob_draw']:.1f}% | {r['prob_away']:.1f}%]", axis=1
    )
    display_df['예상 격차(ΔWUV)'] = filtered_df['gap'].apply(lambda x: f"{x:+.2f}")
    display_df['실제 결과'] = filtered_df.apply(
        lambda r: f"{int(r['actual_score_home'])} : {int(r['actual_score_away'])} ({r['actual_winner']})" 
        if (pd.notna(r.get('actual_score_home')) and pd.notna(r.get('actual_winner')) and r['actual_winner'] not in ['', '경기 연기', '경기 취소']) 
        else (r['actual_winner'] if (pd.notna(r.get('actual_winner')) and r['actual_winner'] != '') else "대기중"), axis=1
    )
    
    def get_status_tag(r):
        act = r['actual_winner']
        if not act or pd.isna(act) or act == '':
            return "⏳ 경기 대기중"
        if act in ['경기 연기', '경기 취소', '연기됨', '취소됨']:
            return "🚫 연기/취소"
        return "✅ 정답" if r['is_correct'] == 1 else "❌ 오답"
        
    # 테이블 내부 스크롤바가 생기지 않도록 해당 주차 경기 수(최대 32경기)에 맞춰 높이 자동 지정
    calc_height = int((len(display_df) + 1) * 36 + 15)
    st.dataframe(display_df, height=calc_height, hide_index=True, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. 최하단 푸터
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; padding-top: 15px;">
        <p>ⓒ DROPSHOT (사업자 번호: 578-81-03214)</p>
        <p>Contact us: liskhan@gmail.com</p>
    </div>
    """,
    unsafe_allow_html=True
)
