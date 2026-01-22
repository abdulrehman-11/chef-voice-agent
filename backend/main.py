"""
Chef Voice AI Agent - Main Entry Point
Uses LiveKit Agents 1.3+ with AgentSession and function_tool pattern
Mistral AI LLM for intelligent conversation
"""
import logging
import os
from typing import Any, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, AutoSubscribe, RunContext, function_tool, room_io
from livekit.plugins import deepgram, cartesia, silero, mistralai, noise_cancellation

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


def clean_text_for_tts(text: str) -> str:
    """
    Clean LLM-generated text before sending to TTS.
    Removes markdown formatting that TTS would speak literally.
    """
    import re
    
    # Remove pronunciation guides: *Too-lee-ah* → Too-lee-ah
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Remove bold markdown: **word** → word  
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Remove remaining asterisks
    text = text.replace('*', '')
    
    # Remove backticks: `code` → code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove underscores for italic: _word_ → word
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    return text.strip()


class ChefAssistant(Agent):
    """Chef AI Voice Assistant with function tools for recipe operations"""
    
    def __init__(self, chef_id: str):
        super().__init__(instructions=SYSTEM_PROMPT)
        self.chef_id = chef_id
        self._room = None  # Will be set by session
        
        # Temporary state for recipe being built in real-time
        self._current_recipe = {
            'name': None,
            'recipe_type': None,  # 'plate' or 'batch'
            'description': '',
            'serves': None,
            'yield_quantity': None,
            'yield_unit': None,
            'cuisine': '',
            'category': '',
            'temperature': None,
            'temperature_unit': 'C',
            'ingredients': [],
            'instructions': [],
            'plating_instructions': '',
            'presentation_notes': '',
        }
        
        logger.info(f"Chef Assistant initialized for: {chef_id}")
    
    async def send_recipe_event(self, event_type: str, data: dict):
        """Send recipe update events to frontend via LiveKit data channel.
        
        This enables real-time UI updates as the recipe is being built.
        
        Args:
            event_type: Type of event (recipe_start, field_update, ingredient_add, recipe_save)
            data: Event data to send to frontend
        """
        if not self._room:
            logger.warning("Room not set, cannot send recipe event")
            return
        
        try:
            import json
            event_payload = {
                "type": "recipe_event",
                "event": event_type,
                "timestamp": datetime.now().isoformat(),
                **data
            }
            message = json.dumps(event_payload)
            
            # Send to all participants via data channel
            await self._room.local_participant.publish_data(
                message.encode('utf-8'),
                reliable=True
            )
            # Enhanced logging to show full payload
            logger.info(f"📤 Sent recipe event: {event_type}")
            logger.debug(f"   📦 Event payload: {event_payload}")
        except Exception as e:
            logger.error(f"Failed to send recipe event: {e}")
    

# ============ INTERMEDIATE FUNCTION TOOLS FOR LIVE RECIPE BUILDING ============
    @function_tool()
    async def start_recipe(
        self,
        context: RunContext,
        name: str,
        recipe_type: str,
        description: str = "",
        serves: Optional[int] = None,
        cuisine: Optional[str] = None,
        category: Optional[str] = None
    ) -> str:
        """Start building a new recipe in real-time.
        
        Call this function AS SOON AS the chef mentions they're making a recipe.
        This initializes the recipe and shows it in the live recipe builder UI.
        
        Args:
            name: Name of the recipe (e.g., "Chicken Biryani")
            recipe_type: Type of recipe - must be either "plate" or "batch"
            description: Optional brief description of the dish
            serves: Number of servings (for plate recipes) - EXTRACT THIS if mentioned!
            cuisine: Type of cuisine (e.g., "Italian", "Chinese") - EXTRACT THIS if mentioned!
            category: Category (e.g., "main", "appetizer") - EXTRACT THIS if mentioned!
            
        Returns:
            Confirmation message
        """
        try:
            logger.info(f"🆕 STARTING RECIPE: {name} ({recipe_type})")
            logger.info(f"   📝 Initial metadata - Serves: {serves}, Cuisine: {cuisine}, Category: {category}")
            
            # Initialize/reset current recipe state
            self._current_recipe = {
                'name': name,
                'recipe_type': recipe_type.lower(),
                'description': description,
                'serves': serves,  # NOW can be set from the start!
                'yield_quantity': None,
                'yield_unit': None,
                'cuisine': cuisine or '',  # NOW can be set from the start!
                'category': category or '',  # NOW can be set from the start!
                'temperature': None,
                'temperature_unit': 'C',
                'ingredients': [],
                'instructions': [],
                'plating_instructions': '',
                'presentation_notes': '',
            }
            
            
            # Send recipe_start event to frontend with initial metadata
            await self.send_recipe_event("recipe_start", {
                "recipe_type": recipe_type.lower(),
                "name": name,
                "description": description,
                # Include initial metadata - NOW these can have values from the start!
                "serves": serves,
                "yield_quantity": self._current_recipe.get('yield_quantity'),
                "yield_unit": self._current_recipe.get('yield_unit'),
                "cuisine": cuisine or '',
                "category": category or ''
            })
            
            return f"Got it! Starting to build {name}. I'll track the details as you describe them."
            
        except Exception as e:
            logger.error(f"Error starting recipe: {e}", exc_info=True)
            return f"I had trouble starting the recipe. Could you try again?"
    @function_tool()
    async def update_recipe_metadata(
        self,
        context: RunContext,
        serves: int = None,
        yield_quantity: float = None,
        yield_unit: str = None,
        cuisine: str = None,
        category: str = None,
        temperature: float = None,
        temperature_unit: str = None,
        description: str = None
    ) -> str:
        """Update metadata for the recipe currently being built.
        
        Call this when the chef mentions serves, yield, cuisine, category, etc.
        Can be called multiple times to update different fields.
        
        Args:
            serves: Number of servings (for plate recipes)
            yield_quantity: Amount yielded (for batch recipes)
            yield_unit: Unit of yield (kg, liters, etc.)
            cuisine: Type of cuisine (Indian, Italian, etc.)
            category: Category (appetizer, main, dessert, etc.)
            temperature: Cooking/storage temperature
            temperature_unit: C or F
            description: Description of the dish
            
        Returns:
            Confirmation message
        """
        try:
            if not self._current_recipe.get('name'):
                return "No recipe in progress. Please start a recipe first by saying what you're making."
            
            # Update state
            updates = {}
            if serves is not None:
                self._current_recipe['serves'] = serves
                updates['serves'] = serves
            if yield_quantity is not None:
                self._current_recipe['yield_quantity'] = yield_quantity
                updates['yield_quantity'] = yield_quantity
            if yield_unit:
                self._current_recipe['yield_unit'] = yield_unit
                updates['yield_unit'] = yield_unit
            if cuisine:
                self._current_recipe['cuisine'] = cuisine
                updates['cuisine'] = cuisine
            if category:
                self._current_recipe['category'] = category
                updates['category'] = category
            if temperature is not None:
                self._current_recipe['temperature'] = temperature
                updates['temperature'] = temperature
            if temperature_unit:
                self._current_recipe['temperature_unit'] = temperature_unit
                updates['temperature_unit'] = temperature_unit
            if description:
                self._current_recipe['description'] = description
                updates['description'] = description
            
            # Enhanced logging to debug metadata flow
            logger.info(f"📝 update_recipe_metadata called with: serves={serves}, cuisine={cuisine}, category={category}, "
                       f"yield_quantity={yield_quantity}, yield_unit={yield_unit}, temperature={temperature}")
            logger.info(f"📝 UPDATED METADATA: {updates}")
            
            # Send metadata update event
            await self.send_recipe_event("recipe_metadata_update", {
                "recipe_type": self._current_recipe['recipe_type'],
                "name": self._current_recipe['name'],
                **updates
            })
            
            # Build response mentioning what was updated
            updated_fields = [f"{k}: {v}" for k, v in updates.items()]
            return f"Noted: {', '.join(updated_fields)}"
            
        except Exception as e:
            logger.error(f"Error updating metadata: {e}", exc_info=True)
            return "I had trouble updating that information."
    @function_tool()
    async def add_ingredient(
        self,
        context: RunContext,
        name: str,
        quantity: str = "",
        unit: str = ""
    ) -> str:
        """Add a single ingredient to the current recipe.
        
        IMPORTANT: Call this function ONCE for EACH ingredient mentioned.
        If the chef says "500g chicken, 300g rice, 2 onions" you should call this
        function THREE separate times (once for chicken, once for rice, once for onions).
        
        Args:
            name: Name of the ingredient (e.g., "chicken", "rice", "onions")
            quantity: Amount (e.g., "500", "2", "1/2")
            unit: Unit of measurement (e.g., "g", "kg", "cups", "tablespoons")
            
        Returns:
            Confirmation message
        """
        try:
            if not self._current_recipe.get('name'):
                return "No recipe in progress. Please start a recipe first."
            
            ingredient = {
                'name': name,
                'quantity': quantity,
                'unit': unit
            }
            
            self._current_recipe['ingredients'].append(ingredient)
            
            logger.info(f"🥗 ADDED INGREDIENT: {quantity} {unit} {name}")
            
            # Send ingredient add event
            await self.send_recipe_event("ingredient_add", {
                "recipe_type": self._current_recipe['recipe_type'],
                "name": self._current_recipe['name'],
                "ingredient": ingredient,
                "total_ingredients": len(self._current_recipe['ingredients'])
            })
            
            return f"Added {quantity} {unit} {name}"
            
        except Exception as e:
            logger.error(f"Error adding ingredient: {e}", exc_info=True)
            return "I had trouble adding that ingredient."
    @function_tool()
    async def add_instruction(
        self,
        context: RunContext,
        instruction: str
    ) -> str:
        """Add a cooking instruction or step to the current recipe.
        
        Call this when the chef describes cooking steps, techniques, or notes.
        Can be called multiple times for different steps.
        
        Args:
            instruction: The instruction text (e.g., "Marinate for 30 minutes")
            
        Returns:
            Confirmation message
        """
        try:
            if not self._current_recipe.get('name'):
                return "No recipe in progress. Please start a recipe first."
            
            self._current_recipe['instructions'].append(instruction)
            
            logger.info(f"📋 ADDED INSTRUCTION: {instruction[:50]}...")
            
            # Send instruction add event
            await self.send_recipe_event("instruction_add", {
                "recipe_type": self._current_recipe['recipe_type'],
                "name": self._current_recipe['name'],
                "instruction": instruction,
                "total_instructions": len(self._current_recipe['instructions'])
            })
            
            return f"Noted: {instruction}"
            
        except Exception as e:
            logger.error(f"Error adding instruction: {e}", exc_info=True)
            return "I had trouble adding that instruction."
    def clear_current_recipe(self):
        """Clear the current recipe state after saving"""
        self._current_recipe = {
            'name': None,
            'recipe_type': None,
            'description': '',
            'serves': None,
            'yield_quantity': None,
            'yield_unit': None,
            'cuisine': '',
            'category': '',
            'temperature': None,
            'temperature_unit': 'C',
            'ingredients': [],
            'instructions': [],
            'plating_instructions': '',
            'presentation_notes': '',
        }
        logger.info("🧹 Cleared current recipe state")
    # ============ END INTERMEDIATE TOOLS ============

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
            
            # Send recipe start event to frontend
            await self.send_recipe_event("recipe_saving", {
                "recipe_type": "plate",
                "name": name,
                "serves": serves,
                "description": description,
                "cuisine": cuisine,
                "category": category,
                "ingredients": ingredients or []
            })
            
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
            
            # Send success event to frontend
            await self.send_recipe_event("recipe_saved", {
                "recipe_type": "plate",
                "recipe_id": str(recipe_id),
                "name": name,
                "success": True
            })
            
            return {
                "success": True,
                "recipe_id": str(recipe_id),
                "message": f"Successfully saved '{name}' to your recipe library"
            }
            
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)
            
            # Send error event to frontend
            await self.send_recipe_event("recipe_error", {
                "recipe_type": "plate",
                "name": name,
                "error": str(e)
            })
            
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
            
            # Send recipe start event to frontend
            await self.send_recipe_event("recipe_saving", {
                "recipe_type": "batch",
                "name": name,
                "yield_quantity": yield_quantity,
                "yield_unit": yield_unit,
                "description": description,
                "temperature": temperature,
                "temperature_unit": temperature_unit,
                "ingredients": ingredients or []
            })
            
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
            
            # Send success event to frontend
            await self.send_recipe_event("recipe_saved", {
                "recipe_type": "batch",
                "recipe_id": str(recipe_id),
                "name": name,
                "success": True
            })
            
            return {
                "success": True,
                "recipe_id": str(recipe_id),
                "message": f"Successfully saved '{name}' to your batch library"
            }
            
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)
            
            # Send error event to frontend
            await self.send_recipe_event("recipe_error", {
                "recipe_type": "batch",
                "name": name,
                "error": str(e)
            })
            
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
    # Set room reference so assistant can send data channel events
    assistant._room = ctx.room
    logger.info("✅ Room reference set on assistant for data channel events")
    
    # Use Mistral AI's large model with low temperature for more deterministic responses
    mistral_model = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
    
    # Create session with STT/TTS/LLM
    logger.info("Setting up STT/TTS/LLM...")
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",  # Upgraded from nova-2 for 47% better accuracy
            language="en",
            smart_format=True,  # Auto punctuation & capitalization
            interim_results=True,  # Real-time transcription
            utterance_end_ms=1000,  # Better turn detection
            punctuate=True,  # Add punctuation
        ),
        llm=mistralai.LLM(model=mistral_model, temperature=0.3),
        tts=cartesia.TTS(voice="d46abd1d-2d02-43e8-819f-51fb652c1c61"),  # Newsman voice
        vad=silero.VAD.load(),
    )
    
    # Start session with noise cancellation to prevent echo
    logger.info("Starting session with noise cancellation...")
    await session.start(
        room=ctx.room,
        agent=assistant,
        before_tts_cb=lambda text: clean_text_for_tts(text),  # Clean markdown before TTS
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
                     'DEEPGRAM_API_KEY', 'CARTESIA_API_KEY', 'MISTRAL_API_KEY', 'DATABASE_URL']
    
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
    logger.info(f"LLM: Mistral AI {os.getenv('MISTRAL_MODEL', 'mistral-large-latest')} (temp=0.3)")
    logger.info("Turn Detection: Multilingual Model")
    logger.info("Noise Cancellation: BVC")
    logger.info("Agent ready - waiting for connections...")
    
    # Inject 'start' command for CLI
    sys.argv = ['main.py', 'start']
    agents.cli.run_app(server)



if __name__ == "__main__":
    # Development mode
    required_vars = ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET',
                     'DEEPGRAM_API_KEY', 'CARTESIA_API_KEY', 'MISTRAL_API_KEY', 'DATABASE_URL']
    
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
