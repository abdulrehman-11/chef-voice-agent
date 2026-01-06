"""
Simplified Voice Agent Server - No LiveKit Cloud Required
Direct WebSocket connection for voice streaming
"""
import asyncio
import json
import logging
import os
import base64
from typing import Optional
from dotenv import load_dotenv

from quart import Quart, websocket, request
from quart_cors import cors

import database as db
from prompts import SYSTEM_PROMPT

# Audio processing
import io
import wave

# Groq for LLM
from groq import Groq

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize
db.init_db()
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Create Quart app
app = Quart(__name__)
app = cors(app, allow_origin="*")

# Groq tools definition
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_plate_recipe",
            "description": "Save a plate recipe",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "serves": {"type": "integer"},
                    "description": {"type": "string"},
                    "cuisine": {"type": "string"},
                    "ingredients": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["name", "serves"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_recipes",
            "description": "Search recipes",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]


class VoiceSession:
    def __init__(self, chef_id: str):
        self.chef_id = chef_id
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
    async def process_audio(self, audio_data: bytes) -> Optional[str]:
        """Process audio through STT -> LLM -> TTS"""
        try:
            # 1. Speech-to-Text (using Deepgram or Groq Whisper)
            # For now, simulate - you'd integrate real STT here
            user_text = await self.speech_to_text(audio_data)
            if not user_text:
                return None
                
            logger.info(f"User said: {user_text}")
            
            # 2. LLM Processing
            self.messages.append({"role": "user", "content": user_text})
            
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.messages,
                tools=GROQ_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message
            
            # Handle function calls
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    # Execute function
                    result = await self.execute_function(func_name, func_args)
                    
                    # Add to messages
                    self.messages.append({
                        "role": "assistant",
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": tool_call.function.arguments
                            }
                        }]
                    })
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                
                # Get final response
                final_response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=self.messages,
                    temperature=0.3,
                    max_tokens=500
                )
                response_text = final_response.choices[0].message.content
            else:
                response_text = assistant_message.content
                
            self.messages.append({"role": "assistant", "content": response_text})
            logger.info(f"Assistant: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            return "I'm sorry, I had trouble processing that."
    
    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """Convert speech to text using Groq Whisper"""
        try:
            # Create a WAV file in memory
            # Note: You may need to adjust format based on frontend audio
            
            # For now, return None to indicate we need proper STT integration
            # TODO: Integrate Deepgram or Groq Whisper properly
            logger.warning("STT not yet integrated - using mock")
            return None
            
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None
    
    async def execute_function(self, func_name: str, args: dict) -> dict:
        """Execute database function"""
        try:
            if func_name == "save_plate_recipe":
                recipe_id = db.save_plate_recipe(
                    chef_id=self.chef_id,
                    name=args.get("name"),
                    serves=args.get("serves"),
                    description=args.get("description", ""),
                    cuisine=args.get("cuisine", ""),
                    ingredients=args.get("ingredients", []),
                    is_complete=True
                )
                return {
                    "success": True,
                    "recipe_id": str(recipe_id),
                    "message": f"Saved {args.get('name')}"
                }
            
            elif func_name == "search_recipes":
                results = db.smart_search_recipes(
                    chef_id=self.chef_id,
                    query=args.get("query")
                )
                return results
            
            return {"success": False, "message": "Unknown function"}
            
        except Exception as e:
            logger.error(f"Function execution error: {e}")
            return {"success": False, "message": str(e)}


@app.websocket('/ws/voice')
async def voice_websocket():
    """WebSocket endpoint for voice communication"""
    chef_id = f"chef-{os.urandom(4).hex()}"
    session = VoiceSession(chef_id)
    
    logger.info(f"New voice session: {chef_id}")
    
    # Send greeting
    await websocket.send_json({
        "type": "message",
        "role": "assistant",
        "text": "Hello! I'm Tullia, your chef assistant. I can help you document recipes. What would you like to do today?"
    })
    
    try:
        while True:
            data = await websocket.receive()
            
            # Handle different message types
            if isinstance(data, bytes):
                # Audio data
                response_text = await session.process_audio(data)
                if response_text:
                    await websocket.send_json({
                        "type": "message",
                        "role": "assistant",
                        "text": response_text
                    })
            
            elif isinstance(data, str):
                # JSON message
                try:
                    msg = json.loads(data)
                    
                    if msg.get("type") == "text":
                        # Text message from user
                        user_text = msg.get("text")
                        session.messages.append({"role": "user", "content": user_text})
                        
                        # Process with LLM
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=session.messages,
                            tools=GROQ_TOOLS,
                            tool_choice="auto",
                            temperature=0.3,
                            max_tokens=500
                        )
                        
                        response_text = response.choices[0].message.content
                        session.messages.append({"role": "assistant", "content": response_text})
                        
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "text": response_text
                        })
                
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
    
    except asyncio.CancelledError:
        logger.info(f"Session closed: {chef_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


@app.route('/health')
async def health():
    """Health check"""
    return {"status": "ok", "service": "Simple Voice Agent"}


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("   Simple Voice Agent Server")
    logger.info("=" * 60)
    logger.info("🌐 WebSocket: ws://localhost:3000/ws/voice")
    logger.info("❤️  Health: http://localhost:3000/health")
    logger.info("=" * 60)
    
    app.run(host="0.0.0.0", port=3000, debug=True)
