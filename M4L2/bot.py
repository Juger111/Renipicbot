# bot.py
import os
import threading
import time
import sqlite3
import cv2

import schedule
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from logic import DatabaseManager, hide_img, create_collage
from config import API_TOKEN, DATABASE

bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)
manager.create_tables()

def gen_markup(prize_id):
    m = InlineKeyboardMarkup(row_width=1)
    m.add(InlineKeyboardButton("Получить!", callback_data=str(prize_id)))
    return m

@bot.message_handler(commands=['старт'])
def handle_start(msg):
    uid = msg.chat.id
    if uid in manager.get_users():
        bot.reply_to(msg, "Ты уже зарегистрирован!")
    else:
        manager.add_user(uid, msg.from_user.username or '')
        bot.reply_to(msg, "Добро пожаловать! Жди рассылок и успей нажать «Получить!» первым.")

@bot.message_handler(commands=['рейтинг'])
def handle_rating(msg):
    rating = manager.get_rating()
    if not rating:
        bot.send_message(msg.chat.id, "Рейтинг пока пуст.")
        return
    txt = "Топ-10 по призам:\n" + "\n".join(f"{i+1}. {u} — {c}" for i,(u,c) in enumerate(rating))
    bot.send_message(msg.chat.id, txt)

@bot.message_handler(commands=['мои_достижения'])
def handle_my_score(msg):
    uid = msg.chat.id
    won = manager.get_winners_img(uid)  # список имён файлов
    all_imgs = [f for f in os.listdir('img') if os.path.isfile(os.path.join('img', f))]
    paths = []
    for fname in all_imgs:
        if fname in won:
            paths.append(os.path.join('img', fname))
        else:
            paths.append(os.path.join('hidden_img', fname))
    try:
        collage = create_collage(paths)
        tmp = f'collage_{uid}.jpg'
        cv2.imwrite(tmp, collage)
        with open(tmp, 'rb') as ph:
            bot.send_photo(uid, ph, caption="Твои достижения 🎉")
        os.remove(tmp)
    except Exception as e:
        bot.send_message(uid, f"Не удалось собрать коллаж: {e}")

@bot.callback_query_handler(func=lambda c: c.data and c.data.isdigit())
def handle_prize_cb(call):
    pid = int(call.data)
    uid = call.from_user.id
    already = manager.get_winners_count(pid)
    if already < 3:
        img = manager.get_prize_img(pid)
        if img:
            bot.send_photo(call.message.chat.id, open(os.path.join('img', img),'rb'))
            conn = sqlite3.connect(DATABASE)
            with conn:
                conn.execute(
                    'INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, datetime("now"))',
                    (uid, pid)
                )
            bot.answer_callback_query(call.id, "Ты выиграл!")
        else:
            bot.answer_callback_query(call.id, "Ошибка: нет изображения.")
    else:
        bot.answer_callback_query(call.id, "Увы, приз разобран.")

def send_message():
    prize = manager.get_random_prize()
    if prize is None:
        print("Нет доступных призов")
        return
    pid, img = prize
    manager.mark_prize_used(pid)
    try:
        hide_img(img)
    except FileNotFoundError as e:
        print(e); return
    hid = os.path.join('hidden_img', img)
    for user in manager.get_users():
        with open(hid, 'rb') as ph:
            bot.send_photo(user, ph, reply_markup=gen_markup(pid))

def schedule_thread():
    schedule.every().hour.do(send_message)
    while True:
        schedule.run_pending(); time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=lambda: bot.polling(none_stop=True), daemon=True).start()
    threading.Thread(target=schedule_thread, daemon=True).start()
    while True:
        time.sleep(10)
