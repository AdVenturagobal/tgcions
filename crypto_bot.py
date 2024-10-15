import logging
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import time

# 使用 CoinGecko API 获取加密货币数据
COINS = ['bitcoin', 'ethereum', 'ripple', 'litecoin', 'cardano', 'polkadot', 'solana', 'binancecoin', 'dogecoin', 'polygon']
API_URL = 'https://api.coingecko.com/api/v3/simple/price'

# 获取图表的 CoinGecko 页面
def get_chart_url(coin):
    return f"https://www.coingecko.com/en/coins/{coin}"

# 读取配置文件
def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

config = load_config()
TOKEN = config["token"]
CHAT_ID = config["chat_id"]

# 初始化日志记录
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取加密货币价格、涨幅和成交量数据
async def get_crypto_data(coin):
    try:
        response = requests.get(f'{API_URL}?ids={coin}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true')
        data = response.json()
        price = data[coin]['usd']
        change = data[coin]['usd_24h_change']
        volume = data[coin]['usd_24h_vol']
        return price, change, volume
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None, None, None

# 获取图表截图并保存为文件
def get_chart_screenshot(coin):
    url = get_chart_url(coin)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(5)  # 等待页面加载

    # 截图并保存为文件
    file_path = f"{coin}_chart.png"
    driver.save_screenshot(file_path)
    driver.quit()
    return file_path

# 格式化加密货币信息，并发送图表图片
async def format_crypto_info(coin, context):
    price, change, volume = await get_crypto_data(coin)
    if price is not None:
        message = (f"💰 {coin.capitalize()} (USD)\n"
                   f"Price: ${price:.2f}\n"
                   f"24hr Change: {change:.2f}%\n"
                   f"24hr Volume: ${volume:.2f}")

        # 获取并发送图表图片
        chart_file = get_chart_screenshot(coin)
        await context.bot.send_photo(chat_id=CHAT_ID, photo=open(chart_file, 'rb'), caption=message)
    else:
        await context.bot.send_message(chat_id=CHAT_ID, text=f"Failed to fetch data for {coin.capitalize()}.")

# 显示前三个币种数据的函数
async def show_top_three(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_three_coins = COINS[:3]  # 选择前三个币种
    for coin in top_three_coins:
        await format_crypto_info(coin, context)

# 启动机器人命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("查看前3个币种数据", callback_data='show_top_three')],
        [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
        [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
        [InlineKeyboardButton("Ripple", callback_data='ripple')],
        [InlineKeyboardButton("Litecoin", callback_data='litecoin')],
        [InlineKeyboardButton("Cardano", callback_data='cardano')],
        [InlineKeyboardButton("Polkadot", callback_data='polkadot')],
        [InlineKeyboardButton("Solana", callback_data='solana')],
        [InlineKeyboardButton("Binance Coin", callback_data='binancecoin')],
        [InlineKeyboardButton("Dogecoin", callback_data='dogecoin')],
        [InlineKeyboardButton("Polygon", callback_data='polygon')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose a cryptocurrency:', reply_markup=reply_markup)

# 处理用户选择的币种
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'show_top_three':
        # 显示前三个币种数据
        await show_top_three(update, context)
    else:
        # 处理单个币种的展示
        coin = query.data
        await query.answer()
        await format_crypto_info(coin, context)

# 定时任务：发送10个主流币种的价格和图表截图
async def scheduled_task(context: ContextTypes.DEFAULT_TYPE):
    coins_to_send = COINS  # 发送10个主流币种
    for coin in coins_to_send:
        await format_crypto_info(coin, context)

# 设置每天定时任务，在 +8 时区的8:00, 16:00和00:00发送消息
def set_daily_schedule(application):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Shanghai"))  # +8 时区
    # 添加每天的 8:00, 16:00, 00:00 定时任务
    scheduler.add_job(lambda: application.create_task(scheduled_task(application)), CronTrigger(hour=8, minute=0))
    scheduler.add_job(lambda: application.create_task(scheduled_task(application)), CronTrigger(hour=16, minute=0))
    scheduler.add_job(lambda: application.create_task(scheduled_task(application)), CronTrigger(hour=0, minute=0))
    scheduler.start()

# 主函数改为同步函数
def main():
    # 创建应用程序
    application = Application.builder().token(TOKEN).build()

    # 注册命令处理器
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))

    # 启动定时任务
    set_daily_schedule(application)

    # 运行应用程序并开始轮询
    application.run_polling()

if __name__ == '__main__':
    main()
