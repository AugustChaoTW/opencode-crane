"""
TDD tests for YAML read/write utilities.
RED phase: define expected behavior before implementation.
"""


from crane.utils.yaml_io import (
    delete_paper_yaml,
    list_paper_keys,
    read_paper_yaml,
    write_paper_yaml,
)


class TestWritePaperYaml:
    """Writing paper YAML files."""

    def test_write_creates_file(self, papers_dir, sample_paper_dict):
        path = write_paper_yaml(papers_dir, "test-key", sample_paper_dict)
        assert path.endswith("test-key.yaml")
        from pathlib import Path

        assert Path(path).exists()

    def test_write_content_is_valid_yaml(self, papers_dir, sample_paper_dict):
        write_paper_yaml(papers_dir, "test-key", sample_paper_dict)
        data = read_paper_yaml(papers_dir, "test-key")
        assert data["key"] == "vaswani2017-attention"
        assert data["title"] == "Attention Is All You Need"

    def test_write_creates_parent_dirs(self, tmp_path, sample_paper_dict):
        deep_dir = str(tmp_path / "a" / "b" / "c")
        path = write_paper_yaml(deep_dir, "test-key", sample_paper_dict)
        from pathlib import Path

        assert Path(path).exists()

    def test_write_overwrites_existing(self, papers_dir, sample_paper_dict):
        write_paper_yaml(papers_dir, "k", {"title": "old"})
        write_paper_yaml(papers_dir, "k", {"title": "new"})
        data = read_paper_yaml(papers_dir, "k")
        assert data["title"] == "new"


class TestReadPaperYaml:
    """Reading paper YAML files."""

    def test_read_existing(self, papers_dir, sample_paper_dict):
        write_paper_yaml(papers_dir, "k", sample_paper_dict)
        data = read_paper_yaml(papers_dir, "k")
        assert data is not None
        assert data["key"] == "vaswani2017-attention"

    def test_read_nonexistent_returns_none(self, papers_dir):
        data = read_paper_yaml(papers_dir, "nonexistent")
        assert data is None

    def test_read_preserves_unicode(self, papers_dir):
        write_paper_yaml(papers_dir, "k", {"title": "Transformer"})
        data = read_paper_yaml(papers_dir, "k")
        assert data["title"] == "Transformer"


class TestListPaperKeys:
    """Listing all paper keys in a directory."""

    def test_empty_dir(self, papers_dir):
        keys = list_paper_keys(papers_dir)
        assert keys == []

    def test_lists_keys_sorted(self, papers_dir):
        write_paper_yaml(papers_dir, "bbb", {"x": 1})
        write_paper_yaml(papers_dir, "aaa", {"x": 2})
        write_paper_yaml(papers_dir, "ccc", {"x": 3})
        keys = list_paper_keys(papers_dir)
        assert keys == ["aaa", "bbb", "ccc"]

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        keys = list_paper_keys(str(tmp_path / "nope"))
        assert keys == []

    def test_ignores_non_yaml_files(self, papers_dir):
        write_paper_yaml(papers_dir, "real", {"x": 1})
        from pathlib import Path

        (Path(papers_dir) / "notes.txt").write_text("not yaml")
        keys = list_paper_keys(papers_dir)
        assert keys == ["real"]


class TestDeletePaperYaml:
    """Deleting paper YAML files."""

    def test_delete_existing_returns_true(self, papers_dir):
        write_paper_yaml(papers_dir, "k", {"x": 1})
        assert delete_paper_yaml(papers_dir, "k") is True

    def test_delete_removes_file(self, papers_dir):
        write_paper_yaml(papers_dir, "k", {"x": 1})
        delete_paper_yaml(papers_dir, "k")
        assert read_paper_yaml(papers_dir, "k") is None

    def test_delete_nonexistent_returns_false(self, papers_dir):
        assert delete_paper_yaml(papers_dir, "nope") is False
