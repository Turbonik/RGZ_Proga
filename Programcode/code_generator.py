# code_generator.py
import re
from GraphModel import GraphModel

class CodeGenerator:
    @staticmethod
    def generate_code(graph: GraphModel) -> list[str]:
        """
        Проверяет связность портов и генерирует Python‑код из графа.
        Бросает ValueError при ошибках.
        """
        # 1. Найти START
        start = graph.find_start()
        if not start:
            raise ValueError("Отсутствует блок START")

        # 2. Валидация портов
        for node in graph.nodes:
            for port in node.ports:
                if (port.port_type == 'in'
                        and port.connection is None
                        and node.type != 'START'
                        and not (node.type in ('FOR','WHILE') and port.name == 'in_back')):
                    raise ValueError(f"Входной порт {node.id}.{port.name} не подключён")
                if (port.port_type == 'out'
                        and port.connection is None
                        and node.type != 'END'
                        and not (node.type in ('FOR','WHILE') and port.name == 'out_end')):
                    raise ValueError(f"Выходной порт {node.id}.{port.name} не подключён")

        # 3. Вспомогательные функции для переходов
        def next_node(n):
            if n.type in ('FOR','WHILE'):
                p_end = next((pp for pp in n.ports if pp.name=='out_end'), None)
                return p_end.connection.parent if p_end and p_end.connection else None
            p = next((pp for pp in n.ports if pp.port_type=='out'), None)
            return p.connection.parent if p and p.connection else None

        def find_merge(tn, fn):
            seen = set()
            cur = tn
            while cur:
                seen.add(cur.id)
                if cur.type in ('MERGE','END'): break
                cur = next_node(cur)
            cur = fn
            while cur and cur.id not in seen:
                if cur.type in ('MERGE','END'): break
                cur = next_node(cur)
            return cur if (cur and cur.type=='MERGE') else None

        # 4. Рекурсивная генерация
        code = ['def main():']

        def process(node, stop, indent, visited=None):
            if visited is None:
                visited = set()
            cur = node

            while cur and cur != stop:
                if cur.id in visited:
                    return
                visited.add(cur.id)

                pad = '    ' * indent
                tp, text = cur.type, cur.content.replace('\n','').strip()

                if tp == 'ACTION':
                    code.append(f"{pad}{text or 'pass'}")
                    cur = next_node(cur)

                elif tp == 'INPUT':
                    vars_ = text.split()
                    if not vars_:
                        raise ValueError(f"Блок {cur.id}: нет переменных")
                    pat = re.compile(r'^[A-Za-z_]\w*$')
                    for v in vars_:
                        if not pat.match(v):
                            raise ValueError(f"Блок {cur.id}: некорректное имя {v}")
                    for v in vars_:
                        code.append(f"{pad}{v} = input()")
                    cur = next_node(cur)

                elif tp == 'OUTPUT':
                    code.append(f"{pad}print({text})")
                    cur = next_node(cur)

                elif tp == 'BRANCH':
                    cond = text or 'condition'
                    true_node  = next(p for p in cur.ports if p.name=='out_true').connection.parent
                    false_node = next(p for p in cur.ports if p.name=='out_false').connection.parent
                    merge_node = find_merge(true_node, false_node)
                    if not merge_node:
                        raise ValueError(f"Блок {cur.id}: нет MERGE")

                    # if ветка
                    code.append(f"{pad}if {cond}:")
                    process(true_node,  merge_node, indent+1, visited.copy())

                    # else ветка: только если там есть действия
                    pre_len = len(code)
                    process(false_node, merge_node, indent+1, visited.copy())
                    if len(code) > pre_len:
                        # если после проверки false ветки появились строки, вставим else перед ними
                        code.insert(pre_len, f"{pad}else:")
                    # продолжаем с merge_node
                    cur = merge_node

                elif tp == 'FOR':
                    itr = text or 'item in iterable'
                    code.append(f"{pad}for {itr}:")
                    body_node = next(p for p in cur.ports if p.name=='out_body').connection.parent
                    end_node  = next(p for p in cur.ports if p.name=='out_end').connection
                    end_node  = end_node.parent if end_node else None

                    process(body_node, cur, indent+1, visited.copy())
                    cur = end_node

                elif tp == 'WHILE':
                    cond = text or 'condition'
                    code.append(f"{pad}while {cond}:")
                    body_node = next(p for p in cur.ports if p.name=='out_body').connection.parent
                    end_node  = next(p for p in cur.ports if p.name=='out_end').connection
                    end_node  = end_node.parent if end_node else None

                    process(body_node, cur, indent+1, visited.copy())
                    cur = end_node

                else:
                    cur = next_node(cur)
            return cur

        first = next_node(start)
        process(first, None, 1)
        code += ['', "if __name__=='__main__':", '    main()']
        return code
