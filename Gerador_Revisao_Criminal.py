import streamlit as st
import pandas as pd
import numpy as np
import io
import re

# Título do aplicativo
st.title("Processamento de Afastamento de Servidores")
st.markdown("---")

# Seção de upload de arquivos
st.header("1. Importação das Planilhas")

uploaded_file_1 = st.file_uploader(
    "Escolha a planilha de Afastamentos (.csv)",
    type=['csv']
)
uploaded_file_2 = st.file_uploader(
    "Escolha a planilha de Lotação (.xlsx)",
    type=['xlsx']
)

# Verifica se ambos os arquivos foram carregados
if uploaded_file_1 is not None and uploaded_file_2 is not None:
    # Lê os arquivos para DataFrames
    try:
        # Lendo o arquivo CSV com a codificação correta
        df_afastamento = pd.read_csv(uploaded_file_1, sep=';', encoding='windows-1252')

        # Lê a planilha de lotação como .xlsx
        df_lotacao = pd.read_excel(uploaded_file_2)

        st.success("Arquivos carregados com sucesso!")
        st.markdown("---")

        # Início do processamento
        st.header("2. Processando os Dados...")

        with st.spinner('Executando o tratamento...'):
            # --- Etapa de Classificação ---
            st.markdown("##### Classificando os dados...")
            df_afastamento['DT_INICIO'] = pd.to_datetime(df_afastamento['DT_INICIO'], format='%d/%m/%Y',
                                                         errors='coerce')
            df_afastamento['DT_ALTERACAO'] = pd.to_datetime(df_afastamento['DT_ALTERACAO'], format='%d/%m/%Y %H:%M:%S',
                                                            errors='coerce')

            df_afastamento_processed = df_afastamento.sort_values(
                by=['SERVIDOR', 'DT_INICIO', 'DT_ALTERACAO'],
                ascending=[True, True, False]
            ).copy()
            st.success(
                "Classificação concluída: SERVIDOR (A-Z), DT_INICIO (mais antigo ao novo) e DT_ALTERACAO (mais novo ao antigo).")

            # --- Exclusão de Linhas com Palavras-chave na Coluna SITUACAO ---
            st.markdown("##### Removendo linhas com palavras-chave na coluna SITUACAO...")
            palavras_chave_situacao = [
                'Excluído', 'Homologado a Indenizar', 'Indenizado', 'Anulado', 'Cancelado', 'Indeferido',
                'Indenização Solicitada'
            ]
            df_afastamento_processed = df_afastamento_processed[
                ~df_afastamento_processed['SITUACAO'].isin(palavras_chave_situacao)
            ]
            st.success("Exclusão de linhas em SITUACAO concluída.")

            # --- Remoção de Duplicatas ---
            st.markdown("##### Removendo duplicatas nas colunas ID_SERVIDOR e ID_AFAST...")
            df_afastamento_processed.drop_duplicates(subset=['ID_SERVIDOR', 'ID_AFAST'], inplace=True)
            st.success("Remoção de duplicatas concluída.")

            # --- Exclusão de Linhas com Palavras-chave nas Colunas JUSTIFICATIVA e MOTIVO ---
            st.markdown("##### Removendo linhas com palavras-chave nas colunas JUSTIFICATIVA e MOTIVO...")

            # Unifica as palavras e frases para o filtro
            termos_excluir = [
                'EXERCÍCIO FUNÇÃO DE CONFIANÇA',
                'MANDATO', 'INDENIZADO', 'INDENIZAR', 'GRATIFICAR', 'indenização',
                'INDEFERIMENTO', 'INDEFERIR', 'GRATIFICAÇÃO',
                'Compensação - Atividades em finais de semana, feriados ou recessos (indenizável) – Ato DPG 277/2024',
                'Indenizada', 'Compensação indeferida a bem do serviço público',
                'Compensação para indenizaçao', 'Compensação indenizável',
                'Indeferida', 'Indeferido', 'Indef', 'INDENIZAÇAO', 'Indenizacao',
                'Indenização','Para fins de pagamento','para pagamento','pagamento','licença maternidade'
            ]

            # Cria um padrão de regex a partir da lista
            regex_pattern = '|'.join([re.escape(termo) for termo in termos_excluir])

            # Aplica o filtro para as colunas 'JUSTIFICATIVA' e 'MOTIVO'
            df_afastamento_processed = df_afastamento_processed[
                ~(df_afastamento_processed['JUSTIFICATIVA'].fillna('').str.contains(regex_pattern, case=False,
                                                                                    regex=True)) &
                ~(df_afastamento_processed['MOTIVO'].fillna('').str.contains(regex_pattern, case=False, regex=True))
                ]

            st.success("Exclusão de linhas em JUSTIFICATIVA e MOTIVO concluída.")

            # --- Cruzamento de Informações ---
            st.markdown("##### Cruzando informações das duas planilhas...")
            df_lotacao_final = df_lotacao[['ID_SERVIDOR', 'ESTRUTURA_DEFENSOR']].copy()
            df_afastamento_merged = pd.merge(
                df_afastamento_processed,
                df_lotacao_final,
                on='ID_SERVIDOR',
                how='left'
            )
            df_afastamento_merged['NM_ESTRUTURA'] = np.where(
                df_afastamento_merged['ESTRUTURA_DEFENSOR'].notna(),
                df_afastamento_merged['ESTRUTURA_DEFENSOR'],
                df_afastamento_merged['NM_ESTRUTURA']
            )
            df_afastamento_merged.drop('ESTRUTURA_DEFENSOR', axis=1, inplace=True)
            st.success("Cruzamento de dados finalizado. A coluna NM_ESTRUTURA foi atualizada.")

        # --- Etapa de Filtro das Colunas Finais ---
        st.markdown("##### Filtrando as colunas finais...")
        colunas_finais = [
            'ID_SERVIDOR', 'SERVIDOR', 'SITUACAO', 'MOTIVO',
            'DT_INICIO', 'DT_FIM', 'QT_DIA', 'NM_ESTRUTURA', 'JUSTIFICATIVA'
        ]
        df_afastamento_final = df_afastamento_merged[colunas_finais]
        st.success("Filtragem de colunas concluída.")

        # --- Formatação das Colunas de Data ---
        st.markdown("##### Formatação das colunas de data...")
        df_afastamento_final['DT_INICIO'] = df_afastamento_final['DT_INICIO'].dt.strftime('%d/%m/%Y')
        df_afastamento_final['DT_FIM'] = pd.to_datetime(df_afastamento_final['DT_FIM'].astype(str), format='%d/%m/%Y',
                                                        errors='coerce').dt.strftime('%d/%m/%Y')

        st.success("Formatação de data concluída.")

        st.markdown("---")
        st.header("3. Planilha Final Processada")

        # Exibir a tabela processada
        st.dataframe(df_afastamento_final)

        # Adicionar botão de download
        output = io.BytesIO()
        df_afastamento_final.to_excel(output, index=False, engine='openpyxl')
        processed_data = output.getvalue()

        st.download_button(
            label="Baixar planilha final em XLSX",
            data=processed_data,
            file_name='afastamento_servidor_processado.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os arquivos. Verifique se os arquivos estão corretos. Erro: {e}")

else:
    st.info("Por favor, faça o upload dos dois arquivos para começar o processamento.")