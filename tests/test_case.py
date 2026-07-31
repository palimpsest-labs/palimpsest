"""Tests for case directory management and path safety."""

import json
import tempfile
from pathlib import Path

import pytest

from palimpsest.case import (
    _VALID_SLUG_RE,
    create_case,
    get_case_dir,
    get_memory_path,
    list_cases,
)


class TestSlugValidation:
    """Kebab-case slug validation for both create and retrieval paths."""

    @pytest.mark.parametrize("slug", [
        "my-investigation",
        "case123",
        "a-b-c",
        "singleword",
        "test-2024",
    ])
    def test_valid_slugs(self, slug):
        assert _VALID_SLUG_RE.match(slug) is not None

    @pytest.mark.parametrize("slug", [
        "../../../etc",
        "valid-case/../../../etc",
        "UPPERCASE",
        "with spaces",
        "-leading-hyphen",
        "trailing-hyphen-",
        "double--hyphen",
        "./hidden",
        "case.dotted",
        "case with/slash",
    ])
    def test_invalid_slugs_rejected(self, slug):
        # create_case rejects invalid slugs
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(ValueError, match="kebab-case"):
                create_case(slug, base_dir=td)

    @pytest.mark.parametrize("slug", [
        "../../../etc",
        "valid-case/../../../etc",
        "./hidden",
    ])
    def test_get_case_dir_rejects_path_traversal(self, slug):
        """get_case_dir must validate the slug before touching the filesystem."""
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(ValueError, match="kebab-case"):
                get_case_dir(slug, base_dir=td)

    @pytest.mark.parametrize("slug", [
        "../../../etc",
        "valid-case/../../../etc",
    ])
    def test_get_memory_path_rejects_path_traversal(self, slug):
        """get_memory_path must validate the slug before touching the filesystem."""
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(ValueError, match="kebab-case"):
                get_memory_path(slug, base_dir=td)


class TestDefenceInDepth:
    """Resolved-path check catches symlink tricks even with a valid-ish slug."""

    def test_symlink_outside_base_raises(self):
        """A slug that happens to be a symlink outside the base is trapped."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "cases"
            base.mkdir()
            # Create a directory outside the base
            outside = Path(td) / "outside"
            outside.mkdir()

            # Create a symlink inside the base pointing outside
            symlink = base / "innocent"
            symlink.symlink_to(outside)

            # Even though "innocent" is a valid kebab-case slug,
            # the resolved path is outside, so get_case_dir should raise.
            with pytest.raises(ValueError, match="Path traversal"):
                get_case_dir("innocent", base_dir=str(base))


class TestCreateAndList:
    """Case creation and listing."""

    def test_create_case_writes_state_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            case_dir = create_case("test-case", title="Test", base_dir=td)
            assert case_dir.is_dir()
            assert (case_dir / "state.json").is_file()
            assert (case_dir / "captures" / "manifest.jsonl").is_file()

            state = json.loads((case_dir / "state.json").read_text(encoding="utf-8"))
            assert state["slug"] == "test-case"
            assert state["title"] == "Test"
            assert state["phase"] == "scope"

    def test_create_case_duplicate_raises(self):
        with tempfile.TemporaryDirectory() as td:
            create_case("dup", base_dir=td)
            with pytest.raises(ValueError, match="already exists"):
                create_case("dup", base_dir=td)

    def test_list_cases_returns_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            create_case("alpha", title="Alpha", base_dir=td)
            create_case("beta", title="Beta", base_dir=td)

            cases = list_cases(td)
            slugs = {c["slug"] for c in cases}
            assert slugs == {"alpha", "beta"}

            alpha = next(c for c in cases if c["slug"] == "alpha")
            assert alpha["title"] == "Alpha"
            assert alpha["phase"] == "scope"

    def test_list_cases_skips_invalid_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "cases"
            base.mkdir()
            (base / "empty-dir").mkdir()
            cases = list_cases(str(base))
            assert cases == []


class TestMemoryPath:
    """get_memory_path creates file atomically."""

    def test_creates_file_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            create_case("mem-test", base_dir=td)
            mem = get_memory_path("mem-test", base_dir=td)
            assert mem.exists()
            assert mem.name == "memory.jsonl"
            assert mem.read_text(encoding="utf-8") == ""

    def test_empty_file_when_already_exists(self):
        with tempfile.TemporaryDirectory() as td:
            create_case("mem-test2", base_dir=td)
            first = get_memory_path("mem-test2", base_dir=td)
            first.write_text("data", encoding="utf-8")
            second = get_memory_path("mem-test2", base_dir=td)
            assert second.read_text(encoding="utf-8") == "data"
