import sqlite3,json
COLS=["complexity","loc","args","struct_branch","struct_linear","struct_args","struct_func_start","struct_class_start","struct_closures","struct_comprehensions","struct_decorators",
 "arch_regex","state_bailout_hits","def_safety","state_danger","arch_io","keyword_density","token_mass","func_fan_in","func_fan_out","func_pagerank","state_flux","state_print_hits"]
out={}
for side in("old","new"):
    c=sqlite3.connect(f"file:gscan/trees/{side}/{side}_galaxy_master.db?mode=ro",uri=True)
    q=f"select f.file_path,u.func_name,"+",".join("u."+x for x in COLS)+" from function_data u join file_data f on f.id=u.file_id"
    n=0
    for row in c.execute(q):
        fp=row[0].replace("\\","/")
        parts=fp.split("/"); 
        if side in parts: parts=parts[parts.index(side)+1:]
        sha10=parts[0]; path="/".join(parts[1:])
        vals=[float(v) if isinstance(v,(int,float)) else 0.0 for v in row[2:]]
        out.setdefault(f"{side}|{sha10}|{path}|{row[1]}",vals); n+=1
    print(side,n)
json.dump({"cols":COLS,"rows":out},open("structure_rows.json","w"))
print(list(out)[:2])
