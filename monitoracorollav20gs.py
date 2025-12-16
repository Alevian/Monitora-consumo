import pandas as pd
import json
import tkinter as tk
from tkinter import filedialog
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import numpy as np

# ==============================================================================
# 1. FUNÇÕES DE LIMPEZA
# ==============================================================================

def selecionar_arquivo():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    caminho = filedialog.askopenfilename(
        title="Selecione o arquivo 'Monitoramento Corolla.csv'",
        filetypes=[("Arquivos CSV", "*.csv")]
    )
    if not caminho:
        print("Cancelado.")
        exit()
    return caminho

def limpar_float(val):
    if pd.isna(val) or str(val).strip() == '': return np.nan
    s = str(val).replace('R$', '').replace(' ', '')
    if '.' in s and ',' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    elif '.' in s: 
        if len(s.split('.')[-1]) == 3: s = s.replace('.', '')
    try:
        f = float(s)
        return f if f > 0 else np.nan
    except: return np.nan

def limpar_float_zero(val):
    res = limpar_float(val)
    return 0.0 if np.isnan(res) else res

def converter_tempo(val):
    if pd.isna(val): return 0.0
    s = str(val).strip()
    try:
        parts = s.split(':')
        if len(parts) >= 2:
            return int(parts[0]) + int(parts[1])/60 + (int(parts[2])/3600 if len(parts)>2 else 0)
    except: pass
    return 0.0

# ==============================================================================
# 2. PROCESSAMENTO
# ==============================================================================

def main():
    caminho = selecionar_arquivo()
    try:
        df = pd.read_csv(caminho, dtype=str)
        if df.shape[1] < 5: df = pd.read_csv(caminho, sep=';', dtype=str)
    except Exception as e:
        print(f"Erro: {e}")
        return

    # 0:Data, 3:Preço, 4:Custo, 5:Litros, 6:Dist, 7:Tempo, 8:Vel, 9:Consumo, 13:Posto
    df['data_dt'] = pd.to_datetime(df.iloc[:, 0], format='%d/%m/%Y', errors='coerce')
    df = df.dropna(subset=['data_dt']).sort_values('data_dt')

    df['dist'] = df.iloc[:, 6].apply(limpar_float_zero)
    df['litros'] = df.iloc[:, 5].apply(limpar_float_zero)
    df['custo'] = df.iloc[:, 4].apply(limpar_float_zero)
    df['vel'] = df.iloc[:, 8].apply(limpar_float)
    df['consumo'] = df.iloc[:, 9].apply(limpar_float)
    df['preco_litro'] = df.iloc[:, 3].apply(limpar_float)
    df['horas'] = df.iloc[:, 7].apply(converter_tempo)
    
    if df.shape[1] > 13: df['posto'] = df.iloc[:, 13].fillna('')
    else: df['posto'] = ''

    df['Ano'] = df['data_dt'].dt.year
    df['Mes'] = df['data_dt'].dt.month
    df['Mes_Nome'] = df['data_dt'].dt.strftime('%B')
    df['Dia'] = df['data_dt'].dt.strftime('%d/%m/%Y')
    
    traducao = {'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril', 'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'}
    df['Mes_Nome'] = df['Mes_Nome'].map(traducao).fillna(df['Mes_Nome'])

    # HIERARQUIA JSON
    dados_hierarquicos = []
    anos = sorted(df['Ano'].unique())
    
    for ano in anos:
        df_ano = df[df['Ano'] == ano]
        a_dist = df_ano['dist'].sum()
        a_custo = df_ano['custo'].sum()
        a_litros = df_ano['litros'].sum()
        a_horas = df_ano['horas'].sum()
        a_vel = df_ano['vel'].mean()
        a_cons = df_ano['consumo'].mean()
        a_custo_km = a_custo / a_dist if a_dist > 0 else 0
        
        dados_hierarquicos.append({
            'tipo': 'ano', 'id': f"y{ano}", 'col1': str(ano),
            'dist': a_dist, 'litros': a_litros, 'custo': a_custo, 'horas': a_horas,
            'vel': 0 if pd.isna(a_vel) else a_vel,
            'consumo': 0 if pd.isna(a_cons) else a_cons,
            'custo_km': a_custo_km, 'abst': len(df_ano)
        })
        
        for mes in sorted(df_ano['Mes'].unique()):
            df_mes = df_ano[df_ano['Mes'] == mes]
            m_dist = df_mes['dist'].sum()
            m_custo = df_mes['custo'].sum()
            m_litros = df_mes['litros'].sum()
            m_horas = df_mes['horas'].sum()
            m_vel = df_mes['vel'].mean()
            m_cons = df_mes['consumo'].mean()
            m_custo_km = m_custo / m_dist if m_dist > 0 else 0
            
            dados_hierarquicos.append({
                'tipo': 'mes', 'pai': f"y{ano}", 'id': f"m{ano}-{mes}",
                'col1': df_mes['Mes_Nome'].iloc[0],
                'dist': m_dist, 'litros': m_litros, 'custo': m_custo, 'horas': m_horas,
                'vel': 0 if pd.isna(m_vel) else m_vel,
                'consumo': 0 if pd.isna(m_cons) else m_cons,
                'custo_km': m_custo_km, 'abst': len(df_mes)
            })
            
            for _, row in df_mes.iterrows():
                d_custo_km = row['custo'] / row['dist'] if row['dist'] > 0 else 0
                d_vel = 0 if pd.isna(row['vel']) else row['vel']
                d_cons = 0 if pd.isna(row['consumo']) else row['consumo']
                
                dados_hierarquicos.append({
                    'tipo': 'detalhe', 'pai': f"m{ano}-{mes}",
                    'col1': f"{row['Dia']} - {row['posto']}",
                    'dist': row['dist'], 'litros': row['litros'], 'custo': row['custo'],
                    'horas': row['horas'], 'vel': d_vel, 'consumo': d_cons,
                    'custo_km': d_custo_km, 'abst': 1
                })

    json_dados = json.dumps(dados_hierarquicos)

    # -------------------------------------------------------------------------
    # GRÁFICOS (AJUSTE VISUAL "SUJEIRA")
    # -------------------------------------------------------------------------
    df_graf = df.groupby(['Ano', 'Mes', 'Mes_Nome']).agg({
        'vel': 'mean', 'consumo': 'mean', 'preco_litro': 'mean'
    }).reset_index()
    df_graf['Periodo'] = pd.to_datetime(df_graf['Ano'].astype(str) + '-' + df_graf['Mes'].astype(str) + '-01')
    df_graf = df_graf.sort_values('Periodo')

    # Configurações de layout limpo
    layout_clean = dict(
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20), # Margem Top maior para o título
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center") # Legenda EM BAIXO
    )

    # Gráfico 1
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df_graf['Periodo'], y=df_graf['consumo'], name="Consumo (km/l)", line=dict(color='#0078d4', width=3), connectgaps=True, mode='lines+markers'), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_graf['Periodo'], y=df_graf['vel'], name="Velocidade (km/h)", line=dict(color='#333', width=2), connectgaps=True, mode='lines'), secondary_y=True)
    
    fig.update_layout(
        title=dict(text="Evolução Mensal", x=0.5), # Título centralizado
        height=420,
        xaxis=dict(
            rangeselector=dict(buttons=list([
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="1a", step="year", stepmode="backward"),
                dict(step="all", label="Tudo")
            ]), x=0, y=1.1), # Botões alinhados a esquerda acima
            rangeslider=dict(visible=True, thickness=0.05),
            type="date"
        ),
        **layout_clean
    )
    div_graf1 = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # Gráfico 2
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_graf['Periodo'], y=df_graf['preco_litro'], name="Preço/L", line=dict(color='#d13438', width=2), fill='tozeroy', connectgaps=True))
    fig2.update_layout(title=dict(text="Histórico Preço/L", x=0.5), height=300, **layout_clean)
    div_graf2 = fig2.to_html(full_html=False, include_plotlyjs=False)

    # -------------------------------------------------------------------------
    # HTML
    # -------------------------------------------------------------------------
    html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Corolla</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1400px; margin: auto; }}
        
        .header {{ background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .kpi-row {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
        .kpi-card {{ flex: 1; min-width: 200px; background: white; padding: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; border-top: 3px solid #0078d4; }}
        .kpi-val {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
        .kpi-lbl {{ font-size: 11px; text-transform: uppercase; color: #666; }}
        
        .charts {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .chart-box {{ background: white; padding: 10px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        
        .table-box {{ background: white; padding: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 800px; }}
        th {{ text-align: left; background: #f8f9fa; padding: 10px; border-bottom: 2px solid #ddd; color: #555; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
        
        .row-ano {{ background: #e3f2fd; font-weight: 700; cursor: pointer; }}
        .row-ano:hover {{ background: #bbdefb; }}
        .row-mes {{ display: none; background: #fff; font-weight: 600; cursor: pointer; }}
        .row-mes:hover {{ background: #f5f5f5; }}
        .row-mes td:first-child {{ padding-left: 30px; color: #0078d4; }}
        .row-det {{ display: none; background: #fafafa; color: #666; font-size: 12px; }}
        .row-det td:first-child {{ padding-left: 60px; font-style: italic; }}
        
        .btn-toggle {{ display: inline-block; width: 15px; text-align: center; font-weight: bold; }}
        .text-right {{ text-align: right; }}
        
        @media (max-width: 900px) {{ .charts {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div>
            <h2 style="margin:0">Dashboard de Custos</h2>
            <small>{os.path.basename(caminho)}</small>
        </div>
        <div>
            <label>Ano:</label>
            <select id="selAno" onchange="render()"></select>
        </div>
    </div>
    
    <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-lbl">Custo/KM</div><div class="kpi-val" id="k-ckm">-</div></div>
        <div class="kpi-card"><div class="kpi-lbl">Total Gasto</div><div class="kpi-val" id="k-total">-</div></div>
        <div class="kpi-card"><div class="kpi-lbl">Distância</div><div class="kpi-val" id="k-dist">-</div></div>
        <div class="kpi-card"><div class="kpi-lbl">Consumo Médio</div><div class="kpi-val" id="k-cons">-</div></div>
    </div>

    <div class="charts">
        <div class="chart-box">{div_graf1}</div>
        <div class="chart-box">{div_graf2}</div>
    </div>

    <div class="table-box">
        <table id="tabela">
            <thead>
                <tr>
                    <th>Período / Detalhe</th>
                    <th class="text-right">R$/km</th>
                    <th class="text-right">Distância</th>
                    <th class="text-right">Litros</th>
                    <th class="text-right">Horas</th>
                    <th class="text-right">Vel. Média</th>
                    <th class="text-right">Total</th>
                </tr>
            </thead>
            <tbody id="tbody"></tbody>
            <tfoot id="tfoot"></tfoot>
        </table>
    </div>
</div>

<script>
    const dados = {json_dados};
    const fmtN = (n, d=0) => n.toLocaleString('pt-BR', {{minimumFractionDigits:d, maximumFractionDigits:d}});
    const fmtM = (n) => n.toLocaleString('pt-BR', {{style:'currency', currency:'BRL'}});

    function init() {{
        const anos = [...new Set(dados.filter(d => d.tipo === 'ano').map(d => parseInt(d.col1)))].sort();
        const sel = document.getElementById('selAno');
        let opt = document.createElement('option'); opt.value='all'; opt.innerText='Todos'; sel.appendChild(opt);
        anos.forEach(a => {{
            let o = document.createElement('option'); o.value=a; o.innerText=a; sel.appendChild(o);
        }});
        sel.value = 'all';
        render();
    }}

    function toggle(id) {{
        const rows = document.querySelectorAll(`tr[data-pai="${{id}}"]`);
        const btn = document.getElementById(`btn-${{id}}`);
        let showing = false;
        rows.forEach(r => {{
            if (r.style.display === 'none') {{ r.style.display = 'table-row'; showing = true; }} 
            else {{ r.style.display = 'none'; const childId = r.getAttribute('data-id'); if(childId) closeChildren(childId); }}
        }});
        if(btn) btn.innerText = showing ? '-' : '+';
    }}
    
    function closeChildren(id) {{
        const rows = document.querySelectorAll(`tr[data-pai="${{id}}"]`);
        const btn = document.getElementById(`btn-${{id}}`);
        rows.forEach(r => {{
            r.style.display = 'none';
            const childId = r.getAttribute('data-id');
            if(childId) closeChildren(childId);
        }});
        if(btn) btn.innerText = '+';
    }}

    function render() {{
        const filtro = document.getElementById('selAno').value;
        const tbody = document.getElementById('tbody');
        const tfoot = document.getElementById('tfoot');
        tbody.innerHTML = ''; tfoot.innerHTML = '';
        
        let t_dist=0, t_custo=0, t_litros=0, t_horas=0;
        let anosExibir = dados.filter(d => d.tipo === 'ano');
        if(filtro !== 'all') anosExibir = anosExibir.filter(d => d.col1 == filtro);

        anosExibir.forEach(anoRow => {{
            t_dist += anoRow.dist; t_custo += anoRow.custo; t_litros += anoRow.litros; t_horas += anoRow.horas;
            
            let vShowAno = anoRow.vel > 0 ? fmtN(anoRow.vel, 2) : '-';
            let cShowAno = anoRow.consumo > 0 ? fmtN(anoRow.consumo, 2) : '-';

            let trAno = `<tr class="row-ano" onclick="toggle('${{anoRow.id}}')" data-id="${{anoRow.id}}">
                <td><span class="btn-toggle" id="btn-${{anoRow.id}}">+</span> ${{anoRow.col1}}</td>
                <td class="text-right">R$ ${{fmtN(anoRow.custo_km, 4)}}</td>
                <td class="text-right">${{fmtN(anoRow.dist)}}</td>
                <td class="text-right">${{fmtN(anoRow.litros)}}</td>
                <td class="text-right">${{fmtN(anoRow.horas, 1)}}</td>
                <td class="text-right">${{vShowAno}}</td>
                <td class="text-right">${{fmtM(anoRow.custo)}}</td>
            </tr>`;
            tbody.innerHTML += trAno;

            const meses = dados.filter(d => d.tipo === 'mes' && d.pai === anoRow.id);
            meses.forEach(mesRow => {{
                let vShowMes = mesRow.vel > 0 ? fmtN(mesRow.vel, 2) : '-';
                let cShowMes = mesRow.consumo > 0 ? fmtN(mesRow.consumo, 2) : '-';
                
                let trMes = `<tr class="row-mes" style="display:none" data-pai="${{anoRow.id}}" data-id="${{mesRow.id}}" onclick="toggle('${{mesRow.id}}'); event.stopPropagation();">
                    <td><span class="btn-toggle" id="btn-${{mesRow.id}}">+</span> ${{mesRow.col1}}</td>
                    <td class="text-right">R$ ${{fmtN(mesRow.custo_km, 4)}}</td>
                    <td class="text-right">${{fmtN(mesRow.dist)}}</td>
                    <td class="text-right">${{fmtN(mesRow.litros)}}</td>
                    <td class="text-right">${{fmtN(mesRow.horas, 1)}}</td>
                    <td class="text-right">${{vShowMes}}</td>
                    <td class="text-right">${{fmtM(mesRow.custo)}}</td>
                </tr>`;
                tbody.innerHTML += trMes;

                const dets = dados.filter(d => d.tipo === 'detalhe' && d.pai === mesRow.id);
                dets.forEach(det => {{
                    let vShow = det.vel > 0 ? fmtN(det.vel, 2) : '-';
                    let trDet = `<tr class="row-det" style="display:none" data-pai="${{mesRow.id}}">
                        <td>${{det.col1}}</td>
                        <td class="text-right">R$ ${{fmtN(det.custo_km, 4)}}</td>
                        <td class="text-right">${{fmtN(det.dist)}}</td>
                        <td class="text-right">${{fmtN(det.litros)}}</td>
                        <td class="text-right">${{fmtN(det.horas, 1)}}</td>
                        <td class="text-right">${{vShow}}</td>
                        <td class="text-right">${{fmtM(det.custo)}}</td>
                    </tr>`;
                    tbody.innerHTML += trDet;
                }});
            }});
        }});

        let g_ckm = t_dist > 0 ? t_custo / t_dist : 0;
        let g_cons = t_litros > 0 ? t_dist / t_litros : 0;

        tfoot.innerHTML = `<tr style="background:#333; color:#fff; font-weight:bold">
            <td style="padding:15px">TOTAL GERAL</td>
            <td class="text-right">R$ ${{fmtN(g_ckm, 4)}}</td>
            <td class="text-right">${{fmtN(t_dist)}}</td>
            <td class="text-right">${{fmtN(t_litros)}}</td>
            <td class="text-right">${{fmtN(t_horas, 1)}}</td>
            <td class="text-right">-</td>
            <td class="text-right">${{fmtM(t_custo)}}</td>
        </tr>`;

        document.getElementById('k-ckm').innerText = "R$ " + fmtN(g_ckm, 4);
        document.getElementById('k-total').innerText = fmtM(t_custo);
        document.getElementById('k-dist').innerText = fmtN(t_dist);
        document.getElementById('k-cons').innerText = fmtN(g_cons, 2);
    }}

    window.onload = init;
</script>
</body>
</html>
"""
    with open("dashboard_corolla_v11.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Sucesso! Dashboard v11 gerado.")

if __name__ == "__main__":
    main()