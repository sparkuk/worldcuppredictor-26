from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Match:
    id: str
    group_id: str
    home_team: str
    away_team: str
    date_time_str: str  # local time string
    timezone_offset: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None

@dataclass
class Prediction:
    match_id: str
    home_score: int
    away_score: int

@dataclass
class User:
    username: str
    password_hash: str
    user_type: str  # 'player' or 'admin'
    predictions: Dict[str, Prediction]  # match_id -> Prediction
