#!/usr/bin/env python3
"""
smart_crop.py — inteligentne kadrowanie zdjęć produktowych.

Input:  PNG z kanałem alpha / przezroczystością.
Output: wykadrowany, kwadratowy PNG z zachowaną przezroczystością.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image
import numpy as np


# Próg alpha powyżej którego piksel jest traktowany jako część produktu.
ALPHA_THRESHOLD = 10


def smart_crop(
    input_path: str,
    output_path: str,
    target_size: int = 1000,
    padding: float = 0.08,
    max_upscale: float = 2.0,
) -> dict:
    """
    Kadruje i skaluje zdjęcie produktowe do kwadratowego canvasu.

    Args:
        input_path:  ścieżka do pliku wejściowego PNG z alpha.
        output_path: ścieżka do pliku wyjściowego PNG.
        target_size: bok kwadratu docelowego w px.
        padding: margines wokół produktu jako ułamek, np. 0.08 = 8%.
        max_upscale: maksymalny mnożnik powiększenia.

    Returns:
        dict z informacjami o operacji.
    """

    img = Image.open(input_path)

    if img.mode != "RGBA":
        raise ValueError(
            f"Input musi być PNG z kanałem alpha / RGBA. "
            f"Otrzymano: {img.mode}. Plik: {input_path}"
        )

    # Maska produktu z kanału alpha.
    alpha = np.array(img)[:, :, 3]
    mask = alpha > ALPHA_THRESHOLD

    if not mask.any():
        raise ValueError(f"Brak produktu na obrazie, cała alpha = 0: {input_path}")

    # Bounding box produktu.
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    cropped = img.crop((cmin, rmin, cmax + 1, rmax + 1))

    w, h = cropped.size
    longer_side = max(w, h)

    # Dostępny obszar wewnątrz canvasu po odjęciu paddingu.
    available = target_size * (1 - 2 * padding)

    # Skala potrzebna, żeby produkt wypełnił dostępny obszar.
    ideal_scale = available / longer_side

    # Limitujemy tylko powiększanie. Zmniejszanie jest bez limitu.
    upscale_limited = ideal_scale > max_upscale
    actual_scale = min(ideal_scale, max_upscale)

    new_w = max(1, int(round(w * actual_scale)))
    new_h = max(1, int(round(h * actual_scale)))

    resized = cropped.resize((new_w, new_h), Image.LANCZOS)

    # Kwadratowy canvas z przezroczystym tłem.
    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))

    offset_x = (target_size - new_w) // 2
    offset_y = (target_size - new_h) // 2

    canvas.paste(resized, (offset_x, offset_y), resized)

    output_path = Path(output_path)

    if output_path.suffix.lower() != ".png":
        raise ValueError("Output musi być .png, aby zachować przezroczystość.")

    canvas.save(output_path, "PNG", optimize=True)

    info = {
        "input_bbox_px": (w, h),
        "longer_side_px": longer_side,
        "ideal_scale": round(ideal_scale, 3),
        "applied_scale": round(actual_scale, 3),
        "final_product_px": (new_w, new_h),
        "upscale_limit_hit": upscale_limited,
    }

    if upscale_limited:
        print(
            f"WARN: {input_path} — produkt mały ({w}x{h}px). "
            f"Wymagany scale x{ideal_scale:.2f}, ograniczony do x{max_upscale}. "
            f"Produkt nie wypełni kadru, będą większe marginesy.",
            file=sys.stderr,
        )

    return info


def main():
    parser = argparse.ArgumentParser(
        description="Inteligentne kadrowanie zdjęć produktowych PNG z przezroczystością."
    )

    parser.add_argument("input", help="plik wejściowy PNG z kanałem alpha")
    parser.add_argument("output", help="plik wyjściowy PNG")
    parser.add_argument(
        "--size",
        type=int,
        default=1000,
        help="bok kwadratu docelowego w px, domyślnie 1000",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.08,
        help="margines wokół produktu, np. 0.08 = 8%",
    )
    parser.add_argument(
        "--max-upscale",
        type=float,
        default=2.0,
        help="maksymalne powiększenie, domyślnie 2.0",
    )

    args = parser.parse_args()

    try:
        info = smart_crop(
            args.input,
            args.output,
            target_size=args.size,
            padding=args.padding,
            max_upscale=args.max_upscale,
        )

        print(
            f"OK: {args.input} -> {args.output} "
            f"(bbox {info['input_bbox_px'][0]}x{info['input_bbox_px'][1]}, "
            f"scale x{info['applied_scale']})"
        )

    except Exception as e:
        print(f"BŁĄD: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()