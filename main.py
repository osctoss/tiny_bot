from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()

app = FastAPI()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY not set")

if not os.getenv("MONGO_URI"):
    raise ValueError("MONGO_URI not set")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client["ChatBot"]
collection = db["chat_history"]

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.get("/")
def root():
    return {"status": "ChatBot Running"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        user_id = request.user_id
        user_message = request.message

        previous_chats = list(
            collection.find({"user_id": user_id})
            .sort("_id", -1)
            .limit(5)
        )
        previous_chats.reverse()

        conversation = [
            {
                "role": "system",
                "content": "You are an intelligent educational assistant. Provide concise, accurate, and well-structured answers to academic and learning-related questions."
            }
        ]

        for chat in previous_chats:
            conversation.append({"role": "user", "content": chat["user_message"]})
            conversation.append({"role": "assistant", "content": chat["bot_response"]})

        conversation.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=conversation
        )

        bot_reply = response.choices[0].message.content

        collection.insert_one({
            "user_id": user_id,
            "user_message": user_message,
            "bot_response": bot_reply
        })

        return {"response": bot_reply}

    except Exception as e:
        return {"error": str(e)}