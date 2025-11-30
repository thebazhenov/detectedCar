import os

import uvicorn
from openai import AsyncOpenAI
from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = AsyncOpenAI(api_key=os.getenv("API"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from openai import AsyncOpenAI
import base64
import json

@app.post("/plate")
async def plate(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()

        # base64-кодирование
        encoded = base64.b64encode(image_bytes).decode()
        mime = file.content_type or "image/jpeg"

        system_prompt = "Ты — система распознавания автомобильных номеров. Дай ответ строго JSON."

        ai_response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Определи номер автомобиля. Ответ строго в формате {\"plate\": \"...\"}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{encoded}"
                            }
                        }
                    ]
                }
            ]
        )

        raw = ai_response.choices[0].message.content
        # модель иногда присылает код-блоки → убираем
        raw = raw.replace("```json", "").replace("```", "").strip()

        return json.loads(raw)

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"AI returned non-JSON: {raw}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, port=8080)