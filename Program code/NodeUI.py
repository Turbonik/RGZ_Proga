from tkinter import simpledialog, messagebox

class NodeUI:
    WIDTH, HEIGHT = 120, 60
    LOOP_DX = 80
    LOOP_DOWN = 40
    ENTRY_OFFSET = -10

    def __init__(self, canvas, model, x, y, app):
        self.canvas = canvas
        self.model = model
        self.app = app
        self.x, self.y = x, y
        self.items = []
        self.port_items = {}
        self.draw()
        self.bind_events()

    def draw(self):
        self.__clear_previous()
        self.__draw_shape()
        self.__draw_text()
        self.__draw_ports()

    def __clear_previous(self):
        for item in self.items:
            self.canvas.delete(item)
        self.items.clear()
        self.port_items.clear()

    def __draw_shape(self):
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.WIDTH, y0 + self.HEIGHT
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        t = self.model.type

        if t in ('START', 'END'):
            self.shape = self.canvas.create_oval(x0, y0, x1, y1, fill='lightgrey', width=2)
        elif t == 'BRANCH':
            pts = [cx, y0, x1, cy, cx, y1, x0, cy]
            self.shape = self.canvas.create_polygon(pts, fill='yellow', outline='black', width=2)
        elif t == 'WHILE':
            pts = [cx, y0, x1, cy, cx, y1, x0, cy]
            self.shape = self.canvas.create_polygon(pts, fill='lightblue', outline='black', width=2)
        elif t == 'MERGE':
            self.shape = self.canvas.create_rectangle(x0, y0, x1, y1, outline='', fill='')
        elif t == 'FOR':
            dx = self.WIDTH * 0.2   
            pts = [x0+dx,y0, x1-dx,y0, x1,cy, x1-dx,y1, x0+dx,y1, x0,cy]
            self.shape = self.canvas.create_polygon(pts, fill='lightblue', outline='black', width=2)
        elif t in ('INPUT','OUTPUT'):
            skew = self.WIDTH * 0.2
            fill = 'lightgreen' if t=='INPUT' else 'lightpink'
            pts = [x0+skew,y0, x1,y0, x1-skew,y1, x0,y1]
            self.shape = self.canvas.create_polygon(pts, fill=fill, outline='black', width=2)
        else:
            self.shape = self.canvas.create_rectangle(x0, y0, x1, y1, fill='lightgrey', width=2)
        self.items.append(self.shape)

    def __draw_text(self):
        if self.model.type != 'MERGE':
            cx = self.x + self.WIDTH / 2
            cy = self.y + self.HEIGHT / 2
            label = self.model.content or self.model.type
            self.text_id = self.canvas.create_text(cx, cy, text=label)
            self.items.append(self.text_id)

    def __draw_ports(self):
        for p in self.model.ports:
            px, py = self.port_position(p)
            cid = self.canvas.create_oval(px-5, py-5, px+5, py+5, fill='black')
            self.port_items[cid] = p
            self.items.append(cid)

    def port_position(self, port):
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.WIDTH, y0 + self.HEIGHT
        cx, cy = (x0 + x1)/2, (y0 + y1)/2
        t = self.model.type

        if t == 'START':
            return cx, y1
        if t == 'END':
            return cx, y0
        if t == 'ACTION':
            return (cx, y0) if port.port_type=='in' else (cx, y1)

        if t == 'BRANCH':
            if port.port_type=='in': return cx, y0
            if port.name=='out_true': return x1, cy
            if port.name=='out_false': return x0, cy

        if t in ('INPUT','OUTPUT'):
            return (cx, y0) if port.port_type=='in' else (cx, y1)

        if t == 'FOR' or t == 'WHILE':
            # Общая схема: in_top, in_back, out_body, out_end
            if port.name=='in':       return cx,   y0
            if port.name=='in_back':  return x0,   cy
            if port.name=='out_body': return cx,   y1
            if port.name=='out_end':  return x1,   cy

        if t == 'MERGE':
            # теперь точки ещё ближе
            dx = self.WIDTH * 0.08  
            dy = self.HEIGHT * 0.08
            if port.name == 'in1':
                return cx - dx, cy - dy
            if port.name == 'in2':
                return cx + dx, cy - dy
            if port.port_type == 'out':
                return cx, cy + dy

        return cx, cy
     

    def bind_events(self):
        editable = ('ACTION','BRANCH','FOR','WHILE', 'OUTPUT', 'INPUT')
        for item in (self.shape, getattr(self, 'text_id', None)):
            if item is None: continue
            self.canvas.tag_bind(item, '<Button1-Motion>', self.on_drag)
            self.canvas.tag_bind(item, '<Button-3>', self.on_right_click)
            if self.model.type in editable:
                self.canvas.tag_bind(item, '<Double-1>', self.on_double_click)
        for cid in self.port_items:
            self.canvas.tag_bind(cid, '<Button-1>', self.on_port_click)

    def on_drag(self, event):
        real_x = self.canvas.canvasx(event.x)
        real_y = self.canvas.canvasy(event.y)
        dx = real_x - (self.x + self.WIDTH/2)
        dy = real_y - (self.y + self.HEIGHT/2)
        self.x += dx
        self.y += dy
        for it in self.items:
            self.canvas.move(it, dx, dy)
        self.app.update_connections(self)

    def on_double_click(self, event):
        prompt = "Введите переменные через пробел:" if self.model.type == 'INPUT' else "Введите текст:"
        new = simpledialog.askstring("Изменение текста", prompt, initialvalue=self.model.content)
        if new is not None:
            self.model.content = new.strip()
            self.canvas.itemconfig(self.text_id, text=self.model.content)

    def on_right_click(self, event):
        if messagebox.askyesno("Удаление блока", f"Удалить блок {self.model.id}?"):
            self.app.delete_node(self)

    def on_port_click(self, event):
        cid = self.canvas.find_withtag("current")[0]
        port = self.port_items[cid]
        self.app.handle_port_click(self, port)

    def on_delete(self):
        for it in self.items: 
            self.canvas.delete(it)