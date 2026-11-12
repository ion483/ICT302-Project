"""Connect desktop analysis results to local sessions and PDF reports."""
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from core.report_generator import generate_pdf_report
from core.integrity import sha256_file
from core.paths import storage_root
from core.session_manager import (
    SessionError, create_session, default_session_directory, load_session, save_session,
)


class AnalysisStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else default_session_directory()

    def _path(self, session_id):
        # Only opaque IDs returned by this service may select stored files.
        return self.directory / f'{UUID(str(session_id)).hex}.json'

    def save(self, filename, result):
        session_id = uuid4().hex
        previous = None
        for entry in self.list():
            _, saved_result = self.open(entry['id'])
            if saved_result.get('sha256') == result['sha256']:
                session_id = entry['id']
                previous = load_session(self._path(session_id))
                break
        session = create_session(session_id, {'filename': filename, 'result': result})
        if previous is not None:
            session['created_at'] = previous['created_at']
        session['analysis_status'] = 'complete'
        save_session(session, self._path(session_id))
        return session_id

    def open(self, session_id):
        session = load_session(self._path(session_id))
        analysis = session['analysis']
        result = analysis.get('result')
        if session['analysis_status'] != 'complete' or not isinstance(result, dict) or not result.get('success'):
            raise ValueError('This session does not contain a completed document analysis.')
        return analysis['filename'], result

    def list(self):
        # Keep the newest saved analysis for each content hash. Older duplicate
        # files remain on disk, but do not produce duplicate history entries.
        entries = {}
        for path in self.directory.glob('*.json'):
            try:
                filename, result = self.open(path.stem)
                session = load_session(path)
                content_hash = result.get('sha256')
                if not isinstance(content_hash, str) or not content_hash:
                    continue
                entry = {'id': path.stem, 'name': filename, 'updated_at': session['updated_at']}
                if content_hash not in entries or entry['updated_at'] > entries[content_hash]['updated_at']:
                    entries[content_hash] = entry
            except (SessionError, ValueError, KeyError, TypeError):
                continue
        return sorted(entries.values(), key=lambda entry: entry['updated_at'], reverse=True)

    def export(self, session_id, destination):
        _, result = self.open(session_id)
        # The report generator expects the pipeline schema rather than the UI schema.
        return generate_pdf_report({
            'ok': True,
            'document': {'document_id': session_id, 'metadata': result['metadata'],
                         'rsid_root': result['rsid_root']},
            'metrics': result['metrics'],
            'integrity': {'original_sha256': result['sha256'],
                          'working_copy_verified': result['integrity_verified']},
            'top_sessions': result['top_sessions'],
            'paragraphs': result.get('paragraphs', []),
            'session_sequence': result.get('session_sequence', []),
            'analysis_notices': result.get('analysis_notices', []),
        }, destination)

    def delete(self, session_id):
        """Delete the saved session and temporary runs with matching content."""
        path = self._path(session_id)
        if not path.is_file():
            return False

        _, result = self.open(session_id)
        target_hash = result.get('sha256')
        temp_dir = storage_root() / 'temp_workspace'
        if target_hash and temp_dir.is_dir():
            for run in temp_dir.iterdir():
                if not run.is_dir() or run.is_symlink() or run.is_junction():
                    continue
                # Resolve each candidate before reading or removing anything.
                if run.resolve().parent != temp_dir.resolve():
                    continue
                matched = False
                for candidate in run.rglob('*'):
                    if (candidate.is_file() and not candidate.is_symlink()
                            and candidate.resolve().is_relative_to(run.resolve())):
                        if sha256_file(candidate) == target_hash:
                            matched = True
                            break
                if matched:
                    shutil.rmtree(run)

        # Keep the session available for retry if cleanup raises an error.
        path.unlink()
        return True
