"""
Conversation Orchestrator with Groq LLM
Uses Groq function calling to save/retrieve recipes
Optimized for free tier rate limits (30 RPM, 40K TPM)
"""
import os
from typing import Dict, List, Optional, Any
import logging
import json
from decimal import Decimal
from datetime import datetime, date
import uuid
import asyncio

from groq import Groq, RateLimitError, APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from prompts import SYSTEM_PROMPT, OFF_TOPIC_RESPONSE
import database as db

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Model selection - using efficient model for free tier
# llama-3.1-8b-instant is faster and uses fewer tokens
# llama-3.3-70b-versatile is more capable for complex function calling
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')


def sanitize_for_json(obj):
    """
    Recursively convert Python objects to JSON-serializable types.
    Handles: Decimal -> float, datetime -> str, UUID -> str, RealDictRow -> dict
    """
    if obj is None:
        return None
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif hasattr(obj, '_asdict'):  # namedtuple
        return sanitize_for_json(obj._asdict())
    elif hasattr(obj, 'keys'):  # dict-like (RealDictRow)
        return {k: sanitize_for_json(obj[k]) for k in obj.keys()}
    else:
        return obj


# Define tools in OpenAI-compatible format for Groq
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_plate_recipe",
            "description": "Save a complete plate recipe (final dish) to the database. Call this when the chef confirms the recipe is ready to save.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the dish"},
                    "serves": {"type": "integer", "description": "Number of servings"},
                    "description": {"type": "string", "description": "Brief description"},
                    "plating_instructions": {"type": "string", "description": "How to plate the dish"},
                    "presentation_notes": {"type": "string", "description": "Notes on presentation (spiciness, temperature, etc)"},
                    "category": {"type": "string", "description": "Category like main, appetizer, dessert"},
                    "cuisine": {"type": "string", "description": "Cuisine type like Indian, Italian"},
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["name", "serves"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_batch_recipe",
            "description": "Save a batch recipe (sauce, stock, base component) to the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the batch recipe"},
                    "yield_quantity": {"type": "number", "description": "How much it yields"},
                    "yield_unit": {"type": "string", "description": "Unit (kg, liters, etc)"},
                    "description": {"type": "string"},
                    "instructions": {"type": "string"},
                    "temperature": {"type": "number"},
                    "temperature_unit": {"type": "string", "enum": ["C", "F"]},
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["name", "yield_quantity", "yield_unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_recipes",
            "description": "Search for recipes by name in the chef's library",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "recipe_type": {"type": "string", "enum": ["batch", "plate", "both"]}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe_details",
            "description": "Get full details of a specific recipe",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_name": {"type": "string"},
                    "recipe_type": {"type": "string", "enum": ["batch", "plate"]}
                },
                "required": ["recipe_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_recipes",
            "description": "List all recipes saved by the chef",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


class ConversationOrchestrator:
    """Orchestrator with Groq LLM and function calling"""
    
    def __init__(self, chef_id: str, session_id: str):
        self.chef_id = chef_id
        self.session_id = session_id
        
        # Function executors
        self.functions = {
            "save_plate_recipe": self._execute_save_plate_recipe,
            "save_batch_recipe": self._execute_save_batch_recipe,
            "search_recipes": self._execute_search_recipes,
            "get_recipe_details": self._execute_get_recipe_details,
            "list_recipes": self._execute_list_recipes,
        }
        
        # Conversation history for context
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Current recipe being built
        self.current_recipe = {}
        self.recipe_type = None
        
        logger.info(f"✅ Orchestrator ready for chef: {chef_id} (Groq: {GROQ_MODEL})")
    
    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        before_sleep=lambda retry_state: logger.warning(f"⏳ Rate limited, waiting {retry_state.next_action.sleep}s...")
    )
    async def _call_groq(self, messages: List[dict], tools: List[dict] = None) -> Any:
        """Call Groq API with retry logic for rate limits"""
        try:
            # Run sync Groq client in thread pool to not block async loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    temperature=0.7,
                    max_tokens=500,  # Keep responses concise for voice
                )
            )
            return response
        except RateLimitError as e:
            logger.warning(f"⚠️ Groq rate limit hit: {e}")
            raise  # Let tenacity handle retry
        except APIError as e:
            logger.error(f"❌ Groq API error: {e}")
            raise
    
    async def process_message(self, user_message: str) -> str:
        """Process user message, execute any function calls, return AI response"""
        
        logger.info(f"📥 Processing: {user_message}")
        
        # Check for off-topic
        if self._is_off_topic(user_message):
            logger.info("⚠️ Off-topic message detected")
            return OFF_TOPIC_RESPONSE
        
        try:
            # Add user message to history
            self.messages.append({"role": "user", "content": user_message})
            
            # Call Groq with tools
            response = await self._call_groq(self.messages, GROQ_TOOLS)
            
            assistant_message = response.choices[0].message
            
            # Check if model wants to call a function
            if assistant_message.tool_calls:
                # Add assistant's response to history
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 Function call: {func_name}({func_args})")
                    
                    if func_name in self.functions:
                        result = await self.functions[func_name](func_args)
                        result = sanitize_for_json(result)
                        
                        # Add function result to history
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })
                
                # Get final response after function execution
                final_response = await self._call_groq(self.messages, GROQ_TOOLS)
                response_text = final_response.choices[0].message.content or "Done!"
                
                # Add final response to history
                self.messages.append({"role": "assistant", "content": response_text})
                
                response_text = self._clean_for_speech(response_text)
                logger.info(f"📤 Response (after function): {response_text}")
                return response_text
            
            # No function call, just return the text response
            response_text = assistant_message.content or "I'm here. What would you like to do?"
            
            # Add to history
            self.messages.append({"role": "assistant", "content": response_text})
            
            response_text = self._clean_for_speech(response_text)
            logger.info(f"📤 Response: {response_text}")
            return response_text
            
        except RateLimitError as e:
            logger.error(f"❌ Rate limit exceeded after retries: {e}")
            return "I'm currently receiving too many requests. Please wait a moment and try again."
        except Exception as e:
            logger.error(f"❌ Groq error: {e}", exc_info=True)
            return "I'm sorry, I had trouble processing that. Could you try again?"
    
    # ==================== Function Executors ====================
    
    async def _execute_save_plate_recipe(self, args: dict) -> dict:
        """Actually save plate recipe to database"""
        try:
            name = args.get("name", "Unnamed Recipe")
            serves = args.get("serves", 1)
            
            logger.info(f"💾 SAVING PLATE RECIPE: {name}")
            
            # Call actual database function
            recipe_id = db.save_plate_recipe(
                chef_id=self.chef_id,
                name=name,
                serves=serves,
                description=args.get("description"),
                plating_instructions=args.get("plating_instructions"),
                presentation_notes=args.get("presentation_notes"),
                category=args.get("category"),
                cuisine=args.get("cuisine"),
                ingredients=args.get("ingredients"),
                is_complete=True
            )
            
            logger.info(f"✅ SAVED to database with ID: {recipe_id}")
            
            return {
                "success": True,
                "recipe_id": recipe_id,
                "message": f"Successfully saved '{name}' to your recipe library"
            }
            
        except Exception as e:
            logger.error(f"❌ Database save error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save recipe: {e}"
            }
    
    async def _execute_save_batch_recipe(self, args: dict) -> dict:
        """Actually save batch recipe to database"""
        try:
            name = args.get("name", "Unnamed Batch")
            yield_qty = args.get("yield_quantity", 1)
            yield_unit = args.get("yield_unit", "kg")
            
            logger.info(f"💾 SAVING BATCH RECIPE: {name}")
            
            recipe_id = db.save_batch_recipe(
                chef_id=self.chef_id,
                name=name,
                yield_quantity=yield_qty,
                yield_unit=yield_unit,
                description=args.get("description"),
                instructions=args.get("instructions"),
                temperature=args.get("temperature"),
                temperature_unit=args.get("temperature_unit", "C"),
                ingredients=args.get("ingredients"),
                is_complete=True
            )
            
            logger.info(f"✅ SAVED to database with ID: {recipe_id}")
            
            return {
                "success": True,
                "recipe_id": recipe_id,
                "message": f"Successfully saved '{name}' to your batch library"
            }
            
        except Exception as e:
            logger.error(f"❌ Database save error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save batch recipe: {e}"
            }
    
    async def _execute_search_recipes(self, args: dict) -> dict:
        """Smart search recipes with priority matching"""
        try:
            query = args.get("query", "")
            
            logger.info(f"🔍 SEARCHING: '{query}' for chef: {self.chef_id}")
            
            results = db.smart_search_recipes(
                chef_id=self.chef_id,
                query=query
            )
            
            # Check for exact or best match (includes full recipe details)
            if results.get('exact_match') or results.get('best_match'):
                recipe = results.get('recipe', {})
                recipe_type = results.get('recipe_type', 'unknown')
                recipe_name = recipe.get('name', query)
                
                match_type = "exact" if results.get('exact_match') else "best"
                logger.info(f"✅ {match_type.upper()} MATCH: {recipe_name} ({recipe_type})")
                
                # Format recipe details for Groq
                return {
                    "found": True,
                    "exact_match": results.get('exact_match', False),
                    "recipe_type": recipe_type,
                    "recipe_name": recipe_name,
                    "serves": recipe.get('serves'),
                    "yield_quantity": recipe.get('yield_quantity'),
                    "yield_unit": recipe.get('yield_unit'),
                    "description": recipe.get('description'),
                    "plating_instructions": recipe.get('plating_instructions'),
                    "presentation_notes": recipe.get('presentation_notes'),
                    "garnish": recipe.get('garnish'),
                    "instructions": recipe.get('instructions'),
                    "notes": recipe.get('notes'),
                    "category": recipe.get('category'),
                    "cuisine": recipe.get('cuisine'),
                    "ingredients": recipe.get('ingredients', []),
                    "message": f"Found {recipe_type} recipe: {recipe_name}"
                }
            
            total = results.get('total_found', 0)
            batch_matches = results.get('batch_recipes', [])
            plate_matches = results.get('plate_recipes', [])
            
            logger.info(f"📊 Found {total} results: {len(batch_matches)} batch, {len(plate_matches)} plate")
            
            if total == 0:
                # No matches - list what's available
                all_recipes = db.list_chef_recipes(self.chef_id)
                available_batches = [r.get('name') for r in all_recipes.get('batch_recipes', [])]
                available_plates = [r.get('name') for r in all_recipes.get('plate_recipes', [])]
                
                logger.info(f"❌ No match. Available: {available_batches + available_plates}")
                
                return {
                    "found": False,
                    "total": 0,
                    "message": f"No recipes matching '{query}'",
                    "available_batch_recipes": available_batches[:5],
                    "available_plate_recipes": available_plates[:5],
                    "suggestion": "Try one of these recipe names"
                }
            
            elif total == 1:
                # Single match from keyword search - get full details
                if batch_matches:
                    recipe = results.get('recipe') or db.get_recipe_by_name(self.chef_id, batch_matches[0]['name'], 'batch')
                    logger.info(f"✅ Found BATCH: {batch_matches[0]['name']}")
                    return {
                        "found": True,
                        "recipe_type": "batch",
                        "recipe_name": recipe.get('name'),
                        "yield_quantity": recipe.get('yield_quantity'),
                        "yield_unit": recipe.get('yield_unit'),
                        "description": recipe.get('description'),
                        "instructions": recipe.get('instructions'),
                        "notes": recipe.get('notes'),
                        "ingredients": recipe.get('ingredients', []),
                        "message": f"Found batch recipe: {recipe.get('name')}"
                    }
                else:
                    recipe = results.get('recipe') or db.get_recipe_by_name(self.chef_id, plate_matches[0]['name'], 'plate')
                    logger.info(f"✅ Found PLATE: {plate_matches[0]['name']}")
                    return {
                        "found": True,
                        "recipe_type": "plate",
                        "recipe_name": recipe.get('name'),
                        "serves": recipe.get('serves'),
                        "description": recipe.get('description'),
                        "plating_instructions": recipe.get('plating_instructions'),
                        "garnish": recipe.get('garnish'),
                        "notes": recipe.get('notes'),
                        "category": recipe.get('category'),
                        "cuisine": recipe.get('cuisine'),
                        "ingredients": recipe.get('ingredients', []),
                        "message": f"Found plate recipe: {recipe.get('name')}"
                    }
            
            else:
                # Multiple matches - list them for clarification
                batch_names = [r['name'] for r in batch_matches]
                plate_names = [r['name'] for r in plate_matches]
                
                logger.info(f"❓ Multiple: batch={batch_names}, plate={plate_names}")
                
                return {
                    "found": True,
                    "total": total,
                    "multiple_matches": True,
                    "batch_recipe_names": batch_names,
                    "plate_recipe_names": plate_names,
                    "message": f"Found {total} recipes. Which one: {', '.join(batch_names + plate_names)}?",
                    "suggestion": "Ask user to specify exact name"
                }
                
        except Exception as e:
            logger.error(f"❌ Search error: {e}", exc_info=True)
            return {"found": False, "error": str(e), "message": f"Search failed: {e}"}

    
    async def _execute_get_recipe_details(self, args: dict) -> dict:
        """Get recipe details from database"""
        return await self._execute_search_recipes({"query": args.get("recipe_name")})
    
    async def _execute_list_recipes(self, args: dict) -> dict:
        """List all recipes for chef"""
        try:
            logger.info(f"📋 LISTING RECIPES for chef: {self.chef_id}")
            
            recipes = db.list_chef_recipes(self.chef_id)
            
            batch_count = len(recipes.get('batch_recipes', []))
            plate_count = len(recipes.get('plate_recipes', []))
            
            logger.info(f"✅ Found {batch_count} batch + {plate_count} plate recipes")
            
            return {
                "total_batch": batch_count,
                "total_plate": plate_count,
                "batch_recipes": [r.get('name') for r in recipes.get('batch_recipes', [])],
                "plate_recipes": [r.get('name') for r in recipes.get('plate_recipes', [])]
            }
            
        except Exception as e:
            logger.error(f"❌ List error: {e}")
            return {"error": str(e)}
    
    # ==================== Helper Methods ====================
    
    def _is_off_topic(self, message: str) -> bool:
        """Check if message is off-topic"""
        off_topic_keywords = ['weather', 'news', 'sports', 'politics', 'joke', 'game', 'movie']
        message_lower = message.lower()
        
        for keyword in off_topic_keywords:
            if keyword in message_lower and 'recipe' not in message_lower and 'cook' not in message_lower:
                return True
        return False
    
    def _clean_for_speech(self, text: str) -> str:
        """Clean text for TTS (remove markdown, etc.)"""
        # Remove asterisks (bold/italic)
        text = text.replace('*', '')
        # Remove hashtags (headers)
        text = text.replace('#', '')
        # Remove bullet points
        text = text.replace('- ', '')
        text = text.replace('• ', '')
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
