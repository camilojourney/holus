# Holus Pipelines

Modular orchestration pipelines connecting Holus products.

## ContentToSocialPipeline

Chains Genpelli (video → clips) → Social Media Auto (captions + schedule posts).

### Usage

```python
import asyncio
from holus.pipelines import ContentToSocialPipeline

pipeline = ContentToSocialPipeline()
result = await pipeline.run(
    video_path="path/to/video.mp4",
    platforms=["twitter", "instagram"]
)
print(result)
```

### Returns

```json
{
  "clips_generated": 3,
  "posts_prepared": 3,
  "posts_scheduled": 2,
  "results": [...]
}
```

Each result: `{"status": "success", "post": {...}, "result": {...}}` or `{"status": "failed", "error": "msg"}`

### Config

Hardcoded server paths relative to workspace. Edit paths if moved.

Errors handled gracefully: failed clips/posts skipped, pipeline continues.