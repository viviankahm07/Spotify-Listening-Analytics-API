from flask import Flask, jsonify
import os
import json
import sqlite3
import glob

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
DATA_DIR = os.path.join(BASE_DIR, "data")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



@app.route("/")
def home():
    return "Spotify Listening API (Extended History) is running!"



@app.route("/api/recently-played")
def recently_played():
    JSON_PATH = os.path.join(DATA_DIR, "recently_played.json")
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    return jsonify(data)



@app.route("/init-db")
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            played_at TEXT NOT NULL,        -- ts
            ms_played INTEGER NOT NULL,

            content_type TEXT NOT NULL,     -- 'track' or 'episode'

            track_name TEXT,
            artist TEXT,
            album TEXT,

            episode_name TEXT,
            episode_show_name TEXT,

            platform TEXT,
            conn_country TEXT,
            skipped INTEGER,
            shuffle INTEGER,
            offline INTEGER,
            reason_start TEXT,
            reason_end TEXT,

            UNIQUE(played_at, content_type, track_name, artist, episode_name, episode_show_name)
        );
    """)

    conn.commit()
    conn.close()
    return "DB initialized (plays table for extended streaming history)!"


@app.route("/api/import-extended-history")
def import_extended_history():
    pattern = os.path.join(DATA_DIR, "Streaming_History_Audio_*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        return jsonify({
            "error": "No Streaming_History_Audio_*.json files found in /data",
            "expected_pattern": pattern
        }), 404

    conn = get_db_connection()
    cur = conn.cursor()

    total_events = 0
    new_events = 0
    files_loaded = 0

    for fp in files:
        with open(fp, "r") as f:
            events = json.load(f)

        files_loaded += 1

        for e in events:
            total_events += 1

            played_at = e.get("ts")
            ms_played = e.get("ms_played")

            track_name = e.get("master_metadata_track_name")
            artist = e.get("master_metadata_album_artist_name")
            album = e.get("master_metadata_album_album_name")

            episode_name = e.get("episode_name")
            episode_show = e.get("episode_show_name")

            if track_name:
                content_type = "track"
            elif episode_name:
                content_type = "episode"
            else:
                content_type = "unknown"

            if not played_at or ms_played is None or content_type == "unknown":
                continue

            platform = e.get("platform")
            conn_country = e.get("conn_country")

            skipped = 1 if e.get("skipped") else 0
            shuffle = 1 if e.get("shuffle") else 0
            offline = 1 if e.get("offline") else 0

            reason_start = e.get("reason_start")
            reason_end = e.get("reason_end")

            cur.execute("""
                INSERT OR IGNORE INTO plays (
                    played_at, ms_played, content_type,
                    track_name, artist, album,
                    episode_name, episode_show_name,
                    platform, conn_country, skipped, shuffle, offline,
                    reason_start, reason_end
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                played_at, ms_played, content_type,
                track_name, artist, album,
                episode_name, episode_show,
                platform, conn_country, skipped, shuffle, offline,
                reason_start, reason_end
            ))

            if cur.rowcount == 1:
                new_events += 1

    conn.commit()
    conn.close()

    return jsonify({
        "files_loaded": files_loaded,
        "events_in_files": total_events,
        "new_events_saved": new_events
    })



@app.route("/api/stats/top-artists")
def top_artists_by_time():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT artist,
               ROUND(SUM(ms_played) / 60000.0, 2) AS minutes
        FROM plays
        WHERE content_type = 'track' AND artist IS NOT NULL
        GROUP BY artist
        ORDER BY SUM(ms_played) DESC
        LIMIT 10;
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([{"artist": r["artist"], "minutes": r["minutes"]} for r in rows])



@app.route("/api/stats/top-tracks")
def top_tracks_by_time():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT track_name, artist, album,
               ROUND(SUM(ms_played) / 60000.0, 2) AS minutes
        FROM plays
        WHERE content_type = 'track' AND track_name IS NOT NULL
        GROUP BY track_name, artist, album
        ORDER BY SUM(ms_played) DESC
        LIMIT 10;
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {"track": r["track_name"], "artist": r["artist"], "album": r["album"], "minutes": r["minutes"]}
        for r in rows
    ])



@app.route("/api/stats/listening-by-hour")
def listening_by_hour():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT substr(played_at, 12, 2) AS hour,
               ROUND(SUM(ms_played) / 60000.0, 2) AS minutes
        FROM plays
        GROUP BY hour
        ORDER BY hour ASC;
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([{"hour": r["hour"], "minutes": r["minutes"]} for r in rows])



@app.route("/api/stats/listening-by-dow")
def listening_by_dow():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT strftime('%w', replace(played_at, 'Z', '+00:00')) AS dow_num,
               ROUND(SUM(ms_played) / 60000.0, 2) AS minutes
        FROM plays
        GROUP BY dow_num
        ORDER BY CAST(dow_num AS INTEGER) ASC;
    """)

    rows = cur.fetchall()
    conn.close()

    dow_map = {
        "0": "Sunday",
        "1": "Monday",
        "2": "Tuesday",
        "3": "Wednesday",
        "4": "Thursday",
        "5": "Friday",
        "6": "Saturday",
    }

    return jsonify([
        {"dow": dow_map.get(r["dow_num"], r["dow_num"]), "minutes": r["minutes"]}
        for r in rows
    ])


# ------------------------
# A) Completion / depth-of-listen by artist
# Metrics:
# - avg_seconds_listened
# - % of listens >= 30s, >= 60s, >= 120s
# ------------------------
@app.route("/api/stats/engagement/artist-depth")
def artist_depth():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            artist,
            COUNT(*) AS plays,
            ROUND(AVG(ms_played) / 1000.0, 2) AS avg_seconds,

            ROUND(100.0 * SUM(CASE WHEN ms_played >= 30000  THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_ge_30s,
            ROUND(100.0 * SUM(CASE WHEN ms_played >= 60000  THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_ge_60s,
            ROUND(100.0 * SUM(CASE WHEN ms_played >= 120000 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_ge_120s

        FROM plays
        WHERE content_type = 'track' AND artist IS NOT NULL
        GROUP BY artist
        HAVING COUNT(*) >= 20
        ORDER BY avg_seconds DESC
        LIMIT 20;
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {
            "artist": r["artist"],
            "plays": r["plays"],
            "avg_seconds_listened": r["avg_seconds"],
            "pct_listens_ge_30s": r["pct_ge_30s"],
            "pct_listens_ge_60s": r["pct_ge_60s"],
            "pct_listens_ge_120s": r["pct_ge_120s"],
        }
        for r in rows
    ])



@app.route("/api/stats/engagement/track-depth")
def track_depth():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            track_name,
            artist,
            COUNT(*) AS plays,
            ROUND(AVG(ms_played) / 1000.0, 2) AS avg_seconds,

            ROUND(100.0 * SUM(CASE WHEN ms_played >= 30000  THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_ge_30s,
            ROUND(100.0 * SUM(CASE WHEN ms_played >= 60000  THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_ge_60s,
            ROUND(100.0 * SUM(CASE WHEN ms_played >= 120000 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_ge_120s

        FROM plays
        WHERE content_type = 'track' AND track_name IS NOT NULL AND artist IS NOT NULL
        GROUP BY track_name, artist
        HAVING COUNT(*) >= 10
        ORDER BY avg_seconds DESC
        LIMIT 20;
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {
            "track": r["track_name"],
            "artist": r["artist"],
            "plays": r["plays"],
            "avg_seconds_listened": r["avg_seconds"],
            "pct_listens_ge_30s": r["pct_ge_30s"],
            "pct_listens_ge_60s": r["pct_ge_60s"],
            "pct_listens_ge_120s": r["pct_ge_120s"],
        }
        for r in rows
    ])


if __name__ == "__main__":
    app.run(debug=True)
