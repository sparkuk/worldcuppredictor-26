import streamlit as st
import datetime
import os
from models import Match, Prediction, User
from storage import CSVStorageEngine, GCSStorageEngine
from scoring import calculate_points
from auth import hash_password, authenticate
import pandas as pd

st.set_page_config(page_title="World Cup Predictor", layout="wide")

MATCHES_FILE = st.secrets['file_names']['matches_file']
USERS_FILE = st.secrets['file_names']['users_file']

# CUTOFF DATE for Prediction Editing as per requirements
CUTOFF_DATE = datetime.datetime(2026, 6, 11)

def friendly_date(date_str: str) -> str:
    date = datetime.datetime.strptime(date_str,"%Y-%m-%dT%H:%M:%S")
    return datetime.datetime.strftime(date,'%a %d %b %H:%M')

def log(message: str) -> None:
   os.write(1, f"{datetime.datetime.now()} - {message}\n".encode())
    

@st.cache_resource
def get_storage():
    # GCS version
    #    return GCSStorageEngine('worldcuppredictor-26', MATCHES_FILE, USERS_FILE, './.streamlit/mc-web-219823-3929ff8ca756.json')
    log(f"Matches File: {MATCHES_FILE}\n")
    log(f"Users File: {USERS_FILE}\n")
    log(f"GCS Access File: {st.secrets['file_names']['gcs_access_file']}\n")
    credentials_dict = {
        'type': 'service_account',
        "project_id": st.secrets['connection_gcs']['project_id'],
        "private_key_id": st.secrets['connection_gcs']['private_key_id'],
        "private_key": st.secrets['connection_gcs']['private_key'],
        "client_email": st.secrets['connection_gcs']['client_email'],
        "client_id": st.secrets['connection_gcs']['client_id'],
        "auth_uri": st.secrets['connection_gcs']['auth_uri'],
        "token_uri": st.secrets['connection_gcs']['token_uri'],
        "auth_provider_x509_cert_url": st.secrets['connection_gcs']['auth_provider_x509_cert_url'],
        "client_x509_cert_url": st.secrets['connection_gcs']['client_x509_cert_url'],
        "universe_domain": st.secrets['connection_gcs']['universe_domain']
    }

    return GCSStorageEngine('worldcuppredictor-26', MATCHES_FILE, USERS_FILE, credentials_dict)

    # CSV version
#    return CSVStorageEngine(MATCHES_FILE, USERS_FILE)

storage = get_storage()

def init_session_state():
    if 'current_user' not in st.session_state:
        st.session_state['current_user'] = None

init_session_state()

def do_login():
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user = authenticate(username, password, storage)
        if user:
            st.session_state['current_user'] = user
            st.sidebar.success(f"Logged in as {user.username}")
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")

def do_logout():
    st.sidebar.write(f"Logged in as: {st.session_state['current_user'].username}")
    if st.sidebar.button("Logout"):
        st.session_state['current_user'] = None
        st.rerun()

def view_leaderboard():
    st.header("League Table")
    users = storage.load_users()
    matches = storage.load_matches()
    
    leaderboard_data = []
    
    for u in users:
        total_points = 0
        for m in matches:
            if m.home_score is not None and m.away_score is not None:
                if m.id in u.predictions:
                    pred = u.predictions[m.id]
                    pts = calculate_points(pred.home_score, pred.away_score, m.home_score, m.away_score)
                    total_points += pts
        leaderboard_data.append({"User": u.username, "Points": total_points})
        
    if leaderboard_data:
        df = pd.DataFrame(leaderboard_data).sort_values(by="Points", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No users found.")

def view_upcoming_matches():
    st.header("Upcoming Matches")
    matches = storage.load_matches()
    
    now = datetime.datetime.now()
    future_matches = []
    
    for m in matches:
        try:
            m_date = pd.to_datetime(f"{m.date_time_str} {m.timezone_offset}")
            m_date_naive = m_date.replace(tzinfo=None)
            if m_date_naive >= now:
                future_matches.append((m_date_naive, m))
        except Exception as e:
            # Fallback for naive string
            try:
                m_date = datetime.datetime.strptime(m.date_time_str, "%Y-%m-%d %H:%M")
                if m_date >= now:
                    future_matches.append((m_date, m))
            except Exception:
                pass
                
    # Sort by date and take the next 6
    future_matches.sort(key=lambda x: x[0])
    upcoming = [m for _, m in future_matches[:6]]
            
    if not upcoming:
        st.info("No upcoming matches.")
    else:
        users = storage.load_users()
        for m in upcoming:
            st.write(f"**{m.home_team} vs {m.away_team}** - {friendly_date(m.date_time_str)} ({m.timezone_offset})")
            st.write("Predictions:")
            preds_list = []
            for u in users:
                if m.id in u.predictions:
                    p = u.predictions[m.id]
                    preds_list.append(f"{u.username}: {p.home_score} - {p.away_score}")
                    
            if preds_list:
                for pl in preds_list:
                    st.write(f"- {pl}")
            else:
                st.write("- None yet")
            st.markdown("---")

def view_recent_matches():
    st.header("Recent Matches")
    matches = storage.load_matches()
    
    now = datetime.datetime.now()
    past_matches = []
    
    for m in matches:
        try:
            m_date = pd.to_datetime(f"{m.date_time_str} {m.timezone_offset}")
            m_date_naive = m_date.replace(tzinfo=None)
            if m_date_naive < now:
                past_matches.append((m_date_naive, m))
        except Exception as e:
            # Fallback for naive string
            try:
                m_date = datetime.datetime.strptime(m.date_time_str, "%Y-%m-%d %H:%M")
                if m_date < now:
                    past_matches.append((m_date, m))
            except Exception:
                pass
                
    # Sort by date descending and take the first 6
    past_matches.sort(key=lambda x: x[0], reverse=True)
    recent = [m for _, m in past_matches[:6]]
            
    if not recent:
        st.info("No recent matches.")
    else:
        for m in recent:
            st.write(f"**{m.home_team} vs {m.away_team}** - {friendly_date(m.date_time_str)} ({m.timezone_offset})")
            if m.home_score is not None and m.away_score is not None:
                st.write(f"**Final Score: {m.home_score} - {m.away_score}**")
            else:
                st.write("**Final Score: Not yet entered**")
                
            st.write("Predictions:")
            users = storage.load_users()
            preds_list = []
            for u in users:
                if m.id in u.predictions:
                    p = u.predictions[m.id]
                    pts_str = ""
                    if m.home_score is not None and m.away_score is not None:
                        pts = calculate_points(p.home_score, p.away_score, m.home_score, m.away_score)
                        pts_str = f" ({pts} pts)"
                    preds_list.append(f"{u.username}: {p.home_score} - {p.away_score}{pts_str}")
                    
            if preds_list:
                for pl in preds_list:
                    st.write(f"- {pl}")
            else:
                st.write("- None yet")
            st.markdown("---")

def view_player_dashboard(user: User):
    st.header("My Predictions")
    now = datetime.datetime.now()
    can_edit = now < CUTOFF_DATE
    
    if not can_edit:
        st.warning("Prediction editing is closed. (Cutoff: June 11th, 2026)")
        
    matches = storage.load_matches()
    
    with st.form("predictions_form"):
        updated_predictions = {}
        for m in matches:
            #st.subheader(f"{m.home_team} vs {m.away_team}")
            #st.write(f"Date: {friendly_date(m.date_time_str)} {m.timezone_offset}")
            st.write(f"Group {m.group_id} - {friendly_date(m.date_time_str)}")
            
            existing_pred = user.predictions.get(m.id)
            home_val = existing_pred.home_score if existing_pred else 0
            away_val = existing_pred.away_score if existing_pred else 0
            
            #col1, col2 = st.columns(2)
            #with col1:
            #    new_home = st.number_input(f"{m.home_team} Score", min_value=0, value=home_val, key=f"h_{m.id}", disabled=not can_edit)
            #with col2:
            #    new_away = st.number_input(f"{m.away_team} Score", min_value=0, value=away_val, key=f"a_{m.id}", disabled=not can_edit)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.subheader(f"\n{m.home_team}")
            with col2:
                new_home = st.number_input("Home score", min_value=0, value=home_val, key=f"h_{m.id}", disabled=not can_edit, label_visibility="collapsed")
            with col3:
                new_away = st.number_input("Away Score", min_value=0, value=away_val, key=f"a_{m.id}", disabled=not can_edit, label_visibility="collapsed")
            with col4:
                st.subheader(f"{m.away_team}")
            #with col5: 
            #    date = datetime.datetime.strptime(m.date_time_str,"%Y-%m-%dT%H:%M:%S")
            #    st.write(f"{datetime.datetime.strftime(date,'%a %d %b')}")



            updated_predictions[m.id] = Prediction(m.id, new_home, new_away)
            st.markdown("---")
            
        if can_edit:
            submitted = st.form_submit_button("Save Predictions")
            if submitted:
                users = storage.load_users()
                for i, u in enumerate(users):
                    if u.username == user.username:
                        users[i].predictions = updated_predictions
                        break
                storage.save_users(users)
                st.session_state['current_user'].predictions = updated_predictions
                st.success("Predictions saved successfully!")

def view_admin_dashboard():
    st.header("Admin Dashboard: Enter Match Results")
    matches = storage.load_matches()
    
    with st.form("results_form"):
        updated_matches = []
        for m in matches:
            st.subheader(f"{m.home_team} vs {m.away_team}")
            st.write(f"Date: {m.date_time_str} {m.timezone_offset}")
            
            col1, col2 = st.columns(2)
            with col1:
                home_res = st.number_input(f"Actual {m.home_team} Score", min_value=-1, value=m.home_score if m.home_score is not None else -1, key=f"res_h_{m.id}")
            with col2:
                away_res = st.number_input(f"Actual {m.away_team} Score", min_value=-1, value=m.away_score if m.away_score is not None else -1, key=f"res_a_{m.id}")
                
            updated_m = Match(
                id=m.id,
                group_id=m.group_id,
                home_team=m.home_team,
                away_team=m.away_team,
                date_time_str=m.date_time_str,
                timezone_offset=m.timezone_offset,
                home_score=home_res if home_res >= 0 else None,
                away_score=away_res if away_res >= 0 else None
            )
            updated_matches.append(updated_m)
            st.markdown("---")
            
        submitted = st.form_submit_button("Save Results")
        if submitted:
            storage.save_matches(updated_matches)
            st.success("Match results updated successfully!")

def main():
    if st.session_state['current_user'] is None:
        do_login()
    else:
        do_logout()
        
    st.title("World Cup Predictor")

    user = st.session_state['current_user']

    if user is None:
        tab1, tab2, tab3 = st.tabs(["League Table", "Recent Matches", "Upcoming Matches"])
        with tab1:
            view_leaderboard()
        with tab2:
            view_recent_matches()
        with tab3:
            view_upcoming_matches()
            
    else:
        if user.user_type == 'admin':
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["League Table", "Recent Matches", "Upcoming Matches", "My Predictions", "Admin: Edit Results"])
            with tab1:
                view_leaderboard()
            with tab2:
                view_recent_matches()
            with tab3:
                view_upcoming_matches()
            with tab4:
                view_player_dashboard(user)
            with tab5:
                view_admin_dashboard()
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["League Table", "Recent Matches", "Upcoming Matches", "My Predictions"])
            with tab1:
                view_leaderboard()
            with tab2:
                view_recent_matches()
            with tab3:
                view_upcoming_matches()
            with tab4:
                view_player_dashboard(user)

if __name__ == "__main__":
    main()
