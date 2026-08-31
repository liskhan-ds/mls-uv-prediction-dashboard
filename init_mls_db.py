import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mls_data.db")

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Predictions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT UNIQUE,
        round_name TEXT NOT NULL,
        home_team TEXT NOT NULL,
        away_team TEXT NOT NULL,
        match_date TEXT NOT NULL,
        home_wuv REAL NOT NULL,
        away_wuv REAL NOT NULL,
        home_total_wuv REAL NOT NULL,
        away_total_wuv REAL NOT NULL,
        gap REAL NOT NULL,
        predicted_winner TEXT NOT NULL,
        prob_home REAL NOT NULL,
        prob_draw REAL NOT NULL,
        prob_away REAL NOT NULL,
        score_home INTEGER NOT NULL,
        score_away INTEGER NOT NULL,
        actual_score_home INTEGER,
        actual_score_away INTEGER,
        actual_winner TEXT,
        is_correct INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Rosters Table (Full 2026 season rosters per team)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rosters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_name TEXT NOT NULL,
        team_name_kr TEXT NOT NULL,
        player_name TEXT NOT NULL,
        position TEXT NOT NULL,
        position_clean TEXT NOT NULL,
        is_starter INTEGER NOT NULL,
        rating REAL NOT NULL,
        goals_per90 REAL NOT NULL,
        calc_uv REAL NOT NULL,
        position_weight REAL NOT NULL,
        starter_sub_weight REAL NOT NULL,
        calc_wuv REAL NOT NULL,
        season INTEGER NOT NULL DEFAULT 2026,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(team_name, player_name, season) ON CONFLICT REPLACE
    )
    """)
    
    # 3. Schedules Table (2026 season week-by-week schedule)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT UNIQUE,
        week_name TEXT NOT NULL,
        match_date TEXT NOT NULL,
        home_team TEXT NOT NULL,
        away_team TEXT NOT NULL,
        status TEXT NOT NULL,
        season INTEGER NOT NULL DEFAULT 2026,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ mls_data.db 데이터베이스 및 테이블(predictions, rosters, schedules) 생성 완료: {DB_PATH}")

if __name__ == "__main__":
    create_tables()
