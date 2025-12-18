from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from math import radians, sin, cos, asin, sqrt
from typing import List, Dict

app = FastAPI()

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def sample_by_service(service: str) -> List[Dict]:
    if service == "plumber":
        return [
            {"name": "Игорь, сантехник", "rating": 4.8, "jobs": 132, "priceFrom": 50, "tagline": "Быстро и без навязываний", "phone": "+491234567890"},
            {"name": "Марина, сантехник", "rating": 4.7, "jobs": 64, "priceFrom": 45, "tagline": "Чисто, аккуратно", "phone": "+491111222333"},
        ]
    if service == "electrician":
        return [
            {"name": "Алина, электрик", "rating": 4.9, "jobs": 98, "priceFrom": 60, "tagline": "С гарантией", "phone": "+492222333444"},
            {"name": "Павел, электрик", "rating": 4.6, "jobs": 51, "priceFrom": 55, "tagline": "Розетки и свет", "phone": "+493333444555"},
        ]
    if service == "furniture":
        return [
            {"name": "Денис, сборка мебели", "rating": 4.8, "jobs": 88, "priceFrom": 45, "tagline": "Быстро и ровно", "phone": "+495555666777"},
            {"name": "Сергей, сборка мебели", "rating": 4.7, "jobs": 210, "priceFrom": 40, "tagline": "IKEA", "phone": "+494444555666"},
        ]
    return [
        {"name": "Кирилл, мастер на час", "rating": 4.6, "jobs": 175, "priceFrom": 35, "tagline": "Мелкий ремонт", "phone": "+496666777888"},
        {"name": "Олег, мастер на час", "rating": 4.5, "jobs": 73, "priceFrom": 30, "tagline": "Домашние задачи", "phone": "+497777888999"},
    ]

@app.get("/api/masters")
def get_masters(
    service: str = Query(...),
    radius_km: float = Query(2.0),
    lat: float = Query(...),
    lng: float = Query(...),
):
    base = sample_by_service(service)
    deltas = [(0.004, 0.002), (-0.006, 0.001), (0.002, -0.007), (-0.003, -0.004)]

    out = []
    for i, m in enumerate(base):
        dlat, dlng = deltas[i % len(deltas)]
        mlat = lat + dlat
        mlng = lng + dlng
        dist = haversine_km(lat, lng, mlat, mlng)
        if dist <= radius_km:
            out.append({**m, "distanceKm": round(dist, 2)})

    out.sort(key=lambda x: x["distanceKm"])
    return {"items": out[:5]}

# ВАЖНО: монтируем статику ПОСЛЕ API
app.mount("/", StaticFiles(directory=".", html=True), name="static")
