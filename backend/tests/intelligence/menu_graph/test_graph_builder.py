"""Tests for menu graph bootstrap algorithm (graph_builder.py).

Tests cover:
1. Ghost item detection (price=0 or high co-occurrence with parent)
2. Variant clustering (Iced/Hot/Large/Small prefix/suffix patterns)
3. Modifier identification (appears in >75% of orders alongside parent)
4. Confidence scoring 0-100 for each inference
5. Writing results to menu_graph_nodes table
"""

import pytest
from sqlalchemy.orm import Session


class TestGhostDetection:
    """Ghost items: price = 0, or high co-occurrence with parent."""

    def test_detects_zero_price_items_as_ghosts(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        ghost_names = [n.display_name for n in result.nodes if n.node_type == "ghost"]
        assert "Oat Milk Upgrade" in ghost_names

    def test_ghost_has_confidence_score(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        ghosts = [n for n in result.nodes if n.node_type == "ghost"]
        assert len(ghosts) > 0
        for g in ghosts:
            assert 0 <= g.confidence_score <= 100

    def test_ghost_has_inference_basis(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        ghosts = [n for n in result.nodes if n.node_type == "ghost"]
        for g in ghosts:
            assert g.inference_basis is not None
            assert len(g.inference_basis) > 0


class TestVariantClustering:
    """Variant detection: Iced/Hot/Large/Small prefix/suffix patterns."""

    def test_clusters_hot_iced_variants(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        # "Hot Pour Over" and "Iced Pour Over" should share a concept "Pour Over"
        variants = [n for n in result.nodes if n.node_type == "variant"]
        concepts = [n for n in result.nodes if n.node_type == "concept"]

        concept_names = [c.concept_name for c in concepts]
        assert "Pour Over" in concept_names or "pour over" in [c.lower() for c in concept_names]

    def test_clusters_large_small_variants(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        concepts = [n for n in result.nodes if n.node_type == "concept"]
        concept_names_lower = [c.concept_name.lower() for c in concepts]

        # Small Cappuccino + Large Cappuccino → concept "Cappuccino"
        assert "cappuccino" in concept_names_lower

    def test_variants_link_to_parent_concept(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        variants = [n for n in result.nodes if n.node_type == "variant"]
        # Every variant must have a parent_node_id pointing to its concept
        for v in variants:
            assert v.parent_node_id is not None

    def test_variant_confidence_between_0_and_100(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        variants = [n for n in result.nodes if n.node_type == "variant"]
        for v in variants:
            assert 0 <= v.confidence_score <= 100


class TestModifierIdentification:
    """Modifiers: items appearing in >75% of orders alongside a parent."""

    def test_detects_high_cooccurrence_modifier(
        self, db: Session, restaurant_id: int, sample_menu_items,
        sample_orders_with_cooccurrence,
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        modifier_names = [n.display_name for n in result.nodes if n.node_type == "modifier"]
        # Extra Shot appears in 80% of coffee orders → should be modifier
        assert "Extra Shot" in modifier_names

    def test_modifier_has_parent(
        self, db: Session, restaurant_id: int, sample_menu_items,
        sample_orders_with_cooccurrence,
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        modifiers = [n for n in result.nodes if n.node_type == "modifier"]
        for m in modifiers:
            assert m.parent_node_id is not None


class TestStandaloneItems:
    """Items that don't fit ghost/variant/modifier are standalone."""

    def test_standalone_items_detected(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        standalone_names = [
            n.display_name for n in result.nodes if n.node_type == "standalone"
        ]
        # Avocado Toast, Banana Bread, Croissant should be standalone
        assert "Avocado Toast" in standalone_names
        assert "Banana Bread" in standalone_names

    def test_standalone_confidence_is_100(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        standalones = [n for n in result.nodes if n.node_type == "standalone"]
        for s in standalones:
            assert s.confidence_score == 100


class TestPersistence:
    """Results written to menu_graph_nodes table."""

    def test_nodes_persisted_to_db(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder
        from intelligence.models import MenuGraphNode

        builder = MenuGraphBuilder(restaurant_id, db)
        builder.build()
        builder.persist()

        count = db.query(MenuGraphNode).filter_by(restaurant_id=restaurant_id).count()
        assert count > 0

    def test_persisted_nodes_have_correct_restaurant_id(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder
        from intelligence.models import MenuGraphNode

        builder = MenuGraphBuilder(restaurant_id, db)
        builder.build()
        builder.persist()

        nodes = db.query(MenuGraphNode).filter_by(restaurant_id=restaurant_id).all()
        for node in nodes:
            assert node.restaurant_id == restaurant_id


class TestBuildResult:
    """The build() method returns a summary object."""

    def test_build_returns_summary(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        assert hasattr(result, "nodes")
        assert hasattr(result, "concepts_count")
        assert hasattr(result, "variants_count")
        assert hasattr(result, "ghosts_count")

    def test_summary_counts_are_correct(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder

        builder = MenuGraphBuilder(restaurant_id, db)
        result = builder.build()

        actual_concepts = len([n for n in result.nodes if n.node_type == "concept"])
        assert result.concepts_count == actual_concepts

        actual_variants = len([n for n in result.nodes if n.node_type == "variant"])
        assert result.variants_count == actual_variants

        actual_ghosts = len([n for n in result.nodes if n.node_type == "ghost"])
        assert result.ghosts_count == actual_ghosts
