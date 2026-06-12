from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class GlobalPlayer(Base):
    __tablename__ = "global_players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    photo_path = Column(String, nullable=True)
    
    # Persistent Stats
    total_games = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)

class MatchHistory(Base):
    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    court_name = Column(String)
    team1_names = Column(String) # Comma separated
    team2_names = Column(String) # Comma separated
    winner = Column(String) # "Team 1" or "Team 2"
    duration_min = Column(Integer)
    
    # We can store IDs for analytical purposes if needed
    player_ids = Column(String) # Comma separated IDs

class SyncSession(Base):
    __tablename__ = "sync_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) # e.g., "active_session"
    data = Column(String) # JSON stringified state
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
