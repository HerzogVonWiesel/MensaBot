# Requires telegram and python-telegram-bot
# Set a cronjob as the following:
# 0 10 * * 1-5 /usr/bin/python /path/to/mensabot.py
# pip install "python-telegram-bot[job-queue]"
import telegram
import time
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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    datefmt='%Y-%m-%d %H:%M:%S')  # Date format

DEBUG_MODE = 1

MENSA_URL = "https://swp.webspeiseplan.de/index.php?token=55ed21609e26bbf68ba2b19390bf7961&model=menu&location=9601&languagetype=1&_=1696321056188" # Please be a static token!

try:
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    bot = telegram.Bot(token=config['TOKEN'])
    chat_id_debug = config['chat_id_debug']

    if DEBUG_MODE == 1:
        chat_id = chat_id_debug

except Exception as e:
    logging.critical("An exception occurred: " + str(e))

async def sendMensapoll(chat_id, poll_options, question="Mensa?"):
    await bot.send_poll(chat_id, question, poll_options,
                        is_anonymous=False, type='regular', allows_multiple_answers=True)

async def sendMessage(chat_id, message):
    await bot.send_message(chat_id, message)

def buildMealMessage(mealObject):
    message = mealObject['categoryName'] + " €" + "{:.2f}".format(mealObject['price']) + " " + mealObject['diet'] + "\n"
    message += mealObject['mealName']
    return message

def buildMealsMessage(mealObjects):
    message = "--- TESTNACHRICHT ---\n\n" if DEBUG_MODE == 1 else ""
    for mealObject in mealObjects:
        message += buildMealMessage(mealObject) + "\n\n"
    return message

async def buildMenuMessage(today = None):
    try:
        json_pre = requests.get(MENSA_URL, headers={"Referer": "https://swp.webspeiseplan.de/Menu"}).text
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
                if meal_category in [112, 119, 120]: # ignore Salattheke & Desserts
                    continue
                elif meal_category == 117:
                    mealObject['categoryName'] = 'Aktionsessen'
                elif meal_category == 118:
                    mealObject['categoryName'] = 'Tagesangebot'
                else:
                    mealObject['categoryName'] = 'Angebot ' + str(meal_category - 148)
                mealObject['mealName'] = meal['speiseplanAdvancedGericht']['gerichtname'].replace("\n", " ")
                mealObject['diet'] = "🌱" if '69' in meal['gerichtmerkmaleIds'] else "🥛🥚" if '68' in meal['gerichtmerkmaleIds'] else ""
                mealObject['price'] = meal['zusatzinformationen']['mitarbeiterpreisDecimal2']
                mealObjects.append(mealObject)

        message = buildMealsMessage(mealObjects)
        return message
    except Exception as e:
        logging.warning("An exception occurred: " + str(e))
        return None


async def main():
    menu_message = await buildMenuMessage()
    for file in os.listdir('./chat_configs'):
        with open(f'./chat_configs/{file}', 'r') as f:
            data = json.load(f)
            chat_id = data['chat_id']
            send_poll = data['send_poll']
            poll_options = data['poll_options']
            if menu_message:
                await sendMessage(chat_id, menu_message)
            if send_poll:
                await sendMensapoll(chat_id, poll_options)
    
async def main2():
    menu_message = await buildMenuMessage("2024-07-26")
    for file in os.listdir('./chat_configs'):
        with open(f'./chat_configs/{file}', 'r') as f:
            data = json.load(f)
            chat_id = data['chat_id']
            send_poll = data['send_poll']
            poll_options = data['poll_options']
            if menu_message:
                await sendMessage(chat_id, menu_message)
            if send_poll:
                await sendMensapoll(chat_id, poll_options)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    if DEBUG_MODE == 1:
        logging.warning("DEBUG MODE")
        loop.run_until_complete(main2())
    else:
        loop.run_until_complete(main())