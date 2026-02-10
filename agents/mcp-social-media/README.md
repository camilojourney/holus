# MCP Social Media Wrapper

## Overview
FastAPI server exposing MCP tools for social media automation.

Port: 3459

## Installation
```bash
pip install -r requirements.txt
```

## Run Server
```bash
uvicorn server:app --host 0.0.0.0 --port 3459 --reload
```

Or:
```bash
python server.py
```

## Tools (POST /tools/&lt;name&gt;)

### post_to_platform
**Request:**
```json
{
  "platform": "twitter",
  "content": "Hello world!",
  "image_url": "https://example.com/img.jpg"
}
```
**Response:** `{"success": true, "post_id": "..."}`

### get_scheduled_posts
**Request:**
```json
{
  "platform": "twitter"
}
```
**Response:** `{"posts": [...]}`

### enhance_text
**Request:**
```json
{
  "text": "hello",
  "style": "excited"
}
```
**Response:** `{"enhanced_text": "..."}`

### translate
**Request:**
```json
{
  "text": "hello",
  "target_lang": "es",
  "source_lang": "en"
}
```
**Response:** `{"translated_text": "..."}`

## Stubs
All tools return mock data. Replace implementations with real APIs.