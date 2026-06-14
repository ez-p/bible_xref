import re

import gradio as gr
import requests

from agents.bible_xref import get_cross_references
from bible_api.esv_api import get_passage, get_passage_markup


def lookup_verse(reference: str) -> tuple[dict, str, str]:
    """Return verse HTML markup and New/Old Testament cross references."""
    label = reference.strip() or "Verse Text"
    empty_refs = ("", "")
    if not re.match(r"^[A-Za-z]+ [0-9]+:[0-9]+$", reference):
        return (
            gr.update(
                value="<p>Invalid reference format. Please use the format 'Book Chapter:Verse' (i.e. John 3:16)</p>",
                label="Verse Text",
            ),
            *empty_refs,
        )

    try:
        passage = get_passage(reference)
        verse_markup = get_passage_markup(passage)
    except (requests.RequestException, ValueError) as exc:
        return (
            gr.update(value=f"<p>Could not fetch passage: {exc}</p>", label="Verse Text"),
            *empty_refs,
        )

    try:
        new_testament_refs = get_cross_references(reference, "New Testament")
    except Exception as exc:
        new_testament_refs = f"Could not fetch cross references: {exc}"

    try:
        old_testament_refs = get_cross_references(reference, "Old Testament")
    except Exception as exc:
        old_testament_refs = f"Could not fetch cross references: {exc}"

    return gr.update(value=verse_markup, label=label), new_testament_refs, old_testament_refs


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
        new_testament_output = gr.Markdown(label="New Testament Cross References")
        old_testament_output = gr.Markdown(label="Old Testament Cross References")

        outputs = [verse_output, new_testament_output, old_testament_output]
        submit_btn.click(fn=lookup_verse, inputs=verse_input, outputs=outputs)
        verse_input.submit(fn=lookup_verse, inputs=verse_input, outputs=outputs)

    return app


def main():
    create_app().launch()


if __name__ == "__main__":
    main()
