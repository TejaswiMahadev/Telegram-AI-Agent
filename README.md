# Telegram AI Agent with Streamlit Dashboard

## Overview
This project consists of a **Telegram AI Agent** powered by Gemini AI and a **Streamlit-based dashboard** for monitoring conversations and managing interactions. The bot is implemented using the **python-telegram-bot** library, and user interactions are stored in **MongoDB**.

## Features
- 🛠 **AI-powered Telegram bot** using Gemini API
- 📊 **Streamlit dashboard** for monitoring and managing user interactions
- 📂 **MongoDB integration** for storing user messages and responses
- 🔍 **Search and filter conversations** in the dashboard
- 🔄 **Real-time updates** with Streamlit

## Tech Stack
- **Backend**: Python, python-telegram-bot, Gemini API
- **Database**: MongoDB
- **Frontend**: Streamlit

## Implementation Details
### 1. Message Handling
- The bot listens for incoming messages using the `telegram.ext.Updater` and `telegram.ext.Dispatcher`.
- User messages are passed to a **message handler**, which processes the text and sends it to the **Gemini AI API**.
- The AI response is retrieved and sent back to the user through the Telegram bot.
- All messages and responses are logged in **MongoDB** for future reference.

### 2. AI Response Generation
- The Gemini AI API is integrated using an HTTP request to fetch intelligent responses.
- A **pre-processing module** cleans user inputs before sending them to the API.
- A **post-processing module** refines the AI-generated response for better readability and relevance.

### 3. Database Integration
- The bot uses **MongoDB** to store chat history, including:
  - User ID
  - Timestamp
  - User message
  - AI response
- This enables **searching**, **filtering**, and **analyzing** past interactions through the dashboard.

### 4. Streamlit Dashboard
- The Streamlit dashboard provides a **real-time interface** to monitor conversations.
- Key features include:
  - **Search & filter** to find specific chats
  - **Conversation history display**
  - **Basic analytics** (e.g., most frequent users, common topics)

## Installation & Setup

### Prerequisites
Ensure you have the following installed:
- Python (>= 3.8)
- MongoDB
- Telegram Bot Token (from BotFather)
- Gemini API Key

### 1. Clone the Repository
```bash
git clone https://github.com/TejaswiMahadev/Telegram-AI-Agent.git
cd telegram-ai-agent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file and add the following:
```
TELEGRAM_BOT_TOKEN=your_telegram_token
GEMINI_API_KEY=your_gemini_api_key
MONGO_URI=your_mongodb_connection_string
DB_NAME=your_database_name
COLLECTION_NAME=your_collection_name
```

### 4. Run the Bot
```bash
python bot.py
```

### 5. Run the Streamlit Dashboard
```bash
streamlit run dashboard.py
```

## Usage
1. **Start the bot** by running `bot.py`.
2. **Monitor conversations** in the Streamlit dashboard.
3. **Search and filter** messages in real-time.
4. **Modify responses** or manage data via MongoDB.

## Future Improvements
- 📢 **Admin controls** to respond to users from the dashboard
- 📈 **Analytics module** to visualize user engagement
- 📤 **Export chat history** to CSV or JSON
- 🤖 **Fine-tuning AI responses** for better accuracy

## Contributing
Pull requests are welcome! If you'd like to contribute, fork the repo and create a PR with your changes.


---
🚀 *Happy coding!*
