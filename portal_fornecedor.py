import streamlit as st
from supabase import create_client, Client
import uuid

# --- 1. CONFIGURAÇÃO E SEGURANÇA ---
st.set_page_config(page_title="Portal do Fornecedor - Apoena", layout="centered", page_icon="🤝")

@st.cache_resource
def init_connection():
    # O st.secrets puxa as senhas do cofre invisível do Streamlit Cloud
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error("Erro de conexão com o servidor da Aura.")
    st.stop()

# --- 2. INTERFACE DE LOGIN ---
st.title("🤝 Portal do Fornecedor")
st.markdown("Sistema de envio de faturamentos e medições - Gestão de Contratos.")
st.markdown("---")

fornecedores = ["Selecione sua empresa...", "Biomed", "Plaza Hotel"]
fornecedor_logado = st.selectbox("Identificação:", fornecedores)

# --- 3. FLUXO DO FORNECEDOR: BIOMED ---
if fornecedor_logado == "Biomed":
    st.subheader("🏥 Lançamento de Exames Ocupacionais")
    
    # Usamos st.form para o fornecedor preencher tudo antes de enviar
    with st.form("form_biomed", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_colaborador = st.text_input("Nome Completo do Colaborador:").strip().upper()
            data_exame = st.date_input("Data do Exame:")
        with col2:
            tipo_exame = st.selectbox("Tipo de Exame:", ["Exame Clínico", "ASO Admissional", "ASO Demissional", "ASO Periódico", "Audiometria", "Outros"])
            valor_exame = st.number_input("Valor Unitário (R$):", min_value=0.0, format="%.2f")

        st.markdown("---")
        st.write("🔒 **Evidência para Auditoria (Obrigatório)**")
        # Campo para o fornecedor subir o PDF original da fatura/exame
        arquivo_pdf = st.file_uploader("Anexe o arquivo PDF gerado pelo seu sistema:", type=['pdf'])

        # Botão de envio central
        enviado = st.form_submit_button("✅ Enviar Dados e Comprovante para a Aura", use_container_width=True)

        if enviado:
            if not nome_colaborador or valor_exame <= 0 or not arquivo_pdf:
                st.error("⚠️ Por favor, preencha todos os campos e anexe o PDF do comprovante.")
            else:
                with st.spinner("Processando e enviando para o banco de dados..."):
                    try:
                        # PASSO A: Criar um nome único para o PDF para não substituir outros
                        nome_arquivo_unico = f"biomed_{uuid.uuid4().hex}.pdf"
                        
                        # PASSO B: Fazer o Upload do PDF para o Storage do Supabase (Pasta 'comprovantes')
                        file_bytes = arquivo_pdf.getvalue()
                        supabase.storage.from_("comprovantes").upload(
                            file=file_bytes,
                            path=nome_arquivo_unico,
                            file_options={"content-type": "application/pdf"}
                        )
                        
                        # PASSO C: Gerar o link público desse PDF para aparecer no seu Dashboard
                        link_evidencia = supabase.storage.from_("comprovantes").get_public_url(nome_arquivo_unico)
                        
                        # PASSO D: Salvar os números e o link na Tabela do Banco de Dados
                        dados_bd = {
                            "fornecedor": "Biomed",
                            "colaborador": nome_colaborador,
                            "data_exame": str(data_exame),
                            "tipo_exame": tipo_exame,
                            "valor": valor_exame,
                            "link_pdf": link_evidencia
                        }
                        supabase.table("faturamentos").insert(dados_bd).execute()
                        
                        st.success("🚀 Registro e evidência salvos com sucesso!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Ocorreu um erro no servidor: {e}")

elif fornecedor_logado == "Plaza Hotel":
    st.info("Formulário do Plaza Hotel será ativado na próxima etapa do Piloto.")
