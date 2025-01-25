import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import logging

# Configure logging
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR)

# Bot token and admin ID
API_TOKEN = '8120903065:AAHteYq0QAIMqPypZq_Gt9B3qHw6J4rEF60'
ADMIN_IDS = ['7858368373', '5756495153']  # Replace with your admin IDs as strings
CHANNELS = ['@BESTBWSTNEST', '@BESTBWSTNEST', '@BESTBWSTNEST']  # Replace with your channel usernames

bot = telebot.TeleBot(API_TOKEN)

# Directories for file storage
BASE_DIR = os.path.join(os.getcwd(), "bot_files")
os.makedirs(BASE_DIR, exist_ok=True)

user_access = set()  # To track users who verified
file_downloads = {}  # To track file downloads {file_name: [{user_id, username}]}

# Helper functions
def check_user_channels(user_id):
    """Check if a user is a member of all required channels."""
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logging.error(f"Error checking channel {channel} for user {user_id}: {e}")
            return False
    return True

def list_files_markup():
    """Create an inline keyboard with available files."""
    files = os.listdir(BASE_DIR)
    markup = InlineKeyboardMarkup()
    for file in files:
        markup.add(InlineKeyboardButton(file, callback_data=f"download:{file}"))
    return markup if files else None

# Start command
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Inline buttons for channels and verification
    markup = InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(InlineKeyboardButton("JOIN", url=f"https://t.me/{channel[1:]}"))
    markup.add(InlineKeyboardButton("VERIFY", callback_data="verify"))

    bot.reply_to(
        message,
        f"Hi @{username}, welcome to the bot!\n\n"
        "To access this bot, you must join the following channels:\n" +
        "\n".join([f"- {channel}" for channel in CHANNELS]) +
        "\n\nClick 'VERIFY' after joining all channels.",
        reply_markup=markup
    )

# Verify membership
@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_membership(call):
    user_id = call.from_user.id

    if check_user_channels(user_id):
        user_access.add(user_id)
        bot.answer_callback_query(call.id, "✅ You have joined all required channels!")
        bot.send_message(user_id, "🎉 You now have access to the bot!")

        # Automatically display available files
        files_markup = list_files_markup()
        if files_markup:
            bot.send_message(user_id, "📂 Available files:", reply_markup=files_markup)
        else:
            bot.send_message(user_id, "❌ No files are available at the moment.")
    else:
        bot.answer_callback_query(call.id, "❌ Please join all channels before verifying.")
        bot.send_message(user_id, "🚫 You have not joined all required channels. Please join them to access the bot.")

# Handle file download requests
@bot.callback_query_handler(func=lambda call: call.data.startswith("download:"))
def download_file(call):
    user_id = call.from_user.id
    username = call.from_user.username
    file_name = call.data.split(":")[1]
    file_path = os.path.join(BASE_DIR, file_name)

    if not os.path.exists(file_path):
        bot.answer_callback_query(call.id, "❌ File does not exist.")
        return

    # Track downloads
    if file_name not in file_downloads:
        file_downloads[file_name] = []
    file_downloads[file_name].append({"user_id": user_id, "username": username})

    bot.answer_callback_query(call.id, f"📤 Sending {file_name}...")
    with open(file_path, 'rb') as f:
        bot.send_document(user_id, f)

    bot.send_message(user_id, f"✅ File `{file_name}` has been sent successfully!")
    # Admin: Upload file
@bot.message_handler(func=lambda msg: msg.text.lower() == "add file" and str(msg.from_user.id) in ADMIN_IDS)
def request_file_upload(message):
    bot.reply_to(message, "Please send the file to upload.")

@bot.message_handler(content_types=['document'], func=lambda msg: str(msg.from_user.id) in ADMIN_IDS)
def handle_file_upload(message):
    try:
        # Get file information
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        file_size = message.document.file_size

        # Debugging: Log the file size
        print(f"DEBUG: File size is {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")

        # Check if the file exceeds the 50MB limit
        if file_size > 50 * 1024 * 1024:  # 50MB
            bot.reply_to(message, "❌ File size exceeds the 50MB limit allowed by Telegram bots.")
            return

        # Proceed to download and save the file
        bot.reply_to(message, f"Uploading {file_name}...")
        downloaded_file = bot.download_file(file_info.file_path)

        with open(os.path.join(BASE_DIR, file_name), 'wb') as f:
            f.write(downloaded_file)

        bot.reply_to(message, f"✅ File {file_name} uploaded successfully!")

    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        bot.reply_to(message, f"❌ An error occurred while uploading the file: {e}")


@bot.message_handler(func=lambda msg: msg.text.lower() == "download stats")
def check_download_stats(message):
    if str(message.from_user.id) not in ADMIN_IDS:  # Check if the user is an admin
        bot.reply_to(message, "🚫 You are not authorized to view download stats.")
        return

    if not file_downloads:
        bot.reply_to(message, "📊 No files have been downloaded yet.")
        return

    stats = "📊 File Download Stats:\n\n"
    for file_name, downloads in file_downloads.items():
        stats += f"📁 {file_name}:\n"
        for user in downloads:
            stats += f"  - {user['username']} (ID: {user['user_id']})\n"
    bot.reply_to(message, stats)

# Run the bot
bot.infinity_polling()