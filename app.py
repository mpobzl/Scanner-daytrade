import streamlit as st
import pandas as pd
import zipfile

st.set_page_config(page_title="Scanner Day Trade", layout="wide")

# =============================
# TÍTULO
# =============================
st.title("📊 Scanner Estatístico Day Trade")

# =============================
# FUNÇÃO DE COR
# =============================
def color_queda(val):
    try:
        val = float(val)
        return f"color: {'red' if val < 0 else 'green'}"
    except:
        return ""

# =============================
# CARREGAR ZIP FIXO
# =============================
try:
    arquivo_zip = "dados.zip"

    dados_ativos = {}
    datas_ativos = {}
    data_referencia = None

    with zipfile.ZipFile(arquivo_zip) as z:

        arquivos = [f for f in z.namelist() if f.endswith(".csv")]

        st.info(f"📦 {len(arquivos)} arquivos carregados")

        for arquivo in arquivos:

            try:
                with z.open(arquivo) as f:

                    colunas = [
                        "Acao","Data","Abertura","Maxima","Minima",
                        "Ultimo","Valor_R$","Volume"
                    ]

                    df = pd.read_csv(f, sep=";", header=None, names=colunas)

                    for col in ["Abertura","Maxima","Minima","Ultimo","Valor_R$","Volume"]:
                        df[col] = df[col].astype(str).str.replace(",",".").astype(float)

                    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
                    df = df.sort_values("Data")

                    df["close_anterior"] = df["Ultimo"].shift(1)
                    df["queda"] = df["Ultimo"] / df["close_anterior"] - 1
                    df["high_d1"] = df["Maxima"].shift(-1)
                    df["range_d1"] = df["high_d1"] / df["Ultimo"] - 1
                    df["ret"] = df["Ultimo"].pct_change()

                    acao = arquivo.split("/")[-1].split("_")[0]

                    dados_ativos[acao] = df

                    ultima_data = df.iloc[-1]["Data"]
                    datas_ativos[acao] = ultima_data

                    if data_referencia is None:
                        data_referencia = ultima_data
                    else:
                        data_referencia = max(data_referencia, ultima_data)

            except:
                continue

    st.success(f"📅 Data analisada: {data_referencia.strftime('%d/%m/%Y')}")

    # =============================
    # FILTRO DE ATIVOS ATUALIZADOS
    # =============================
    ativos_validos = [a for a in dados_ativos if datas_ativos[a] == data_referencia]

    scanner = []
    quedas_dia = []

    # =============================
    # PROCESSAMENTO
    # =============================
    for acao in ativos_validos:

        df = dados_ativos[acao]

        eventos = df[df["queda"] <= -0.01]
        eventos_range = eventos[eventos["range_d1"] >= 0.01]

        prob = len(eventos_range) / len(eventos) if len(eventos) > 0 else 0

        ultimo = df.iloc[-1]

        queda_dia = ultimo["queda"]
        volume_fin = ultimo["Valor_R$"]
        volatilidade = df["ret"].std()
        zscore = queda_dia / volatilidade if volatilidade != 0 else 0

        if volume_fin >= 100_000_000:

            quedas_dia.append({
                "Acao": acao,
                "Queda": queda_dia,
                "Volume": volume_fin
            })

            if queda_dia <= -0.01 and prob >= 0.70:

                score = abs(zscore) * prob * volume_fin

                scanner.append({
                    "Acao": acao,
                    "Queda": queda_dia,
                    "Prob": prob,
                    "ZScore": zscore,
                    "Score": score
                })

    # =============================
    # MÉTRICAS
    # =============================
    col1, col2, col3 = st.columns(3)
    col1.metric("Ativos analisados", len(ativos_validos))
    col2.metric("Quedas relevantes", len(quedas_dia))
    col3.metric("Oportunidades", len(scanner))

    st.divider()

    # =============================
    # TOP QUEDAS
    # =============================
    st.subheader("📉 Top 15 Maiores Quedas")

    if quedas_dia:
        df_quedas = pd.DataFrame(quedas_dia).sort_values("Queda").head(15)

        df_quedas["Queda_num"] = df_quedas["Queda"]

        df_quedas["Queda"] = df_quedas["Queda"].apply(lambda x: f"{x:.2%}")
        df_quedas["Volume"] = df_quedas["Volume"].apply(lambda x: f"R$ {x:,.0f}")

        st.dataframe(df_quedas.style.applymap(color_queda, subset=["Queda_num"]), use_container_width=True)

    st.divider()

    # =============================
    # SCANNER
    # =============================
    st.subheader("🚀 Scanner Estatístico")

    if scanner:
        df_scan = pd.DataFrame(scanner).sort_values("Score", ascending=False)

        df_scan["Queda"] = df_scan["Queda"].apply(lambda x: f"{x:.2%}")
        df_scan["Prob"] = df_scan["Prob"].apply(lambda x: f"{x:.2%}")

        st.dataframe(df_scan, use_container_width=True)
    else:
        st.warning("Nenhum ativo passou no filtro.")

    st.divider()

    # =============================
    # EXPECTATIVA
    # =============================
    st.subheader("📊 Expectativa da Estratégia")

    expectativa_lista = []

    for acao in ativos_validos:

        df = dados_ativos[acao]

        ultimo = df.iloc[-1]
        volume_fin = ultimo["Valor_R$"]

        if volume_fin < 100_000_000:
            continue

        eventos = df[df["queda"] <= -0.01]

        if len(eventos) < 30:
            continue

        ranges = eventos["range_d1"].dropna()

        if len(ranges) == 0:
            continue

        ganhos = ranges[ranges >= 0.01]
        perdas = ranges[ranges < 0.01]

        prob_ganho = len(ganhos) / len(ranges)
        ganho_medio = ganhos.mean() if len(ganhos) > 0 else 0
        perda_media = perdas.mean() if len(perdas) > 0 else 0

        expectativa = prob_ganho * ganho_medio + (1 - prob_ganho) * perda_media

        expectativa_lista.append({
            "Acao": acao,
            "Prob": prob_ganho,
            "Ganho": ganho_medio,
            "Perda": perda_media,
            "Expectativa": expectativa
        })

    if expectativa_lista:
        df_exp = pd.DataFrame(expectativa_lista).sort_values("Expectativa", ascending=False)

        df_exp["Prob"] = df_exp["Prob"].apply(lambda x: f"{x:.2%}")
        df_exp["Ganho"] = df_exp["Ganho"].apply(lambda x: f"{x:.2%}")
        df_exp["Perda"] = df_exp["Perda"].apply(lambda x: f"{x:.2%}")
        df_exp["Expectativa"] = df_exp["Expectativa"].apply(lambda x: f"{x:.2%}")

        st.dataframe(df_exp, use_container_width=True)

except Exception as e:
    st.error("Erro ao carregar dados")
    st.text(str(e))