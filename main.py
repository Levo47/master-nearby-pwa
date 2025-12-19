from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from math import radians, sin, cos, asin, sqrt
from typing import Optional, List, Dict
import sqlite3
from pathlib import Path

app = FastAPI()

DB_PATH = Path("masters.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS masters (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      service TEXT NOT NULL CHECK(service IN ('plumber','electrician','furniture','handyman')),
      phone TEXT NOT NULL,
      rating REAL NOT NULL DEFAULT 4.5,
      jobs INTEGER NOT NULL DEFAULT 0,
      price_from INTEGER NOT NULL DEFAULT 0,
      tagline TEXT NOT NULL DEFAULT '',
      lat REAL NOT NULL,
      lng REAL NOT NULL,
      is_verified INTEGER NOT NULL DEFAULT 0
    );
    """)

    # seed если база пустая
    cur.execute("SELECT COUNT(*) AS c FROM masters;")
    if cur.fetchone()["c"] == 0:
        seed = [
            ("Игорь, сантехник","plumber","+491234567890",4.8,132,50,"Быстро и без навязываний",52.5205,13.4070,1),
            ("Марина, сантехник","plumber","+491111222333",4.7,64,45,"Чисто, аккуратно",52.5198,13.4039,1),

            ("Алина, электрик","electrician","+492222333444",4.9,98,60,"С гарантией",52.5212,13.4018,1),
            ("Павел, электрик","electrician","+493333444555",4.6,51,55,"Розетки и свет",52.5178,13.4091,0),

            ("Денис, сборка мебели","furniture","+495555666777",4.8,88,45,"Быстро и ровно",52.5231,13.4062,1),
            ("Сергей, сборка мебели","furniture","+494444555666",4.7,210,40,"IKEA/кухни/шкафы",52.5189,13.4009,0),

            ("Кирилл, мастер на час","handyman","+496666777888",4.6,175,35,"Мелкий ремонт",52.5209,13.4104,1),
            ("Олег, мастер на час","handyman","+497777888999",4.5,73,30,"Домашние задачи",52.5169,13.4022,0),
        ]
        cur.executemany("""
          INSERT INTO masters
          (name,service,phone,rating,jobs,price_from,tagline,lat,lng,is_verified)
          VALUES (?,?,?,?,?,?,?,?,?,?)
        """, seed)

    conn.commit()
    conn.close()

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/api/masters")
def get_masters(
    service: str = Query(..., pattern="^(plumber|electrician|furniture|handyman)$"),
    radius_km: float = Query(2.0, ge=0.1, le=10.0),
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    verified_only: bool = Query(False),
):
    conn = connect()
    cur = conn.cursor()

    sql = """
      SELECT id, name, service, phone, rating, jobs, price_from, tagline, lat, lng, is_verified
      FROM masters
      WHERE service = ?
    """
    params = [service]
    if verified_only:
        sql += " AND is_verified = 1"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    items: List[Dict] = []
    for r in rows:
        dist = haversine_km(lat, lng, r["lat"], r["lng"])
        if dist <= radius_km:
            items.append({
                "id": r["id"],
                "name": r["name"],
                "phone": r["phone"],
                "rating": float(r["rating"]),
                "jobs": int(r["jobs"]),
                "priceFrom": int(r["price_from"]),
                "tagline": r["tagline"],
                "distanceKm": round(dist, 2),
                "isVerified": bool(r["is_verified"]),
            })

    items.sort(key=lambda x: x["distanceKm"])
    return {"items": items[:5]}

# Статика после API
app.mount("/", StaticFiles(directory=".", html=True), name="static")
