# Requires telegram and python-telegram-bot
import telegram
import time
import asyncio
import os
import yaml

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

with open('config.yaml') as f:
    config = yaml.safe_load(f)

DEBUG_MODE = 1
TIME_TO_SEND = 10

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
    message = mealObject['categoryName'] + " €" + mealObject['price'] + " " + mealObject['diet'] + "\n"
    message += mealObject['mealName']
    return message

def buildMealsMessage(mealObjects):
    message = "--- TESTNACHRICHT ---\n\n" if DEBUG_MODE == 1 else ""
    for mealObject in mealObjects:
        message += buildMealMessage(mealObject) + "\n\n"
    return message

async def buildMenuMessage(day, month):
    try:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument("window-size=1100,600")

        profile_path = (r"./MENSABOT_PROFILE")
        options.add_argument("-profile")
        options.add_argument(profile_path)

        service = webdriver.FirefoxService(executable_path=r'./geckodriver')
        driver = webdriver.Firefox(options=options, service=service)
        
        driver.set_window_size(1100, 600)
        driver.get('https://swp.webspeiseplan.de/Menu')
        time.sleep(20)
        source = driver.page_source
        soup = BeautifulSoup(source, 'html.parser')
        meals = soup.find_all(class_="meal-wrapper")
        mealObjects = []
        for meal in meals:
            # print(meal.prettify())
            mealObject = {}
            mealObject['categoryName'] = meal.find(class_="categoryName").get_text()
            if mealObject['categoryName'] == "Salattheke":
                continue
            mealObject['mealName'] = meal.find(class_="mealNameWrapper").get_text().replace("\n", " ")
            mealObject['diet'] = "🌱" if meal.find(class_="feature-69") is not None else "🥛🥚" if meal.find(class_="feature-68") else ""
            mealObject['price'] = meal.find(class_="price-value").get_text().replace(" €", "")
            mealObjects.append(mealObject)

        message = buildMealsMessage(mealObjects)
        driver.quit()
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