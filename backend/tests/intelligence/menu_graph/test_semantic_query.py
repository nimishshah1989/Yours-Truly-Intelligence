"""Tests for semantic_query.py — the agent-facing query interface.

All agents use this instead of querying raw PetPooja tables.
Must support: get_active_items(), get_item_by_name(fuzzy),
get_variants_of(concept), get_modifiers_of(item), get_item_margin(item_id).
"""

import pytest
from sqlalchemy.orm import Session


@pytest.fixture()
def populated_graph(db: Session, restaurant_id: int, sample_menu_items):
    """Build and persist a menu graph so semantic_query can read it."""
    from intelligence.menu_graph.graph_builder import MenuGraphBuilder

    builder = MenuGraphBuilder(restaurant_id, db)
    builder.build()
    builder.persist()
    return restaurant_id


class TestGetActiveItems:
    def test_returns_only_active_items(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        items = query.get_active_items()

        assert len(items) > 0
        for item in items:
            assert item.is_active is True

    def test_excludes_ghost_items(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        items = query.get_active_items()

        item_types = [i.node_type for i in items]
        assert "ghost" not in item_types


class TestGetItemByName:
    def test_exact_match(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        result = query.get_item_by_name("Hot Latte")

        assert result is not None
        assert "Latte" in result.display_name or "Latte" in result.concept_name

    def test_fuzzy_match_case_insensitive(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        result = query.get_item_by_name("hot latte")

        assert result is not None

    def test_fuzzy_match_partial(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        result = query.get_item_by_name("avocado")

        assert result is not None
        assert "Avocado" in result.display_name or "Avocado" in result.concept_name

    def test_returns_none_for_no_match(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        result = query.get_item_by_name("Lobster Thermidor")

        assert result is None


class TestGetVariantsOf:
    def test_returns_variants_for_concept(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        variants = query.get_variants_of("Pour Over")

        assert len(variants) >= 2
        variant_names = [v.display_name for v in variants]
        assert any("Hot" in n for n in variant_names)
        assert any("Iced" in n for n in variant_names)

    def test_returns_empty_for_standalone(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        variants = query.get_variants_of("Avocado Toast")

        assert variants == []


class TestGetModifiersOf:
    def test_returns_modifiers(
        self, db: Session, restaurant_id: int, sample_menu_items,
        sample_orders_with_cooccurrence,
    ):
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        builder = MenuGraphBuilder(restaurant_id, db)
        builder.build()
        builder.persist()

        query = MenuGraphQuery(restaurant_id, db)
        modifiers = query.get_modifiers_of("Hot Latte")

        modifier_names = [m.display_name for m in modifiers]
        assert "Extra Shot" in modifier_names


class TestGetItemMargin:
    def test_returns_margin_data(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)

        # Get any standalone item
        items = query.get_active_items()
        if items:
            margin = query.get_item_margin(items[0].id)
            # margin should be a dict with price info
            assert margin is not None
            assert "price_paisa" in margin

    def test_returns_none_for_missing_item(self, db: Session, populated_graph):
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        query = MenuGraphQuery(populated_graph, db)
        margin = query.get_item_margin(99999)

        assert margin is None
