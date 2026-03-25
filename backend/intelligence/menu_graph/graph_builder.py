"""Menu Graph Bootstrap Algorithm.

Reads raw menu_items, detects ghosts, clusters variants, identifies modifiers,
and scores each inference 0-100 for confidence. Writes results to menu_graph_nodes.

Agents never query raw PetPooja tables — they use semantic_query.py which reads
from the graph this module builds.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

logger = logging.getLogger("ytip.menu_graph.builder")

# Variant prefixes/suffixes that indicate the same base concept
VARIANT_PREFIXES = {"hot", "iced", "cold", "large", "small", "regular", "medium", "mini", "xl"}
VARIANT_SUFFIXES = {"hot", "iced", "cold", "large", "small", "regular", "medium", "mini", "xl"}

# Co-occurrence threshold: if an addon appears in >=75% of a parent's orders, it's a modifier
MODIFIER_COOCCURRENCE_THRESHOLD = 0.75


@dataclass
class GraphNode:
    """In-memory representation of a node before persistence."""
    petpooja_item_id: Optional[str]
    node_type: str  # concept / variant / modifier / ghost / standalone
    concept_name: str
    display_name: Optional[str]
    parent_node_id: Optional[int] = None
    price_paisa: Optional[int] = None
    category: Optional[str] = None
    is_active: bool = True
    confidence_score: int = 100
    inference_basis: Optional[str] = None
    owner_validated: bool = False
    # Internal tracking — not persisted directly
    _temp_id: Optional[int] = None
    _parent_concept: Optional[str] = None


@dataclass
class BuildResult:
    """Summary returned by build()."""
    nodes: list = field(default_factory=list)
    concepts_count: int = 0
    variants_count: int = 0
    ghosts_count: int = 0
    modifiers_count: int = 0
    standalone_count: int = 0
    lowest_confidence: list = field(default_factory=list)


class MenuGraphBuilder:
    """Bootstrap the semantic menu graph from raw PetPooja menu_items."""

    def __init__(self, restaurant_id: int, db: Session):
        self.restaurant_id = restaurant_id
        self.db = db
        self._result: Optional[BuildResult] = None
        self._nodes: list[GraphNode] = []

    def build(self) -> BuildResult:
        """Run the full bootstrap pipeline. Returns BuildResult."""
        from core.models import MenuItem

        # 1. Load all menu items for this restaurant
        items = (
            self.db.query(MenuItem)
            .filter_by(restaurant_id=self.restaurant_id)
            .all()
        )

        if not items:
            self._result = BuildResult()
            return self._result

        self._nodes = []

        # 2. Detect ghosts (price = 0)
        ghosts, non_ghosts = self._detect_ghosts(items)

        # 3. Cluster variants (Iced/Hot/Large/Small patterns)
        concepts, variants, remaining = self._cluster_variants(non_ghosts)

        # 4. Detect modifiers via co-occurrence analysis
        # Pass ALL non-ghost items as potential parents (variants included)
        all_non_ghost = [i for i in items if i not in ghosts]
        modifiers, standalones = self._detect_modifiers(remaining, all_non_ghost)

        # 5. Anything left is standalone
        for item in standalones:
            node = GraphNode(
                petpooja_item_id=item.petpooja_item_id,
                node_type="standalone",
                concept_name=item.name,
                display_name=item.name,
                price_paisa=item.base_price,
                category=item.category,
                confidence_score=100,
                inference_basis="No variant/modifier pattern detected — standalone item",
            )
            self._nodes.append(node)

        # 6. Assign temporary IDs and resolve parent_node_id in-memory
        self._resolve_in_memory_parents()

        # 7. Build result
        all_nodes = self._nodes
        self._result = BuildResult(
            nodes=all_nodes,
            concepts_count=len([n for n in all_nodes if n.node_type == "concept"]),
            variants_count=len([n for n in all_nodes if n.node_type == "variant"]),
            ghosts_count=len([n for n in all_nodes if n.node_type == "ghost"]),
            modifiers_count=len([n for n in all_nodes if n.node_type == "modifier"]),
            standalone_count=len([n for n in all_nodes if n.node_type == "standalone"]),
            lowest_confidence=sorted(all_nodes, key=lambda n: n.confidence_score)[:5],
        )
        return self._result

    def persist(self) -> int:
        """Write built nodes to menu_graph_nodes table. Returns count written."""
        if self._result is None:
            raise RuntimeError("Call build() before persist()")

        from intelligence.models import MenuGraphNode

        # Clear existing nodes for this restaurant
        self.db.query(MenuGraphNode).filter_by(
            restaurant_id=self.restaurant_id
        ).delete()
        self.db.flush()

        # First pass: persist concepts and standalones (no parent dependency)
        concept_id_map: dict[str, int] = {}  # concept_name → db id
        for node in self._nodes:
            if node.node_type in ("concept", "standalone"):
                db_node = MenuGraphNode(
                    restaurant_id=self.restaurant_id,
                    petpooja_item_id=node.petpooja_item_id,
                    node_type=node.node_type,
                    concept_name=node.concept_name,
                    display_name=node.display_name,
                    price_paisa=node.price_paisa,
                    category=node.category,
                    is_active=node.is_active,
                    confidence_score=node.confidence_score,
                    inference_basis=node.inference_basis,
                    owner_validated=node.owner_validated,
                )
                self.db.add(db_node)
                self.db.flush()
                concept_id_map[node.concept_name.lower()] = db_node.id

        # Second pass: persist variants, ghosts, modifiers (with parent links)
        for node in self._nodes:
            if node.node_type in ("concept", "standalone"):
                continue

            parent_id = None
            if node._parent_concept:
                parent_id = concept_id_map.get(node._parent_concept.lower())

            db_node = MenuGraphNode(
                restaurant_id=self.restaurant_id,
                petpooja_item_id=node.petpooja_item_id,
                node_type=node.node_type,
                concept_name=node.concept_name,
                display_name=node.display_name,
                parent_node_id=parent_id,
                price_paisa=node.price_paisa,
                category=node.category,
                is_active=node.is_active,
                confidence_score=node.confidence_score,
                inference_basis=node.inference_basis,
                owner_validated=node.owner_validated,
            )
            self.db.add(db_node)

        self.db.flush()
        return len(self._nodes)

    def _resolve_in_memory_parents(self) -> None:
        """Assign temp IDs and resolve _parent_concept → parent_node_id in-memory."""
        # Assign temp IDs
        concept_id_map: dict[str, int] = {}
        for i, node in enumerate(self._nodes, start=1):
            node._temp_id = i
            if node.node_type in ("concept", "standalone"):
                concept_id_map[node.concept_name.lower()] = i

        # Resolve parent links
        for node in self._nodes:
            if node._parent_concept:
                parent_id = concept_id_map.get(node._parent_concept.lower())
                if parent_id is not None:
                    node.parent_node_id = parent_id

    # -----------------------------------------------------------------------
    # Detection algorithms
    # -----------------------------------------------------------------------

    def _detect_ghosts(self, items: list) -> tuple[list, list]:
        """Detect ghost items: price = 0 and in Add-ons/addon classification."""
        ghosts = []
        non_ghosts = []

        for item in items:
            is_ghost = False
            basis = ""

            if item.base_price == 0:
                is_ghost = True
                basis = f"Price is ₹0 — likely a POS artefact or free addon"
                confidence = 85
            elif item.classification == "addon" and item.base_price > 0:
                # Paid addon — not a ghost, but might be a modifier
                non_ghosts.append(item)
                continue
            else:
                non_ghosts.append(item)
                continue

            if is_ghost:
                node = GraphNode(
                    petpooja_item_id=item.petpooja_item_id,
                    node_type="ghost",
                    concept_name=item.name,
                    display_name=item.name,
                    price_paisa=item.base_price,
                    category=item.category,
                    confidence_score=confidence,
                    inference_basis=basis,
                )
                self._nodes.append(node)
                ghosts.append(item)

        return ghosts, non_ghosts

    def _cluster_variants(self, items: list) -> tuple[list, list, list]:
        """Group items by stripping variant prefixes/suffixes.

        "Hot Latte" + "Iced Latte" → concept "Latte", variants Hot/Iced.
        "Small Cappuccino" + "Large Cappuccino" → concept "Cappuccino".
        """
        # Build a mapping: base_name → [items]
        base_groups: dict[str, list] = defaultdict(list)
        item_to_base: dict[str, str] = {}

        for item in items:
            base = self._extract_base_name(item.name)
            base_groups[base].append(item)
            item_to_base[item.petpooja_item_id or item.name] = base

        concepts = []
        variants = []
        remaining = []

        for base_name, group in base_groups.items():
            if len(group) >= 2:
                # This is a concept with variants
                concept_node = GraphNode(
                    petpooja_item_id=None,
                    node_type="concept",
                    concept_name=base_name,
                    display_name=base_name,
                    category=group[0].category,
                    confidence_score=self._variant_confidence(group),
                    inference_basis=f"Grouped {len(group)} items sharing base name '{base_name}': {', '.join(i.name for i in group)}",
                )
                self._nodes.append(concept_node)
                concepts.append(concept_node)

                for item in group:
                    variant_node = GraphNode(
                        petpooja_item_id=item.petpooja_item_id,
                        node_type="variant",
                        concept_name=base_name,
                        display_name=item.name,
                        price_paisa=item.base_price,
                        category=item.category,
                        confidence_score=self._variant_confidence(group),
                        inference_basis=f"Variant of '{base_name}' — detected via prefix/suffix pattern",
                        _parent_concept=base_name,
                    )
                    self._nodes.append(variant_node)
                    variants.append(variant_node)
            else:
                # Single item — not a variant cluster
                remaining.extend(group)

        return concepts, variants, remaining

    def _detect_modifiers(
        self, items: list, all_potential_parents: Optional[list] = None
    ) -> tuple[list, list]:
        """Detect items that appear in >75% of orders alongside a parent.

        Uses order_items co-occurrence analysis.
        all_potential_parents: full list of non-ghost items to check co-occurrence
        against (includes items already consumed by variant clustering).
        """
        from core.models import OrderItem

        modifiers = []
        standalones = []

        # Get addon-classified items from remaining
        addon_items = [i for i in items if i.classification == "addon"]
        non_addon_items = [i for i in (all_potential_parents or items) if i.classification != "addon"]

        if not addon_items:
            return [], items

        # For each addon, check co-occurrence with non-addon items
        for addon in addon_items:
            # Count orders containing this addon
            addon_order_count = (
                self.db.query(func.count(func.distinct(OrderItem.order_id)))
                .filter(
                    OrderItem.restaurant_id == self.restaurant_id,
                    OrderItem.item_name == addon.name,
                )
                .scalar()
            ) or 0

            if addon_order_count == 0:
                standalones.append(addon)
                continue

            # Find the most co-occurring non-addon item
            best_parent = None
            best_ratio = 0.0

            # Get all orders that contain this addon
            addon_orders = (
                self.db.query(OrderItem.order_id)
                .filter(
                    OrderItem.restaurant_id == self.restaurant_id,
                    OrderItem.item_name == addon.name,
                )
                .subquery()
            )

            # For each potential parent, check co-occurrence
            for parent_candidate in non_addon_items:
                parent_in_addon_orders = (
                    self.db.query(func.count(func.distinct(OrderItem.order_id)))
                    .filter(
                        OrderItem.order_id.in_(
                            self.db.query(addon_orders.c.order_id)
                        ),
                        OrderItem.item_name == parent_candidate.name,
                    )
                    .scalar()
                ) or 0

                if parent_in_addon_orders > 0:
                    # Count total orders of this parent
                    parent_total = (
                        self.db.query(func.count(func.distinct(OrderItem.order_id)))
                        .filter(
                            OrderItem.restaurant_id == self.restaurant_id,
                            OrderItem.item_name == parent_candidate.name,
                        )
                        .scalar()
                    ) or 0

                    if parent_total > 0:
                        ratio = parent_in_addon_orders / parent_total
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_parent = parent_candidate

            if best_ratio >= MODIFIER_COOCCURRENCE_THRESHOLD and best_parent:
                confidence = min(95, int(50 + best_ratio * 50))
                # Find parent concept name
                parent_concept = self._extract_base_name(best_parent.name)
                # Check if this parent is already in a concept group
                existing_concepts = [
                    n for n in self._nodes
                    if n.node_type == "concept"
                ]
                parent_concept_match = None
                for c in existing_concepts:
                    if c.concept_name.lower() == parent_concept.lower():
                        parent_concept_match = c.concept_name
                        break

                # If no concept, use the parent item itself as the concept
                if not parent_concept_match:
                    parent_concept_match = best_parent.name

                node = GraphNode(
                    petpooja_item_id=addon.petpooja_item_id,
                    node_type="modifier",
                    concept_name=addon.name,
                    display_name=addon.name,
                    price_paisa=addon.base_price,
                    category=addon.category,
                    confidence_score=confidence,
                    inference_basis=(
                        f"Appears in {best_ratio:.0%} of '{best_parent.name}' orders "
                        f"({addon_order_count} co-occurrences) — modifier pattern"
                    ),
                    _parent_concept=parent_concept_match,
                )
                self._nodes.append(node)
                modifiers.append(addon)
            else:
                standalones.append(addon)

        # Non-addon remaining items (from the `items` list, not all_potential_parents)
        remaining_non_addon = [i for i in items if i.classification != "addon"]
        standalones.extend(remaining_non_addon)
        return modifiers, standalones

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_base_name(name: str) -> str:
        """Strip variant prefixes/suffixes to get the base concept name.

        "Hot Latte" → "Latte"
        "Iced Pour Over" → "Pour Over"
        "Large Cappuccino" → "Cappuccino"
        "Small Cappuccino" → "Cappuccino"
        """
        words = name.strip().split()
        if not words:
            return name

        # Strip leading variant prefix
        if words[0].lower() in VARIANT_PREFIXES and len(words) > 1:
            words = words[1:]

        # Strip trailing variant suffix
        if words[-1].lower() in VARIANT_SUFFIXES and len(words) > 1:
            words = words[:-1]

        return " ".join(words)

    @staticmethod
    def _variant_confidence(group: list) -> int:
        """Score confidence for a variant cluster.

        Higher confidence when:
        - More items in the group
        - Items share the same category
        - Price differences are reasonable (size variants cost more)
        """
        base_confidence = 60

        # Bonus for group size
        if len(group) >= 3:
            base_confidence += 15
        elif len(group) == 2:
            base_confidence += 10

        # Bonus for same category
        categories = set(i.category for i in group)
        if len(categories) == 1:
            base_confidence += 15

        # Cap at 95 — only owner validation gets 100
        return min(95, base_confidence)
