"""DESIGN-1 UI-session discriminator without importing optional Streamlit runtime.

Execute only the real UI state-reset function from source. A workspace switch
with the same project ID must invalidate the pinned provider/model cache.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace


def test_project_id_is_scoped_to_workspace_for_session_pinning(tmp_path):
    source = Path(__file__).resolve().parents[2] / "apps" / "design_studio.py"
    parsed = ast.parse(source.read_text(encoding="utf-8"))
    function = next(node for node in parsed.body
                    if isinstance(node, ast.FunctionDef) and node.name == "_reset_project")
    mock_st = SimpleNamespace(session_state={})
    namespace = {"st": mock_st, "Path": Path}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
    reset = namespace["_reset_project"]

    reset("client", tmp_path / "workspace-a")
    state = mock_st.session_state
    state.update(snapshot="old site", evaluations={"cached": "old"},
                 comparisons=["old"], snapshot_clock="old",
                 design_control_depth=9.0)
    reset("client", tmp_path / "workspace-a")
    assert state["snapshot"] == "old site"  # identical project: no needless refetch
    reset("client", tmp_path / "workspace-b")
    for stale in ("snapshot", "evaluations", "comparisons", "snapshot_clock",
                  "design_control_depth"):
        assert stale not in state
    assert state["loaded_id"] == (str((tmp_path / "workspace-b").resolve()), "client")
