from resolveops_core.graph.state import TicketState





def run_supervisor(state: TicketState) -> dict:

    if state.get("status") == "new":

        return {"status": "processing"}

    return {}


