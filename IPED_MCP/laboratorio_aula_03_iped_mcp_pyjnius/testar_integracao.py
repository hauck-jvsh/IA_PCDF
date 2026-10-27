"""Testa consultas e gravação de marcadores no caso sintético IPED real."""
import asyncio
import ast
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # O servidor mantém as chamadas à ponte dentro dos handlers, sem offload.
    source = Path(__file__).with_name("servidor_mcp.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    expected_tools = {"caso_info", "buscar_itens", "obter_metadados", "ler_texto",
                      "listar_marcadores", "criar_marcador", "associar_itens_marcador"}
    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name in expected_tools]
    assert {n.name for n in handlers} == expected_tools
    assert not any(isinstance(n, ast.Await) for h in handlers for n in ast.walk(h))
    assert "run_in_executor" not in source and "ThreadPoolExecutor" not in source
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).with_name("servidor_mcp.py"))],
        env={**os.environ, "IPED_ALLOW_BOOKMARK_WRITE": "1"})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            writes = {"criar_marcador", "associar_itens_marcador"}
            assert {t.name for t in tools} == {"caso_info", "buscar_itens", "obter_metadados",
                "ler_texto", "listar_marcadores", *writes}
            assert all(t.annotations.readOnlyHint == (t.name not in writes) for t in tools)
            async def call(name, args):
                result = await s.call_tool(name, args)
                assert not result.isError, result
                assert result.structuredContent is not None
                return result.structuredContent

            info = await call("caso_info", {})
            assert info["ok"] and info["backend"] == "iped"
            categories = info["data"]["categories"]
            assert categories and info["data"]["category_count"] == len(categories)
            assert info["data"]["category_counting"] == "unique_items_including_subcategories"
            assert info["data"]["categories_may_overlap"] is True
            assert all(c["name"] and c["label"] and c["item_count"] >= 0 for c in categories)
            search_schema = next(t.inputSchema for t in tools if t.name == "buscar_itens")
            assert "categoria" in search_schema["properties"]
            assert "categoria" not in search_schema.get("required", [])
            assert "maximum" not in search_schema["properties"]["offset"]
            matches, offset = [], 0
            while True:
                response = await call("buscar_itens", {"query": "aurora", "limit": 2, "offset": offset})
                assert response["ok"], response
                data = response["data"]
                assert data["total"] == 5
                matches.extend(data["items"])
                if data["next_offset"] is None:
                    break
                offset = data["next_offset"]
            assert len(matches) == 5 and len({x["item_id"] for x in matches}) == 5
            dados = Path(__file__).with_name("dados_sinteticos")
            for item in matches:
                item_id = item["item_id"]
                metadata = await call("obter_metadados", {"item_id": item_id})
                assert metadata["data"] == item
                text = await call("ler_texto", {"item_id": item_id})
                assert text["ok"] and not text["data"]["has_more"]
                assert text["data"]["origin"] == "iped_text_viewer_pipeline"
                original = (dados / item["name"]).read_text(encoding="utf-8").strip()
                assert original in text["data"]["text"]
                assert text["data"]["includes_metadata"]
            first = matches[0]["item_id"]
            page1 = await call("ler_texto", {"item_id": first, "limit": 20})
            page2 = await call("ler_texto", {"item_id": first, "offset": 20, "limit": 20})
            assert page1["data"]["next_offset"] == 20
            assert page2["data"]["offset_chars"] == 20
            text_schema = next(t.inputSchema for t in tools if t.name == "ler_texto")
            assert text_schema["properties"]["limit"]["maximum"] == 32768
            assert "maximum" not in text_schema["properties"]["offset"]
            for name, arguments in [("buscar_itens", {"query": "aurora", "limit": 51}),
                ("ler_texto", {"item_id": first, "offset": -1}),
                ("ler_texto", {"item_id": first, "limit": 32769})]:
                assert (await s.call_tool(name, arguments)).isError

            # Todos os formatos passam pelo IPED real, sem lista de MIME permitidos.
            expected = json.loads(Path(__file__).with_name("formatos_esperados.json").read_text(encoding="utf-8"))
            all_items = await call("buscar_itens", {"query": "*:*", "limit": 50})
            by_name = {i["name"]: i for i in all_items["data"]["items"]}
            assert set(expected) <= set(by_name)
            assert all_items["data"]["categoria"] is None
            assert info["data"]["total_items"] == all_items["data"]["total"]
            assert len(by_name) == all_items["data"]["total"]  # conjunto didático cabe nesta página
            for category in categories:
                descendants = {c["name"].casefold() for c in categories
                               if c["path"][:len(category["path"])] == category["path"]}
                expected_ids = {i["item_id"] for i in by_name.values()
                                if any(c.casefold() in descendants for c in i["categories"])}
                collected, offset = [], 0
                while True:
                    filtered = await call("buscar_itens", {"query": "*:*",
                        "categoria": category["name"], "offset": offset, "limit": 2})
                    assert filtered["ok"], filtered
                    page = filtered["data"]
                    assert page["categoria"] == category["name"]
                    assert page["total"] == category["item_count"] == len(expected_ids)
                    collected.extend(i["item_id"] for i in page["items"])
                    if page["next_offset"] is None:
                        break
                    assert page["next_offset"] > offset
                    offset = page["next_offset"]
                assert len(collected) == len(set(collected))
                assert set(collected) == expected_ids
                intersected = await call("buscar_itens", {"query": "aurora",
                    "categoria": category["name"], "limit": 50})
                assert intersected["ok"]
                assert {i["item_id"] for i in intersected["data"]["items"]} == expected_ids & {i["item_id"] for i in matches}
                # Nome/label retornados pelo caso são aceitos sem diferenciar caixa.
                alias = await call("buscar_itens", {"query": "*:*",
                    "categoria": " " + category["label"].swapcase() + " ", "limit": 50})
                assert alias["ok"] and alias["data"]["total"] == len(expected_ids)
            documents = next(c for c in categories if c["name"] == "Documents")
            assert documents["item_count"] == 3
            strict = await call("buscar_itens", {"query": "*:* OR name:relatorio.pdf",
                "categoria": "PDF Documents", "limit": 50})
            assert strict["ok"] and strict["data"]["total"] == 1
            assert strict["data"]["items"][0]["name"] == "relatorio.pdf"
            beyond = await call("buscar_itens", {"query": "*:*",
                "categoria": "Documents", "offset": 10001})
            assert beyond["ok"] and beyond["data"]["total"] == 3
            assert beyond["data"]["items"] == [] and beyond["data"]["next_offset"] is None
            for invalid in ["categoria inexistente", 'PDF Documents" OR *:*', "  "]:
                rejected = await call("buscar_itens", {"query": "*:*", "categoria": invalid})
                assert not rejected["ok"] and "CATEGORIA_INEXISTENTE" in rejected["error"]["message"]
            assert (await s.call_tool("buscar_itens", {"query": "*:*", "categoria": ""})).isError
            print("CATEGORIAS OK:", len(categories), "categorias; pais, contagens, interseção e paginação")
            for filename, token in expected.items():
                item_id = by_name[filename]["item_id"]
                parts, offset, reference = [], 0, None
                while True:
                    extracted = await call("ler_texto", {"item_id": item_id, "offset": offset, "limit": 4096})
                    assert extracted["ok"], (filename, extracted)
                    body = extracted["data"]
                    assert body["origin"] == "iped_text_viewer_pipeline"
                    assert not any(body["extraction_flags"].values()), (filename, body["extraction_flags"])
                    parts.append(body["text"])
                    if not body["has_more"]:
                        break
                    assert body["next_offset"] == offset + body["returned_chars"]
                    offset = body["next_offset"]
                complete = ''.join(parts)
                if token is not None:
                    assert token in complete, (filename, complete[:250])
                if filename == "unicode_longo.txt":
                    unicode_text = (dados / 'formatos' / filename).read_text(encoding='utf-8').strip()
                    assert unicode_text in complete.replace('\r\n', '\n') and '\ufffd' not in complete
                    assert len(complete) > 65536
                    far = await call("ler_texto", {"item_id": item_id, "offset": 70001, "limit": 17})
                    assert far["ok"] and far["data"]["text"] == complete[70001:70018]
                print('TEXTO OK:', filename, 'MIME:', by_name[filename]['media_type'], 'chars:', len(complete))
            missing = await call("obter_metadados", {"item_id": 2147483647})
            assert not missing["ok"] and missing["error"]["message"] == "ITEM_INEXISTENTE"
            invalid = await s.call_tool("buscar_itens", {"query": "aurora", "limit": 51})
            assert invalid.isError
            marker_name = "AULA_AURORA_" + uuid4().hex[:8]
            created = await call("criar_marcador", {"nome": marker_name, "comentario": "Teste didático sintético"})
            assert created["ok"] and created["data"]["created"] and created["data"]["persisted"]
            marker_id = created["data"]["marcador_id"]
            duplicate = await call("criar_marcador", {"nome": marker_name, "comentario": "Não alterar"})
            assert duplicate["ok"] and not duplicate["data"]["created"]
            assert duplicate["data"]["comentario"] == "Teste didático sintético"
            catalog = await call("listar_marcadores", {"limit": 100})
            assert any(b["marcador_id"] == marker_id for b in catalog["data"]["items"])
            selected = [item["item_id"] for item in matches[:2]]
            bad = await call("associar_itens_marcador", {"marcador_id": marker_id,
                "item_ids": [selected[0], 2147483647]})
            assert not bad["ok"]
            before = await call("listar_marcadores", {"item_id": selected[0]})
            assert all(x["marcador_id"] != marker_id for x in before["data"]["items"])
            added = await call("associar_itens_marcador", {"marcador_id": marker_id,
                "item_ids": [*selected, selected[0]]})
            assert added["ok"] and added["data"]["added_count"] == 2
            assert added["data"]["item_count"] == 2 and added["data"]["persisted"]
            again = await call("associar_itens_marcador", {"marcador_id": marker_id, "item_ids": selected})
            assert again["ok"] and again["data"]["added_count"] == 0
    # Novo subprocesso e nova JVM: comprovar persistência e bloqueio de escrita.
    params.env["IPED_ALLOW_BOOKMARK_WRITE"] = "0"
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            for item_id in selected:
                result = await s.call_tool("listar_marcadores", {"item_id": item_id})
                listing = result.structuredContent
                assert listing["ok"]
                saved = next(x for x in listing["data"]["items"] if x["marcador_id"] == marker_id)
                assert saved["nome"] == marker_name and saved["item_count"] == 2
            blocked = await s.call_tool("criar_marcador", {"nome": "NAO_DEVE_SER_CRIADO"})
            assert not blocked.structuredContent["ok"]
            assert blocked.structuredContent["error"]["message"].startswith("ESCRITA_DESABILITADA")
    print("OK: IPED real, sete tools, texto multiformato, Unicode, marcadores, persistência em nova JVM e escrita desabilitada")


if __name__ == "__main__":
    asyncio.run(main())
