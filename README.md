# Agent Core Examples

A collection of examples demonstrating how to build agent cores using various AI/LLM platforms and frameworks.

## Overview

This repository serves as a practical reference for implementing agent cores — the central reasoning and orchestration logic that drives AI agents — across different platforms. Each example is self-contained and illustrates the key patterns, tools, and conventions for that platform.

## Examples

| Directory | Platform | Description |
|-----------|----------|-------------|
| `simple_langchain/` | [LangChain](https://www.langchain.com/) | A basic agent core built with LangChain, demonstrating tool use, memory, and chain composition. |

> More examples covering additional platforms are coming soon.

## Platforms Covered (Planned)

- **LangChain** — Python-first framework for building LLM-powered applications with chains and agents
- **LangGraph** — Graph-based agent orchestration built on top of LangChain
- **CrewAI** — Multi-agent framework for role-based collaborative agents
- **AutoGen** — Microsoft's framework for multi-agent conversation and code execution
- **OpenAI Assistants API** — Native agent primitives from OpenAI (threads, tools, runs)
- **Anthropic Claude API** — Direct agent implementation using Claude's tool use and extended thinking

## Getting Started

Each example directory contains its own setup instructions. In general:

```bash
# Navigate to an example
cd simple_langchain

# Install dependencies (each example uses its own virtual environment)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the example
python main.py
```

## Prerequisites

- Python 3.10+
- API keys for the relevant LLM provider (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)

## Contributing

To add a new example:

1. Create a new directory named after the platform (e.g., `simple_crewai/`)
2. Include a `requirements.txt` and a `README.md` describing the example
3. Keep the implementation minimal and focused on the agent core pattern

## License

MIT
