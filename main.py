import os
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, 
    ConversationHandler, filters
)
import google.generativeai as genai
import logging
from PIL import Image
import io

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client.telegram_bot
users = db.users

# Configure Gemini

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
text_model = genai.GenerativeModel("gemini-pro")
vision_model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation states
PHONE_NUMBER, WEBSEARCH_QUERY , CHAT_QUERY = range(3)

def escape_markdown_v2(text):
    """Escape Telegram MarkdownV2 special characters"""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in special_chars else char for char in text)

def generate_google_search_urls(query, num_results=3):
    """Generate Google search URLs for the given query"""
    encoded_query = urllib.parse.quote(query)
    base_urls = [
        f"https://www.google.com/search?q={encoded_query}",
        f"https://www.google.com/search?q={encoded_query}+detailed",
        f"https://www.google.com/search?q={encoded_query}+tutorial"
    ]
    return base_urls[:num_results]

def start_bot():
    # Get the token from environment variable
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        raise ValueError("No Telegram bot token found in environment variables.")

    async def start(update, context):
        await update.message.reply_text('Hello!')

    # Initialize the application
    application = Application.builder().token(TOKEN).build()

    # Add command handler
    application.add_handler(CommandHandler("start", start))

    # Set up webhook
    WEBHOOK_URL = "https://telegram-ai-agent-rvf0.onrender.com"
    application.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_url=WEBHOOK_URL
    )


# User Registration Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and initiate registration"""
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Check if user exists
    existing_user = users.find_one({"chat_id": chat_id})
    
    if existing_user and existing_user.get("phone_number"):
        await update.message.reply_text(
            "Welcome back! You're already registered. Use /websearch to start searching.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Create or update user document
    if not existing_user:
        users.insert_one({
            "chat_id": chat_id,
            "first_name": user.first_name,
            "username": user.username,
            "phone_number": None,
            "chat_history": [],
            "files": [],
            "searches": []
        })

    contact_button = KeyboardButton("Share Contact", request_contact=True)
    reply_markup = ReplyKeyboardMarkup(
        [[contact_button]], 
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Welcome! Please share your phone number using the button below or type it in international format (+1234567890):",
        reply_markup=reply_markup
    )
    return PHONE_NUMBER

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shared contact information"""
    chat_id = update.effective_chat.id
    contact = update.message.contact
    
    if not contact:
        await update.message.reply_text(
            "Please share your contact or type your phone number.",
            reply_markup=ReplyKeyboardRemove()
        )
        return PHONE_NUMBER
    
    phone_number = contact.phone_number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    users.update_one(
        {"chat_id": chat_id},
        {"$set": {"phone_number": phone_number}}
    )

    await update.message.reply_text(
        "Thank you for registering! You can now use /websearch to start searching.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle manually typed phone number"""
    chat_id = update.effective_chat.id
    phone_number = update.message.text.strip()

    if not phone_number.startswith('+'):
        await update.message.reply_text(
            "Please use international format starting with + (e.g., +1234567890)",
            reply_markup=ReplyKeyboardRemove()
        )
        return PHONE_NUMBER

    # Basic validation - you might want to add more sophisticated validation
    if not phone_number[1:].isdigit() or len(phone_number) < 10:
        await update.message.reply_text(
            "Invalid phone number format. Please try again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return PHONE_NUMBER

    users.update_one(
        {"chat_id": chat_id},
        {"$set": {"phone_number": phone_number}}
    )

    await update.message.reply_text(
        "Registration complete! You can now use /websearch to start searching.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END



# Web Search Handlers
async def websearch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate web search conversation"""
    chat_id = update.effective_chat.id
    user_data = users.find_one({"chat_id": chat_id})

    if not user_data or not user_data.get("phone_number"):
        await update.message.reply_text(
            "Please complete registration first using /start"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Please enter your search query:",
        reply_markup=ReplyKeyboardRemove()
    )
    return WEBSEARCH_QUERY

async def handle_websearch_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process web search query using direct Google search URLs and provide AI summary"""
    query = update.message.text
    chat_id = update.effective_chat.id
    user = update.effective_user

    try:
        logger.info(f"Web search initiated by {user.id} for query: '{query}'")
        await update.message.reply_text("🔍 Searching and generating summary...")

        # Generate Google search URLs
        search_urls = generate_google_search_urls(query)

        # Store search in database
        users.update_one(
            {"chat_id": chat_id},
            {"$push": {"searches": {
                "query": query,
                "results_count": len(search_urls),
                "timestamp": datetime.now()
            }}}
        )

        # Generate AI summary and search tips
        summary_prompt = f"""
        For the search query: "{query}"
        
        Provide a concise summary of what someone might find when searching this topic.
        Include:
        1. Key points or main information
        2. Types of resources likely to be found
        3. One specific search tip
        
        Keep the summary under 150 words.
        """

        try:
            ai_response = text_model.generate_content(summary_prompt)
            summary_text = ai_response.text if ai_response else "Summary not available"
        except Exception as ai_error:
            logger.warning(f"Summary generation failed: {str(ai_error)}")
            summary_text = "⚠️ Could not generate search summary"

        # Build and send response
        response_lines = [
            f"🔎 *Search Results for* {escape_markdown_v2(query)}:\n",
            f"{escape_markdown_v2(summary_text)}\n",
            "*Relevant Links:*"
        ]

        for i, url in enumerate(search_urls, 1):
            search_type = "General" if i == 1 else "Detailed" if i == 2 else "Tutorial"
            response_lines.append(
                f"{i}\\. [{escape_markdown_v2(search_type)} Search]({escape_markdown_v2(url)})"
            )

        await update.message.reply_text(
            "\n".join(response_lines),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        logger.error(f"Critical failure: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Failed to process search request.")

    return ConversationHandler.END
#========================= CHAT QUERY=============================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a chat conversation with Gemini"""
    chat_id = update.effective_chat.id
    user_data = users.find_one({"chat_id": chat_id})

    if not user_data or not user_data.get("phone_number"):
        await update.message.reply_text(
            "Please complete registration first using /start"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "You can now chat with me! Send your message or /end to finish.",
        reply_markup=ReplyKeyboardRemove()
    )
    return CHAT_QUERY

async def handle_chat_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process chat messages using Gemini"""
    query = update.message.text
    chat_id = update.effective_chat.id
    
    if query.lower() == '/end':
        await update.message.reply_text("Chat ended. You can start a new chat with /chat")
        return ConversationHandler.END

    try:
        # Generate response using Gemini
        response = text_model.generate_content(query)
        response_text = response.text if response else "I couldn't generate a response."

        # Store chat history
        chat_entry = {
            "user_message": query,
            "bot_response": response_text,
            "timestamp": datetime.now()
        }
        
        users.update_one(
            {"chat_id": chat_id},
            {"$push": {"chat_history": chat_entry}}
        )

        await update.message.reply_text(response_text)
        return CHAT_QUERY

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")
        return CHAT_QUERY

# File Analysis Handlers
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image and file uploads"""
    chat_id = update.effective_chat.id
    user_data = users.find_one({"chat_id": chat_id})

    if not user_data or not user_data.get("phone_number"):
        await update.message.reply_text("Please complete registration first using /start")
        return

    try:
        # Handle image files
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_info = await context.bot.get_file(file_id)
            file_bytes = await file_info.download_as_bytearray()
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(file_bytes))
            
            # Generate image analysis using Gemini Vision
            response = vision_model.generate_content([
                "Analyze this image and describe what you see in detail",
                image
            ])
            analysis = response.text if response else "Could not analyze the image."
            
            # Store file metadata
            file_entry = {
                "file_id": file_id,
                "file_type": "image",
                "analysis": analysis,
                "timestamp": datetime.now()
            }
            
            users.update_one(
                {"chat_id": chat_id},
                {"$push": {"files": file_entry}}
            )
            
            await update.message.reply_text(f"Image Analysis:\n\n{analysis}")
            
        # Handle document files (e.g., PDF)
        elif update.message.document:
            doc = update.message.document
            file_id = doc.file_id
            file_name = doc.file_name
            mime_type = doc.mime_type
            
            # Store file metadata
            file_entry = {
                "file_id": file_id,
                "file_name": file_name,
                "file_type": mime_type,
                "timestamp": datetime.now()
            }
            
            users.update_one(
                {"chat_id": chat_id},
                {"$push": {"files": file_entry}}
            )
            
            await update.message.reply_text(
                f"File received: {file_name}\n"
                f"Type: {mime_type}\n"
                "File has been stored in the database."
            )

    except Exception as e:
        logger.error(f"File handling error: {str(e)}", exc_info=True)
        await update.message.reply_text("Sorry, I encountered an error processing your file.")

def main():
    """Start the bot"""
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Registration conversation handler
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE_NUMBER: [
                MessageHandler(filters.CONTACT, contact_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_number)
            ]
        },
        fallbacks=[],
        name="registration"
    )
    application.add_handler(reg_conv)

    # Web search conversation handler
    websearch_conv = ConversationHandler(
        entry_points=[CommandHandler("websearch", websearch)],
        states={
            WEBSEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_websearch_query)
            ]
        },
        fallbacks=[],
        name="websearch"
    )

    chat_conv = ConversationHandler(
        entry_points=[CommandHandler("chat", chat)],
        states={
            CHAT_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_query)
            ]
        },
        fallbacks=[CommandHandler("end", lambda u, c: ConversationHandler.END)],
        name="chat"
    )

    application.add_handler(websearch_conv)
    application.add_handler(reg_conv)
    application.add_handler(chat_conv)
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_file))

    application.run_polling()

if __name__ == "__main__":
    main()
    start_bot()

