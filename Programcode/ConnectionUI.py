
class ConnectionUI:
    """
    Гибкая ломаная линия со сгибами, которые можно:
      - добавить двойным кликом по расширенной (невидимой) зоне линии,
      - удалить правым кликом по любому сгибу,
      - перетаскивать сгибы за микро-точки.
    При перемещении узлов концы линии подтягиваются к портам, внутренние сгибы сохраняются.
    """
    __HANDLE_SIZE = 3
    __LOOP_DX = 140
    __LOOP_DOWN = 40
    __ENTRY_OFFSET = -10

    def __init__(self, canvas, src_ui, sp, dst_ui, dp, app, points=None):
        self.canvas = canvas
        self.app = app
        self.src_ui, self.sp = src_ui, sp
        self.dst_ui, self.dp = dst_ui, dp
        self.__init_loop_flag()
        self.points = points if points is not None else self.__calc_points()
        self.__register_connection()
        self.__draw_all()

    def __init_loop_flag(self):
        self.is_loop = (
            self.dst_ui.model.type in ('FOR', 'WHILE')
            and self.sp.name == 'out'
            and self.dp.name == 'in_back'
        )

    def __register_connection(self):
        self.app.diagram_state.add_connection(self)
        self.sp.connection = self.dp
        self.dp.connection = self.sp

    def __calc_points(self):
        x0, y0 = self.src_ui.port_position(self.sp)
        x1, y1 = self.dst_ui.port_position(self.dp)
        if self.is_loop:
            return [
                (x0, y0),
                (x0, y0 + self.__LOOP_DOWN),
                (x0 - self.__LOOP_DX, y0 + self.__LOOP_DOWN),
                (x0 - self.__LOOP_DX, y1),
                (x1 + self.__ENTRY_OFFSET, y1),
                (x1, y1),
            ]
        else:
            ym = (y0 + y1) / 2
            return [(x0, y0), (x0, ym), (x1, ym), (x1, y1)]

    def __flat(self):
        return [c for pt in self.points for c in pt]

    def __draw_all(self):
        self.__clear_previous_drawing()
        self.line_id = self.canvas.create_line(*self.__flat(), arrow='last', width=2)
        self.hit_id = self.canvas.create_line(*self.__flat(), width=12, fill='')
        self.canvas.tag_bind(self.hit_id, '<Double-1>', self.on_line_double_click)
        self.__create_handles()

    def __clear_previous_drawing(self):
        for attr in ('line_id', 'hit_id'):
            if hasattr(self, attr):
                self.canvas.delete(getattr(self, attr))
        if hasattr(self, 'handles'):
            for h in self.handles:
                self.canvas.delete(h)

    def __create_handles(self):
        self.handles = []
        for idx in range(1, len(self.points) - 1):
            x, y = self.points[idx]
            h = self.canvas.create_oval(
                x - self.__HANDLE_SIZE, y - self.__HANDLE_SIZE,
                x + self.__HANDLE_SIZE, y + self.__HANDLE_SIZE,
                fill='gray', outline=''  
            )
            self.canvas.tag_bind(h, '<B1-Motion>', lambda e, i=idx: self.on_handle_drag(e, i))
            self.canvas.tag_bind(h, '<Button-3>', lambda e, i=idx: self.on_handle_right_click(e, i))
            self.handles.append(h)

    def on_handle_drag(self, event, idx):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.points[idx] = (x, y)
        self.canvas.coords(self.line_id, *self.__flat())
        self.canvas.coords(self.hit_id, *self.__flat())
        h = self.handles[idx - 1]
        self.canvas.coords(
            h,
            x - self.__HANDLE_SIZE, y - self.__HANDLE_SIZE,
            x + self.__HANDLE_SIZE, y + self.__HANDLE_SIZE
        )

    def on_handle_right_click(self, event, idx):
        if 0 < idx < len(self.points) - 1:
            self.points.pop(idx)
            self.__draw_all()

    def on_line_double_click(self, event):
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
        self.__draw_all()

    def refresh_endpoints(self):
        x0, y0 = self.src_ui.port_position(self.sp)
        xn, yn = self.dst_ui.port_position(self.dp)
        self.points[0] = (x0, y0)
        self.points[-1] = (xn, yn)
        self.canvas.coords(self.line_id, *self.__flat())
        self.canvas.coords(self.hit_id, *self.__flat())
        for idx, h in enumerate(self.handles, start=1):
            px, py = self.points[idx]
            self.canvas.coords(
                h,
                px - self.__HANDLE_SIZE, py - self.__HANDLE_SIZE,
                px + self.__HANDLE_SIZE, py + self.__HANDLE_SIZE
            )

    def destroy(self):
        self.canvas.delete(self.line_id)
        self.canvas.delete(self.hit_id)
        for h in self.handles:
            self.canvas.delete(h)
        self.app.diagram_state.remove_connection(self)
        self.sp.connection = None
        self.dp.connection = None