import tkinter as tk
from tkinter import filedialog, messagebox
from GraphModel import GraphModel
from NodeModel import NodeModel
from NodeUI import NodeUI
import DiagramIO

class DiagramApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Конвертер блок-схем в программный код')
        self.io = DiagramIO.DiagramIo(self)
        
        # === Toolbar слева ===
        toolbar = tk.Frame(self.root)
        toolbar.pack(side='left', fill='y', padx=5, pady=5)

        lbl = tk.Label(toolbar,
               text='Блоки:',
               font=('Arial', 14, 'bold'),    
               pady=10)                     
        lbl.pack()
        
        texts = [('START', 'Блок старта'), ('INPUT', 'Блок Ввода'), ('OUTPUT', 'Блок Вывода'),
                  ('ACTION', 'Блок действия'), ('BRANCH', 'Блок ветвления'),
                  ('FOR', 'Блок цикла for'), ('WHILE', 'Блок цикла while'), ('MERGE', 'Слияние ветвей'),
                    ('END', 'Блок конца')]
        
        for t in texts:
            btn = tk.Button(toolbar, text=t[1], command=lambda t = t[0]: self.create_node(t))
            btn.pack(fill='x', pady=2)
        
        lbl = tk.Label(toolbar,
               text='Генерация кода:',
               font=('Arial', 14, 'bold'),    
               pady=10)                     
        lbl.pack()

        tk.Button(toolbar, text='Генерация кода', command=self.generate_code).pack(fill='x', pady=10)

        lbl = tk.Label(toolbar,
               text='Сохранение/Загрузка:',
               font=('Arial', 14, 'bold'),    
               pady=10)                     
        lbl.pack()

        tk.Button(toolbar, text='Сохранить блок-схему', command=self.io.save_dialog).pack(fill='x')
        tk.Button(toolbar, text='Загрузить блок-схему', command=self.io.load_dialog).pack(fill='x')
       
        # === Canvas + Scrollbars справа ===
        container = tk.Frame(self.root)
        container.pack(side='right', fill='both', expand=True)

        vsb = tk.Scrollbar(container, orient='vertical')
        hsb = tk.Scrollbar(container, orient='horizontal')
        self.canvas = tk.Canvas(container, width=900, height=600,
                                bg='white',
                                yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set)
        vsb.config(command=self.canvas.yview)
        hsb.config(command=self.canvas.xview)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.canvas.pack(side='left', fill='both', expand=True)

        # === Фиксированный холст ===
        total_height = 3000
        total_width  = 900
        self.canvas.config(scrollregion=(0, 0, total_width, total_height))

        # Модель и хранилки
        self.graph = GraphModel()
        self.nodes_ui = []
        self.selected = None
        self.connections = []  # список dict{'line','src':(ui,p),'dst':(ui,p)}

    def create_node(self, ntype):
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
        # удаляем все соединения, в которых участвует ui
        for conn in self.connections[:]:
            s_ui, _ = conn['src']
            d_ui, _ = conn['dst']
            if ui in (s_ui, d_ui):
                # сбросим связи в моделях
                conn['src'][1].connection = None
                conn['dst'][1].connection = None
                self.canvas.delete(conn['line'])
                self.connections.remove(conn)
        # удаляем сам узел
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

            # порт сам в себя?
            if su is du and sp is dp:
                messagebox.showerror("Нельзя соединить", "Нельзя соединить порт сам с собой")
            # два разных порта одного узла?
            elif su is du:
                messagebox.showerror("Нельзя соединить", "Нельзя соединить разные порты одного блока")
            # проверяем направления
            elif sp.port_type=='out' and dp.port_type=='in':
                # фиксируем связь в моделях
                sp.connection = dp
                dp.connection = sp
                # рисуем с учётом всех специальных обходов
                su.draw_connection(sp, du, dp)
            else:
                messagebox.showerror("Неправильное соединение", "Можно только out → in")

            # сбрасываем выделение
            cid = next(k for k,v in su.port_items.items() if v == sp)
            self.canvas.itemconfig(cid, fill='black')
            self.selected = None

    def update_connections(self, moved_ui):
        
        for conn in self.connections:
            su, sp = conn['src']
            du, dp = conn['dst']
            if moved_ui not in (su, du):
                continue

            if conn['route'] == 'loop':
                su._redraw_loop(conn)
            else:
                su._redraw_default(conn)
    
    

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
                    # если content = "x y z", генерим "x, y, z = input().split()"
                    vars_ = cur.content.split()
                    if len(vars_) > 1:
                        line = f"{', '.join(vars_)} = input()"
                    else:
                        line = f"{vars_[0]} = input()"
                    code.append(pad + line)
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
