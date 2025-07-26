import os
import threading
import time
import sqlite3

import schedule
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from logic import DatabaseManager, hide_img
from config import API_TOKEN, DATABASE

# Инициализация бота и менеджера базы
bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)
manager.create_tables()

# Генерация разметки для кнопки
def gen_markup(prize_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Получить!", callback_data=str(prize_id)))
    return markup

# Обработчик команды "/старт"
@bot.message_handler(commands=['старт'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username or '')
        bot.reply_to(
            message,
            (
                "Привет! Добро пожаловать!\n"
                "Тебя успешно зарегистрировали.\n"
                "Каждый час ты будешь получать новые картинки — попробуй первым нажать на кнопку 'Получить!'\n"
                "Только первые три пользователя получат настоящий приз!"
            )
        )

# Обработчик команды "/рейтинг"
@bot.message_handler(commands=['рейтинг'])
def handle_rating(message):
    rating = manager.get_rating()
    if not rating:
        bot.send_message(message.chat.id, "Рейтинг пока пуст.")
        return
    text = "Топ 10 пользователей по количеству призов:\n"
    for i, (user_name, count) in enumerate(rating, start=1):
        text += f"{i}. {user_name} — {count}\n"
    bot.send_message(message.chat.id, text)

# Обработчик нажатия на кнопку "Получить!"
@bot.callback_query_handler(func=lambda call: call.data and call.data.isdigit())
def handle_prize_callback(call):
    prize_id = int(call.data)
    user_id = call.from_user.id
    # Сколько уже получили этот приз
    count = manager.get_winners_count(prize_id)
    if count < 3:
        # Отправляем оригинальное изображение
        img = manager.get_prize_img(prize_id)
        if img:
            with open(os.path.join('img', img), 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo)
            # Записываем победителя в таблицу winners
            conn = sqlite3.connect(manager.database)
            with conn:
                conn.execute(
                    'INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, datetime("now"))',
                    (user_id, prize_id)
                )
            bot.answer_callback_query(call.id, "Поздравляем! Вы выиграли приз.")
        else:
            bot.answer_callback_query(call.id, "Ошибка: изображение не найдено.")
    else:
        # Для тех, кто слишком медлил
        bot.answer_callback_query(call.id, "К сожалению, вы не успели получить приз.")

# Функция рассылки новой пикселизированной картинки
def send_message():
    prize = manager.get_random_prize()
    if prize is None:
        print("Нет доступных призов")
        return
    prize_id, img = prize
    manager.mark_prize_used(prize_id)
    try:
        hide_img(img)
    except FileNotFoundError as e:
        print(e)
        return
    hidden = os.path.join('hidden_img', img)
    for uid in manager.get_users():
        if os.path.isfile(hidden):
            with open(hidden, 'rb') as photo:
                bot.send_photo(uid, photo, reply_markup=gen_markup(prize_id))
        else:
            print(f"Не найден файл для рассылки: {hidden}")

# Поток для планировщика
def schedule_thread():
    schedule.every().hour.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=lambda: bot.polling(none_stop=True), daemon=True).start()
    threading.Thread(target=schedule_thread, daemon=True).start()
    while True:
        time.sleep(10)
