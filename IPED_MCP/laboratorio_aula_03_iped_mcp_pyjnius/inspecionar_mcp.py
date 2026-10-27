"""Cliente sem LLM. Descobre tools e confere consultas pelo protocolo real."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(query, limit):
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).with_name("servidor_mcp.py"))],
        env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            catalog = await session.list_tools()
            print(json.dumps({"tools": [t.model_dump(mode="json") for t in catalog.tools]},
                             ensure_ascii=False, indent=2))

            async def call(name, arguments):
                result = await session.call_tool(name, arguments)
                if result.isError:
                    raise RuntimeError(str(result.content))
                data = result.structuredContent
                if data is None:
                    data = json.loads(next(c.text for c in result.content if c.type == "text"))
                print(json.dumps(data, ensure_ascii=False, indent=2))
                if not data["ok"]:
                    raise RuntimeError("Consulta retornou erro de domínio")
                return data

            await call("caso_info", {})
            result = await call("buscar_itens", {"query": query, "limit": 2})
            if not result["data"]["items"]:
                raise RuntimeError("A consulta não retornou itens neste caso")
            item_id = result["data"]["items"][0]["item_id"]
            await call("obter_metadados", {"item_id": item_id})
            await call("ler_texto", {"item_id": item_id, "limit": limit})
            await call("listar_marcadores", {"item_id": item_id})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="aurora")
    parser.add_argument("--limit", type=int, default=4096)
    args = parser.parse_args()
    asyncio.run(main(args.query, args.limit))
