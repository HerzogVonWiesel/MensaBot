# Requires telegram and python-telegram-bot
# pip install "python-telegram-bot[job-queue]"
import telegram
from telegram.ext import Application, CommandHandler, ContextTypes, Defaults
import datetime
import time
import pytz
import asyncio
import os
import yaml
import logging

import requests
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

logging.basicConfig(
    filename='mensabot.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    datefmt='%Y-%m-%d %H:%M:%S')  # Date format

DEBUG_MODE = 0

try:
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    chat_id_debug = config['chat_id_debug']

    if DEBUG_MODE == 1:
        chat_id = chat_id_debug

except Exception as e:
    logging.critical("An exception occurred: " + str(e))

async def sendMensapoll(context: ContextTypes.DEFAULT_TYPE, chat_id, poll_options, question="Mensa?"):
    await context.bot.send_poll(chat_id, question, poll_options,
                        is_anonymous=False, type='regular', allows_multiple_answers=True)

def buildMealsMessage(mealObjects):
    message = "--- TESTNACHRICHT ---\n\n" if DEBUG_MODE == 1 else ""
    for mealObject in mealObjects:
        message += mealObject['categoryName'] + " €" + "{:.2f}".format(mealObject['price']) + " " + mealObject['diet'] + "\n"
        message += mealObject['mealName'] + "\n\n"
    return message

async def buildMenuMessage(mensa, today = None):
    try:
        with open("mensen/" + mensa + ".json") as f:
            mensa_data = json.load(f)
        mensa_url = f"https://swp.webspeiseplan.de/index.php?token=55ed21609e26bbf68ba2b19390bf7961&model=menu&location={mensa_data['location']}&languagetype=1&_=1696321056188" # Please be a static token!
        json_pre = requests.get(mensa_url, headers={"Referer": "https://swp.webspeiseplan.de/Menu"}).text
        menu_json = json.loads(json_pre)
        menu = menu_json['content'][0]['speiseplanGerichtData']
        if today is None:
            today = time.strftime("%Y-%m-%d")
        mealObjects = []
        if DEBUG_MODE == 1:
            json.dump(menu, open('menu.json', 'w'))
        for meal in menu:
            mealObject = {}
            if meal['speiseplanAdvancedGericht']['datum'][:10] == today:
                meal_category = meal['speiseplanAdvancedGericht']['gerichtkategorieID']
                if meal_category in mensa_data['ignore'] or meal_category in [mensa_data['offsetGer'], mensa_data['offsetGer']+7, mensa_data['offsetGer']+8]: # ignore Salattheke & Desserts
                    continue
                elif meal_category == mensa_data['offsetGer']+5:
                    mealObject['categoryName'] = 'Aktionsessen'
                elif meal_category == mensa_data['offsetGer']+6:
                    mealObject['categoryName'] = 'Tagesangebot'
                else:
                    mealObject['categoryName'] = 'Angebot ' + str(meal_category - mensa_data['offsetNum'])
                mealObject['mealName'] = meal['speiseplanAdvancedGericht']['gerichtname'].replace("\n", " ")
                mealObject['diet'] = "🌱" if str(mensa_data['vegan']) in meal['gerichtmerkmaleIds'] else "🥛🥚" if str(mensa_data['vegan']-1) in meal['gerichtmerkmaleIds'] else ""
                mealObject['price'] = meal['zusatzinformationen']['mitarbeiterpreisDecimal2']
                mealObjects.append(mealObject)

        if len(mealObjects) == 0:
            return "Kein Menü verfügbar"
        return buildMealsMessage(mealObjects)
    except Exception as e:
        logging.warning("An exception occurred: " + str(e))
        return "Kein Menü verfügbar"

async def filmuni(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    message = await buildMenuMessage("Filmuni")
    await context.bot.send_message(chat_id=chat_id, text=message)
    # await sendMessage(chat_id, ["Ja", "Nein"], "Filmuni much?")

async def main(context: ContextTypes.DEFAULT_TYPE):
    menu_message = await buildMenuMessage("Griebnitzsee")
    for file in os.listdir('./chat_configs'):
        with open(f'./chat_configs/{file}', 'r') as f:
            data = json.load(f)
            if menu_message:
                await context.bot.send_message(data['chat_id'], menu_message)
            if data['send_poll']:
                await sendMensapoll(context, data['chat_id'], data['poll_options'])
    
async def main2(context: ContextTypes.DEFAULT_TYPE):
    print("WILDO")
    await context.bot.send_message(chat_id=chat_id_debug, text="Daily job is running")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    #build application and pass to bot token
    defaults = Defaults(tzinfo=pytz.timezone('Europe/Berlin'))
    application = (Application.builder()
                   .token(config['TOKEN'])
                   .defaults(defaults)
                   .build())
    if DEBUG_MODE == 1:
        application.job_queue.run_daily(main, time=datetime.time(hour=13, minute=58), days=(0, 1, 2, 3, 4, 5), chat_id=chat_id_debug)
    else:
        application.job_queue.run_daily(main, time=datetime.time(hour=9, minute=30), days=(1, 2, 3, 4, 5))
    application.add_handler(CommandHandler(["filmuni"], filmuni))
    application.run_polling(allowed_updates=telegram.Update.ALL_TYPES)