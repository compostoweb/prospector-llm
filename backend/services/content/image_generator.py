"""
services/content/image_generator.py

Geração de imagem para posts do Content Hub via Gemini Nano Banana 2
(gemini-3.1-flash-image-preview).

Estilos disponíveis:
  - clean:       foto/ilustração profissional sem texto
  - with_text:   visual com headline renderizado em destaque
  - infographic: sub-tipos metrics | steps | comparison

Aspect ratios: 4:5 (padrão LinkedIn), 1:1, 16:9
"""

from __future__ import annotations

from integrations.llm.registry import LLMRegistry
from models.content_post import ContentPost

# Paleta de tons por pilar (usada nos prompts)
_PILLAR_TONE: dict[str, str] = {
    "authority": "professional, authoritative, dark blues and grays, corporate aesthetic",
    "case": "warm storytelling, human connection, earthy tones, optimistic",
    "vision": "forward-looking, modern, gradient blues and purples, innovative tech feel",
}

_PILLAR_PT: dict[str, str] = {
    "authority": "autoridade e expertise",
    "case": "caso de sucesso e storytelling",
    "vision": "visão de futuro e inovação",
}


def _build_prompt(
    post: ContentPost,
    style: str,
    sub_type: str | None = None,
    custom_prompt: str | None = None,
) -> str:
    """Constrói o prompt de geração por estilo e pilar."""
    if custom_prompt:
        return custom_prompt

    pillar = post.pillar or "authority"
    tone = _PILLAR_TONE.get(pillar, _PILLAR_TONE["authority"])
    title = post.title or ""

    if style == "clean":
        return (
            f"Professional LinkedIn post visual. Topic: '{title}'. "
            f"Style: {tone}. "
            "Photorealistic or premium illustration. No text overlay whatsoever. "
            "Clean composition, ample negative space, high-quality corporate aesthetics. "
            "Suitable for a B2B LinkedIn feed post."
        )

    if style == "with_text":
        return (
            f"LinkedIn post visual with the following headline prominently displayed: '{title}'. "
            f"Style: {tone}. "
            "Bold, legible typography. The text must be clearly rendered and readable. "
            "Professional background image that complements the text. "
            "Corporate B2B LinkedIn aesthetic."
        )

    # infographic
    if sub_type == "metrics":
        return (
            f"Data-driven infographic for a LinkedIn post about '{title}'. "
            f"Style: {tone}. "
            "Clean corporate charts, numbers, and KPIs visually highlighted. "
            "Minimal clutter. Professional B2B LinkedIn infographic layout."
        )

    if sub_type == "steps":
        return (
            f"Step-by-step process infographic for a LinkedIn post about '{title}'. "
            f"Style: {tone}. "
            "Numbered visual steps (3-5 steps), clean icons, arrows connecting stages. "
            "Professional, minimal. B2B LinkedIn style."
        )

    if sub_type == "comparison":
        return (
            f"Comparison infographic for a LinkedIn post about '{title}'. "
            f"Style: {tone}. "
            "Two-column layout: before vs after, or option A vs option B. "
            "Clear labels, clean dividers. Professional B2B LinkedIn style."
        )

    # fallback: infographic sem sub-tipo
    return (
        f"Professional LinkedIn infographic for '{title}'. "
        f"Style: {tone}. "
        "Clean layout with visual hierarchy. B2B corporate aesthetic."
    )


async def generate_post_image(
    post: ContentPost,
    style: str,
    registry: LLMRegistry,
    *,
    aspect_ratio: str = "4:5",
    sub_type: str | None = None,
    custom_prompt: str | None = None,
    image_size: str = "1K",
) -> tuple[bytes, str]:
    """
    Gera imagem para o post e retorna (image_bytes, prompt_used).

    style: 'clean' | 'with_text' | 'infographic'
    sub_type: 'metrics' | 'steps' | 'comparison' (só para style='infographic')
    aspect_ratio: '4:5' | '1:1' | '16:9'
    image_size: '512' | '1K' | '2K' | '4K'
    """
    prompt = _build_prompt(post, style, sub_type=sub_type, custom_prompt=custom_prompt)
    image_bytes = await registry.generate_image(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
    )
    return image_bytes, prompt
