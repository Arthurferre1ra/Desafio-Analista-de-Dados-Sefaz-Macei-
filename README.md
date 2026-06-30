# Desafio Tecnico - Estagio em Analise de Dados | Sefaz Maceio

Solucao para o desafio de analise das despesas por funcao das capitais brasileiras, usando dados FINBRA/Siconfi de 2020 a 2025.

O projeto foi organizado para ser simples de reproduzir e facil de avaliar:

1. descompacta os arquivos de `dados_compactos/` por codigo;
2. le os CSVs no formato correto do Siconfi;
3. consolida todos os anos em uma unica base;
4. gera uma base otimizada para consulta;
5. produz indicadores e um relatorio sobre despesas empenhadas versus despesas pagas.

## Estrutura

```text
.
|-- dados_compactos/      # ZIPs originais do desafio
|-- dados_extraidos/      # CSVs extraidos pelo pipeline (ignorado no Git)
|-- dados_processados/    # base consolidada CSV gzip + SQLite
|-- relatorios/           # tabelas analiticas, graficos SVG e relatorio
|-- src/
|   |-- config.py         # caminhos, nomes de colunas e constantes do projeto
|   |-- finbra_etl.py     # extracao, leitura, limpeza e persistencia
|   |-- indicators.py     # consultas e calculo dos indicadores
|   |-- reporting.py      # formatacao e escrita dos relatorios
|   |-- visualizations.py # geracao de graficos SVG
|   |-- pipeline.py       # entrada de linha de comando do ETL
|   `-- analysis.py       # entrada de linha de comando da analise
|-- tests/                # testes unitarios dos pontos criticos
`-- requirements.txt
```

## Como executar

Crie um ambiente virtual e instale as dependencias:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Rode o ETL:

```bash
python -m src.pipeline
```

Rode a analise:

```bash
python -m src.analysis
```

Os comandos tambem aceitam `--verbose` para exibir detalhes tecnicos no console:

```bash
python -m src.pipeline --verbose
python -m src.analysis --verbose
```

Rode os testes:

```bash
python -m unittest discover -s tests
```

## Decisoes de arquitetura

- `src/config.py` centraliza caminhos, colunas esperadas, estagios da despesa e indices SQLite.
- `src/finbra_etl.py` concentra o fluxo de extracao e tratamento, deixando `src/pipeline.py` apenas como CLI.
- `src/indicators.py` concentra consultas e metricas analiticas.
- `src/reporting.py` concentra formatacao, escrita de CSVs e geracao do relatorio Markdown.
- `src/visualizations.py` gera graficos SVG versionaveis, sem depender de ferramenta externa.
- `src/logging_utils.py` padroniza logs claros no console e logs detalhados em arquivo.
- Os anos completos sao inferidos pela maior quantidade de capitais declaradas, em vez de fixar 2024 manualmente.
- A taxa de execucao usa divisao segura, evitando resultado enganoso quando o empenhado for zero.
- `dados_extraidos/` e ignorado porque e um artefato intermediario reproduzivel a partir dos ZIPs originais.

## Logs

Cada comando registra um resumo limpo no console e salva um log detalhado em arquivo:

```text
relatorios/logs/pipeline.log
relatorios/logs/analysis.log
```

No console ficam as etapas principais e o resumo final. Nos arquivos ficam timestamps, nivel do log, modulo de origem e mensagens de depuracao. Em caso de erro, a excecao tambem e capturada no arquivo de log para facilitar auditoria e correcao.

## Tratamento dos dados

Os CSVs do Siconfi nao seguem o padrao internacional. O pipeline trata explicitamente:

- `encoding="latin-1"` para preservar acentos;
- `sep=";"` como separador de colunas;
- `skiprows=3` para ignorar metadados;
- `decimal=","` e `thousands="."` para converter valores monetarios;
- criacao da coluna `ano` a partir da pasta de origem;
- classificacao de `Conta` em `funcao`, `subfuncao`, `demais_subfuncoes`, `total` ou `outra`;
- extracao de `capital`, `codigo_conta` e `nome_conta`.

As linhas de totais e de subfuncoes nao sao somadas junto com funcoes nas analises principais, evitando dupla contagem.

## Base otimizada

Escolhi SQLite para a base performatica porque ele usa biblioteca padrao do Python, e portanto deixa o projeto facil de reproduzir sem instalar servidor ou depender de extensoes nativas.

Arquivos gerados:

```text
dados_processados/finbra_consolidado.sqlite
dados_processados/finbra_consolidado.csv.gz
```

A tabela principal se chama `despesas` e tem indices em `ano`, `capital`, `tipo_conta`, `estagio` e `codigo_conta`.

## Indicadores

O principal indicador usado e a taxa de execucao financeira:

```text
taxa_execucao = despesas_pagas / despesas_empenhadas
```

Ela mostra quanto do valor empenhado foi efetivamente pago dentro do exercicio.

Tambem foram calculados:

- diferenca entre empenhado e pago;
- valor pago per capita;
- rankings por funcao, capital e ano;
- completude dos dados por ano;
- recorte de Maceio em funcoes prioritarias;
- subfuncoes de Saude e Educacao para Maceio no ano completo mais recente.
- graficos de completude, volume pago por funcao, evolucao de Maceio, maiores gaps e subfuncoes.

## Resultados

O relatorio principal fica em:

```text
relatorios/relatorio_analise.md
```

Arquivos auxiliares:

- `relatorios/indicadores_funcao_capital.csv`
- `relatorios/completude_por_ano.csv`
- `relatorios/resumo_funcoes_anos_completos.csv`
- `relatorios/maceio_funcoes_prioritarias.csv`
- `relatorios/maiores_gaps_ano_referencia.csv`
- `relatorios/maceio_subfuncoes_saude_educacao_ano_referencia.csv`

Graficos gerados:

- `relatorios/figuras/completude_por_ano.svg`
- `relatorios/figuras/top_funcoes_pagas.svg`
- `relatorios/figuras/maceio_pago_per_capita.svg`
- `relatorios/figuras/maiores_gaps_empenhado_pago.svg`
- `relatorios/figuras/maceio_subfuncoes_empenhado_pago.svg`

## Observacao sobre 2025

O README original do desafio alerta que 2025 esta incompleto. Por isso, o script conta quantas capitais existem por ano antes das comparacoes. As conclusoes principais usam apenas anos completos; 2025 aparece como dado parcial.
