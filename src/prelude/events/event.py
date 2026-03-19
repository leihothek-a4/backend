class Event:
    def __init__(self, type: str, broadcast: bool = False):
        self.type: str = type
        self.broadcast: bool = broadcast
        self.consumed: bool = False

    def consume(self) -> None:
        """
        Marks the event as consumed. Systems later in the pipeline
        will ignore it unless broadcast=True.
        """
        self.consumed = True
