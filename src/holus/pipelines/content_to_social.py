import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

from mcp.client.stdio import stdio_client
from mcp.types import StdioServerParameters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentToSocialPipeline:
    def __init__(self):
        workspace_path = Path(__file__).resolve().parents[5]
        genpelli_server_path = workspace_path / &quot;github/content_ai_generation/mcp_server/server.py&quot;
        social_server_path = workspace_path / &quot;github/social-media-automatization/mcp_server/server.py&quot;
        
        self.genpelli_params = StdioServerParameters(
            command=sys.executable,
            args=[str(genpelli_server_path)]
        )
        self.social_params = StdioServerParameters(
            command=sys.executable,
            args=[str(social_server_path)]
        )

    async def _call_tool(self, params, tool_name: str, arguments: Dict[str, Any]) -&gt; Dict[str, Any]:
        &quot;&quot;&quot;Call MCP tool and parse JSON result.&quot;&quot;&quot;
        async with stdio_client(params) as client:
            await client.initialize()
            result = await client.call_tool(tool_name, arguments)
            if not result.content:
                raise ValueError(f&quot;No content from {tool_name}&quot;)
            text = result.content[0].text.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f&quot;JSON parse failed for {tool_name}: {e}. Raw: {text[:200]}&quot;)
                return {&quot;raw&quot;: text}

    async def _generate_clips(self, video_path: str) -&gt; List[Dict[str, Any]]:
        # Ingest video
        ingest_res = await self._call_tool(self.genpelli_params, &quot;ingest_video&quot;, {&quot;video_input&quot;: video_path})
        job_id = ingest_res.get(&quot;job_id&quot;)
        logger.info(f&quot;Ingested video, job_id: {job_id}&quot;)

        # Poll for clips
        clips: List[Dict[str, Any]] = []
        prev_len = 0
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) &lt; 600:  # 10 min timeout
            list_res = await self._call_tool(self.genpelli_params, &quot;list_clips&quot;, {})
            current_clips = list_res.get(&quot;clips&quot;, [])
            if len(current_clips) &gt; prev_len:
                prev_len = len(current_clips)
                clips = current_clips[-10:]  # Keep last 10
                logger.info(f&quot;New clips: total {len(clips)}&quot;)
            await asyncio.sleep(10)
        
        if not clips:
            raise ValueError(&quot;No clips generated within timeout&quot;)

        # Get details for up to 5 recent clips
        detailed_clips = []
        for clip in clips[-5:]:
            clip_id = clip.get(&quot;id&quot;)
            if clip_id:
                try:
                    detail_res = await self._call_tool(self.genpelli_params, &quot;get_clip&quot;, {&quot;clip_id&quot;: clip_id})
                    detailed_clip = {**clip, **detail_res}
                    detailed_clips.append(detailed_clip)
                    logger.info(f&quot;Clip {clip_id} ready at {detail_res.get(&#x27;path&#x27;)}&quot;)
                except Exception as e:
                    logger.warning(f&quot;Failed detail for {clip_id}: {e}&quot;)
            else:
                logger.warning(&quot;Clip missing ID&quot;)
        
        logger.info(f&quot;Generated {len(detailed_clips)} detailed clips&quot;)
        return detailed_clips

    async def prepare_posts(self, clips: List[Dict[str, Any]]) -&gt; List[Dict[str, Any]]:
        posts = []
        for i, clip in enumerate(clips):
            try:
                topic = clip.get(&quot;topic&quot;, f&quot;Clip {i+1}&quot;)
                text = f&quot;{topic}&quot;  # Enhance topic as caption
                
                enhance_res = await self._call_tool(
                    self.social_params, 
                    &quot;enhance_text&quot;, 
                    {&quot;text&quot;: text, &quot;content_type&quot;: &quot;post&quot;}
                )
                enhanced_text = enhance_res  # Assume direct text or {&quot;enhanced&quot;: ...}
                if isinstance(enhanced_text, dict):
                    enhanced_text = enhanced_text.get(&quot;text&quot;, enhanced_text.get(&quot;enhanced_text&quot;, text))
                else:
                    enhanced_text = str(enhanced_text)
                
                posts.append({
                    &quot;clip&quot;: clip,
                    &quot;text&quot;: enhanced_text,
                    &quot;media_url&quot;: clip.get(&quot;path&quot;)
                })
                logger.info(f&quot;Prepared post {i+1}: {enhanced_text[:50]}...&quot;)
            except Exception as e:
                logger.warning(f&quot;Failed to prepare post {i}: {e}&quot;)
        return posts

    async def schedule_posts(self, posts: List[Dict[str, Any]], platforms: List[str]) -&gt; List[Dict[str, Any]]:
        results = []
        for i, post in enumerate(posts):
            try:
                post_args = {
                    &quot;text&quot;: post[&quot;text&quot;],
                    &quot;platforms&quot;: platforms,
                    &quot;image_url&quot;: post[&quot;media_url&quot;]
                }
                post_res = await self._call_tool(self.social_params, &quot;post_to_platform&quot;, post_args)
                results.append({
                    &quot;index&quot;: i,
                    &quot;post&quot;: post,
                    &quot;result&quot;: post_res,
                    &quot;status&quot;: &quot;success&quot;
                })
                logger.info(f&quot;Scheduled post {i+1} to {platforms}&quot;)
            except Exception as e:
                results.append({
                    &quot;index&quot;: i,
                    &quot;post&quot;: post,
                    &quot;error&quot;: str(e),
                    &quot;status&quot;: &quot;failed&quot;
                })
                logger.warning(f&quot;Failed to schedule post {i+1}: {e}&quot;)
        return results

    async def run(self, video_path: str, platforms: List[str]) -&gt; Dict[str, Any]:
        try:
            clips = await self._generate_clips(video_path)
            posts = await self.prepare_posts(clips)
            results = await self.schedule_posts(posts, platforms)
            successful = len([r for r in results if r[&quot;status&quot;] == &quot;success&quot;])
            return {
                &quot;clips_generated&quot;: len(clips),
                &quot;posts_prepared&quot;: len(posts),
                &quot;posts_scheduled&quot;: successful,
                &quot;total_failed&quot;: len(results) - successful,
                &quot;results&quot;: results
            }
        except Exception as e:
            logger.error(f&quot;Pipeline run failed: {e}&quot;)
            return {&quot;error&quot;: str(e), &quot;status&quot;: &quot;failed&quot;}