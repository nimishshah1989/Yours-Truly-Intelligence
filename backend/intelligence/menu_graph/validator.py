"""Menu Graph Validator — generates WhatsApp validation questions
for low-confidence inferences (score < 70). Max 8 questions.

Output: list of {question_text, answer_options, node_id}
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from intelligence.models import MenuGraphNode

logger = logging.getLogger("ytip.menu_graph.validator")

# Confidence threshold below which we ask the owner
CONFIDENCE_THRESHOLD = 70

# Maximum questions to ask in one validation batch
MAX_QUESTIONS = 8


class MenuGraphValidator:
    """Generate WhatsApp-friendly validation questions for uncertain inferences."""

    def __init__(self, restaurant_id: int, db: Session):
        self.restaurant_id = restaurant_id
        self.db = db

    def generate_validation_questions(self) -> list[dict]:
        """Generate questions for low-confidence nodes.

        Returns list of dicts with keys:
        - question_text: human-readable question
        - answer_options: list of possible answers
        - node_id: MenuGraphNode.id this question validates
        """
        # Get low-confidence, unvalidated nodes
        nodes = (
            self.db.query(MenuGraphNode)
            .filter(
                MenuGraphNode.restaurant_id == self.restaurant_id,
                MenuGraphNode.confidence_score < CONFIDENCE_THRESHOLD,
                MenuGraphNode.owner_validated.is_(False),
            )
            .order_by(MenuGraphNode.confidence_score.asc())
            .limit(MAX_QUESTIONS)
            .all()
        )

        questions = []
        for node in nodes:
            question = self._build_question(node)
            if question:
                questions.append(question)

        return questions

    def _build_question(self, node: MenuGraphNode) -> Optional[dict]:
        """Build a validation question based on node type."""
        if node.node_type == "variant":
            return self._variant_question(node)
        elif node.node_type == "modifier":
            return self._modifier_question(node)
        elif node.node_type == "ghost":
            return self._ghost_question(node)
        else:
            return self._generic_question(node)

    def _variant_question(self, node: MenuGraphNode) -> dict:
        """Ask if an item is really a variant of its parent concept."""
        parent = None
        if node.parent_node_id:
            parent = self.db.query(MenuGraphNode).get(node.parent_node_id)

        parent_name = parent.concept_name if parent else node.concept_name

        return {
            "question_text": (
                f"Is '{node.display_name}' a version/size of '{parent_name}'? "
                f"Or is it a separate item?"
            ),
            "answer_options": [
                f"Yes, it's a variant of {parent_name}",
                "No, it's a separate item",
                "Not sure",
            ],
            "node_id": node.id,
        }

    def _modifier_question(self, node: MenuGraphNode) -> dict:
        """Ask if an item is an addon/modifier."""
        return {
            "question_text": (
                f"Is '{node.display_name}' an add-on that customers add to other items? "
                f"Or is it ordered on its own?"
            ),
            "answer_options": [
                "Yes, it's an add-on/modifier",
                "No, it's ordered independently",
                "Both — sometimes add-on, sometimes standalone",
            ],
            "node_id": node.id,
        }

    def _ghost_question(self, node: MenuGraphNode) -> dict:
        """Ask about a zero-price or POS artefact item."""
        return {
            "question_text": (
                f"'{node.display_name}' shows as ₹0 in your POS. "
                f"Is this still an active item? Should it have a price?"
            ),
            "answer_options": [
                "It's a free add-on, keep it",
                "It should have a price, I'll update POS",
                "It's inactive, please hide it",
            ],
            "node_id": node.id,
        }

    def _generic_question(self, node: MenuGraphNode) -> dict:
        """Fallback question for any uncertain node."""
        return {
            "question_text": (
                f"I'm not sure how to classify '{node.display_name}'. "
                f"Is it a main menu item, an add-on, or something else?"
            ),
            "answer_options": [
                "Main menu item",
                "Add-on / modifier",
                "Not actively sold",
            ],
            "node_id": node.id,
        }
