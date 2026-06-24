---
title: bible_xref
app_file: main.py
sdk: gradio
sdk_version: 6.18.0
---

# Bible Verse Contextual Study Guide

A Gradio web app that helps you study a Bible verse using the **Scripture interprets Scripture** approach. Enter a verse reference, and the app will:

1. Fetch the verse text from the [ESV API](https://api.esv.org/)
2. Look up Old and New Testament cross references
3. Stream a detailed textual study guide written by an LLM

**Live demo:** https://huggingface.co/spaces/paulpowell/bible_xref

## Requirements

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or `pip`
- API keys for the services you plan to use (see below)
- **[Ollama](https://ollama.com/)** (optional, only for local LLM models)

## Download the project

Clone the repository:

```bash
git clone https://github.com/ez-p/bible_xref.git
cd bible_xref
```

If you do not use Git, download the project as a ZIP from GitHub and extract it, then open a terminal in the project folder.

## Configuration

Create a `.env` file in the project root. This file is listed in `.gitignore` and should not be committed.

```env
# Required for verse text and cross references (non-Ollama models)
ESV_API_TOKEN=your_esv_api_token
OPENAI_API_KEY=your_openai_api_key

# Optional — only needed for the models you select in the UI
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

| Variable | Used for |
| --- | --- |
| `ESV_API_TOKEN` | Fetching Bible verse text from [api.esv.org](https://api.esv.org/account/create) |
| `OPENAI_API_KEY` | Default study model (`gpt-5.4`) and cross-reference lookup (`gpt-4o-mini`) |
| `GOOGLE_API_KEY` | Gemini models (`gemini-2.5-flash`, `gemini-3.5-flash`) |
| `ANTHROPIC_API_KEY` | Claude model (`claude-sonnet-4-6`) |

Ollama models do not require cloud API keys, but Ollama must be running locally at `http://localhost:11434`.

## Install and run

### Using uv (recommended)

```bash
uv sync
uv run main.py
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Gradio prints a local URL (typically `http://127.0.0.1:7860`). Open that address in your browser.

## Using the app

1. Enter a Bible verse reference, for example `John 3:16` or `1 Peter 1:19`.
2. Optionally enter a **Study Question** to steer the generated guide.
3. Choose an **LLM Model** from the dropdown (default: `gpt-5.4`).
4. Click **Submit** or press **Enter** in the verse field.

Results appear in stages:

- **Verse Text** — ESV passage HTML
- **Cross References** — three Old Testament and three New Testament references
- **Study Guide** — streamed markdown analysis at the bottom of the page

While the study guide is being prepared, an animated status message is shown until streaming begins.

## Supported LLM models

| Model | Provider | Notes |
| --- | --- | --- |
| `gpt-5.4` | OpenAI | Default study guide model |
| `claude-sonnet-4-6` | Anthropic | Requires `ANTHROPIC_API_KEY` |
| `gemini-2.5-flash` | Google | Requires `GOOGLE_API_KEY` |
| `gemini-3.5-flash` | Google | Requires `GOOGLE_API_KEY` |
| `deepseek-r1` | Ollama | Maps to `deepseek-r1:1.5b` locally |
| `llama3.2` | Ollama | Maps to `llama3.2:latest` locally |
| `gpt-oss` | Ollama | Maps to `gpt-oss:latest` locally |

When an Ollama model is selected, both cross-reference lookup and the study guide use that local model. All other models use `gpt-4o-mini` for cross references and the selected model for the study guide.

### Local Ollama setup

Install Ollama, start the service, and pull the models you need:

```bash
ollama pull deepseek-r1:1.5b
ollama pull llama3.2
ollama pull gpt-oss
```

Verify they are available:

```bash
ollama list
```

## Project layout

```
bible_xref/
├── main.py              # Gradio UI and orchestration
├── agents/
│   ├── bible_xref.py    # Cross-reference lookup
│   └── bible_scholar.py # Study guide generation (streaming LLM)
├── bible_api/
│   └── esv_api.py       # ESV Bible API client
├── media/
│   └── bible_app_logo.png
├── pyproject.toml
└── .env                 # Your API keys (create this yourself)
```

## Deploying to Hugging Face Spaces

This repository includes Gradio Spaces metadata in the YAML front matter at the top of this file. Add your API keys as Space secrets rather than committing a `.env` file.
