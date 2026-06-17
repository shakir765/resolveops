from langgraph.graph import END, StateGraph

from resolveops_core.graph.checkpoint import get_checkpointer
from resolveops_core.graph.edges import (
    route_after_diagnostic,
    route_after_escalation,
    route_after_validator,
)
from resolveops_core.graph.nodes import (
    classifier_node,
    communication_node,
    diagnostic_node,
    escalation_node,
    human_review_node,
    knowledge_node,
    resolution_node,
    supervisor_node,
    tool_executor_node,
    triage_node,
    validator_node,
)
from resolveops_core.graph.state import TicketState


def build_workflow():
    graph = StateGraph(TicketState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("triage", triage_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("diagnostic", diagnostic_node)
    graph.add_node("resolution", resolution_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("validator", validator_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("communication", communication_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "triage")
    graph.add_edge("triage", "classifier")
    graph.add_edge("classifier", "knowledge")
    graph.add_edge("knowledge", "diagnostic")
    graph.add_conditional_edges("diagnostic", route_after_diagnostic, {
        "escalation": "escalation",
        "resolution": "resolution",
    })
    graph.add_edge("resolution", "tool_executor")
    graph.add_edge("tool_executor", "validator")
    graph.add_conditional_edges("validator", route_after_validator, {
        "communication": "communication",
        "escalation": "escalation",
        "diagnostic": "diagnostic",
    })
    graph.add_edge("communication", END)
    graph.add_conditional_edges("escalation", route_after_escalation, {
        "human_review": "human_review",
        "end": END,
    })
    graph.add_edge("human_review", "resolution")

    return graph


def compile_workflow(with_checkpoint: bool = True):
    workflow = build_workflow()
    if with_checkpoint:
        checkpointer = get_checkpointer()
        return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])
    return workflow.compile(interrupt_before=["human_review"])
