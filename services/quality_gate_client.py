"""
Client adapter for Document Quality Gate.
Supports direct local Python module execution or remote HTTP REST service.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import requests

from HedgeDoc.configs.app_config import config
from HedgeDoc.services.engine_loader import get_quality_gate_pipeline


class QualityGateClient:
    """
    Client for interacting with Document Quality Gate.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or config.QUALITY_GATE_API_URL
        self._local_pipeline = None

    def _get_local_pipeline(self):
        if self._local_pipeline is None:
            self._local_pipeline = get_quality_gate_pipeline()
        return self._local_pipeline

    def assess_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Assess document quality and OCR readiness.
        Returns a dictionary representing DocumentQualityAssessment.
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # 1. Remote HTTP mode if configured
        if self.api_url:
            try:
                url = f"{self.api_url.rstrip('/')}/quality/assess"
                with open(file_path, "rb") as f:
                    resp = requests.post(url, files={"file": f}, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except Exception:
                pass

        # 2. Local direct execution mode
        pipeline = self._get_local_pipeline()
        assessment = pipeline.assess_document(file_path)
        return assessment.model_dump()
