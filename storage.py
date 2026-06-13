from altair.vegalite.v5.schema import core
import csv
import io
import json
import os
import datetime
from typing import List

from google.cloud import storage
from models import Match, User, Prediction

def log(message: str) -> None:
   os.write(1, f"{datetime.datetime.now()} - {message}\n".encode())

class StorageEngine:
    def load_matches(self) -> List[Match]:
        raise NotImplementedError
        
    def save_matches(self, matches: List[Match]) -> None:
        raise NotImplementedError
        
    def load_users(self) -> List[User]:
        raise NotImplementedError
        
    def save_users(self, users: List[User]) -> None:
        raise NotImplementedError

class CSVStorageEngine(StorageEngine):
    def __init__(self, matches_file: str, users_file: str):
        os.write(1,("Initialising CSVStorageEngine").encode())
        self.matches_file = matches_file
        self.users_file = users_file
        self._ensure_files()
        
    def _ensure_files(self):
        if not os.path.exists(self.matches_file):
            # Create matches directory if needed
            os.makedirs(os.path.dirname(self.matches_file) or '.', exist_ok=True)
            with open(self.matches_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'home_team', 'away_team', 'date_time_str', 'timezone_offset', 'home_score', 'away_score'])
        
        if not os.path.exists(self.users_file):
            os.makedirs(os.path.dirname(self.users_file) or '.', exist_ok=True)
            with open(self.users_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['username', 'password_hash', 'user_type', 'predictions'])
                
    def load_matches(self) -> List[Match]:
        log(f"Loading matches from CSV")
        matches = []
        with open(self.matches_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            log(f"Reader, about to loop")
            for row in reader:
                log(f"Row: {row}")
                home_score = int(row['home_score']) if row.get('home_score') else None
                away_score = int(row['away_score']) if row.get('away_score') else None
                matches.append(Match(
                    id=row['id'],
                    group_id=row['group_id'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    date_time_str=row['date_time_str'],
                    timezone_offset=row['timezone_offset'],
                    home_score=home_score,
                    away_score=away_score
                ))
        return matches
        
    def save_matches(self, matches: List[Match]) -> None:
        with open(self.matches_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'group_id', 'home_team', 'away_team', 'date_time_str', 'timezone_offset', 'home_score', 'away_score'])
            for m in matches:
                writer.writerow([
                    m.id, m.group_id, m.home_team, m.away_team, m.date_time_str, m.timezone_offset,
                    m.home_score if m.home_score is not None else '',
                    m.away_score if m.away_score is not None else ''
                ])
                
    def load_users(self) -> List[User]:
        users = []
        with open(self.users_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                preds_dict = {}
                if row.get('predictions'):
                    raw_preds = json.loads(row['predictions'])
                    for pid, pdata in raw_preds.items():
                        preds_dict[pid] = Prediction(pid, pdata['home_score'], pdata['away_score'])
                
                users.append(User(
                    username=row['username'],
                    password_hash=row['password_hash'],
                    user_type=row['user_type'],
                    predictions=preds_dict
                ))
        return users
        
    def save_users(self, users: List[User]) -> None:
        with open(self.users_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password_hash', 'user_type', 'predictions'])
            for u in users:
                preds_json = {
                    pid: {'home_score': p.home_score, 'away_score': p.away_score}
                    for pid, p in u.predictions.items()
                }
                writer.writerow([
                    u.username, u.password_hash, u.user_type, json.dumps(preds_json)
                ])


class GCSStorageEngine(StorageEngine):
    def __init__(self, bucket_name: str, matches_blob: str, users_blob: str, credentials_list: dict):
        self.bucket_name = bucket_name
        self.matches_blob = matches_blob
        self.users_blob = users_blob
        
#        if credentials_path:
            #self.client = storage.Client.from_service_account_json(credentials_path)
        self.client = storage.Client.from_service_account_info(credentials_list)
#        else:
#            self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)
        self._ensure_files()
        
    def _ensure_files(self):
        matches_blob_ref = self.bucket.blob(self.matches_blob)
        if not matches_blob_ref.exists():
            f = io.StringIO()
            writer = csv.writer(f)
            writer.writerow(['id', 'group_id', 'home_team', 'away_team', 'date_time_str', 'timezone_offset', 'home_score', 'away_score'])
            matches_blob_ref.upload_from_string(f.getvalue(), content_type='text/csv')
            
        users_blob_ref = self.bucket.blob(self.users_blob)
        if not users_blob_ref.exists():
            f = io.StringIO()
            writer = csv.writer(f)
            writer.writerow(['username', 'password_hash', 'user_type', 'predictions'])
            users_blob_ref.upload_from_string(f.getvalue(), content_type='text/csv')
            
    def load_matches(self) -> List[Match]:
        matches = []
        blob = self.bucket.blob(self.matches_blob)
        content = blob.download_as_text(encoding='utf-8')
        f = io.StringIO(content)
        reader = csv.DictReader(f)
        for row in reader:
            home_score = int(row['home_score']) if row.get('home_score') else None
            away_score = int(row['away_score']) if row.get('away_score') else None
            matches.append(Match(
                id=row['id'],
                group_id=row['group_id'],
                home_team=row['home_team'],
                away_team=row['away_team'],
                date_time_str=row['date_time_str'],
                timezone_offset=row['timezone_offset'],
                home_score=home_score,
                away_score=away_score
            ))
        return matches
        
    def save_matches(self, matches: List[Match]) -> None:
        f = io.StringIO()
        writer = csv.writer(f)
        writer.writerow(['id', 'group_id', 'home_team', 'away_team', 'date_time_str', 'timezone_offset', 'home_score', 'away_score'])
        for m in matches:
            writer.writerow([
                m.id, m.group_id, m.home_team, m.away_team, m.date_time_str, m.timezone_offset,
                m.home_score if m.home_score is not None else '',
                m.away_score if m.away_score is not None else ''
            ])
        blob = self.bucket.blob(self.matches_blob)
        blob.upload_from_string(f.getvalue(), content_type='text/csv')
        
    def load_users(self) -> List[User]:
        os.write(1, f"{datetime.datetime.now()} - Loading users\n".encode())
        users = []
        blob = self.bucket.blob(self.users_blob)
        content = blob.download_as_text(encoding='utf-8')
        f = io.StringIO(content)
        reader = csv.DictReader(f)
        for row in reader:
            preds_dict = {}
            if row.get('predictions'):
                raw_preds = json.loads(row['predictions'])
                for pid, pdata in raw_preds.items():
                    preds_dict[pid] = Prediction(pid, pdata['home_score'], pdata['away_score'])
            
            users.append(User(
                username=row['username'],
                password_hash=row['password_hash'],
                user_type=row['user_type'],
                predictions=preds_dict
            ))
        return users
        
    def save_users(self, users: List[User]) -> None:
        os.write(1, f"{datetime.datetime.now()} - Saving users\n".encode())
        f = io.StringIO()
        writer = csv.writer(f)
        writer.writerow(['username', 'password_hash', 'user_type', 'predictions'])
        for u in users:
            preds_json = {
                pid: {'home_score': p.home_score, 'away_score': p.away_score}
                for pid, p in u.predictions.items()
            }
            writer.writerow([
                u.username, u.password_hash, u.user_type, json.dumps(preds_json)
            ])
        blob = self.bucket.blob(self.users_blob)
        blob.upload_from_string(f.getvalue(), content_type='text/csv')
