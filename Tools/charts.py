import math

def plot_chart(title,x_values,y_values,chart_type="line",x_label="",y_label=""):
    if not isinstance(x_values,list) or not isinstance(y_values,list) or not x_values or len(x_values)!=len(y_values) or len(x_values)>100: raise ValueError("Fournis 1 à 100 points, avec autant de valeurs X que Y.")
    if chart_type not in {"line","bar"}: raise ValueError("chart_type doit être line ou bar.")
    vals=[]
    for v in y_values:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError("Toutes les valeurs Y doivent être des nombres finis.")
        vals.append(float(v))
    return {"chart":{"title":str(title)[:120],"x_values":[str(v)[:40] for v in x_values],"y_values":vals,"chart_type":chart_type,"x_label":str(x_label)[:80],"y_label":str(y_label)[:80]}}
