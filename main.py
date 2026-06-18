import re
import threading
import time

import gradio as gr
import requests

from agents.bible_scholar import (
    DEFAULT_MODEL,
    MODEL_OPTIONS,
    OLLAMA_BASE_URL,
    OLLAMA_MODELS,
    generate_study_guide,
)
from agents.bible_xref import get_cross_references
from bible_api.esv_api import get_passage, get_passage_markup, get_passage_text

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


def lookup_verse(reference: str) -> tuple[dict, str, str, str, str]:
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
            "",
        )

    return (
        gr.update(value=verse_markup, label=label),
        "Fetching cross references...",
        "Fetching cross references...",
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


def generate_study(
    reference: str,
    target_verse_text: str,
    old_testament_refs: str,
    new_testament_refs: str,
    user_question: str,
    model: str,
):
    """Generate the textual study guide with animated loading feedback."""
    if not target_verse_text:
        yield ""
        return

    result: dict[str, str | None] = {"value": None, "error": None}

    def run() -> None:
        try:
            result["value"] = generate_study_guide(
                reference,
                target_verse_text,
                old_testament_refs,
                new_testament_refs,
                user_question,
                model,
            )
        except Exception as exc:
            result["error"] = str(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    frame = 0
    while thread.is_alive():
        yield loading_status(frame)
        frame += 1
        time.sleep(0.4)

    thread.join()

    if result["error"]:
        yield f"Could not generate study guide: {result['error']}"
    else:
        yield result["value"] or ""


def create_app() -> gr.Blocks:
    with gr.Blocks(title="Bible XRef") as app:
        gr.Markdown("# Bible Verse Contextual Study Guide")
        gr.Markdown("""Enter a Bible verse to generate a contextual study guide based on the your reference Bible verse 
                        and Old and New Testament cross references.""")

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
                    f"**Ollama models** require Ollama running locally at `{OLLAMA_BASE_URL}`:\n\n"
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
        target_text_state = gr.State("")

        lookup_outputs = [
            verse_output,
            new_testament_output,
            old_testament_output,
            study_output,
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
            return event.then(fn=generate_study, inputs=study_inputs, outputs=study_output)

        submit_event = submit_btn.click(
            fn=lookup_verse, inputs=verse_input, outputs=lookup_outputs
        )
        wire_submit(submit_event)

        submit_event = verse_input.submit(
            fn=lookup_verse, inputs=verse_input, outputs=lookup_outputs
        )
        wire_submit(submit_event)

    return app


def main():
    create_app().launch()


if __name__ == "__main__":
    main()
