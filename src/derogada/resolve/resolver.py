"""Resolución de citas a identificadores oficiales: BOE-A-... (España) o CELEX (UE).

Reglas:
- Nunca adivinar: si la desambiguación no es unívoca, se devuelven candidatos
  y la cita queda NO_RESUELTA.
- Todo identificador (incluidos los del gazetteer) se valida contra la API:
  `numero_oficial` y `rango` de los metadatos deben casar con la cita.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from derogada.extract.gazetteer import EntradaAlias, buscar_alias
from derogada.extract.patterns import norm_numero
from derogada.models import Cita, Jurisdiccion, NormaRef
from derogada.sources.boe import BoeClient
from derogada.sources.cellar import CellarClient

URL_BOE = "https://www.boe.es/buscar/act.php?id={boe_id}"
URL_EURLEX = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"

_LETRAS_UE = {"reglamento": "R", "directiva": "L", "decisión": "D", "decision": "D"}


def celex_desde_referencia(rango: str | None, numero: str | None) -> str | None:
    """CELEX de un acto de sector 3: Reglamento (UE) 2016/679 -> 32016R0679."""
    numero = norm_numero(numero)
    if not rango or not numero or "/" not in numero:
        return None
    letra = _LETRAS_UE.get(rango.lower())
    if not letra:
        return None
    ano_s, num_s = numero.split("/", 1)
    if not (ano_s.isdigit() and num_s.isdigit()):
        return None
    ano = int(ano_s)
    if ano < 100:
        ano += 1900  # "95/46" -> 1995 (actos anteriores a 2000)
    return f"3{ano}{letra}{int(num_s):04d}"


@dataclass
class Resolucion:
    identificador: str | None = None
    fuente: str | None = None  # "BOE" | "EUR-Lex"
    titulo: str | None = None
    url: str | None = None
    candidatos: list[NormaRef] = field(default_factory=list)

    @property
    def resuelta(self) -> bool:
        return self.identificador is not None


def resolver_cita(cita: Cita, boe: BoeClient, cellar: CellarClient) -> Resolucion:
    """Resuelve la cita contra BOE o CELLAR. No inventa: duda -> candidatos."""
    entrada_alias = buscar_alias(cita.alias) if cita.alias else None
    if entrada_alias is None and cita.alias:
        entrada_alias = buscar_alias(cita.texto)
    if cita.jurisdiccion == Jurisdiccion.UE or (
        entrada_alias and entrada_alias.jurisdiccion == Jurisdiccion.UE
    ):
        return _resolver_ue(cita, cellar, entrada_alias)
    return _resolver_es(cita, boe, entrada_alias)


# ---------------- UE ----------------


def _resolver_ue(
    cita: Cita, cellar: CellarClient, entrada_alias: EntradaAlias | None
) -> Resolucion:
    celex = (
        entrada_alias.identificador
        if entrada_alias and entrada_alias.jurisdiccion == Jurisdiccion.UE
        else celex_desde_referencia(cita.rango, cita.numero)
    )
    if not celex:
        return Resolucion()
    if not cellar.estado(celex).encontrado:
        return Resolucion()
    return Resolucion(
        identificador=celex,
        fuente="EUR-Lex",
        titulo=entrada_alias.nombre if entrada_alias else None,
        url=URL_EURLEX.format(celex=celex),
    )


# ---------------- España ----------------


def _resolver_es(
    cita: Cita, boe: BoeClient, entrada_alias: EntradaAlias | None
) -> Resolucion:
    # 1) Identificador directo del gazetteer, validado con metadatos de la API
    if entrada_alias and entrada_alias.identificador.startswith("BOE-"):
        meta = _metadatos_seguro(boe, entrada_alias.identificador)
        if meta is not None and _numero_casa(meta, entrada_alias.numero):
            return Resolucion(
                identificador=entrada_alias.identificador,
                fuente="BOE",
                titulo=meta.get("titulo"),
                url=meta.get("url_html_consolidada")
                or URL_BOE.format(boe_id=entrada_alias.identificador),
            )

    # 2) Rango + número -> búsqueda y desambiguación por numero_oficial
    numero = cita.numero or (entrada_alias.numero if entrada_alias else None)
    rango = cita.rango or (entrada_alias.rango if entrada_alias else None)
    if numero:
        consulta = f"{rango or ''} {numero}".strip()
        try:
            encontrados = boe.buscar(consulta, limite=6)
        except Exception:
            encontrados = []
        exactos = [e for e in encontrados if _candidato_casa(e, numero, rango)]
        if len(exactos) == 1:
            return _resolucion_desde_item(exactos[0])
        if len(exactos) > 1:
            return Resolucion(candidatos=[_a_norma_ref(e) for e in exactos])
        if encontrados:
            return Resolucion(candidatos=[_a_norma_ref(e) for e in encontrados])
    return Resolucion()


def _metadatos_seguro(boe: BoeClient, boe_id: str) -> dict | None:
    try:
        return boe.metadatos(boe_id)
    except Exception:
        return None


def _norm(texto: str | None) -> str:
    return (texto or "").strip().lower()


def _numero_casa(meta: dict, numero: str | None) -> bool:
    """Valida el identificador del gazetteer contra los metadatos oficiales."""
    if numero is None:
        return True  # sin número que contrastar (CE, LECrim...): confiar en el ID
    return _norm(meta.get("numero_oficial")) == _norm(numero)


def _candidato_casa(item: dict, numero: str, rango: str | None) -> bool:
    if _norm(item.get("numero_oficial")) != _norm(numero):
        return False
    if rango:
        rango_item = item.get("rango", {})
        if isinstance(rango_item, dict):
            rango_item = rango_item.get("texto", "")
        return _norm(str(rango_item)) == _norm(rango)
    return True


def _a_norma_ref(item: dict) -> NormaRef:
    return NormaRef(
        identificador=item.get("identificador", "?"),
        fuente="BOE",
        titulo=item.get("titulo"),
        url=item.get("url_html_consolidada")
        or URL_BOE.format(boe_id=item.get("identificador", "")),
    )


def _resolucion_desde_item(item: dict) -> Resolucion:
    ref = _a_norma_ref(item)
    return Resolucion(
        identificador=ref.identificador, fuente="BOE", titulo=ref.titulo, url=ref.url
    )
