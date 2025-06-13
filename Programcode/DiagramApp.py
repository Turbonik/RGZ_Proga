import tkinter as tk
import os
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk  
from NodeUI import NodeUI
import DiagramIO
from GraphModel import GraphModel
from NodeModel import NodeModel
from DiagramState import DiagramState
from ConnectionUI import ConnectionUI
from code_generator import CodeGenerator

class DiagramApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Конвертер блок-схем в программный код')
        self.diagram_state = DiagramState()
        self.io = DiagramIO.DiagramIo(self)
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
            ('START',  'Блок начала'),
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



    def clear_canvas(self):
        self.canvas.delete('all')
        self.diagram_state.clear()

    def run(self):
        self.root.mainloop()

    def generate_code(self):
        # строим GraphModel
        graph = GraphModel()
        for node_ui in self.diagram_state.nodes_ui:
            graph.add_node(node_ui.model)
        try:
            lines = CodeGenerator.generate_code(graph)
        except ValueError as e:
            messagebox.showerror('Error', str(e))
            return
        # показываем окно с кодом
        win = tk.Toplevel(self.root)
        win.title('Сгенерированный python код')
        txt = tk.Text(win, wrap='none')
        txt.insert('1.0', '\n'.join(lines))
        txt.pack(fill='both', expand=True)
        def save():
            fn = filedialog.asksaveasfilename(
                defaultextension='.py', filetypes=[('Python files','*.py')]
            )
            if fn:
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                messagebox.showinfo('Успех', f'Сохранено в {fn}')
        tk.Button(win, text='Сохранить .py', command=save).pack(pady=5)

if __name__ == '__main__':
    DiagramApp().run()
