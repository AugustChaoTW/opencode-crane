# pyright: reportMissingImports=false
"""
Shared service layer for CRANE tools.
Extracts business logic from MCP tool registrations for reuse across
tools and pipelines.
"""

from crane.services.journal_recommender import JournalRecommender
from crane.services.paper_service import PaperService
from crane.services.reference_service import ReferenceService
from crane.services.semantic_search_service import SemanticSearchService
from crane.services.task_service import TaskService

try:
    from crane.services.figure_generator import FigureGenerator
except ModuleNotFoundError:
    FigureGenerator = None

if FigureGenerator is None:
    __all__ = [
        "PaperService",
        "JournalRecommender",
        "ReferenceService",
        "SemanticSearchService",
        "TaskService",
    ]
else:
    __all__ = [
        "PaperService",
        "FigureGenerator",
        "JournalRecommender",
        "ReferenceService",
        "SemanticSearchService",
        "TaskService",
    ]
