import csv
import io
import sqlite3
import urllib.request
import zipfile
from pathlib import Path


# ============================================================
# 設定
# ============================================================

DATABASE_URL = (
    "https://github.com/konoui/m-league-game-db/"
    "releases/latest/download/database.zip"
)

SEASON_START_YEAR = 2026

OUTPUT_FILE = Path("data/mleague_results.csv")


# ============================================================
# 最新DBをダウンロード
# ============================================================

print("最新のMリーグDBを取得します...")

with urllib.request.urlopen(DATABASE_URL) as response:
    zip_bytes = response.read()

print(
    "ダウンロード完了:",
    len(zip_bytes),
    "bytes"
)


# ============================================================
# ZIPからSQLiteファイルを取り出す
# ============================================================

with zipfile.ZipFile(
    io.BytesIO(zip_bytes)
) as zf:

    sqlite_files = [
        name
        for name in zf.namelist()
        if name.endswith(".sqlite3")
    ]

    if not sqlite_files:
        raise RuntimeError(
            "ZIP内にSQLiteファイルが見つかりません。"
        )

    sqlite_name = sqlite_files[0]

    print(
        "SQLite:",
        sqlite_name
    )

    db_bytes = zf.read(sqlite_name)


temp_db = Path("database.sqlite3")

temp_db.write_bytes(db_bytes)


# ============================================================
# DBから2026-27シーズンの試合結果を取得
# ============================================================

conn = sqlite3.connect(temp_db)

query = """
SELECT
    g.date,
    g.match_number,
    p.name,
    ROUND(
        gpr.points
        + COALESCE(gpr.penalty_points, 0),
        1
    ) AS points,
    gpr.rank
FROM game_player_result gpr
JOIN game g
    ON gpr.game_id = g.id
JOIN player p
    ON gpr.player_id = p.id
JOIN season_stage ss
    ON g.season_stage_id = ss.id
JOIN league_season ls
    ON ss.league_season_id = ls.id
WHERE
    ls.start_year = ?
    AND ss.stage = 'regular'
ORDER BY
    g.date,
    g.match_number,
    p.name
"""

rows = conn.execute(
    query,
    (SEASON_START_YEAR,)
).fetchall()

conn.close()


if not rows:
    raise RuntimeError(
        "2026-27シーズンの試合結果が0件でした。"
    )


print(
    "取得件数:",
    len(rows)
)

print(
    "最終試合日:",
    rows[-1][0]
)


# ============================================================
# CSV出力
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with OUTPUT_FILE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "date",
        "game",
        "player",
        "points",
        "rank"
    ])

    writer.writerows(rows)


print(
    "CSV作成完了:",
    OUTPUT_FILE
)


# 一時DB削除
temp_db.unlink(
    missing_ok=True
)

print("完了")
