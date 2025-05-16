import DiagramApp
import json
from tkinter import filedialog, messagebox
from NodeModel import NodeModel
from NodeUI import NodeUI

class DiagramIo:
    """
    Отвечает за сохранение/загрузку диаграммы в JSON-файл.
    """

    def __init__(self, app: 'DiagramApp'):
        self.app = app  # экземпляр DiagramApp

    def _collect_data(self):
        """Собирает из текущей диаграммы питоновскую структуру для JSON."""
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

        edges = []
        for conn in self.app.connections:
            su, sp = conn['src']
            du, dp = conn['dst']
            edges.append({
                'from_node': su.model.id,
                'from_port': sp.name,
                'to_node':   du.model.id,
                'to_port':   dp.name,
                'route':     conn.get('route', 'default'),
            })

        return {'nodes': nodes, 'edges': edges}

    def save_dialog(self):
        """Открывает диалог «Сохранить как…» и пишет JSON-файл."""
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
        """Открывает диалог «Открыть…», читает JSON и восстанавливает диаграмму."""
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
        Собирает UI и модели из переданной структуры data.
        Очищает предыдущую диаграмму и полностью её восстанавливает.
        """
        # --- 1) Очистка ---
        # удаляем всё нарисованное
        self.app.canvas.delete('all')
        # сбрасываем списки узлов и связей
        self.app.nodes_ui.clear()
        self.app.connections.clear()
        # сбрасываем модель графа
        self.app.graph.nodes.clear()

        # промежуточный мэппинг id → NodeUI
        id_to_ui = {}

        # --- 2) Восстановление узлов ---
        for n in data.get('nodes', []):
            m = NodeModel(n['id'], n['type'], n.get('content', ''))
            # добавляем в модель
            self.app.graph.add_node(m)
            # создаём UI
            ui = NodeUI(self.app.canvas, m, n['x'], n['y'], self.app)
            self.app.nodes_ui.append(ui)
            id_to_ui[m.id] = ui

        # --- 3) Восстановление связей ---
        for e in data.get('edges', []):
            from_id = e['from_node']
            to_id   = e['to_node']
            from_port = e['from_port']
            to_port   = e['to_port']
            route     = e.get('route', None)

            su_ui = id_to_ui[from_id]
            du_ui = id_to_ui[to_id]

            sp = next(p for p in su_ui.model.ports if p.name == from_port)
            dp = next(p for p in du_ui.model.ports if p.name == to_port)

            su_ui.draw_connection(sp, du_ui, dp, route=route)

            # ОБНОВЛЯЕМ МОДЕЛЬ
            sp.connection = dp
            dp.connection = sp
