import json
import random
from datetime import datetime
from app.config import MIN_LAT, MAX_LAT, MIN_LON, MAX_LON
from app.coastline import is_land

def generate_current_vessels(num_vessels=50, max_attempts=500):
    vessels = []
    attempts = 0
    while len(vessels) < num_vessels and attempts < max_attempts:
        lat = random.uniform(MIN_LAT, MAX_LAT)
        lon = random.uniform(MIN_LON, MAX_LON)
        if lon > 180:
            lon = lon - 360
        if not is_land(lat, lon):
            vessel = {
                "id": len(vessels) + 1,
                "name": f"Vessel_{len(vessels)+1}",
                "latitude": lat,
                "longitude": lon,
                "sog": round(random.uniform(0, 20), 1),
                "cog": random.uniform(0, 360),
                "vessel_type": random.choice(["cargo", "tanker", "passenger", "fishing", "tug"]),
                "timestamp": datetime.now().isoformat()
            }
            vessels.append(vessel)
        attempts += 1
    if len(vessels) < num_vessels:
        print(f"Предупреждение: удалось сгенерировать только {len(vessels)} судов из {num_vessels}")
    with open("data/current_vessels.json", "w") as f:
        json.dump(vessels, f, indent=2)
    print(f"Сгенерировано {len(vessels)} текущих судов в data/current_vessels.json (только на воде)")

if __name__ == "__main__":
    generate_current_vessels()
