import { tool } from "@opencode-ai/plugin"
import path from "node:path"

export default tool({
  description: "Aplica uma receita fechada sobre bytes e registra a saída localmente.",
  args: {
    receita_json: tool.schema.string().max(300000),
    fontes: tool.schema.array(tool.schema.string().min(1).max(200)).min(1).max(20),
  },
  async execute(args, context) {
    if (context.agent !== "analista") throw new Error("Uso exclusivo do analista")
    const python = path.resolve(context.directory, "..", ".venv", "Scripts", "python.exe")
    const script = path.join(context.directory, "calcular_receita.py")
    const proc = Bun.spawn([python, script], {
      cwd: context.directory, stdin: "pipe", stdout: "pipe", stderr: "pipe",
    })
    proc.stdin.write(JSON.stringify(args))
    proc.stdin.end()
    const [out, err, code] = await Promise.all([
      new Response(proc.stdout).text(), new Response(proc.stderr).text(), proc.exited,
    ])
    if (code !== 0) throw new Error(err.trim() || "Falha na receita")
    return out.trim()
  },
})
