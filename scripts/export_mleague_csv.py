import csv
import io
import sqlite3
import urllib.request
import zipfile
from pathlib import Path


DATABASE_URL = (
    "https://github.com/konoui/m-league-game-db/"
    "releases/latest/download/database.zip"
)

SEASON_START_YEAR = 2026
OUTPUT_FILE = Path("data/mleague_results.csv")


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


def choose_column(columns, candidates, label):
    for candidate in candidates:
        if candidate in columns:
            print(
                f"{label}: {candidate}"
            )
            return candidate

    raise RuntimeError(
        f"{label} が見つかりません。"
        f"候補={candidates} "
        f"実際={sorted(columns)}"
    )


print("最新のMリーグDBを取得します...")

with urllib.request.urlopen(
    DATABASE_URL
) as response:
    zip_bytes = response.read()

print(
    "ダウンロード完了:",
    len(zip_bytes),
    "bytes"
)


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

    db_bytes = zf.read(
        sqlite_name
    )


temp_db = Path(
    "database.sqlite3"
)

temp_db.write_bytes(
    db_bytes
)


conn = sqlite3.connect(
    temp_db
)


# ============================================================
# 現在のDB列名を自動判定
# ============================================================

game_columns = get_columns(
    conn,
    "game"
)

result_columns = get_columns(
    conn,
    "game_player_result"
)


game_number_col = choose_column(
    game_columns,
    [
        "match_number",
        "game_number"
    ],
    "試合番号列"
)


points_col = choose_column(
    result_columns,
    [
        "points",
        "league_points"
    ],
    "リーグポイント列"
)


penalty_col = None

for candidate in [
    "penalty_points",
    "penalty_league_points"
]:
    if candidate in result_columns:
        penalty_col = candidate
        break


if penalty_col:
    print(
        "ペナルティ列:",
        penalty_col
    )

    point_expression = (
        f"gpr.{points_col} "
        f"+ COALESCE(gpr.{penalty_col}, 0)"
    )

else:
    print(
        "ペナルティ列: なし"
    )

    point_expression = (
        f"gpr.{points_col}"
    )


print(
    "game columns:",
    sorted(game_columns)
)

print(
    "game_player_result columns:",
    sorted(result_columns)
)


# ============================================================
# 2026-27 レギュラーシーズン取得
# ============================================================

query = f"""
SELECT
    g.date,
    g.{game_number_col},
    p.name,
    ROUND(
        {point_expression},
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
    g.{game_number_col},
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

    writer.writerows(
        rows
    )


print(
    "CSV作成完了:",
    OUTPUT_FILE
)


temp_db.unlink(
    missing_ok=True
)

print("完了")
