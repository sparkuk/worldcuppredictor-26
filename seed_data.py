from models import Match, User, Prediction
from storage import CSVStorageEngine
from auth import hash_password
import datetime

storage = CSVStorageEngine('matches.csv', 'users.csv')

def seed():
    now = datetime.datetime.now()
    in_5_hours = now + datetime.timedelta(hours=5)
    
    matches = [
        Match("m1", "Brazil", "Argentina", in_5_hours.strftime("%Y-%m-%d %H:%M"), "+00:00"),
        Match("m2", "Germany", "France", "2026-06-13 20:00", "+00:00"),
        Match("m3", "Spain", "Italy", "2026-06-14 15:00", "+00:00"),
    ]
    storage.save_matches(matches)
    
    admin_pw = hash_password("admin123")
    player_pw = hash_password("player123")
    
    users = [
        User("admin", admin_pw, "admin", {}),
        User("player1", player_pw, "player", {"m1": Prediction("m1", 2, 1)}),
        User("player2", player_pw, "player", {"m1": Prediction("m1", 1, 1), "m2": Prediction("m2", 0, 2)})
    ]
    storage.save_users(users)
    print("Database seeded with sample data.")

if __name__ == "__main__":
    seed()
