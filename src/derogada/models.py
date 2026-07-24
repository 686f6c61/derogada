"""Modelos de datos de derogada (Pydantic v2).

Recorren todo el pipeline: ingesta -> extracción -> resolución -> verificación -> informe.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

AVISO_LEGAL = (
    "Este informe es meramente informativo y no constituye asesoramiento jurídico. "
    "Los textos consolidados del BOE no tienen valor oficial: a efectos jurídicos, "
    "consulte siempre la publicación oficial correspondiente."
)


class Jurisdiccion(str, Enum):
    """Ordenamiento al que pertenece la norma citada."""

    ES = "ES"  # normativa española -> BOE
    UE = "UE"  # derecho de la UE -> EUR-Lex / CELLAR


class EstadoCita(str, Enum):
    """Resultado de la verificación de una cita."""

    VIGENTE = "VIGENTE"
    MODIFICADA = "MODIFICADA"
    DEROGADA = "DEROGADA"
    VIGENCIA_AGOTADA = "VIGENCIA AGOTADA"
    NO_RESUELTA = "NO RESUELTA"
    NO_ENCONTRADA = "NO ENCONTRADA"


class Cita(BaseModel):
    """Referencia normativa detectada en el documento."""

    texto: str  # literal, tal y como aparece en el documento
    jurisdiccion: Jurisdiccion
    rango: str | None = None  # "Ley", "Real Decreto", "Reglamento", "Directiva"...
    numero: str | None = None  # "30/1992", "2016/679"
    articulo: str | None = None  # "42", "42.1", "6"
    alias: str | None = None  # sigla usada: "LECrim", "RGPD"...
    contexto: str | None = None  # fragmento del documento alrededor de la cita


class NormaRef(BaseModel):
    """Norma identificada en una fuente oficial."""

    identificador: str  # "BOE-A-2015-10565" | "32016R0679"
    fuente: str  # "BOE" | "EUR-Lex"
    titulo: str | None = None
    url: str | None = None


class ResultadoCita(BaseModel):
    """Veredicto de una cita tras resolver y verificar."""

    cita: Cita
    estado: EstadoCita
    norma: NormaRef | None = None  # la norma citada, si se resolvió
    derogada_por: NormaRef | None = None  # norma que la derogó, si aplica
    modificada_por: list[NormaRef] = Field(default_factory=list)
    nota: str | None = None  # explicación breve ("artículo derogado", "2 candidatos"...)
    candidatos: list[NormaRef] = Field(default_factory=list)  # si NO_RESUELTA
    sugerencia: str | None = None  # propuesta de cambio textual anclada a fuente


class Resumen(BaseModel):
    total: int = 0
    vigentes: int = 0
    modificadas: int = 0
    derogadas: int = 0
    vigencia_agotada: int = 0
    no_resueltas: int = 0
    no_encontradas: int = 0


class Informe(BaseModel):
    """Resultado completo del análisis de un documento."""

    documento: str
    generado: datetime = Field(default_factory=datetime.now)
    resultados: list[ResultadoCita] = Field(default_factory=list)
    aviso: str = AVISO_LEGAL

    @property
    def resumen(self) -> Resumen:
        r = Resumen(total=len(self.resultados))
        for res in self.resultados:
            if res.estado == EstadoCita.VIGENTE:
                r.vigentes += 1
            elif res.estado == EstadoCita.MODIFICADA:
                r.modificadas += 1
            elif res.estado == EstadoCita.DEROGADA:
                r.derogadas += 1
            elif res.estado == EstadoCita.VIGENCIA_AGOTADA:
                r.vigencia_agotada += 1
            elif res.estado == EstadoCita.NO_RESUELTA:
                r.no_resueltas += 1
            elif res.estado == EstadoCita.NO_ENCONTRADA:
                r.no_encontradas += 1
        return r
