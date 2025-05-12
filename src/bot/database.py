import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_file="jobani.db"):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # Only create users table with preferences
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_id INTEGER PRIMARY KEY,
                     preferences TEXT,
                     subscribed BOOLEAN DEFAULT 1,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (user_id, subscribed) VALUES (?, 1)", (user_id,))
        conn.commit()
        conn.close()
    
    def remove_user(self, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("UPDATE users SET subscribed = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    
    def update_preferences(self, user_id, preferences):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("UPDATE users SET preferences = ? WHERE user_id = ?", 
                 (json.dumps(preferences), user_id))
        conn.commit()
        conn.close()
    
    def get_user_preferences(self, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT preferences FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        if result and result[0]:
            return json.loads(result[0])
        return None
    
    def get_all_subscribed_users(self):
        """Get all subscribed users and their preferences"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT user_id, preferences FROM users WHERE subscribed = 1")
        results = c.fetchall()
        conn.close()
        
        users = []
        for row in results:
            users.append({
                'user_id': row[0],
                'preferences': json.loads(row[1]) if row[1] else {}
            })
        return users
    
    def _job_matches_preferences(self, job, preferences):
        """Check if a job matches user preferences"""
        if not preferences:
            return True
            
        exam_type = preferences.get('exam_type')
        state = preferences.get('state')
        
        if not exam_type or exam_type == 'all':
            return True
            
        if exam_type == 'state' and state:
            return state.lower() in job['title'].lower()
            
        return exam_type.lower() in job['title'].lower() 