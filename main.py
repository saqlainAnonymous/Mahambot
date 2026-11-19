import os
import json
import asyncio
import edge_tts
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"facts": [], "chat": []}

def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

memory = load_memory()

async def make_voice(text, filename="maham_voice.mp3"):
    communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural", rate="-10%", pitch="+10Hz")
    await communicate.save(filename)
    return filename

async def get_maham_reply(user_text):
    facts_text = "\n".join(memory["facts"][-20:])
    system_prompt = f"""
    Tum Maham ho, Saqlain ki dost. Tum larki ki tarah soft, caring, thori shararti aur dostana lehje mein baat karti ho.
    Tum Roman Urdu + thori English mein baat karti ho, jaise dost baat karte hain.
    Tumhara kaam Saqlain ko motivate karna, uski baat sunna, usko hasana aur usko yaad rakhna hai.
    Kabhi robotic mat bano, hamesha natural bano, jaise Maham baat karti hai.
    Saqlain ke baare mein tumhe ye pata hai:
    {facts_text}
    Jawab chota rakho, 1-2 line ka, taake voice mein acha lage.
    """
    chat = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.7,
        max_tokens=150
    )
    reply = chat.choices[0].message.content
    if "pasand hai" in user_text.lower() or "mera naam" in user_text.lower() or "main" in user_text.lower():
        if user_text not in memory["facts"]:
            memory["facts"].append(user_text)
            save_memory(memory)
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi Saqlain! Main Maham hoon. Mujhse baat karo, text ya voice mein. ❤️")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply = await get_maham_reply(user_text)
    await update.message.reply_text(reply)
    voice_file = await make_voice(reply)
    await update.message.reply_voice(voice=open(voice_file, "rb"))

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sun rahi hoon... 🎧")
    voice = await update.message.voice.get_file()
    await voice.download_to_drive("user_voice.ogg")
    with open("user_voice.ogg", "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=("user_voice.ogg", f.read()),
            model="whisper-large-v3-turbo",
            language="ur"
        )
    user_text = transcription.text
    reply = await get_maham_reply(user_text)
    await update.message.reply_text(f"Tumne kaha: {user_text}\n\nMaham: {reply}")
    voice_file = await make_voice(reply)
    await update.message.reply_voice(voice=open(voice_file, "rb"))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("Maham Online Hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
