import re

import gradio as gr
import requests

from agents.bible_scholar import generate_study_guide
from agents.bible_xref import get_cross_references
from bible_api.esv_api import get_passage, get_passage_markup, get_passage_text


def lookup_verse(reference: str) -> tuple[dict, str, str, str]:
    """Return verse HTML markup, cross references, and study guide."""
    label = reference.strip() or "Verse Text"
    empty_output = ("", "", "")
    if not re.match(r"^[A-Za-z]+ [0-9]+:[0-9]+$", reference):
        return (
            gr.update(
                value="<p>Invalid reference format. Please use the format 'Book Chapter:Verse' (i.e. John 3:16)</p>",
                label="Verse Text",
            ),
            *empty_output,
        )

    try:
        passage = get_passage(reference)
        verse_markup = get_passage_markup(passage)
        target_verse_text = get_passage_text(passage)
    except (requests.RequestException, ValueError) as exc:
        return (
            gr.update(value=f"<p>Could not fetch passage: {exc}</p>", label="Verse Text"),
            *empty_output,
        )

    try:
        new_testament_refs = get_cross_references(reference, "New Testament")
    except Exception as exc:
        new_testament_refs = f"Could not fetch cross references: {exc}"

    try:
        old_testament_refs = get_cross_references(reference, "Old Testament")
    except Exception as exc:
        old_testament_refs = f"Could not fetch cross references: {exc}"

    try:
        study_guide = generate_study_guide(
            reference,
            target_verse_text,
            old_testament_refs,
            new_testament_refs,
        )
    except Exception as exc:
        study_guide = f"Could not generate study guide: {exc}"

    return (
        gr.update(value=verse_markup, label=label),
        new_testament_refs,
        old_testament_refs,
        study_guide,
    )


def create_app() -> gr.Blocks:
    with gr.Blocks(title="Bible XRef") as app:
        gr.Markdown("# Bible Verse Contextual Study Guide")

        verse_input = gr.Textbox(
            label="Bible Verse",
            placeholder="e.g. John 3:16",
            lines=1,
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

        outputs = [verse_output, new_testament_output, old_testament_output, study_output]
        submit_btn.click(fn=lookup_verse, inputs=verse_input, outputs=outputs)
        verse_input.submit(fn=lookup_verse, inputs=verse_input, outputs=outputs)

    return app


def main():
    create_app().launch()


if __name__ == "__main__":
    main()
