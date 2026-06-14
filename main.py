import re

import gradio as gr
import requests

from bible_api.esv_api import get_passage, get_passage_markup


def lookup_verse(reference: str) -> tuple[dict, str]:
    """Return verse HTML markup and markdown content."""
    label = reference.strip() or "Verse Text"
    if not re.match(r"^[A-Za-z]+ [0-9]+:[0-9]+$", reference):
        return (
            gr.update(
                value="<p>Invalid reference format. Please use the format 'Book Chapter:Verse' (i.e. John 3:16)</p>",
                label="Verse Text",
            ),
            "",
        )

    try:
        passage = get_passage(reference)
        verse_markup = get_passage_markup(passage)
    except (requests.RequestException, ValueError) as exc:
        return (
            gr.update(value=f"<p>Could not fetch passage: {exc}</p>", label="Verse Text"),
            "",
        )

    return gr.update(value=verse_markup, label=label), "This is the markdown output"


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
        markdown_output = gr.Markdown(label="Notes")

        submit_btn.click(
            fn=lookup_verse, inputs=verse_input, outputs=[verse_output, markdown_output]
        )
        verse_input.submit(
            fn=lookup_verse, inputs=verse_input, outputs=[verse_output, markdown_output]
        )

    return app


def main():
    create_app().launch()


if __name__ == "__main__":
    main()
