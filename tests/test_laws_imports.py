"""The import graph: what each language's import line resolves to, and the header collapse that makes C
comparable with the call graph at all."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_imports as I  # noqa: E402


def idx(paths):
    return I._suffix_index(paths), I._module_index(paths)


def test_a_c_include_resolves_relative_then_by_unique_basename():
    paths = ["src/parser.c", "src/parser.h", "include/libxml/tree.h", "src/uri.c"]
    suffix, _ = idx(paths)
    assert I.targets('#include "parser.h"', "src/parser.c", "c", suffix, {}, None) == ["src/parser.h"]
    assert I.targets("#include <libxml/tree.h>", "src/parser.c", "c", suffix, {}, None) == ["include/libxml/tree.h"]
    assert I.targets("#include <stdio.h>", "src/parser.c", "c", suffix, {}, None) == []   # a system header
    assert I.targets("int x;", "src/parser.c", "c", suffix, {}, None) == []


def test_a_python_import_resolves_absolute_and_relative_forms():
    paths = ["sphinx/__init__.py", "sphinx/util/osutil.py", "sphinx/util/__init__.py", "sphinx/application.py"]
    suffix, module = idx(paths)
    assert module["sphinx.util.osutil"] == "sphinx/util/osutil.py" and module["sphinx.util"] == "sphinx/util/__init__.py"
    assert I.targets("import sphinx.util.osutil", "x.py", "python", suffix, module, None) == ["sphinx/util/osutil.py"]
    got = I.targets("from sphinx.util import osutil", "x.py", "python", suffix, module, None)
    assert "sphinx/util/osutil.py" in got            # `from a import b` where b is itself a module
    rel = I.targets("from . import osutil", "sphinx/util/application.py", "python", suffix, module, None)
    assert "sphinx/util/__init__.py" in rel or "sphinx/util/osutil.py" in rel
    assert I.targets("import os", "x.py", "python", suffix, module, None) == []   # the standard library


def test_a_java_import_resolves_by_path_and_drops_a_static_member():
    paths = ["src/main/java/org/apache/commons/lang3/StringUtils.java"]
    suffix, _ = idx(paths)
    t = "src/main/java/org/apache/commons/lang3/StringUtils.java"
    assert I.targets("import org.apache.commons.lang3.StringUtils;", "x.java", "java", suffix, {}, None) == [t]
    assert I.targets("import static org.apache.commons.lang3.StringUtils.isEmpty;", "x.java", "java",
                     suffix, {}, None) == [t]
    assert I.targets("import java.util.List;", "x.java", "java", suffix, {}, None) == []


def test_a_go_import_names_a_directory_so_every_file_in_it_is_a_target():
    paths = ["pkg/labels/labels.go", "pkg/labels/matcher.go", "web/api.go"]
    by_dir = {"pkg/labels": ["pkg/labels/labels.go", "pkg/labels/matcher.go"], "web": ["web/api.go"]}
    suffix, _ = idx(paths)
    got = I.targets('\t"github.com/prometheus/prometheus/pkg/labels"', "web/api.go", "go", suffix, {},
                    "github.com/prometheus/prometheus", by_dir)
    assert sorted(got) == ["pkg/labels/labels.go", "pkg/labels/matcher.go"]
    assert I.targets('\t"fmt"', "web/api.go", "go", suffix, {}, "github.com/prometheus/prometheus", by_dir) == []
    assert I.targets('\t"github.com/other/repo/x"', "web/api.go", "go", suffix, {},
                     "github.com/prometheus/prometheus", by_dir) == []


def test_the_header_collapse_maps_includes_onto_implementations():
    paths = ["src/parser.c", "src/parser.h", "src/uri.c", "src/uri.h", "src/only.h"]
    # a.c includes b.h; the call graph instead has a.c -> b.c, so without the collapse they never meet
    raw = {("src/parser.c", "src/uri.h"), ("src/uri.c", "src/parser.h")}
    got = I.collapse_headers(raw, paths)
    assert got == {("src/parser.c", "src/uri.c"), ("src/uri.c", "src/parser.c")}
    assert I.collapse_headers({("src/parser.c", "src/only.h")}, paths) == set()   # a header with no .c is dropped
    assert I.collapse_headers({("src/parser.c", "src/parser.h")}, paths) == set()  # and no self-loop
    assert I.collapse_headers({("src/parser.c", "src/uri.c")}, paths) == {("src/parser.c", "src/uri.c")}


def test_the_in_repo_share_is_a_property_of_the_code_not_the_instrument():
    """Documented so it is not read as coverage: an import of the JDK correctly fails to resolve."""
    src = (Path(__file__).resolve().parent.parent / "tools" / "laws_imports.py").read_text()
    assert "share_in_repo" in src and "NOT of the instrument" in src
    assert "share_resolved" not in src
