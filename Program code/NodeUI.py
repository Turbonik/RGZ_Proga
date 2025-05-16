from tkinter import simpledialog, messagebox

class NodeUI:
    WIDTH, HEIGHT = 120, 60
    # константы обхода
    LOOP_DX     = 80   # насколько уходим влево
    LOOP_DOWN   = 40   # насколько опускаемся вниз от выхода
    ENTRY_OFFSET = -10

    def __init__(self, canvas, model, x, y, app):
        self.canvas = canvas
        self.model = model
        self.app = app
        self.x, self.y = x, y
        self.items = [] 
        self.port_items = {}
        self.draw()
        self.bind()

    def draw(self):
        # Удаляем предыдущие элементы
        for item in self.items:
            self.canvas.delete(item)
        self.items.clear()
        self.port_items.clear()

        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.WIDTH, y0 + self.HEIGHT
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        t = self.model.type

        # === Форма узла ===
        if t in ('START', 'END'):
            self.shape = self.canvas.create_oval(x0, y0, x1, y1,
                                                 fill='lightgrey', width=2)
        elif t == 'BRANCH':
            pts = [cx, y0, x1, cy, cx, y1, x0, cy]
            self.shape = self.canvas.create_polygon(pts,
                                                    fill='yellow',
                                                    outline='black', width=2)
        elif t == 'WHILE':
            pts = [cx, y0, x1, cy, cx, y1, x0, cy]
            self.shape = self.canvas.create_polygon(pts,
                                                    fill='lightblue',
                                                    outline='black', width=2)
        elif t == 'MERGE':
        
            self.shape = self.canvas.create_rectangle(x0, y0, x1, y1, outline='', fill='')
        elif t == 'FOR':
            # шестиугольник: верхняя и нижняя «срезы»
            dx = self.WIDTH * 0.2   
            pts = [
                x0 + dx, y0,       # верхний левый
                x1 - dx, y0,       # верхний правый
                x1,      cy,       # правый средний
                x1 - dx, y1,       # нижний правый
                x0 + dx, y1,       # нижний левый
                x0,      cy        # левый средний
            ]
            self.shape = self.canvas.create_polygon(
                pts, fill='lightblue', outline='black', width=2
            )
        elif t in ('INPUT','OUTPUT'):
            # 1) рисуем параллелограмм
            skew = self.WIDTH * 0.2
            fill = 'lightgreen' if t=='INPUT' else 'lightpink'
            pts = [
                x0 + skew, y0,
                x1,        y0,
                x1 - skew, y1,
                x0,        y1
            ]
            self.shape = self.canvas.create_polygon(
                pts, fill=fill, outline='black', width=2
            )



        else:
            fill = 'lightgrey'
            self.shape = self.canvas.create_rectangle(x0, y0, x1, y1,
                                                      fill=fill, width=2)

        # === Текст ===
        if t != 'MERGE':
            label = self.model.content or self.model.type
            self.text_id = self.canvas.create_text(cx, cy, text=label)
            self.items += [self.shape, self.text_id]
        else:
            self.items.append(self.shape)

        # === Порты ===
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
            dx = self.WIDTH * 0.06  
            dy = self.HEIGHT * 0.06
            if port.name == 'in1':
                return cx - dx, cy - dy
            if port.name == 'in2':
                return cx + dx, cy - dy
            if port.port_type == 'out':
                return cx, cy + dy

        return cx, cy

    def bind(self):
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

        # Считаем смещение относительно центра текущего узла
        dx = real_x - (self.x + self.WIDTH/2)
        dy = real_y - (self.y + self.HEIGHT/2)

        # Сохраняем новые координаты узла
        self.x += dx
        self.y += dy

        # Сдвигаем все его графические элементы
        for it in self.items:
            self.canvas.move(it, dx, dy)

        # Обновляем все соединения, которые к нему привязаны
        self.app.update_connections(self)


    def on_double_click(self, event):

        if self.model.type in ('INPUT','OUTPUT'):
            new = simpledialog.askstring(
            "Изменение текста", "Введите переменные через пробел:",
            initialvalue=self.model.content
        )
        else:
           new = simpledialog.askstring(
           "Изменение текста", "Введите текст:",
            initialvalue=self.model.content
            ) 

        if new is not None:
            self.model.content=new.strip()
            self.canvas.itemconfig(self.text_id, text=self.model.content)

    def on_right_click(self, event):
        if messagebox.askyesno("Удаление блока", f"Вы действительно хотите удалить блок {self.model.id}?"):
            self.app.delete_node(self)

    def on_port_click(self, event):
        cid = self.canvas.find_withtag("current")[0]
        port = self.port_items[cid]
        self.app.handle_port_click(self, port)

    

    def draw_connection(self, sp, du, dp, route=None):
        """
        Рисует соединение из порта sp (source port) в порт dp (destination port).
        Если route=='loop', рисует L‑образную петлю;
        если route=='default', рисует обычное G‑образное соединение;
        если route is None — определяет автоматически.
        """
        # Автовыбор маршрута, если он не передан
        if route == 'loop':
            is_loop = True
        elif route == 'default':
            is_loop = False
        else:
            # автоматическая детекция петли
            is_loop = (
                du.model.type in ('FOR', 'WHILE')
                and sp.name == 'out'
                and dp.name == 'in_back'
            )

        # вызываем нужный метод и сохраняем результат
        if is_loop:
            line = self._create_loop_line(sp, du, dp)
            actual_route = 'loop'
        else:
            line = self._create_default_line(sp, du, dp)
            actual_route = 'default'

        # сохраняем в список соединений приложения
        self.app.connections.append({
            'line':  line,
            'src':   (self, sp),
            'dst':   (du, dp),
            'route': actual_route
        })
        return line

    def _create_default_line(self, sp, du, dp):
        """
        Обычная «G‑образная» линия: вниз, затем вправо, затем вниз до цели.
        """
        x1, y1 = self.port_position(sp)
        x2, y2 = du.port_position(dp)
        ym = (y1 + y2) / 2

        return self.canvas.create_line(
            x1, y1,
            x1, ym,
            x2, ym,
            x2, y2,
            arrow='last',
            width=2
        )

    def _create_loop_line(self, sp, du, dp):
        """
        L‑образная петля: из тела вниз, влево, вверх, вправо к цели.
        """
        x1, y1 = self.port_position(sp)
        x2, y2 = du.port_position(dp)

        # 0) точка выхода из тела
        pt0 = (x1, y1)
        # 1) вниз от тела
        pt1 = (x1, y1 + self.LOOP_DOWN)
        # 2) влево
        pt2 = (pt1[0] - self.LOOP_DX, pt1[1])
        # 3) вниз до чуть выше порта
        pt3 = (pt2[0], y2)
        # 4) вправо до небольшого отступа от входного порта
        entry_x = x2 + self.ENTRY_OFFSET
        pt4 = (entry_x, pt3[1])
        # 5) вниз до уровня порта
        pt5 = (entry_x, y2)
        # 6) влево к самому порту
        pt6 = (x2, y2)

        pts = [pt0, pt1, pt2, pt3, pt4, pt5, pt6]
        flat = [coord for pt in pts for coord in pt]
        return self.canvas.create_line(
            *flat,
            smooth=False,
            arrow='last',
            width=2
        )
    
    def _redraw_loop(self, conn):
        sp = conn['src'][1]
        du, dp = conn['dst']
        x1, y1 = self.port_position(sp)
        x2, y2 = du.port_position(dp)

        pt0 = (x1, y1)
        pt1 = (x1, y1 + self.LOOP_DOWN)
        pt2 = (pt1[0] - self.LOOP_DX, pt1[1])
        pt3 = (pt2[0], y2)
        entry_x = x2 + self.ENTRY_OFFSET
        pt4 = (entry_x, pt3[1])
        pt5 = (entry_x, y2)
        pt6 = (x2, y2)

        pts = [pt0, pt1, pt2, pt3, pt4, pt5, pt6]
        flat = [c for pt in pts for c in pt]
        self.canvas.coords(conn['line'], *flat)

    def _redraw_default(self, conn):
        sp = conn['src'][1]; du, dp = conn['dst']
        x1,y1 = self.port_position(sp)
        x2,y2 = du.port_position(dp)
        ym = (y1+y2)/2
        self.canvas.coords(conn['line'],
                           x1,y1, x1,ym, x2,ym, x2,y2)


    
            
    def on_delete(self):
        for it in self.items: self.canvas.delete(it)