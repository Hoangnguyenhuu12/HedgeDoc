"""
Client adapter for Document OCR Engine.
Supports direct local Python module execution or remote HTTP REST service.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import requests

from HedgeDoc.configs.app_config import config
from HedgeDoc.services.engine_loader import get_ocr_pipeline


class OCRClient:
    """
    Client for interacting with Document OCR Engine.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or config.OCR_ENGINE_API_URL
        self._local_pipeline = None

    def _get_local_pipeline(self):
        if self._local_pipeline is None:
            self._local_pipeline = get_ocr_pipeline(enable_vlm=False)
        return self._local_pipeline

    def process_document(
        self,
        file_path: Path,
        backend: str = "auto",
        clean_bleed: bool = True
    ) -> Dict[str, Any]:
        """
        Process document through OCR and return standardized OCROutput dictionary.
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # 1. Remote HTTP mode if configured
        if self.api_url:
            try:
                url = f"{self.api_url.rstrip('/')}/ocr/process"
                with open(file_path, "rb") as f:
                    resp = requests.post(
                        url,
                        files={"file": f},
                        data={"backend": backend, "clean_bleed": clean_bleed},
                        timeout=60
                    )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                pass

        # 2. Local direct execution mode
        pipeline = self._get_local_pipeline()
        ocr_output = pipeline.process_document(file_path)
        return ocr_output.model_dump()
