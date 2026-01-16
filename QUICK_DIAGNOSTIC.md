## Quick Diagnostic Steps

The backend IS sending events (confirmed in logs), but the frontend isn't updating.

### Option 1: Check Browser Console (Quickest)

1. Open `http://localhost:8080`
2. Press **F12** to open DevTools
3. Go to **Console** tab
4. Connect to voice agent
5. Say: **"I'm making paneer tikka"**
6. Look for these console messages:

```
✅ Recipe Builder initialized
📨 Raw data received: ...
📝 Decoded string: ...
✅ Parsed data: ...
🎨 Recipe event received: recipe_start
```

**If you see these:** Events are reaching frontend but RecipeBuilder not responding
**If you DON'T see these:** Events not reaching frontend at all

### Option 2: Use Debug Page

1. Open `http://localhost:8080/debug.html`
2. Connect and test
3. Events will be displayed in real-time

### Option 3: Add Console Logging

Add this to beginning of `recipe-builder.js` (line 8):

```javascript
// State management
const RecipeBuilder = {
    currentRecipe: null,
    recipeHistory: [],
    isVisible: false,
    animationQueue: [],

    // ADD THIS LINE:
    _debug: true,  // Enable debug logging
```

Then look for "📨 Recipe event received:" in console.

### Send Me:

**All console output** from the moment you connect until you finish describing the recipe. Include any errors!
