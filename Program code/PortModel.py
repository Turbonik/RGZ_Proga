class PortModel:
    def __init__(self, parent, name, port_type):
        self.parent = parent
        self.name = name
        self.port_type = port_type
        self.connection = None