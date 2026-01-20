/**
 * Recipe Builder Module
 * Real-time recipe building UI with Liquid Glass aesthetics
 * Mobile-first approach with smooth animations
 */

// State management
const RecipeBuilder = {
    currentRecipe: null,
    recipeHistory: [],
    isVisible: false,
    animationQueue: [],

    // DOM elements (set on init)
    container: null,
    recipeCard: null,
    recipeHeader: null,
    recipeName: null,
    recipeType: null,
    recipeMetadata: null,
    ingredientsList: null,
    instructionsArea: null,
    progressIndicator: null,

    /**
     * Initialize the Recipe Builder
     */
    init() {
        console.log('🎨 Initializing Recipe Builder...');

        // Get DOM elements
        this.container = document.getElementById('recipeBuilder');
        this.recipeCard = document.getElementById('recipeCard');
        this.recipeHeader = document.getElementById('recipeHeaderSection');
        this.recipeName = document.getElementById('recipeNameDisplay');
        this.recipeType = document.getElementById('recipeTypeBadge');
        this.recipeMetadata = document.getElementById('recipeMetadata');
        this.ingredientsList = document.getElementById('ingredientsList');
        this.instructionsArea = document.getElementById('recipeInstructions');
        this.progressIndicator = document.getElementById('recipeProgress');

        console.log('✅ Recipe Builder initialized');
    },

    /**
     * Handle incoming recipe events from backend via LiveKit data channel
     * @param {Object} event - Recipe event data
     */
    handleRecipeEvent(event) {
        console.log('📨 Recipe event received:', event.event, event);

        switch (event.event) {
            case 'recipe_start':
                this.startNewRecipe(event);
                break;
            case 'recipe_metadata_update':
                this.updateMetadataFromEvent(event);
                break;
            case 'ingredient_add':
                this.addIngredientFromEvent(event);
                break;
            case 'instruction_add':
                this.addInstructionFromEvent(event);
                break;
            case 'recipe_saving':
                this.setProgress('saving');
                break;
            case 'recipe_saved':
                this.showRecipeSaved(event);
                break;
            case 'recipe_error':
                this.showError(event);
                break;
            default:
                console.warn('Unknown recipe event:', event.event);
        }
    },

    /**
     * Start building a new recipe
     * @param {Object} data - Recipe data including name, type, serves, ingredients
     */
    startNewRecipe(data) {
        console.log('🆕 Starting new recipe:', data.name);
        console.log('   📦 Received event data:', data);

        // Initialize current recipe state
        this.currentRecipe = {
            name: data.name || '',
            type: data.recipe_type || '',
            serves: data.serves || data.yield_quantity || null,
            unit: data.yield_unit || '',
            description: data.description || '',
            cuisine: data.cuisine || '',
            category: data.category || '',
            ingredients: data.ingredients || [],
            instructions: data.instructions || '',
            temperature: data.temperature || null,
            temperatureUnit: data.temperature_unit || 'C'
        };

        console.log('   ✅ Initial recipe state:', this.currentRecipe);
        console.log('   🍽️ Serves:', this.currentRecipe.serves, '| Cuisine:', this.currentRecipe.cuisine);

        // Show the recipe builder
        this.show();

        // Update UI with smooth animations
        this.updateRecipeHeader();
        this.updateRecipeMetadata();
        this.updateIngredients();
        this.updateInstructions();
        this.setProgress('building');
    },

    /**
     * Show the recipe builder with smooth fade-in
     */
    show() {
        if (this.container) {
            this.container.classList.remove('hidden');
            this.container.classList.add('visible');
            this.isVisible = true;

            // CRITICAL FIX: Hide the empty state when showing the recipe
            const emptyState = document.getElementById('emptyRecipeState');
            if (emptyState) {
                emptyState.style.display = 'none';
            }

            // Trigger entrance animation
            setTimeout(() => {
                if (this.recipeCard) {
                    this.recipeCard.style.opacity = '0';
                    this.recipeCard.style.transform = 'translateY(20px) scale(0.95)';

                    // Force reflow
                    this.recipeCard.offsetHeight;

                    this.recipeCard.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                    this.recipeCard.style.opacity = '1';
                    this.recipeCard.style.transform = 'translateY(0) scale(1)';
                }
            }, 10);
        }
    },

    /**
     * Hide the recipe builder
     */
    hide() {
        if (this.container) {
            this.container.classList.remove('visible');
            this.container.classList.add('hidden');
            this.isVisible = false;
        }
    },

    /**
     * Update recipe header (name and type badge)
     */
    updateRecipeHeader() {
        if (!this.currentRecipe) return;

        // Update name with fallback for null/undefined
        if (this.recipeName) {
            const displayName = this.currentRecipe.name || 'Building Recipe...';
            this.recipeName.textContent = displayName;
            this.recipeName.classList.add('pulse-once');
            setTimeout(() => {
                this.recipeName.classList.remove('pulse-once');
            }, 600);
        }

        // Update type badge
        if (this.recipeType) {
            const typeText = this.currentRecipe.type === 'plate' ? 'Plate Recipe' : 'Batch Recipe';
            this.recipeType.textContent = typeText;
            this.recipeType.className = `type-badge ${this.currentRecipe.type}`;
        }
    },

    /**
     * Update recipe metadata (serves, cuisine, temperature, etc.)
     */
    updateRecipeMetadata() {
        if (!this.currentRecipe || !this.recipeMetadata) return;

        console.log('🎨 updateRecipeMetadata() called');
        console.log('   📊 Current state - Serves:', this.currentRecipe.serves, '| Cuisine:', this.currentRecipe.cuisine);

        let metadataHTML = '';

        // Serves or Yield
        if (this.currentRecipe.serves) {
            console.log('   ✅ Rendering Serves card:', this.currentRecipe.serves);
            metadataHTML += `
                <div class="metadata-item">
                    <Span class="metadata-icon">👥</span>
                    <span class="metadata-label">Serves:</span>
                    <span class="metadata-value">${this.currentRecipe.serves}</span>
                </div>
            `;
        } else if (this.currentRecipe.unit) {
            metadataHTML += `
                <div class="metadata-item">
                    <span class="metadata-icon">📦</span>
                    <span class="metadata-label">Yield:</span>
                    <span class="metadata-value">${this.currentRecipe.serves || ''} ${this.currentRecipe.unit}</span>
                </div>
            `;
        }

        // Cuisine
        if (this.currentRecipe.cuisine) {
            console.log('   ✅ Rendering Cuisine card:', this.currentRecipe.cuisine);
            metadataHTML += `
                <div class="metadata-item">
                    <span class="metadata-icon">🌍</span>
                    <span class="metadata-label">Cuisine:</span>
                    <span class="metadata-value">${this.currentRecipe.cuisine}</span>
                </div>
            `;
        }

        // Temperature (for batch recipes)
        if (this.currentRecipe.temperature) {
            const tempUnit = this.currentRecipe.temperatureUnit || 'C';
            metadataHTML += `
                <div class="metadata-item">
                    <span class="metadata-icon">🌡️</span>
                    <span class="metadata-label">Temp:</span>
                    <span class="metadata-value">${this.currentRecipe.temperature}°${tempUnit}</span>
                </div>
            `;
        }

        // Description
        if (this.currentRecipe.description) {
            metadataHTML += `
                <div class="metadata-description">
                    ${this.currentRecipe.description}
                </div>
            `;
        }

        this.recipeMetadata.innerHTML = metadataHTML;
    },

    /**
     * Update ingredients list with smooth animations
     */
    updateIngredients() {
        if (!this.currentRecipe || !this.ingredientsList) return;

        const ingredients = this.currentRecipe.ingredients || [];

        if (ingredients.length === 0) {
            this.ingredientsList.innerHTML = '<div class="empty-state">No ingredients yet...</div>';
            return;
        }

        let html = '<div class="ingredients-header">Ingredients</div>';
        html += '<div class="ingredients-grid">';

        ingredients.forEach((ing, index) => {
            const quantity = ing.quantity || ing.amount || '';
            const unit = ing.unit || '';
            const name = ing.name || ing.ingredient || '';

            html += `
                <div class="ingredient-item glass-item" style="animation-delay: ${index * 50}ms">
                    <div class="ingredient-quantity">${quantity} ${unit}</div>
                    <div class="ingredient-name">${name}</div>
                </div>
            `;
        });

        html += '</div>';
        this.ingredientsList.innerHTML = html;
    },

    /**
     * Update instructions/plating area
     */
    updateInstructions() {
        if (!this.currentRecipe || !this.instructionsArea) return;

        const instructions = this.currentRecipe.instructions || '';

        if (!instructions) {
            this.instructionsArea.innerHTML = '';
            return;
        }

        this.instructionsArea.innerHTML = `
            <div class="instructions-header">Instructions</div>
            <div class="instructions-content glass-panel">
                ${instructions.split('\n').map(line => `<p>${line}</p>`).join('')}
            </div>
        `;
    },

    /**
     * Update metadata from a real-time event
     * @param {Object} event - Metadata update event
     */
    updateMetadataFromEvent(event) {
        console.log('📝 Updating metadata from event:', event);

        if (!this.currentRecipe) {
            // If no recipe started yet, initialize one
            console.log('   ⚠️ No current recipe, initializing from event');
            this.currentRecipe = {
                name: event.name || 'Building Recipe...',
                type: event.recipe_type || '',
                serves: null,
                ingredients: [],
                instructions: ''
            };
            this.show();
            this.updateRecipeHeader();
        }

        // Log state before update
        console.log('   📊 Before update - Serves:', this.currentRecipe.serves, '| Cuisine:', this.currentRecipe.cuisine);

        // Update fields
        if (event.serves !== undefined) this.currentRecipe.serves = event.serves;
        if (event.yield_quantity !== undefined) this.currentRecipe.serves = event.yield_quantity;
        if (event.yield_unit) this.currentRecipe.unit = event.yield_unit;
        if (event.cuisine) this.currentRecipe.cuisine = event.cuisine;
        if (event.category) this.currentRecipe.category = event.category;
        if (event.temperature !== undefined) this.currentRecipe.temperature = event.temperature;
        if (event.temperature_unit) this.currentRecipe.temperatureUnit = event.temperature_unit;
        if (event.description) this.currentRecipe.description = event.description;

        // Log state after update
        console.log('   ✅ After update - Serves:', this.currentRecipe.serves, '| Cuisine:', this.currentRecipe.cuisine);
        console.log('   🔄 Calling updateRecipeMetadata() to re-render UI');

        // Re-render metadata
        this.updateRecipeMetadata();
    },

    /**
     * Add a single ingredient from a real-time event
     * @param {Object} event - Ingredient add event
     */
    addIngredientFromEvent(event) {
        console.log('🥗 Adding ingredient from event:', event.ingredient);

        if (!this.currentRecipe) {
            // Initialize if needed
            this.currentRecipe = {
                name: event.name || 'Building Recipe...',
                type: event.recipe_type || '',
                ingredients: [],
                instructions: ''
            };
            this.show();
            this.updateRecipeHeader();
        }

        // Add the new ingredient
        if (event.ingredient) {
            this.currentRecipe.ingredients.push(event.ingredient);
        }

        // Re-render ingredients with new one
        this.updateIngredients();
    },

    /**
     * Add an instruction from a real-time event
     * @param {Object} event - Instruction add event
     */
    addInstructionFromEvent(event) {
        console.log('📋 Adding instruction from event:', event.instruction);

        if (!this.currentRecipe) {
            this.currentRecipe = {
                name: event.name || 'Building Recipe...',
                type: event.recipe_type || '',
                ingredients: [],
                instructions: ''
            };
            this.show();
            this.updateRecipeHeader();
        }

        // Append instruction (as array or string)
        if (event.instruction) {
            if (typeof this.currentRecipe.instructions === 'string') {
                this.currentRecipe.instructions = this.currentRecipe.instructions
                    ? this.currentRecipe.instructions + '\n' + event.instruction
                    : event.instruction;
            }
        }

        // Re-render instructions
        this.updateInstructions();
    },

    /**
     * Set progress indicator
     * @param {string} status - 'building' | 'saving' | 'saved' | 'error'
     */
    setProgress(status) {
        if (!this.progressIndicator) return;

        this.progressIndicator.className = `progress-indicator ${status}`;

        const statusText = {
            'building': '✨ Building...',
            'saving': '💾 Saving...',
            'saved': '✅ Saved!',
            'error': '❌ Error'
        };

        this.progressIndicator.textContent = statusText[status] || '';

        // Auto-hide if saved
        if (status === 'saved') {
            setTimeout(() => {
                this.progressIndicator.style.opacity = '0';
            }, 2000);
        }
    },

    /**
     * Show recipe saved celebration
     */
    showRecipeSaved(data) {
        console.log('🎉 Recipe saved successfully!');

        this.setProgress('saved');

        // Add to history
        if (this.currentRecipe) {
            this.recipeHistory.push({
                ...this.currentRecipe,
                recipe_id: data.recipe_id,
                timestamp: new Date()
            });
        }

        // Show celebration effect
        if (this.recipeCard) {
            this.recipeCard.classList.add('success-glow');
            setTimeout(() => {
                this.recipeCard.classList.remove('success-glow');
            }, 1500);
        }

        // Auto-hide after a few seconds
        setTimeout(() => {
            this.hide();
            this.currentRecipe = null;
        }, 5000);
    },

    /**
     * Show error state
     */
    showError(data) {
        console.error('❌ Recipe error:', data.error);

        this.setProgress('error');

        if (this.recipeCard) {
            this.recipeCard.classList.add('error-shake');
            setTimeout(() => {
                this.recipeCard.classList.remove('error-shake');
            }, 600);
        }
    },

    /**
     * Clear recipe builder
     */
    clear() {
        this.currentRecipe = null;

        if (this.recipeName) this.recipeName.textContent = '';
        if (this.recipeMetadata) this.recipeMetadata.innerHTML = '';
        if (this.ingredientsList) this.ingredientsList.innerHTML = '';
        if (this.instructionsArea) this.instructionsArea.innerHTML = '';

        // CRITICAL FIX: Restore the empty state when clearing
        const emptyState = document.getElementById('emptyRecipeState');
        if (emptyState) {
            emptyState.style.display = 'flex';
        }

        this.hide();
    }
};

// Expose to global scope
window.RecipeBuilder = RecipeBuilder;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => RecipeBuilder.init());
} else {
    RecipeBuilder.init();
}
