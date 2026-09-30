from os import getenv
from aiogram import Bot, Dispatcher
import asyncio
from handlers.routes import router, init_db, scheduler

TOKEN = getenv('BOT_TOKEN')
dp = Dispatcher()
dp.include_router(router)
async def main():
  bot = Bot(token = TOKEN)
  print('start...')
  scheduler.start()
  await dp.start_polling(bot)
if __name__ == '__main__':
  init_db()
  asyncio.run(main())