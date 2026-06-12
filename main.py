import os
import json
from typing import List, Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, database
from database import engine, get_db
import shutil
import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/api/players")
def get_players(db: Session = Depends(get_db)):
    return db.query(models.GlobalPlayer).all()

@app.post("/api/players")
async def create_player(
    name: str = Form(...),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Check if player exists
    db_player = db.query(models.GlobalPlayer).filter(models.GlobalPlayer.name == name).first()
    
    if db_player:
        # Update photo if provided
        if photo:
            file_ext = photo.filename.split(".")[-1]
            file_name = f"{name}_{int(datetime.datetime.utcnow().timestamp())}.{file_ext}"
            photo_path = os.path.join(UPLOAD_DIR, file_name)
            with open(photo_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            db_player.photo_path = photo_path
        
        db_player.last_seen = datetime.datetime.utcnow()
        db.commit()
        db.refresh(db_player)
        return db_player

    photo_path = None
    if photo:
        file_ext = photo.filename.split(".")[-1]
        file_name = f"{name}_{int(datetime.datetime.utcnow().timestamp())}.{file_ext}"
        photo_path = os.path.join(UPLOAD_DIR, file_name)
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

    new_player = models.GlobalPlayer(
        name=name,
        photo_path=photo_path
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player

@app.post("/api/matches/resolve")
async def resolve_match(
    court_name: str = Form(...),
    team1_names: str = Form(...),
    team2_names: str = Form(...),
    winner: str = Form(...),
    duration_min: int = Form(...),
    player_ids: str = Form(...),
    db: Session = Depends(get_db)
):
    # Create history record
    match = models.MatchHistory(
        court_name=court_name,
        team1_names=team1_names,
        team2_names=team2_names,
        winner=winner,
        duration_min=duration_min,
        player_ids=player_ids
    )
    db.add(match)
    
    # Update global stats for players
    ids = [int(id_str) for id_str in player_ids.split(",") if id_str]
    team1_list = team1_names.split(" & ")
    team2_list = team2_names.split(" & ")
    
    for player_id in ids:
        player = db.query(models.GlobalPlayer).filter(models.GlobalPlayer.id == player_id).first()
        if player:
            player.total_games += 1
            # Check if this player was on the winning team
            is_winner = False
            if winner == "Team 1" and player.name in team1_list:
                is_winner = True
            elif winner == "Team 2" and player.name in team2_list:
                is_winner = True
            
            if is_winner:
                player.total_wins += 1
            
            # Simple rating update logic
            player.rating = (player.total_wins / player.total_games) * 100
            
    db.commit()
    return {"status": "success"}

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    return db.query(models.MatchHistory).order_by(models.MatchHistory.timestamp.desc()).limit(50).all()

# --- MULTI-DEVICE SESSION SYNC ---

@app.get("/api/session/sync")
def get_session_state(db: Session = Depends(get_db)):
    session = db.query(models.SyncSession).filter(models.SyncSession.key == "active_session").first()
    if not session:
        return {"data": None, "updated_at": None}
    return {"data": json.loads(session.data), "updated_at": session.updated_at.isoformat()}

@app.post("/api/session/sync")
async def post_session_state(
    state: dict = Body(...),
    client_timestamp: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    session = db.query(models.SyncSession).filter(models.SyncSession.key == "active_session").first()
    
    if session and client_timestamp:
        # Simple conflict resolution: server timestamp wins if newer
        server_ts = session.updated_at.replace(tzinfo=None)
        try:
            # Handle possible Z or offset in isoformat
            client_ts = datetime.datetime.fromisoformat(client_timestamp.replace('Z', '+00:00')).replace(tzinfo=None)
            if server_ts > client_ts:
                return {
                    "status": "conflict", 
                    "message": "Server has newer state", 
                    "data": json.loads(session.data),
                    "updated_at": session.updated_at.isoformat()
                }
        except ValueError:
            pass

    if not session:
        session = models.SyncSession(key="active_session")
        db.add(session)
    
    session.data = json.dumps(state)
    session.updated_at = datetime.datetime.utcnow()
    db.commit()
    
    return {
        "status": "success", 
        "updated_at": session.updated_at.isoformat()
    }
