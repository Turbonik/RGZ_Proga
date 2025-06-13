import json
from tkinter import messagebox, filedialog
from NodeModel import NodeModel
from DiagramApp import DiagramApp
from NodeUI import NodeUI
from ConnectionUI import ConnectionUI

class DiagramIo:
    def __init__(self, app: 'DiagramApp'):
        self.app = app

    def _collect_data(self):
        nodes = []
        for ui in self.app.diagram_state.nodes_ui:
            m = ui.model
            nodes.append({
                'id':      m.id,
                'type':    m.type,
                'content': m.content,
                'x':       ui.x,
                'y':       ui.y,
            })

        edges = []
        for conn in self.app.diagram_state.connections_ui:
           
            inner = conn.points[1:-1]
            edges.append({
                'from_node': conn.src_ui.model.id,
                'from_port': conn.sp.name,
                'to_node':   conn.dst_ui.model.id,
                'to_port':   conn.dp.name,
                'points':    inner if inner else None,
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
        # 0) Очистка предыдущего
        self.app.canvas.delete('all')
        self.app.diagram_state.clear()

        # 1) создаём все узлы, автоматически правим повторяющиеся ID
        id_to_ui = {}
        used_ids = set()
        for n in data.get('nodes', []):
            orig_id = n['id']
            new_id = orig_id
            i = 2
            # если встречался — добавляем суффикс _2, _3 …
            while new_id in used_ids:
                new_id = f"{orig_id}_{i}"
                i += 1
            used_ids.add(new_id)

            # создаём узел с уникальным new_id
            m  = NodeModel(new_id, n['type'], n.get('content',''))
            ui = NodeUI(self.app.canvas, m, n['x'], n['y'], self.app)
            self.app.diagram_state.add_node(ui)
            id_to_ui[new_id] = ui

        # 2) создаём связи
        for e in data.get('edges', []):
     
            su_ui = id_to_ui[e['from_node']]
            du_ui = id_to_ui[e['to_node']]
            sp    = next(p for p in su_ui.model.ports if p.name == e['from_port'])
            dp    = next(p for p in du_ui.model.ports if p.name == e['to_port'])

            raw = e.get('points')
            inner = [tuple(pt) for pt in raw] if raw else None

            x0, y0 = su_ui.port_position(sp)
            x1, y1 = du_ui.port_position(dp)
            pts = [(x0, y0)] + inner + [(x1, y1)] if inner else None

            ConnectionUI(
                self.app.canvas,
                src_ui=su_ui, sp=sp,
                dst_ui=du_ui, dp=dp,
                app=self.app,
                points=pts
            )
