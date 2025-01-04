import streamlit as st
import json
import hashlib
import os
from datetime import datetime
from enum import Enum
import pandas as pd
import jwt
from typing import Optional, Dict, List
import time
from pathlib import Path

# Constants
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Better security
    TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours in seconds
    DATA_DIR = Path("data")  # Better file organization

# Create data directory if it doesn't exist
Config.DATA_DIR.mkdir(exist_ok=True)

class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

# Set page configuration
st.set_page_config(
    page_title="Task Scheduler",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Improved CSS styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .task-container {
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 8px;
        margin: 10px 0;
        background-color: #f9f9f9;
        transition: all 0.3s ease;
    }
    .task-container:hover {
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stTextInput>div>div>input {
        background-color: #f0f2f5;
        color: black !important;
        border-radius: 5px;
    }
    .main-header {
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    input[type="text"], input[type="password"] {
        color: black !important;
        background-color: #f0f2f5;
    }
    input::placeholder {
        color: #666 !important;
        opacity: 1 !important;
    }
    .error-message {
        color: #d32f2f;
        padding: 10px;
        border-radius: 5px;
        background-color: #ffebee;
    }
    .success-message {
        color: #388e3c;
        padding: 10px;
        border-radius: 5px;
        background-color: #e8f5e9;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state with type hints
def init_session_state():
    if 'token' not in st.session_state:
        st.session_state.token: Optional[str] = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated: bool = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user: Optional[str] = None
    if 'tasks' not in st.session_state:
        st.session_state.tasks: List[Dict] = []

init_session_state()

# Improved file handling with error handling
class FileHandler:
    @staticmethod
    def load_users() -> Dict:
        users_file = Config.DATA_DIR / 'users.json'
        try:
            if users_file.exists():
                with open(users_file, 'r') as f:
                    return json.load(f)
            return {}
        except json.JSONDecodeError:
            st.error("Error loading users data. File might be corrupted.")
            return {}

    @staticmethod
    def save_users(users: Dict):
        users_file = Config.DATA_DIR / 'users.json'
        try:
            with open(users_file, 'w') as f:
                json.dump(users, f)
        except Exception as e:
            st.error(f"Error saving users data: {str(e)}")

    @staticmethod
    def load_user_tasks(username: str) -> List:
        tasks_file = Config.DATA_DIR / f"tasks_{username}.json"
        try:
            if tasks_file.exists():
                with open(tasks_file, 'r') as f:
                    return json.load(f)
            return []
        except json.JSONDecodeError:
            st.error("Error loading tasks data. File might be corrupted.")
            return []

    @staticmethod
    def save_user_tasks(username: str, tasks: List):
        tasks_file = Config.DATA_DIR / f"tasks_{username}.json"
        try:
            with open(tasks_file, 'w') as f:
                json.dump(tasks, f)
        except Exception as e:
            st.error(f"Error saving tasks data: {str(e)}")

# Improved authentication with better security
class Auth:
    @staticmethod
    def create_token(username: str) -> str:
        expiry = time.time() + Config.TOKEN_EXPIRY
        return jwt.encode(
            {"username": username, "exp": expiry},
            Config.SECRET_KEY,
            algorithm="HS256"
        )

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            if payload["exp"] >= time.time():
                return payload["username"]
        except jwt.InvalidTokenError:
            pass
        except jwt.ExpiredSignatureError:
            st.warning("Session expired. Please login again.")
        return None

    @staticmethod
    def hash_password(password: str) -> str:
        salt = "random_salt"  # In production, use a proper salt
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    @classmethod
    def register_user(cls, username: str, password: str) -> bool:
        if not username or not password:
            st.error("Username and password are required.")
            return False
            
        users = FileHandler.load_users()
        if username in users:
            return False
        
        users[username] = cls.hash_password(password)
        FileHandler.save_users(users)
        return True

    @classmethod
    def verify_user(cls, username: str, password: str) -> bool:
        users = FileHandler.load_users()
        return username in users and users[username] == cls.hash_password(password)

# Task management class
class TaskManager:
    @staticmethod
    def add_task(title: str, description: str, due_date: datetime, priority: str) -> bool:
        if not title.strip():
            st.error("Title is required!")
            return False

        task = {
            "id": str(time.time()),
            "title": title.strip(),
            "description": description.strip(),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "priority": priority,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.tasks.append(task)
        FileHandler.save_user_tasks(st.session_state.current_user, st.session_state.tasks)
        return True

    @staticmethod
    def delete_task(task_id: str):
        st.session_state.tasks = [task for task in st.session_state.tasks if task['id'] != task_id]
        FileHandler.save_user_tasks(st.session_state.current_user, st.session_state.tasks)

    @staticmethod
    def toggle_task(task_id: str):
        for task in st.session_state.tasks:
            if task['id'] == task_id:
                task['completed'] = not task['completed']
                break
        FileHandler.save_user_tasks(st.session_state.current_user, st.session_state.tasks)

    @staticmethod
    def filter_and_sort_tasks(tasks: List, filter_status: str, sort_by: str) -> pd.DataFrame:
        if not tasks:
            return pd.DataFrame()
        
        df = pd.DataFrame(tasks)
        
        # Apply filters
        if filter_status == "Active":
            df = df[~df['completed']]
        elif filter_status == "Completed":
            df = df[df['completed']]
        
        # Apply sorting
        if sort_by == "Due Date":
            df['due_date'] = pd.to_datetime(df['due_date'])
            df = df.sort_values('due_date')
        elif sort_by == "Priority":
            priority_order = {Priority.HIGH.value: 0, Priority.MEDIUM.value: 1, Priority.LOW.value: 2}
            df['priority_order'] = df['priority'].map(priority_order)
            df = df.sort_values('priority_order')
            df = df.drop('priority_order', axis=1)
        else:  # Created Date
            df['created_at'] = pd.to_datetime(df['created_at'])
            df = df.sort_values('created_at', ascending=False)
        
        return df

# UI Components
def login_page():
    st.markdown("<h1 class='main-header'>Task Scheduler</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    if Auth.verify_user(username, password):
                        st.session_state.token = Auth.create_token(username)
                        st.session_state.authenticated = True
                        st.session_state.current_user = username
                        st.session_state.tasks = FileHandler.load_user_tasks(username)
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose Username")
                new_password = st.text_input("Choose Password", type="password")
                register = st.form_submit_button("Register")
                
                if register:
                    if Auth.register_user(new_username, new_password):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username already exists")

def main_page():
    st.markdown(f"<h1 class='main-header'>Welcome {st.session_state.current_user}! 👋</h1>", unsafe_allow_html=True)
    
    # Logout button
    col1, col2, col3 = st.columns([1,1,1])
    with col3:
        if st.button("🚪 Logout"):
            for key in st.session_state.keys():
                del st.session_state[key]
            init_session_state()
            st.rerun()
    
    # Add new task
    with st.expander("➕ Add New Task", expanded=False):
        with st.form(key="add_task_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Task Title")
                priority = st.selectbox("Priority", [p.value for p in Priority])
            with col2:
                due_date = st.date_input("Due Date")
                description = st.text_area("Description")
            
            if st.form_submit_button("Add Task"):
                if TaskManager.add_task(title, description, due_date, priority):
                    st.success("Task added successfully!")
                    st.rerun()

    # Task filters
    col1, col2 = st.columns(2)
    with col1:
        filter_status = st.selectbox("📊 Filter by Status", ["All", "Active", "Completed"])
    with col2:
        sort_by = st.selectbox("🔄 Sort by", ["Due Date", "Priority", "Created Date"])

    # Display tasks
    st.markdown("### 📝 Your Tasks")
    
    if not st.session_state.tasks:
        st.info("No tasks found. Add your first task above!")
        return

    # Filter and sort tasks
    df = TaskManager.filter_and_sort_tasks(st.session_state.tasks, filter_status, sort_by)
    
    # Display tasks
    for _, task in df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                title_text = "✅ " if task['completed'] else "⬜ "
                title_text += task['title']
                st.markdown(f"{title_text}")
                if task['description']:
                    st.markdown(f"{task['description']}")
                st.caption(f"📅 Due: {task['due_date']}")
            
            with col2:
                priority_colors = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
                st.write(f"{priority_colors[task['priority']]} {task['priority']}")
            
            with col3:
                if st.button("✓", key=f"toggle_{task['id']}"):
                    TaskManager.toggle_task(task['id'])
                    st.rerun()
            
            with col4:
                if st.button("🗑", key=f"delete_{task['id']}"):
                    TaskManager.delete_task(task['id'])
                    st.rerun()

def main():
    # Verify token if exists
    if st.session_state.token:
        username = Auth.verify_token(st.session_state.token)
        if not username:
            for key in st.session_state.keys():
                del st.session_state[key]
            init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        main_page()

if __name__ == "__main__":
    main()