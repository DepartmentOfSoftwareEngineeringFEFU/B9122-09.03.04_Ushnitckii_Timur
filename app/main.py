from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import json
from collections import defaultdict
from geopy.distance import distance
from app.config import MIN_LAT, MAX_LAT, MIN_LON, MAX_LON, GRID_STEP_M
from app.router import MaritimeRouter
from app.ml.risk_zones import load_zones
from app.ml.similarity import SimilaritySearch
from app.speed_predictor import SpeedPredictor

app = FastAPI(title="Maritime Route Optimization API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

historical_df = None
router = None
risk_zones = []
similarity_model = None
speed_predictor = None

@app.on_event("startup")
async def startup():
    global historical_df, router, risk_zones, similarity_model, speed_predictor
    try:
        historical_df = pd.read_parquet("data/retrospective.parquet")
        print("Retrospective data loaded")
    except:
        try:
            historical_df = pd.read_parquet("data/historical_enriched.parquet")
            print("Historical data loaded (as retrospective)")
        except:
            print("No retrospective data found. Route will use default speed.")
            historical_df = None
    if historical_df is not None:
        speed_predictor = SpeedPredictor(historical_df)
        print("Speed predictor initialized")
    else:
        speed_predictor = None
        print("Speed predictor not available, using default speed 15 knots")
    router = MaritimeRouter(MIN_LAT, MAX_LAT, MIN_LON, MAX_LON, step_m=GRID_STEP_M)
    try:
        risk_zones = load_zones("data/risk_zones.json")
        print(f"Loaded {len(risk_zones)} risk zones")
    except:
        pass
    similarity_model = SimilaritySearch(k=5)
    try:
        similarity_model.load("models/knn_model.joblib")
        print("k-NN model loaded")
    except:
        print("k-NN model not loaded")
    print("Application startup complete.")

class Point(BaseModel):
    lat: float
    lon: float

class RouteRequest(BaseModel):
    start: Point
    end: Point
    waypoints: Optional[List[Point]] = None
    vessel_type: str = "cargo"
    optimization: str = "time"
    wind_speed: float = 15.0
    wave_height: float = 2.5
    season: int = 1

class SimilarRequest(BaseModel):
    risk_score: float
    wind_speed: float
    wave_height: float
    vessel_type: str
    season: int
    k: int = 5

class AnalyzeRequest(BaseModel):
    segments: List[Dict]
    vessel_type: str

def build_full_path(start, waypoints, end):
    points = [(start.lat, start.lon)]
    if waypoints:
        points.extend([(wp.lat, wp.lon) for wp in waypoints])
    points.append((end.lat, end.lon))
    return points

@app.post("/api/route")
async def get_route(req: RouteRequest):
    if router is None:
        raise HTTPException(status_code=500, detail="Router not initialized")
    full_points = build_full_path(req.start, req.waypoints, req.end)
    all_segments = []
    total_dist = 0
    # Вычисляем погодный риск на основе переданных параметров
    weather_risk = min(1.0, (req.wind_speed / 25.0 + req.wave_height / 8.0) / 2.0)
    for i in range(len(full_points)-1):
        start = full_points[i]
        end = full_points[i+1]
        path = router.route(
            start, end,
            speed_predictor=speed_predictor,
            risk_zones=risk_zones,
            optimization=req.optimization,
            vessel_type=req.vessel_type,
            wind_speed=req.wind_speed,
            wave_height=req.wave_height,
            season=req.season
        )
        if path is None:
            raise HTTPException(status_code=404, detail=f"No route found between {start} and {end}")
        for j in range(len(path)-1):
            p1 = path[j]
            p2 = path[j+1]
            dist = distance(p1, p2).km
            total_dist += dist
            if speed_predictor is not None:
                try:
                    center_lat = (p1[0]+p2[0])/2
                    center_lon = (p1[1]+p2[1])/2
                    predicted_speed = speed_predictor.predict_speed(
                        center_lat, center_lon, req.vessel_type, req.wind_speed, req.wave_height, req.season
                    )
                except:
                    predicted_speed = 15.0
            else:
                predicted_speed = 15.0
            all_segments.append({
                "start": {"lat": p1[0], "lon": p1[1]},
                "end": {"lat": p2[0], "lon": p2[1]},
                "distance_km": dist,
                "recommended_speed_knots": predicted_speed,
                "risk_level": weather_risk,   # теперь риск не нулевой
                "course_deg": np.arctan2(p2[1]-p1[1], p2[0]-p1[0]) * 180/np.pi,
                "warning": "High waves" if req.wave_height > 4 else None
            })
    return {"segments": all_segments, "total_distance_km": total_dist, "optimization": req.optimization}

@app.post("/api/similar")
async def find_similar(req: SimilarRequest):
    if similarity_model is None or historical_df is None:
        raise HTTPException(status_code=500, detail="ML models or historical data not loaded")
    query = {
        "risk_score": req.risk_score,
        "wind_speed": req.wind_speed,
        "wave_height": req.wave_height,
        "vessel_type": req.vessel_type,
        "season": req.season
    }
    indices, distances, recommended_idx = similarity_model.predict(query, historical_df)
    results = historical_df.iloc[indices].to_dict(orient="records")
    recommended = None
    if recommended_idx is not None:
        recommended = historical_df.iloc[recommended_idx].to_dict()
    return {"similar_situations": results, "distances": distances, "recommended": recommended}

@app.post("/api/analyze_route")
async def analyze_route(req: AnalyzeRequest):
    if similarity_model is None or historical_df is None:
        raise HTTPException(status_code=500, detail="ML models or historical data not loaded")
    avg_risk = historical_df['risk_score'].mean()
    avg_wind = historical_df['wind_speed'].mean()
    avg_wave = historical_df['wave_height'].mean()
    import datetime
    current_season = (datetime.datetime.now().month % 12 // 3)
    query = {
        "risk_score": avg_risk,
        "wind_speed": avg_wind,
        "wave_height": avg_wave,
        "vessel_type": req.vessel_type,
        "season": current_season
    }
    indices, distances, recommended_idx = similarity_model.predict(query, historical_df)
    recommended_record = historical_df.iloc[recommended_idx].to_dict() if recommended_idx is not None else None
    recommendation = {
        "avg_risk": avg_risk,
        "avg_wind": avg_wind,
        "avg_wave": avg_wave,
        "similar_count": len(indices),
        "best_match": recommended_record
    }
    return recommendation

@app.get("/api/risk_zones")
async def get_risk_zones():
    return {"zones": risk_zones}

@app.get("/api/land.geojson")
async def get_land_geojson():
    try:
        return FileResponse("data/land_polygons_far_east.geojson", media_type="application/json")
    except:
        return {"error": "Land polygons file not found"}

@app.get("/api/heatmap_data")
async def get_heatmap_data():
    if historical_df is None:
        return {"points": []}
    df = historical_df[['latitude', 'longitude', 'risk_score']].copy()
    df['lat_round'] = df['latitude'].round(1)
    df['lon_round'] = df['longitude'].round(1)
    grouped = df.groupby(['lat_round', 'lon_round']).agg(
        intensity=('risk_score', 'mean')
    ).reset_index()
    heat_data = grouped[['lat_round', 'lon_round', 'intensity']].values.tolist()
    return {"points": heat_data}

@app.get("/api/current_vessels")
async def get_current_vessels():
    try:
        with open("data/current_vessels.json", "r") as f:
            vessels = json.load(f)
        return {"vessels": vessels}
    except FileNotFoundError:
        return {"vessels": []}

@app.get("/api/current_heatmap_data")
async def get_current_heatmap_data():
    try:
        with open("data/current_vessels.json", "r") as f:
            vessels = json.load(f)
    except FileNotFoundError:
        return {"points": []}
    cells = defaultdict(list)
    for v in vessels:
        lat = round(v['latitude'], 1)
        lon = round(v['longitude'], 1)
        cells[(lat, lon)].append(1)
    points = [[lat, lon, len(cells[(lat, lon)])] for (lat, lon) in cells]
    if points:
        max_intensity = max(p[2] for p in points)
        if max_intensity > 0:
            points = [[p[0], p[1], p[2] / max_intensity] for p in points]
    return {"points": points}
