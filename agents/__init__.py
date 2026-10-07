"""
Multi-Agent Module for HedgeDoc.
Coordinates specialized agents:
- FrontdeskAgent (Receptionist / User Guide)
- ResearchAgent (Document Retrieval & Synthesis Specialist)
- MultiAgentCoordinator (Workflow orchestrator)
"""

from .frontdesk_agent import FrontdeskAgent
from .research_agent import ResearchAgent
from .coordinator import MultiAgentCoordinator

__all__ = ["FrontdeskAgent", "ResearchAgent", "MultiAgentCoordinator"]
