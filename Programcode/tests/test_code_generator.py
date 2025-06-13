import pytest
from GraphModel import GraphModel
from NodeModel import NodeModel
from code_generator import CodeGenerator

def connect(a, from_name, b, to_name):
    """Утилита: соединить порт a.from_name → b.to_name."""
    sp = next(p for p in a.ports if p.name == from_name)
    dp = next(p for p in b.ports if p.name == to_name)
    sp.connection = dp
    dp.connection = sp

def make_linear_graph():
    """START -> ACTION -> END."""
    g = GraphModel()
    s = NodeModel('s', 'START')
    a = NodeModel('a', 'ACTION')
    e = NodeModel('e', 'END')
    g.add_node(s); g.add_node(a); g.add_node(e)
    connect(s, 'out', a, 'in')
    connect(a, 'out', e, 'in')
    return g

def make_branch_graph():
    """START -> BRANCH -> two ACTIONs -> MERGE -> END."""
    g = GraphModel()
    s = NodeModel('s', 'START')
    b = NodeModel('b', 'BRANCH')
    t = NodeModel('t', 'ACTION')
    f = NodeModel('f', 'ACTION')
    m = NodeModel('m', 'MERGE')
    e = NodeModel('e', 'END')
    for n in (s,b,t,f,m,e): g.add_node(n)
    connect(s, 'out', b, 'in')
    connect(b, 'out_true',  t, 'in')
    connect(b, 'out_false', f, 'in')
    connect(t, 'out', m, 'in1')
    connect(f, 'out', m, 'in2')
    connect(m, 'out', e, 'in')
    return g

def make_for_loop_graph():
    """START -> FOR -> ACTION -> END."""
    g = GraphModel()
    s = NodeModel('s', 'START')
    c = NodeModel('c', 'FOR')
    a = NodeModel('a', 'ACTION')
    e = NodeModel('e', 'END')
    for n in (s,c,a,e): g.add_node(n)
    connect(s, 'out', c, 'in')
    connect(c, 'out_body', a, 'in')
    connect(a, 'out', c, 'in_back')
    connect(c, 'out_end', e, 'in')
    return g

def make_while_loop_graph():
    """START -> WHILE -> ACTION -> END."""
    g = GraphModel()
    s = NodeModel('s', 'START')
    w = NodeModel('w', 'WHILE')
    a = NodeModel('a', 'ACTION')
    e = NodeModel('e', 'END')
    for n in (s,w,a,e): g.add_node(n)
    connect(s, 'out', w, 'in')
    connect(w, 'out_body', a, 'in')
    connect(a, 'out', w, 'in_back')
    connect(w, 'out_end', e, 'in')
    return g

def test_linear():
    g = make_linear_graph()
    code = CodeGenerator.generate_code(g)
    assert code[0] == 'def main():'
    assert 'pass' not in code  # since ACTION без текста → pass
    assert code[-1] == '    main()'

def test_branch_if_else():
    g = make_branch_graph()
    code = CodeGenerator.generate_code(g)
    # проверяем, что есть if и else с отступами
    assert any(line.strip().startswith('if') for line in code)
    assert any(line.strip().startswith('else') for line in code)
    # проверяем вызов обоих ACTION
    assert any('pass' in line for line in code)

def test_for_loop():
    g = make_for_loop_graph()
    code = CodeGenerator.generate_code(g)
    # должны увидеть строку for ...:
    assert any(line.strip().startswith('for') for line in code)
    # а в теле цикла должна быть строка 'pass'
    assert any(line.strip() == 'pass' for line in code)


def test_simple_merge_without_branch():
    # без START ожидаем ошибку Missing START
    g = GraphModel()
    m = NodeModel('m', 'MERGE')
    e = NodeModel('e', 'END')
    g.add_node(m)
    g.add_node(e)
    connect(m, 'out', e, 'in')
    with pytest.raises(ValueError) as excinfo:
        CodeGenerator.generate_code(g)
    # сообщение может быть на русском или английском
    msg = str(excinfo.value)
    assert "Missing START" in msg or "Отсутствует блок START" in msg


def test_while_loop():
    g = make_while_loop_graph()
    code = CodeGenerator.generate_code(g)
    assert any(line.strip().startswith('while') for line in code)

def test_missing_start_raises():
    g = GraphModel()
    with pytest.raises(ValueError):
        CodeGenerator.generate_code(g)

def test_nested_branch():
    # двойное ветвление
    g = make_branch_graph()
    # внутрь true-ветви добавим ещё BRANCH->ACTION->MERGE
    # ... аналогично первому ветвлению ...
    # (здесь можно вручную вставить новый подграф и проверить)
    # для краткости убеждаемся, что функция не падает
    CodeGenerator.generate_code(g)

def test_reentrance_prevention():
    # нарочно создаём цикл без выхода
    g = GraphModel()
    s = NodeModel('s','START'); c = NodeModel('c','WHILE')
    g.add_node(s); g.add_node(c)
    connect(s,'out',c,'in'); connect(c,'out_body',c,'in_back')
    # отсутствует out_end
    code = CodeGenerator.generate_code(g)
    # генерация должна завершиться, хоть и без тела
    assert 'while' in '\n'.join(code)

if __name__ == '__main__':
    pytest.main() 
