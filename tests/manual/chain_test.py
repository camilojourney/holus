"""Phase 5: Specialist chain test — hook-architect → storyteller → voice-guardian → cta-strategist.

Run with: ANTHROPIC_BASE_URL=http://localhost:8080 ANTHROPIC_API_KEY=x uv run python tests/manual/chain_test.py
"""

import json
import os
import time

os.environ.setdefault("ANTHROPIC_BASE_URL", "http://localhost:8080")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-proxy")

import anthropic

from holus.core.prompt_loader import PromptLoader

client = anthropic.Anthropic(
    base_url=os.environ["ANTHROPIC_BASE_URL"],
    api_key=os.environ["ANTHROPIC_API_KEY"],
)
loader = PromptLoader()


GENERATION_PREFIX = (
    "IMPORTANT: You are in GENERATION MODE. Do NOT search for, read, or access "
    "any files. Do NOT use any tools. Generate content directly based on the brief "
    "provided and the instructions in your system prompt. Respond with text only.\n\n"
)


def call_specialist(agent_id: str, model: str, user_input: str, max_tokens: int = 1200) -> str:
    prompt = loader.get_prompt(agent_id)
    t0 = time.time()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=prompt,
        messages=[{"role": "user", "content": GENERATION_PREFIX + user_input}],
    )
    elapsed = time.time() - t0
    text = resp.content[0].text
    print(f"  [{elapsed:.1f}s] {agent_id} → {len(text)} chars", flush=True)
    return text


def main() -> None:
    import sys

    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)

    print("=" * 60)
    print("SPECIALIST CHAIN TEST")
    print("=" * 60)

    # === STEP 1: Hook Architect ===
    print("\n--- Step 1: hook-architect ---")
    hook_input = (
        "Content brief:\n"
        "- Content pillar: builder_stories\n"
        "- Core claim: I built an AI image generation platform with memory — "
        "every generation tracked, characters consistent, backends swappable.\n"
        "- Product: Pilaster\n"
        "- Key number: 3 architectural layers, thousands of generations tracked\n"
        "- Platform: LinkedIn"
    )
    hook_output = call_specialist("hook-architect", "claude-sonnet-4-6", hook_input)
    print(hook_output[:600])

    # Extract recommended hook — strip markdown code fences if present
    clean = hook_output.strip()
    if clean.startswith("```"):
        # Remove opening ```json and closing ```
        lines = clean.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        clean = "\n".join(lines)

    try:
        hook_data = json.loads(clean)
        rec_idx = hook_data["recommended"]["index"]
        best_hook = hook_data["hooks"][rec_idx]["text"]
        print(f"\n  Recommended hook (JSON parsed): {best_hook}")
        print(f"  Scores: {hook_data['hooks'][rec_idx]['scores']}")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        print(f"\n  [JSON parse failed: {e}]")
        # Try to find hook text in the output
        import re

        match = re.search(r'"text":\s*"([^"]+)"', hook_output)
        if match:
            best_hook = match.group(1)
            print(f"  [regex fallback] Hook: {best_hook}")
        else:
            best_hook = "I built an AI image generation platform with 3 architectural layers. Most AI projects skip the hardest one."
            print(f"  [hardcoded fallback] Hook: {best_hook}")

    # === STEP 2: Storyteller ===
    print("\n--- Step 2: storyteller ---")
    story_input = (
        f"Content brief:\n"
        f"- Content pillar: builder_stories\n"
        f"- Core claim: I built an AI image generation platform with memory.\n"
        f"- Product: Pilaster\n"
        f"- Platform: LinkedIn\n"
        f"- Hook (from hook-architect): {best_hook}\n\n"
        f"Write the narrative body that follows this hook. Do NOT include the hook."
    )
    raw_story = call_specialist("storyteller", "claude-sonnet-4-6", story_input, max_tokens=1500)

    # Extract body from JSON output contract if present
    story_clean = raw_story.strip()
    if story_clean.startswith("```"):
        lines = story_clean.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        story_clean = "\n".join(lines)
    try:
        story_data = json.loads(story_clean)
        story_output = story_data.get("body", story_clean)
        print(f"  [JSON parsed] narrative_arc: {story_data.get('narrative_arc_type')}")
        print(f"  [JSON parsed] voice_check: {story_data.get('voice_check')}")
    except (json.JSONDecodeError, TypeError):
        story_output = raw_story if raw_story else "(empty output)"

    print(story_output[:800])

    # === STEP 3: Voice Guardian (GATE) ===
    print("\n--- Step 3: voice-guardian (GATE) ---")
    full_post = f"{best_hook}\n\n{story_output}"
    guardian_input = (
        f"Review the following LinkedIn post for brand consistency:\n\n"
        f"---\n{full_post}\n---\n\n"
        f"Apply all checks from brand.yaml anti_patterns and voice-profile.md."
    )
    guardian_output = call_specialist(
        "voice-guardian", "claude-haiku-4-5-20251001", guardian_input, max_tokens=800
    )
    print(guardian_output[:600])

    # Determine gate result
    upper = guardian_output.upper()
    if '"PASS"' in upper or "'PASS'" in upper:
        gate_passed = "FAIL" not in upper.split("PASS")[0][-20:]  # Check FAIL isn't before PASS
    else:
        gate_passed = "PASS" in upper and "FAIL" not in upper
    print(f"\n  Gate result: {'PASS' if gate_passed else 'FAIL'}")

    # === STEP 4: CTA Strategist ===
    print("\n--- Step 4: cta-strategist ---")
    cta_input = (
        f"Content brief:\n"
        f"- Content pillar: builder_stories\n"
        f"- Hook: {best_hook}\n"
        f"- Body (first 400 chars): {story_output[:400]}\n\n"
        f"Design 2-3 CTA options for this LinkedIn post."
    )
    cta_output = call_specialist("cta-strategist", "claude-sonnet-4-6", cta_input, max_tokens=800)
    print(cta_output[:600])

    # === FINAL ASSEMBLY ===
    print("\n" + "=" * 60)
    print("ASSEMBLED POST")
    print("=" * 60)
    print()
    print(full_post[:2000])
    print("\n--- CTA options ---")
    print(cta_output[:400])

    print("\n" + "=" * 60)
    print(f"CHAIN RESULT: {'PASS' if gate_passed else 'FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
