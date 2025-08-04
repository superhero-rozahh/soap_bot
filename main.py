from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import psycopg2
import os
import datetime

load_dotenv()

app = Flask(__name__)

# PostgreSQL connection
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

# In-memory user session state
user_state = {}

@app.route("/", methods=["GET"])
def health():
    return "✅ App is running!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    from_number = request.form.get("From")
    user_msg = request.form.get("Body").strip()

    print(f"[{datetime.datetime.now()}] From: {from_number}, Msg: {user_msg}")

    state = user_state.get(from_number, {"step": "меню"})
    print(f"[{datetime.datetime.now()}] State Step: {state.get('step')}")

    resp = MessagingResponse()
    msg = resp.message()

    if user_msg.lower() in ("привет", "меню", "здравствуйте"):
        state = {"step": "меню"}
        msg.body(
            "👋 Привет! Добро пожаловать в наш WhatsApp-магазин мыла-пенки!\n\n"
            "🌿 Нежная пена, натуральный состав и удобный флакон — всё, что нужно для заботы о себе.\n\n"
            "Что хотите сделать?\n\n"
            "1️⃣ Заказать мыло\n"
            "2️⃣ Узнать подробнее\n\n"
            "Введите 1 или 2:"
        )
        user_state[from_number] = state
        return str(resp)

    if state["step"] == "меню":
        if user_msg == "1":
            state["step"] = "ask_quantity"
            msg.body("Отлично! 🧼 Сколько штук мыла вы хотите заказать?")
        elif user_msg == "2":
            msg.body(
                "ℹ️ Наша мыло-пенка:\n\n"
                "- Подходит для всех типов кожи\n"
                "- Без сульфатов и парабенов\n"
                "- Объём: 150 мл\n"
                "- Цена: 1800₸ за 1 штуку\n\n"
                "Напишите 'меню', чтобы вернуться назад."
            )
        else:
            msg.body("❗ Введите 1 чтобы заказать или 2 чтобы узнать подробнее.")
        user_state[from_number] = state
        return str(resp)

    if state["step"] == "ask_quantity":
        if user_msg.isdigit():
            quantity = int(user_msg)
            price = quantity * 1800
            state.update({
                "quantity": quantity,
                "price": price,
                "step": "ask_name"
            })
            msg.body(f"Хорошо, {quantity} штук будет стоить {price}₸.\n\n2️⃣ Укажите, пожалуйста, ваше имя:")
        else:
            msg.body("❗ Пожалуйста, введите число.")
        user_state[from_number] = state
        return str(resp)

    if state["step"] == "ask_name":
        name = user_msg.strip().title()
        state.update({
            "name": name,
            "step": "ask_address"
        })
        msg.body(f"Спасибо, {name}!\n\n3️⃣ Укажите, пожалуйста, адрес доставки:")
        user_state[from_number] = state
        return str(resp)

    if state["step"] == "ask_address":
        address = user_msg.strip()
        state.update({
            "address": address,
            "step": "ask_phone"
        })
        msg.body("4️⃣ Укажите, пожалуйста, ваш номер телефона:")
        user_state[from_number] = state
        return str(resp)

    if state["step"] == "ask_phone":
        phone = user_msg.strip()
        name = state["name"]
        quantity = state["quantity"]
        price = state["price"]
        address = state["address"]

        cursor.execute(
            "INSERT INTO orders (name, quantity, price, address, phone) VALUES (%s, %s, %s, %s, %s)",
            (name, quantity, price, address, phone)
        )
        conn.commit()

        msg.body(
            f"✅ Всё готово! Заказ принят:\n\n"
            f"Имя: {name}\n"
            f"Количество: {quantity}\n"
            f"Сумма: {price}₸\n"
            f"Адрес: {address}\n"
            f"Телефон: {phone}\n\n"
            f"Мы свяжемся с вами для подтверждения. Спасибо за заказ! 💚\n"
            f"Напишите 'меню' чтобы начать сначала"
        )

        user_state.pop(from_number)
        return str(resp)

    msg.body("😕 Я вас не понял. Напишите 'меню' чтобы начать сначала.")
    return str(resp)

# ✅ START SERVER (Only once)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

