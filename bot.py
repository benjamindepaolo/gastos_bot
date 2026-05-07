import os
import json
import telebot
import gspread
import google.generativeai as genai
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# --- MINI SERVIDOR PARA MANTENERLO VIVO EN LA NUBE ---
app = Flask('')
@app.route('/')
def home():
    return "Bot de Gastos Online"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ----------------------------------------------------

# Configuración
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SHEET_NAME = os.getenv("SPREADSHEET_NAME")
MY_ID = int(os.getenv("MY_ID"))
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: m.from_user.id == MY_ID)
def handle(m):
    try:
        prompt = f"Extrae el gasto en JSON: {{'fecha': 'DD/MM', 'monto': 0, 'categoria': 'Otros', 'descripcion': ''}}. Texto: {m.text}"
        res = model.generate_content(prompt)
        data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
        
        sheet.append_row([data['fecha'], data['monto'], data['categoria'], data['descripcion']])
        bot.reply_to(m, f"✅ Registrado: ${data['monto']} en {data['categoria']}")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

if __name__ == "__main__":
    keep_alive() # Inicia el mini servidor web
    print("Bot iniciado...")
    bot.infinity_polling()
