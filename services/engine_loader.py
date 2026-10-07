"""
Engine Loader Utility for HedgeDoc.
Safely loads each independent Document AI engine into its own isolated Python package namespace
to prevent collision between their internal `src/` modules.
"""

from pathlib import Path
import importlib.util
import sys
from typing import Any

from HedgeDoc.configs.app_config import WORKSPACE_ROOT


def _load_package(pkg_name: str, src_dir: Path):
    if pkg_name in sys.modules:
        return sys.modules[pkg_name]

    init_file = src_dir / "__init__.py"
    if not init_file.exists():
        init_file.touch()

    spec = importlib.util.spec_from_file_location(
        pkg_name,
        str(init_file),
        submodule_search_locations=[str(src_dir)]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    return mod


def get_quality_gate_pipeline() -> Any:
    """Returns an instance of DocumentQualityPipeline from document-quality-gate."""
    pkg_dir = WORKSPACE_ROOT / "document-quality-gate" / "src"
    _load_package("doc_qg_pkg", pkg_dir)
    import doc_qg_pkg.pipeline.quality_pipeline as qg_p
    return qg_p.DocumentQualityPipeline()


def get_ocr_pipeline(enable_vlm: bool = False) -> Any:
    """Returns an instance of DocumentOCRPipeline from document-ocr-engine."""
    pkg_dir = WORKSPACE_ROOT / "document-ocr-engine" / "src"
    _load_package("doc_ocr_pkg", pkg_dir)
    import doc_ocr_pkg.pipeline.ocr_pipeline as ocr_p
    return ocr_p.DocumentOCRPipeline(enable_vlm=enable_vlm)


from HedgeDoc.configs.app_config import config


def get_rag_pipeline() -> Any:
    """Returns an instance of DocumentRAGPipeline from document-rag-engine."""
    pkg_dir = WORKSPACE_ROOT / "document-rag-engine" / "src"
    _load_package("doc_rag_pkg", pkg_dir)
    import doc_rag_pkg.pipeline.rag_pipeline as rag_p
    rag_dir = WORKSPACE_ROOT / "document-rag-engine"
    return rag_p.DocumentRAGPipeline.from_configs(
        embedding_config_path=rag_dir / "configs" / "embedding.yaml",
        retrieval_config_path=rag_dir / "configs" / "retrieval.yaml",
        llm_config_path=rag_dir / "configs" / "llm.yaml",
        vector_store_dir=config.CHROMA_DIR
    )
