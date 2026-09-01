from abc import ABC
from app.layer_3.steps.contracts.step import ExtractionContext, ExtractionState

class NamedStatefulSingleton(ABC):

    name : str = "please.specify.the.name"

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        self.context = context
        self.state   = state
    
    @classmethod
    def get_or_create(cls, context: ExtractionContext, state: ExtractionState) -> "NamedStatefulSingleton":
        if not cls.name in state.data:
            state.data[cls.name] = cls(context, state)
        return state.data[cls.name]
