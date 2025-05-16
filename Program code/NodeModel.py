from PortModel import PortModel

class NodeModel:
    def __init__(self, node_id, ntype, content=""):
        self.id = node_id
        self.type = ntype
        self.content = content
        self.ports = []

        # Определение портов для разных типов узлов
        if ntype == 'BRANCH':
            self.ports = [
                PortModel(self, 'in', 'in'),
                PortModel(self, 'out_true', 'out'),
                PortModel(self, 'out_false', 'out')
            ]
        elif ntype == 'INPUT' or ntype == 'OUTPUT':
            self.ports = [
                PortModel(self, 'in',  'in'),
                PortModel(self, 'out', 'out'),
            ]
        elif ntype == 'FOR':
            self.ports = [
                PortModel(self, 'in',       'in'),   # главный вход сверху
                PortModel(self, 'in_back',  'in'),   # левый вход из тела
                PortModel(self, 'out_body', 'out'),  # выход в тело (вниз)
                PortModel(self, 'out_end',  'out')   # выход из цикла (вправо)
            ]
        elif ntype == 'WHILE':
            self.ports = [
                PortModel(self, 'in',       'in'),   # главный вход сверху
                PortModel(self, 'in_back',  'in'),   # левый вход из тела
                PortModel(self, 'out_body', 'out'),  # выход в тело (вниз)
                PortModel(self, 'out_end',  'out')   # выход из цикла (вправо)
            ]
        elif ntype == 'MERGE':
            self.ports = [
                PortModel(self, 'in1', 'in'),
                PortModel(self, 'in2', 'in'),
                PortModel(self, 'out', 'out')
            ]
        elif ntype == 'START':
            self.ports = [PortModel(self, 'out', 'out')]
        elif ntype == 'END':
            self.ports = [PortModel(self, 'in', 'in')]
        else:
            self.ports = [
                PortModel(self, 'in', 'in'),
                PortModel(self, 'out', 'out')
            ]