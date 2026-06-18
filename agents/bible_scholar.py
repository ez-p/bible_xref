import os

from dotenv import load_dotenv
from openai import OpenAI

from bible_api.esv_api import get_passage, get_passage_text

load_dotenv()

OLLAMA_BASE_URL = "http://localhost:11434/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

MODEL_OPTIONS = [
    "gpt-5.4",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "deepseek-r1",
    "llama3.2",
    "gpt-oss",
]
DEFAULT_MODEL = "gpt-5.4"

GEMINI_MODELS = {"gemini-2.5-flash", "gemini-3.5-flash"}

OLLAMA_MODELS = {
    "deepseek-r1": "deepseek-r1:1.5b",
    "llama3.2": "llama3.2:latest",
    "gpt-oss": "gpt-oss:latest",
}

system_prompt = """
You are an expert Biblical Scholar and Hermeneutics Professor specializing in the "Scripture Interprets Scripture"
(Scriptura sui ipsius interpres) methodology. Your goal is to help users understand a specific Target Verse by using
the provided Old Testament and New Testament cross-references as the primary commentary.

Adhere strictly to these exegetical guidelines:
1. THE PRINCIPLE OF COHERENCE: Treat the Bible as a unified narrative. Use the provided cross-references to explain the
target verse's theological depth, linguistic roots, and fulfillment.
2. TYPES OF CONNECTIONS: Identify and explain why the cross-references are relevant:
   - Verbal Connections: Matching key words, phrases, or original language concepts.
   - Conceptual/Theological Connections: Shared motifs, doctrines, or themes.
   - Parallel/Fulfillment Connections: Prophecy and fulfillment, or parallel historical accounts.
3. CONTEXT INTEGRITY: Ensure you do not rip a cross-reference out of its immediate context. Respect the original author's
intent in both the target verse and the references.
4. NO EXTERNAL SPECULATION: Rely primarily on the provided texts to interpret the target verse rather than introducing
external modern commentaries or unrelated theological debates.

Structure your final Textual Study Guide using the following Markdown format:

# Biblical Study Guide: [Insert Target Verse Reference]

## 1. The Target Text
*Provide a brief 2-3 sentence overview of the immediate literary and historical context of the target verse.*

## 2. Deep-Dive Analysis: Old Testament Foundations
*Analyze how the provided Old Testament cross-reference(s) anchor, illuminate, or provide the historical/theological
foundation for the target verse. Focus on verbal or conceptual links.*

## 3. Deep-Dive Analysis: New Testament Fulfillments & Expansions
*Analyze how the provided New Testament cross-reference(s) expand, apply, or fulfill the themes of the target verse.
Focus on verbal or conceptual links.*

## 4. Synthesis: The Unfolding Theme
*Synthesize the target text and cross-references into a cohesive theological summary. How do these texts together reveal
a grander biblical truth?*

## 5. Guided Reflection & Observation Questions
*Provide 3 inductive questions (Observation, Interpretation, Application) based entirely on the interplay between these
specific texts to help the student study further.*
"""

user_prompt = """
Please generate a comprehensive Textual Study Guide using the Scripture Interprets Scripture methodology based on the
following input data:

### TARGET VERSE TO INTERPRET:
- **Reference:** {{ target_verse_reference }}
- **Text:** "{{ target_verse_text }}"

### PROVIDED CROSS-REFERENCES:

#### Old Testament Reference(s):
{{ loop through old testament references }}
- **Reference:** {{ ot_reference }}
- **Text:** "{{ ot_text }}"
{{ end loop }}

#### New Testament Reference(s):
{{ loop through new testament references }}
- **Reference:** {{ nt_reference }}
- **Text:** "{{ nt_text }}"
{{ end loop }}

{{ user_question_context }}

Following the structure outlined in your system instructions and the user question context, analyze these specific passages to
demonstrate how they interpret, illuminate, and clarify the Target Verse. Do not invent external cross-references; rely strictly
on the texts provided above.
"""

OLD_TESTAMENT_LOOP = """{{ loop through old testament references }}
- **Reference:** {{ ot_reference }}
- **Text:** "{{ ot_text }}"
{{ end loop }}"""

NEW_TESTAMENT_LOOP = """{{ loop through new testament references }}
- **Reference:** {{ nt_reference }}
- **Text:** "{{ nt_text }}"
{{ end loop }}"""


def _parse_references(references: str) -> list[str]:
    return [reference.strip() for reference in references.split(",") if reference.strip()]


def _fetch_reference_texts(references: str) -> list[tuple[str, str]]:
    return [(reference, get_passage_text(get_passage(reference))) for reference in _parse_references(references)]


def _format_reference_block(reference_texts: list[tuple[str, str]]) -> str:
    return "\n".join(
        f'- **Reference:** {reference}\n- **Text:** "{text}"'
        for reference, text in reference_texts
    )


def _format_user_question_context(user_question: str | None) -> str:
    question = (user_question or "").strip()
    if not question:
        return ""
    return f"""### ADDITIONAL USER CONTEXT:
- **Question:** {question}

Please incorporate this question as additional context when preparing the study guide.
"""


def _build_user_message(
    target_reference: str,
    target_verse_text: str,
    old_testament_references: str,
    new_testament_references: str,
    user_question: str | None = None,
) -> str:
    message = user_prompt.replace("{{ target_verse_reference }}", target_reference)
    message = message.replace("{{ target_verse_text }}", target_verse_text)
    message = message.replace(
        OLD_TESTAMENT_LOOP,
        _format_reference_block(_fetch_reference_texts(old_testament_references)),
    )
    message = message.replace(
        NEW_TESTAMENT_LOOP,
        _format_reference_block(_fetch_reference_texts(new_testament_references)),
    )
    message = message.replace(
        "{{ user_question_context }}",
        _format_user_question_context(user_question),
    )
    return message


def _create_client(model: str) -> tuple[OpenAI, str]:
    if model == "gpt-5.4":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        return OpenAI(api_key=api_key), model

    if model in GEMINI_MODELS:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        return OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL), model

    if model in OLLAMA_MODELS:
        return OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL), OLLAMA_MODELS[model]

    raise ValueError(f"Unsupported model: {model}")


def generate_study_guide(
    target_reference: str,
    target_verse_text: str,
    old_testament_references: str,
    new_testament_references: str,
    user_question: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a textual study guide from the target verse and cross references."""
    client, model_name = _create_client(model)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": _build_user_message(
                    target_reference,
                    target_verse_text,
                    old_testament_references,
                    new_testament_references,
                    user_question,
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")

    return content.strip()
