"""Exporta el reporte comparativo a PDF con fpdf2."""

from fpdf import FPDF

from backend.comparison.comparative_report import Reporte, Tabla

_REEMPLAZOS = {"—": "-", "–": "-", "−": "-", "→": "->", "≈": "aprox.", "…": "...", "“": '"', "”": '"',
               "‘": "'", "’": "'", "≤": "<=", "≥": ">=", " ": " ", " ": " "}
_VERDE, _GRIS, _TEXTO, _TENUE = (59, 130, 14), (240, 243, 246), (31, 42, 48), (91, 103, 112)


def _texto(valor: str) -> str:
    """Las fuentes base del PDF solo cubren Latin-1; se reemplazan los demás símbolos."""
    for original, reemplazo in _REEMPLAZOS.items():
        valor = valor.replace(original, reemplazo)
    return valor.encode("latin-1", "replace").decode("latin-1")


class _Documento(FPDF):
    def __init__(self, reporte: Reporte):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.reporte = reporte
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 16, 16)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_TENUE)
        self.cell(0, 6, _texto(f"EcoResiduos del Llano · {self.reporte.titulo} · página {self.page_no()}"),
                  align="C")


def generar_pdf(reporte: Reporte) -> bytes:
    pdf = _Documento(reporte)
    pdf.add_page()
    pdf.set_text_color(*_VERDE)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _texto(reporte.titulo))
    pdf.ln(10)
    pdf.set_text_color(*_TENUE)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _texto(f"{reporte.subtitulo} · generado el {reporte.generado_en:%d/%m/%Y %H:%M}"))
    pdf.ln(10)

    for seccion in reporte.secciones:
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_text_color(*_TEXTO)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, _texto(seccion.titulo))
        pdf.ln(9)
        pdf.set_font("Helvetica", "", 10)
        for parrafo in seccion.parrafos:
            pdf.multi_cell(0, 5, _texto(parrafo))
            pdf.ln(2)
        for tabla in seccion.tablas:
            _tabla(pdf, tabla)
            pdf.ln(4)
        pdf.ln(3)
    return bytes(pdf.output())


def _tabla(pdf: FPDF, tabla: Tabla) -> None:
    ancho_total = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", "", 9)
    medidas = [max([pdf.get_string_width(_texto(c)) for c in [col] + [f[k] for f in tabla.filas]] + [8]) + 4
               for k, col in enumerate(tabla.columnas)]
    escala = ancho_total / sum(medidas)
    anchos = [m * escala for m in medidas]
    alineacion = tabla.alineacion or ["i"] + ["d"] * (len(tabla.columnas) - 1)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*_GRIS)
    for ancho, columna, lado in zip(anchos, tabla.columnas, alineacion):
        pdf.cell(ancho, 7, _texto(columna), border=0, align="R" if lado == "d" else "L", fill=True)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for fila in tabla.filas:
        if pdf.get_y() > 270:
            pdf.add_page()
        for ancho, valor, lado in zip(anchos, fila, alineacion):
            pdf.cell(ancho, 6, _texto(valor), border="B", align="R" if lado == "d" else "L")
        pdf.ln(6)
