import sqlite3
import os
import cv2
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
            conn.executemany(
                'INSERT INTO prizes (image) VALUES (?)',
                data
            )
            conn.commit()

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute(
                'UPDATE prizes SET used = 1 WHERE prize_id = ?',
                (prize_id,)
            )
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
            return [row[0] for row in cur.fetchall()]

    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT image FROM prizes WHERE prize_id = ?',
                (prize_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT prize_id, image FROM prizes WHERE used = 0 '
                'ORDER BY RANDOM() LIMIT 1'
            )
            return cur.fetchone()

    def get_all_prize_images(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT image FROM prizes')
            return [row[0] for row in cur.fetchall()]

    # ==== Новые методы ====
    def get_winners_count(self, prize_id):
        """Возвращает число победителей для данного prize_id."""
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT COUNT(*) FROM winners WHERE prize_id = ?',
                (prize_id,)
            )
            count = cur.fetchone()[0]
            return count

    def get_rating(self):
        """Возвращает топ-10 пользователей по числу полученных призов (user_name, count_prize)."""
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT u.user_name,
                       COUNT(w.prize_id) AS count_prize
                FROM winners w
                JOIN users u ON u.user_id = w.user_id
                GROUP BY w.user_id
                ORDER BY count_prize DESC
                LIMIT 10
            ''')
            return cur.fetchall()


def hide_img(img_name):
    os.makedirs('hidden_img', exist_ok=True)
    src = os.path.join('img', img_name)
    dst = os.path.join('hidden_img', img_name)

    image = cv2.imread(src)
    if image is None:
        raise FileNotFoundError(f"Не найден исходник: {src}")

    blurred = cv2.GaussianBlur(image, (15, 15), 0)
    small = cv2.resize(blurred, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated = cv2.resize(
        small,
        (image.shape[1], image.shape[0]),
        interpolation=cv2.INTER_NEAREST
    )
    cv2.imwrite(dst, pixelated)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    existing = set(manager.get_all_prize_images())
    folder = 'img'
    if os.path.isdir(folder):
        to_add = [(f,) for f in os.listdir(folder)
                  if os.path.isfile(os.path.join(folder, f)) and f not in existing]
        if to_add:
            manager.add_prize(to_add)
            print(f"Добавлено новых призов: {len(to_add)}")
        else:
            print("Новых изображений для добавления не найдено.")
    else:
        print(f"Папка `{folder}` не найдена!")

    manager.reset_all_prizes()
    print("Все призы отмечены как неиспользованные (used = 0).")
