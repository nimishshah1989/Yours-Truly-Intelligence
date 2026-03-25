"""Tests for validator.py — generates WhatsApp validation questions
for low-confidence inferences (score < 70). Max 8 questions.
Output: list of {question_text, answer_options, node_id}
"""

import pytest
from sqlalchemy.orm import Session


@pytest.fixture()
def graph_with_low_confidence(db: Session, restaurant_id: int, sample_menu_items):
    """Build graph — some inferences will have low confidence."""
    from intelligence.menu_graph.graph_builder import MenuGraphBuilder

    builder = MenuGraphBuilder(restaurant_id, db)
    builder.build()
    builder.persist()
    return restaurant_id


class TestValidationQuestionGeneration:
    def test_generates_questions_for_low_confidence(
        self, db: Session, graph_with_low_confidence
    ):
        from intelligence.menu_graph.validator import MenuGraphValidator

        validator = MenuGraphValidator(graph_with_low_confidence, db)
        questions = validator.generate_validation_questions()

        assert isinstance(questions, list)

    def test_max_8_questions(self, db: Session, graph_with_low_confidence):
        from intelligence.menu_graph.validator import MenuGraphValidator

        validator = MenuGraphValidator(graph_with_low_confidence, db)
        questions = validator.generate_validation_questions()

        assert len(questions) <= 8

    def test_question_structure(self, db: Session, graph_with_low_confidence):
        from intelligence.menu_graph.validator import MenuGraphValidator

        validator = MenuGraphValidator(graph_with_low_confidence, db)
        questions = validator.generate_validation_questions()

        for q in questions:
            assert "question_text" in q
            assert "answer_options" in q
            assert "node_id" in q
            assert isinstance(q["answer_options"], list)
            assert len(q["answer_options"]) >= 2

    def test_only_low_confidence_nodes_questioned(
        self, db: Session, graph_with_low_confidence
    ):
        from intelligence.menu_graph.validator import MenuGraphValidator
        from intelligence.models import MenuGraphNode

        validator = MenuGraphValidator(graph_with_low_confidence, db)
        questions = validator.generate_validation_questions()

        for q in questions:
            node = db.query(MenuGraphNode).get(q["node_id"])
            assert node is not None
            assert node.confidence_score < 70

    def test_no_questions_when_all_high_confidence(
        self, db: Session, restaurant_id: int, sample_menu_items
    ):
        """If we manually set all confidence to 100, no questions generated."""
        from intelligence.menu_graph.graph_builder import MenuGraphBuilder
        from intelligence.menu_graph.validator import MenuGraphValidator
        from intelligence.models import MenuGraphNode

        builder = MenuGraphBuilder(restaurant_id, db)
        builder.build()
        builder.persist()

        # Force all nodes to high confidence
        db.query(MenuGraphNode).filter_by(
            restaurant_id=restaurant_id
        ).update({"confidence_score": 100})
        db.flush()

        validator = MenuGraphValidator(restaurant_id, db)
        questions = validator.generate_validation_questions()

        assert len(questions) == 0
