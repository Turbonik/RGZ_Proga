import tkinter as tk
import os, re
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk  # <-- Pillow
from GraphModel import GraphModel
import DiagramIO
from NodeUI import NodeUI
from NodeModel import NodeModel

class DiagramApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Конвертер блок-схем в программный код')
        self.io = DiagramIO.DiagramIo(self)

        # === Меню Файл ===
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label='Сохранить схему...', command=self.io.save_dialog)
        file_menu.add_command(label='Загрузить схему...', command=self.io.load_dialog)
        file_menu.add_separator()
        file_menu.add_command(label='Генерация Python кода...', command=self.generate_code)
        menu_bar.add_cascade(label='Файл', menu=file_menu)
        self.root.config(menu=menu_bar)
        
        # === Загрузка иконок с ресайзом в папке icons ===
        self.btn_images = {}
        icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
        target_size = (48, 24)  # желаемый размер иконок

        types = ['START','INPUT','OUTPUT','ACTION','BRANCH','FOR','WHILE', 'END']
        for t in types:
            path = os.path.join(icons_dir, f"{t}.png")
            if os.path.isfile(path):
                img = Image.open(path)
                img = img.resize(target_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.btn_images[t] = photo
            else:
                self.btn_images[t] = None
   
        self.btn_images['MERGE'] = None

        # === Создание toolbar с кнопками «иконка + текст» ===
        toolbar = tk.Frame(self.root)
        toolbar.pack(side='left', fill='y', padx=5, pady=5)
        tk.Label(toolbar, text='Блоки:', font=('Arial', 14, 'bold'), pady=10).pack()

        blocks = [
            ('START',  'Начало / конец'),
            ('INPUT',  'Блок ввода'),
            ('OUTPUT', 'Блок вывода'),
            ('ACTION', 'Блок действия'),
            ('BRANCH', 'Блок ветвления'),
            ('FOR',    'Цикл for'),
            ('WHILE',  'Цикл while'),
            ('END',    'Блок конца'),
            ('MERGE',  'Слияние ветвей'),
        ]

        for t, tooltip in blocks:
            img = self.btn_images.get(t)
            if img:
                btn = tk.Button(
                    toolbar,
                    text=tooltip,
                    image=img,
                    compound='left',
                    padx=5,
                    anchor='w',
                    command=lambda t=t: self.create_node(t)
                )
                btn.image = img  # держим ссылку
            else:
                btn = tk.Button(
                    toolbar,
                    text=tooltip,
                    anchor='w',
                    padx=60,
                    command=lambda t=t: self.create_node(t)
                )
            btn.pack(fill='x', pady=2)

        # === Генерация кода ===
        lbl_code = tk.Label(toolbar,
               text='Генерация кода:',
               font=('Arial', 14, 'bold'),
               pady=10)
        lbl_code.pack()
        tk.Button(
            toolbar,
            text='Генерация кода',
            command=self.generate_code
        ).pack(fill='x', pady=10)

            # --- Кнопка очистки холста ---
        tk.Button(
            toolbar,
            text='Очистить холст',
            fg='red',
            command=self.clear_canvas
        ).pack(fill='x', pady=(20,2))

        # === Canvas + Scrollbars справа ===
        container = tk.Frame(self.root)
        container.pack(side='right', fill='both', expand=True)
        vsb = tk.Scrollbar(container, orient='vertical')
        hsb = tk.Scrollbar(container, orient='horizontal')
        self.canvas = tk.Canvas(
            container, width=900, height=600, bg='white',
            yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )
        vsb.config(command=self.canvas.yview)
        hsb.config(command=self.canvas.xview)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.config(scrollregion=(0, 0, 900, 3000))

        # Модель и хранилища
        self.graph = GraphModel()
        self.nodes_ui = []
        self.selected = None
        self.connections_ui = []

    def clear_canvas(self):
            # Удаляем все элементы на canvas и сбрасываем модели
            self.canvas.delete('all')
            self.nodes_ui.clear()
            self.connections_ui.clear()
            self.graph.nodes.clear()

    def create_node(self, ntype):
        # Запрет на более чем один START и один END
        if ntype == 'START' and self.graph.find_start():
            messagebox.showerror("Нельзя создать", "Блок START уже существует")
            return
        if ntype == 'END':
            # ищем существующий END
            if any(n.type == 'END' for n in self.graph.nodes):
                messagebox.showerror("Нельзя создать", "Блок END уже существует")
                return

        # кладём в центр текущей видимой области
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        view_x, view_y = self.canvas.canvasx(0), self.canvas.canvasy(0)
        x = view_x + (w  - NodeUI.WIDTH )/2
        y = view_y + (h - NodeUI.HEIGHT)/2

        m = NodeModel(f'n{len(self.graph.nodes)}', ntype)
        self.graph.add_node(m)
        ui = NodeUI(self.canvas, m, x, y, self)
        self.nodes_ui.append(ui)

    def delete_node(self, ui):
        # --- 1) удаляем все соединения, в которых участвует ui ---
        for conn in self.connections_ui[:]:  
            if ui in (conn.src_ui, conn.dst_ui):
                conn.destroy()            
                self.connections_ui.remove(conn)

                # сбрасываем связи в модели
                conn.sp.connection = None
                conn.dp.connection = None

        # --- 2) удаляем сам узел ---
        ui.on_delete()
        self.nodes_ui.remove(ui)
        self.graph.remove_node(ui.model)

    def handle_port_click(self, ui, port):
        if not self.selected:
            # запоминаем первую точку
            self.selected = (ui, port)
            cid = next(k for k,v in ui.port_items.items() if v == port)
            self.canvas.itemconfig(cid, fill='red')
        else:
            su, sp = self.selected
            du, dp = ui, port

            # сброс выделения
            cid = next(k for k,v in su.port_items.items() if v == sp)
            self.canvas.itemconfig(cid, fill='black')
            self.selected = None

            # Запрет на объединение ветвей разных условий
            if dp.parent.type == 'MERGE':
                # Проверка соответствия порта
                if sp.name == 'out_true' and dp.name != 'in2':
                    messagebox.showerror("Ошибка", "Выход True соединяется с правым портом")
                    return
                if sp.name == 'out_false' and dp.name != 'in1':
                    messagebox.showerror("Ошибка", "Выход False соединяется с левым портом ")
                    return

            # проверяем уникальность соединения портов
            if su is du and sp is dp:
                messagebox.showerror("Нельзя соединить", "Нельзя соединить порт сам с собой")
                return
            if su is du:
                messagebox.showerror("Нельзя соединить", "Нельзя соединить разные порты одного блока")
                return
            if dp.port_type == 'in' and dp.connection is not None:
                messagebox.showerror("Нельзя соединить", "Входной порт уже используется")
                return
            if sp.port_type == 'out' and sp.connection is not None:
                messagebox.showerror("Нельзя соединить", "Исходящий порт уже используется")
                return
            # проверка направления
            if sp.port_type=='out' and dp.port_type=='in':
                sp.connection = dp
                dp.connection = sp
                su.draw_connection(sp, du, dp)
            else:
                messagebox.showerror("Неправильное соединение", "Можно только out → in")
            
            

    def update_connections(self, moved_ui):
        # self.connections_ui — список ConnectionUI
        for conn in self.connections_ui:
            if moved_ui in (conn.src_ui, conn.dst_ui):
                conn.refresh_endpoints()
    
    

    def generate_code(self):
        start=self.graph.find_start()
        if not start: 
            messagebox.showerror('Error','Отсутствует блок начала')
            return
        for n in self.graph.nodes:
            for p in n.ports:
                if p.port_type=='in' and p.connection is None and n.type!='START': messagebox.showerror('Error',f'Порт{n.id} без соединения'); return
                if p.port_type=='out' and p.connection is None and n.type!='END': messagebox.showerror('Error',f'Порт {n.id} без соединения'); return
        code=['def main():']
        def next_node(n): p=next((pp for pp in n.ports if pp.port_type=='out'),None); return p.connection.parent if p and p.connection else None
        def find_merge(tn,fn):
            seen=set(); cur=tn
            while cur: 
                seen.add(cur.id)
                if cur.type in ('MERGE','END'): break
                cur=next_node(cur)
            cur=fn
            while cur and cur.id not in seen:
                if cur.type in ('MERGE','END'): break
                cur=next_node(cur)
            return cur if cur and cur.type=='MERGE' else None
        
        def save_code():
        # открываем диалог сохранения
            fn = filedialog.asksaveasfilename(
                title="Сохранить код как…",
                defaultextension=".py",
                filetypes=[("Python files", "*.py")]
            )
            if not fn:
                return
            try:
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write(txt.get('1.0', 'end-1c'))
                messagebox.showinfo("Успех", f"Код сохранён в {fn}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")

        def process_path(sn,stop,indent):
            cur=sn
            while cur and cur!=stop:
                pad='    '*indent
                tp=cur.type
                if tp=='ACTION': 
                    code.append(f"{pad}{(cur.content or 'pass').strip()}")
                    cur=next_node(cur)
                elif tp == 'INPUT':
                    # Разбираем список имён
                    vars_ = cur.content.split()
                    # Проверка: хотя бы одно имя
                    if not vars_:
                        messagebox.showerror('Error', f'Блок {cur.id}: не указаны переменные для INPUT')
                        return
                    # Проверка каждого имени: допустимый Python-идентификатор
                    identifier_pattern = re.compile(r'^[A-Za-z_]\w*$')
                    for v in vars_:
                        if not identifier_pattern.match(v):
                            messagebox.showerror('Error',
                                f'Блок {cur.id}: недопустимое имя переменной "{v}"\n'
                                'Имя должно начинаться с буквы или подчеркивания\n'
                                'и содержать только буквы, цифры и подчеркивание.'
                            )
                            return
                    # Генерируем по одной строке на каждую переменную
                    for v in vars_:
                        code.append(f"{pad}{v} = input()")
                    cur = next_node(cur)

                elif tp == 'OUTPUT':
                    line = f"print({cur.content})"
                    code.append(pad + line)
                    cur = next_node(cur)

                elif tp=='BRANCH':
                    cond=cur.content.strip() or 'condition'; t=next(p for p in cur.ports if p.name=='out_true').connection.parent
                    f=next(p for p in cur.ports if p.name=='out_false').connection.parent; m=find_merge(t,f)
                    code.append(f"{pad}if {cond}:"); process_path(t,m,indent+1)
                    code.append(f"{pad}else:"); process_path(f,m,indent+1); cur=m
                elif tp=='FOR':
                    it=cur.content.strip() or 'item in iterable'; code.append(f"{pad}for {it}:")
                    b=next(p for p in cur.ports if p.name=='out_body').connection.parent
                    e=next(p for p in cur.ports if p.name=='out_end').connection.parent
                    process_path(b,cur,indent+1); cur=e
                elif tp == 'WHILE':
                    cond = cur.content.strip() or 'condition'
                    # узел тела
                    body_node = next(p for p in cur.ports if p.name=='out_body').connection.parent
                    # узел выхода из цикла
                    end_node  = next(p for p in cur.ports if p.name=='out_end').connection.parent

                    # Добавляем строку заголовка цикла
                    code.append(f"{pad}while {cond}:")

                    # Обходим тело до самого заголовка (stop = cur)
                    process_path(body_node, cur, indent+1)

                    # После того, как тело отработало и мы «вернулись» к заголовку,
                    # повторяется проверка: если условие ложно, выходим
                    cur = end_node

                else: cur=next_node(cur)
            return cur
        
        cursor=next_node(start); process_path(cursor,None,1)
        code+=['',"if __name__=='__main__':",'    main()']
        win=tk.Toplevel(self.root)
        win.title('Сгенерированный python код')
        txt=tk.Text(win,wrap='none')
        txt.insert('1.0','\n'.join(code))
        txt.pack(fill='both',expand=True)
        
        btn_save = tk.Button(win, text='Сохранить .py', command=save_code)
        btn_save.pack(pady=5)
    

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    DiagramApp().run()
