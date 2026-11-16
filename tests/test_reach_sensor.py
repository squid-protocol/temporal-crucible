import sqlite3, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools" / "sensor"))
import reach_sensor as R

def make(tmp):
    (tmp/"a").mkdir(); (tmp/"b").mkdir()
    (tmp/"a/x.h").write_text("int f(void);"); (tmp/"b/x.h").write_text("int g(void);")
    (tmp/"a/one.c").write_text('#include "x.h"\nint f(void){return 1;}'); (tmp/"b/two.c").write_text('#include "x.h"\n#include <stdio.h>\nint g(void){return f();}')
    (tmp/"b/three.c").write_text('#include "a/x.h"\nvoid h(void){g();}')
    db = tmp/"s.db"; c = sqlite3.connect(db)
    c.executescript("""create table file_data(id integer primary key,file_path text,language text,function_count int);
    create table function_data(id integer primary key,file_id int,func_name text,is_public int,loc int);
    create table fcall_data(src_func_id int,src_file_id int,dst_func_id int,dst_file_id int);
    insert into file_data values(1,'a/x.h','c',0),(2,'b/x.h','c',0),(3,'a/one.c','c',1),(4,'b/two.c','c',1),(5,'b/three.c','c',1),(6,'README','text',0);
    insert into function_data values(10,3,'f',1,2),(11,4,'g',1,2),(12,5,'h',1,2);
    insert into fcall_data values(11,4,10,3),(12,5,11,4),(12,5,10,3);""")
    c.commit(); return str(db)

def test_reach(tmp_path):
    out = R.build(make(tmp_path), tmp_path); rows = {r["path"]: r for r in out["rows"]}
    assert rows["a/one.c"]["reach_files"] == 2 and rows["a/one.c"]["caller_functions"] == 2
    assert rows["b/two.c"]["reach_files"] == 1 and rows["b/two.c"]["one_hop_out"] == 0
    assert rows["a/one.c"]["one_hop_out"] == 1
    assert rows["a/x.h"]["reach_files"] == 2 and rows["b/x.h"]["reach_files"] == 1   # same-named headers stay separate
    assert [n["path"] for n in out["not_measured"]] == ["README"]
    assert out["public_functions"][0]["function"] == "f" and out["public_functions"][0]["called_from_files"] == 2

def test_report_mentions_limits(tmp_path):
    assert "lower bounds" in R.report(R.build(make(tmp_path), tmp_path))
