"""Tests for deterministic vs AI visual generation strategy."""

from __future__ import annotations

from collections import Counter

from holus.visual.dispatcher import RefinedVisualSource, VisualProvider
from holus.visual.generation_strategy import (
    VisualPaletteName,
    VisualRenderingPath,
    VisualTemplateKind,
    choose_visual_generation_strategy,
)
from holus.visual.proximity_router import (
    VisualProximityMode,
    choose_visual_concept_route,
)


def test_generation_strategy_uses_deterministic_news_battlecard() -> None:
    source = RefinedVisualSource(
        piece_id="amd-nvidia",
        platform="linkedin",
        content_type="image_post",
        refined_text=(
            "AMD Ryzen AI Halo vs NVIDIA DGX Spark: same memory, same bandwidth, "
            "$700 less for local AI developers."
        ),
        topic="AMD vs NVIDIA local AI workstation comparison",
        intended_takeaway="Same memory, same bandwidth, $700 less.",
    )
    route = choose_visual_concept_route(source)
    strategy = choose_visual_generation_strategy(source, route)

    assert strategy.rendering_path == VisualRenderingPath.DETERMINISTIC_TEMPLATE
    assert strategy.provider == VisualProvider.HTML_RENDERER
    assert strategy.template_kind == VisualTemplateKind.NEWS_BATTLECARD
    assert strategy.design_system.palette == VisualPaletteName.RED_GREEN_COMPARE
    assert "numeric delta" in " ".join(strategy.required_inputs)


def test_generation_strategy_sends_metaphors_to_ai_image() -> None:
    source = RefinedVisualSource(
        piece_id="metaphor",
        platform="linkedin",
        content_type="image_post",
        refined_text="A pile of reasonable notes can bury the one card that changes the decision.",
        topic="Reasonable notes bury the signal.",
        intended_takeaway="Expose the one idea under the pile.",
    )
    route = choose_visual_concept_route(source)
    strategy = choose_visual_generation_strategy(source, route)

    assert route.mode == VisualProximityMode.OBJECT_METAPHOR
    assert strategy.rendering_path == VisualRenderingPath.AI_IMAGE
    assert strategy.provider == VisualProvider.CODEX_CLI_IMAGE
    assert strategy.template_kind == VisualTemplateKind.SINGLE_METAPHOR


def test_object_metaphor_beats_broad_team_language() -> None:
    source = RefinedVisualSource(
        piece_id="strategy-pile",
        platform="linkedin",
        content_type="image_post",
        refined_text="Most teams do not have an AI strategy. They have a pile of disconnected prompts.",
        topic="Disconnected AI prompts",
        intended_takeaway="Disconnected prompts are not an AI strategy.",
    )
    route = choose_visual_concept_route(source)
    strategy = choose_visual_generation_strategy(source, route)

    assert route.mode == VisualProximityMode.OBJECT_METAPHOR
    assert strategy.rendering_path == VisualRenderingPath.AI_IMAGE
    assert strategy.template_kind == VisualTemplateKind.SINGLE_METAPHOR


def test_founder_marked_draft_routes_to_story_artifact() -> None:
    source = RefinedVisualSource(
        piece_id="founder-line",
        platform="linkedin",
        content_type="image_post",
        refined_text="The founder points at one awkward sentence in the draft.",
        topic="Founder story artifact",
        intended_takeaway="The marked sentence reveals the failure.",
    )
    route = choose_visual_concept_route(source)
    strategy = choose_visual_generation_strategy(source, route)

    assert route.mode == VisualProximityMode.PERSON_STORY
    assert strategy.template_kind == VisualTemplateKind.ARTIFACT_STORY


def test_map_and_compass_metaphors_route_to_object_metaphor() -> None:
    for text in [
        "A routing system without ownership is a map with no legend.",
        "Without an evaluator, the system is a compass spinning on a metal desk.",
    ]:
        source = RefinedVisualSource(
            piece_id="metaphor",
            platform="linkedin",
            content_type="image_post",
            refined_text=text,
        )
        route = choose_visual_concept_route(source)

        assert route.mode == VisualProximityMode.OBJECT_METAPHOR


def test_generation_strategy_routes_100_cases_with_expected_paths() -> None:
    cases = _strategy_eval_cases()
    assert len(cases) == 100

    counts: Counter[str] = Counter()
    palettes: Counter[str] = Counter()
    for case in cases:
        route = choose_visual_concept_route(case)
        strategy = choose_visual_generation_strategy(case, route)
        expected_path = case["expected_path"]
        expected_template = case["expected_template"]
        assert strategy.rendering_path.value == expected_path, case["piece_id"]
        assert strategy.template_kind.value == expected_template, case["piece_id"]
        assert strategy.design_system.guardrails, case["piece_id"]
        assert strategy.design_system.accent.startswith("#"), case["piece_id"]
        assert strategy.required_inputs, case["piece_id"]
        counts[strategy.rendering_path.value] += 1
        palettes[strategy.design_system.palette.value] += 1

    assert counts[VisualRenderingPath.NO_VISUAL.value] == 10
    assert counts[VisualRenderingPath.DETERMINISTIC_TEMPLATE.value] == 75
    assert counts[VisualRenderingPath.AI_IMAGE.value] == 10
    assert counts[VisualRenderingPath.HYBRID.value] == 5
    assert len(palettes) >= 5


def test_generation_strategy_routes_public_linkedin_examples() -> None:
    examples = _public_linkedin_examples()
    assert len(examples) >= 12

    for example in examples:
        route = choose_visual_concept_route(example)
        strategy = choose_visual_generation_strategy(example, route)
        assert strategy.rendering_path.value == example["expected_path"], example["piece_id"]
        assert strategy.template_kind.value == example["expected_template"], example["piece_id"]
        assert strategy.provider.value == example["expected_provider"], example["piece_id"]


def _public_linkedin_examples() -> list[dict[str, str]]:
    return [
        {
            "piece_id": "linkedin_amd_nvidia_battlecard",
            "topic": "AMD Ryzen AI Halo vs NVIDIA DGX Spark",
            "refined_text": (
                "AMD Ryzen AI Halo vs NVIDIA DGX Spark: same memory, same bandwidth, "
                "$700 less, with Windows and Linux support."
            ),
            "intended_takeaway": "Same memory and bandwidth, lower price.",
            "source_url": "https://www.linkedin.com/posts/alexwang2911_amd-just-showed-the-worlds-smallest-ai-development-activity-7472526463829729281-Op0M",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.NEWS_BATTLECARD.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_ai_models_sales_table",
            "topic": "5 best AI models for Sales",
            "refined_text": (
                "Compare AI models for sales by use case, prompt examples, speed, and cost."
            ),
            "intended_takeaway": "Pick the AI model by sales job, not hype.",
            "source_url": "https://www.linkedin.com/posts/superhuman-co_superhuman-ai-already-helps-you-read-write-activity-7298024425243693057-In4d",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.CLAIM_CHART.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_b2b_b2c_comparison",
            "topic": "B2B vs B2C marketing",
            "refined_text": (
                "B2B vs B2C marketing: B2B has multiple stakeholders, shared buying projects, "
                "and ROI logic. B2C has simpler consumer decision paths."
            ),
            "intended_takeaway": "The buying process is the real difference.",
            "source_url": "https://www.linkedin.com/posts/the-midnight-marketer_b2b-and-b2c-marketing-have-one-big-difference-activity-7448308815860531200-xN-q",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.NEWS_BATTLECARD.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_carousel_or_infographic",
            "topic": "Carousel or infographic",
            "refined_text": (
                "Carousel document posts get saves, resurfacing, and compounding reach. "
                "Infographics get a glance. Document posts carry reach and engagement multipliers."
            ),
            "intended_takeaway": "Use carousel when saves and dwell time matter.",
            "source_url": "https://www.linkedin.com/posts/melaniegoodman-training-marketing-employeeadvocacy_carousel-or-infographic-which-is-better-for-activity-7456953268796280835-yD64",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.CLAIM_CHART.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_document_posts_outperform",
            "topic": "Document posts outperform text",
            "refined_text": (
                "Document posts hit 12.4% engagement, text posts 2.8%, video 5.1%, "
                "single image 1.9%. Same audience, same timing, 443% difference."
            ),
            "intended_takeaway": "Document posts outperform other formats in this test.",
            "source_url": "https://www.linkedin.com/posts/umoh-emmanuel_document-posts-are-hitting-660-engagement-activity-7430598089398407169-w3BB",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.CLAIM_CHART.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_carousel_evolution",
            "topic": "LinkedIn carousels evolved",
            "refined_text": (
                "LinkedIn carousels changed from square JPEGs and long decks to vertical PDFs, "
                "value-dense slides, authentic textures, and saves-focused design."
            ),
            "intended_takeaway": "Carousel design evolved toward dense saveable frameworks.",
            "source_url": "https://www.linkedin.com/posts/7285-prakash-gupta_are-linkedin-carousels-dead-short-answer-activity-7422477343706886144-8mov",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.CLAIM_CHART.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_algorithm_update",
            "topic": "LinkedIn ranking system changed",
            "refined_text": (
                "LinkedIn replaced its ranking system. The new playbook is core topics, "
                "strong hooks, semantic relevance, and proof-driven posts."
            ),
            "intended_takeaway": "Topic discipline and proof matter more now.",
            "source_url": "https://www.linkedin.com/posts/roxinekee_linkedin-just-replaced-its-entire-ranking-activity-7438199689646092288-sXHA",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.OPERATING_MAP.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_infographic_style_rules",
            "topic": "Infographic style rules",
            "refined_text": (
                "Put every box in a grid. Show clear font hierarchy. Allow breathing room. "
                "Use a working color palette. Keep padding and stroke widths consistent."
            ),
            "intended_takeaway": "Pixel-perfect infographics come from grid, hierarchy, and spacing.",
            "source_url": "https://www.linkedin.com/posts/vincent-angelo-coach_how-to-make-pixel-perfect-infographics-activity-7396925098802204672-bOqf",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.OPERATING_MAP.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_top_creator_templates",
            "topic": "100 LinkedIn templates",
            "refined_text": (
                "100 LinkedIn infographic templates helped convert plain visuals into repeatable "
                "content systems and recognizable brand formats."
            ),
            "intended_takeaway": "Repeatable templates beat blank-canvas design.",
            "source_url": "https://www.linkedin.com/posts/will-mctighe_these-100-linkedin-templates-helped-me-get-activity-7325142260453408768-8Icz",
            "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
            "expected_template": VisualTemplateKind.OPERATING_MAP.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
        {
            "piece_id": "linkedin_notes_metaphor",
            "topic": "Specific examples beat generic phrases",
            "refined_text": (
                "A pile of generic phrases can bury the one specific example that makes the post useful."
            ),
            "intended_takeaway": "Expose the specific example under the pile.",
            "source_url": "https://www.linkedin.com/posts/rosannacampbell_i-have-16000-followers-on-linkedin-and-activity-7424099645745876992-g7jV",
            "expected_path": VisualRenderingPath.AI_IMAGE.value,
            "expected_template": VisualTemplateKind.SINGLE_METAPHOR.value,
            "expected_provider": VisualProvider.CODEX_CLI_IMAGE.value,
        },
        {
            "piece_id": "linkedin_founder_story_artifact",
            "topic": "Creator voice note",
            "refined_text": (
                "The creator records a voice note, then points at the one sentence that sounds human "
                "instead of copied from top creators."
            ),
            "intended_takeaway": "The marked sentence reveals the real voice.",
            "source_url": "https://www.linkedin.com/posts/rosannacampbell_i-have-16000-followers-on-linkedin-and-activity-7424099645745876992-g7jV",
            "expected_path": VisualRenderingPath.HYBRID.value,
            "expected_template": VisualTemplateKind.ARTIFACT_STORY.value,
            "expected_provider": VisualProvider.CODEX_CLI_IMAGE.value,
        },
        {
            "piece_id": "linkedin_single_image_text_post",
            "topic": "If the image needs the caption",
            "refined_text": (
                "If the image needs the caption to explain itself, it is not done. "
                "The visual must carry the core idea first."
            ),
            "intended_takeaway": "If the image needs the caption, it is not done.",
            "source_url": "user-provided-reference",
            "expected_path": VisualRenderingPath.NO_VISUAL.value,
            "expected_template": VisualTemplateKind.NO_VISUAL.value,
            "expected_provider": VisualProvider.HTML_RENDERER.value,
        },
    ]


def _strategy_eval_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for index in range(20):
        cases.append(
            {
                "piece_id": f"battlecard_{index}",
                "topic": f"Tool A vs Tool B pricing comparison {index}",
                "refined_text": (
                    f"Tool A vs Tool B: same output quality, same workflow coverage, "
                    f"${100 + index} less for teams."
                ),
                "intended_takeaway": "Same useful outcome, lower cost.",
                "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
                "expected_template": VisualTemplateKind.NEWS_BATTLECARD.value,
            }
        )
    for index in range(20):
        cases.append(
            {
                "piece_id": f"chart_{index}",
                "topic": f"Metric changed by {index + 12}%",
                "refined_text": (
                    f"Carousel saves rose {index + 12}% while replies fell. "
                    "The chart should show attention and intent moving apart."
                ),
                "intended_takeaway": "Attention and intent can diverge.",
                "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
                "expected_template": VisualTemplateKind.CLAIM_CHART.value,
            }
        )
    for index in range(20):
        cases.append(
            {
                "piece_id": f"workflow_{index}",
                "topic": f"Workflow handoff quality {index}",
                "refined_text": (
                    "The workflow improves when planning, execution, review, and fallback "
                    f"each get a separate lane. Handoff {index} is the bottleneck."
                ),
                "intended_takeaway": "Separate the lanes before asking for better output.",
                "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
                "expected_template": VisualTemplateKind.OPERATING_MAP.value,
            }
        )
    for index in range(15):
        cases.append(
            {
                "piece_id": f"product_{index}",
                "topic": f"Review queue needs reason {index}",
                "refined_text": (
                    "A content queue should show a selected draft, a fit signal, "
                    f"and an approve or revise decision state for reviewer {index}."
                ),
                "intended_takeaway": "Put the reason beside the draft.",
                "expected_path": VisualRenderingPath.DETERMINISTIC_TEMPLATE.value,
                "expected_template": VisualTemplateKind.DECISION_SURFACE.value,
            }
        )
    for index in range(10):
        cases.append(
            {
                "piece_id": f"typography_{index}",
                "topic": f"If the image needs the caption, it is not done {index}",
                "refined_text": (
                    "The LinkedIn image should carry the thesis before the caption expands it. "
                    f"If the visual needs the caption, it is decoration {index}."
                ),
                "intended_takeaway": "If the image needs the caption, it is not done.",
                "expected_path": VisualRenderingPath.NO_VISUAL.value,
                "expected_template": VisualTemplateKind.NO_VISUAL.value,
            }
        )
    for index in range(10):
        cases.append(
            {
                "piece_id": f"metaphor_{index}",
                "topic": f"Notes bury the signal {index}",
                "refined_text": (
                    f"A pile of notes can bury the one card that changes the decision {index}."
                ),
                "intended_takeaway": "Expose the useful card under the pile.",
                "expected_path": VisualRenderingPath.AI_IMAGE.value,
                "expected_template": VisualTemplateKind.SINGLE_METAPHOR.value,
            }
        )
    for index in range(5):
        cases.append(
            {
                "piece_id": f"person_{index}",
                "topic": f"Founder pause reveals the requirement {index}",
                "refined_text": (
                    f"The founder pauses and points at one awkward line. That human mark {index} "
                    "reveals what the system failed to explain."
                ),
                "intended_takeaway": "The marked artifact reveals the requirement.",
                "expected_path": VisualRenderingPath.HYBRID.value,
                "expected_template": VisualTemplateKind.ARTIFACT_STORY.value,
            }
        )
    return cases
