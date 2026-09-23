"""Agrega la lámina 'Rigor Avanzado' (conformal + anomalías) a la presentación
oficial, con el mismo sistema de diseño, insertada tras 'Caso Real' y renumerando.
"""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import deck_premium as D  # reutiliza paleta + helpers (mismo diseño)

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("/home/tuxilo/aquabosque-minero-ia/outputs/jurado_2026/AquaBosque_Presentacion_CON_RIGOR.pptx")
INSERT_AFTER_0BASED = 8   # tras la slide 9 (Caso Real) -> nueva slide 10
NEW_NUMBER = 8            # numeración de esquina de la nueva lámina


import copy

NOTA = ("Aquí está lo que nos pone en otra liga. La mayoría de soluciones muestra una 'confianza' que es solo la "
        "probabilidad del modelo. Nosotros vamos más allá con conformal prediction: le damos al nivel de cada "
        "municipio una garantía estadística del 90%, verificada empíricamente en 91.4%. Y con detección de "
        "anomalías, de forma independiente y sin usar etiquetas, confirmamos 43 municipios prioritarios y "
        "descubrimos 14 atípicos que la fórmula no destaca. Es el tipo de rigor que se usa en medicina y "
        "finanzas, y que rara vez se ve en el sector público colombiano.")


def set_notes_robust(src_slide, dst_slide, text):
    """Pone la nota en dst; si su notes slide no tiene placeholder BODY, lo clona de src."""
    dst_ns = dst_slide.notes_slide
    if dst_ns.notes_text_frame is None:
        src_ns = src_slide.notes_slide
        for ph in src_ns.placeholders:
            if ph.placeholder_format.type == 2:  # BODY (notas)
                dst_ns.shapes._spTree.append(copy.deepcopy(ph._element))
                break
    tf = dst_ns.notes_text_frame
    if tf is not None:
        tf.text = text
        return True
    return False


def num_textbox(slide):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip().isdigit() \
           and sh.left is not None and abs(sh.left/914400 - 12.40) < 0.2 and abs((sh.top or 0)/914400 - 7.04) < 0.2:
            return sh
    return None


def build_rigor_slide(prs):
    s = D.base_slide(prs, page=NEW_NUMBER)
    D.title_block(s, "Rigor avanzado", "Confianza con garantía\nmatemática.")
    D.bullets(s, 0.78, 2.7, 5.5, [
        "Conformal prediction: garantizamos el nivel real con 90% de cobertura (91.4% verificado).",
        "Detección de anomalías: confirma 43 municipios y revela 14 atípicos que el índice no ve.",
        "Rigor de ML de alto riesgo (medicina, finanzas), poco visto en el sector público.",
    ])
    D.kpi_row(s, 5.2, [("91.4%", "Cobertura garantizada", D.NAVY),
                       ("57", "Anomalías detectadas", D.ALTO),
                       ("14", "Atípicos nuevos", D.EMER)], x0=0.8, dx=1.95)

    ix, iw = 6.6, 6.05
    # Caja A: Confianza (lo común)
    D.rect(s, ix, 1.75, iw, 1.45, fill=D.RGBColor(0xEE, 0xF4, 0xF1), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    tb, tf = D.textbox(s, ix + 0.3, 1.95, iw - 0.6, 1.1)
    D._run(tf.paragraphs[0], "Confianza (lo habitual)", 15, D.GRAY, font=D.F_TIT, bold=True)
    p = tf.add_paragraph(); D._run(p, "Probabilidad que reporta el modelo (softmax). Útil, pero sin garantía estadística.", 14, D.INK, font=D.F_BODY); p.space_before = Pt(4)
    # Caja B: Certeza calibrada (nuestro diferenciador)
    D.rect(s, ix, 3.4, iw, 1.75, fill=D.WHITE, line=D.EMER, line_w=2.2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, shadow=True)
    tb, tf = D.textbox(s, ix + 0.3, 3.6, iw - 0.6, 1.4)
    D._run(tf.paragraphs[0], "🔬  Certeza calibrada (conformal)", 15, D.EMER, font=D.F_TIT, bold=True)
    p = tf.add_paragraph(); D._run(p, "El nivel real cae dentro del conjunto con ≥90% de garantía, ", 14, D.INK, font=D.F_BODY)
    D._run(p, "verificada empíricamente en 91.4%.", 14, D.INK, font=D.F_BODY, bold=True); p.space_before = Pt(4)
    D.chip(s, ix, 5.4, iw, 0.75, "Anomalías independientes (sin etiquetas): confirman y descubren lo que la fórmula no ve", D.NAVY, size=12.5)
    return s


def main():
    prs = Presentation(str(SRC))
    slides = list(prs.slides)
    # 1) renumerar: las slides desde el punto de inserción suben +1
    for s in slides[INSERT_AFTER_0BASED + 1:]:
        nb = num_textbox(s)
        if nb is not None:
            r = nb.text_frame.paragraphs[0].runs[0] if nb.text_frame.paragraphs[0].runs else None
            nuevo = str(int(nb.text_frame.text.strip()) + 1)
            if r is not None:
                r.text = nuevo
            else:
                nb.text_frame.text = nuevo
    # 2) construir la nueva lámina (queda al final) + nota clonando placeholder de Caso Real
    nueva = build_rigor_slide(prs)
    ok = set_notes_robust(slides[INSERT_AFTER_0BASED], nueva, NOTA)
    print("nota del orador:", "OK" if ok else "NO se pudo")
    # 3) moverla a la posición deseada (índice INSERT_AFTER+1)
    sldIdLst = prs.slides._sldIdLst
    ids = list(sldIdLst)
    nuevo = ids[-1]
    sldIdLst.remove(nuevo)
    sldIdLst.insert(INSERT_AFTER_0BASED + 1, nuevo)
    prs.save(str(OUT))
    print("OK:", OUT, "·", len(prs.slides._sldIdLst), "slides")


if __name__ == "__main__":
    main()
