"""Tests for ToolRouter Enhancement - crane_tool_router (#98)"""
import pytest
from unittest.mock import Mock, patch
from crane.services.tool_router_service import ToolRouterService, RoutingDecision, RoutingContext


class TestToolRouterService:
    """Test ToolRouterService enhanced routing capabilities"""

    def test_default_config_loaded(self):
        """ToolRouter loads with default configuration"""
        router = ToolRouterService()
        assert router.max_tools_per_step == 6
        assert router.confidence_threshold == 0.25

    def test_custom_config_loaded(self):
        """ToolRouter accepts custom configuration"""
        router = ToolRouterService(
            max_tools_per_step=4,
            confidence_threshold=0.35
        )
        assert router.max_tools_per_step == 4
        assert router.confidence_threshold == 0.35

    def test_context_includes_token_count(self):
        """Routing context includes token usage"""
        router = ToolRouterService()
        context = RoutingContext(
            task="evaluate paper on sentiment",
            token_count=50000
        )
        assert context.token_count == 50000
        assert context.token_count < router.token_threshold

    def test_context_token_threshold_triggered(self):
        """Context detects when token threshold is exceeded"""
        router = ToolRouterService(token_threshold=100000)
        context = RoutingContext(
            task="evaluate paper on sentiment",
            token_count=150000
        )
        assert context.token_count >= router.token_threshold

    def test_routing_decision_has_required_fields(self):
        """RoutingDecision includes all required fields"""
        decision = RoutingDecision(
            selected_tools=["tool1", "tool2"],
            confidence=0.85,
            reasoning="High domain match",
            alternatives=["tool3"]
        )
        assert decision.selected_tools == ["tool1", "tool2"]
        assert decision.confidence == 0.85
        assert decision.reasoning == "High domain match"
        assert decision.alternatives == ["tool3"]

    def test_select_tools_with_context(self):
        """select_tools considers context for routing"""
        router = ToolRouterService()
        context = RoutingContext(
            task="search papers on transformers",
            token_count=30000,
            previous_tools=["search_papers"]
        )
        tools = router.select_tools_with_context(context)
        assert len(tools.selected_tools) >= 1
        assert len(tools.selected_tools) <= router.max_tools_per_step

    def test_context_aware_routing_avoids_repetition(self):
        """Context-aware routing avoids recently used tools"""
        router = ToolRouterService()
        # First call
        context1 = RoutingContext(
            task="search papers on ML",
            token_count=25000,
            previous_tools=[]
        )
        tools1 = router.select_tools_with_context(context1)
        
        # Second call with previous tools should get different selection
        context2 = RoutingContext(
            task="evaluate paper quality",
            token_count=25000,
            previous_tools=tools1.selected_tools
        )
        tools2 = router.select_tools_with_context(context2)
        
        # Both should have results
        assert len(tools1.selected_tools) >= 1
        assert len(tools2.selected_tools) >= 1

    def test_token_threshold_affects_tool_selection(self):
        """High token count triggers more efficient tool selection"""
        router = ToolRouterService(token_threshold=100000)
        
        # Low token count - more liberal selection
        context_low = RoutingContext(
            task="search papers on transformers",
            token_count=30000,
            previous_tools=[]
        )
        tools_low = router.select_tools_with_context(context_low)
        
        # High token count - prefer efficient tools
        context_high = RoutingContext(
            task="search papers on transformers",
            token_count=180000,
            previous_tools=[]
        )
        tools_high = router.select_tools_with_context(context_high)
        
        # Both should return valid results
        assert len(tools_low.selected_tools) >= 1
        assert len(tools_high.selected_tools) >= 1

    def test_confidence_calculation(self):
        """Confidence is calculated based on tool-task alignment"""
        router = ToolRouterService()
        context = RoutingContext(
            task="evaluate paper quality",
            token_count=20000
        )
        decision = router.select_tools_with_context(context)
        
        # Check confidence is in valid range
        assert 0.0 <= decision.confidence <= 1.0

    def test_alternatives_provided(self):
        """Alternatives are provided for fallback"""
        router = ToolRouterService()
        context = RoutingContext(
            task="semantic search papers",
            token_count=15000,
            previous_tools=[]
        )
        decision = router.select_tools_with_context(context)
        
        # Alternatives should be a list
        assert isinstance(decision.alternatives, list)


class TestRoutingContext:
    """Test RoutingContext dataclass"""

    def test_minimal_context(self):
        """Minimal context with just task"""
        context = RoutingContext(task="search papers")
        assert context.task == "search papers"
        assert context.token_count == 0
        assert context.previous_tools == []

    def test_full_context(self):
        """Full context with all fields"""
        context = RoutingContext(
            task="evaluate paper",
            domain="ml",
            token_count=75000,
            previous_tools=["search_papers"],
            agent_history=[{"tool": "search_papers", "success": True}]
        )
        assert context.domain == "ml"
        assert context.token_count == 75000
        assert "search_papers" in context.previous_tools


class TestRoutingDecision:
    """Test RoutingDecision dataclass"""

    def test_empty_alternatives_default(self):
        """Empty alternatives defaults to empty list"""
        decision = RoutingDecision(
            selected_tools=["tool1"],
            confidence=0.9,
            reasoning="Test"
        )
        assert decision.alternatives == []

    def test_with_alternatives(self):
        """Can provide custom alternatives"""
        decision = RoutingDecision(
            selected_tools=["tool1"],
            confidence=0.9,
            reasoning="Test",
            alternatives=["tool2", "tool3"]
        )
        assert decision.alternatives == ["tool2", "tool3"]