"""PDF layout for membership and event certificates (ReportLab)."""

from __future__ import annotations

import io

import qrcode
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _register_cyrillic_fonts() -> tuple[str, str, str] | None:
    """Try to register DejaVu fonts and return (regular, bold, italic) names."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]

    import os

    regular_path = None
    for path in font_paths:
        if os.path.exists(path):
            regular_path = path
            break

    if not regular_path:
        return None

    pdfmetrics.registerFont(TTFont("DejaVuSans", regular_path))
    regular = "DejaVuSans"
    bold = regular
    italic = regular

    bold_path = regular_path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
    if os.path.exists(bold_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
        bold = "DejaVuSans-Bold"

    oblique_path = regular_path.replace("DejaVuSans.ttf", "DejaVuSans-Oblique.ttf")
    if os.path.exists(oblique_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans-Oblique", oblique_path))
        italic = "DejaVuSans-Oblique"

    return regular, bold, italic


_CYRILLIC_FONTS: tuple[str, str, str] | None = None


def _ensure_fonts() -> tuple[str, str, str]:
    """Return (regular, bold, italic) font names."""
    global _CYRILLIC_FONTS  # noqa: PLW0603
    if _CYRILLIC_FONTS is None:
        result = _register_cyrillic_fonts()
        _CYRILLIC_FONTS = result or ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique")
    return _CYRILLIC_FONTS


def _bytes_to_image_reader(data: bytes | None) -> ImageReader | None:
    if not data:
        return None
    try:
        return ImageReader(io.BytesIO(data))
    except Exception:
        return None


def _generate_qr_image(url: str, box_size: int = 6) -> ImageReader:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_border(c: canvas.Canvas, width: float, height: float) -> None:
    """Draw a brown ornamental double border."""
    brown = HexColor("#6B4226")
    c.setStrokeColor(brown)

    m = 40
    c.setLineWidth(3)
    c.rect(m, m, width - 2 * m, height - 2 * m)

    c.setLineWidth(1.5)
    c.rect(m + 7, m + 7, width - 2 * (m + 7), height - 2 * (m + 7))

    c.setLineWidth(0.5)
    c.rect(m + 12, m + 12, width - 2 * (m + 12), height - 2 * (m + 12))


def _wrap_text(text: str, max_width: float, font_name: str, font_size: float) -> list[str]:
    """Simple word-wrap for centered text."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        if stringWidth(test, font_name, font_size) <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines or [""]


def _generate_member_pdf(
    full_name: str,
    cert_number: str,
    year: int,
    body_text: str,
    validity_text: str,
    president_name: str,
    president_title: str,
    qr_url: str,
    logo_bytes: bytes | None = None,
    stamp_bytes: bytes | None = None,
    signature_bytes: bytes | None = None,
    background_bytes: bytes | None = None,
) -> bytes:
    regular, bold, italic = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Background watermark — draw BEFORE border so edges are hidden
    bg_img = _bytes_to_image_reader(background_bytes)
    if bg_img:
        c.saveState()
        c.setFillAlpha(0.18)
        c.drawImage(
            bg_img, 0, 0,
            width=width, height=height,
            mask="auto",
        )
        c.restoreState()

    _draw_border(c, width, height)

    content_margin = 70
    max_text_width = width - 2 * content_margin

    y_cursor = height - 90

    # Logo
    logo_img = _bytes_to_image_reader(logo_bytes)
    if logo_img:
        logo_w, logo_h = 95, 95
        c.drawImage(
            logo_img,
            (width - logo_w) / 2, y_cursor - logo_h,
            width=logo_w, height=logo_h,
            mask="auto",
            preserveAspectRatio=True,
        )
        y_cursor -= logo_h + 25
    else:
        y_cursor -= 20

    # "СЕРТИФИКАТ" heading
    heading_color = HexColor("#2c2c2c")
    c.setFont(italic, 30)
    c.setFillColor(heading_color)
    c.drawCentredString(width / 2, y_cursor, "СЕРТИФИКАТ")
    y_cursor -= 45

    # Doctor full name
    c.setFont(bold, 20)
    c.setFillColor(HexColor("#1a1a1a"))
    name_lines = _wrap_text(full_name, max_text_width, bold, 20)
    for line in name_lines:
        c.drawCentredString(width / 2, y_cursor, line)
        y_cursor -= 28
    y_cursor -= 35

    # Body text — uppercase, centered
    c.setFont(regular, 10)
    c.setFillColor(HexColor("#333333"))
    body_upper = body_text.upper()
    body_lines = _wrap_text(body_upper, max_text_width, regular, 10)
    for line in body_lines:
        c.drawCentredString(width / 2, y_cursor, line)
        y_cursor -= 14
    y_cursor -= 30

    # Validity text
    if validity_text:
        c.setFont(regular, 11)
        c.setFillColor(HexColor("#666666"))
        c.drawCentredString(width / 2, y_cursor, validity_text.upper())
        y_cursor -= 40

    # Bottom section
    bottom_y = 80
    margin_x = 65

    # QR code — bottom left
    qr_img = _generate_qr_image(qr_url, box_size=5)
    qr_size = 85
    c.setFont(regular, 7)
    c.setFillColor(HexColor("#888888"))
    c.drawString(margin_x, bottom_y + qr_size + 6, "проверить сертификат")
    c.drawImage(qr_img, margin_x, bottom_y, width=qr_size, height=qr_size, mask="auto")

    # Stamp + Signature — bottom right
    right_block_x = width - margin_x - 190
    stamp_img = _bytes_to_image_reader(stamp_bytes)
    sig_img = _bytes_to_image_reader(signature_bytes)

    stamp_size = 100
    sig_w, sig_h = 110, 35

    # Draw signature first, then stamp on top (correct real-world order)
    if sig_img:
        c.drawImage(
            sig_img,
            right_block_x + stamp_size - 15, bottom_y + 45,
            width=sig_w, height=sig_h,
            mask="auto",
            preserveAspectRatio=True,
        )

    if stamp_img:
        c.drawImage(
            stamp_img,
            right_block_x, bottom_y + 20,
            width=stamp_size, height=stamp_size,
            mask="auto",
            preserveAspectRatio=True,
        )

    # President info text — below stamp/signature
    c.setFont(regular, 9)
    c.setFillColor(HexColor("#333333"))
    pres_x = right_block_x + 15
    if president_title:
        c.drawString(pres_x, bottom_y + 8, president_title)
    if president_name:
        c.drawString(pres_x, bottom_y - 5, president_name)

    c.save()
    return buf.getvalue()


def generate_event_certificate_pdf(
    full_name: str, event_title: str, event_date: str, cert_number: str
) -> bytes:
    regular, bold, italic = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    _draw_border(c, width, height)

    c.setFont(italic, 28)
    c.setFillColor(HexColor("#5C3A1E"))
    c.drawCentredString(width / 2, height - 140, "СЕРТИФИКАТ УЧАСТНИКА")

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 190, "Настоящим подтверждается, что")

    c.setFont(bold, 22)
    c.setFillColor(HexColor("#1a1a1a"))
    c.drawCentredString(width / 2, height - 230, full_name)

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 270, "принял(а) участие в мероприятии")

    c.setFont(bold, 16)
    c.setFillColor(HexColor("#2c3e50"))
    c.drawCentredString(width / 2, height - 310, event_title[:60])

    c.setFont(regular, 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 340, f"Дата: {event_date}")

    c.setFont(regular, 11)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(width / 2, height - 400, f"Номер: {cert_number}")

    c.setFont(regular, 10)
    c.setFillColor(HexColor("#aaaaaa"))
    c.drawCentredString(width / 2, 80, "Профессиональное общество трихологов")

    c.save()
    return buf.getvalue()
