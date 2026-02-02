import asyncio
import os
import re
from datetime import datetime
from typing import List, Optional
import aiofiles
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ForceReply, ChatJoinRequest,
    ChatMemberUpdated
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import json

# Configuration
API_TOKEN = os.getenv("8449120211:AAFDvImeAPSO7ytlF6FPU22Ptyf52FiY0e8")  # Tokenni environment variable dan oling (Renderda qo'shasiz)
XASANOV_UZ = os.getenv("ADMIN_ID", "8362016991")  # Admin ID ni env dan, default qiymat bilan

# Set timezone
os.environ['TZ'] = 'Asia/Tashkent'

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# FSM States
class AdminStates(StatesGroup):
    add_admin = State()
    remove_admin = State()
    add_channel = State()
    add_public_channel = State()
    remove_channel = State()
    remove_public_channel = State()
    upload_movie = State()
    send_message = State()
    kino_channel = State()
    single_message_id = State()  # New state for single user ID
    single_message_content = State()  # New state for single message content
    delete_movie = State()  # New state for deleting movie
    add_comment = State()  # New state for adding comment to movie
    ban_user = State()
    unban_user = State()

class UserStates(StatesGroup):
    contact_admin = State()  # State for contacting admin


# Helper functions
def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = ["step", "admin", "kino", "tizim", "users"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def ensure_files():
    """Create necessary files if they don't exist"""
    files = {
        "admin/user.txt": "Kiritilmagan",
        "admin/admins.txt": XASANOV_UZ,
        "kino/son.txt": "0",
        "kino/kodi.txt": "0",
        "kino/id.txt": "0",
        "holat.txt": "Yoqilgan",
        "azo.dat": "",
        "block": "",
        "channel.txt": "",
        "channel2.txt": "",
        "kino_ch.txt": "",
        "tizim/admins.txt": "",
        "reaksiya.json": "{}"  # New JSON file for reactions
    }
    
    for filepath, default_content in files.items():
        if not os.path.exists(filepath):
            dir_path = os.path.dirname(filepath)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(default_content)


async def read_file(filepath: str) -> str:
    """Read file content asynchronously"""
    try:
        if os.path.exists(filepath):
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                return await f.read()
        return ""
    except Exception:
        return ""


async def write_file(filepath: str, content: str, mode: str = 'w'):
    """Write to file asynchronously"""
    try:
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        async with aiofiles.open(filepath, mode, encoding='utf-8') as f:
            await f.write(content)
    except Exception as e:
        print(f"Error writing file {filepath}: {e}")


async def append_file(filepath: str, content: str):
    """Append to file asynchronously"""
    await write_file(filepath, content, mode='a')


def read_file_sync(filepath: str) -> str:
    """Read file content synchronously"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    except Exception:
        return ""


def write_file_sync(filepath: str, content: str, mode: str = 'w'):
    """Write to file synchronously"""
    try:
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(filepath, mode, encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error writing file {filepath}: {e}")


async def get_admins() -> List[str]:
    """Get list of admin IDs"""
    admins_content = await read_file("tizim/admins.txt")
    admin_list = [admin.strip() for admin in admins_content.split('\n') if admin.strip()]
    if XASANOV_UZ not in admin_list:
        admin_list.append(str(XASANOV_UZ))
    return admin_list


async def addstat(user_id: int):
    """Add user statistics"""
    user_dir = "users"
    os.makedirs(user_dir, exist_ok=True)
    
    file_path = f"{user_dir}/{user_id}.txt"
    sana = datetime.now().strftime("%d.m.%Y")
    
    if not os.path.exists(file_path):
        await write_file(file_path, sana)


async def addblock(user_id: int):
    """Add user to block list"""
    block_content = await read_file("block")
    check = block_content.split('\n')
    
    if str(user_id) not in check:
        await append_file("block", f"\n{user_id}")


async def removeblock(user_id: int):
    """Remove user from block list"""
    block_content = await read_file("block")
    lines = block_content.split('\n')
    
    new_lines = [l for l in lines if l.strip() != str(user_id)]
    await write_file("block", '\n'.join(new_lines))


async def is_blocked(user_id: int) -> bool:
    """Check if user is blocked"""
    block_content = await read_file("block")
    return str(user_id) in block_content.split('\n')


async def joinchat(user_id: int) -> bool:
    """Check if user has joined all required channels"""
    buttons = []
    
    # Check public channels
    kanallar = await read_file("channel.txt")
    if kanallar.strip():
        lines = kanallar.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split('@')
            if len(parts) < 2:
                continue
                
            url = parts[1].strip()
            try:
                chat_info = await bot.get_chat(f"@{url}")
                ism = chat_info.title
                
                member = await bot.get_chat_member(f"@{url}", user_id)
                if member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                    buttons.append([InlineKeyboardButton(text=f"❌ {ism}", url=f"https://t.me/{url}")])
            except Exception as e:
                print(f"Error checking public channel {url}: {e}")
                continue
    
    # Check private channels
    maxfiy_kanallar = await read_file("channel2.txt")
    if maxfiy_kanallar.strip():
        lines = maxfiy_kanallar.strip().split('\n')
        
        i = 0
        while i < len(lines):
            if i + 1 >= len(lines):
                break
                
            link = lines[i].strip()
            kanal_id = lines[i + 1].strip()
            
            if not link or not kanal_id:
                i += 2
                continue
            
            fayl_nomi = f"tizim/{kanal_id}.txt"
            
            try:
                if not os.path.exists(fayl_nomi):
                    buttons.append([InlineKeyboardButton(text="❌ Maxfiy kanal", url=link)])
                else:
                    file_content = await read_file(fayl_nomi)
                    user_ids = [uid.strip() for uid in file_content.split('\n') if uid.strip()]
                    
                    if str(user_id) not in user_ids:
                        buttons.append([InlineKeyboardButton(text="❌ Maxfiy kanal", url=link)])
            except Exception as e:
                print(f"Error checking private channel: {e}")
            
            i += 2
    
    # If user hasn't joined all channels, send message with buttons
    if buttons:
        buttons.append([InlineKeyboardButton(text="🔄 Tekshirish", callback_data="checksuv")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await bot.send_message(
            chat_id=user_id,
            text="<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>",
            reply_markup=keyboard
        )
        return False
    
    return True


async def notify_new_user(user_id: int, name: str, username: Optional[str]):
    """Notify admin about new user"""
    try:
        username_text = f"@{username}" if username else "Yo'q"
        current_time = datetime.now().strftime("%d.%m.%Y | %H:%M")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Ko'rish", url=f"tg://user?id={user_id}")]
        ])
        
        await bot.send_message(
            chat_id=XASANOV_UZ,
            text=f"<b>👤 Yangi obunachi qo'shildi!\n\n"
                 f"👤 Ism: {name}\n"
                 f"🆔 ID: <code>{user_id}</code>\n"
                 f"🔗 Telegram: {username_text}\n"
                 f"🕒 Vaqt: {current_time}</b>",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error notifying admin: {e}")


async def check_user_in_database(user_id: int) -> bool:
    """Check if user exists in database"""
    baza = await read_file("azo.dat")
    user_ids = [uid.strip() for uid in baza.split('\n') if uid.strip()]
    return str(user_id) in user_ids


async def add_user_to_database(user_id: int):
    """Add user to database"""
    if not await check_user_in_database(user_id):
        await append_file("azo.dat", f"\n{user_id}")
        return True
    return False


async def load_reactions():
    """Load reactions from JSON file"""
    if os.path.exists("reaksiya.json"):
        async with aiofiles.open("reaksiya.json", 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content) if content else {}
    return {}


async def save_reactions(reactions):
    """Save reactions to JSON file"""
    async with aiofiles.open("reaksiya.json", 'w', encoding='utf-8') as f:
        await f.write(json.dumps(reactions, ensure_ascii=False, indent=4))


# Keyboards
def get_panel_keyboard():
    """Get admin panel keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="📥 Kino Yuklash")],
            [KeyboardButton(text="🗑 Kino O'chirish"), KeyboardButton(text="💬 Kino Izohi")],
            [KeyboardButton(text="📈 Top Reaksiyalar")],
            [KeyboardButton(text="🚫 Ban qilish"), KeyboardButton(text="✅ Unban qilish")],
            [KeyboardButton(text="✉ Xabarnoma"), KeyboardButton(text="✉ Alohida xabar")],
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🤖 Bot holati"), KeyboardButton(text="👥 Adminlar")],
            [KeyboardButton(text="◀️ Orqaga")]
        ],
        resize_keyboard=True
    )


def get_back_keyboard():
    """Get back keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Orqaga")]],
        resize_keyboard=True
    )


def get_bosh_keyboard():
    """Get main keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🗄 Boshqaruv paneli")]],
        resize_keyboard=True
    )


def get_user_panel_keyboard():
    """Get user panel keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📈 Top Kinolar")],
            [KeyboardButton(text="☎️ Admin bilan bog'lanish")],
            [KeyboardButton(text="◀️ Orqaga")]
        ],
        resize_keyboard=True
    )


# Handlers
@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    user_id = message.from_user.id
    name = message.from_user.first_name or ""
    username = message.from_user.username
    
    # Add user statistics
    await addstat(user_id)
    
    # Check and add user to database
    if await add_user_to_database(user_id):
        await notify_new_user(user_id, name, username)
    
    # Check if user joined all channels
    if not await joinchat(user_id):
        return
    
    # Check bot status
    holat = await read_file("holat.txt")
    admins = await get_admins()
    
    if holat.strip() == "O'chirilgan" and str(user_id) not in admins:
        await message.answer(
            "⛔️ <b>Bot vaqtinchalik o'chirilgan!</b>\n\n"
            "<i>Botda ta'mirlash ishlari olib borilayotgan bo'lishi mumkin!</i>"
        )
        return
    
    # Check if blocked
    if await is_blocked(user_id):
        await message.answer("🚫 Siz botdan bloklangansiz!")
        return
    
    # Get kino channel
    kino_ch = await read_file("kino_ch.txt")
    kino_ch_clean = kino_ch.strip().replace("@", "")
    
    # Check if user is admin
    boshqar_text = ""
    keyboard_buttons = [[InlineKeyboardButton(text="🔎 Kino kodlari", url=f"https://t.me/steammotion")]]
    
    if str(user_id) in admins:
        boshqar_text = "🗄 Boshqaruv paneli"
        keyboard_buttons.append([InlineKeyboardButton(text=boshqar_text, callback_data="boshqar")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="🛠 Foydalanuvchi paneli", callback_data="user_panel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    nameru = f'<a href="tg://user?id={user_id}">{name}</a>'
    
    await message.answer(
        f"🖐 <b>Assalomu alaykum, {nameru}\n\n"
        f"<blockquote>📊 Bot buyruqlari:\n"
        f"/start - ♻️ Botni qayta ishga tushirish\n"
        f"/help - ☎️ Qo'llab-quvvatlash</blockquote>\n\n"
        f"🔎 Film kodini yuboring:</b>",
        reply_markup=keyboard
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    """Handle /help command"""
    user_id = message.from_user.id
    
    # Check if user joined all channels
    if not await joinchat(user_id):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☎️ Qo'llab-quvvatlash", url=f"tg://user?id={XASANOV_UZ}")]
    ])
    
    await message.answer(
        "💻 <b>Savol va Takliflaringiz bolsa pastdagi manzilimizga murojaat qiling!</b>",
        reply_markup=keyboard
    )


@router.message(F.text == "◀️ Orqaga")
async def back_handler(message: Message, state: FSMContext):
    """Handle back button"""
    await state.clear()
    
    user_id = message.from_user.id
    name = message.from_user.first_name or ""
    
    # Check if user joined all channels
    if not await joinchat(user_id):
        return
    
    # Get kino channel
    kino_ch = await read_file("kino_ch.txt")
    kino_ch_clean = kino_ch.strip().replace("@", "")
    
    nameru = f'<a href="tg://user?id={user_id}">{name}</a>'
    
    await message.answer(
        f"🖐 <b>Assalomu alaykum, {nameru}\n\n"
        f"<blockquote>📊 Bot buyruqlari:\n"
        f"/start - ♻️ Botni qayta ishga tushirish\n"
        f"/help - ☎️ Qo'llab-quvvatlash</blockquote>\n\n"
        f"🔎 Film kodini yuboring:</b>",
        reply_markup=ForceReply(selective=True)
    )


@router.message(F.text.in_(["🗄 Boshqaruv paneli", "/panel"]))
async def panel_handler(message: Message, state: FSMContext):
    """Handle admin panel command"""
    await state.clear()
    
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) in admins:
        await message.answer(
            "<b>Admin paneliga xush kelibsiz!</b>",
            reply_markup=get_panel_keyboard()
        )


@router.callback_query(F.data == "boshqar")
async def boshqar_callback(callback: CallbackQuery):
    """Handle admin panel callback"""
    await callback.message.delete()
    await callback.message.answer(
        "<b>🖥️ Boshqaruv panelidasiz!</b>",
        reply_markup=get_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "user_panel")
async def user_panel_callback(callback: CallbackQuery):
    """Handle user panel callback"""
    user_id = callback.from_user.id
    admins = await get_admins()
    
    if str(user_id) in admins:
        await callback.answer("Bu panel faqat oddiy foydalanuvchilar uchun!")
        return
    
    await callback.message.delete()
    await callback.message.answer(
        "<b>🛠 Foydalanuvchi panelidasiz!</b>",
        reply_markup=get_user_panel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "checksuv")
async def check_subscription_callback(callback: CallbackQuery):
    """Handle check subscription callback"""
    user_id = callback.from_user.id
    
    await callback.message.delete()
    
    if await joinchat(user_id):
        await callback.message.answer("<b>✅ Obunangiz tasdiqlandi!</b>")
        
        # Get kino channel
        kino_ch = await read_file("kino_ch.txt")
        kino_ch_clean = kino_ch.strip().replace("@", "")
        
        # Check if user is admin
        admins = await get_admins()
        keyboard_buttons = [[InlineKeyboardButton(text="🔎 Kinolarni qidirish", url=f"https://t.me/{kino_ch_clean}")]]
        
        if str(user_id) in admins:
            keyboard_buttons.append([InlineKeyboardButton(text="🗄 Boshqaruv paneli", callback_data="boshqar")])
        else:
            keyboard_buttons.append([InlineKeyboardButton(text="🛠 Foydalanuvchi paneli", callback_data="user_panel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        name = callback.from_user.first_name or ""
        nameu = f'<a href="tg://user?id={user_id}">{name}</a>'
        
        await callback.message.answer(
            f"🖐 <b>Assalomu alaykum, {nameu}\n\n"
            f"<blockquote>📊 Bot buyruqlari:\n"
            f"/start - ♻️ Botni qayta ishga tushirish\n"
            f"/help - ☎️ Qo'llab-quvvatlash</blockquote>\n\n"
            f"🔎 Film kodini yuboring:</b>",
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data == "yopish")
async def close_callback(callback: CallbackQuery):
    """Handle close button"""
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "bosh")
async def bosh_callback(callback: CallbackQuery):
    """Handle main menu callback"""
    await callback.message.delete()
    await callback.message.answer(
        "<b>Admin paneliga xush kelibsiz!</b>",
        reply_markup=get_panel_keyboard()
    )
    await callback.answer()


# Admin management handlers
@router.message(F.text == "👥 Adminlar")
async def admins_handler(message: Message):
    """Handle admins menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    if str(user_id) == str(XASANOV_UZ):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="add")],
            [
                InlineKeyboardButton(text="📑 Ro'yxat", callback_data="list"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data="remove")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📑 Ro'yxat", callback_data="list")]
        ])
    
    await message.answer(
        "🔰 <b>Quyidagilardan birini tanlang:</b>",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admins")
async def admins_callback(callback: CallbackQuery):
    """Handle admins menu callback"""
    user_id = callback.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        await callback.answer()
        return
    
    if str(user_id) == str(XASANOV_UZ):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="add")],
            [
                InlineKeyboardButton(text="📑 Ro'yxat", callback_data="list"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data="remove")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📑 Ro'yxat", callback_data="list")]
        ])
    
    await callback.message.edit_text(
        "🔰 <b>Quyidagilardan birini tanlang:</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "list")
async def list_admins_callback(callback: CallbackQuery):
    """List all admins"""
    admins_content = await read_file("tizim/admins.txt")
    
    if not admins_content.strip():
        text = "🚫 <b>Yordamchi adminlar topilmadi!</b>"
    else:
        text = f"👮‍♂️ <b>Adminlar ro'yxati:</b>\n{admins_content}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admins")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "add")
async def add_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Start add admin process"""
    if str(callback.from_user.id) != str(XASANOV_UZ):
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer(
        "🔢 <b>Kerakli foydalanuvchi ID raqamini yuboring:</b>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.add_admin)
    await callback.answer()


@router.message(AdminStates.add_admin)
async def process_add_admin(message: Message, state: FSMContext):
    """Process add admin"""
    if str(message.from_user.id) != str(XASANOV_UZ):
        return
    
    new_admin_id = message.text.strip()
    
    # Check if user exists in database
    users = await read_file("azo.dat")
    if new_admin_id not in users:
        await message.answer(
            "🚫 <b>Ushbu foydalanuvchi botdan foydalanmaydi!</b>\n\n"
            "🔢 Boshqa ID raqamni kiriting:"
        )
        return
    
    # Check if user is already admin
    admins_content = await read_file("tizim/admins.txt")
    if new_admin_id in admins_content:
        await message.answer(
            "🚫 <b>Ushbu foydalanuvchi allaqachon admin!</b>\n\n"
            "🔢 Boshqa ID raqamni kiriting:"
        )
        return
    
    # Add admin
    new_content = f"{new_admin_id}\n{admins_content}"
    await write_file("tizim/admins.txt", new_content)
    
    await message.answer(
        f"✅ <code>{new_admin_id}</code> <b>adminlar ro'yxatiga qo'shildi!</b>",
        reply_markup=get_panel_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "remove")
async def remove_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Start remove admin process"""
    if str(callback.from_user.id) != str(XASANOV_UZ):
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer(
        "🔢 <b>Kerakli foydalanuvchi ID raqamini yuboring:</b>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.remove_admin)
    await callback.answer()


@router.message(AdminStates.remove_admin)
async def process_remove_admin(message: Message, state: FSMContext):
    """Process remove admin"""
    if str(message.from_user.id) != str(XASANOV_UZ):
        return
    
    admin_id = message.text.strip()
    
    # Check if user is in admin list
    admins_content = await read_file("tizim/admins.txt")
    if admin_id not in admins_content:
        await message.answer(
            "🚫 <b>Ushbu foydalanuvchi adminlar ro'yxatida mavjud emas!</b>\n\n"
            "🔢 Boshqa ID raqamni kiriting:"
        )
        return
    
    # Remove admin
    new_admins = admins_content.replace(f"{admin_id}\n", "")
    await write_file("tizim/admins.txt", new_admins)
    
    await message.answer(
        f"✅ <code>{admin_id}</code> <b>adminlar ro'yxatidan olib tashlandi!</b>",
        reply_markup=get_panel_keyboard()
    )
    await state.clear()


# Channel management handlers
@router.message(F.text == "📢 Kanallar")
async def channels_handler(message: Message):
    """Handle channels menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Majburiy obunalar", callback_data="majburiy")],
        [
            InlineKeyboardButton(text="🎥 Kino kanal", callback_data="qoshimcha"),
            InlineKeyboardButton(text="❌ Yopish", callback_data="bosh")
        ]
    ])
    
    await message.answer(
        "<b>Majburiy obunalarni sozlash bo'limidasiz:</b>",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "kanallar")
async def channels_callback(callback: CallbackQuery):
    """Handle channels menu callback"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Majburiy obunalar", callback_data="majburiy")],
        [
            InlineKeyboardButton(text="🎥 Kino kanal", callback_data="qoshimcha"),
            InlineKeyboardButton(text="❌ Yopish", callback_data="bosh")
        ]
    ])
    
    await callback.message.edit_text(
        "<b>⬇️ Quyidagilardan birini tanlang:</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "majburiy")
async def majburiy_callback(callback: CallbackQuery):
    """Handle mandatory subscription menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Ommaviy", callback_data="ommav"),
            InlineKeyboardButton(text="🔐 Maxfiy", callback_data="maxfiy")
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="kanallar")]
    ])
    
    await callback.message.edit_text(
        "<b>⁉️ Qaysi turda kanal qo'shmoqchisiz!</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "ommav")
async def ommav_callback(callback: CallbackQuery):
    """Handle public channels menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="qoshish")],
        [
            InlineKeyboardButton(text="📑 Ro'yxat", callback_data="royxati"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data="ochirish")
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="majburiy")]
    ])
    
    await callback.message.edit_text(
        "<b>✅ Ommaviy kanallarni sozlash bo'limidasiz:</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "maxfiy")
async def maxfiy_callback(callback: CallbackQuery):
    """Handle private channels menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="qosh")],
        [
            InlineKeyboardButton(text="📑 Ro'yxat", callback_data="roy"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data="ochir")
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="majburiy")]
    ])
    
    await callback.message.edit_text(
        "<b>✅ Maxfiy kanallarni sozlash bo'limidasiz:</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "qoshish")
async def add_public_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Start add public channel process"""
    await callback.message.delete()
    await callback.message.answer(
        "📢 <b>Ommaviy kanalni quyidagicha yuboring:</b>\n\n"
        "📄 <b>Namuna:</b> <code>@xasanov_uz</code>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.add_public_channel)
    await callback.answer()


@router.message(AdminStates.add_public_channel)
async def process_add_public_channel(message: Message, state: FSMContext):
    """Process add public channel"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    text = message.text.strip()
    
    if not text.startswith('@'):
        await message.answer("🚫 <b>Xato format! @ bilan boshlanishi kerak!</b>")
        return
    
    # Add to channel.txt
    kanallar = await read_file("channel.txt")
    lines = [line.strip() for line in kanallar.split('\n') if line.strip()]
    
    if text in lines:
        await message.answer("🚫 <b>Bu kanal allaqachon qo'shilgan!</b>")
        return
    
    await append_file("channel.txt", f"{text}\n")
    
    await message.answer(
        f"<b>✅ {text} - kanal muvaffaqiyatli qo'shildi.</b>",
        reply_markup=get_panel_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "royxati")
async def list_public_channels_callback(callback: CallbackQuery):
    """List public channels"""
    content = await read_file("channel.txt")
    
    if not content.strip():
        text = "🚫 <b>Ommaviy kanallar topilmadi!</b>"
    else:
        text = f"📢 <b>Ommaviy kanallar ro'yxati:</b>\n{content}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="ommav")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "ochirish")
async def remove_public_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Start remove public channel process"""
    await callback.message.delete()
    await callback.message.answer(
        "📢 <b>O'chirmoqchi bo'lgan ommaviy kanalni yuboring:</b>\n\n"
        "📄 <b>Namuna:</b> <code>@xasanov_uz</code>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.remove_public_channel)
    await callback.answer()


@router.message(AdminStates.remove_public_channel)
async def process_remove_public_channel(message: Message, state: FSMContext):
    """Process remove public channel"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    text = message.text.strip()
    
    if not text.startswith('@'):
        await message.answer("🚫 <b>Xato format!</b>")
        return
    
    content = await read_file("channel.txt")
    lines = content.split('\n')
    
    if text + '\n' not in lines and text not in lines:
        await message.answer("🚫 <b>Bu kanal ro'yxatda yo'q!</b>")
        return
    
    new_lines = [l for l in lines if l.strip() != text]
    await write_file("channel.txt", '\n'.join(new_lines))
    
    await message.answer(
        f"<b>✅ {text} - kanal muvaffaqiyatli o'chirildi.</b>",
        reply_markup=get_panel_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "qosh")
async def add_private_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Start add private channel process"""
    await callback.message.delete()
    await callback.message.answer(
        "<i>⚠️ Kanalingiz manzilini yuborishdan avval botni kanalingizga admin qilib olishingiz kerak! "
        "Aks holda xatoliklar yuzaga keladi!</i>\n\n"
        "📢 <b>Maxfiy kanalni quyidagicha yuboring:</b>\n\n"
        "📄 <b>Namuna:</b> <code>https://t.me/+ZEcQiRY_pRphZTdi\n-100326189432</code>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.add_channel)
    await callback.answer()


@router.message(AdminStates.add_channel)
async def process_add_private_channel(message: Message, state: FSMContext):
    """Process add private channel"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    text = message.text.strip()
    
    if not text:
        await message.answer("🚫 <b>Xato format!</b>")
        return
    
    if "https://t.me/+" not in text:
        await message.answer("🚫 <b>Xato format! Maxfiy kanal havolasi yuborishingiz kerak!</b>")
        return
    
    # Extract channel ID using regex
    match = re.search(r'-100\d+', text)
    if not match:
        await message.answer("🚫 <b>Kanal ID topilmadi! To'g'ri formatda yuboring!</b>")
        return
    
    kanal_id = match.group(0)
    
    # Create tizim directory if not exists
    os.makedirs("tizim", exist_ok=True)
    
    # Create file for channel ID
    await write_file(f"tizim/{kanal_id}.txt", "")
    
    # Add channel to channel2.txt
    kanallar = await read_file("channel2.txt")
    
    await append_file("channel2.txt", f"{text}\n")
    
    await message.answer(
        f"<b>✅ {text} - kanal muvaffaqiyatli qo'shildi.</b>",
        reply_markup=get_panel_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "roy")
async def list_private_channels_callback(callback: CallbackQuery):
    """List private channels"""
    content = await read_file("channel2.txt")
    
    if not content.strip():
        text = "🚫 <b>Maxfiy kanallar topilmadi!</b>"
    else:
        lines = content.strip().split('\n')
        formatted = ""
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                formatted += f"{lines[i]}\n{lines[i+1]}\n\n"
        text = f"📢 <b>Maxfiy kanallar ro'yxati:</b>\n{formatted}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="maxfiy")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "ochir")
async def remove_private_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Start remove private channel process"""
    await callback.message.delete()
    await callback.message.answer(
        "📢 <b>O'chirmoqchi bo'lgan maxfiy kanal ID sini yuboring:</b>\n\n"
        "📄 <b>Namuna:</b> <code>-100326189432</code>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.remove_channel)
    await callback.answer()


@router.message(AdminStates.remove_channel)
async def process_remove_private_channel(message: Message, state: FSMContext):
    """Process remove private channel"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    kanal_id = message.text.strip()
    
    if not re.match(r'^-100\d+$', kanal_id):
        await message.answer("🚫 <b>Xato format! -100 bilan boshlanadigan raqam bo'lishi kerak!</b>")
        return
    
    content = await read_file("channel2.txt")
    lines = content.split('\n')
    
    try:
        index = lines.index(kanal_id)
        link = lines[index - 1]
        del lines[index - 1:index + 1]
        await write_file("channel2.txt", '\n'.join(lines))
        
        # Remove the file
        fayl_nomi = f"tizim/{kanal_id}.txt"
        if os.path.exists(fayl_nomi):
            os.remove(fayl_nomi)
        
        await message.answer(
            f"<b>✅ {link}\n{kanal_id} - kanal muvaffaqiyatli o'chirildi.</b>",
            reply_markup=get_panel_keyboard()
        )
    except ValueError:
        await message.answer("🚫 <b>Bu ID ro'yxatda yo'q!</b>")
    
    await state.clear()


@router.callback_query(F.data == "qoshimcha")
async def set_kino_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Start set kino channel process"""
    await callback.message.delete()
    await callback.message.answer(
        "🎥 <b>Kino kodlari chiqadigan kanalni yuboring:</b>\n\n"
        "📄 <b>Namuna:</b> <code>@xasanov_uz</code>",
        reply_markup=get_bosh_keyboard()
    )
    await state.set_state(AdminStates.kino_channel)
    await callback.answer()


@router.message(AdminStates.kino_channel)
async def process_set_kino_channel(message: Message, state: FSMContext):
    """Process set kino channel"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    text = message.text.strip()
    
    if not text.startswith('@'):
        await message.answer("🚫 <b>Xato format!</b>")
        return
    
    await write_file("kino_ch.txt", text)
    
    await message.answer(
        f"<b>✅ {text} - kino kanali muvaffaqiyatli o'rnatildi.</b>",
        reply_markup=get_panel_keyboard()
    )
    await state.clear()


# Movie upload handlers
@router.message(F.text == "📥 Kino Yuklash")
async def upload_movie_handler(message: Message, state: FSMContext):
    """Handle upload movie menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>🎥 Kinoni yuboring (video yoki file formatida):</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.upload_movie)


@router.message(AdminStates.upload_movie)
async def process_upload_movie(message: Message, state: FSMContext):
    """Process movie upload"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    kino_ch = await read_file("kino_ch.txt")
    if not kino_ch.strip():
        await message.answer("🚫 <b>Avval kino kanalini o'rnating!</b>")
        await state.clear()
        return
    
    if not (message.video or message.document):
        await message.answer("🚫 <b>Faqat video yoki file yuboring!</b>")
        return
    
    file_id = message.video.file_id if message.video else message.document.file_id
    is_video = bool(message.video)
    
    try:
        # Post to channel with code
        kodi = int(await read_file("kino/kodi.txt") or "0") + 1
        await write_file("kino/kodi.txt", str(kodi))
        
        caption = f"Kod: {kodi}"
        
        if is_video:
            await bot.send_video(chat_id=kino_ch.strip(), video=file_id, caption=caption)
        else:
            await bot.send_document(chat_id=kino_ch.strip(), document=file_id, caption=caption)
        
        # Save file_id for code
        await write_file(f"kino/{kodi}.txt", file_id)
        
        # Initialize reactions for new movie
        reactions = await load_reactions()
        if str(kodi) not in reactions:
            reactions[str(kodi)] = {"likes": [], "dislikes": []}
            await save_reactions(reactions)
        
        await message.answer(f"✅ Kino yuklandi, kod: {kodi}", reply_markup=get_panel_keyboard())
        await state.clear()
    except Exception as e:
        await message.answer(f"Xato: {str(e)}")
        await state.clear()


# Movie delete handlers
@router.message(F.text == "🗑 Kino O'chirish")
async def delete_movie_handler(message: Message, state: FSMContext):
    """Handle delete movie menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>🗑 O'chirmoqchi bo'lgan kino kodini yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.delete_movie)


@router.message(AdminStates.delete_movie)
async def process_delete_movie(message: Message, state: FSMContext):
    """Process movie delete"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    code = message.text.strip()
    
    if not code.isdigit():
        await message.answer("🚫 <b>Xato! Kod raqam bo'lishi kerak.</b>")
        return
    
    file_path = f"kino/{code}.txt"
    comment_path = f"kino/{code}_comment.txt"
    
    if not os.path.exists(file_path):
        await message.answer("🚫 <b>Bunday kod mavjud emas!</b>")
        return
    
    try:
        # Remove file
        os.remove(file_path)
        
        # Remove comment if exists
        if os.path.exists(comment_path):
            os.remove(comment_path)
        
        # Remove from reactions
        reactions = await load_reactions()
        if code in reactions:
            del reactions[code]
            await save_reactions(reactions)
        
        await message.answer(f"✅ Kino (kod: {code}) muvaffaqiyatli o'chirildi!", reply_markup=get_panel_keyboard())
    except Exception as e:
        await message.answer(f"🚫 Xato: {str(e)}")
    
    await state.clear()


# Movie comment handlers
@router.message(F.text == "💬 Kino Izohi")
async def add_comment_handler(message: Message, state: FSMContext):
    """Handle add comment menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>💬 Izoh qo'shmoqchi bo'lgan kino kodini yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.update_data(comment_step="code")
    await state.set_state(AdminStates.add_comment)


@router.message(AdminStates.add_comment)
async def process_add_comment(message: Message, state: FSMContext):
    """Process add comment"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    data = await state.get_data()
    comment_step = data.get("comment_step", "code")
    
    if comment_step == "code":
        code = message.text.strip()
        
        if not code.isdigit():
            await message.answer("🚫 <b>Xato! Kod raqam bo'lishi kerak.</b>")
            return
        
        file_path = f"kino/{code}.txt"
        
        if not os.path.exists(file_path):
            await message.answer("🚫 <b>Bunday kod mavjud emas!</b>")
            return
        
        await state.update_data(code=code, comment_step="comment")
        await message.answer("<b>💬 Endi izoh matnini yuboring:</b>")
    
    elif comment_step == "comment":
        code = data.get("code")
        comment = message.text.strip()
        
        comment_path = f"kino/{code}_comment.txt"
        await write_file(comment_path, comment)
        
        await message.answer(f"✅ Izoh (kod: {code}) muvaffaqiyatli qo'shildi!", reply_markup=get_panel_keyboard())
        await state.clear()


# Top reactions handler
@router.message(F.text.in_({"📈 Top Reaksiyalar", "📈 Top Kinolar"}))
async def top_reactions_handler(message: Message):
    """Handle top reactions menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    reactions = await load_reactions()
    
    table = "| Kod | Like | Dislike |\n|-----|------|---------|\n"
    found = False
    
    for code, data in reactions.items():
        likes = len(data.get("likes", []))
        dislikes = len(data.get("dislikes", []))
        if likes > 50 or dislikes > 50:
            table += f"| {code} | {likes} | {dislikes} |\n"
            found = True
    
    if not found:
        table = "🚫 50 tadan oshgan reaksiyalar topilmadi!"
    
    await message.answer(f"<b>📈 50+ reaksiyali kinolar:</b>\n<pre>{table}</pre>")


# Broadcast handlers
@router.message(F.text == "✉ Xabarnoma")
async def send_message_handler(message: Message, state: FSMContext):
    """Handle broadcast menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>Xabarni yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.send_message)


@router.message(AdminStates.send_message)
async def process_send_message(message: Message, state: FSMContext):
    """Process broadcast"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    users = await read_file("azo.dat")
    user_list = [uid.strip() for uid in users.split('\n') if uid.strip()]
    
    success = 0
    fail = 0
    for uid in user_list:
        try:
            await bot.copy_message(chat_id=int(uid), from_chat_id=user_id, message_id=message.message_id)
            success += 1
        except:
            fail += 1
    
    await message.answer(f"✅ Yuborildi: {success}\n🚫 Xato: {fail}", reply_markup=get_panel_keyboard())
    await state.clear()


# Single message handler
@router.message(F.text == "✉ Alohida xabar")
async def single_message_handler(message: Message, state: FSMContext):
    """Handle single message menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>Foydalanuvchi ID sini yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.single_message_id)


@router.message(AdminStates.single_message_id)
async def process_single_message_id(message: Message, state: FSMContext):
    """Process single user ID"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    target_id = message.text.strip()
    if not target_id.isdigit():
        await message.answer("🚫 <b>Xato! ID raqam bo'lishi kerak.</b>")
        return
    
    # Save target ID to state
    await state.update_data(target_id=target_id)
    
    await message.answer(
        "<b>Endi xabarni yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.single_message_content)


@router.message(AdminStates.single_message_content)
async def process_single_message_content(message: Message, state: FSMContext):
    """Process single message content"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    data = await state.get_data()
    target_id = data.get("target_id")
    
    if not target_id:
        await message.answer("🚫 <b>Xato! ID topilmadi.</b>")
        await state.clear()
        return
    
    try:
        await bot.copy_message(chat_id=int(target_id), from_chat_id=user_id, message_id=message.message_id)
        await message.answer(f"✅ Xabar {target_id} ga yuborildi!", reply_markup=get_panel_keyboard())
    except Exception as e:
        await message.answer(f"🚫 Xato: {str(e)}")
    
    await state.clear()


# Statistics handler
@router.message(F.text == "📊 Statistika")
async def stats_handler(message: Message):
    """Handle statistics"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    users = await read_file("azo.dat")
    count = len([uid for uid in users.split('\n') if uid.strip()])
    
    await message.answer(f"👥 Obunachilar: {count}")


# Bot status handler
@router.message(F.text == "🤖 Bot holati")
async def bot_status_handler(message: Message):
    """Handle bot status"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    holat = (await read_file("holat.txt")).strip() or "Yoqilgan"
    toggle_text = "⛔️ O'chirish" if holat == "Yoqilgan" else "✅ Yoqish"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data="toggle_holat")]
    ])
    
    await message.answer(f"🤖 Bot holati: {holat}", reply_markup=keyboard)


@router.callback_query(F.data == "toggle_holat")
async def toggle_holat_callback(callback: CallbackQuery):
    """Toggle bot status"""
    holat = (await read_file("holat.txt")).strip() or "Yoqilgan"
    new_holat = "O'chirilgan" if holat == "Yoqilgan" else "Yoqilgan"
    await write_file("holat.txt", new_holat)
    
    toggle_text = "⛔️ O'chirish" if new_holat == "Yoqilgan" else "✅ Yoqish"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data="toggle_holat")]
    ])
    
    await callback.message.edit_text(f"🤖 Bot holati: {new_holat}", reply_markup=keyboard)
    await callback.answer()


# Ban user handler
@router.message(F.text == "🚫 Ban qilish")
async def ban_user_handler(message: Message, state: FSMContext):
    """Handle ban user menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>🚫 Ban qilmoqchi bo'lgan foydalanuvchi ID sini yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.ban_user)


@router.message(AdminStates.ban_user)
async def process_ban_user(message: Message, state: FSMContext):
    """Process ban user"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    target_id = message.text.strip()
    
    if not target_id.isdigit():
        await message.answer("🚫 <b>Xato! ID raqam bo'lishi kerak.</b>")
        return
    
    if not await check_user_in_database(int(target_id)):
        await message.answer("🚫 <b>Bunday foydalanuvchi mavjud emas!</b>")
        return
    
    await addblock(int(target_id))
    await message.answer(f"✅ Foydalanuvchi {target_id} ban qilindi!", reply_markup=get_panel_keyboard())
    await state.clear()


# Unban user handler
@router.message(F.text == "✅ Unban qilish")
async def unban_user_handler(message: Message, state: FSMContext):
    """Handle unban user menu"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    await message.answer(
        "<b>✅ Unban qilmoqchi bo'lgan foydalanuvchi ID sini yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.unban_user)


@router.message(AdminStates.unban_user)
async def process_unban_user(message: Message, state: FSMContext):
    """Process unban user"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) not in admins:
        return
    
    target_id = message.text.strip()
    
    if not target_id.isdigit():
        await message.answer("🚫 <b>Xato! ID raqam bo'lishi kerak.</b>")
        return
    
    if not await is_blocked(int(target_id)):
        await message.answer("🚫 <b>Bu foydalanuvchi banlanmagan!</b>")
        return
    
    await removeblock(int(target_id))
    await message.answer(f"✅ Foydalanuvchi {target_id} unban qilindi!", reply_markup=get_panel_keyboard())
    await state.clear()


# Contact admin handler
@router.message(F.text == "☎️ Admin bilan bog'lanish")
async def contact_admin_handler(message: Message, state: FSMContext):
    """Handle contact admin"""
    user_id = message.from_user.id
    admins = await get_admins()
    
    if str(user_id) in admins:
        await message.answer("Siz adminsiz!")
        return
    
    await message.answer(
        "<b>Admin ga xabar yuboring:</b>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(UserStates.contact_admin)


@router.message(UserStates.contact_admin)
async def process_contact_admin(message: Message, state: FSMContext):
    """Process contact admin message"""
    admins = await get_admins()
    user_id = message.from_user.id
    
    if str(user_id) in admins:
        await message.answer("Siz adminsiz!")
        await state.clear()
        return
    
    try:
        await bot.copy_message(chat_id=XASANOV_UZ, from_chat_id=user_id, message_id=message.message_id)
        await message.answer("✅ Xabaringiz adminga yuborildi!", reply_markup=get_user_panel_keyboard())
    except Exception as e:
        await message.answer(f"🚫 Xato: {str(e)}")
    
    await state.clear()


# User message handler for movie codes
@router.message()
async def message_handler(message: Message, state: FSMContext):
    """Handle user messages for movie codes"""
    user_id = message.from_user.id
    
    current_state = await state.get_state()
    if current_state is not None:
        return  # Let state handlers handle if in state
    
    if not await joinchat(user_id):
        return
    
    if await is_blocked(user_id):
        await message.answer("🚫 Siz bloklangansiz!")
        return
    
    text = message.text.strip()
    
    if text.isdigit():
        code = text
        file_path = f"kino/{code}.txt"
        comment_path = f"kino/{code}_comment.txt"
        
        if not os.path.exists(file_path):
            await message.answer("🚫 Kod topilmadi!")
            return
        
        file_id = await read_file(file_path)
        
        # Load reactions
        reactions = await load_reactions()
        movie_reactions = reactions.get(code, {"likes": [], "dislikes": []})
        
        # Create keyboard with like/dislike
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"👍 {len(movie_reactions['likes'])}", callback_data=f"like_{code}"),
                InlineKeyboardButton(text=f"👎 {len(movie_reactions['dislikes'])}", callback_data=f"dislike_{code}")
            ]
        ])
        
        # Get admin comment if exists
        admin_comment = ""
        if os.path.exists(comment_path):
            admin_comment = await read_file(comment_path)
            admin_comment = f"\n\n💬 <b>Admin izohi:</b> {admin_comment}"
        
        try:
            await bot.send_video(chat_id=user_id, video=file_id, caption=admin_comment, reply_markup=keyboard)
        except:
            try:
                await bot.send_document(chat_id=user_id, document=file_id, caption=admin_comment, reply_markup=keyboard)
            except Exception as e:
                await message.answer(f"Xato: {str(e)}")
    else:
        await message.answer("🔢 Film kodini yuboring!")


# Reaction callback handlers
@router.callback_query(F.data.startswith("like_"))
async def like_callback(callback: CallbackQuery):
    """Handle like button"""
    code = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    reactions = await load_reactions()
    if code in reactions:
        if user_id in reactions[code]["likes"]:
            reactions[code]["likes"].remove(user_id)  # toggle off
        else:
            if user_id in reactions[code]["dislikes"]:
                reactions[code]["dislikes"].remove(user_id)
            reactions[code]["likes"].append(user_id)
        await save_reactions(reactions)
    
    # Update keyboard
    movie_reactions = reactions.get(code, {"likes": [], "dislikes": []})
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"👍 {len(movie_reactions['likes'])}", callback_data=f"like_{code}"),
            InlineKeyboardButton(text=f"👎 {len(movie_reactions['dislikes'])}", callback_data=f"dislike_{code}")
        ]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("👍 Baho qabul qilindi!")


@router.callback_query(F.data.startswith("dislike_"))
async def dislike_callback(callback: CallbackQuery):
    """Handle dislike button"""
    code = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    reactions = await load_reactions()
    if code in reactions:
        if user_id in reactions[code]["dislikes"]:
            reactions[code]["dislikes"].remove(user_id)  # toggle off
        else:
            if user_id in reactions[code]["likes"]:
                reactions[code]["likes"].remove(user_id)
            reactions[code]["dislikes"].append(user_id)
        await save_reactions(reactions)
    
    # Update keyboard
    movie_reactions = reactions.get(code, {"likes": [], "dislikes": []})
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"👍 {len(movie_reactions['likes'])}", callback_data=f"like_{code}"),
            InlineKeyboardButton(text=f"👎 {len(movie_reactions['dislikes'])}", callback_data=f"dislike_{code}")
        ]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("👎 Baho qabul qilindi!")


# Chat join request handler
@router.chat_join_request()
async def chat_join_request_handler(chat_join_request: ChatJoinRequest):
    """Handle chat join requests for private channels"""
    join_chat_id = chat_join_request.chat.id
    join_user_id = chat_join_request.from_user.id
    
    # Create tizim directory
    os.makedirs("tizim", exist_ok=True)
    
    # Read or create file for this channel
    fayl_nomi = f"tizim/{join_chat_id}.txt"
    
    if os.path.exists(fayl_nomi):
        ids = await read_file(fayl_nomi)
        ids_list = [uid.strip() for uid in ids.split('\n') if uid.strip()]
    else:
        ids_list = []
    
    # Add user ID if not already present
    if str(join_user_id) not in ids_list:
        ids_list.append(str(join_user_id))
        await write_file(fayl_nomi, '\n'.join(ids_list) + '\n')
        
        try:
            await bot.send_message(
                chat_id=join_user_id,
                text="<b>/start - bosing va kino kodini yuboring!</b>"
            )
        except Exception as e:
            print(f"Error sending message to user {join_user_id}: {e}")


# Chat member update handler (for block detection)
@router.my_chat_member()
async def my_chat_member_handler(chat_member: ChatMemberUpdated):
    """Handle bot being blocked/kicked"""
    if chat_member.new_chat_member.status == ChatMemberStatus.KICKED:
        await addblock(chat_member.from_user.id)


# Webhook setup
async def on_startup(dispatcher: Dispatcher):
    # Webhookni o'rnatish (Renderda domain o'zgaruvchisi kerak, masalan RENDER_APP_NAME env)
    app_name = os.getenv("RENDER_APP_NAME")  # Renderda app nomini env ga qo'shing, masalan "my-bot"
    webhook_url = f"https://{app_name}.onrender.com/webhook"
    await bot.set_webhook(webhook_url)


# Main function
async def main():
    """Main function to run the bot"""
    # Create directories and files
    ensure_directories()
    ensure_files()
    
    # Include router
    dp.include_router(router)
    
    # Webhook server setup
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    # Startup hook
    dp.startup.register(on_startup)

    # Run web app
    port = int(os.getenv("PORT", 8080))
    print(f"Bot webhook server starting on port {port}...")
    await web._run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    asyncio.run(main())
