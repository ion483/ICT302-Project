"""
@file analysis_pipeline.py
@brief Coordinates CopyQ's local DOCX analysis workflow.
"""

from pathlib import Path
from typing import Any

from core.data_contract import create_parsed_document
from core.doc_handler import handle_upload
from core.docx_unzipper import DocxUnzipper
from core.integrity import verify_working_copy
from core.metrics_calculator import MetricsCalculator
from core.verification_log import Event, VerificationLog
from core.xml_parser import XMLParser


class AnalysisPipeline:
    """
    @brief Runs one local forensic analysis without modifying the original file.
    """

    def __init__(
        self,
        workspace_dir: str | Path = "storage/temp_workspace",
        log: VerificationLog | None = None,
    ):
        """
        @brief Create the pipeline and its local verification log.

        @param workspace_dir Directory used only for verified working copies.
        @param log Optional existing verification log.
        """
        self.workspace_dir = Path(workspace_dir)
        self.log = log or VerificationLog(
            self.workspace_dir / "verification_log.jsonl"
        )

    def analyse(self, source_path: str | Path, top_n: int = 5) -> dict[str, Any]:
        """
        @brief Analyse a DOCX file and return descriptive findings.

        The method validates and copies the source first, then verifies that the
        working copy has not changed before and after OOXML analysis.
        """
        if not isinstance(top_n, int) or top_n < 1:
            raise ValueError("top_n must be a positive integer")

        uploaded, message, upload_details = handle_upload(
            source_path,
            self.workspace_dir,
            self.log,
        )

        if not uploaded:
            return {
                "ok": False,
                "message": message,
                "validation": upload_details,
            }

        working_path = Path(upload_details["working_path"])
        expected_hash = upload_details["sha256"]

        # Check the copy before reading its OOXML contents.
        if not verify_working_copy(working_path, expected_hash):
            self.log.write(
                Event.REVERIFY_MISMATCH,
                file_name=working_path.name,
                sha256=expected_hash,
            )
            return {
                "ok": False,
                "message": "Working copy changed before analysis began.",
                "validation": upload_details,
            }

        self.log.write(
            Event.REVERIFY_MATCH,
            file_name=working_path.name,
            sha256=expected_hash,
        )
        self.log.write(
            Event.ANALYSIS_STARTED,
            file_name=working_path.name,
            sha256=expected_hash,
        )

        try:
            xml_buffers = DocxUnzipper(working_path).extract_xml_buffers()
            parser = XMLParser(xml_buffers)

            paragraphs = parser.parse_document_structure()
            metadata = parser.extract_core_metadata()
            rsid_root = parser.extract_rsid_root()
            rsid_table = self._collect_rsids(paragraphs)

            parsed_document = create_parsed_document(
                document_id=expected_hash,
                paragraphs=paragraphs,
                metadata=metadata,
                rsid_root=rsid_root,
                rsid_table=rsid_table,
            )

            calculator = MetricsCalculator(paragraphs, metadata)
            metrics = calculator.compute_macro_metrics()
            top_sessions = calculator.generate_top_n_rankings(top_n)

        except Exception as error:
            self.log.write(
                Event.ANALYSIS_DONE,
                file_name=working_path.name,
                sha256=expected_hash,
                details={"status": "failed", "error": str(error)},
            )
            return {
                "ok": False,
                "message": f"Analysis failed: {error}",
                "validation": upload_details,
            }

        # Re-check the file after parsing to preserve the evidence trail.
        still_verified = verify_working_copy(working_path, expected_hash)
        self.log.write(
            Event.REVERIFY_MATCH if still_verified else Event.REVERIFY_MISMATCH,
            file_name=working_path.name,
            sha256=expected_hash,
        )

        if not still_verified:
            return {
                "ok": False,
                "message": "Working copy changed during analysis.",
                "validation": upload_details,
            }

        self.log.write(
            Event.ANALYSIS_DONE,
            file_name=working_path.name,
            sha256=expected_hash,
            details={"status": "complete"},
        )

        return {
            "ok": True,
            "message": "Analysis complete.",
            "document": parsed_document,
            "metrics": metrics,
            "top_sessions": top_sessions,
            "integrity": {
                "original_sha256": expected_hash,
                "working_copy_verified": True,
            },
        }

    @staticmethod
    def _collect_rsids(paragraphs: list[dict]) -> list[str]:
        """
        @brief Return a sorted list of RSIDs found in parsed paragraphs and runs.
        """
        rsids = set()

        for paragraph in paragraphs:
            for key in ("paragraph_rsidR", "paragraph_rsidDefault"):
                value = paragraph.get(key)
                if value:
                    rsids.add(value)

            for run in paragraph.get("runs", []):
                value = run.get("rsidR")
                if value:
                    rsids.add(value)

        return sorted(rsids)
