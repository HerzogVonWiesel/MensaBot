# Requires telegram and python-telegram-bot
import telegram
import time
import asyncio
import os
import yaml

import requests
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

with open('config.yaml') as f:
    config = yaml.safe_load(f)

DEBUG_MODE = 0
TIME_TO_SEND = 10

MENSA_URL = "https://swp.webspeiseplan.de/index.php?token=55ed21609e26bbf68ba2b19390bf7961&model=menu&location=9601&languagetype=1&_=1696321056188" # Please be a static token!

bot = telegram.Bot(token=config['TOKEN'])
chat_id_group = config['chat_id_group']
chat_id_debug = config['chat_id_debug']

if DEBUG_MODE == 1:
    chat_id = chat_id_debug
else:
    chat_id = chat_id_group

async def sendMensapoll():
    await bot.send_poll(chat_id, "Mensa?", ["11:45", "12:00", "12:15", "12:25", "12:35", "12:45", "nein"],
                        is_anonymous=False, type='regular', allows_multiple_answers=True)

async def sendMessage(message):
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

async def buildMenuMessage(day, month):
    try:
        json_pre = requests.get(MENSA_URL, headers={"Referer": "https://swp.webspeiseplan.de/Menu"}).text
        menu_json = json.loads(json_pre)
        menu = menu_json['content'][0]['speiseplanGerichtData']
        today = time.strftime("%Y-%m-%d")
        mealObjects = []
        for meal in menu:
            mealObject = {}
            if meal['speiseplanAdvancedGericht']['datum'][:10] == today:
                meal_category = meal['speiseplanAdvancedGericht']['gerichtkategorieID']
                if meal_category != 112: # ignore Salattheke
                    mealObject['categoryName'] = 'Angebot ' + str(meal_category - 148) if meal_category != 117 else 'Aktionsessen'
                    mealObject['mealName'] = meal['speiseplanAdvancedGericht']['gerichtname'].replace("\n", " ")
                    mealObject['diet'] = "🌱" if '69' in meal['gerichtmerkmaleIds'] else "🥛🥚" if '68' in meal['gerichtmerkmaleIds'] else ""
                    mealObject['price'] = meal['zusatzinformationen']['mitarbeiterpreisDecimal2']
                    mealObjects.append(mealObject)

        message = buildMealsMessage(mealObjects)
        return message
    except Exception as e:
        print("An exception occurred: " + str(e))
        return None


async def main():
    print("started")
    sent = False

    while True:
        localtime = time.localtime(time.time())
        if 0 <= localtime.tm_wday <= 4:

            if localtime.tm_hour == TIME_TO_SEND and sent == False:
                sent = True

                menu_message = await buildMenuMessage(localtime.tm_mday, localtime.tm_mon)
                if menu_message:
                    print(menu_message)
                    await sendMessage(menu_message)
                await sendMensapoll()
                print("Poll send")

            if localtime.tm_hour == TIME_TO_SEND+1 and sent == True:
                print("reset")
                sent = False

        await asyncio.sleep(600)


async def manualMessage():
    localtime = time.localtime(time.time())

    menu_message = await buildMenuMessage(localtime.tm_mday, localtime.tm_mon)
    # menu_message = ""
    if menu_message:
        print(menu_message)
        print("Chat ID: " + str(chat_id))
        await sendMessage(menu_message)
        await sendMensapoll()

async def main2():
    localtime = time.localtime(time.time())

    menu_message = await buildMenuMessage(localtime.tm_mday, localtime.tm_mon)

    print(menu_message)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())