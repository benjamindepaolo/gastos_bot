import os
import json
import telebot
import gspread
import google.generativeai as genai
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

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
sheet = client.open(SHEET_NAME).worksheet("Track")

# Gemini
genai.configure(api_key=GEMINI_KEY)

# --- BUSCADOR AUTOMÁTICO DE MODELOS ---
# Esto evita el error 404. Le pregunta a tu API Key qué modelos tenés permitidos
# y selecciona el primero que sirva para analizar texto.
modelo_elegido = None
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        modelo_elegido = m.name
        # Si encontramos uno de la familia "flash" (más rápido), nos quedamos con ese
        if 'flash' in m.name.lower():
            break

# Si por alguna razón falla la búsqueda, intenta con uno genérico
if not modelo_elegido:
    modelo_elegido = 'gemini-1.5-flash'

model = genai.GenerativeModel(modelo_elegido)
# --------------------------------------

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: m.from_user.id == MY_ID)
def handle(m):
    try:
        # Captura la fecha de Telegram y la ajusta a hora local (UTC -3)
        fecha_hora_utc = datetime.utcfromtimestamp(m.date)
        fecha_local = fecha_hora_utc - timedelta(hours=3)
        fecha_exacta = fecha_local.strftime("%d/%m %H:%M")

        # Le pedimos a Gemini solo los datos financieros (sacamos la fecha del prompt)
        prompt = f"Extrae el gasto en JSON: {{'monto': 0, 'categoria': 'Otros', 'descripcion': ''}}. Texto: {m.text}"
        res = model.generate_content(prompt)
        data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
        
        # Guardamos usando la fecha capturada de Telegram
        sheet.append_row([fecha_exacta, data['monto'], data['categoria'], data['descripcion']])
        bot.reply_to(m, f"✅ Registrado: ${data['monto']} en {data['categoria']}")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

if __name__ == "__main__":
    keep_alive() # Inicia el mini servidor web
    print(f"Bot iniciado usando el modelo: {modelo_elegido}")
    bot.infinity_polling()
