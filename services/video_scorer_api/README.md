# 🎬 Video Scorer API

AI-powered video scoring for YouTube creators. Get a 1-10 score before you publish.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
python main.py
# or
uvicorn main:app --reload
```

## Endpoints

### `POST /score/url`
Score a video from URL (YouTube, direct links)

```bash
curl -X POST http://localhost:8000/score/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=..."}'
```

### `POST /score/upload`
Score an uploaded video file

```bash
curl -X POST http://localhost:8000/score/upload \
  -F "file=@video.mp4"
```

### `GET /health`
Health check

```bash
curl http://localhost:8000/health
```

## Response Format

```json
{
  "overall_score": 7.5,
  "breakdown": {
    "hook_strength": "7.5/10",
    "pacing": "8.0/10",
    "visual_quality": "7.0/10",
    "audio_quality": "8.5/10",
    "content_value": "7.5/10",
    "cta_presence": "6.0/10"
  },
  "shorts_candidates": [
    {"start": "0:15", "end": "0:45", "reason": "High energy intro"}
  ],
  "improvements": [
    "Add stronger hook in first 3 seconds"
  ]
}
```

## Scoring Criteria

| Criteria | Weight | Description |
|----------|--------|-------------|
| Hook Strength | 25% | First 5 seconds engaging? |
| Pacing | 20% | Energy consistent, no dead spots? |
| Visual Quality | 15% | Lighting, framing, clarity |
| Audio Quality | 15% | Clear voice, good levels |
| Content Value | 15% | Educational/entertaining? |
| CTA Presence | 10% | Subscribe/like prompt? |

## Pricing

- **Free**: 10 videos (beta)
- **Pay-per-use**: $0.10/video
- **Pro**: $99/mo (10K videos)
- **Enterprise**: $499/mo (unlimited + support)

## Tech Stack

- **Framework**: FastAPI
- **Video Processing**: FFmpeg
- **AI**: Hugging Face CLIP + Whisper
- **Hosting**: Vercel / Railway

## Roadmap

- [x] Basic scoring endpoint
- [ ] FFmpeg frame extraction
- [ ] CLIP visual analysis
- [ ] Whisper transcription
- [ ] YouTube URL support
- [ ] Shorts cut detection
- [ ] Feedback loop (actual vs predicted CTR)

---

Built by Juan Martinez | [Pilaster.ai](https://pilaster.ai)
