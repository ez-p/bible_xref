import gradio as gr


def lookup_verse(reference: str) -> tuple[str, str]:
    """Return verse text and markdown content. Lookup to be implemented later."""
    return reference, "This is the markdown output"


def create_app() -> gr.Blocks:
    with gr.Blocks(title="Bible XRef") as app:
        gr.Markdown("# Bible Verse Lookup")

        verse_input = gr.Textbox(
            label="Bible Verse",
            placeholder="e.g. John 3:16",
            lines=1,
        )
        submit_btn = gr.Button("Submit", variant="primary")
        verse_output = gr.Textbox(
            label="Verse Text",
            lines=10,
            interactive=False,
        )
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
