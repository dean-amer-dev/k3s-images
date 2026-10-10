"""research-0: run GPT Researcher once for $QUERY and write the report to the Obsidian vault."""

import asyncio
import datetime
import os
import re
import sys

from fastmcp import Client

OBSIDIAN_MCP_URL = os.environ.get(
    "OBSIDIAN_MCP_URL", "http://obsidian-mcp-server.mcp.svc.cluster.local:8787/mcp"
)
NOTE_DIR = "Projects/llm-agents/research"


def setup_tracing() -> None:
    if not os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"):
        return
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from phoenix.otel import register

    provider = register(
        project_name=os.environ.get("PHOENIX_PROJECT_NAME", "agents"),
        auto_instrument=False,
    )
    OpenAIInstrumentor().instrument(tracer_provider=provider)


def load_prompt(query: str) -> tuple[str, str]:
    """Report instructions from the Phoenix prompt (name/tag from env) and a label for the note; empty text means use the built-in default."""
    name = os.environ.get("PHOENIX_PROMPT_NAME")
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not name or not endpoint:
        return "", "default"
    try:
        from phoenix.client import Client

        version = Client(base_url=endpoint).prompts.get(
            prompt_identifier=name, tag=os.environ.get("PHOENIX_PROMPT_TAG", "production")
        )
        messages = version.format(variables={"query": query, "question": query, "date": datetime.date.today().strftime("%A, %B %d, %Y")}).messages
        text = "\n\n".join(
            m["content"] if isinstance(m["content"], str) else "".join(p.get("text", "") for p in m["content"])
            for m in messages
        )
        if query not in text:
            # the report writer is not told the question otherwise
            text += f"\n\nResearch question: {query}"
        label = f"phoenix:{name}@{getattr(version, 'id', '?')}"
        print(f"using Phoenix prompt {label}")
        return text, label
    except Exception as e:
        print(f"WARNING: could not load Phoenix prompt {name!r}, using built-in default: {e}")
        return "", f"default (phoenix prompt unavailable: {type(e).__name__}: {str(e)[:150]!r})"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "report"


async def main() -> None:
    query = os.environ["QUERY"]
    setup_tracing()

    from gpt_researcher import GPTResearcher

    researcher = GPTResearcher(query=query, report_type="research_report")
    await researcher.conduct_research()
    prompt_text, prompt_label = load_prompt(query)
    report = await researcher.write_report(custom_prompt=prompt_text)
    sources = sorted(set(researcher.get_source_urls()))
    if not report or not sources:
        sys.exit(f"research produced no report or no sources (sources={len(sources)})")

    today = datetime.date.today().isoformat()
    path = f"{NOTE_DIR}/{today}-{slugify(query)}.md"
    note = (
        f"---\nstatus: active\ntype: note\nprompt: {prompt_label}\n---\n\n"
        f"Query: {query}\n\n{report}\n\n## Sources\n\n"
        + "\n".join(f"- {u}" for u in sources)
        + "\n"
    )
    async with Client(OBSIDIAN_MCP_URL) as client:
        await client.call_tool("write_note", {"path": path, "content": note})
    print(f"wrote {path} with {len(sources)} sources")


asyncio.run(main())
