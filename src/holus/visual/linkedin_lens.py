"""LinkedIn impact lens for social image production plans.

The lens turns a generic visual plan into a stronger LinkedIn-native artifact:
clear news hook, evidence structure, mobile hierarchy, and an explicit verdict.
It is based on observed high-performing infographic patterns, not on private
LinkedIn view-count data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from holus.visual.proximity_router import VisualConceptRoute, VisualProximityMode

if TYPE_CHECKING:
    from holus.visual.production_plan import VisualProductionPlan


def apply_linkedin_impact_lens(
    plan: VisualProductionPlan,
    route: VisualConceptRoute,
    source: Any,
) -> VisualProductionPlan:
    """Strengthen a visual plan with LinkedIn-native impact rules."""
    pattern = _choose_pattern(route, source)
    rules = _lens_rules(pattern, route.mode)
    return plan.model_copy(
        update={
            "scene_script": f"{plan.scene_script} LinkedIn impact lens: {rules['scene']}",
            "composition_script": (
                f"{plan.composition_script} LinkedIn impact lens: {rules['composition']}"
            ),
            "required_elements": [
                *plan.required_elements,
                *rules["required"],
            ],
            "forbidden_elements": [
                *plan.forbidden_elements,
                *rules["forbidden"],
            ],
            "compliance_checks": [
                *plan.compliance_checks,
                *rules["checks"],
            ],
        }
    )


def _choose_pattern(route: VisualConceptRoute, source: Any) -> str:
    text = _source_text(source).lower()
    if any(signal in text for signal in (" vs ", " versus ", "$", " less", " cheaper")):
        return "news_battlecard"
    if route.mode == VisualProximityMode.CHART:
        return "claim_metric_verdict"
    if route.mode == VisualProximityMode.PRODUCT_SCENE:
        return "decision_surface"
    if route.mode == VisualProximityMode.WORKFLOW:
        return "operating_map"
    if route.mode == VisualProximityMode.PERSON_STORY:
        return "artifact_story"
    if route.mode == VisualProximityMode.TYPOGRAPHY_CARD:
        return "thesis_poster"
    return "single_metaphor"


def _lens_rules(pattern: str, mode: VisualProximityMode) -> dict[str, list[str] | str]:
    common_required = [
        "one scroll-stopping top claim",
        "one visible evidence structure below the claim",
        "one clear verdict or takeaway panel",
        "mobile-first hierarchy readable at thumbnail size",
    ]
    common_forbidden = [
        "generic motivational poster",
        "pretty scene without evidence",
        "unstructured collage",
        "fake unreadable paragraphs",
        "made-up logos or unverifiable brand marks",
    ]
    common_checks = [
        "Can the viewer repeat the claim in two seconds?",
        "Is there a concrete proof block below the hook?",
        "Is the final verdict visually separate from the evidence?",
    ]

    if pattern == "news_battlecard":
        return {
            "scene": (
                "Build a news comparison battlecard: headline claim, one numeric delta, two compared "
                "subjects, compact evidence table, and verdict strip. This is an artifact, not a scene."
            ),
            "composition": (
                "Use a strong vertical hierarchy: small context line, huge claim, accent number, "
                "two-column comparison, evidence grid, bottom verdict. Use red/green or warm/cool "
                "contrast only when it maps to the comparison."
            ),
            "required": [
                *common_required,
                "two-column comparison structure",
                "one dominant numeric delta",
                "compact evidence grid with 3-5 rows",
                "small source or caveat line when claims are factual",
            ],
            "forbidden": [
                *common_forbidden,
                "product logos unless source/licensing is explicit",
                "invented prices, benchmarks, or specs",
            ],
            "checks": [
                *common_checks,
                "Does the comparison teach the viewer what changed?",
                "Are all factual numbers sourced or marked as illustrative?",
            ],
        }

    if pattern == "claim_metric_verdict":
        return {
            "scene": "Build a claim-led chart card with one metric contrast and a verdict.",
            "composition": (
                "Top third is the claim. Middle is one chart. Bottom-right is the verdict/callout. "
                "Keep axes and labels minimal but readable."
            ),
            "required": [*common_required, "one chart only", "one highlighted metric delta"],
            "forbidden": [*common_forbidden, "dashboard chrome", "multiple unrelated charts"],
            "checks": [*common_checks, "Is there exactly one plotted relationship?"],
        }

    if pattern == "decision_surface":
        return {
            "scene": "Build a product decision artifact, not a fake screenshot.",
            "composition": (
                "Show selected item -> reason/evidence -> decision. Use short real labels and large UI blocks."
            ),
            "required": [*common_required, "selected item", "reason/evidence panel", "decision badge"],
            "forbidden": [*common_forbidden, "dense SaaS dashboard", "tiny pseudo UI text"],
            "checks": [*common_checks, "Can the viewer see what was decided and why?"],
        }

    if pattern == "operating_map":
        return {
            "scene": "Build an operating map with the bottleneck made visible.",
            "composition": (
                "Use 4-6 stages, one input, one output, and one highlighted failure/handoff point."
            ),
            "required": [*common_required, "input boundary", "output boundary", "highlighted bottleneck"],
            "forbidden": [*common_forbidden, "unlabeled modules", "decorative arrows"],
            "checks": [*common_checks, "Can the viewer identify the sequence and the bottleneck?"],
        }

    if pattern == "artifact_story":
        return {
            "scene": "Show the artifact causing the human decision; the artifact is more important than the face.",
            "composition": (
                "Use one hand/gesture/silhouette plus one marked artifact. Avoid portrait-first framing."
            ),
            "required": [*common_required, "marked artifact", "visible action gesture"],
            "forbidden": [*common_forbidden, "smiling stock portrait", "generic laptop photo"],
            "checks": [*common_checks, "Is the human action tied to one artifact?"],
        }

    if pattern == "thesis_poster":
        return {
            "scene": "Make the sentence itself the artifact.",
            "composition": (
                "Use one huge thesis, one support line, one accent mark, and no illustration that competes."
            ),
            "required": [*common_required, "exact thesis text", "one support line"],
            "forbidden": [*common_forbidden, "extra quote fragments", "decorative background scene"],
            "checks": [*common_checks, "Is the thesis legible and exact?"],
        }

    return {
        "scene": "Use one metaphor object as evidence for the idea, not as decoration.",
        "composition": "One object, one tension, one verdict line. Leave negative space.",
        "required": [*common_required, "single metaphor object", "visible tension"],
        "forbidden": [*common_forbidden, "premium desk object pile"],
        "checks": [*common_checks, "Can the metaphor be explained in one sentence?"],
    }


def _source_text(source: Any) -> str:
    if isinstance(source, dict):
        return " ".join(
            str(source.get(key, "") or "")
            for key in ("refined_text", "text", "topic", "headline", "intended_takeaway")
        )
    return " ".join(
        str(getattr(source, key, "") or "")
        for key in ("refined_text", "topic", "headline", "intended_takeaway")
    )
