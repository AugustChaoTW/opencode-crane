"""
TDD tests for BibTeX read/write utilities.
RED phase: define expected behavior before implementation.
"""

from pathlib import Path

from crane.utils.bibtex import append_entry, read_entries, remove_entry


class TestAppendEntry:
    """Appending BibTeX entries to .bib file."""

    def test_append_to_empty_file(self, bib_path, sample_bibtex):
        append_entry(bib_path, sample_bibtex)
        content = Path(bib_path).read_text()
        assert "vaswani2017-attention" in content

    def test_append_multiple_entries(self, bib_path, sample_bibtex):
        entry2 = """@article{brown2020-gpt3,
  title={Language Models are Few-Shot Learners},
  author={Brown, Tom},
  year={2020}
}"""
        append_entry(bib_path, sample_bibtex)
        append_entry(bib_path, entry2)
        content = Path(bib_path).read_text()
        assert "vaswani2017-attention" in content
        assert "brown2020-gpt3" in content

    def test_append_creates_parent_dirs(self, tmp_path, sample_bibtex):
        deep_path = str(tmp_path / "a" / "b" / "refs.bib")
        append_entry(deep_path, sample_bibtex)
        assert Path(deep_path).exists()


class TestRemoveEntry:
    """Removing BibTeX entries by key."""

    def test_remove_existing_returns_true(self, bib_path, sample_bibtex):
        append_entry(bib_path, sample_bibtex)
        assert remove_entry(bib_path, "vaswani2017-attention") is True

    def test_remove_deletes_entry(self, bib_path, sample_bibtex):
        append_entry(bib_path, sample_bibtex)
        remove_entry(bib_path, "vaswani2017-attention")
        content = Path(bib_path).read_text()
        assert "vaswani2017-attention" not in content

    def test_remove_nonexistent_returns_false(self, bib_path):
        assert remove_entry(bib_path, "nonexistent") is False

    def test_remove_preserves_other_entries(self, bib_path, sample_bibtex):
        entry2 = "@article{other,\n  title={Other},\n  year={2024}\n}"
        append_entry(bib_path, sample_bibtex)
        append_entry(bib_path, entry2)
        remove_entry(bib_path, "vaswani2017-attention")
        content = Path(bib_path).read_text()
        assert "other" in content


class TestReadEntries:
    """Reading all entries from .bib file."""

    def test_read_empty_returns_empty(self, bib_path):
        entries = read_entries(bib_path)
        assert entries == []

    def test_read_single_entry(self, bib_path, sample_bibtex):
        append_entry(bib_path, sample_bibtex)
        entries = read_entries(bib_path)
        assert len(entries) == 1
        assert entries[0]["key"] == "vaswani2017-attention"

    def test_read_entry_has_fields(self, bib_path, sample_bibtex):
        append_entry(bib_path, sample_bibtex)
        entries = read_entries(bib_path)
        entry = entries[0]
        assert "title" in entry
        assert "author" in entry
        assert "year" in entry
