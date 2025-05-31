class DiagramState:
    def __init__(self):
        self.nodes_ui = []
        self.connections_ui = []
        self.selected = None

    def add_node(self, node_ui):
        self.nodes_ui.append(node_ui)

    def remove_node(self, node_ui):
        self.nodes_ui.remove(node_ui)

    def add_connection(self, connection):
        self.connections_ui.append(connection)

    def remove_connection(self, connection):
        self.connections_ui.remove(connection)

    def clear(self):
        self.nodes_ui.clear()
        self.connections_ui.clear()
        self.selected = None