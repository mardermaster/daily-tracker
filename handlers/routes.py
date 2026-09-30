from aiogram import Router, F
from aiogram.dispatcher.event.handler import CallbackType
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, \
    InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram import Bot
import asyncio
import sqlite3
from aiogram.fsm.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import re

router = Router()
scheduler = AsyncIOScheduler()


# залить бота на сервер

def done_mark(daily_id, user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("UPDATE plans SET done=1 WHERE id=? AND user_id=?", (daily_id, user_id))
    conn.commit()
    conn.close()


def reset_done(user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("UPDATE plans SET done=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


async def summa(bot: Bot, user_id: int):
    reset = select_done(user_id)
    nolik = any(0 in tup for tup in reset)
    print(nolik)
    if nolik:
        await bot.send_message(user_id, 'Вы выполнили не все ежедневные задания на сегодня.🙁')
    reset_done(user_id)


def reset(bot: Bot, user_id: int):
    scheduler.add_job(
        summa,
        'cron',
        hour=18, minute=0,
        args=(bot, user_id))


async def wasted(bot: Bot, user_id: int, plan_id: int):
    await bot.send_message(user_id, 'Время на выполнение задачи на день вышло.🙁')
    delete_plan(plan_id, user_id)


def over(bot: Bot, user_id: int, plan_id: int, minutes=1440):
    time = minutes
    run = datetime.now() + timedelta(minutes=time)
    jobs_id = f'timer_{user_id}_{plan_id}'
    scheduler.add_job(
        wasted,
        trigger=DateTrigger(run_date=run),
        args=[bot, user_id, plan_id],
        id=jobs_id,
    )


def delete_plan(plan_id, user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM plans WHERE id=? AND user_id=?", (plan_id, user_id))
    conn.commit()
    conn.close()


def delete_daily(daily_id, user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM plans WHERE id=? AND user_id=?", (daily_id, user_id))
    conn.commit()
    conn.close()


async def reminder(bot: Bot, user_id: int):
    completed = select_done(user_id)
    nolik = any(0 in tup for tup in completed)
    print(nolik)
    if nolik:
        await bot.send_message(user_id, 'НАПОМИНАНИЕ: выполните ваши ежедневные задачи.')
    else:
        return


def timer(bot: Bot, user_id: int, interval_minutes: int = 1440):
    job_id = f'timer_{user_id}'
    scheduler.add_job(
        reminder,
        trigger=IntervalTrigger(minutes=interval_minutes),
        args=[bot, user_id],
        id=job_id,
        replace_existing=True
    )


# def reset_timer(user_id: int, interval_minutes: int=5):
#  job_id = f'timer_{user_id}'
#  if scheduler.get_job(job_id):
#    scheduler.reschedule_job(
#      job_id,
#      trigger=IntervalTrigger(minutes=interval_minutes)
#    )


# async def reminder_plan(bot: Bot, user_id: int):
#  prov = plan(user_id)
#  print('1')
#  if prov:
#    await bot.send_message(user_id, 'НАПОМИНАНИЕ: выполните ваши задачи на день.')
#  else:
#    return


# def plan_timer(bot: Bot, user_id: int, interval_minutes: int =  1):
#  job_id = f'timer_plan__{user_id}'
#  scheduler.add_job(
#    reminder_plan,
#    trigger=IntervalTrigger(minutes=interval_minutes),
#    args=[bot, user_id],
#    id=job_id,
#    replace_existing=True
#  )


class Form(StatesGroup):
    daytext = State()
    dailytext = State()


def init_db():
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan TEXT, daily TEXT, done INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()


def add_plan(user_id, plan):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO plans (user_id, plan) VALUES (?, ?)", (user_id, plan))
    conn.commit()
    conn.close()


def add_daily(user_id, daily):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO plans (user_id, daily) VALUES (?, ?)", (user_id, daily))
    conn.commit()
    conn.close()


def plan(user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("SELECT id, plan FROM plans WHERE user_id=? AND plan IS NOT NULL ORDER BY id", (user_id,))
    result = cur.fetchall()
    conn.close()
    return result


def select(plan):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("SELECT id FROM plans WHERE plan=?", (plan,))
    result = cur.fetchall()
    conn.close()
    return result


def daily_plans(user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("SELECT id, daily, done FROM plans WHERE user_id=? AND daily IS NOT NULL ORDER BY id", (user_id,))
    result = cur.fetchall()
    conn.close()
    return result


def select_done(user_id):
    conn = sqlite3.connect('plans.db')
    cur = conn.cursor()
    cur.execute("SELECT done FROM plans WHERE user_id=? AND daily IS NOT NULL ORDER BY id", (user_id,))
    result = cur.fetchall()
    conn.close()
    return result


def add():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Задачи')], [KeyboardButton(text='Помощь')],
        ],
        resize_keyboard=True
    )
    return keyboard


def inline(plans, daily):
    rows = []
    num = 1
    for plan_id, text in plans:
        rows.append([
            InlineKeyboardButton(text='✅', callback_data=f'done_plan_{plan_id}'),
            InlineKeyboardButton(text=f'{num}', callback_data=f'ignore{num}'),
            InlineKeyboardButton(text='❌', callback_data=f'del_plan_{plan_id}')
        ])
        num += 1
    for daily_id, text, done in daily:
        if done:
            rows.append([
                InlineKeyboardButton(text=f'{num}✅', callback_data=f'ignore{num}'),
                InlineKeyboardButton(text='❌', callback_data=f'del_daily_{daily_id}')
            ])
            num += 1


        else:
            rows.append([
                InlineKeyboardButton(text='✅', callback_data=f'done_daily_{daily_id}'),
                InlineKeyboardButton(text=f'{num}', callback_data=f'ignore{num}'),
                InlineKeyboardButton(text='❌', callback_data=f'del_daily_{daily_id}')
            ])
            num += 1

    rows.append([
        InlineKeyboardButton(text='Добавить задачу на день', callback_data='day')
    ])

    rows.append([
        InlineKeyboardButton(text='Добавить ежедневную задачу', callback_data='daily')
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def refresh_tasks(callback: CallbackQuery):
    user_id = callback.from_user.id
    planes = plan(user_id)
    dailies = daily_plans(user_id)
    if not planes and not dailies:
        await callback.message.edit_text('Активных задач нет.', reply_markup=inline(planes, dailies))
        return
    numb = 1
    text = 'ЗАДАЧИ:\n\n✅ - Выполнить.\n❌ - Удалить.\n\n'
    if planes:
        text += 'Сегодня:\n' + '\n'.join(f'{i}. {t}' for i, (_, t) in enumerate(planes, numb)) + '\n\n'
        numb += len(planes)
    if dailies:
        text += 'Ежедневные:\n' + '\n'.join(f'{i}. {t}' for i, (_, t, _) in enumerate(dailies, numb))
    await callback.message.edit_text(text, reply_markup=inline(planes, dailies))


@router.callback_query(F.data.startswith('ignore'))
async def ignore(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(lambda c: c.data == 'day')
async def day(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введите дело на сегодня.')
    await state.set_state(Form.daytext)


@router.message(Form.daytext, F.text)
async def ontext1(message: Message, state: FSMContext, bot: Bot):
    plan = message.text
    add_plan(message.from_user.id, plan)
    id = select(plan)
    real_id = id[0][0]
    over(bot, message.from_user.id, real_id, minutes=1440)
    await message.answer('Добавлено!')
    await state.clear()


@router.callback_query(lambda c: c.data == 'daily')
async def daily(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введите ежедневную задачу.')
    await state.set_state(Form.dailytext)


@router.message(Form.dailytext, F.text)
async def ontext2(message: Message, state: FSMContext, bot: Bot):
    daily = message.text
    add_daily(message.from_user.id, daily)
    timer(bot, message.from_user.id, interval_minutes=720)
    reset(bot, message.from_user.id)
    await message.answer('Добавлено!')
    await state.clear()


@router.callback_query(F.data.startswith('done_plan_'))
async def done_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split('_')[2])
    delete_plan(plan_id, callback.from_user.id)
    await callback.answer('Выполнено ✅')
    await refresh_tasks(callback)


@router.callback_query(F.data.startswith('del_plan_'))
async def del_plan(callback: CallbackQuery):
    plan_id = int(callback.data.split('_')[2])
    delete_plan(plan_id, callback.from_user.id)
    await callback.answer('Удалено ❌')
    await refresh_tasks(callback)


@router.callback_query(F.data.startswith('done_daily_'))
async def done_daily(callback: CallbackQuery):
    daily_id = int(callback.data.split('_')[2])
    done_mark(daily_id, callback.from_user.id)
    await callback.answer('Ежедневная задача выполнена ✅')
    await refresh_tasks(callback)


#  reset_timer(callback.from_user.id, interval_minutes=5)

@router.callback_query(F.data.startswith('del_daily_'))
async def del_daily(callback: CallbackQuery):
    daily_id = int(callback.data.split('_')[2])
    delete_daily(daily_id, callback.from_user.id)
    await callback.answer('Удалено ❌')
    await refresh_tasks(callback)


@router.message(Command('start'))
async def start(message: Message):
    await message.answer(
        'Это бот для более удобной распланировки ваших дел на сегодняшний день и для отметки выполнения ежедневных задач.',
        reply_markup=add())


@router.message(F.text.lower() == 'помощь')
async def help(message: Message):
    await message.answer(
        'С помощью этого бота вы можете запланировать какое-нибудь дело и назначить себе срок на его выполнение(например: "Убраться в комнате, осталось: 1 день").\nЛибо вы можете назначить какую-нибудь задачу, которую будете выполнять ежедневно(например: "Сделать 120 отжиманий").\n\nНажмите "Задачи", чтобы добавить задачу или просмотреть активные задачи')


@router.message(F.text.lower() == 'задачи')
async def zadachs(message: Message):
    user_id = message.from_user.id
    planes = plan(user_id)
    dailies = daily_plans(user_id)
    if not planes and not dailies:
        await message.answer('Активных задач нет.', reply_markup=inline(planes, dailies))
        return
    numb = 1
    text = 'ЗАДАЧИ:\n\n✅ - Выполнить.\n❌ - Удалить.\n\n'
    if planes:
        text += 'Сегодня:\n' + '\n'.join(f'{i}. {t}' for i, (_, t) in enumerate(planes, numb)) + '\n\n'
        numb += len(planes)
    if dailies:
        text += 'Ежедневные:\n' + '\n'.join(f'{i}. {t}' for i, (_, t, _) in enumerate(dailies, numb))
    await message.answer(text, reply_markup=inline(planes, dailies))
