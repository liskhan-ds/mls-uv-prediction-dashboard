import sqlite3
import requests
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mls_data.db")
ROSTERS_PATH = os.path.join(BASE_DIR, "rosters_2026.json")

# Clean English Team Name Normalization Map
TEAM_NAME_MAP = {
    "Inter Miami CF": "Inter Miami CF",
    "Inter Miami": "Inter Miami CF",
    "LAFC": "LAFC",
    "Los Angeles Football Club": "LAFC",
    "LA Galaxy": "LA Galaxy",
    "Los Angeles Galaxy": "LA Galaxy",
    "Columbus Crew": "Columbus Crew",
    "FC Cincinnati": "FC Cincinnati",
    "Seattle Sounders FC": "Seattle Sounders FC",
    "Seattle Sounders": "Seattle Sounders FC",
    "Real Salt Lake": "Real Salt Lake",
    "Colorado Rapids": "Colorado Rapids",
    "Houston Dynamo FC": "Houston Dynamo FC",
    "Houston Dynamo": "Houston Dynamo FC",
    "Minnesota United FC": "Minnesota United FC",
    "Minnesota United": "Minnesota United FC",
    "Vancouver Whitecaps": "Vancouver Whitecaps",
    "Vancouver Whitecaps FC": "Vancouver Whitecaps",
    "Portland Timbers": "Portland Timbers",
    "Sporting Kansas City": "Sporting Kansas City",
    "Sporting KC": "Sporting Kansas City",
    "St. Louis CITY SC": "St. Louis CITY SC",
    "St. Louis City": "St. Louis CITY SC",
    "FC Dallas": "FC Dallas",
    "San Jose Earthquakes": "San Jose Earthquakes",
    "Philadelphia Union": "Philadelphia Union",
    "Red Bull New York": "Red Bull New York",
    "New York Red Bulls": "Red Bull New York",
    "New York City FC": "New York City FC",
    "NYCFC": "New York City FC",
    "Orlando City SC": "Orlando City SC",
    "Orlando City": "Orlando City SC",
    "Charlotte FC": "Charlotte FC",
    "Atlanta United FC": "Atlanta United FC",
    "Atlanta United": "Atlanta United FC",
    "Nashville SC": "Nashville SC",
    "CF Montréal": "CF Montréal",
    "CF Montreal": "CF Montréal",
    "Toronto FC": "Toronto FC",
    "D.C. United": "D.C. United",
    "DC United": "D.C. United",
    "New England Revolution": "New England Revolution",
    "Chicago Fire FC": "Chicago Fire FC",
    "Chicago Fire": "Chicago Fire FC",
    "Austin FC": "Austin FC",
    "San Diego FC": "San Diego FC",
}

def normalize_team_name(raw_name):
    if not raw_name:
        return ""
    for key, val in TEAM_NAME_MAP.items():
        if key.lower() in raw_name.lower() or raw_name.lower() in key.lower():
            return val
    return raw_name

# Official Player Ratings & Goals per 90 Stats (2026 MLS)
OFFICIAL_STATS = {
    "Lionel Messi": (7.95, 0.85),
    "Luis Suárez": (7.65, 0.65),
    "Sergio Busquets": (7.45, 0.10),
    "Jordi Alba": (7.40, 0.12),
    "Denis Bouanga": (7.70, 0.60),
    "Cucho Hernández": (7.65, 0.55),
    "Riqui Puig": (7.60, 0.30),
    "Luciano Acosta": (7.65, 0.40),
    "Evander": (7.60, 0.45),
    "Hany Mukhtar": (7.50, 0.40),
    "Emil Forsberg": (7.35, 0.25),
    "Christian Benteke": (7.40, 0.50),
    "Hugo Lloris": (7.35, 0.0),
    "Marco Reus": (7.45, 0.35),
    "Olivier Giroud": (7.40, 0.42),
    "Gabriel Pec": (7.35, 0.35),
    "Joseph Paintsil": (7.30, 0.30),
    "Diego Gómez": (7.25, 0.20),
    "Federico Redondo": (7.20, 0.10),
    "Brian White": (7.30, 0.40),
    "Cristian Arango": (7.45, 0.50),
    "Dejan Joveljić": (7.30, 0.45),
    "Santiago Rodríguez": (7.25, 0.25),
    "Lewis Morgan": (7.30, 0.35),
    "Petar Musa": (7.25, 0.38),
    "Daniel Gazdag": (7.30, 0.35),
    "Facundo Torres": (7.35, 0.35),
    "Jordan Morris": (7.25, 0.30),
    "Cristian Roldan": (7.20, 0.18),
    "Raúl Ruidíaz": (7.20, 0.35),
}

TEAM_GOALS_PER_GAME = {
    "Inter Miami CF": 2.2, "LAFC": 2.0, "Columbus Crew": 1.9, "LA Galaxy": 1.8,
    "FC Cincinnati": 1.7, "Real Salt Lake": 1.6, "Colorado Rapids": 1.5, "Seattle Sounders FC": 1.5,
    "Portland Timbers": 1.5, "Red Bull New York": 1.4, "New York City FC": 1.4, "Orlando City SC": 1.4,
    "Houston Dynamo FC": 1.3, "Minnesota United FC": 1.3, "Vancouver Whitecaps": 1.3, "Charlotte FC": 1.25,
    "Philadelphia Union": 1.25, "St. Louis CITY SC": 1.2, "Nashville SC": 1.15, "Atlanta United FC": 1.2,
    "D.C. United": 1.1, "FC Dallas": 1.1, "San Diego FC": 1.1, "San Jose Earthquakes": 1.0,
    "Sporting Kansas City": 1.05, "CF Montréal": 1.0, "Toronto FC": 0.95, "New England Revolution": 0.90,
    "Chicago Fire FC": 0.85, "Austin FC": 0.90,
}

TEAM_CONCEDED_PER_GAME = {
    "Inter Miami CF": 1.3, "LAFC": 1.1, "Columbus Crew": 1.0, "LA Galaxy": 1.3,
    "FC Cincinnati": 1.0, "Real Salt Lake": 1.2, "Colorado Rapids": 1.3, "Seattle Sounders FC": 0.9,
    "Portland Timbers": 1.4, "Red Bull New York": 0.9, "New York City FC": 1.1, "Orlando City SC": 1.15,
    "Houston Dynamo FC": 1.1, "Minnesota United FC": 1.2, "Vancouver Whitecaps": 1.15, "Charlotte FC": 1.1,
    "Philadelphia Union": 1.2, "St. Louis CITY SC": 1.35, "Nashville SC": 1.1, "Atlanta United FC": 1.3,
    "D.C. United": 1.4, "FC Dallas": 1.3, "San Diego FC": 1.25, "San Jose Earthquakes": 1.6,
    "Sporting Kansas City": 1.5, "CF Montréal": 1.45, "Toronto FC": 1.55, "New England Revolution": 1.5,
    "Chicago Fire FC": 1.6, "Austin FC": 1.4,
}

LOW_POSSESSION_TEAMS = [
    "San Jose Earthquakes", "Chicago Fire FC", "Toronto FC", "New England Revolution",
    "CF Montréal", "Sporting Kansas City", "St. Louis CITY SC"
]

def calculate_player_uv(player_data, team_name=""):
    p_name_raw = player_data.get("name", "")
    position = player_data.get("pos", "M")
    
    rating = None
    goals_per90 = 0.0
    
    for off_name, (off_r, off_g90) in OFFICIAL_STATS.items():
        if off_name.lower() in p_name_raw.lower() or p_name_raw.lower() in off_name.lower():
            rating = off_r
            goals_per90 = off_g90
            break
            
    pos_clean = "GK" if position in ["G", "GK", "Goalkeeper"] else ("DF" if position in ["D", "DF", "Defender"] else ("MF" if position in ["M", "MF", "Midfielder"] else "FW"))
    
    tgoals = TEAM_GOALS_PER_GAME.get(team_name, 1.30)
    is_low_poss = team_name in LOW_POSSESSION_TEAMS
    
    if rating is None:
        if pos_clean == "GK":
            raw_uv = 0.95
        elif pos_clean == "DF":
            raw_uv = 0.90
        elif pos_clean == "MF":
            raw_uv = 0.82 if is_low_poss else 0.88
        else: # FW
            raw_uv = 0.78 if tgoals < 1.1 else 0.85
    elif rating >= 6.65:
        if pos_clean == "GK":
            raw_uv = 1.0 + (rating - 6.65) * 0.45
        elif pos_clean == "DF":
            raw_uv = 1.0 + (rating - 6.65) * 0.40
        elif pos_clean == "MF":
            raw_uv = 1.0 + (rating - 6.65) * 0.35
            if is_low_poss:
                raw_uv -= 0.08
        else: # FW
            raw_uv = 1.0 + (rating - 6.65) * 0.35 + (goals_per90 * 0.20)
            if goals_per90 < 0.15 or tgoals < 1.1:
                fw_penalty = min(0.15, round(0.10 + (0.15 - max(goals_per90, 0.0)) * 0.33, 3))
                raw_uv -= fw_penalty
    else:
        slope = 0.80 if pos_clean == "MF" else 0.65
        raw_uv = 1.0 + (rating - 6.65) * slope + (goals_per90 * 0.20 if pos_clean == "FW" else 0.0)
        if pos_clean == "MF" and is_low_poss:
            raw_uv -= 0.08
        elif pos_clean == "FW" and (goals_per90 < 0.15 or tgoals < 1.1):
            fw_penalty = min(0.15, round(0.10 + (0.15 - max(goals_per90, 0.0)) * 0.33, 3))
            raw_uv -= fw_penalty
        
    conc = TEAM_CONCEDED_PER_GAME.get(team_name, 1.30)
    if pos_clean in ["GK", "DF"] and conc > 1.4:
        def_penalty = min(0.12, round(0.04 + (conc - 1.4) * 0.10, 3))
        raw_uv -= def_penalty
        
    return round(min(max(raw_uv, 0.4), 2.0), 3)

def get_team_roster(team_name):
    if not os.path.exists(ROSTERS_PATH):
        return {"starters": [], "subs": []}
        
    with open(ROSTERS_PATH, "r", encoding="utf-8") as f:
        rosters = json.load(f)
        
    plist = rosters.get(team_name, [])
    if not plist:
        for k, v in rosters.items():
            if normalize_team_name(k) == normalize_team_name(team_name):
                plist = v
                break
                
    available = []
    for p in plist:
        p_copy = dict(p)
        p_copy["calc_uv"] = calculate_player_uv(p_copy, team_name)
        available.append(p_copy)
        
    gks = sorted([p for p in available if p.get("pos") in ["G", "GK", "Goalkeeper"]], key=lambda x: x["calc_uv"], reverse=True)
    dfs = sorted([p for p in available if p.get("pos") in ["D", "DF", "Defender"]], key=lambda x: x["calc_uv"], reverse=True)
    mfs = sorted([p for p in available if p.get("pos") in ["M", "MF", "Midfielder"]], key=lambda x: x["calc_uv"], reverse=True)
    fws = sorted([p for p in available if p.get("pos") in ["F", "FW", "Forward"]], key=lambda x: x["calc_uv"], reverse=True)
    
    starters = gks[:1] + dfs[:4] + mfs[:3] + fws[:3]
    if len(starters) < 11:
        used_names = {p["name"] for p in starters}
        remaining = [p for p in available if p["name"] not in used_names]
        starters += remaining[:11 - len(starters)]
        
    used_names = {p["name"] for p in starters}
    remaining = [p for p in available if p["name"] not in used_names]
    subs = remaining[:5]
    
    return {"starters": starters, "subs": subs}

def calculate_wuv(team_name):
    roster = get_team_roster(team_name)
    starters = roster.get("starters", [])
    subs = roster.get("subs", [])
    
    pos_weights = {"GK": 0.10, "DF": 0.30, "MF": 0.30, "FW": 0.30}
    
    starters_detail = []
    subs_detail = []
    
    st_weighted_sum = 0.0
    for p in starters:
        uv = calculate_player_uv(p, team_name)
        pos = p.get("pos", "M")
        pos_clean = "GK" if pos in ["G","GK","Goalkeeper"] else ("DF" if pos in ["D","DF","Defender"] else ("MF" if pos in ["M","MF","Midfielder"] else "FW"))
        
        count_in_pos = max(sum(1 for sp in starters if ("GK" if sp.get("pos") in ["G","GK","Goalkeeper"] else ("DF" if sp.get("pos") in ["D","DF","Defender"] else ("MF" if sp.get("pos") in ["M","MF","Midfielder"] else "FW"))) == pos_clean), 1)
        p_pos_weight = pos_weights[pos_clean] / count_in_pos
        wuv_contrib = uv * p_pos_weight * 1.0 * 0.85
        st_weighted_sum += wuv_contrib
        
        starters_detail.append({
            "name": p.get("name"),
            "pos": pos_clean,
            "uv": uv,
            "pos_weight": round(p_pos_weight, 4),
            "st_weight": 0.85,
            "wuv_contrib": round(wuv_contrib, 4)
        })
        
    sub_weighted_sum = 0.0
    for p in subs:
        uv = calculate_player_uv(p, team_name)
        pos = p.get("pos", "M")
        pos_clean = "GK" if pos in ["G","GK","Goalkeeper"] else ("DF" if pos in ["D","DF","Defender"] else ("MF" if pos in ["M","MF","Midfielder"] else "FW"))
        
        p_pos_weight = pos_weights[pos_clean] / 4.0
        wuv_contrib = uv * p_pos_weight * 0.15
        sub_weighted_sum += wuv_contrib
        
        subs_detail.append({
            "name": p.get("name"),
            "pos": pos_clean,
            "uv": uv,
            "pos_weight": round(p_pos_weight, 4),
            "sub_weight": 0.15,
            "wuv_contrib": round(wuv_contrib, 4)
        })
        
    st_avg = sum([p["uv"] for p in starters_detail]) / len(starters_detail) if starters_detail else 0.95
    sub_avg = sum([p["uv"] for p in subs_detail]) / len(subs_detail) if subs_detail else 0.85
    
    raw_wuv = (0.85 * st_avg + 0.15 * sub_avg)
    team_wuv = round(11.0 + 10.5 * (raw_wuv - 0.835), 2)
    
    pos_sums = {"GK": 0.0, "DF": 0.0, "MF": 0.0, "FW": 0.0}
    for p in starters_detail:
        pos_sums[p["pos"]] += p["uv"]
    st_tot_sum = sum([p["uv"] for p in starters_detail])
    
    gk_wuv = round(team_wuv * (pos_sums["GK"] / st_tot_sum), 2) if st_tot_sum > 0 else 1.0
    df_wuv = round(team_wuv * (pos_sums["DF"] / st_tot_sum), 2) if st_tot_sum > 0 else 4.0
    mf_wuv = round(team_wuv * (pos_sums["MF"] / st_tot_sum), 2) if st_tot_sum > 0 else 3.0
    fw_wuv = round(team_wuv * (pos_sums["FW"] / st_tot_sum), 2) if st_tot_sum > 0 else 3.0
    
    return {
        "team_wuv": team_wuv,
        "st_avg": round(st_avg, 3),
        "sub_avg": round(sub_avg, 3),
        "gk_wuv": gk_wuv,
        "df_wuv": df_wuv,
        "mf_wuv": mf_wuv,
        "fw_wuv": fw_wuv,
        "starters_detail": starters_detail,
        "subs_detail": subs_detail
    }

def get_match_prediction(home_team, away_team):
    h_info = calculate_wuv(home_team)
    a_info = calculate_wuv(away_team)
    
    h_total = h_info["team_wuv"] + 0.25 # Home advantage
    a_total = a_info["team_wuv"]
    
    gap = h_total - a_total
    
    home_name = normalize_team_name(home_team)
    away_name = normalize_team_name(away_team)
    
    if abs(gap) <= 0.40:
        winner = "Draw"
        code = "DRAW"
    elif gap > 0.40:
        winner = f"{home_name} Win"
        code = "HOME"
    else:
        winner = f"{away_name} Win"
        code = "AWAY"
        
    z = gap
    lh = 1.55 * z
    la = -1.55 * z
    ld = 0.35 - 1.25 * abs(z)
    
    eh, ed, ea = np.exp(lh), np.exp(ld), np.exp(la)
    tot = eh + ed + ea
    
    p_home = round((eh / tot) * 100, 1)
    p_draw = round((ed / tot) * 100, 1)
    p_away = round((ea / tot) * 100, 1)
    
    sc_h = int(round(1.35 * (h_total / 11.0)))
    sc_a = int(round(1.35 * (a_total / 11.0)))
    
    if code == "DRAW":
        sc_h = sc_a = int(round((sc_h + sc_a) / 2.0))
    elif code == "HOME" and sc_h <= sc_a:
        sc_h = sc_a + 1
    elif code == "AWAY" and sc_a <= sc_h:
        sc_a = sc_h + 1
        
    return {
        "home_wuv": h_info,
        "away_wuv": a_info,
        "h_total": h_total,
        "a_total": a_total,
        "gap": gap,
        "winner": winner,
        "code": code,
        "p_home": p_home,
        "p_draw": p_draw,
        "p_away": p_away,
        "sc_h": sc_h,
        "sc_a": sc_a
    }

def populate_rosters_db(conn):
    if not os.path.exists(ROSTERS_PATH):
        return
        
    with open(ROSTERS_PATH, "r", encoding="utf-8") as f:
        rosters_data = json.load(f)
        
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rosters WHERE season = 2026")
    
    count = 0
    for t_name, plist in rosters_data.items():
        t_clean = normalize_team_name(t_name)
        wuv_info = calculate_wuv(t_name)
        st_names = {p["name"] for p in wuv_info["starters_detail"]}
        
        for p in plist:
            p_name = p.get("name")
            pos = p.get("pos", "M")
            pos_clean = "GK" if pos in ["G","GK","Goalkeeper"] else ("DF" if pos in ["D","DF","Defender"] else ("MF" if pos in ["M","MF","Midfielder"] else "FW"))
            is_st = 1 if p_name in st_names else 0
            
            uv = calculate_player_uv(p, t_name)
            pos_w = 0.10 if pos_clean == "GK" else (0.30 if pos_clean in ["DF","MF","FW"] else 0.25)
            st_sub_w = 0.85 if is_st == 1 else 0.15
            calc_wuv = round(uv * pos_w * st_sub_w * 11.0, 4)
            
            cursor.execute("""
            INSERT INTO rosters (
                team_name, team_name_kr, player_name, position, position_clean,
                is_starter, rating, goals_per90, calc_uv, position_weight, starter_sub_weight, calc_wuv, season
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t_name, t_clean, p_name, pos, pos_clean,
                is_st, 6.80, 0.0, uv, pos_w, st_sub_w, calc_wuv, 2026
            ))
            count += 1
            
    conn.commit()
    print(f"✅ rosters table updated: {count} players saved (2026 Season)")

def run_pipeline():
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard?dates=20260201-20261130&limit=1000"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15).json()
        events = resp.get("events", [])
    except Exception as e:
        print(f"⚠️ ESPN API error: {e}")
        return

    if not events:
        print("⚠️ No 2026 MLS match events found.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS predictions")
    cursor.execute("DROP TABLE IF EXISTS schedules")
    
    # Ensure init_mls_db tables exist with updated schema
    import init_mls_db
    init_mls_db.create_tables()
    
    populate_rosters_db(conn)
    
    cursor.execute("DELETE FROM predictions")
    cursor.execute("DELETE FROM schedules")
    
    events.sort(key=lambda x: x["date"])
    
    date_objs = [datetime.fromisoformat(e["date"].replace("Z", "+00:00")) for e in events]
    iso_weeks = [d.isocalendar()[1] for d in date_objs]
    min_week = min(iso_weeks) if iso_weeks else 1
    
    tz_et = ZoneInfo("America/New_York")
    tz_kst = ZoneInfo("Asia/Seoul")
    
    # Sequential Round Assigner (Round 1 ~ Round 34, ~15 matches per round)
    team_game_count = {}
    
    for idx, e in enumerate(events, 1):
        comp = e.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
            
        home_comp = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
        away_comp = competitors[1] if competitors[0].get("homeAway") == "home" else competitors[0]
        
        h_team_raw = home_comp.get("team", {}).get("displayName", "")
        a_team_raw = away_comp.get("team", {}).get("displayName", "")
        
        h_team = normalize_team_name(h_team_raw)
        a_team = normalize_team_name(a_team_raw)
        
        # Calculate sequential round number based on team match counts
        h_cnt = team_game_count.get(h_team, 0) + 1
        a_cnt = team_game_count.get(a_team, 0) + 1
        team_game_count[h_team] = h_cnt
        team_game_count[a_team] = a_cnt
        
        round_num = max(h_cnt, a_cnt)
        week_label = f"Round {round_num} (Gameweek {round_num})"
        
        date_raw = e.get("date", "")
        dt_utc = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
        
        # Convert to US Eastern (ET) and KST time strings
        dt_et = dt_utc.astimezone(tz_et)
        dt_kst = dt_utc.astimezone(tz_kst)
        
        match_date_et = dt_et.strftime("%Y-%m-%d %H:%M")
        match_date_kst = dt_kst.strftime("%Y-%m-%d %H:%M")
        
        status_type = e.get("status", {}).get("type", {}).get("name", "")
        is_completed = (status_type == "STATUS_FULL_TIME")
        is_cancelled = status_type in ["STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_ABANDONED"]
        
        act_sc_h = int(home_comp.get("score")) if (is_completed and home_comp.get("score") is not None) else None
        act_sc_a = int(away_comp.get("score")) if (is_completed and away_comp.get("score") is not None) else None
        
        if is_completed and act_sc_h is not None and act_sc_a is not None:
            if act_sc_h > act_sc_a:
                act_winner = f"{h_team} Win"
            elif act_sc_a > act_sc_h:
                act_winner = f"{a_team} Win"
            else:
                act_winner = "Draw"
        elif is_cancelled:
            act_winner = "Postponed"
        else:
            act_winner = None
            
        pred = get_match_prediction(h_team_raw, a_team_raw)
        pred_winner = pred["winner"]
        
        if is_completed and act_winner is not None:
            if (act_winner == pred_winner) or (h_team in act_winner and h_team in pred_winner) or (a_team in act_winner and a_team in pred_winner):
                is_corr = 1
            else:
                is_corr = 0
        else:
            is_corr = None
            
        mid = f"2026_MLS_{idx}"
        
        cursor.execute("""
        INSERT INTO predictions (
            match_id, round_name, home_team, away_team, match_date,
            match_date_et, match_date_kst,
            home_wuv, away_wuv, home_total_wuv, away_total_wuv,
            gap, predicted_winner, prob_home, prob_draw, prob_away,
            score_home, score_away,
            actual_score_home, actual_score_away, actual_winner, is_correct
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mid, week_label, h_team, a_team, date_raw[:10],
            match_date_et, match_date_kst,
            pred["home_wuv"]["team_wuv"], pred["away_wuv"]["team_wuv"], pred["h_total"], pred["a_total"],
            pred["gap"], pred_winner, pred["p_home"], pred["p_draw"], pred["p_away"],
            pred["sc_h"], pred["sc_a"],
            act_sc_h, act_sc_a, act_winner, is_corr
        ))
        
        cursor.execute("""
        INSERT INTO schedules (
            match_id, week_name, match_date, home_team, away_team, status, season
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mid, week_label, date_raw[:10], h_team, a_team, status_type, 2026
        ))

    conn.commit()
    conn.close()
    print(f"✅ 2026 MLS Pipeline Complete! {len(events)} matches processed with US Eastern & KST times.")

if __name__ == "__main__":
    print("🚀 2026 MLS AI Match Prediction Pipeline starting...", flush=True)
    run_pipeline()
