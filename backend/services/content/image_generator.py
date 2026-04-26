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

_PILLAR_MOOD: dict[str, str] = {
    "authority": "credible, precise, executive, strategic",
    "case": "practical, optimistic, grounded, results-oriented",
    "vision": "forward-looking, inventive, ambitious, high-clarity",
}

_VISUAL_DIRECTION_BRIEF: dict[str, str] = {
    "auto": (
        "Choose an original visual direction that fits the subject instead of defaulting to the same palette. "
        "Vary composition, dominant colors, and icon language between generations. "
        "Avoid repeating the common amber-and-green look unless the topic clearly calls for it."
    ),
    "editorial": (
        "Editorial cover style, premium magazine layout, restrained typography, sophisticated composition, "
        "balanced whitespace, elegant contrast, modern B2B art direction."
    ),
    "minimal": (
        "Minimalist design, very clean layout, generous negative space, restrained color palette, few elements, "
        "simple geometric accents, calm and polished aesthetic."
    ),
    "bold": (
        "Bold campaign look, high contrast, striking shapes, dynamic framing, confident hierarchy, vivid accents, "
        "strong visual impact without looking playful or generic."
    ),
    "organic": (
        "Warm contemporary design, softer shapes, more natural rhythm, approachable color relationships, "
        "subtle texture, modern but human-centered B2B aesthetic."
    ),
}

_WITH_TEXT_AUTO_BRIEF = (
    "Default toward premium editorial minimalism for text-led covers. "
    "Prefer a restrained composition, a calm background, generous negative space, and very few accent elements. "
    "Avoid busy tech-diagram aesthetics, dense geometric clutter, and infographic-like layouts."
)

_WITH_TEXT_BACKGROUND_HEX = "#051932"


def _build_with_text_aspect_ratio_brief(aspect_ratio: str) -> str:
    if aspect_ratio == "16:9":
        return (
            "For a 16:9 landscape canvas, use a strong widescreen editorial layout with larger emphasis treatments. "
            "If one phrase is highlighted, it must sit inside a clearly visible solid rectangular accent block with generous padding, not a thin underline or subtle marker. "
            "Make the highlight bold enough to read immediately at thumbnail size. "
            "Prefer 2 to 3 balanced text lines with a wide, obvious emphasis area rather than many short stacked fragments."
        )
    if aspect_ratio == "1:1":
        return "For a 1:1 square canvas, keep the composition centered or slightly offset, with balanced margins and a compact but strong emphasis block."
    return "For a 4:5 portrait canvas, use a tall editorial composition with generous breathing room and a clearly visible emphasis treatment."


def _build_general_constraints(style: str) -> str:
    no_photo = (
        "NO people, NO photographs, NO photorealistic elements, NO stock-photo look. "
        "Prefer vector illustration, graphic design, iconography, abstract shapes, or stylized composition."
    )
    if style == "infographic":
        return (
            "This must read as a professional infographic for LinkedIn. "
            "Use flat vector icons, charts, labels, dividers, and a clear information hierarchy. "
            "DO NOT add any website URL, domain, footer CTA, brand signature, company name, email, QR code, "
            "watermark, social handle, or invented contact information anywhere in the image. "
            "DO NOT invent extra copy beyond the explicitly requested title, labels, and data points. "
            + no_photo
        )
    if style == "with_text":
        return (
            "The main title must be large, legible, and integrated into the composition with clear hierarchy. "
            "Use only one textual block: the requested main title. "
            f"The background must be dominated by a deep navy blue close to {_WITH_TEXT_BACKGROUND_HEX}. "
            "Use text colors with strong contrast on top of that dark background, preferring white, off-white, or a restrained warm accent only for emphasis. "
            "Never use low-contrast text against the dark blue base. "
            "Keep the background intentionally sparse and secondary to the headline. "
            "Use at most one simple highlight strip or color block behind a short part of the title. "
            "Do not add icon clusters, charts, dashboards, diagrams, UI cards, multiple stickers, circuitry patterns, or decorative micro-details. "
            "Do not add subtitle, supporting copy, caption, bullet list, footer text, CTA, URL, logo, watermark, brand signature, or invented contact details. "
            + no_photo
        )
    return (
        "Keep the composition clean and professional for a B2B LinkedIn post cover. "
        "ABSOLUTELY NO text, NO letters, NO words, NO numbers, NO captions, NO typography, NO logos, "
        "NO labels, and NO watermark. The image must communicate only through shapes, icons, color, and composition. "
        + no_photo
    )


def _build_prompt(
    post: ContentPost,
    style: str,
    aspect_ratio: str = "4:5",
    sub_type: str | None = None,
    visual_direction: str = "auto",
    custom_prompt: str | None = None,
) -> str:
    """Constrói o prompt de geração por estilo e pilar."""
    pillar = post.pillar or "authority"
    mood = _PILLAR_MOOD.get(pillar, _PILLAR_MOOD["authority"])
    title = post.title or ""
    direction = (
        _WITH_TEXT_AUTO_BRIEF
        if style == "with_text" and visual_direction == "auto"
        else _VISUAL_DIRECTION_BRIEF.get(
            visual_direction,
            _VISUAL_DIRECTION_BRIEF["auto"],
        )
    )
    constraints = _build_general_constraints(style)
    aspect_ratio_brief = _build_with_text_aspect_ratio_brief(aspect_ratio)
    custom_instruction = (
        f" Additional instruction: {custom_prompt.strip()}." if custom_prompt else ""
    )

    if style == "clean":
        return (
            f"Minimalist professional LinkedIn post cover image representing the concept of '{title}'. "
            f"Brand mood: {mood}. "
            f"Art direction: {direction}. "
            "Use abstract geometric shapes, light iconography, or a single dominant concept illustration. "
            "Keep the layout clean with ample negative space and a distinctive composition. "
            "Do not render the title text itself. Do not place any headline or written element in the artwork. "
            f"{constraints}{custom_instruction}"
        )

    if style == "with_text":
        return (
            f"LinkedIn post cover with bold headline text and a premium editorial look. "
            f"Main title: '{title}'. "
            f"Aspect ratio: {aspect_ratio}. "
            f"Brand mood: {mood}. "
            f"Art direction: {direction}. "
            f"Use a dark navy background anchored around {_WITH_TEXT_BACKGROUND_HEX} as the main base color. "
            "Use a text-first composition where the headline is the clear focal point and occupies most of the attention. "
            "Prefer a solid or softly graded background, very restrained geometry, and only a few large supporting shapes. "
            "Large, bold, clearly readable sans-serif typography with strong spacing and ample margins. "
            "The headline text must be perfectly legible and visually dominant. "
            "Adapt the headline colors for high contrast on the dark navy base, using mostly white or off-white text and, if needed, one contrasting accent color for a short emphasized phrase. "
            "If the title is long, break the exact same title into 2 to 4 short lines for readability, without changing any words. "
            "Optionally emphasize only one short phrase with a flat highlight strip or simple color block. "
            f"{aspect_ratio_brief} "
            "Render only the exact requested title as text. "
            "Do not rewrite the title, do not shorten it, do not expand it, and do not introduce any additional words. "
            "Avoid dense patterns, many small shapes, overlapping collage elements, illustrative scenes, and busy high-tech backgrounds. "
            "Do not add supporting copy, subtitles, labels, metrics, footer text, CTA, URL, logo, watermark, or contact details. "
            f"{constraints}{custom_instruction}"
        )

    if sub_type == "metrics":
        return (
            f"Clean data infographic for LinkedIn post about '{title}'. "
            f"Brand mood: {mood}. "
            f"Art direction: {direction}. "
            "Contains: large KPI numbers (placeholder values), bar charts or donut charts, "
            "clean data labels, minimal grid lines. "
            "Layout: 2-3 key metrics with icons above each number. "
            "If text is used, keep it limited to the requested infographic title and short metric labels only. "
            f"{constraints}{custom_instruction}"
        )

    if sub_type == "steps":
        return (
            f"Step-by-step process infographic for LinkedIn post about '{title}'. "
            f"Brand mood: {mood}. "
            f"Art direction: {direction}. "
            "Contains: 3 to 5 numbered steps in vertical or horizontal flow, "
            "simple flat icons per step, arrow connectors between steps, short text labels. "
            "Clean minimal layout with clear visual hierarchy. "
            "If text is used, keep it limited to the requested infographic title and very short step labels only. "
            f"{constraints}{custom_instruction}"
        )

    if sub_type == "comparison":
        return (
            f"Two-column comparison infographic for LinkedIn post about '{title}'. "
            f"Brand mood: {mood}. "
            f"Art direction: {direction}. "
            "Left column: labeled 'Antes' or 'Opção A' with a contrasting background color. "
            "Right column: labeled 'Depois' or 'Opção B' with an accent color background. "
            "Each column has 3-4 bullet points with flat icons. "
            "Bold divider line in the center, clear column headers. "
            "If text is used, keep it limited to the requested infographic title, column headers, and short bullet labels only. "
            f"{constraints}{custom_instruction}"
        )

    # fallback: generic infographic
    return (
        f"Professional LinkedIn infographic for '{title}'. "
        f"Brand mood: {mood}. "
        f"Art direction: {direction}. "
        "Clean visual hierarchy, icons, and data elements. "
        "If text is used, keep it minimal and directly tied to the requested infographic content only. "
        f"{constraints}{custom_instruction}"
    )


async def generate_post_image(
    post: ContentPost,
    style: str,
    registry: LLMRegistry,
    *,
    aspect_ratio: str = "4:5",
    sub_type: str | None = None,
    visual_direction: str = "auto",
    custom_prompt: str | None = None,
    image_size: str = "1K",
    **_: object,
) -> tuple[bytes, str]:
    """
    Gera imagem para o post e retorna (image_bytes, prompt_used).

    style: 'clean' | 'with_text' | 'infographic'
    sub_type: 'metrics' | 'steps' | 'comparison' (só para style='infographic')
    aspect_ratio: '4:5' | '1:1' | '16:9'
    image_size: '512' | '1K' | '2K' | '4K'
    """
    prompt = _build_prompt(
        post,
        style,
        aspect_ratio=aspect_ratio,
        sub_type=sub_type,
        visual_direction=visual_direction,
        custom_prompt=custom_prompt,
    )
    image_bytes = await registry.generate_image(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
    )
    return image_bytes, prompt
