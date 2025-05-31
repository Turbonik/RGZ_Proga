import tkinter as tk
import os, re
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk  
from NodeUI import NodeUI
import diagramIO
from GraphModel import GraphModel
from NodeModel import NodeModel
from DiagramState import DiagramState
from ConnectionUI import ConnectionUI
from CodeGenerator import CodeGenerator

class DiagramApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Конвертер блок-схем в программный код')
        self.diagram_state = DiagramState()
        self.io = diagramIO.DiagramIo(self)
        self.__setup_ui()


    def __setup_ui(self):
        self.__create_menu()
        self.__create_toolbar()
        self.__create_canvas()

    def __create_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label='Сохранить схему...', command=self.io.save_dialog)
        file_menu.add_command(label='Загрузить схему...', command=self.io.load_dialog)
        file_menu.add_separator()
        file_menu.add_command(label='Генерация Python кода...', command=self.generate_code)
        menu_bar.add_cascade(label='Файл', menu=file_menu)
        self.root.config(menu=menu_bar)

    def __create_toolbar(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(side='left', fill='y', padx=5, pady=5)
        self.__load_icons()
        self.__create_toolbar_buttons(toolbar)

    def __load_icons(self):
        self.btn_images = {}
        icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
        target_size = (48, 24) 
        types = ['START','INPUT','OUTPUT','ACTION','BRANCH','FOR','WHILE', 'END']
        for t in types:
            path = os.path.join(icons_dir, f"{t}.png")
            if os.path.isfile(path):
                img = Image.open(path).resize(target_size, Image.LANCZOS)
                self.btn_images[t] = ImageTk.PhotoImage(img)
            else:
                self.btn_images[t] = None

    def __create_toolbar_buttons(self, toolbar):
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
            self.__create_toolbar_button(toolbar, t, tooltip)
        self.__create_code_generation_section(toolbar)

    def __create_toolbar_button(self, toolbar, node_type, tooltip):
        img = self.btn_images.get(node_type)
        if img:
            btn = tk.Button(
                toolbar,
                text=tooltip,
                image=img,
                compound='left',
                padx=5,
                anchor='w',
                command=lambda t=node_type: self.create_node(t)
            )
            btn.image = img
        else:
            btn = tk.Button(
                toolbar,
                text=tooltip,
                anchor='w',
                padx=60,
                command=lambda t=node_type: self.create_node(t)
            )
        btn.pack(fill='x', pady=2)

    def __create_code_generation_section(self, toolbar):
        tk.Label(toolbar, text='Генерация кода:', font=('Arial', 14, 'bold'), pady=10).pack()
        tk.Button(toolbar, text='Генерация кода', command=self.generate_code).pack(fill='x', pady=10)
        tk.Button(toolbar, text='Очистить холст', fg='red', command=self.clear_canvas).pack(fill='x', pady=(20,2))

    def __create_canvas(self):
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

    def create_node(self, ntype):
        if self.__is_start_or_end_exists(ntype):
            return
        x, y = self.__get_center_position()
        m = NodeModel(f'n{len(self.diagram_state.nodes_ui)}', ntype)
        ui = NodeUI(self.canvas, m, x, y, self)
        self.diagram_state.add_node(ui)

    def __is_start_or_end_exists(self, ntype):
        if ntype == 'START' and any(n.model.type == 'START' for n in self.diagram_state.nodes_ui):
            messagebox.showerror("Нельзя создать", "Блок START уже существует")
            return True
        if ntype == 'END' and any(n.model.type == 'END' for n in self.diagram_state.nodes_ui):
            messagebox.showerror("Нельзя создать", "Блок END уже существует")
            return True
        return False

    def __get_center_position(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        view_x, view_y = self.canvas.canvasx(0), self.canvas.canvasy(0)
        return (
            view_x + (w - NodeUI.WIDTH) / 2,
            view_y + (h - NodeUI.HEIGHT) / 2
        )

    def delete_node(self, ui):
        connections_to_remove = [
            conn for conn in self.diagram_state.connections_ui
            if ui in (conn.src_ui, conn.dst_ui)
        ]
        for conn in connections_to_remove:
            conn.destroy()
        ui.on_delete()
        self.diagram_state.remove_node(ui)

    def handle_port_click(self, ui, port):
        if not self.diagram_state.selected:
            self.__select_port(ui, port)
        else:
            self.__connect_ports(ui, port)

    def __select_port(self, ui, port):
        self.diagram_state.selected = (ui, port)
        cid = next(k for k, v in ui.port_items.items() if v == port)
        self.canvas.itemconfig(cid, fill='red')

    def __connect_ports(self, ui, port):
        su, sp = self.diagram_state.selected
        du, dp = ui, port
        self.__reset_port_selection(su, sp)
        if self.__validate_connection(su, sp, du, dp):
            sp.connection = dp
            dp.connection = sp
            ConnectionUI(self.canvas, su, sp, du, dp, self)

    def __reset_port_selection(self, ui, port):
        cid = next(k for k, v in ui.port_items.items() if v == port)
        self.canvas.itemconfig(cid, fill='black')
        self.diagram_state.selected = None

    def __validate_connection(self, su, sp, du, dp):
        if su is du:
            if sp is dp:
                messagebox.showerror("Нельзя соединить", "Нельзя соединить порт сам с собой")
            else:
                messagebox.showerror("Нельзя соединить", "Нельзя соединить разные порты одного блока")
            return False
        if dp.connection:
            messagebox.showerror("Нельзя соединить", "Входной порт уже используется")
            return False
        if sp.connection:
            messagebox.showerror("Нельзя соединить", "Исходящий порт уже используется")
            return False
        if not (sp.port_type == 'out' and dp.port_type == 'in'):
            messagebox.showerror("Неправильное соединение", "Можно только out → in")
            return False
        return True

    def update_connections(self, moved_ui):
        for conn in self.diagram_state.connections_ui:
            if moved_ui in (conn.src_ui, conn.dst_ui):
                conn.refresh_endpoints()

    def generate_code(self):
        generator = CodeGenerator(self.diagram_state)
        generator.generate()

    def clear_canvas(self):
        self.canvas.delete('all')
        self.diagram_state.clear()

    def run(self):
        self.root.mainloop()

    def generate_code(self):
        graph = GraphModel()
        for node_ui in self.diagram_state.nodes_ui:
            graph.add_node(node_ui.model)
        
        start = graph.find_start()
        if not start:
            messagebox.showerror('Error','Отсутствует блок начала')
            return

        # Проверяем: нет «незакрытых» портов
        for n in graph.nodes:
            for p in n.ports:
                if p.port_type=='in' and p.connection is None and n.type!='START':
                    messagebox.showerror('Error',f'Порт {n.id} без соединения')
                    return
                if p.port_type=='out' and p.connection is None and n.type!='END':
                    messagebox.showerror('Error',f'Порт {n.id} без соединения')
                    return

        code = ['def main():']

        def next_node(n):
            """
            Возвращает следующий узел «по потоку» для
            одного «исходящего» перехода.
            """
            if n.type in ('FOR', 'WHILE'):
                # у циклов есть порт 'out_end'
                p_end = next((pp for pp in n.ports if pp.name=='out_end'), None)
                if p_end and p_end.connection:
                    return p_end.connection.parent
                else:
                    return None
            else:
                # для всех остальных узлов: обычный первый порт out
                p = next((pp for pp in n.ports if pp.port_type=='out'), None)
                return p.connection.parent if p and p.connection else None

        def find_merge(tn, fn):
            seen = set()
            cur = tn
            # 1) идём по ветке true, собираем во множество id пройденных узлов
            while cur:
                seen.add(cur.id)
                if cur.type in ('MERGE', 'END'):
                    break
                cur = next_node(cur)
            # 2) идём по ветке false, пока не встретим узел из seen или сам MERGE/END
            cur = fn
            while cur and cur.id not in seen:
                if cur.type in ('MERGE', 'END'):
                    break
                cur = next_node(cur)
            return cur if (cur and cur.type=='MERGE') else None

        # Рекурсивно «спускаемся» по диаграмме, генерируя код
        def process_path(sn, stop, indent):
            cur = sn
            while cur and cur != stop:
                pad = '    ' * indent
                tp = cur.type

                if tp == 'ACTION':
                    code.append(f"{pad}{(cur.content or 'pass').strip()}")
                    cur = next_node(cur)

                elif tp == 'INPUT':
                    vars_ = cur.content.split()
                    if not vars_:
                        messagebox.showerror('Error', f'Блок {cur.id}: не указаны переменные для INPUT')
                        return
                    identifier_pattern = re.compile(r'^[A-Za-z_]\w*$')
                    for v in vars_:
                        if not identifier_pattern.match(v):
                            messagebox.showerror(
                                'Error',
                                f'Блок {cur.id}: недопустимое имя переменной \"{v}\"\n'
                                'Имя должно начинаться с буквы или подчеркивания\n'
                                'и содержать только буквы, цифры и подчеркивание.'
                            )
                            return
                    for v in vars_:
                        code.append(f"{pad}{v} = input()")
                    cur = next_node(cur)

                elif tp == 'OUTPUT':
                    line = f"print({cur.content})"
                    code.append(pad + line)
                    cur = next_node(cur)

                elif tp == 'BRANCH':
                    cond = cur.content.strip() or 'condition'
                    t = next(p for p in cur.ports if p.name=='out_true').connection.parent
                    f = next(p for p in cur.ports if p.name=='out_false').connection.parent
                    m = find_merge(t, f)
                    if m is None:
                        messagebox.showerror('Error', f'Не найдена точка MERGE для блока {cur.id}')
                        return
                    code.append(f"{pad}if {cond}:")
                    process_path(t, m, indent+1)
                    code.append(f"{pad}else:")
                    process_path(f, m, indent+1)
                    cur = m

                elif tp == 'FOR':
                    it = cur.content.strip() or 'item in iterable'
                    code.append(f"{pad}for {it}:")
                    b = next(p for p in cur.ports if p.name=='out_body').connection.parent
                    e = next(p for p in cur.ports if p.name=='out_end').connection.parent
                    process_path(b, cur, indent+1)
                    # после выхода из тела – переходим в узел после цикла
                    cur = e

                elif tp == 'WHILE':
                    cond = cur.content.strip() or 'condition'
                    code.append(f"{pad}while {cond}:")
                    body_node = next(p for p in cur.ports if p.name=='out_body').connection.parent
                    end_node  = next(p for p in cur.ports if p.name=='out_end').connection.parent
                    process_path(body_node, cur, indent+1)
                    cur = end_node

                else:
                    cur = next_node(cur)
            return cur

        
        cursor = next_node(start)
        process_path(cursor, None, 1)

        code += ['', "if __name__=='__main__':", '    main()']

        # ---окно с результатом ---
        win = tk.Toplevel(self.root)
        win.title('Сгенерированный python код')
        txt = tk.Text(win, wrap='none')
        txt.insert('1.0', '\n'.join(code))
        txt.pack(fill='both', expand=True)

        def save_code():
            fn = filedialog.asksaveasfilename(
                title="Сохранить код как…",
                defaultextension=".py",
                filetypes=[("Python files", "*.py")]
            )
            if not fn:
                return
            try:
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(code))
                messagebox.showinfo("Успех", f"Код сохранён в {fn}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")

        btn_save = tk.Button(win, text='Сохранить .py', command=save_code)
        btn_save.pack(pady=5)

if __name__ == '__main__':
    DiagramApp().run()
