# AI Engineer — Learning Journey

This repo is my hands-on path to becoming an AI Engineer. Each folder is one small,
self-contained project. They start with a first LLM API call and build up to RAG,
tool-using agents, LangGraph workflows, multi-agent systems and a custom MCP server.

Every project is a separate Python app managed with [uv](https://docs.astral.sh/uv/),
and most of them use **Groq** as the LLM provider (`llama-3.3-70b-versatile`,
`openai/gpt-oss-20b`, `openai/gpt-oss-120b`).

---

## What I learned, step by step

| # | Folder | Topic | What I learned and how |
|---|--------|-------|-------------------|
| 1 | [day1](day1/) | **First LLM call** | Loaded an API key from `.env`, created a Groq client, and sent a single `user` message with `chat.completions.create` to get a response. |
| 2 | [day2](day2/) | **System prompts & temperature** | Added a `system` message to give the model a persona, and used `temperature` to control how creative or random the answers are. |
| 3 | [day3](day3/) | **Tokens & limits** | Ran several prompts with `max_tokens`, then read `usage` (prompt, completion and total tokens) and `finish_reason` to see when an answer gets cut off. |
| 4 | [day4](day4/) | **Structured output (JSON + Pydantic)** | Defined a Pydantic model, put its JSON schema in the system prompt, used `response_format={"type": "json_object"}`, and checked the result by loading it back into the model. |
| 5 | [day5](day5/) | **Resume ↔ Job matcher** | Read real resumes from PDF (`pypdf`) and DOCX (`python-docx`), pulled structured `Job` and `Resume` objects out of them with the LLM, and scored how well each candidate matches. |
| 6 | [day6](day6/) | **Prompt engineering** | Wrote structured prompts with sections (ROLE, TASK, CONSTRAINT, OUTPUT FORMAT, EXAMPLE, FALLBACK) and used them to classify support tickets reliably. |
| 7 | [day7](day7/) | **ReAct pattern from scratch** | Built a shopping assistant that loops through *Thought → Action → Observation*. It reads the model's text output, calls Python tools (price lookup, calculator), and sends the results back to the model. |
| 8 | [day8](day8/) | **Prompt chaining** | Split one big task into steps: extract the resume, then extract the JD, then match the two. Each step's output becomes the next step's input. |
| 9 | [RAG](RAG/) | **Retrieval-Augmented Generation** | `rag.py`: made embeddings with `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dims), retrieved the best document by **cosine similarity**, and grounded the LLM answer in it. `qdrant.py`: moved the vectors into the **Qdrant Cloud** vector DB. `qdrantfull.py`: added **payload indexes and metadata filters** and learned how the HNSW index works. |
| 10 | [Agents](Agents/) | **First real AI agent** | Used native **tool calling** with JSON tool schemas. The agent can search the web (**Tavily**) and use a safe AST-based calculator, then decides by itself which tool to call. |
| 11 | [langGraph](langGraph/) | **LangGraph workflows** | `lang.py`: the basics (State, Nodes, Edges, Conditional Edges, START/END). `restraunt.py`: a restaurant system where an LLM **router** (with structured Pydantic output) picks the next node (take order → cook → serve → end). |
| 12 | [MultiAgent](MultiAgent/) | **Multi-agent system** | A **Manager agent** plans the steps and hands them to worker agents (a Search Agent and a Math Agent). Each step's result is passed to the next step, the final answers are combined, and every request is logged to `notebook.json`. |
| 13 | [mcpserver](mcpserver/) | **Building my own MCP server** | Created an MCP server ("MCP_Kitchen") with the `mcp` SDK and exposed a custom tool using `@mcp.tool()`, so any MCP client (like Claude) can find and call it. |

---

## Concepts covered

- **LLM basics:** messages and roles, system prompts, temperature, tokens, finish reasons
- **Reliable outputs:** JSON mode, Pydantic schemas, validation
- **Prompting:** structured prompts, few-shot examples, fallbacks, prompt chaining
- **Agents:** the ReAct loop, native tool and function calling, safe tool design
- **RAG:** embeddings, cosine similarity, vector databases (Qdrant), metadata filtering, HNSW
- **Orchestration:** LangGraph state machines, conditional routing, LLM-as-router
- **Multi-agent:** manager/worker planning, passing context between agents, logging
- **Protocols:** Model Context Protocol (MCP) servers and tools

## Tech stack

Python 3.11+, uv, Groq, Pydantic, sentence-transformers, NumPy, Qdrant, Tavily,
LangChain, LangGraph, MCP SDK, pypdf, python-docx

---

## How to run a project

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Go into a project folder and install its dependencies:
   ```bash
   cd day1
   uv sync
   ```
3. Create a `.env` file in that folder with the keys it needs:
   ```env
   Groq_API_KEY=your_groq_key        # day1–day5, RAG, Agents, MultiAgent
   GROQ_API_KEY=your_groq_key        # day6–day8, langGraph
   TAVILY_API_KEY=your_tavily_key    # Agents, MultiAgent
   QDRANT_URL=your_qdrant_url        # RAG (qdrant*.py)
   QDRANT_API_KEY=your_qdrant_key    # RAG (qdrant*.py)
   ```
4. Run the script:
   ```bash
   uv run hello.py          # e.g. day1
   uv run react.py          # e.g. day7
   uv run restraunt.py      # e.g. langGraph
   uv run mcpserver.py      # e.g. mcpserver
   ```

> `.env` files are git-ignored, so never commit your API keys.
