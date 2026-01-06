"""
Chef Voice AI Agent - Main Entry Point
Uses LiveKit Agents 1.3+ with AgentSession and function_tool pattern
Groq LLM for intelligent conversation
"""
import logging
import os
from typing import Any
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, AutoSubscribe, RunContext, function_tool, room_io
from livekit.plugins import deepgram, cartesia, silero, groq, noise_cancellation

import database as db
import google_sheets
from prompts import SYSTEM_PROMPT

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
logger.info("Initializing database...")
db.init_db()
logger.info("Database ready")

# Initialize Google Sheets (non-blocking - agent works even if Sheets fails)
logger.info("Initializing Google Sheets...")
if google_sheets.init_sheets():
    logger.info("Google Sheets ready - real-time sync enabled")
else:
    logger.warning("Google Sheets not available - recipes will only save to database")


def serialize_for_json(obj):
    """
    Convert Python objects to JSON-serializable types.
    Handles: Decimal -> float, UUID -> str, datetime -> str, RealDictRow -> dict
    This is critical for function_tool returns to work with LiveKit/Groq.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, 'items') and not isinstance(obj, dict):  # RealDictRow
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj


class ChefAssistant(Agent):
    """Chef AI Voice Assistant with function tools for recipe operations"""
    
    def __init__(self, chef_id: str):
        super().__init__(instructions=SYSTEM_PROMPT)
        self.chef_id = chef_id
        logger.info(f"Chef Assistant initialized for: {chef_id}")
    
    @function_tool()
    async def save_plate_recipe(
        self, 
        context: RunContext,
        name: str,
        serves: int,
        description: str = "",
        plating_instructions: str = "",
        presentation_notes: str = "",
        category: str = "",
        cuisine: str = "",
        ingredients: list = None
    ) -> dict[str, Any]:
        """Save a complete plate recipe (final dish) to the database. 
        Call this when the chef confirms the recipe is ready to save.
        
        Args:
            name: Name of the dish
            serves: Number of servings
            description: Brief description of the dish
            plating_instructions: How to plate the dish
            presentation_notes: Notes on presentation (spiciness, temperature, etc)
            category: Category like main, appetizer, dessert
            cuisine: Cuisine type like Indian, Italian
            ingredients: List of ingredients with name, quantity, unit
        """
        try:
            logger.info(f"SAVING PLATE RECIPE: {name}")
            
            recipe_id = db.save_plate_recipe(
                chef_id=self.chef_id,
                name=name,
                serves=serves,
                description=description,
                plating_instructions=plating_instructions,
                presentation_notes=presentation_notes,
                category=category,
                cuisine=cuisine,
                ingredients=ingredients,
                is_complete=True
            )
            
            logger.info(f"SAVED to database with ID: {recipe_id}")
            
            return {
                "success": True,
                "recipe_id": str(recipe_id),
                "message": f"Successfully saved '{name}' to your recipe library"
            }
            
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save recipe: {e}"
            }
    
    @function_tool()
    async def save_batch_recipe(
        self,
        context: RunContext,
        name: str,
        yield_quantity: float,
        yield_unit: str,
        description: str = "",
        instructions: str = "",
        temperature: float = None,
        temperature_unit: str = "C",
        ingredients: list = None
    ) -> dict[str, Any]:
        """Save a batch recipe (sauce, stock, base component) to the database.
        
        Args:
            name: Name of the batch recipe
            yield_quantity: How much it yields
            yield_unit: Unit (kg, liters, etc)
            description: Brief description
            instructions: Cooking instructions
            temperature: Cooking temperature
            temperature_unit: C or F
            ingredients: List of ingredients with name, quantity, unit
        """
        try:
            logger.info(f"SAVING BATCH RECIPE: {name}")
            
            recipe_id = db.save_batch_recipe(
                chef_id=self.chef_id,
                name=name,
                yield_quantity=yield_quantity,
                yield_unit=yield_unit,
                description=description,
                instructions=instructions,
                temperature=temperature,
                temperature_unit=temperature_unit,
                ingredients=ingredients,
                is_complete=True
            )
            
            logger.info(f"SAVED to database with ID: {recipe_id}")
            
            return {
                "success": True,
                "recipe_id": str(recipe_id),
                "message": f"Successfully saved '{name}' to your batch library"
            }
            
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save batch recipe: {e}"
            }
    
    @function_tool()
    async def search_recipes(
        self,
        context: RunContext,
        query: str,
        recipe_type: str = "both"
    ) -> str:
        """Search for recipes by name in the chef's library.
        
        Args:
            query: Search term - the recipe name or keywords
            recipe_type: Type to search - batch, plate, or both
        
        Returns:
            A formatted string describing the search results that you should speak to the chef.
        """
        try:
            logger.info(f"SEARCHING: '{query}' for chef: {self.chef_id}")
            
            results = db.smart_search_recipes(
                chef_id=self.chef_id,
                query=query
            )
            
            # Check for exact or best match
            if results.get('exact_match') or results.get('best_match'):
                recipe = serialize_for_json(results.get('recipe', {}))
                found_type = results.get('recipe_type', 'unknown')
                recipe_name = recipe.get('name', query)
                
                logger.info(f"Found match: {recipe_name} ({found_type})")
                
                # Build a concise speakable response
                description = recipe.get('description', '')
                serves = recipe.get('serves')
                cuisine = recipe.get('cuisine', '')
                
                # Keep it short and clear
                result = f"Found {recipe_name}."
                if description:
                    result += f" {description}."
                if serves:
                    result += f" Serves {serves}."
                if cuisine:
                    result += f" {cuisine} cuisine."
                    
                # List just first 3 ingredients briefly
                ingredients = recipe.get('ingredients', [])
                if ingredients:
                    ing_names = [ing.get('name', '') for ing in ingredients[:3] if ing.get('name')]
                    if ing_names:
                        result += f" Ingredients: {', '.join(ing_names)}."
                
                return result
            
            total = results.get('total_found', 0)
            batch_matches = serialize_for_json(results.get('batch_recipes', []))
            plate_matches = serialize_for_json(results.get('plate_recipes', []))
            
            if total == 0:
                all_recipes = db.list_chef_recipes(self.chef_id)
                available = [r.get('name') for r in all_recipes.get('batch_recipes', [])] + \
                           [r.get('name') for r in all_recipes.get('plate_recipes', [])]
                
                if available:
                    sample = ", ".join(available[:5])
                    return f"I couldn't find any recipes matching '{query}'. You have recipes like {sample}. Would you like to search for one of those instead?"
                else:
                    return f"I couldn't find any recipes matching '{query}', and you don't have any saved recipes yet. Would you like to save a new recipe?"
            
            elif total == 1:
                # Single match found in keyword search - get full details
                if batch_matches:
                    recipe = serialize_for_json(db.get_recipe_by_name(self.chef_id, batch_matches[0]['name'], 'batch'))
                    recipe_name = recipe.get('name', query)
                    return f"I found one batch recipe: {recipe_name}. Would you like me to give you the details?"
                else:
                    recipe = serialize_for_json(db.get_recipe_by_name(self.chef_id, plate_matches[0]['name'], 'plate'))
                    recipe_name = recipe.get('name', query)
                    return f"I found one plate recipe: {recipe_name}. Would you like me to give you the details?"
            
            else:
                # Multiple matches
                batch_names = [r['name'] for r in batch_matches]
                plate_names = [r['name'] for r in plate_matches]
                all_names = batch_names + plate_names
                names_text = ", ".join(all_names[:5])
                if len(all_names) > 5:
                    names_text += f", and {len(all_names) - 5} more"
                
                return f"I found {total} recipes matching '{query}': {names_text}. Which one would you like me to look up?"
                
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return f"I had trouble searching for that recipe. Could you try again or rephrase your request?"

    
    @function_tool()
    async def list_recipes(
        self, 
        context: RunContext,
        include_details: bool = False
    ) -> str:
        """List all recipes saved by the chef.
        
        Args:
            include_details: If True, include full recipe details (not implemented yet)
        
        Returns:
            A formatted string listing the chef's recipes that you should speak.
        """
        try:
            logger.info(f"LISTING RECIPES for chef: {self.chef_id}")
            
            recipes = db.list_chef_recipes(self.chef_id)
            
            batch_recipes = recipes.get('batch_recipes', [])
            plate_recipes = recipes.get('plate_recipes', [])
            batch_count = len(batch_recipes)
            plate_count = len(plate_recipes)
            total = batch_count + plate_count
            
            logger.info(f"Found {batch_count} batch + {plate_count} plate recipes")
            
            if total == 0:
                return "You don't have any saved recipes yet. Would you like to save a new recipe?"
            
            response_parts = [f"You have {total} recipes saved."]
            
            if plate_count > 0:
                plate_names = [r.get('name') for r in plate_recipes[:5]]
                plate_text = ", ".join(plate_names)
                if plate_count > 5:
                    plate_text += f", and {plate_count - 5} more"
                response_parts.append(f"Plate recipes include: {plate_text}.")
            
            if batch_count > 0:
                batch_names = [r.get('name') for r in batch_recipes[:5]]
                batch_text = ", ".join(batch_names)
                if batch_count > 5:
                    batch_text += f", and {batch_count - 5} more"
                response_parts.append(f"Batch recipes include: {batch_text}.")
            
            response_parts.append("Would you like me to search for a specific recipe?")
            
            return " ".join(response_parts)
            
        except Exception as e:
            logger.error(f"List error: {e}")
            return "I had trouble listing your recipes. Could you try again?"

    
    @function_tool()
    async def update_recipe(
        self,
        context: RunContext,
        recipe_name: str,
        new_name: str = "",
        new_description: str = "",
        new_serves: int = 0,
        new_cuisine: str = "",
        recipe_type: str = "plate"
    ) -> str:
        """Update an existing recipe's information like name, description, or serves.
        
        Args:
            recipe_name: The current name of the recipe to update
            new_name: New name for the recipe (leave empty to keep current)
            new_description: New description (leave empty to keep current)
            new_serves: New number of servings, use 0 to keep current (for plate recipes)
            new_cuisine: New cuisine type (leave empty to keep current)
            recipe_type: Type of recipe - 'plate' or 'batch'
        
        Returns:
            A message confirming the update or explaining any errors.
        """
        try:
            logger.info(f"UPDATING RECIPE: '{recipe_name}' for chef: {self.chef_id}")
            
            # Convert empty values to None for the database function
            result = db.update_recipe(
                chef_id=self.chef_id,
                recipe_name=recipe_name,
                recipe_type=recipe_type,
                new_name=new_name if new_name else None,
                new_description=new_description if new_description else None,
                new_serves=new_serves if new_serves > 0 else None,
                new_cuisine=new_cuisine if new_cuisine else None
            )
            
            if result.get('success'):
                return f"Done! {result.get('message')}."
            else:
                return f"Sorry, I couldn't update the recipe: {result.get('message')}"
                
        except Exception as e:
            logger.error(f"Update error: {e}", exc_info=True)
            return "I had trouble updating the recipe. Could you try again?"

    
    @function_tool()
    async def delete_recipe(
        self,
        context: RunContext,
        recipe_name: str,
        recipe_type: str = "plate"
    ) -> str:
        """Delete a recipe from the chef's library permanently.
        
        Args:
            recipe_name: The name of the recipe to delete
            recipe_type: Type of recipe - 'plate' or 'batch'
        
        Returns:
            A message confirming the deletion or explaining any errors.
        """
        try:
            logger.info(f"DELETING RECIPE: '{recipe_name}' for chef: {self.chef_id}")
            
            result = db.delete_recipe(
                chef_id=self.chef_id,
                recipe_name=recipe_name,
                recipe_type=recipe_type
            )
            
            if result.get('success'):
                return f"Done! {result.get('message')}. This has been permanently removed from your library and the spreadsheet."
            else:
                return f"Sorry, I couldn't delete the recipe: {result.get('message')}"
                
        except Exception as e:
            logger.error(f"Delete error: {e}", exc_info=True)
            return "I had trouble deleting the recipe. Could you try again?"


# Create server instance
server = AgentServer()


@server.rtc_session()
async def chef_agent(ctx: agents.JobContext):
    """Main agent session handler"""
    
    logger.info("=" * 60)
    logger.info("NEW SESSION STARTED")
    logger.info("=" * 60)
    logger.info(f"Room: {ctx.room.name}")
    
    # Wait for participant
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    participant = await ctx.wait_for_participant()
    
    # Use fixed chef_id 'mock_user' so all sessions access the same recipe database
    chef_id = 'mock_user'
    logger.info(f"Participant {participant.identity} joined, using chef_id: {chef_id}")
    
    # Create assistant with chef ID for database context
    assistant = ChefAssistant(chef_id)
    
    # Use Groq's Llama 3.3 70B model with low temperature for more deterministic responses
    groq_model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    
    # Create session with STT/TTS/LLM
    logger.info("Setting up STT/TTS/LLM...")
    session = AgentSession(
        stt=deepgram.STT(model="nova-2-general", language="en"),
        llm=groq.LLM(model=groq_model, temperature=0.3),
        tts=cartesia.TTS(voice="d46abd1d-2d02-43e8-819f-51fb652c1c61"),  # Newsman voice
        vad=silero.VAD.load(),
    )
    
    # Start session with noise cancellation to prevent echo
    logger.info("Starting session with noise cancellation...")
    await session.start(
        room=ctx.room,
        agent=assistant,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Use noise cancellation - BVC for web, BVCTelephony for SIP
                noise_cancellation=lambda params: 
                    noise_cancellation.BVCTelephony() 
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP 
                    else noise_cancellation.BVC(),
            ),
        ),
    )
    
    logger.info("Session started")
    
    # Send greeting
    logger.info("Sending greeting...")
    await session.generate_reply(
        instructions="Greet the chef warmly. Introduce yourself as Tullia (pronounce it as 'Too-lee-ah'), their chef assistant who can help them document recipes as they cook, or retrieve recipes they've saved. Ask what they'd like to do today. Keep it brief and conversational."
    )
    
    logger.info("Greeting sent - listening for chef...")



def run_agent_production():
    """Run agent in production mode (for Railway)"""
    import sys
    
    required_vars = ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET',
                     'DEEPGRAM_API_KEY', 'CARTESIA_API_KEY', 'GROQ_API_KEY', 'DATABASE_URL']
    
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        exit(1)
    
    logger.info("=" * 60)
    logger.info("   Chef Voice AI Agent - PRODUCTION")
    logger.info("=" * 60)
    logger.info(f"LiveKit: {os.getenv('LIVEKIT_URL')}")
    logger.info("STT: Deepgram Nova-2")
    logger.info("TTS: Cartesia Sonic-3 (Newsman)")
    logger.info(f"LLM: Groq {os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')} (temp=0.3)")
    logger.info("Turn Detection: Multilingual Model")
    logger.info("Noise Cancellation: BVC")
    logger.info("Agent ready - waiting for connections...")
    
    # Inject 'start' command for CLI
    sys.argv = ['main.py', 'start']
    agents.cli.run_app(server)



if __name__ == "__main__":
    # Development mode
    required_vars = ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET',
                     'DEEPGRAM_API_KEY', 'CARTESIA_API_KEY', 'GROQ_API_KEY', 'DATABASE_URL']
    
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        exit(1)
    
    logger.info("=" * 60)
    logger.info("   Chef Voice AI Agent")
    logger.info("=" * 60)
    logger.info(f"LiveKit: {os.getenv('LIVEKIT_URL')}")
    logger.info("STT: Deepgram Nova-2")
    logger.info("TTS: Cartesia Sonic-3 (Newsman)")
    logger.info(f"LLM: Groq {os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')} (temp=0.3)")
    logger.info("Turn Detection: Multilingual Model")
    logger.info("Noise Cancellation: BVC (Background Voice Cancellation)")
    logger.info("Agent ready - waiting for connections...")
    
    # Run the agent server
    agents.cli.run_app(server)
