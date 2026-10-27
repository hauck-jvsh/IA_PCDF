"""Servidor MCP stdio. Python 3.12, mcp 1.26.0 e PyJNIus 1.6.1."""
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sys
from uuid import uuid4

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Any
from ponte_iped import PonteIPED

LOG = logging.getLogger("iped_mcp")


@contextmanager
def registrar(ctx, operation, arguments):
    """Registra retorno e erros. A chamada à ponte aparece no próprio handler."""
    state = ctx.request_context.lifespan_context
    ponte = state["ponte"]
    state["sequence"] += 1
    record_id = f"Q{state['sequence']:04d}"
    timestamp = datetime.now(timezone.utc).isoformat()
    result = {"ok": True}
    try:
        yield result
    except ValueError as exc:
        result.update(ok=False, error={"code": "CONSULTA_INVALIDA", "message": str(exc)[:500]})
    except Exception:
        LOG.exception("Falha na operação %s, registro %s", operation, record_id)
        result.update(ok=False, error={"code": "FALHA_IPED",
                      "message": "Conferir stderr e o ambiente do IPED"})
    result.update({"record_id": record_id, "session_id": state["session_id"],
                   "case_label": ponte.case_label, "backend": ponte.backend,
                   "timestamp_utc": timestamp})
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True)
    record = {"operation": operation, "arguments": arguments, "result": result,
              "result_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
    with state["audit_path"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_ponte(ctx):
    return ctx.request_context.lifespan_context["ponte"]


def create_server(audit_path=None):
    audit_path = Path(audit_path or Path(__file__).with_name("consultas.jsonl"))

    @asynccontextmanager
    async def lifespan(server):
        # A abertura, as chamadas dos handlers e o fechamento ficam na thread principal.
        ponte = PonteIPED()
        try:
            yield {"ponte": ponte, "audit_path": audit_path,
                   "session_id": uuid4().hex, "sequence": 0}
        finally:
            ponte.close()

    mcp = FastMCP("iped", lifespan=lifespan)
    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write_annotations = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                        idempotentHint=True, openWorldHint=False)

    # Handlers async mantêm a execução no fluxo principal do MCP.
    # As chamadas Java abaixo são diretas e bloqueiam esse fluxo até terminarem.
    @mcp.tool(annotations=annotations)
    async def caso_info(ctx: Context) -> dict[str, Any]:
        """Identifica o caso IPED e lista categorias com contagem incluindo subcategorias, permissões e pipeline de texto. Categorias podem se sobrepor; não somar suas contagens."""
        with registrar(ctx, "info", {}) as result:
            result["data"] = get_ponte(ctx).info()
        return result

    @mcp.tool(annotations=annotations)
    async def buscar_itens(ctx: Context,
        query: Annotated[str, Field(min_length=1, max_length=300)],
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=50)] = 20,
        categoria: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    ) -> dict[str, Any]:
        """Busca no caso IPED fixado. categoria opcional usa name de caso_info e inclui subcategorias, combinando o filtro com a query. Use query='*:*' para listar a categoria. Retorna página e total; a busca Java pode varrer todo o índice."""
        arguments = {"query": query, "offset": offset, "limit": limit, "categoria": categoria}
        with registrar(ctx, "search", arguments) as result:
            result["data"] = get_ponte(ctx).search(query, offset, limit, categoria)
        return result

    @mcp.tool(annotations=annotations)
    async def obter_metadados(ctx: Context,
        item_id: Annotated[int, Field(ge=0, le=2147483647)]) -> dict[str, Any]:
        """Obtém campos básicos de um item. O ID pertence apenas ao caso informado."""
        with registrar(ctx, "metadata", {"item_id": item_id}) as result:
            result["data"] = get_ponte(ctx).metadata(item_id)
        return result

    @mcp.tool(annotations=annotations)
    async def ler_texto(ctx: Context,
        item_id: Annotated[int, Field(ge=0, le=2147483647)],
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=32768)] = 4096) -> dict[str, Any]:
        """Extrai texto de qualquer item pelo pipeline da aba Texto do IPED. Pagina por caracteres Unicode, sem filtro de MIME. Inclui metadados e flags de erro/cifra."""
        arguments = {"item_id": item_id, "offset": offset, "limit": limit}
        with registrar(ctx, "text", arguments) as result:
            result["data"] = get_ponte(ctx).text(item_id, offset, limit)
        return result

    @mcp.tool(annotations=annotations)
    async def listar_marcadores(ctx: Context,
        item_id: Annotated[int | None, Field(ge=0, le=2147483647)] = None,
        offset: Annotated[int, Field(ge=0, le=10000)] = 0,
        limit: Annotated[int, Field(ge=1, le=100)] = 50) -> dict[str, Any]:
        """Lista marcadores do caso ou de um item, com comentário e contagem."""
        arguments = {"item_id": item_id, "offset": offset, "limit": limit}
        with registrar(ctx, "list_bookmarks", arguments) as result:
            result["data"] = get_ponte(ctx).list_bookmarks(item_id, offset, limit)
        return result

    @mcp.tool(annotations=write_annotations)
    async def criar_marcador(ctx: Context,
        nome: Annotated[str, Field(min_length=1, max_length=120)],
        comentario: Annotated[str, Field(max_length=1000)] = "") -> dict[str, Any]:
        """Cria e salva marcador no caso. Nome existente é reutilizado sem mudar seu comentário."""
        arguments = {"nome": nome, "comentario": comentario}
        with registrar(ctx, "create_bookmark", arguments) as result:
            result["data"] = get_ponte(ctx).create_bookmark(nome, comentario)
        return result

    @mcp.tool(annotations=write_annotations)
    async def associar_itens_marcador(ctx: Context,
        marcador_id: Annotated[int, Field(ge=0, le=2147483647)],
        item_ids: Annotated[list[Annotated[int, Field(ge=0, le=2147483647)]],
                            Field(min_length=1, max_length=100)]) -> dict[str, Any]:
        """Valida todos os IDs, associa até 100 itens e salva. Repetir o lote não duplica vínculos."""
        arguments = {"marcador_id": marcador_id, "item_ids": item_ids}
        with registrar(ctx, "associate_bookmark", arguments) as result:
            result["data"] = get_ponte(ctx).associate_bookmark(marcador_id, item_ids)
        return result

    return mcp


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    create_server().run(transport="stdio")
