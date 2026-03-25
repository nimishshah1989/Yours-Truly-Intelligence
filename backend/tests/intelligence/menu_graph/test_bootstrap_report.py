"""Quick bootstrap report — prints detection summary for review."""

import pytest
from sqlalchemy.orm import Session


def test_bootstrap_report(
    db: Session, restaurant_id: int, sample_menu_items,
    sample_orders_with_cooccurrence, capsys
):
    from intelligence.menu_graph.graph_builder import MenuGraphBuilder

    builder = MenuGraphBuilder(restaurant_id, db)
    result = builder.build()
    builder.persist()

    print("\n" + "=" * 60)
    print("MENU GRAPH BOOTSTRAP REPORT — YoursTruly Coffee Roaster")
    print("=" * 60)
    print(f"Concepts detected:    {result.concepts_count}")
    print(f"Variants detected:    {result.variants_count}")
    print(f"Ghost items detected: {result.ghosts_count}")
    print(f"Modifiers detected:   {result.modifiers_count}")
    print(f"Standalone items:     {result.standalone_count}")
    print(f"Total nodes:          {len(result.nodes)}")

    print("\n--- All Nodes ---")
    for n in result.nodes:
        parent = f" (parent: {n._parent_concept})" if n._parent_concept else ""
        print(f"  [{n.node_type:10}] {n.display_name:25} conf={n.confidence_score:3d}{parent}")

    print("\n--- 5 Lowest Confidence Inferences ---")
    for n in result.lowest_confidence:
        print(f"  [{n.confidence_score:3d}] {n.display_name:25} type={n.node_type}")
        print(f"         Basis: {n.inference_basis}")

    from intelligence.menu_graph.validator import MenuGraphValidator
    validator = MenuGraphValidator(restaurant_id, db)
    questions = validator.generate_validation_questions()

    print(f"\n--- Validation Questions ({len(questions)}) ---")
    for q in questions:
        print(f"  Q: {q['question_text']}")
        print(f"     Options: {q['answer_options']}")
        print(f"     Node ID: {q['node_id']}")
        print()

    # The test always passes — it's for reporting
    assert result.concepts_count > 0
