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
    "authority": "dark navy blue and gray color palette, corporate and authoritative",
    "case": "warm amber and green color palette, human and optimistic",
    "vision": "gradient blue and purple color palette, futuristic and innovative",
}

_PILLAR_BG: dict[str, str] = {
    "authority": "dark navy blue",
    "case": "warm off-white or light amber",
    "vision": "deep purple to blue gradient",
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
    bg = _PILLAR_BG.get(pillar, _PILLAR_BG["authority"])
    title = post.title or ""

    if style == "clean":
        return (
            f"Minimalist professional LinkedIn post cover image about '{title}'. "
            f"Style: flat design illustration, {tone}. "
            f"Background: solid {bg}. Abstract geometric shapes or simple icons. "
            "NO people, NO photographs, NO photorealistic elements. "
            "Clean layout, ample negative space. Subtle texture allowed. "
            "Professional B2B aesthetic, vector illustration style."
        )

    if style == "with_text":
        return (
            f"LinkedIn post cover with bold headline text. "
            f"Main title: '{title}'. "
            f"Style: graphic design poster, {tone}. "
            f"Background: {bg} with geometric shapes. "
            "Large, bold, clearly readable sans-serif typography. "
            "The headline text must be perfectly legible and prominently centered. "
            "NO people, NO photographs. Pure graphic design."
        )

    # infographic styles — all must avoid photos
    _no_photo = (
        "IMPORTANT: This must be a flat design infographic with icons and shapes. "
        "NO photographs, NO realistic images, NO people photos. "
        "Use only flat vector icons, geometric shapes, charts, and labels. "
    )

    if sub_type == "metrics":
        return (
            f"Clean data infographic for LinkedIn post about '{title}'. "
            f"Style: flat design, {tone}, {bg} background. "
            "Contains: large KPI numbers (placeholder values), bar charts or donut charts, "
            "clean data labels, minimal grid lines. "
            "Layout: 2-3 key metrics with icons above each number. "
            + _no_photo
            + "Professional B2B infographic, vector style."
        )

    if sub_type == "steps":
        return (
            f"Step-by-step process infographic for LinkedIn post about '{title}'. "
            f"Style: flat design, {tone}, {bg} background. "
            "Contains: 3 to 5 numbered steps in vertical or horizontal flow, "
            "simple flat icons per step, arrow connectors between steps, short text labels. "
            "Clean minimal layout with clear visual hierarchy. "
            + _no_photo
            + "Professional B2B infographic, vector style."
        )

    if sub_type == "comparison":
        return (
            f"Two-column comparison infographic for LinkedIn post about '{title}'. "
            f"Style: flat design, {tone}. "
            "Left column: labeled 'Antes' or 'Opção A' with a contrasting background color. "
            "Right column: labeled 'Depois' or 'Opção B' with an accent color background. "
            "Each column has 3-4 bullet points with flat icons. "
            "Bold divider line in the center, clear column headers. "
            + _no_photo
            + "Professional B2B comparison infographic, vector style."
        )

    # fallback: generic infographic
    return (
        f"Professional LinkedIn infographic for '{title}'. "
        f"Style: flat design, {tone}, {bg} background. "
        "Clean visual hierarchy, icons, and data elements. "
        + _no_photo
        + "B2B corporate aesthetic, vector illustration."
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
