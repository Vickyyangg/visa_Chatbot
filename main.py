import json
import os
import random
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

# ✅ Create FastAPI app
app = FastAPI()

# ✅ Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to specific domain if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ API Key and Endpoint for OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ✅ Load conversation examples
DATA_PATH = Path(__file__).parent / "data" / "conversations.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    conversations_data = json.load(f)

# ✅ Input model
class MessageInput(BaseModel):
    messages: list[str]

# ✅ Friendly fallback responses for irrelevant inputs
FALLBACK_RESPONSES = [
    "I might not be great with that, but ask me anything about visas!",
    "Let’s stick to visa support — ask me anything on that!",
]

# ✅ Relevance check
def is_relevant(message: str):
    friendly_openers = ["hello", "hi", "hey", "how are you", "good morning", "good evening", "thank you"]
    visa_keywords = ["visa", "apply", "application", "document", "canada", "sop", "deadline", "graduate", "dtv"]
    message_lower = message.lower()
    return any(kw in message_lower for kw in visa_keywords + friendly_openers)

# ✅ Interest detection
def detect_interest(messages: list[str]):
    interest_keywords = ["ready", "apply now", "send documents", "next step", "book a call", "how soon"]
    for msg in messages[-3:]:
        if any(kw in msg.lower() for kw in interest_keywords):
            return True
    return False

# ✅ Prompt builder using few-shot learning
def build_few_shot_prompt(latest_message: str):
    examples = []
    for convo_id, convo in conversations_data.items():
        msgs = convo.get("messages", [])
        for i in range(len(msgs) - 1):
            if msgs[i]["sender"] == "customer" and msgs[i + 1]["sender"] == "other":
                cust = msgs[i]["text"].replace("\n", " ")
                agent = msgs[i + 1]["text"].replace("\n", " ")
                examples.append((cust, agent))
            if len(examples) >= 3:
                break
        if len(examples) >= 3:
            break

    prompt_text = "You are a visa support agent. Speak casually and naturally like a human — no AI tone.\nHere are some examples:\n\n"
    for cust, agent in examples:
        prompt_text += f"Customer: {cust}\nAgent: {agent}\n\n"
    prompt_text += f"Now respond to this:\nCustomer: {latest_message}\nAgent:"

    return prompt_text

# ✅ Main API endpoint
@app.post("/respond")
async def respond(input: MessageInput):
    try:
        latest_message = input.messages[-1]

        # ❌ If not relevant, send a casual fallback
        if not is_relevant(latest_message):
            fallback_reply = random.choice(FALLBACK_RESPONSES)
            return {"reply": fallback_reply, "high_interest": False}

        # ✅ Build few-shot prompt
        prompt = build_few_shot_prompt(latest_message)

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://yourdomain.com",  # Optional
            "X-Title": "VisaBot Assistant"
        }

        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful visa support assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }

        # ✅ Send request to OpenRouter
        async with httpx.AsyncClient() as client:
            response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

        reply = result["choices"][0]["message"]["content"].strip()
        high_interest = detect_interest(input.messages)

        return {"reply": reply, "high_interest": high_interest}

    except Exception as e:
        print(f"❌ Error in /respond: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong.")
