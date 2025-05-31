import re
from tkinter import messagebox, filedialog
import tkinter as tk

class CodeGenerator:
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