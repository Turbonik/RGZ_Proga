from tkinter import simpledialog, messagebox
import tkinter.font as tkfont

class NodeUI:
    # Базовые размеры и отступы
    MIN_WIDTH      = 140
    MIN_HEIGHT     = 70

    WIDTH = MIN_WIDTH
    HEIGHT = MIN_HEIGHT
    PADDING_X      = 20
    PADDING_Y      = 20

    # Параметры для циклов (петли)
    LOOP_DX        = 80
    LOOP_DOWN      = 40
    ENTRY_OFFSET   = -10

    # Ограничения на вводимый текст
    max_char_line  = 15
    max_char       = 50

    def __init__(self, canvas, model, x, y, app):
        self.canvas     = canvas
        self.model      = model
        self.app        = app
        self.x, self.y  = x, y
        self.items      = []       # все графические элементы узла
        self.port_items = {}       # mapping canvas_id -> PortModel
        # Рассчитываем размер и рисуем
        self.__draw()

    def __draw(self):
        # Подогнать размер блока под текст
        self._adjust_size_to_text()
        # Удалить предыдущие элементы
        self.__clear_previous()
        # Нарисовать форму и текст (специализированно для BRANCH)
        if self.model.type == 'BRANCH':
            self.__draw_branch()
        else:
            self.__draw_shape()
            self.__draw_text()
        # Нарисовать порты
        self.__draw_ports()
        # Привязать события
        self.__bind_events()

    def _adjust_size_to_text(self):
        """Устанавливает WIDTH и HEIGHT в зависимости от содержимого."""
        label = self.model.content or self.model.type
        lines = label.split('\n')
        font = tkfont.Font()
        text_width  = max(font.measure(line) for line in lines)
        text_height = font.metrics("linespace") * len(lines)
        self.WIDTH  = max(self.MIN_WIDTH,  text_width  + self.PADDING_X)
        self.HEIGHT = max(self.MIN_HEIGHT, text_height + self.PADDING_Y)

    def __clear_previous(self):
        """Удаляет все ранее отрисованные элементы."""
        for item in self.items:
            self.canvas.delete(item)
        self.items.clear()
        self.port_items.clear()

    def __draw_shape(self):
        """Рисует форму узла (без текста)."""
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.WIDTH,  y0 + self.HEIGHT
        t = self.model.type
        if t in ('START', 'END'):
            shape_id = self.canvas.create_oval(x0, y0, x1, y1, fill='lightgrey', width=2)
        elif t == 'MERGE':
            shape_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline='', fill='')
        elif t == 'WHILE':
            cx, cy = (x0 + x1)/2, (y0 + y1)/2
            pts = [cx, y0, x1, cy, cx, y1, x0, cy]
            shape_id = self.canvas.create_polygon(pts, fill='lightblue', outline='black', width=2)
        elif t == 'FOR':
            cx, cy = (x0 + x1)/2, (y0 + y1)/2
            dx = self.WIDTH * 0.2
            pts = [x0+dx, y0, x1-dx, y0, x1, cy, x1-dx, y1, x0+dx, y1, x0, cy]
            shape_id = self.canvas.create_polygon(pts, fill='lightblue', outline='black', width=2)
        elif t in ('INPUT', 'OUTPUT'):
            skew = self.WIDTH * 0.2
            fill = 'lightgreen' if t=='INPUT' else 'lightpink'
            pts = [x0+skew, y0, x1, y0, x1-skew, y1, x0, y1]
            shape_id = self.canvas.create_polygon(pts, fill=fill, outline='black', width=2)
        else:
            shape_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill='lightgrey', width=2)
        self.items.append(shape_id)
        self.shape = shape_id

    def __draw_text(self):
        """Рисует центральный текст для всех типов, кроме MERGE."""
        if self.model.type != 'MERGE':
            cx = self.x + self.WIDTH/2
            cy = self.y + self.HEIGHT/2
            label = self.model.content or self.model.type
            text_id = self.canvas.create_text(cx, cy, text=label)
            self.items.append(text_id)
            self.text_id = text_id

    def __draw_branch(self):
        """Рисует ромб ветвления вместе с текстом и метками 0/1."""
        x0, y0 = self.x, self.y
        x1, y1 = x0 + self.WIDTH, y0 + self.HEIGHT
        cx, cy = (x0 + x1)/2, (y0 + y1)/2
        # ромб
        pts = [cx, y0, x1, cy, cx, y1, x0, cy]
        shape_id = self.canvas.create_polygon(pts, fill='yellow', outline='black', width=2)
        self.items.append(shape_id)
        self.shape = shape_id
        # текст условия
        label = self.model.content or self.model.type
        text_id = self.canvas.create_text(cx, cy, text=label)
        self.items.append(text_id)
        self.text_id = text_id
        # метки 0/1
        w, h = self.WIDTH, self.HEIGHT
        label_y  = y0 + h * 0.10
        label_x0 = x0 + w * 0.25
        label_x1 = x0 + w * 0.75
        zero_id = self.canvas.create_text(label_x0, label_y, text='0', font=('Arial', 10, 'bold'))
        one_id  = self.canvas.create_text(label_x1, label_y, text='1', font=('Arial', 10, 'bold'))
        self.items.extend([zero_id, one_id])

    def __draw_ports(self):
        """Рисует порты (маленькие кружки) для подключения стрелок."""
        for p in self.model.ports:
            px, py = self.port_position(p)
            cid = self.canvas.create_oval(px-5, py-5, px+5, py+5, fill='black')
            self.port_items[cid] = p
            self.items.append(cid)

    def port_position(self, port):
        """Вычисляет координаты центра порта в зависимости от типа узла."""
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
            if port.port_type=='in':      return cx, y0
            if port.name=='out_true':     return x1, cy
            if port.name=='out_false':    return x0, cy
        if t in ('INPUT','OUTPUT'):
            return (cx, y0) if port.port_type=='in' else (cx, y1)
        if t in ('FOR','WHILE'):
            if port.name=='in':           return cx,   y0
            if port.name=='in_back':      return x0,   cy
            if port.name=='out_body':     return cx,   y1
            if port.name=='out_end':      return x1,   cy
        if t == 'MERGE':
            dx = self.WIDTH * 0.08
            dy = self.HEIGHT * 0.08
            if port.name == 'in1':       return cx - dx, cy - dy
            if port.name == 'in2':       return cx + dx, cy - dy
            if port.port_type == 'out':  return cx,      cy + dy
        return cx, cy

    def __bind_events(self):
        """Привязывает события мыши к графическим элементам узла."""
        editable = ('ACTION','BRANCH','FOR','WHILE','OUTPUT','INPUT')
        # перетаскивание и контекстное меню для shape и текста
        for item in (self.shape, getattr(self, 'text_id', None)):
            if item is None:
                continue
            self.canvas.tag_bind(item, '<Button1-Motion>', self.on_drag)
            self.canvas.tag_bind(item, '<Button-3>',         self.on_right_click)
            if self.model.type in editable:
                self.canvas.tag_bind(item, '<Double-1>',    self.on_double_click)
        # клик по портам
        for cid in self.port_items:
            self.canvas.tag_bind(cid, '<Button-1>', self.on_port_click)

    def on_drag(self, event):
        """Обработка перетаскивания узла."""
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
        """Редактирование текста блока."""
        prompt = "Введите переменные через пробел:" if self.model.type == 'INPUT' else "Введите текст:"
        new = simpledialog.askstring("Изменение текста", prompt, initialvalue=self.model.content)
        if new is not None:
            if len(new) > self.max_char:
                messagebox.showerror('Error', f'Размер текста не может превышать {self.max_char} символов')
                return
            # разбивка на строки по max_char_line
            if len(new) > self.max_char_line:
                parts = [new[i:i+self.max_char_line] for i in range(0, len(new), self.max_char_line)]
                _new = "\n".join(parts)
            else:
                _new = new
            self.model.content = _new.strip()
            # после изменения текста пересоздать всю графику
            self.__draw()

    def on_right_click(self, event):
        """Контекстное меню: удаление блока."""
        if messagebox.askyesno("Удаление блока", f"Удалить блок {self.model.id}?"):
            self.app.delete_node(self)

    def on_port_click(self, event):
        """Обработка клика по порту — начало/завершение соединения."""
        cid  = self.canvas.find_withtag("current")[0]
        port = self.port_items[cid]
        self.app.handle_port_click(self, port)

    def on_delete(self):
        """Полное удаление всех графических элементов узла."""
        for it in self.items:
            self.canvas.delete(it)
