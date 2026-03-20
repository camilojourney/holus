"""Icon registry for infographic rendering.

Maps icon names to display names and brand colors. Used by InfographicRenderer
to draw colored icon cells. Real SVG icons can be added later — for now, each
icon is a colored rounded rectangle with its display name as a text label.
"""

from __future__ import annotations


class IconRegistry:
    """Registry of known icon names with display names and colors.

    Usage::

        registry = IconRegistry()
        display_name, hex_color = registry.get_icon("claude")
        # ("Claude", "#D97706")
    """

    _DEFAULT_COLOR = "#9CA3AF"

    _ICONS: dict[str, tuple[str, str]] = {
        # AI models & companies
        "claude": ("Claude", "#D97706"),
        "openai": ("OpenAI", "#10A37F"),
        "gpt": ("GPT", "#10A37F"),
        "gemini": ("Gemini", "#4285F4"),
        "llama": ("Llama", "#0467DF"),
        "mistral": ("Mistral", "#FF7000"),
        "cohere": ("Cohere", "#39594D"),
        "anthropic": ("Anthropic", "#D97706"),
        "deepseek": ("DeepSeek", "#4D6BFE"),
        "perplexity": ("Perplexity", "#20808D"),
        # Programming languages & tools
        "python": ("Python", "#3776AB"),
        "javascript": ("JavaScript", "#F7DF1E"),
        "typescript": ("TypeScript", "#3178C6"),
        "rust": ("Rust", "#DEA584"),
        "go": ("Go", "#00ADD8"),
        "java": ("Java", "#ED8B00"),
        "docker": ("Docker", "#2496ED"),
        "kubernetes": ("K8s", "#326CE5"),
        "git": ("Git", "#F05032"),
        "github": ("GitHub", "#6E7681"),
        # AI/ML concepts
        "rag": ("RAG", "#7C3AED"),
        "fine-tuning": ("Fine-tune", "#EC4899"),
        "embedding": ("Embedding", "#06B6D4"),
        "vector-db": ("VectorDB", "#00C7B7"),
        "transformer": ("Transformer", "#FF6F00"),
        "diffusion": ("Diffusion", "#A855F7"),
        "agent": ("Agent", "#F59E0B"),
        "mcp": ("MCP", "#6366F1"),
        # Cloud & infra
        "aws": ("AWS", "#FF9900"),
        "gcp": ("GCP", "#4285F4"),
        "azure": ("Azure", "#0078D4"),
        "vercel": ("Vercel", "#5C6370"),
        "supabase": ("Supabase", "#3ECF8E"),
        "redis": ("Redis", "#DC382D"),
        "postgres": ("Postgres", "#4169E1"),
        # Monitoring & observability
        "grafana": ("Grafana", "#F46800"),
        "datadog": ("Datadog", "#632CA6"),
        "prometheus": ("Prometheus", "#E6522C"),
        "langfuse": ("Langfuse", "#4F46E5"),
        # Frontend
        "react": ("React", "#61DAFB"),
        "nextjs": ("Next.js", "#5C6370"),
        "tailwind": ("Tailwind", "#06B6D4"),
        # Messaging
        "slack": ("Slack", "#4A154B"),
        "telegram": ("Telegram", "#26A5E4"),
        # Skills
        "code": ("Code", "#22C55E"),
        "specs": ("Specs", "#3B82F6"),
        "research": ("Research", "#8B5CF6"),
        "ux": ("UX", "#EC4899"),
        "verify": ("Verify", "#F59E0B"),
        "maintenance": ("Maint.", "#6366F1"),
        # Eval
        "security": ("Security", "#EF4444"),
        "eval": ("Eval", "#14B8A6"),
    }

    def get_icon(self, name: str) -> tuple[str, str]:
        """Return (display_name, hex_color) for an icon name.

        If the icon name is not found, returns the raw name with a default gray color.
        """
        if name in self._ICONS:
            return self._ICONS[name]
        return (name, self._DEFAULT_COLOR)

    def has_icon(self, name: str) -> bool:
        """Check if an icon name is registered."""
        return name in self._ICONS

    @property
    def known_icons(self) -> list[str]:
        """Return all registered icon names."""
        return list(self._ICONS.keys())
