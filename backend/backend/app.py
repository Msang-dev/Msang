from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import json
from typing import Optional, List
import os
from supabase import create_client, Client
import jwt
from passlib.context import CryptContext
import asyncio
from contextlib import asynccontextmanager

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Supabase setup
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# JWT setup
SECRET_KEY = os.getenv("SECRET_KEY", "kenya-smart-grid-student-project-2024")
ALGORITHM = "HS256"

class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class GridData(BaseModel):
    frequency: float
    load_demand: float
    geothermal: float
    hydro: float
    wind: float
    solar: float
    thermal: float
    bess_power: float
    bess_soc: float
    total_generation: float
    scenario: str

class SmartGridSimulator:
    def __init__(self):
        self.nominal_frequency = 50.0
        self.bess_capacity_mw = 300
        self.bess_capacity_mwh = 300
        self.bess_soc = 65
        
        self.geothermal_capacity = 985
        self.hydro_capacity = 826
        self.wind_capacity = 170
        self.solar_capacity = 80
        self.thermal_capacity = 255
        
        self.scenario_modifiers = {
            'normal': {'frequency_var': 0.15, 'load_var': 30},
            'load_surge': {'frequency_var': 0.25, 'load_var': 80, 'load_bias': 80},
            'generator_trip': {'frequency_var': 0.4, 'load_var': 30, 'generation_bias': -150},
            'renewable_drop': {'frequency_var': 0.3, 'load_var': 30, 'solar_bias': -80, 'wind_bias': -100},
            'blackout': {'frequency_var': 0.5, 'load_var': 10, 'load_bias': -300}
        }

    def generate_grid_data(self, scenario='normal'):
        modifier = self.scenario_modifiers.get(scenario, self.scenario_modifiers['normal'])
        
        base_load = 1800
        load_variation = np.random.uniform(-modifier['load_var'] * 3, modifier['load_var'] * 3)
        load_bias = modifier.get('load_bias', 0)
        current_load = max(1000, base_load + load_variation + load_bias)
        
        freq_variation = np.random.uniform(-modifier['frequency_var'], modifier['frequency_var'])
        current_frequency = self.nominal_frequency + freq_variation
        
        hour = datetime.now().hour
        
        geo_gen = self.geothermal_capacity * np.random.uniform(0.80, 0.95)
        hydro_gen = self.hydro_capacity * np.random.uniform(0.80, 0.90)
        
        wind_bias = modifier.get('wind_bias', 0)
        wind_gen = max(0, self.wind_capacity * np.random.uniform(0.50, 0.80) + wind_bias)
        
        solar_bias = modifier.get('solar_bias', 0)
        if 6 <= hour <= 18:
            solar_intensity = np.sin((hour - 6) * np.pi / 12)
            solar_gen = self.solar_capacity * solar_intensity * np.random.uniform(0.8, 1.0) + solar_bias
        else:
            solar_gen = 0
        
        thermal_gen = self.thermal_capacity * np.random.uniform(0.40, 0.80)
        total_conventional = geo_gen + hydro_gen + wind_gen + solar_gen + thermal_gen
        
        bess_power = 0
        generation_balance = total_conventional - current_load
        
        max_charge_power = self.bess_capacity_mw
        max_discharge_power = self.bess_capacity_mw
        
        if current_frequency > 50.1 and self.bess_soc < 100:
            available_charge_capacity = (100 - self.bess_soc) * self.bess_capacity_mwh / 100
            charge_power = min(max_charge_power, generation_balance, available_charge_capacity)
            if charge_power > 0:
                bess_power = -charge_power
                energy_stored_mwh = abs(bess_power) * (2 / 3600)
                soc_increase = (energy_stored_mwh / self.bess_capacity_mwh) * 100
                self.bess_soc = min(100, self.bess_soc + soc_increase)
                
        elif current_frequency < 49.9 and self.bess_soc > 0:
            available_discharge_capacity = (self.bess_soc - 0) * self.bess_capacity_mwh / 100
            discharge_power = min(max_discharge_power, current_load - total_conventional, available_discharge_capacity)
            if discharge_power > 0:
                bess_power = discharge_power
                energy_discharged_mwh = bess_power * (2 / 3600)
                soc_decrease = (energy_discharged_mwh / self.bess_capacity_mwh) * 100
                self.bess_soc = max(0, self.bess_soc - soc_decrease)
        
        generation_bias = modifier.get('generation_bias', 0)
        if scenario == 'generator_trip':
            geo_gen = max(0, geo_gen * 0.7)
        
        if scenario == 'blackout':
            current_load = max(200, current_load * 0.1)
            current_frequency = max(48, min(52, current_frequency))
        
        total_generation = geo_gen + hydro_gen + wind_gen + solar_gen + thermal_gen + bess_power
        
        return {
            'timestamp': datetime.now().isoformat(),
            'frequency': round(current_frequency, 2),
            'load_demand': round(current_load, 1),
            'geothermal': round(geo_gen, 1),
            'hydro': round(hydro_gen, 1),
            'wind': round(wind_gen, 1),
            'solar': round(solar_gen, 1),
            'thermal': round(thermal_gen, 1),
            'bess_power': round(bess_power, 1),
            'bess_soc': round(self.bess_soc, 1),
            'total_generation': round(total_generation, 1),
            'scenario': scenario
        }

simulator = SmartGridSimulator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Kenyan Smart Grid System Starting...")
    
    # Create tables in Supabase
    try:
        # Users table
        supabase.table("users").select("*").limit(1).execute()
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"⚠️ Database setup needed: {e}")
    
    yield
    # Shutdown
    print("🛑 System shutting down...")

app = FastAPI(title="Kenyan Smart Grid API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# Routes
@app.get("/")
async def root():
    return {"message": "🇰🇪 Kenyan Smart Grid Dispatch System API", "status": "active"}

@app.post("/register")
async def register(user: UserRegister):
    try:
        # Check if user exists
        existing_user = supabase.table("users").select("*").eq("username", user.username).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Hash password
        hashed_password = get_password_hash(user.password)
        
        # Create user
        new_user = {
            "username": user.username,
            "email": user.email,
            "password_hash": hashed_password,
            "full_name": user.full_name,
            "role": "operator",
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("users").insert(new_user).execute()
        
        # Create token
        access_token = create_access_token(data={"sub": user.username})
        
        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user.username,
                "full_name": user.full_name,
                "role": "operator"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login(user: UserLogin):
    try:
        # Find user
        result = supabase.table("users").select("*").eq("username", user.username).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        db_user = result.data[0]
        
        # Verify password
        if not verify_password(user.password, db_user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Update last login
        supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("username", user.username).execute()
        
        # Create token
        access_token = create_access_token(data={"sub": user.username})
        
        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": db_user["username"],
                "full_name": db_user["full_name"],
                "role": db_user["role"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/grid/current")
async def get_current_grid_data(current_user: str = Depends(get_current_user)):
    try:
        data = simulator.generate_grid_data('normal')
        
        # Log the data access
        log_entry = {
            "username": current_user,
            "action": "grid_data_access",
            "description": f"Accessed current grid data",
            "timestamp": datetime.now().isoformat()
        }
        supabase.table("user_activity").insert(log_entry).execute()
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/grid/scenario/{scenario_name}")
async def set_scenario(scenario_name: str, current_user: str = Depends(get_current_user)):
    valid_scenarios = ['normal', 'load_surge', 'generator_trip', 'renewable_drop', 'blackout']
    if scenario_name not in valid_scenarios:
        raise HTTPException(status_code=400, detail="Invalid scenario")
    
    data = simulator.generate_grid_data(scenario_name)
    
    # Log scenario change
    log_entry = {
        "username": current_user,
        "action": "scenario_change",
        "description": f"Changed scenario to {scenario_name}",
        "timestamp": datetime.now().isoformat()
    }
    supabase.table("user_activity").insert(log_entry).execute()
    
    return {"message": f"Scenario changed to {scenario_name}", "data": data}

@app.get("/grid/history")
async def get_grid_history(current_user: str = Depends(get_current_user)):
    # Generate some historical data
    history = []
    for i in range(50):
        timestamp = datetime.now() - timedelta(minutes=i)
        data = simulator.generate_grid_data()
        data['timestamp'] = timestamp.isoformat()
        history.append(data)
    
    return {"history": history}

@app.get("/system/status")
async def get_system_status():
    return {
        "status": "operational",
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "kenya_capacity": {
            "geothermal": 985,
            "hydro": 826,
            "wind": 170,
            "solar": 80,
            "thermal": 255,
            "total": 2316
        },
        "bess_specs": {
            "power_capacity": 300,
            "energy_capacity": 300,
            "soc_range": "0-100%"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
