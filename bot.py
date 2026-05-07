import os
import json
import telebot
import gspread
import google.generativeai as genai
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Configuración de llaves desde Variables de Entorno (GitHub/Railway)
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SHEET_NAME = os.getenv("SPREADSHEET_NAME")
MY_ID = int(os.getenv("MY_ID"))
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# Configuración de Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Inicializar Telegram
bot = telebot.TeleBot(TOKEN)

def extract_expense(text):
    prompt = f"""
    Sos un extractor de datos financieros. Extrae el gasto del siguiente mensaje y devolvé exclusivamente un JSON.
    Categorías: Comida, Transporte, Servicios, Salud, Inversiones, Ocio, Otros.
    Mensaje: "{text}"
    Formato: {{"fecha": "DD/MM/AAAA", "monto": numero, "categoria": "Texto", "descripcion": "Texto"}}
    """
    response = model.generate_content(prompt)
    # Limpieza de formato markdown si Gemini lo incluye
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

@bot.message_handler(func=lambda m: m.from_user.id == MY_ID)
def handle_message(message):
    try:
        data = extract_expense(message.text)
        # Escribir en Google Sheets: [Fecha, Monto, Categoría, Descripción]
        sheet.append_row([data['fecha'], data['monto'], data['categoria'], data['descripcion']])
        bot.reply_to(message, f"✅ Registrado: ${data['monto']} en {data['categoria']} ({data['descripcion']})")
    except Exception as e:
        bot.reply_to(message, f"❌ Error al procesar: {e}")

print("Bot en línea...")
bot.infinity_polling()
