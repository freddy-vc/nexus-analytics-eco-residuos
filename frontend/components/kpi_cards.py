"""Fragmentos HTML reutilizables: indicadores, insignias y avisos."""

from frontend.components import icons


def insignia(texto: str, tipo: str = "ok") -> str:
    return f'<span class="insignia {tipo}">{texto}</span>'


def indicador_icono(etiqueta: str, valor: str, nota: str, icono: str) -> str:
    return (f'<div class="tarjeta indicador"><span class="ic">{icons.icono(icono, 22)}</span>'
            f'<span class="indicador-cuerpo"><span>{etiqueta}</span><strong>{valor}</strong>'
            f'<small>{nota}</small></span></div>')


def dato(etiqueta: str, valor: str, nota: str, resaltado: bool = False) -> str:
    color = "var(--act)" if resaltado else "var(--tx)"
    return (f'<div class="tarjeta dato"><span>{etiqueta}</span>'
            f'<strong style="color:{color}">{valor}</strong><small>{nota}</small></div>')


def rejilla_indicadores(tarjetas: list[str], compacta: bool = False) -> str:
    clase = "rejilla-compacta" if compacta else "rejilla-indicadores"
    return f'<section class="rejilla {clase}">{"".join(tarjetas)}</section>'


def clave_valor(etiqueta: str, valor: str, simple: bool = False) -> str:
    return (f'<div class="fila-cv{" simple" if simple else ""}"><span>{etiqueta}</span>'
            f'<strong>{valor}</strong></div>')


def verificacion(titulo: str, detalle: str, cumple: bool) -> str:
    estado = "ok" if cumple else "wa"
    return (f'<div class="verificacion"><span class="marca-estado {estado}">'
            f'{icons.icono("visto" if cumple else "alerta", 14)}</span>'
            f'<span><strong>{titulo}</strong><span>{detalle}</span></span></div>')
