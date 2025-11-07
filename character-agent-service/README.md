# Character Agent Service

AI characters with distinct personalities for collaborative world-building in Ashiorid AI Manager.

## Features

- **Character Personalities**: Pre-defined characters (Gandalf, Paul Atreides, Master Chief)
- **Lore Integration**: Queries lore-rag-service for relevant context
- **Conversation History**: PostgreSQL-backed conversation storage
- **Multi-turn Conversations**: Maintains context across messages
- **Custom Characters**: Create new characters via API

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ashiorid

# Run service
uvicorn src.main:app --reload --port 8003
```

## API Endpoints

### List Characters
```bash
GET /characters
```

### Chat with Character
```bash
POST /characters/gandalf/chat
{
  "character_name": "gandalf",
  "message": "What should we do about the ring?",
  "context": []
}
```

### Create Character
```bash
POST /characters
{
  "name": "New Character",
  "description": "Description",
  "system_prompt": "You are...",
  "traits": {"wisdom": 10}
}
```

## Pre-defined Characters

- **Gandalf the Grey** - Wise wizard from Middle-earth (LOTR)
- **Paul Atreides** - The Kwisatz Haderach from Dune
- **Master Chief** - SPARTAN-II supersoldier from Halo

## Configuration

Edit `config.yaml` to customize:
- Character personalities
- LLM settings (model, temperature)
- Conversation history limits
- Service endpoints

## License

MIT License
