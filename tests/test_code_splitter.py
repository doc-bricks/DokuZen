#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für plugins/special_text/code_splitter.py."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.special_text.code_splitter import (
    CodeElementType,
    CodeSplitter,
    analyze_python_file,
    split_python_file,
)

SAMPLE_SOURCE = """#!/usr/bin/env python3
\"\"\"Beispielmodul.\"\"\"

import os
import json
from pathlib import Path

MAX_ITEMS = 42


def cache_dec(fn):
    return fn


@cache_dec
def helper_fn(x: int) -> int:
    \"\"\"Hilfsfunktion.\"\"\"
    return x + 1


async def async_worker() -> str:
    return "ok"


class DataBox:
    \"\"\"Container-Klasse.\"\"\"

    def get_value(self) -> int:
        return MAX_ITEMS
"""


def test_analyze_source_extracts_elements_imports_and_stats():
    splitter = CodeSplitter()
    analysis = splitter.analyze_source(SAMPLE_SOURCE, "sample_mod.py")
    assert analysis is not None
    assert analysis.filepath == "sample_mod.py"
    assert "os" in analysis.imports
    assert "json" in analysis.imports
    assert "pathlib.Path" in analysis.imports

    class_names = [c.name for c in analysis.classes]
    func_names = [f.name for f in analysis.functions]
    const_names = [
        e.name for e in analysis.elements if e.element_type == CodeElementType.CONSTANT
    ]

    assert class_names == ["DataBox"]
    assert func_names == ["cache_dec", "helper_fn", "async_worker"]
    assert const_names == ["MAX_ITEMS"]

    helper = next(f for f in analysis.functions if f.name == "helper_fn")
    assert helper.decorators == ["cache_dec"]
    assert helper.docstring == "Hilfsfunktion."
    assert helper.line_count >= 4

    assert analysis.total_lines == len(SAMPLE_SOURCE.split("\n"))
    assert analysis.comment_lines >= 1
    assert analysis.blank_lines >= 1
    assert analysis.code_lines > 0

    summary = splitter.generate_summary(analysis)
    assert "CODE-ANALYSE: sample_mod.py" in summary
    assert "DataBox" in summary
    assert "helper_fn()" in summary


def test_analyze_source_returns_none_on_syntax_error():
    splitter = CodeSplitter()
    assert splitter.analyze_source("def kaputt(:\n    pass\n", "bad.py") is None


def test_analyze_file_handles_missing_non_py_and_latin1(tmp_path: Path):
    splitter = CodeSplitter()

    assert splitter.analyze_file(str(tmp_path / "missing.py")) is None

    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("x = 1\n", encoding="utf-8")
    assert splitter.analyze_file(str(txt_file)) is None

    latin_py = tmp_path / "umlaut.py"
    latin_py.write_bytes('# -*- coding: latin-1 -*-\nTEXT = "Größe"\n'.encode("latin-1"))
    analysis = analyze_python_file(str(latin_py))
    assert analysis is not None
    assert any(e.name == "TEXT" for e in analysis.elements)


def test_split_to_files_writes_class_and_function_modules(tmp_path: Path):
    src_file = tmp_path / "sample_mod.py"
    src_file.write_text(SAMPLE_SOURCE, encoding="utf-8")
    out_dir = tmp_path / "split_out"

    created = split_python_file(str(src_file), str(out_dir))
    created_names = {Path(p).name for p in created}

    assert created_names == {"sample_mod_databox.py", "sample_mod_functions.py"}
    cls_text = (out_dir / "sample_mod_databox.py").read_text(encoding="utf-8")
    fn_text = (out_dir / "sample_mod_functions.py").read_text(encoding="utf-8")

    assert "class DataBox:" in cls_text
    assert "import json" in cls_text
    assert "import os" in cls_text
    assert "def helper_fn" in fn_text
    assert "async def async_worker" in fn_text


def test_split_to_files_class_only_module_skips_empty_functions_file(tmp_path: Path):
    src_file = tmp_path / "only_cls.py"
    src_file.write_text("class Solo:\n    pass\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    created = split_python_file(str(src_file), str(out_dir))
    assert [Path(p).name for p in created] == ["only_cls_solo.py"]
    assert not (out_dir / "only_cls_functions.py").exists()


def test_split_python_file_missing_returns_empty_list(tmp_path: Path):
    assert split_python_file(str(tmp_path / "nope.py"), str(tmp_path / "out")) == []
