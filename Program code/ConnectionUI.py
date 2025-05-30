import math

class ConnectionUI:
    """
    Гибкая ломаная линия со сгибами, которые можно:
      - добавить двойным кликом по расширенной (невидимой) зоне линии,
      - удалить правым кликом по любому сгибу,
      - перетаскивать сгибы за микро-точки.
    При перемещении узлов концы линии подтягиваются к портам, внутренние сгибы сохраняются.
    """
   
    HANDLE_SIZE   = 3   
    LOOP_DX       = 140
    LOOP_DOWN     = 40
    ENTRY_OFFSET  = -10

    def __init__(self, canvas, src_ui, sp, dst_ui, dp, app, points=None):
        self.canvas = canvas
        self.app    = app
        self.src_ui, self.sp = src_ui, sp
        self.dst_ui, self.dp = dst_ui, dp

        # определяем петлю (цикл FOR/WHILE)
        self.is_loop = (
            dst_ui.model.type in ('FOR', 'WHILE')
            and sp.name == 'out'
            and dp.name == 'in_back'
        )

        # точки ломаной: либо из JSON, либо рассчитываем из портов
        self.points = points if points is not None else self._calc_points()

        # зарегистрировать себя и модельно привязать
        app.connections_ui.append(self)
        sp.connection = dp
        dp.connection = sp

        # отрисовать линию, хит-зону и микро-точки
        self._draw_all()

    def _calc_points(self):
        """Считаем точки для G-образной линии или L-образной петли."""
        x0, y0 = self.src_ui.port_position(self.sp)
        x1, y1 = self.dst_ui.port_position(self.dp)
        if self.is_loop:
            # L-образная петля: вниз → влево → вверх → вправо
            return [
                (x0, y0),
                (x0, y0 + self.LOOP_DOWN),
                (x0 - self.LOOP_DX, y0 + self.LOOP_DOWN),
                (x0 - self.LOOP_DX, y1),
                (x1 + self.ENTRY_OFFSET, y1),
                (x1, y1),
            ]
        else:
            # G-образная: вниз → вправо → вниз
            ym = (y0 + y1) / 2
            return [(x0, y0), (x0, ym), (x1, ym), (x1, y1)]

    def _flat(self):
        """Развёртка списка точек в плоский список координат."""
        return [c for pt in self.points for c in pt]

    def _draw_all(self):
        """Перерисовывает линию, хит-зону и микро-точки handle."""
        # удаляем старые элементы
        for attr in ('line_id', 'hit_id'):
            if hasattr(self, attr):
                self.canvas.delete(getattr(self, attr))
        if hasattr(self, 'handles'):
            for h in self.handles:
                self.canvas.delete(h)

        # основная линия
        self.line_id = self.canvas.create_line(
            *self._flat(), arrow='last', width=2
        )
        # невидимая хит-зона для двойного клика
        self.hit_id = self.canvas.create_line(
            *self._flat(), width=12, fill=''
        )
        self.canvas.tag_bind(self.hit_id, '<Double-1>', self.on_line_double_click)

        # создаём микро-точки для сгибов
        self._create_handles()

    def _create_handles(self):
        """Создаёт точки-изгиба"""
        self.handles = []
        for idx in range(1, len(self.points) - 1):
            x, y = self.points[idx]
            h = self.canvas.create_oval(
                x - self.HANDLE_SIZE, y - self.HANDLE_SIZE,
                x + self.HANDLE_SIZE, y + self.HANDLE_SIZE,
                fill='gray', outline=''  
            )
            # перетаскивание сгиба
            self.canvas.tag_bind(h, '<B1-Motion>', lambda e, i=idx: self.on_handle_drag(e, i))
            # удаление сгиба правым кликом
            self.canvas.tag_bind(h, '<Button-3>', lambda e, i=idx: self.on_handle_right_click(e, i))
            self.handles.append(h)

    def on_handle_drag(self, event, idx):
        """Перетаскиваем сгиб"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.points[idx] = (x, y)
        self.canvas.coords(self.line_id, *self._flat())
        self.canvas.coords(self.hit_id, *self._flat())
        h = self.handles[idx - 1]
        self.canvas.coords(
            h,
            x - self.HANDLE_SIZE, y - self.HANDLE_SIZE,
            x + self.HANDLE_SIZE, y + self.HANDLE_SIZE
        )

    def on_handle_right_click(self, event, idx):
        """Удаляем сгиб по правому клику"""
        if 0 < idx < len(self.points) - 1:
            self.points.pop(idx)
            self._draw_all()

    def on_line_double_click(self, event):
        """Добавляем сгиб двойным кликом по хит-зоне"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        best_i, best_d = 0, float('inf')
        for i in range(len(self.points) - 1):
            x0, y0 = self.points[i]
            x1, y1 = self.points[i + 1]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            d = (mx - x)**2 + (my - y)**2
            if d < best_d:
                best_d, best_i = d, i
        self.points.insert(best_i + 1, (x, y))
        self._draw_all()

    def refresh_endpoints(self):
        """При перетаскивании узлов подтягиваем только концы, внутренние сгибы сохраняются."""
        x0, y0 = self.src_ui.port_position(self.sp)
        xn, yn = self.dst_ui.port_position(self.dp)
        self.points[0] = (x0, y0)
        self.points[-1] = (xn, yn)
        self.canvas.coords(self.line_id, *self._flat())
        self.canvas.coords(self.hit_id, *self._flat())
        for idx, h in enumerate(self.handles, start=1):
            px, py = self.points[idx]
            self.canvas.coords(
                h,
                px - self.HANDLE_SIZE, py - self.HANDLE_SIZE,
                px + self.HANDLE_SIZE, py + self.HANDLE_SIZE
            )

    def destroy(self):
        """Удаляет всю графику соединения из канваса"""
        self.canvas.delete(self.line_id)
        self.canvas.delete(self.hit_id)
        for h in self.handles:
            self.canvas.delete(h)
