# Chef Voice AI Agent 🍳🎙️

A real-time voice-powered AI assistant for chefs to document and manage recipes through natural conversation.

![Voice Agent Demo](screenshot_placeholder.png)

## Features

✨ **Voice-First Interface**: Speak naturally to document recipes hands-free  
🗣️ **Real-time Transcription**: See your words and TULLIA's responses in real-time  
📝 **Smart Recipe Management**: Save batch recipes, plate recipes, search, and retrieve  
☁️ **Auto-Sync to Google Sheets**: All recipes automatically sync to Google Sheets  
🎯 **Multi-Chef Support**: Each chef has their own recipe database  
🔊 **Natural TTS**: TULLIA speaks back with high-quality voice synthesis

## Architecture

```
User → LiveKit → Deepgram (STT) → Groq LLM → Recipe Tools → PostgreSQL + Sheets
                                        ↓
                                   Cartesia TTS → LiveKit → User
```

### Tech Stack

- **Frontend**: Vanilla JS + LiveKit Client SDK
- **Backend**: LiveKit Agents (Python)
- **STT**: Deepgram Nova-2
- **LLM**: Groq (llama-3.1-8b-instant)
- **TTS**: Cartesia Sonic-3
- **Database**: NeonDB PostgreSQL
- **Sync**: Google Sheets API
- **Hosting**: LiveKit Cloud

## Prerequisites

- Python 3.10+
- PostgreSQL database (NeonDB recommended)
- API Keys:
  - LiveKit Cloud account
  - Deepgram API key
  - Groq API key
  - Cartesia API key
  - Google Sheets credentials (optional)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cooking-voice-ai-agent.git
   cd cooking-voice-ai-agent
   ```

2. **Set up Python environment**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Initialize database**
   ```bash
   python -c "import database; database.init_db()"
   ```

## Usage

### Start the Backend Agent

```bash
cd backend
.\venv\Scripts\python main.py dev
```

### Start the Token Server (separate terminal)

```bash
cd backend
python token_server.py
```

### Start the Frontend

```bash
cd frontend-improved
python -m http.server 8000
```

Open `http://localhost:8000` in your browser.

## Configuration

### Recommended Model for Production

Edit `.env`:
```bash
GROQ_MODEL=llama-3.1-8b-instant
```

This model is:
- ✅ Faster (2-3x)
- ✅ Lower rate limits
- ✅ Still very capable
- ⚠️ Large model (llama-3.3-70b) hits rate limits quickly on free tier

## Project Structure

```
cooking-voice-ai-agent/
├── backend/
│   ├── main.py                 # LiveKit agent entrypoint
│   ├── token_server.py         # Token generation server
│   ├── database.py             # PostgreSQL operations
│   ├── google_sheets.py        # Sheets sync
│   ├── prompts.py              # System prompts
│   ├── tools.py                # Function schemas
│   └── orchestrator.py         # Console mode (testing)
├── frontend-improved/
│   ├── index.html              # Landing + app UI
│   ├── app.js                  # LiveKit client logic
│   └── styles.css              # Styling
├── database/
│   └── schema.sql              # Database schema
├── .env.example                # Environment template
├── .gitignore
└── README.md
```

## Common Issues

### Issue: Recipe saves twice
**Cause**: Multiple backend processes running  
**Fix**: Stop all processes and run only ONE `python main.py dev`

### Issue: Rate limit errors
**Cause**: Groq free tier limits (100k tokens/day)  
**Fix**: Switch to `llama-3.1-8b-instant` model in `.env`

### Issue: Voice delay/cutting off
**Cause**: API rate limiting or network latency  
**Fix**: See `voice_delay_troubleshooting.md` in docs

## Development

### Run in Console Mode (no voice)
```bash
python orchestrator.py
```

### View Database
```sql
psql $DATABASE_URL
SELECT * FROM batch_recipes WHERE chef_id = 'mock_user';
```

### Test Token Server
```bash
curl -X POST http://localhost:5000/get-token \
  -H "Content-Type: application/json" \
  -d '{"room":"test-room","identity":"test-user"}'
```

## Deployment

### Important: Before Deploying

1. **Never commit `.env`** - it contains sensitive API keys
2. **Never commit `*.json`** - Google credentials
3. **Use `.env.example`** as template for production

### Deploy to Production

See `DEPLOYMENT.md` for instructions on deploying to:
- LiveKit Cloud
- Fly.io
- Docker
- Kubernetes

## API Reference

### Voice Commands

- **"Create a batch recipe called [name]"** - Start new batch recipe
- **"Create a plate recipe called [name]"** - Start new plate recipe
- **"Search for [recipe name]"** - Find recipes
- **"Show me recipe [name]"** - Get recipe details
- **"List my recipes"** - Get all recipes

### Environment Variables

See `.env.example` for full list.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file

## Acknowledgments

- LiveKit for real-time infrastructure
- Deepgram for speech recognition
- Cartesia for natural TTS
- Groq for fast LLM inference

## Support

For issues and questions:
- GitHub Issues: [Link]
- Documentation: [Link]

---

Built with ❤️ by [Your Name]
