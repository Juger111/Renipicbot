# logic.py
import sqlite3
import os
import cv2
import numpy as np
from math import sqrt, ceil, floor
from config import DATABASE

class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS prizes (
                    prize_id INTEGER PRIMARY KEY,
                    image TEXT,
                    used INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS winners (
                    user_id INTEGER,
                    prize_id INTEGER,
                    win_time TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
                )
            ''')
            conn.commit()

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute(
                'INSERT OR IGNORE INTO users (user_id, user_name) VALUES (?, ?)',
                (user_id, user_name)
            )
            conn.commit()

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany('INSERT INTO prizes (image) VALUES (?)', data)
            conn.commit()

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('UPDATE prizes SET used = 1 WHERE prize_id = ?', (prize_id,))
            conn.commit()

    def reset_all_prizes(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('UPDATE prizes SET used = 0')
            conn.commit()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT user_id FROM users')
            return [r[0] for r in cur.fetchall()]

    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT image FROM prizes WHERE prize_id = ?', (prize_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT prize_id, image FROM prizes WHERE used = 0 ORDER BY RANDOM() LIMIT 1')
            return cur.fetchone()  # None или (prize_id, image)

    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM winners WHERE prize_id = ?', (prize_id,))
            return cur.fetchone()[0]

    def get_rating(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT u.user_name, COUNT(w.prize_id) AS count_prize
                FROM winners w
                JOIN users u ON u.user_id = w.user_id
                GROUP BY w.user_id
                ORDER BY count_prize DESC
                LIMIT 10
            ''')
            return cur.fetchall()

    def get_winners_img(self, user_id):
        """Возвращает список имён файлов изображений, которые выиграл пользователь."""
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT p.image
                FROM winners w
                JOIN prizes p ON w.prize_id = p.prize_id
                WHERE w.user_id = ?
            ''', (user_id,))
            return [r[0] for r in cur.fetchall()]

def hide_img(img_name):
    os.makedirs('hidden_img', exist_ok=True)
    src = os.path.join('img', img_name)
    dst = os.path.join('hidden_img', img_name)
    image = cv2.imread(src)
    if image is None:
        raise FileNotFoundError(f"Не найден исходник: {src}")
    blurred = cv2.GaussianBlur(image, (15,15), 0)
    small = cv2.resize(blurred, (30,30), interpolation=cv2.INTER_NEAREST)
    pixelated = cv2.resize(small, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(dst, pixelated)

def create_collage(image_paths):
    """Собирает коллаж из списка путей к картинкам."""
    images = [cv2.imread(p) for p in image_paths]
    images = [img for img in images if img is not None]
    if not images:
        raise ValueError("Нет изображений для коллажа")
    h, w = images[0].shape[:2]
    num = len(images)
    cols = floor(sqrt(num)) or 1
    rows = ceil(num / cols)
    collage = np.zeros((rows*h, cols*w, 3), dtype=np.uint8)
    for idx, img in enumerate(images):
        r = idx // cols
        c = idx % cols
        collage[r*h:(r+1)*h, c*w:(c+1)*w] = img
    return collage

if __name__ == '__main__':
    mgr = DatabaseManager(DATABASE)
    mgr.create_tables()
    # ... загрузка призов и сброс used как раньше ...
