import base64
import queue
import re
import threading
from pathlib import Path

import gradio as gr
import requests

from agents.bible_scholar import (
    DEFAULT_MODEL,
    MODEL_OPTIONS,
    OLLAMA_BASE_URL,
    OLLAMA_MODELS,
    continue_conversation,
    generate_study_guide,
)
from agents.bible_xref import get_cross_references
from bible_api.esv_api import get_passage, get_passage_markup, get_passage_text

APP_LOGO = Path(__file__).resolve().parent / "media" / "bible_app_logo.png"
CHAT_HEADER_MD = """## Continue the Conversation

Continue the conversation by asking followup questions"""
CHAT_SECTION_HIDDEN = "chat-section-hidden"
CHAT_SECTION_CSS = """
<style>
.chat-section-hidden { display: none !important; }
</style>
"""


def _header_html() -> str:
    logo_data = base64.b64encode(APP_LOGO.read_bytes()).decode("ascii")
    return f"""
<div style="display:flex;align-items:center;justify-content:flex-start;gap:12px;width:100%;margin:0 0 12px 0;">
  <img src="data:image/png;base64,{logo_data}" alt="Bible app logo"
       style="height:72px;width:72px;object-fit:contain;display:block;flex-shrink:0;">
  <h1 style="margin:0;padding:0;font-size:2rem;font-weight:700;line-height:1.2;">
    Bible Verse Contextual Study Guide
  </h1>
</div>
"""


SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
LOADING_MESSAGES = (
    "Gathering passage texts",
    "Analyzing cross references",
    "Consulting the Biblical Scholar",
    "Preparing your study guide",
)


def loading_status(frame_index: int) -> str:
    spinner = SPINNER_FRAMES[frame_index % len(SPINNER_FRAMES)]
    message = LOADING_MESSAGES[(frame_index // 2) % len(LOADING_MESSAGES)]
    return f"### {spinner} {message}\n\n*This may take a minute...*"


def lookup_verse(reference: str) -> tuple[dict, str, str, str, dict, dict, dict, dict, list, str]:
    """Fetch and display the target verse."""
    label = reference.strip() or "Verse Text"
    if not re.match(r"^(?:[0-9]+\s+)?[A-Za-z]+ [0-9]+:[0-9]+$", reference):
        return (
            gr.update(
                value="<p>Invalid reference format. Please use the format 'Book Chapter:Verse' (i.e. John 3:16)</p>",
                label="Verse Text",
            ),
            "",
            "",
            "",
            *hide_chat_section(),
            "",
            "",
        )

    try:
        passage = get_passage(reference)
        verse_markup = get_passage_markup(passage)
        target_verse_text = get_passage_text(passage)
    except (requests.RequestException, ValueError) as exc:
        return (
            gr.update(value=f"<p>Could not fetch passage: {exc}</p>", label="Verse Text"),
            "",
            "",
            "",
            *hide_chat_section(),
            "",
            "",
        )

    return (
        gr.update(value=verse_markup, label=label),
        "Fetching cross references...",
        "Fetching cross references...",
        "",
        *hide_chat_section(),
        "",
        target_verse_text,
    )


def lookup_cross_references(
    reference: str, target_verse_text: str, model: str
) -> tuple[str, str, str]:
    """Fetch and display New and Old Testament cross references."""
    if not target_verse_text:
        return "", "", ""

    try:
        new_testament_refs = get_cross_references(reference, "New Testament", model)
    except Exception as exc:
        new_testament_refs = f"Could not fetch cross references: {exc}"

    try:
        old_testament_refs = get_cross_references(reference, "Old Testament", model)
    except Exception as exc:
        old_testament_refs = f"Could not fetch cross references: {exc}"

    return new_testament_refs, old_testament_refs, loading_status(0)


def _is_study_guide_ready(study_content: str) -> bool:
    content = (study_content or "").strip()
    if not content or content.startswith("Could not generate study guide"):
        return False
    if "*This may take a minute...*" in content:
        return False
    return (
        "Biblical Study Guide" in content
        or "## 1. The Target Text" in content
    )


def reveal_chat_section(study_content: str):
    """Show the follow-up chat section after a study guide is ready."""
    if _is_study_guide_ready(study_content):
        return (
            study_content.strip(),
            gr.update(value=CHAT_HEADER_MD, elem_classes=[]),
            gr.update(visible=True),
            gr.update(value="", interactive=True, elem_classes=[]),
            gr.update(interactive=True, elem_classes=[]),
        )

    return (
        "",
        gr.update(value="", elem_classes=[CHAT_SECTION_HIDDEN]),
        gr.update(value=[], visible=False),
        gr.update(value="", interactive=False, elem_classes=[CHAT_SECTION_HIDDEN]),
        gr.update(interactive=False, elem_classes=[CHAT_SECTION_HIDDEN]),
    )


def hide_chat_section():
    """Hide and reset the follow-up chat section."""
    return (
        gr.update(value="", elem_classes=[CHAT_SECTION_HIDDEN]),
        gr.update(value=[], visible=False),
        gr.update(value="", interactive=False, elem_classes=[CHAT_SECTION_HIDDEN]),
        gr.update(interactive=False, elem_classes=[CHAT_SECTION_HIDDEN]),
    )


def chat_followup(
    user_message: str,
    history: list,
    study_guide: str,
    model: str,
) -> tuple[list, str]:
    """Handle follow-up chat using the generated study guide as context."""
    history = history or []
    if not user_message.strip():
        return history, ""

    if not _is_study_guide_ready(study_guide):
        history = history + [
            {"role": "user", "content": user_message.strip()},
            {
                "role": "assistant",
                "content": "Please generate a study guide before continuing the conversation.",
            },
        ]
        return history, ""

    history = history + [{"role": "user", "content": user_message.strip()}]
    try:
        reply = continue_conversation(study_guide, history[:-1], user_message, model)
    except Exception as exc:
        reply = f"Could not get a response: {exc}"

    history = history + [{"role": "assistant", "content": reply}]
    return history, ""


def generate_study(
    reference: str,
    target_verse_text: str,
    old_testament_refs: str,
    new_testament_refs: str,
    user_question: str,
    model: str,
):
    """Animate loading, then stream the textual study guide to the UI."""
    if not target_verse_text:
        yield ""
        return

    chunk_queue: queue.Queue[str | None] = queue.Queue()
    errors: list[Exception] = []

    def run() -> None:
        try:
            for partial in generate_study_guide(
                reference,
                target_verse_text,
                old_testament_refs,
                new_testament_refs,
                user_question,
                model,
            ):
                chunk_queue.put(partial)
        except Exception as exc:
            errors.append(exc)
        finally:
            chunk_queue.put(None)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    frame = 0
    streaming = False

    while True:
        try:
            partial = chunk_queue.get(timeout=0.4 if not streaming else None)
        except queue.Empty:
            yield loading_status(frame)
            frame += 1
            continue

        if partial is None:
            break

        streaming = True
        yield partial

    thread.join()

    if errors:
        yield f"Could not generate study guide: {errors[0]}"
    elif not streaming:
        yield "Could not generate study guide: empty response"


def create_app() -> gr.Blocks:
    with gr.Blocks(title="Bible XRef") as app:
        gr.HTML(_header_html())
        gr.Markdown("""Enter a Bible verse to generate a contextual study guide.\n\nThe study guide will automatically cross reference several Old and New Testament verses 
                       to provide a comprehensive study of the input verse.\n\nYou can also provide an optional study question to focus the study guide on a specific topic.""")

        with gr.Row():
            with gr.Column():
                verse_input = gr.Textbox(
                    label="Bible Verse",
                    placeholder="e.g. John 3:16",
                    lines=1,
                )
                question_input = gr.Textbox(
                    label="Study Question (optional)",
                    placeholder="e.g. What does this verse teach about God's love?",
                    lines=2,
                )
            with gr.Column():
                model_input = gr.Dropdown(
                    label="LLM Model",
                    choices=MODEL_OPTIONS,
                    value=DEFAULT_MODEL,
                )
                ollama_models = "\n".join(f"- `{name}`" for name in OLLAMA_MODELS)
                gr.Markdown(
                    f"Ollama models require Ollama running locally.\n\n"
                    f"{ollama_models}"
                )
        with gr.Row():
            submit_btn = gr.Button("Submit", variant="primary", scale=0, size="lg")
        verse_output = gr.HTML(label="Verse Text")
        new_testament_output = gr.Textbox(
            label="New Testament Cross References",
            lines=2,
            interactive=False,
        )
        old_testament_output = gr.Textbox(
            label="Old Testament Cross References",
            lines=2,
            interactive=False,
        )
        study_output = gr.Markdown()
        gr.HTML(CHAT_SECTION_CSS)
        chat_header = gr.Markdown("", elem_classes=[CHAT_SECTION_HIDDEN])
        chatbot = gr.Chatbot(height=400, visible=False)
        chat_input = gr.Textbox(
            label="Follow-up question",
            placeholder="Ask a follow-up question about the study guide...",
            lines=2,
            interactive=False,
            elem_classes=[CHAT_SECTION_HIDDEN],
        )
        chat_submit_btn = gr.Button(
            "Send",
            variant="primary",
            interactive=False,
            elem_classes=[CHAT_SECTION_HIDDEN],
            scale=0,
        )
        target_text_state = gr.State("")
        study_guide_state = gr.State("")

        chat_outputs = [chat_header, chatbot, chat_input, chat_submit_btn]

        lookup_outputs = [
            verse_output,
            new_testament_output,
            old_testament_output,
            study_output,
            *chat_outputs,
            study_guide_state,
            target_text_state,
        ]
        cross_ref_outputs = [
            new_testament_output,
            old_testament_output,
            study_output,
        ]
        study_inputs = [
            verse_input,
            target_text_state,
            old_testament_output,
            new_testament_output,
            question_input,
            model_input,
        ]

        def wire_submit(event):
            event = event.then(
                fn=lookup_cross_references,
                inputs=[verse_input, target_text_state, model_input],
                outputs=cross_ref_outputs,
            )
            event = event.then(
                fn=generate_study,
                inputs=study_inputs,
                outputs=study_output,
            )
            return event.then(
                fn=reveal_chat_section,
                inputs=study_output,
                outputs=[study_guide_state, *chat_outputs],
            )

        submit_event = submit_btn.click(
            fn=lookup_verse, inputs=verse_input, outputs=lookup_outputs
        )
        wire_submit(submit_event)

        submit_event = verse_input.submit(
            fn=lookup_verse, inputs=verse_input, outputs=lookup_outputs
        )
        wire_submit(submit_event)

        chat_submit_btn.click(
            chat_followup,
            inputs=[chat_input, chatbot, study_guide_state, model_input],
            outputs=[chatbot, chat_input],
        )

    return app


def main():
    create_app().launch()


if __name__ == "__main__":
    main()
