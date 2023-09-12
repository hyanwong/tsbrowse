import pathlib
import time
import traceback

import click
import daiquiri
import panel as pn
import tskit
import tszip

import model
import pages


logger = daiquiri.getLogger("app")


def load_data(path):
    logger.info(f"Loading {path}")
    try:
        ts = tskit.load(path)
    except tskit.FileFormatError:
        ts = tszip.decompress(path)

    tsm = model.TSModel(ts, path.name)
    return tsm


page_map = {
    "Overview": pages.overview,
    "Mutations": pages.mutations,
    "Edges": pages.edges,
    "Edge Explorer": pages.edge_explorer,
    "Trees": pages.trees,
    "Nodes": pages.nodes,
    "Popgen": pages.popgen,
}


def get_app(tsm):
    pn.extension(sizing_mode="stretch_width")
    pn.extension("tabulator")

    def show(page):
        logger.info(f"Showing page {page}")
        yield pn.indicators.LoadingSpinner(value=True, width=50, height=50)
        try:
            before = time.time()
            content = page_map[page](tsm)
            duration = time.time() - before
            logger.info(f"Loaded page {page} in {duration:.2f}s")
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            error_traceback = traceback.format_exc().replace("\n", "<br>")
            error_traceback = f"<pre>{error_traceback}</pre>"
            error_panel = pn.pane.Markdown(
                f"## Error\n\n{error_message}\n\n{error_traceback}",
                style={"color": "red"},
            )
            yield error_panel
            return
        yield content

    starting_page = pn.state.session_args.get("page", [b"Overview"])[0].decode()
    page = pn.widgets.RadioButtonGroup(
        value=starting_page,
        options=list(page_map.keys()),
        name="Page",
        # sizing_mode="fixed",
        button_type="success",
        orientation="vertical",
    )
    ishow = pn.bind(show, page=page)
    pn.state.location.sync(page, {"value": "page"})

    ACCENT_COLOR = "#0072B5"
    DEFAULT_PARAMS = {
        "site": "QC dashboard",
        "accent_base_color": ACCENT_COLOR,
        "header_background": ACCENT_COLOR,
    }

    return pn.template.FastListTemplate(
        title=tsm.name,
        sidebar=[page],
        main=[ishow],
        **DEFAULT_PARAMS,
    )


@click.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--port", default=8080, help="Port to serve on")
def main(path, port):
    """
    Run the tsqc server.
    """
    daiquiri.setup(level="INFO")
    tsm = load_data(pathlib.Path(path))

    # Note: functools.partial doesn't work here
    def app():
        return get_app(tsm)

    pn.serve(app, port=port, location=True, verbose=True)


if __name__ == "__main__":
    main()