# Chatbot Assistant with RAG and Voice AI

AI-powered chatbot assistant with Retrieval-Augmented Generation (RAG) and voice support using Groq and ElevenLabs.

## Features

- 🤖 **Intelligent Chatbot**: Powered by Groq's llama-3.3-70b-versatile model
- 🔍 **RAG (Retrieval-Augmented Generation)**: Semantic search over user's tasks, meetings, and notifications
- 🎤 **Voice Input**: Speech-to-text using Groq Whisper
- 🔊 **Voice Output**: Text-to-speech using ElevenLabs (optional)
- 💬 **Conversation History**: Persistent chat sessions with context
- 🔒 **Privacy**: User-isolated data with secure authentication
- ⚡ **Streaming**: Real-time response streaming with Server-Sent Events

## Architecture

```
User Input (Text/Voice)
         ↓
   API Endpoints
         ↓
   ┌─────────────────┐
   │ Voice AI Service│ (if voice input)
   │  - Transcribe   │
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │ Chatbot Service │
   │  - RAG Pipeline │
   │  - Vector Store │
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │  Groq LLM API   │
   │  (Streaming)    │
   └────────┬────────┘
            ↓
   Response (Text/Stream)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `groq` - Groq API client
- `chromadb` - Vector database
- `sentence-transformers` - Local embeddings
- `elevenlabs` - Text-to-speech (optional)

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Groq API (Required)
GROQ_API_KEY=your-groq-api-key-here
GROQ_API_KEY_TWO=your-second-groq-key-for-voice  # Or use same key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=1.0
GROQ_MAX_TOKENS=1024

# ElevenLabs (Optional - for TTS)
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL

# Embeddings (Local - No API key needed)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Vector Store
VECTOR_STORE_PATH=./data/vectors

# Voice AI
VOICE_AI_ENABLED=true
VOICE_TRANSCRIPTION_MODEL=whisper-large-v3
VOICE_MAX_AUDIO_SIZE=25
```

### 3. Initialize Database

```bash
python init_chatbot_db.py
```

This creates the required database tables:
- `chatbot_sessions` - Conversation sessions
- `chatbot_messages` - Chat messages

### 4. Index User Data

Before using the chatbot, index your user data:

```bash
POST /api/chatbot/index
```

This indexes tasks, meetings, and notifications into the vector store for semantic search.

## API Endpoints

### Send Message

```http
POST /api/chatbot/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "What tasks do I have today?",
  "session_id": "optional-session-id",
  "stream": false
}
```

Response:
```json
{
  "success": true,
  "response": "You have 3 tasks today: ...",
  "session_id": "uuid",
  "sources": [
    {
      "type": "task",
      "title": "Task title",
      "id": "task-id"
    }
  ]
}
```

### Send Voice Message

```http
POST /api/chatbot/voice
Authorization: Bearer <token>
Content-Type: multipart/form-data

audio: <audio-file>
session_id: optional-session-id
include_audio_response: false
```

Response:
```json
{
  "success": true,
  "transcription": "What tasks do I have today?",
  "response": "You have 3 tasks today: ...",
  "session_id": "uuid",
  "sources": [...],
  "audio_response": "base64-encoded-audio"  // if requested
}
```

### Get Conversation History

```http
GET /api/chatbot/history?session_id=<session-id>&limit=50
Authorization: Bearer <token>
```

### Clear Conversation

```http
DELETE /api/chatbot/history
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "optional-session-id"
}
```

### Get Sessions

```http
GET /api/chatbot/sessions?limit=10
Authorization: Bearer <token>
```

### Index User Data

```http
POST /api/chatbot/index
Authorization: Bearer <token>
```

## Components

### LLM Service (`llm.py`)
- Groq API integration
- Streaming and non-streaming generation
- Local embeddings with sentence-transformers

### Voice AI Service (`voice.py`)
- Groq Whisper for transcription
- ElevenLabs for text-to-speech
- End-to-end voice processing

### Vector Store (`vector_store.py`)
- ChromaDB for semantic search
- User-isolated collections
- Document management (add, update, delete)

### Conversation Manager (`conversation.py`)
- Session management
- Message history
- Database persistence

### Data Indexer (`indexer.py`)
- Index tasks, meetings, notifications
- Batch embedding generation
- Incremental updates

### Chatbot Service (`service.py`)
- Main orchestration layer
- RAG pipeline
- Context building

## Usage Examples

### Python Client

```python
import requests

# Send message
response = requests.post(
    'http://localhost:5000/api/chatbot/message',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'message': 'Show me my high priority tasks',
        'stream': False
    }
)

print(response.json()['response'])
```

### Streaming Response

```python
import requests

response = requests.post(
    'http://localhost:5000/api/chatbot/message',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'message': 'Summarize my meetings',
        'stream': True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8').replace('data: ', ''))
        if 'chunk' in data:
            print(data['chunk'], end='', flush=True)
```

### Voice Input

```python
import requests

with open('audio.mp3', 'rb') as audio_file:
    response = requests.post(
        'http://localhost:5000/api/chatbot/voice',
        headers={'Authorization': f'Bearer {token}'},
        files={'audio': audio_file},
        data={'include_audio_response': 'true'}
    )

print(response.json()['transcription'])
print(response.json()['response'])
```

## Performance

- **Response Time**: ~1-3 seconds (depending on context size)
- **Streaming**: Real-time token generation
- **Vector Search**: <100ms for semantic search
- **Embeddings**: ~50ms per document (local)
- **Voice Transcription**: ~2-5 seconds (Groq Whisper)

## Privacy & Security

- ✅ User-isolated vector stores
- ✅ Authentication required for all endpoints
- ✅ No data sharing between users
- ✅ Conversation history per user
- ✅ Secure API key management

## Troubleshooting

### Model Download Issues
First run downloads sentence-transformers model (~90MB):
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Vector Store Errors
Clear and reinitialize:
```bash
rm -rf ./data/vectors
POST /api/chatbot/index
```

### Voice Transcription Fails
Check audio file:
- Max size: 25MB
- Supported formats: mp3, wav, m4a, webm
- Groq API key is valid

### No Context in Responses
Index user data first:
```bash
POST /api/chatbot/index
```

## Development

### Run Tests
```bash
pytest backend/chatbot/tests/
```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Monitor Vector Store
```python
from chatbot.vector_store import VectorStore

store = VectorStore(user_id)
print(f"Documents: {store.get_document_count()}")
```

## Roadmap

- [ ] Multi-language support
- [ ] Custom voice selection
- [ ] Action execution (create/update tasks)
- [ ] Meeting scheduling
- [ ] Export conversations
- [ ] Analytics dashboard

## License

MIT License - See LICENSE file for details
