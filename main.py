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

    # Reset command
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
            "🧴 *О продукте*\n"
            "• Это мыло-пенка для интимного ухода, предназначенная для деликатной очистки интимных зон.\n"
            "• Подходит для чувствительной кожи и не вызывает раздражения.\n"
            "• Мягкая нежная пена, которая не пересушивает кожу.\n"
            "• Без спирта и отдушек – гипоаллергенная формула.\n\n"
        
            "*Преимущества*\n"
            "• Гипоаллергенность – безопасно для ежедневного применения.\n"
            "• Компактный формат – удобно брать с собой.\n"
            "• Поддерживает естественный баланс кожи.\n\n"
        
            "*Состав:*\n"
            "Вода, Теа-Лаурил сульфат, Метилхлороизотиазолинон, Метилизотиазолинон,\n"
            "Хлорид магния, Нитрат магния, Глицерин, Кокамидопропил бетаин, Хлорид натрия,\n"
            "Пропиленгликоль, Лаурил сульфат натрия, Сульфат натрия, Спирты C12-16,\n"
            "Лауроилсаркозинат натрия, Феноксиэтанол, Бензоат натрия и др.\n\n"
        
            "*Назначение:*\n"
            "Для ежедневной гигиены интимной зоны. Подходит для всех типов кожи.\n\n"
        
            "*Рекомендации:*\n"
            "Использовать утром и вечером во время душа.\n\n"
        
            "*Инструкция:*\n"
            "1. Встряхните бутылочку.\n"
            "2. Нанесите пену на ладонь.\n"
            "3. Аккуратно нанесите на интимную зону.\n"
            "4. Смойте тёплой водой.\n"
            "5. Промокните кожу полотенцем.\n\n"
        
            "*Противопоказания:*\n"
            "Индивидуальная непереносимость. При раздражении прекратить использование.\n\n"
        
            "*Предупреждения:*\n"
            "Только для наружного применения. Избегать попадания в глаза.\n\n"
        
            "*Форма выпуска:*\n"
            "Флакон 30 мл с помпой. Подходит для переработки.\n\n"
        
            "*Производитель:*\n"
            "ИП “DarAi Trade”, ИИН 900520401139\n"
            "ул. Акатаева 75/2, г. Алматы, Казахстан\n"
            "Email: info@daraitrade.com\n\n"
        
            "Напишите *меню*, чтобы вернуться назад."
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

        # Insert into DB and return the order ID
        cursor.execute(
            "INSERT INTO orders (name, quantity, price, address, phone) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (name, quantity, price, address, phone)
        )
        order_id = cursor.fetchone()[0]
        conn.commit()

        msg.body(
            f"✅ Всё готово! Ваш заказ №{order_id} принят:\n\n"
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

    # Fallback if input unrecognized
    msg.body("😕 Я вас не понял. Напишите 'меню' чтобы начать сначала.")
    return str(resp)

# ✅ Start server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


