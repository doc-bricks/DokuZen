import os
from pathlib import Path

import fitz
import pytest

from core.pdf import collection

def create_pdf(path, text='Original'):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), text)
        doc.save(path)

@pytest.mark.parametrize('kind', ['pdf', 'text', 'hardlink', 'late-hardlink'])
def test_collection_preserves_all_originals(tmp_path, monkeypatch, kind):
    source = tmp_path / ('original.txt' if kind == 'text' else 'original.pdf')
    if kind == 'text':
        source.write_text('Bücher und Originaltexte.', encoding='utf-8')
    else:
        create_pdf(source)
    original = source.read_bytes()
    target = source if kind in ('pdf', 'text') else tmp_path / 'alias.pdf'
    if kind == 'hardlink':
        os.link(source, target)
    if kind == 'late-hardlink':
        real_save = fitz.Document.save
        def save(doc, path, *args, **kwargs):
            real_save(doc, path, *args, **kwargs)
            if not target.exists():
                os.link(source, target)
        monkeypatch.setattr(fitz.Document, 'save', save)
    result = collection.export_collection_pdf([source], target)
    assert not result.success
    assert result.error
    assert source.read_bytes() == original
    assert target.read_bytes() == original
    assert set(tmp_path.iterdir()) == ({source} if target == source else {source, target})

@pytest.mark.parametrize('stage', ['partial', 'empty', 'truncated', 'image', 'publish'])
@pytest.mark.parametrize('existing', [False, True])
def test_failed_collection_preserves_previous_output(tmp_path, monkeypatch, stage, existing):
    source = tmp_path / 'source.pdf'
    target = tmp_path / 'report.pdf'
    create_pdf(source)
    source_bytes = source.read_bytes()
    old = b'Previous output bytes'
    if existing:
        target.write_bytes(old)
    real_save = fitz.Document.save
    def save(doc, path, *args, **kwargs):
        if stage == 'publish':
            return real_save(doc, path, *args, **kwargs)
        if stage == 'image':
            from PIL import Image
            Image.new('RGB', (10, 10), 'white').save(path, format='PNG')
            return
        Path(path).write_bytes(b'' if stage == 'empty' else b'%PDF-incomplete')
        if stage == 'partial':
            raise OSError('Interrupted output write')
    monkeypatch.setattr(fitz.Document, 'save', save)
    if stage == 'publish':
        def fail_replace(*args):
            raise PermissionError('Output locked')
        monkeypatch.setattr(os, 'replace', fail_replace)
    result = collection.export_collection_pdf([source], target)
    assert not result.success
    assert result.error
    assert source.read_bytes() == source_bytes
    assert target.read_bytes() == old if existing else not target.exists()
    assert set(tmp_path.iterdir()) == ({source, target} if existing else {source})

def test_regular_collection_replaces_pdf_and_keeps_bookmarks(tmp_path):
    source = tmp_path / 'chapter.pdf'
    target = tmp_path / 'report.pdf'
    create_pdf(source)
    create_pdf(target, 'Previous report')
    source_bytes = source.read_bytes()
    result = collection.export_collection_pdf([source], target)
    assert result.success and result.total_pages == 1 and result.document_count == 1
    assert source.read_bytes() == source_bytes
    with fitz.open(target) as doc:
        assert len(doc) == 1
        assert 'Original' in doc[0].get_text()
        assert doc.get_toc() == [[1, 'chapter', 1]]
    assert set(tmp_path.iterdir()) == {source, target}


def test_invalid_output_parent_returns_failure(tmp_path):
    source = tmp_path / 'source.pdf'
    create_pdf(source)
    blocked_parent = tmp_path / 'file'
    blocked_parent.write_bytes(b'Keep this file')
    result = collection.export_collection_pdf([source], blocked_parent / 'report.pdf')
    assert not result.success and result.error
    assert blocked_parent.read_bytes() == b'Keep this file'


def test_empty_collection_document_is_closed(tmp_path, monkeypatch):
    source = tmp_path / 'unsupported.xyz'
    source.write_bytes(b'Unsupported')
    real_open = fitz.open
    opened = []

    def track_open(*args, **kwargs):
        doc = real_open(*args, **kwargs)
        opened.append(doc)
        return doc

    monkeypatch.setattr(fitz, 'open', track_open)
    result = collection.export_collection_pdf([source], tmp_path / 'report.pdf')
    assert not result.success
    assert len(opened) == 1 and opened[0].is_closed


def test_cleanup_failure_after_publication_reports_success(tmp_path, monkeypatch):
    source = tmp_path / 'source.pdf'
    target = tmp_path / 'report.pdf'
    create_pdf(source)
    real_directory = collection.tempfile.TemporaryDirectory

    class CleanupFailure:
        def __init__(self, *args, **kwargs):
            self.directory = real_directory(*args, **kwargs)

        def __enter__(self):
            return self.directory.__enter__()

        def __exit__(self, *args):
            self.directory.__exit__(*args)
            raise PermissionError('Cleanup failed after publication')

    monkeypatch.setattr(collection.tempfile, 'TemporaryDirectory', CleanupFailure)
    result = collection.export_collection_pdf([source], target)
    assert result.success and result.total_pages == 1
    with fitz.open(target) as doc:
        assert 'Original' in doc[0].get_text()
    assert set(tmp_path.iterdir()) == {source, target}


def test_identity_check_permission_failure_preserves_output(tmp_path, monkeypatch):
    source = tmp_path / 'source.pdf'
    target = tmp_path / 'report.pdf'
    create_pdf(source)
    target.write_bytes(b'Previous output')

    def denied(*args):
        raise PermissionError('Cannot establish file identity')

    monkeypatch.setattr(Path, 'samefile', denied)
    result = collection.export_collection_pdf([source], target)
    assert not result.success and result.error
    assert target.read_bytes() == b'Previous output'
    assert set(tmp_path.iterdir()) == {source, target}
