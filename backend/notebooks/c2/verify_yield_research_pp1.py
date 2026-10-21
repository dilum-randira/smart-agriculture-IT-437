"""Execute the trusted local PP1 notebook without installing Jupyter packages.

Run with backend/.venv/Scripts/python.exe. This is a sequential Python-cell
execution check, not a Jupyter kernel or a substitute for nbformat validation.
Only the notebook output is written; no training entry point is called.
"""
from pathlib import Path
import ast
import base64
import contextlib
import io
import json
import os
import sys

os.environ.setdefault("MPLBACKEND", "Agg")
sys.dont_write_bytecode = True
NOTEBOOK = Path(__file__).with_name("yield_research_pp1.ipynb")


def main():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4 and notebook["nbformat_minor"] == 5
    ids = [cell["id"] for cell in notebook["cells"]]
    assert len(ids) == len(set(ids))
    namespace = {"__name__": "__pp1_notebook__"}
    count = 0
    for index, cell in enumerate(notebook["cells"]):
        assert cell["cell_type"] in {"code", "markdown"}
        assert isinstance(cell["source"], list)
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        ast.parse(source)
        outputs = []

        def publish(value):
            from matplotlib.figure import Figure
            import pandas as pd
            if isinstance(value, Figure):
                buffer = io.BytesIO()
                value.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
                data = {"image/png": base64.b64encode(buffer.getvalue()).decode("ascii"),
                        "text/plain": "<Matplotlib figure>"}
            elif isinstance(value, pd.DataFrame):
                data = {"text/html": value.to_html(), "text/plain": value.to_string()}
            else:
                data = {"text/plain": str(value)}
            outputs.append({"output_type": "display_data", "data": data, "metadata": {}})

        namespace["__pp1_display__"] = publish
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            exec(compile(source, f"{NOTEBOOK.name}:cell-{index + 1}", "exec"), namespace)
        if captured.getvalue():
            outputs.append({"output_type": "stream", "name": "stdout",
                            "text": captured.getvalue().splitlines(keepends=True)})
        count += 1
        cell["execution_count"] = count
        cell["outputs"] = outputs
        print(f"PASS code cell {count} (notebook cell {index + 1})")
    # Do not leave a partially executed notebook if any assertion/cell fails.
    NOTEBOOK.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Executed {count} code cells; saved local outputs to {NOTEBOOK}")


if __name__ == "__main__":
    main()
