import requests
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import boto3
import zipfile
from io import BytesIO
from datetime import datetime, timedelta
import os

# Função para calcular a data do pregão D-1 (ignorar fins de semana)
def obter_data_pregao_anterior():
    hoje = datetime.now()
    if hoje.weekday() == 0:  # Segunda-feira
        data_pregao = hoje - timedelta(days=3)  # Pega o pregão de sexta
    else:
        data_pregao = hoje - timedelta(days=1)
    return data_pregao.strftime('%Y-%m-%d')

# Função para baixar o arquivo de cotações do pregão
def baixar_arquivo_pregao_d1(url_base):
    data_pregao = obter_data_pregao_anterior()
    url = f"{url_base}{data_pregao}"  # Adapta a URL conforme necessárioi
    print(url)
    response = requests.get(url)
    if response.status_code == 200:
        arquivo_zip_bytes = BytesIO(response.content)
        with zipfile.ZipFile(arquivo_zip_bytes, 'r') as zip_ref:
        # Como há apenas um arquivo no zip, podemos obter o primeiro
            nome_arquivo = zip_ref.namelist()[0]
            conteudo_arquivo = zip_ref.read(nome_arquivo)

        return conteudo_arquivo
    else:
        raise Exception("Erro ao baixar o arquivo.")

# Função para converter o arquivo em DataFrame e depois em Parquet
def converter_para_parquet(arquivo_csv):
    df = pd.read_csv(arquivo_csv)
    table = pa.Table.from_pandas(df)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)
    return buffer

def salvar_localmente(arquivo_csv):
   
    # Salvar o arquivo localmente
    with open("dia.csv", 'wb') as f:
        f.write(arquivo_csv)
    print(f"Arquivo salvo localmente: ")

# Função para fazer upload para o S3 com partição diária
def salvar_no_s3(buffer_parquet, bucket_name, diretorio_s3):
    s3_client = boto3.client('s3')
    data_particao = obter_data_pregao_anterior().replace('/', '-')
    caminho_s3 = f"{diretorio_s3}/data_pregao={data_particao}/cotas.parquet"
    s3_client.upload_fileobj(buffer_parquet, bucket_name, caminho_s3)
    print(f"Arquivo salvo no S3: {caminho_s3}")

# Função principal que coordena as etapas
def executar():
    url_base = "https://arquivos.b3.com.br/rapinegocios/tickercsv/"
    bucket_name = "seu-bucket"
    diretorio_s3 = "pregoes"

    try:
        arquivo_csv = baixar_arquivo_pregao_d1(url_base)
        #salvar_localmente(arquivo_csv)
        parquet_buffer = converter_para_parquet(arquivo_csv)
        salvar_no_s3(parquet_buffer, bucket_name, diretorio_s3)
        print("Processo concluído com sucesso.")
    except Exception as e:
        print(f"Erro durante o processo: {e}")

if __name__ == "__main__":
    executar()