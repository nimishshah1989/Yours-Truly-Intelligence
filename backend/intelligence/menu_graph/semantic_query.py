"""Semantic Query Interface — ALL agents use this instead of raw PetPooja tables.

Provides: get_active_items(), get_item_by_name(fuzzy), get_variants_of(concept),
get_modifiers_of(item), get_item_margin(item_id).
"""

import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from intelligence.models import MenuGraphNode

logger = logging.getLogger("ytip.menu_graph.query")


class MenuGraphQuery:
    """Agent-facing interface to the semantic menu graph."""

    def __init__(self, restaurant_id: int, db: Session):
        self.restaurant_id = restaurant_id
        self.db = db

    def get_active_items(self) -> list[MenuGraphNode]:
        """Return all active, non-ghost nodes for this restaurant.

        Agents should use this as their primary menu view.
        Ghosts are excluded — they are POS artefacts.
        """
        return (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                MenuGraphNode.is_active.is_(True),
                MenuGraphNode.node_type != "ghost",
            )
            .all()
        )

    def get_item_by_name(self, name: str) -> Optional[MenuGraphNode]:
        """Fuzzy lookup by name. Tries exact → case-insensitive → partial match.

        Returns the best single match or None.
        """
        name_stripped = name.strip()

        # 1. Exact match on display_name
        exact = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                MenuGraphNode.display_name == name_stripped,
                MenuGraphNode.is_active.is_(True),
            )
            .first()
        )
        if exact:
            return exact

        # 2. Case-insensitive match on display_name
        ci_match = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                func.lower(MenuGraphNode.display_name) == name_stripped.lower(),
                MenuGraphNode.is_active.is_(True),
            )
            .first()
        )
        if ci_match:
            return ci_match

        # 3. Case-insensitive match on concept_name
        concept_match = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                func.lower(MenuGraphNode.concept_name) == name_stripped.lower(),
                MenuGraphNode.is_active.is_(True),
            )
            .first()
        )
        if concept_match:
            return concept_match

        # 4. Partial match — name contained in display_name or concept_name
        partial = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                MenuGraphNode.is_active.is_(True),
                (
                    func.lower(MenuGraphNode.display_name).contains(name_stripped.lower())
                    | func.lower(MenuGraphNode.concept_name).contains(name_stripped.lower())
                ),
            )
            .first()
        )
        return partial

    def get_variants_of(self, concept_name: str) -> list[MenuGraphNode]:
        """Return all variants of a concept.

        Looks up the concept node first, then returns its children.
        If the concept_name matches a standalone item, returns empty.
        """
        concept_name_lower = concept_name.strip().lower()

        # Find the concept node
        concept = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                func.lower(MenuGraphNode.concept_name) == concept_name_lower,
                MenuGraphNode.node_type == "concept",
            )
            .first()
        )
        if not concept:
            return []

        # Return all variant children
        return (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                MenuGraphNode.parent_node_id == concept.id,
                MenuGraphNode.node_type == "variant",
                MenuGraphNode.is_active.is_(True),
            )
            .all()
        )

    def get_modifiers_of(self, item_name: str) -> list[MenuGraphNode]:
        """Return all modifiers associated with a menu item.

        Finds the item (or its concept), then returns modifier children.
        """
        item_name_lower = item_name.strip().lower()

        # Find the item or its parent concept
        item = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                func.lower(MenuGraphNode.display_name) == item_name_lower,
                MenuGraphNode.is_active.is_(True),
            )
            .first()
        )
        if not item:
            return []

        # If item is a variant, look for modifiers on its concept parent
        target_ids = [item.id]
        if item.parent_node_id:
            target_ids.append(item.parent_node_id)

        # Also include concept nodes that match the item's concept_name
        concept = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                func.lower(MenuGraphNode.concept_name) == item.concept_name.lower(),
                MenuGraphNode.node_type == "concept",
            )
            .first()
        )
        if concept:
            target_ids.append(concept.id)

        # Also look for standalone nodes with same name
        standalone = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                func.lower(MenuGraphNode.display_name) == item_name_lower,
                MenuGraphNode.node_type == "standalone",
            )
            .first()
        )
        if standalone:
            target_ids.append(standalone.id)

        return (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                MenuGraphNode.parent_node_id.in_(target_ids),
                MenuGraphNode.node_type == "modifier",
                MenuGraphNode.is_active.is_(True),
            )
            .all()
        )

    def get_item_margin(self, node_id: int) -> Optional[dict]:
        """Return margin data for a menu graph node.

        Returns dict with price_paisa, cost_price_paisa (if available),
        and margin_pct. Returns None if node not found.
        """
        node = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.id == node_id,
                MenuGraphNode.restaurant_id == self.restaurant_id,
            )
            .first()
        )
        if not node:
            return None

        # Try to get cost data from menu_items table
        cost_price_paisa = None
        try:
            from core.models import MenuItem

            menu_item = (
                self.db.query(MenuItem)
                .filter(
                    MenuItem.restaurant_id == self.restaurant_id,
                    MenuItem.petpooja_item_id == node.petpooja_item_id,
                )
                .first()
            )
            if menu_item:
                cost_price_paisa = menu_item.cost_price
        except Exception:
            pass

        result = {
            "node_id": node.id,
            "concept_name": node.concept_name,
            "display_name": node.display_name,
            "price_paisa": node.price_paisa,
            "cost_price_paisa": cost_price_paisa,
            "margin_pct": None,
        }

        if node.price_paisa and cost_price_paisa and node.price_paisa > 0:
            margin = (node.price_paisa - cost_price_paisa) / node.price_paisa * 100
            result["margin_pct"] = round(margin, 2)

        return result
