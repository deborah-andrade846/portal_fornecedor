import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Auditor Automático - Apoena", layout="wide", page_icon="🔎")

st.title("🔎 Auditor Automático de Faturação")
st.markdown("Cruzamento de dados: **Sistema (SIGec/Supabase) vs. Ficheiro PDF (Biomed)**")
st.markdown("---")

# 1. SIMULAÇÃO DO BANCO DE DADOS (SIGec / Supabase)
# Na versão final, isto viria de uma consulta direta ao seu banco de dados.
# Aqui, coloquei um valor errado de propósito (40.00) para forçar o sistema a apanhar a divergência.
dados_sistema = pd.DataFrame({
    "Colaborador": [
        "JONATHAN DAVID REZENDE CORREA", 
        "FERNANDO BENFICA DE OLIVEIRA LEMOS", 
        "PAULO RICARDO DE ALMEIDA GOMES"
    ],
    "Exame_Esperado": ["Exame Clínico", "Exame Clínico", "ASO Admissional"],
    "Valor_Sistema": [40.00, 45.00, 45.00] # O valor do Jonathan está 40 em vez de 45
})

st.subheader("1. Dados Aprovados no Sistema (Referência)")
st.dataframe(dados_sistema, use_container_width=True)

# 2. CARREGAMENTO DO FICHEIRO DE EVIDÊNCIA
st.subheader("2. Fatura do Fornecedor (Contraprova)")
ficheiro_pdf = st.file_uploader("Arraste o PDF da Biomed para iniciar a auditoria cruzada:", type=['pdf'])

if ficheiro_pdf:
    with st.spinner("A ler o PDF e a cruzar informações..."):
        dados_pdf = []
        
        # --- Lógica de Extração do PDF ---
        with pdfplumber.open(ficheiro_pdf) as pdf:
            texto_completo = "\n".join([pagina.extract_text() or "" for pagina in pdf.pages])
            linhas = texto_completo.split('\n')
            
            nome_atual = "DESCONHECIDO"
            
            for linha in linhas:
                # Tenta capturar o nome do colaborador (geralmente antes do exame)
                if "(" in linha and ")" in linha and "em" in linha:
                    # Limpa o texto para extrair apenas o nome antes do CPF
                    nome_atual = linha.split("(")[0].strip()
                    
                # Captura a linha do exame e do valor
                elif "R$" in linha:
                    partes = linha.split("R$")
                    if len(partes) >= 2:
                        nome_exame = partes[0].replace('"', '').replace(',', '').strip()
                        # Extrai o valor numérico para facilitar a comparação matemática
                        valor_texto = partes[1].replace('"', '').replace(',', '').strip()
                        try:
                            valor_numerico = float(valor_texto.replace('.', '').replace(',', '.'))
                        except:
                            valor_numerico = 0.0
                            
                        if nome_exame and nome_atual != "DESCONHECIDO":
                            dados_pdf.append({
                                "Colaborador": nome_atual,
                                "Exame_Cobrado": nome_exame,
                                "Valor_PDF": valor_numerico
                            })
                            # Reseta o nome para evitar duplicações erradas
                            nome_atual = "DESCONHECIDO"

        df_pdf = pd.DataFrame(dados_pdf)

        # 3. O CRUZAMENTO DE DADOS (A MÁGICA DO PANDAS)
        if not df_pdf.empty:
            # Faz o "PROCV" juntando as duas tabelas usando o Nome do Colaborador como chave
            df_auditoria = pd.merge(dados_sistema, df_pdf, on="Colaborador", how="outer")
            
            # Preenche espaços vazios (caso alguém esteja no PDF mas não no sistema e vice-versa)
            df_auditoria.fillna({"Valor_Sistema": 0.0, "Valor_PDF": 0.0, "Exame_Esperado": "-", "Exame_Cobrado": "-"}, inplace=True)
            
            # 4. APLICAÇÃO DAS REGRAS DE NEGÓCIO (Identificar os Erros)
            def classificar_status(linha):
                if linha["Valor_Sistema"] == 0.0:
                    return "🔴 Cobrança Indevida (Não está no sistema)"
                elif linha["Valor_PDF"] == 0.0:
                    return "🟡 Faltou Cobrar (Está no sistema, mas não no PDF)"
                elif linha["Valor_Sistema"] != linha["Valor_PDF"]:
                    return "🔴 Divergência de Valor"
                else:
                    return "✅ OK (Valores conferem)"

            df_auditoria["Status da Auditoria"] = df_auditoria.apply(classificar_status, axis=1)
            
            # 5. EXIBIÇÃO VISUAL DOS RESULTADOS
            st.markdown("---")
            st.subheader("3. Resultado da Auditoria Automática")
            
            # Conta os erros para o resumo
            erros = len(df_auditoria[df_auditoria["Status da Auditoria"].str.contains("🔴")])
            
            if erros > 0:
                st.error(f"Atenção: Foram encontradas {erros} divergências que bloqueiam o pagamento.")
            else:
                st.success("Tudo certo! A fatura corresponde exatamente ao sistema. Pagamento libertado.")
            
            # Mostra a tabela final focada na auditoria
            st.dataframe(
                df_auditoria[["Colaborador", "Exame_Esperado", "Valor_Sistema", "Valor_PDF", "Status da Auditoria"]], 
                use_container_width=True
            )
            
        else:
            st.warning("Não foi possível extrair dados válidos deste PDF para cruzamento.")
