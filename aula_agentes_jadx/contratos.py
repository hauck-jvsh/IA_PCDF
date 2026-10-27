"""Contratos das etapas. Nenhum campo contém respostas da amostra."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Evidencia(Contrato):
    registro_fonte: str
    classe: str
    metodo: str
    trecho: str = Field(min_length=8)

class Pista(Contrato):
    id: str
    categoria: str
    descricao: str
    prioridade: Literal["alta", "media", "baixa"]
    evidencias: list[Evidencia] = Field(min_length=1)

class Cobertura(Contrato):
    area: str
    estado: Literal["examinada", "parcial", "nao_examinada"]
    justificativa: str

class Hunt(Contrato):
    pistas: list[Pista]
    cobertura: list[Cobertura]
    limites: list[str]

class Achado(Contrato):
    id: str
    pista_ids: list[str] = Field(min_length=1)
    funcionamento: str
    classificacao: Literal[
        "sustentado_no_codigo", "hipotese", "descartado", "pendente"]
    confianca: Literal["alta", "media", "baixa"]
    evidencias: list[Evidencia] = Field(min_length=1)
    lacunas: list[str]

class IOC(Contrato):
    id: str
    tipo: str
    valor_original: str
    valor_normalizado: str
    papel: str
    estado: Literal["sustentado_no_codigo", "candidato", "descartado"]
    confianca: Literal["alta", "media", "baixa"]
    achado_ids: list[str] = Field(min_length=1)
    evidencias: list[Evidencia] = Field(min_length=1)

class Analise(Contrato):
    resumo_funcionamento: str
    fluxo_alto_nivel: list[str]
    achados: list[Achado]
    iocs: list[IOC]
    cobertura: list[Cobertura]
    limites: list[str]

class Relatorio(Contrato):
    resumo_executivo: str
    funcionamento_alto_nivel: str
    achado_ids: list[str]
    ioc_ids: list[str]
    limitacoes: list[str]
    proximos_passos: list[str]
