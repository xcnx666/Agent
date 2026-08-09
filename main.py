import argparse
import os
import time

from llm import LLM, MockLLM
from tools import ToolRegistry, ALL_TOOLS
from memory import BufferMemory
from agent import Agent, PlannerAgent
from core.guardrail import Guardrail
from core.tracer import Tracer
from prompt import SYSTEM_PROMPT
from logger import logger


def build_registry(use_mcp: bool) -> ToolRegistry:
    reg = ToolRegistry()
    for t in ALL_TOOLS:
        reg.register(t)

    if use_mcp:
        try:
            from tools.mcp.mcp_client import load_mcp_registry

            cfg_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "tools",
                "mcp",
                "config.json",
            )
            mcp_reg = load_mcp_registry(cfg_path)
            for name in mcp_reg.names():
                reg.register(mcp_reg.get(name))
            logger.info(f"MCP 共加载 {len(mcp_reg.names())} 个工具")
        except Exception as e:
            logger.warning(f"MCP 加载失败，已跳过: {e}")
    return reg


def print_summary(tracer: Tracer, elapsed: float) -> None:
    s = tracer.summary()
    print("\n── 执行摘要 ─────────────────────────────")
    print(f"耗时          : {elapsed:.1f}s")
    print(f"LLM 调用      : {s['llm_calls']}")
    print(f"工具调用      : {s['tool_calls']}（拦截 {s['blocked_tools']}）")
    print(f"输入 tokens   : {s['input_tokens']}")
    print(f"输出 tokens   : {s['output_tokens']}")
    print(f"估算成本      : ${s['estimated_cost_usd']}")


def main():
    ap = argparse.ArgumentParser(description="Koda Agent Harness")
    ap.add_argument("query", nargs="?", help="用户问题（不填进入交互模式）")
    ap.add_argument("--planner", action="store_true", help="使用 Planner 编排（先计划后执行）")
    ap.add_argument("--no-stream", action="store_true", help="关闭流式输出")
    ap.add_argument("--mock", action="store_true", help="使用 Mock LLM（无需 API key）")
    ap.add_argument("--allow-destructive", action="store_true", help="放行危险命令")
    ap.add_argument("--ask", action="store_true", help="危险命令人工审批（交互确认）")
    ap.add_argument("--no-mcp", action="store_true", help="不加载 MCP 工具")
    ap.add_argument("--max-steps", type=int, default=25, help="最大推理步数")
    ap.add_argument("--trace", metavar="PATH", help="将运行轨迹保存为 JSON（如 traces/run.json）")
    args = ap.parse_args()

    registry = build_registry(use_mcp=not args.no_mcp)
    memory = BufferMemory(system_prompt=SYSTEM_PROMPT)
    tracer = Tracer()

    approver = None
    if args.ask:

        def approver(cmd: str) -> bool:
            answer = input(f"\n⚠️ 检测到危险命令: {cmd}\n是否放行? [y/N] ").strip().lower()
            return answer in ("y", "yes")

    guardrail = Guardrail(allow_destructive=args.allow_destructive, approver=approver)

    if args.mock:
        if args.planner:
            # 脚本化演示：计划 + 两个步骤
            from config import ModelResponse

            llm = MockLLM(
                scripted=[
                    ModelResponse(content='["解析需求", "生成交付物"]'),
                    ModelResponse(content="步骤一：已解析需求。"),
                    ModelResponse(content="步骤二：交付物已生成。"),
                ]
            )
        else:
            llm = MockLLM(final_text="[Mock] 任务已完成。")
    else:
        llm = LLM(stream=not args.no_stream)

    agent_cls = PlannerAgent if args.planner else Agent
    agent = agent_cls(
        llm=llm,
        registry=registry,
        memory=memory,
        guardrail=guardrail,
        tracer=tracer,
        max_llm_steps=args.max_steps,
    )

    start = time.time()
    if args.query:
        resp = agent.run(args.query)
        elapsed = time.time() - start
        print("\n\n=== 最终回复 ===")
        print(resp.content)
        print_summary(tracer, elapsed)
        if args.trace:
            tracer.save(args.trace)
            print(f"轨迹已保存: {args.trace}")
        return

    print("Koda Harness 交互模式（输入 exit / quit 退出）")
    while True:
        try:
            q = input("\n🧑 > ")
        except (EOFError, KeyboardInterrupt):
            break
        if q.strip().lower() in ("exit", "quit"):
            break
        if not q.strip():
            continue
        t0 = time.time()
        resp = agent.run(q)
        print(f"\n🤖 {resp.content}")
        print_summary(tracer, time.time() - t0)
        if args.trace:
            tracer.save(args.trace)
            print(f"轨迹已保存: {args.trace}")


if __name__ == "__main__":
    main()
