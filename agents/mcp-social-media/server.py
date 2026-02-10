from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="MCP Social Media Auto", version="0.1.0")

# Tool models
class PostToPlatformRequest(BaseModel):
    platform: str
    content: str
    image_url: str | None = None

class GetScheduledPostsRequest(BaseModel):
    platform: str | None = None

class EnhanceTextRequest(BaseModel):
    text: str
    style: str | None = None

class TranslateRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str | None = None

@app.post("/tools/post_to_platform")
async def post_to_platform(request: PostToPlatformRequest):
    try:
        # Stub: mock post
        post_id = f"mock_post_{hash(request.content)}"
        return {
            "success": True,
            "post_id": post_id,
            "platform": request.platform,
            "message": "Posted successfully (mock)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_scheduled_posts")
async def get_scheduled_posts(request: GetScheduledPostsRequest):
    try:
        # Stub: mock list
        return {
            "posts": [
                {"id": "1", "platform": "twitter", "content": "Hello", "scheduled_at": "2024-01-01T12:00:00Z"},
                {"id": "2", "platform": "linkedin", "content": "World", "scheduled_at": "2024-01-02T12:00:00Z"}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/enhance_text")
async def enhance_text(request: EnhanceTextRequest):
    try:
        enhanced = f"🚀 {request.text.upper()} 🚀"  # Mock enhance
        return {"enhanced_text": enhanced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/translate")
async def translate(request: TranslateRequest):
    try:
        # Mock translate
        translated = f"[MOCK {request.target_lang.upper()}] {request.text}"
        return {"translated_text": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3459)