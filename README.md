# Especificação do Trabalho: Sistema de Arquivos FURGfs4

## 📌 Informações Gerais e Entrega

### O que entregar
* **Código-fonte (comentado)** na linguagem de programação de sua preferência.
* **Instruções de compilação/interpretação e execução** do código.
* **Um arquivo de exemplo** do `FURGfs4` com dados armazenados internamente.
* **Dados do grupo** (nome, matrícula e e-mail) salvos em um arquivo chamado `autores.txt`, armazenado na raiz do próprio `FURGfs4`.

### Quando e Onde entregar
* **Entrega no AVA:** até **14/09/2025 às 23h55**.

### Ambiente e Sistema
* O **Sistema Operacional alvo** para o qual a aplicação será escrita é de livre escolha e não fará diferença na avaliação.

### Apresentação / Demonstração em Aula
* Os alunos devem ser capazes de **demonstrar o funcionamento** do seu programa em sala de aula.
* **Todos os alunos** do grupo devem estar aptos a apresentar qualquer parte do trabalho.

> ⚠️ **Atenção:** Todas as entregas serão submetidas à verificação de plágio por **medida de similaridade de código**.

---

## 🛠️ Descrição do FURGfs4

O **FURGfs4** é um pequeno sistema de arquivos que reside inteiramente dentro de um outro arquivo armazenado no sistema de arquivos real do hospedeiro. 

Ele aplica conceitos vistos em aula, tais como:
* **FAT** (Tabela de Alocação de Arquivos);
* Operações estruturadas sobre arquivos e diretórios;
* Suporte a diretórios e a um número finito (e $> 100$) de arquivos.

Sua tarefa é criar um programa que implemente a especificação do `FURGfs4`.

---

## 💻 Operações Suportadas

1. **Criar um FURGfs4** no tamanho escolhido pelo usuário:
   * Podem ser delimitados tamanhos mínimos e máximos, desde que mínimo $\neq$ máximo.
   * Esta opção resultará na criação de um novo arquivo no sistema de arquivos real (ex: `trabalhos/SO/furgfs3.fs`).
   * O tamanho do arquivo real corresponderá ao tamanho escolhido (ex: se o usuário criar um sistema de $800\text{ MB}$, o arquivo `furgfs3.fs` terá $800\text{ MB}$).
2. **Copiar arquivo externo para o FURGfs4:**
   * Copia do sistema real (disco, pendrive, etc.) para dentro do FURGfs4.
   * Comando: `cp <origem>/arquivo <furgfs>/arquivo`
3. **Copiar arquivo interno para o sistema real:**
   * Copia de dentro do FURGfs4 para o sistema de arquivos real.
   * Comando: `cp <furgfs>/arquivo <destino>/arquivo`
4. **Renomear arquivo:**
   * Comando: `mv antigo.txt novo.txt`
5. **Remover arquivo:**
   * Comando: `rm arquivo.mp3` *(Suporte a `rm -r` conta como recurso extra)*.
6. **Listar arquivos e diretórios (`ls`):**
   * Deve mostrar o **tamanho real** do arquivo e o **tamanho ocupado** no FURGfs4.
7. **Exibir espaço livre (`df`):**
   * Mostra o espaço livre em relação ao total (ex: `301 MB livres de 800 MB`).
8. **Proteger / Desproteger arquivos (`protect`):**
   * Define permissões contra escrita e/ou remoção.
9. **Modo Debug (`debug arquivo.pdf`):**
   * Lista os índices dos blocos físicos que compõem o arquivo indicado.

---

## 📐 Parâmetros e Estrutura de Implementação

Alguns parâmetros devem ser decididos na sua implementação:
* **Tamanho do bloco**
* **Tamanho máximo do nome dos arquivos**
* **Ordem de armazenamento das partes internas** (com exceção do cabeçalho)
* **Metadados** (obrigatórios: apenas nome e tamanho do arquivo)

### Estrutura do Cabeçalho
O tamanho do sistema de arquivos é de escolha do usuário, mas deve ser utilizável. Os **primeiros bytes** do arquivo devem conter um cabeçalho com as informações necessárias para localizar os demais dados:
* Tamanho do cabeçalho
* Tamanho do bloco
* Tamanho total do sistema de arquivos
* Endereço de início da FAT
* Endereço de início do diretório raiz
* Endereço de início da área de dados

---

## 🎯 Requisitos e Avaliação

* O trabalho possui **requisitos mínimos** e **recomendados**.
* Trabalhos que implementarem **apenas os requisitos mínimos** terão nota oscilando próximo à média (**7,0**).
* Para alcançar notas maiores, será necessário implementar parte (ou a totalidade) dos **requisitos recomendados**.
* Para trabalhos desenvolvidos em **grupo**, espera-se um número maior de funcionalidades em relação aos desenvolvidos de forma individual.

---

## 💡 Dicas e Recomendações Técnicas

* **Memória RAM:** **NÃO** carregue o sistema de arquivos inteiro na RAM. Carregue apenas o necessário para completar a operação atual.
* **Serialização:** Use rotinas de (de)serialização para armazenar as estruturas de dados.
* **Diretórios:** Faça com que as entradas de diretório ocupem exatamente o tamanho de um bloco.

### Exemplos de Funcionalidades Recomendadas (Extras)
* **Busca:** Buscar arquivos em todo o sistema de arquivos.
* **Desfragmentação:** Algoritmo para desfragmentar blocos do sistema.
* **Compressão:** Compactar os blocos de dados ao armazenar no FURGfs4.
* **Metadados adicionais:** Data de criação e/ou modificação.
* **Quotas:** Limite de espaço por diretório.
* **Checksum:** Exibir o `sha256sum` para auxílio na verificação de integridade.
* **Comparação de arquivos:** Comparar arquivo interno com externo e verificar se são idênticos (ex: `diff arquivo.txt /tmp/outro.txt`).