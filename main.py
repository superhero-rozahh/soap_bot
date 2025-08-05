from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import psycopg2
import os
import datetime

load_dotenv()
app = Flask(__name__)

# Подключение к базе данных
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
except Exception as e:
    print(f"❌ Ошибка подключения к базе: {e}")
    exit(1)

# Состояние пользователей
user_state = {}

@app.route("/", methods=["GET"])
def health():
    return "✅ App is running!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    from_number = request.form.get("From")
    user_msg = request.form.get("Body", "").strip()

    print(f"[{datetime.datetime.now()}] From: {from_number}, Msg: {user_msg}")

    state = user_state.get(from_number, {"step": "меню"})
    resp = MessagingResponse()
    msg = resp.message()

    # Команда сброса
    if user_msg.lower() in ("привет", "меню", "здравствуйте"):
        state = {"step": "меню"}
        msg.body(
            "👋 Привет! Добро пожаловать в наш WhatsApp-магазин мыла-пенки!\n\n"
            "🌿 Натуральный состав, нежная пена и забота о себе каждый день.\n\n"
            "Что хотите сделать?\n"
            "1️⃣ Заказать мыло\n"
            "2️⃣ Узнать подробнее\n\n"
            "Введите 1 или 2:"
        )
        user_state[from_number] = state
        return str(resp)

    # Главное меню
    if state["step"] == "меню":
        if user_msg == "1":
            state["step"] = "ask_quantity"
            msg.body("🧼 Сколько штук мыла вы хотите заказать?")
        elif user_msg == "2":
            msg.body(
                "🧴 *О продукте*\n"
                "• Мыло-пенка для интимной гигиены.\n"
                "• Подходит для чувствительной кожи.\n"
                "• Без спирта и отдушек.\n"
                "• Объём: 30 мл с помпой.\n"
                "• Цена: 1800₸ за штуку.\n\n"
                "Напишите *меню*, чтобы вернуться."
            )
        else:
            msg.body("❗ Введите 1 чтобы заказать или 2 чтобы узнать подробнее.")
        user_state[from_number] = state
        return str(resp)

    # Шаг 1 — количество
    if state["step"] == "ask_quantity":
        if user_msg.isdigit():
            quantity = int(user_msg)
            price = quantity * 1800
            state.update({
                "quantity": quantity,
                "price": price,
                "step": "ask_name"
            })
            msg.body(f"🔢 {quantity} штук будет стоить {price}₸.\n\nУкажите ваше имя:")
        else:
            msg.body("❗ Пожалуйста, введите число.")
        user_state[from_number] = state
        return str(resp)

    # Шаг 2 — имя
    if state["step"] == "ask_name":
        name = user_msg.strip().title()
        state.update({
            "name": name,
            "step": "ask_address"
        })
        msg.body(f"Спасибо, {name}!\nТеперь укажите адрес доставки:")
        user_state[from_number] = state
        return str(resp)

    # Шаг 3 — адрес
    if state["step"] == "ask_address":
        address = user_msg.strip()
        state.update({
            "address": address,
            "step": "ask_phone"
        })
        msg.body("📞 Введите номер телефона:")
        user_state[from_number] = state
        return str(resp)

    # Шаг 4 — телефон и финализация
    if state["step"] == "ask_phone":
        phone = user_msg.strip()
        name = state["name"]
        quantity = state["quantity"]
        price = state["price"]
        address = state["address"]

        try:
            cursor.execute(
                "INSERT INTO orders (name, quantity, price, address, phone) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (name, quantity, price, address, phone)
            )
            order_id = cursor.fetchone()[0]
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка записи в БД: {e}")
            msg.body("❗ Ошибка при сохранении заказа. Попробуйте позже.")
            return str(resp)

        msg.body(
            f"✅ Ваш заказ №{order_id} принят!\n\n"
            f"Имя: {name}\n"
            f"Кол-во: {quantity} шт\n"
            f"Сумма: {price}₸\n"
            f"Адрес: {address}\n"
            f"Телефон: {phone}\n\n"
            "Мы свяжемся с вами для подтверждения. Спасибо! 💚"
        )

        user_state.pop(from_number)
        return str(resp)

    # Запасной путь
    msg.body("❗ Не удалось обработать сообщение. Напишите 'меню' чтобы начать заново.")
    return str(resp)

# Запуск сервера
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
