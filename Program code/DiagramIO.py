from ConnectionUI import ConnectionUI
import json
from tkinter import filedialog, messagebox
from DiagramApp import DiagramApp
from NodeModel import NodeModel
from NodeUI import NodeUI

class DiagramIo:
    """
    Отвечает за сохранение/загрузку диаграммы в JSON-файл.
    """
    def __init__(self, app: 'DiagramApp'):
        self.app = app

    def _collect_data(self):
        """
        Собирает из текущей диаграммы питоновскую структуру для JSON.
        """
        # 1) Ноды
        nodes = []
        for ui in self.app.nodes_ui:
            m = ui.model
            nodes.append({
                'id':      m.id,
                'type':    m.type,
                'content': m.content,
                'x':       ui.x,
                'y':       ui.y,
            })

        # 2) Рёбра с точками
        edges = []
        for conn in self.app.connections_ui:
            edges.append({
                'from_node': conn.src_ui.model.id,
                'from_port': conn.sp.name,
                'to_node':   conn.dst_ui.model.id,
                'to_port':   conn.dp.name,
                'points':    conn.points,   # список [(x,y),...]
            })

        return {'nodes': nodes, 'edges': edges}

    def save_dialog(self):
        data = self._collect_data()
        fn = filedialog.asksaveasfilename(
            title="Сохранить диаграмму",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if not fn:
            return
        try:
            with open(fn, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Успех", f"Диаграмма сохранена в:\n{fn}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")

    def load_dialog(self):
        fn = filedialog.askopenfilename(
            title="Открыть диаграмму",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if not fn:
            return
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
            return

        try:
            self._load_data(data)
            messagebox.showinfo("Успех", "Диаграмма успешно загружена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"При загрузке произошла ошибка:\n{e}")

    def _load_data(self, data):
        """
        Очищает текущую диаграмму и рисует заново из данных JSON.
        """
        # --- 1) очистка ---
        self.app.canvas.delete('all')
        self.app.nodes_ui.clear()
        self.app.connections_ui.clear()
        self.app.graph.nodes.clear()

        # temporary map node_id -> NodeUI
        id_to_ui = {}

        # --- 2) создаём ноды ---
        for n in data.get('nodes', []):
            m = NodeModel(n['id'], n['type'], n.get('content', ''))
            self.app.graph.add_node(m)
            ui = NodeUI(self.app.canvas, m, n['x'], n['y'], self.app)
            self.app.nodes_ui.append(ui)
            id_to_ui[m.id] = ui

        # --- 3) создаём связи по данным edges ---
        for e in data.get('edges', []):
            su_ui = id_to_ui[e['from_node']]
            du_ui = id_to_ui[e['to_node']]
            sp = next(p for p in su_ui.model.ports if p.name == e['from_port'])
            dp = next(p for p in du_ui.model.ports if p.name == e['to_port'])
            pts = e.get('points', None)

            # создаём ConnectionUI с восстановленными точками
            conn = ConnectionUI(
                self.app.canvas,
                src_ui=su_ui, sp=sp,
                dst_ui=du_ui, dp=dp,
                app=self.app,
                points=pts
            )
            # привязываем модельно
            sp.connection = dp
            dp.connection = sp
