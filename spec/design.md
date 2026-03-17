# Navis - Design Specification

## Architecture Overview

### High-Level Semantic + RL Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Voice Input   │───▶│  Intent Parser   │───▶│  Semantic       │
│   (Speech-to-   │    │  (Single LLM     │    │  Requirements   │
│   Text)         │    │   Call)          │    │  Extractor      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   UI Controller │    │   DOM Analyzer   │    │   Semantic      │
│   (Visual       │    │   (Local, Fast   │    │   Element       │
│   Feedback)     │    │   Element        │    │   Scorer        │
└─────────────────┘    │   Extraction)    │    │   (Intent-aware)│
         ▲              └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         │              ┌──────────────────┐    ┌─────────────────┐
         │              │   Vision Model   │    │   RL Agent      │
         │              │   (Fallback      │    │   (Learning     │
         │              │   Only)          │    │   from Feedback)│
         │              └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         └──────────────────────────────────────┌─────────────────┐
                                                │   Action        │
                                                │   Selector      │
                                                │   (Confidence   │
                                                │   Based)        │
                                                └─────────────────┘
```

### Component Architecture

#### 1. Chrome Extension Structure
```
navis-extension/
├── manifest.json           # Extension configuration
├── background/
│   ├── service-worker.js   # Background script coordinator
│   ├── intent-parser.js    # LLM integration for intent parsing
│   ├── semantic-scorer.js  # Element relevance scoring engine
│   ├── rl-agent.js         # Reinforcement learning model
│   └── vision-fallback.js  # Vision model integration
├── content/
│   ├── content-script.js   # Main coordinator
│   ├── dom-analyzer.js     # DOM element extraction
│   ├── semantic-analyzer.js # Intent-aware element analysis
│   ├── action-selector.js  # Confidence-based action selection
│   ├── feedback-collector.js # Human feedback collection
│   └── action-executor.js  # Action execution with learning
├── popup/
│   ├── popup.html          # Extension popup UI
│   ├── popup.js            # Popup logic
│   └── popup.css           # Popup styling
├── ui/
│   ├── overlay.js          # Page overlay components
│   ├── voice-input.js      # Voice interface
│   ├── visual-feedback.js  # Highlighting and confidence display
│   ├── feedback-ui.js      # Human feedback collection interface
│   └── learning-progress.js # RL learning progress display
└── assets/
    ├── icons/              # Extension icons
    └── sounds/             # Audio feedback
```

## Core Components Design

### 1. Voice Input System

#### Speech-to-Text Integration
```javascript
class VoiceInputManager {
  constructor() {
    this.recognition = new webkitSpeechRecognition();
    this.isListening = false;
    this.confidenceThreshold = 0.7;
  }
  
  startListening() {
    // Configure speech recognition for goal capture
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-US';
    
    return new Promise((resolve, reject) => {
      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const confidence = event.results[0][0].confidence;
        resolve({ transcript, confidence });
      };
      
      this.recognition.start();
    });
  }
}
```

### 2. Intent Parser + Semantic Requirements

#### Python Backend - Intent Parser
```python
class IntentParser:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def parse_user_goal(self, voice_input, page_context):
        prompt = f"""
        You are a web navigation intent parser. Parse the user's goal and extract semantic requirements.
        
        User Goal: "{voice_input}"
        Current Page: {page_context['title']}
        Current URL: {page_context['url']}
        
        Return JSON with:
        {{
          "goal": "clear, specific goal statement",
          "action_type": "navigate|search|fill_form|purchase|contact|click|select",
          "target_semantics": {{
            "keywords": ["relevant", "keywords", "from", "goal"],
            "element_types": ["button", "link", "input", "select"],
            "context_clues": ["nearby", "text", "indicators"],
            "visual_hints": ["color", "position", "size", "prominence"]
          }},
          "urgency": "low|medium|high",
          "requires_confirmation": bool,
          "confidence": 0.0-1.0
        }}
        """
        
        response = await self.llm.call(prompt)
        return json.loads(response)
```

#### JavaScript Frontend - Communication Layer
```javascript
class IntentParserClient {
  constructor() {
    this.backendUrl = 'http://localhost:8000';
  }
  
  async parseUserGoal(voiceInput, pageContext) {
    const response = await fetch(`${this.backendUrl}/parse-intent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        voice_input: voiceInput,
        page_context: pageContext
      })
    });
    
    return await response.json();
  }
}
```

### 3. Python Backend - Semantic Element Analysis Engine

#### Intent-Aware Element Scoring
```python
class SemanticAnalyzer:
    def __init__(self):
        self.scoring_weights = {
            'text_match': 0.3,
            'semantic_relevance': 0.25,
            'contextual_position': 0.2,
            'visual_prominence': 0.15,
            'interaction_history': 0.1
        }
    
    def analyze_elements(self, elements, intent):
        scored_elements = []
        
        for element in elements:
            scores = {
                'text_match': self.calculate_text_match(element, intent['target_semantics']['keywords']),
                'semantic_relevance': self.calculate_semantic_relevance(element, intent),
                'contextual_position': self.calculate_contextual_score(element, intent),
                'visual_prominence': self.calculate_visual_score(element),
                'interaction_history': self.get_historical_score(element, intent['action_type'])
            }
            
            total_score = sum(score * self.scoring_weights[key] 
                            for key, score in scores.items())
            
            scored_elements.append({
                **element,
                'scores': scores,
                'total_score': total_score,
                'confidence': self.calculate_confidence(scores, total_score)
            })
        
        return sorted(scored_elements, key=lambda x: x['total_score'], reverse=True)
    
    def calculate_text_match(self, element, keywords):
        element_text = (element.get('text', '') + ' ' + element.get('aria_label', '')).lower()
        matches = [kw for kw in keywords if kw.lower() in element_text]
        return len(matches) / len(keywords) if keywords else 0
    
    def calculate_semantic_relevance(self, element, intent):
        # Check if element type matches expected types
        type_match = 0.5 if element.get('type') in intent['target_semantics']['element_types'] else 0
        
        # Check for context clues in nearby elements
        context_match = self.check_context_clues(element, intent['target_semantics']['context_clues'])
        
        return type_match + context_match
    
    def calculate_contextual_score(self, element, intent):
        # Score based on element position and surrounding context
        position_score = self.get_position_relevance(element, intent['action_type'])
        proximity_score = self.get_proximity_to_relevant_elements(element, intent)
        
        return (position_score + proximity_score) / 2
```

#### JavaScript Frontend - Element Analysis Client
```javascript
class SemanticAnalyzerClient {
  constructor() {
    this.backendUrl = 'http://localhost:8000';
  }
  
  async analyzeElements(elements, intent) {
    const response = await fetch(`${this.backendUrl}/analyze-elements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        elements: elements,
        intent: intent
      })
    });
    
    return await response.json();
  }
}
```

### 4. Python Backend - Reinforcement Learning Agent

#### Learning from Human Feedback
```python
import numpy as np
import json
from datetime import datetime

class RLAgent:
    def __init__(self):
        self.model = self.initialize_model()
        self.experience_buffer = []
        self.learning_rate = 0.01
        self.exploration_rate = 0.1
    
    def select_action(self, candidates, intent, page_context):
        # Epsilon-greedy action selection
        if np.random.random() < self.exploration_rate:
            # Explore: select random high-confidence candidate
            top_candidates = candidates[:3]
            return np.random.choice(top_candidates)
        else:
            # Exploit: use learned policy
            features = self.extract_features(candidates, intent, page_context)
            predictions = self.model.predict(features)
            
            # Combine semantic scores with RL predictions
            combined_candidates = []
            for i, candidate in enumerate(candidates):
                combined_score = candidate['total_score'] * 0.7 + predictions[i] * 0.3
                combined_candidates.append({
                    **candidate,
                    'rl_score': predictions[i],
                    'combined_score': combined_score
                })
            
            return max(combined_candidates, key=lambda x: x['combined_score'])
    
    def record_experience(self, state, action, reward, feedback=None):
        experience = {
            'state': state,
            'action': action,
            'reward': reward,
            'feedback': feedback,
            'timestamp': datetime.now().isoformat()
        }
        
        self.experience_buffer.append(experience)
        
        # Learn from experience batch
        if len(self.experience_buffer) >= 10:
            self.update_model()
    
    def update_model(self):
        batch = self.experience_buffer[-10:]
        
        # Convert experiences to training data
        training_data = []
        for exp in batch:
            features = self.extract_features([exp['action']], exp['state']['intent'], exp['state']['page_context'])
            target = self.calculate_target(exp['reward'], exp['feedback'])
            training_data.append({'features': features, 'target': target})
        
        # Update model weights
        self.model.train(training_data)
        
        # Decay exploration rate
        self.exploration_rate = max(0.01, self.exploration_rate * 0.995)
    
    def calculate_target(self, reward, feedback):
        # Combine success/failure with human feedback
        target = reward  # 1 for success, -1 for failure, 0 for neutral
        
        if feedback:
            feedback_adjustments = {
                'correct_action': 0.5,
                'wrong_action': -0.5,
                'better_alternative': -0.2
            }
            target += feedback_adjustments.get(feedback.get('type'), 0)
        
        return max(-1, min(1, target))
    
    def extract_features(self, candidates, intent, page_context):
        # Extract numerical features for ML model
        features = []
        for candidate in candidates:
            feature_vector = [
                candidate.get('total_score', 0),
                len(candidate.get('text', '')),
                candidate.get('position', {}).get('x', 0),
                candidate.get('position', {}).get('y', 0),
                1 if candidate.get('type') in intent.get('target_semantics', {}).get('element_types', []) else 0
            ]
            features.append(feature_vector)
        return np.array(features)
```

#### JavaScript Frontend - RL Client
```javascript
class RLAgentClient {
  constructor() {
    this.backendUrl = 'http://localhost:8000';
  }
  
  async selectAction(candidates, intent, pageContext) {
    const response = await fetch(`${this.backendUrl}/select-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidates: candidates,
        intent: intent,
        page_context: pageContext
      })
    });
    
    return await response.json();
  }
  
  async recordExperience(state, action, reward, feedback = null) {
    await fetch(`${this.backendUrl}/record-experience`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        state: state,
        action: action,
        reward: reward,
        feedback: feedback
      })
    });
  }
}
```

### 5. Python Backend - Action Selector with Confidence

#### Smart Action Selection with Human Feedback
```python
class ActionSelector:
    def __init__(self, rl_agent):
        self.rl_agent = rl_agent
        self.confidence_threshold = 0.7
    
    async def select_best_action(self, candidates, intent, page_context):
        # Get RL agent's recommendation
        selected_action = self.rl_agent.select_action(candidates, intent, page_context)
        
        # Check confidence level
        if selected_action['confidence'] < self.confidence_threshold:
            # Return top candidates for user selection
            return {
                'requires_user_selection': True,
                'top_candidates': candidates[:3],
                'recommended': selected_action
            }
        
        return {
            'requires_user_selection': False,
            'selected_action': selected_action
        }
    
    async def record_user_selection(self, candidates, selected_candidate, intent):
        # Record user's choice for learning
        await self.rl_agent.record_experience(
            state={'intent': intent, 'candidates': candidates},
            action=selected_candidate,
            reward=1,  # User selection is positive reward
            feedback={'type': 'user_selection', 'alternative': selected_candidate}
        )
    
    async def record_action_result(self, action, intent, success, feedback=None):
        # Record execution result
        reward = 1 if success else -1
        
        await self.rl_agent.record_experience(
            state={'intent': intent, 'action': action},
            action=action,
            reward=reward,
            feedback=feedback
        )
```

#### JavaScript Frontend - Action Execution Client
```javascript
class ActionExecutionClient {
  constructor() {
    this.backendUrl = 'http://localhost:8000';
  }
  
  async selectBestAction(candidates, intent, pageContext) {
    const response = await fetch(`${this.backendUrl}/select-best-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidates: candidates,
        intent: intent,
        page_context: pageContext
      })
    });
    
    return await response.json();
  }
  
  async recordUserSelection(candidates, selectedCandidate, intent) {
    await fetch(`${this.backendUrl}/record-user-selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidates: candidates,
        selected_candidate: selectedCandidate,
        intent: intent
      })
    });
  }
  
  async recordActionResult(action, intent, success, feedback = null) {
    await fetch(`${this.backendUrl}/record-action-result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: action,
        intent: intent,
        success: success,
        feedback: feedback
      })
    });
  }
}
```

### 6. Python Backend - Vision Fallback System

#### Computer Vision for Edge Cases
```python
import base64
from io import BytesIO

class VisionFallback:
    def __init__(self, vision_client):
        self.vision = vision_client
        self.is_active = False
    
    async def handle_failed_action(self, step, error, page_context, screenshot_base64):
        print(f"DOM action failed: {error}. Activating vision fallback.")
        self.is_active = True
        
        # Decode screenshot
        screenshot_data = base64.b64decode(screenshot_base64)
        
        # Use vision model to understand the page
        vision_analysis = await self.vision.analyze_screenshot(
            image_data=screenshot_data,
            goal=step.get('description'),
            failed_action=step.get('action'),
            context=page_context
        )
        
        return {
            'success': True,
            'method': 'vision_fallback',
            'target_coordinates': vision_analysis.get('coordinates'),
            'confidence': vision_analysis.get('confidence'),
            'alternative_action': vision_analysis.get('suggested_action')
        }
    
    async def analyze_screenshot(self, image_data, goal, failed_action, context):
        # Call a multimodal vision API (e.g., GPT-4V, Claude Vision, Gemini)
        prompt = f"""
        The DOM-based action failed. Analyze this screenshot to complete the action.
        
        Failed Action: {failed_action}
        User Goal: {goal}
        Error Context: {context}
        
        Identify the target element and provide:
        1. Coordinates (x, y) of the element
        2. Confidence score (0-1)
        3. Alternative action suggestion
        """
        
        response = await self.vision.call_with_image(prompt, image_data)
        return response
```

#### JavaScript Frontend - Vision Fallback Client
```javascript
class VisionFallbackClient {
  constructor() {
    this.backendUrl = 'http://localhost:8000';
  }
  
  async handleFailedAction(step, error, pageContext) {
    // Capture screenshot
    const screenshot = await this.captureScreenshot();
    
    const response = await fetch(`${this.backendUrl}/vision-fallback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        step: step,
        error: error.message,
        page_context: pageContext,
        screenshot: screenshot  // base64 encoded
      })
    });
    
    const result = await response.json();
    
    if (result.success && result.target_coordinates) {
      // Execute action at coordinates
      return await this.executeAtCoordinates(result.target_coordinates);
    }
    
    throw new Error('Vision fallback could not complete action');
  }
  
  async captureScreenshot() {
    return new Promise((resolve) => {
      chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
        resolve(dataUrl.split(',')[1]); // Return base64 part
      });
    });
  }
  
  async executeAtCoordinates(coordinates) {
    const element = document.elementFromPoint(coordinates.x, coordinates.y);
    if (element) {
      element.click();
      return { success: true, method: 'vision_fallback' };
    }
    throw new Error('No element found at coordinates');
  }
}
```

## User Interface Design

### 1. Extension Popup Interface
```html
<!-- popup.html -->
<div class="navis-popup">
  <header>
    <h1>Navis</h1>
    <p>Don't just browse. Arrive.</p>
  </header>
  
  <main>
    <div class="voice-controls">
      <button id="start-voice" class="voice-button">
        🎤 Tell me your goal
      </button>
      <div id="voice-status" class="status-indicator"></div>
    </div>
    
    <div class="current-plan" id="current-plan" hidden>
      <h3>Navigation Plan:</h3>
      <div id="plan-steps" class="plan-steps"></div>
      <div class="plan-actions">
        <button id="execute-plan">Execute Plan</button>
        <button id="modify-plan">Modify</button>
        <button id="cancel-plan">Cancel</button>
      </div>
    </div>
    
    <div class="execution-progress" id="execution-progress" hidden>
      <h3>Progress:</h3>
      <div class="progress-bar">
        <div id="progress-fill" class="progress-fill"></div>
      </div>
      <p id="current-step-description"></p>
      <button id="pause-execution">Pause</button>
    </div>
  </main>
</div>
```

### 2. Plan Visualization System
```javascript
class PlanDisplay {
  showPlan(plan) {
    const planContainer = document.getElementById('plan-steps');
    planContainer.innerHTML = '';
    
    plan.steps.forEach((step, index) => {
      const stepElement = this.createStepElement(step, index);
      planContainer.appendChild(stepElement);
    });
    
    this.showEstimatedTime(plan.estimatedTime);
    this.highlightConfirmationSteps(plan.steps);
  }
  
  createStepElement(step, index) {
    return `
      <div class="plan-step ${step.requiresConfirmation ? 'requires-confirmation' : ''}">
        <span class="step-number">${index + 1}</span>
        <span class="step-description">${step.description}</span>
        ${step.requiresConfirmation ? '<span class="confirmation-badge">⚠️ Confirmation Required</span>' : ''}
      </div>
    `;
  }
}
```

### 3. Enhanced Visual Feedback
```css
/* Hybrid approach visual styles */
.navis-highlight {
  position: absolute;
  border: 3px solid #007bff;
  border-radius: 4px;
  background: rgba(0, 123, 255, 0.1);
  pointer-events: none;
  z-index: 10000;
  animation: pulse 2s infinite;
}

.navis-plan-preview {
  position: fixed;
  top: 20px;
  right: 20px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 10002;
  max-width: 300px;
}

.plan-step {
  padding: 8px 12px;
  margin: 4px 0;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.plan-step.requires-confirmation {
  border-left-color: #ffc107;
  background-color: #fff3cd;
}

.plan-step.completed {
  border-left-color: #28a745;
  background-color: #d4edda;
}

.vision-fallback-indicator {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #ff6b35;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  z-index: 10003;
}
```

## Data Flow Design

### 1. Hybrid Processing Flow
```
Voice Input → Intent Parser → DOM Analyzer → Structured Planner → Action Executor
     ↓             ↓              ↓               ↓               ↓
User Speaks → Goal Structure → Page Context → Execution Plan → Guided Actions
                                                    ↓
                                            Vision Fallback (if needed)
```

### 2. Performance-Optimized Flow
```
Page Load → DOM Analysis (local) → Element Mapping → Context Caching
     ↓           ↓                      ↓               ↓
New Content → Interactive Elements → Semantic IDs → Ready for Planning
```

### 3. Error Handling with Fallback
```
DOM Action Failure → Vision Fallback → Screenshot Analysis → Alternative Action
      ↓                    ↓                 ↓                    ↓
Element Missing → Computer Vision → Visual Element ID → Coordinate Click
```

### 4. Cost-Optimized API Usage
```
User Goal → Intent Parse (LLM Call 1) → Plan Generation (LLM Call 2) → Local Execution
    ↓              ↓                           ↓                          ↓
Single Voice → Structured Intent → Complete Action Plan → DOM-based Actions
                                                              ↓
                                                    Vision API (only if DOM fails)
```

## LLM Architecture Design

### Architecture Comparison Analysis

#### 1. Rejected: Dynamic Agent Creation (LangChain DeepAgent)
```javascript
// This approach was considered but rejected
class RejectedDeepAgent {
  async handleUserCommand(voiceInput) {
    // Creates new agent for each goal - INEFFICIENT
    const agent = create_agent(
      llm=this.llm,
      tools=this.select_relevant_tools(voiceInput), // UNPREDICTABLE
      system_prompt=this.build_context_prompt(voiceInput)
    );
    
    // Agent creates own routine - UNRELIABLE
    return agent.run(voiceInput); // 5-10 LLM calls, 15+ seconds
  }
}
```

**Rejection Reasons:**
- Unpredictable tool selection
- 5-10x more expensive (multiple LLM calls)
- 10-15 second latency from reasoning loops
- Difficult to debug and control

#### 2. Rejected: Pure Vision Approach (Mariner-style)
```javascript
// This approach was considered but rejected for primary use
class RejectedVisionFirst {
  async processGoal(userGoal) {
    while (!this.goalAchieved()) {
      const screenshot = await this.captureScreen(); // EXPENSIVE
      const analysis = await this.visionModel.analyze(screenshot); // SLOW
      await this.executeAction(analysis.nextAction);
    }
  }
}
```

**Rejection Reasons:**
- 10-20x more expensive than text APIs
- 3-5 second latency per action
- Vision hallucination risks
- High bandwidth requirements

#### 3. Chosen: Hybrid DOM + Structured Planning
```javascript
// Our chosen architecture
class HybridNavisAgent {
  async processVoiceGoal(voiceInput) {
    // STEP 1: Parse intent (1 LLM call, ~2 seconds)
    const intent = await this.intentParser.parse(voiceInput);
    
    // STEP 2: Analyze page structure (LOCAL, ~1 second)
    const pageContext = this.domAnalyzer.getPageContext();
    
    // STEP 3: Create execution plan (1 LLM call, ~2 seconds)
    const plan = await this.structuredPlanner.createPlan(intent, pageContext);
    
    // STEP 4: Execute with confirmations (LOCAL, fast)
    return await this.executeWithConfirmation(plan);
  }
}
```

**Selection Reasons:**
- Only 2 LLM calls total
- DOM analysis is local and fast
- Predictable, structured behavior
- 90% cost reduction vs alternatives

### Detailed Component Architecture

#### Intent Parser Design
```javascript
class IntentParser {
  async parse(voiceInput, pageContext) {
    const systemPrompt = `
    You are a web navigation intent parser. Convert user goals into structured format.
    
    Rules:
    - Output valid JSON only
    - Classify action type accurately
    - Determine confirmation requirements
    - Keep goals specific and actionable
    `;
    
    const userPrompt = `
    User Goal: "${voiceInput}"
    Current Page: ${pageContext.title}
    URL: ${pageContext.url}
    
    Parse into JSON:
    {
      "goal": "specific goal statement",
      "actionType": "navigate|search|fillForm|purchase|contact|read",
      "target": "what user seeks",
      "urgency": "low|medium|high",
      "requiresConfirmation": boolean,
      "confidence": 0.0-1.0
    }
    `;
    
    // Single LLM call with structured output
    return await this.llm.generateStructured(systemPrompt, userPrompt);
  }
}
```

#### Structured Planner Design
```javascript
class StructuredPlanner {
  async createPlan(intent, pageContext) {
    const systemPrompt = `
    You are a web navigation planner. Create efficient, step-by-step plans.
    
    Available Tools:
    - click(elementId): Click interactive element
    - scroll(direction, pixels): Scroll page
    - fillField(elementId, value): Fill form field
    - selectOption(elementId, option): Select dropdown
    - navigate(url): Go to different page
    - wait(seconds): Wait for loading
    
    Rules:
    - Use ONLY available tools
    - Maximum 8 steps per plan
    - Include confirmation for sensitive actions
    - Provide clear descriptions
    - Include fallback options
    `;
    
    const userPrompt = `
    Intent: ${JSON.stringify(intent)}
    Page Elements: ${JSON.stringify(pageContext.interactiveElements)}
    Page Structure: ${JSON.stringify(pageContext.landmarks)}
    
    Create JSON plan:
    {
      "planId": "unique_id",
      "goal": "${intent.goal}",
      "estimatedTime": "seconds",
      "confidence": 0.0-1.0,
      "steps": [
        {
          "stepId": 1,
          "action": "tool_name",
          "target": "element_id",
          "description": "human readable",
          "requiresConfirmation": boolean,
          "expectedOutcome": "what happens next"
        }
      ],
      "fallbackOptions": ["alternative approaches"]
    }
    `;
    
    // Single LLM call with structured output
    return await this.llm.generateStructured(systemPrompt, userPrompt);
  }
}
```

#### Vision Fallback Integration
```javascript
class VisionFallback {
  async handleDOMFailure(step, error, pageContext) {
    // Only activate when DOM approach fails
    console.log(`DOM failed: ${error}. Activating vision fallback.`);
    
    const screenshot = await this.captureScreenshot();
    
    const visionPrompt = `
    The DOM-based action failed. Analyze this screenshot to complete the action.
    
    Failed Action: ${step.action}
    Target Description: ${step.description}
    Error: ${error.message}
    
    Find the target element and provide coordinates or alternative approach.
    `;
    
    const analysis = await this.visionModel.analyze(screenshot, visionPrompt);
    return await this.executeVisionAction(analysis);
  }
}
```

### Performance Optimization Strategy

#### API Call Minimization
```javascript
// Efficient call pattern
const processUserGoal = async (voiceInput) => {
  // Call 1: Intent parsing (required)
  const intent = await intentParser.parse(voiceInput, pageContext);
  
  // Call 2: Plan generation (required)
  const plan = await planner.createPlan(intent, pageContext);
  
  // Call 3: Vision fallback (only if DOM fails - <10% of cases)
  // const visionResult = await visionFallback.handle(failedStep);
  
  // Total: 2 calls normally, 3 calls in edge cases
};
```

#### Cost Comparison
```
Traditional ReAct Agent:
- 8-12 LLM calls per goal
- $0.10-0.30 per navigation
- 15-25 seconds total time

Vision-First Approach:
- 3-8 vision API calls
- $0.50-2.00 per navigation  
- 10-20 seconds total time

Our Hybrid Approach:
- 2 LLM calls normally
- $0.01-0.05 per navigation
- 5-8 seconds total time
- 90% cost reduction
```

### Error Handling and Reliability

#### Graceful Degradation Strategy
```javascript
class ReliabilityManager {
  async executeWithFallbacks(plan) {
    for (const step of plan.steps) {
      try {
        // Primary: DOM-based execution
        const result = await this.domExecutor.execute(step);
        if (result.success) continue;
      } catch (domError) {
        try {
          // Fallback: Vision-based execution
          const result = await this.visionFallback.execute(step, domError);
          if (result.success) continue;
        } catch (visionError) {
          // Final fallback: User intervention
          await this.requestUserHelp(step, [domError, visionError]);
        }
      }
    }
  }
}
```

## Security & Privacy Design

### 1. Permission Model
```json
{
  "permissions": [
    "activeTab",
    "scripting",
    "storage"
  ],
  "host_permissions": [
    "<all_urls>"
  ],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'"
  }
}
```

### 2. Data Handling
- **No Persistent Storage**: All data cleared on tab close
- **Local Processing**: DOM analysis happens locally
- **API Calls**: Only for LLM intent understanding
- **User Control**: All actions require explicit confirmation

### 3. Content Script Isolation
```javascript
// Isolated execution context
(function() {
  'use strict';
  
  // Navis functionality wrapped in IIFE
  // No global variable pollution
  // Clean event listener management
  
})();
```

## Backend Integration Architecture

### Overview
Navis uses a provider-neutral backend architecture so the extension can work with different LLM, storage, observability, and deployment stacks without locking the system to a single cloud vendor.

### Core Service Responsibilities

#### 1. LLM Gateway
**Purpose**: Intent parsing and semantic understanding

**Responsibilities**:
- Route intent parsing requests to the configured model provider
- Normalize model responses into a stable JSON schema
- Support fallback providers when the primary model is unavailable
- Enforce request timeouts, retries, and safety checks

**Implementation**:
```python
import json

class IntentModelGateway:
    def __init__(self, llm_client, model_name):
        self.llm_client = llm_client
        self.model_name = model_name
    
    async def parse_user_goal(self, voice_input, page_context):
        prompt = f"""
        Parse the user's navigation goal and extract semantic requirements.
        
        User Goal: "{voice_input}"
        Current Page: {page_context['title']}
        
        Return JSON with goal, keywords, element_types, and confidence.
        """
        
        result = await self.llm_client.generate(
            model=self.model_name,
            prompt=prompt,
            response_format="json"
        )
        
        return json.loads(result)
```

#### 2. Experience Store
**Purpose**: Store RL training data and user interaction patterns

**Responsibilities**:
- Persist action outcomes and user feedback events
- Support append-only writes for training data
- Allow replay for offline learning and debugging
- Keep storage implementation swappable across file, object, or database backends

**Implementation**:
```python
import json
from datetime import datetime

class ExperienceStorage:
    def __init__(self, storage_client):
        self.storage = storage_client
    
    async def store_experience(self, user_id, experience):
        key = f"experiences/{user_id}/{datetime.now().isoformat()}.json"
        await self.storage.write_json(key, experience)
    
    async def load_user_experiences(self, user_id, limit=100):
        keys = await self.storage.list_keys(f"experiences/{user_id}/", limit=limit)
        return [await self.storage.read_json(key) for key in keys]
```

#### 3. Session State Service
**Purpose**: Fast session state management and short-lived execution context

**Responsibilities**:
- Store active session state for the current task
- Expire stale sessions automatically
- Track recent actions, confidence scores, and feedback

**Implementation**:
```python
from datetime import datetime, timedelta

class SessionStateManager:
    def __init__(self, session_store):
        self.session_store = session_store
    
    async def store_session_state(self, session_id, state):
        expires_at = datetime.now() + timedelta(hours=24)
        await self.session_store.set(
            session_id,
            {
                'state': state,
                'timestamp': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }
        )
    
    async def get_session_state(self, session_id):
        item = await self.session_store.get(session_id)
        return item.get('state') if item else None
    
    async def update_rl_metrics(self, session_id, metrics):
        await self.session_store.patch(session_id, {'rl_metrics': metrics})
```

#### 4. Model Training Pipeline
**Purpose**: Train and deploy reinforcement learning models at scale

**Responsibilities**:
- Consume stored interaction history
- Train updated policies on a scheduled basis
- Version and evaluate candidate models before rollout
- Publish the active model to inference services or bundled artifacts

**Implementation**:
```python
class RLModelTrainer:
    def __init__(self, training_runtime, model_registry):
        self.training_runtime = training_runtime
        self.model_registry = model_registry
    
    async def train_rl_model(self, training_dataset_uri):
        job = await self.training_runtime.start_job(
            entry_point='train_rl.py',
            dataset_uri=training_dataset_uri,
            hyperparameters={
                'learning_rate': 0.01,
                'exploration_rate': 0.1,
                'batch_size': 32
            }
        )
        
        model_artifact = await job.wait_for_result()
        return await self.model_registry.register(model_artifact)
```

#### 5. Vision Fallback Service
**Purpose**: Computer vision for element detection when DOM analysis fails

**Responsibilities**:
- Analyze screenshots with a multimodal model
- Extract candidate targets, coordinates, and confidence
- Return actionable fallback output without changing the rest of the planner

**Implementation**:
```python
import base64

class VisionFallbackService:
    def __init__(self, vision_client):
        self.vision_client = vision_client
    
    async def analyze_screenshot(self, screenshot_base64, goal):
        image_bytes = base64.b64decode(screenshot_base64)
        
        prompt = f"""
        User goal: {goal}
        Identify the UI target that best matches the user's goal.
        Return the coordinates and confidence.
        """
        
        return await self.vision_client.analyze(
            image_bytes=image_bytes,
            prompt=prompt
        )
```

#### 6. Observability Layer
**Purpose**: Monitor system performance and user interactions

**Responsibilities**:
- Record latency, success rates, and fallback frequency
- Centralize logs for backend debugging
- Provide dashboards and alerting through the selected telemetry stack

**Implementation**:
```python
from datetime import datetime

class MetricsLogger:
    def __init__(self, metrics_client):
        self.metrics = metrics_client
    
    async def log_intent_parsing_time(self, duration_ms):
        await self.metrics.record(
            name='intent_parsing_latency_ms',
            value=duration_ms,
            timestamp=datetime.now().isoformat()
        )
    
    async def log_action_success(self, action_type, success):
        await self.metrics.record(
            name=f'{action_type}_success',
            value=1 if success else 0,
            timestamp=datetime.now().isoformat()
        )
    
    async def log_rl_accuracy(self, accuracy):
        await self.metrics.record(
            name='rl_accuracy',
            value=accuracy,
            timestamp=datetime.now().isoformat()
        )
```

#### 7. HTTP Backend
**Purpose**: Run backend APIs without coupling the design to a single deployment platform

**Responsibilities**:
- Expose intent parsing, semantic analysis, and vision fallback endpoints
- Support deployment on local dev servers, containers, or serverless runtimes
- Handle authentication, rate limiting, and CORS consistently

**Implementation**:
```python
import json

def handle_parse_intent(request, intent_service):
    body = json.loads(request.body)
    voice_input = body['voice_input']
    page_context = body['page_context']
    
    intent = intent_service.parse(voice_input, page_context)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(intent)
    }
```

### Backend Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                     Chrome Extension (JS)                  │
│                  ↓ HTTPS API Calls ↓                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Backend Layer                      │
│           (local server, container, or serverless)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ LLM Gateway  │   │ Session      │   │ Experience   │
│ (intent/ML)  │   │ Store        │   │ Store        │
└──────────────┘   └──────────────┘   └──────────────┘
        ↓                                       ↓
┌──────────────┐                      ┌──────────────┐
│ Vision       │                      │ RL Training  │
│ Service      │                      │ Pipeline     │
└──────────────┘                      └──────────────┘
        ↓                                       ↓
┌─────────────────────────────────────────────────────┐
│             Metrics, Logs, and Tracing             │
│               (observability stack)                │
└─────────────────────────────────────────────────────┘
```

### Cost Optimization Principles

1. **Minimize LLM Calls**
   - Use one intent parsing call per user goal
   - Keep semantic analysis local whenever possible

2. **Keep State Lightweight**
   - Store only short-lived session context
   - Use compact event payloads for RL experience logging

3. **Train Asynchronously**
   - Run RL training on a schedule instead of inline with user actions
   - Reuse saved datasets and model versions

4. **Use Vision Sparingly**
   - Reserve screenshot analysis for DOM failures and low-confidence cases

### Security Best Practices

```python
class SecretsProvider:
    def __init__(self, secrets_client):
        self.secrets_client = secrets_client
    
    async def get_api_key(self, secret_name):
        return await self.secrets_client.get(secret_name)

# Use least-privilege service credentials
# Encrypt secrets and data at rest
# Restrict network exposure for backend services
# Maintain audit logs for backend access and configuration changes
```

## Performance Considerations

### 1. Lazy Loading Strategy
- Load components only when needed
- Defer heavy DOM analysis until user activation
- Cache frequently accessed elements

### 2. Memory Management
- Clean up event listeners on navigation
- Limit stored navigation history
- Garbage collect unused DOM references

### 3. Optimization Targets (Updated for Hybrid Architecture)
- Intent parsing latency < 2s (single LLM call)
- DOM analysis completion < 1s (local processing)
- Plan generation < 2s (single LLM call)
- Visual feedback response < 100ms
- Total goal-to-execution time < 6s
- Memory usage < 50MB per tab
- Vision fallback activation < 10% of cases
- API cost reduction > 90% vs vision-only approaches

## Testing Strategy

### 1. Component Testing
- Voice input accuracy testing
- Intent parsing validation (structured output)
- DOM analysis validation (element detection accuracy)
- Structured plan generation testing
- Pre-defined tool execution testing
- Vision fallback activation and accuracy
- Visual feedback rendering and timing

### 2. Integration Testing
- End-to-end hybrid flow testing
- DOM-to-vision fallback scenarios
- Cross-browser compatibility (Chrome focus)
- Website compatibility testing (top 1000 sites)
- Accessibility compliance validation
- Performance benchmarking (API calls, latency)

### 3. User Testing
- Usability testing with target accessibility users
- Voice command accuracy in real environments
- Plan comprehension and confirmation flow
- Accessibility testing with assistive technologies
- Performance testing on various devices and networks
- Real-world navigation scenario validation
