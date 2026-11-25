# Modelo V para projeto e teste de sistemas embarcados

Resumo do tutorial do professor (https://frdm-kl25z-com-zephyr-rtos.super.site/tutoriais/modelo-v). Os prints originais estão em `prints_modelo_v/`.

## Ideia geral

Em sistemas críticos (aviões, trens, carros), uma falha pode machucar pessoas. O modelo V liga cada fase do desenvolvimento a uma fase de teste, o que dá **rastreabilidade entre requisitos e testes**, validação em várias etapas e menos risco, porque se testa cedo e com simulação.

| Fase de desenvolvimento | O que se faz | Teste correspondente |
|---|---|---|
| 1. Requisitos de sistema | requisitos funcionais e não funcionais | **Aceitação**: o sistema completo atende aos requisitos |
| 2. Arquitetura de sistema | hardware/software, interfaces, modos de falha | **Sistema integrado**: subsistemas e interfaces funcionam como especificado |
| 3. Projeto de componentes | módulos de software (drivers, tarefas) e hardware | **Integração**: comunicação e interação entre módulos |
| 4. Implementação | código e firmware | **Unidade**: cada módulo isolado |

## Níveis de teste

- **Unidade**: módulos isolados (funções, drivers, tarefas do RTOS). Pode usar *mocks* no lugar de periféricos que faltam.
- **Integração**: vários módulos juntos, conferindo a comunicação entre eles.
- **Sistema**: sistema completo, hardware + software, em simulação ou bancada.
- **Aceitação**: confere os requisitos especificados, em ambiente real ou representativo.

## Como escrever um teste

- **Pré-condição**: estado inicial (configuração, variáveis, tarefas), para o teste ser repetível.
- **Etapas**: ações executadas (apertar botão, gerar interrupção, rodar threads), descritas de forma que outra pessoa consiga repetir.
- **Pós-condição**: estado esperado no fim; é com ela que se decide se passou.

## Avaliação por pares e versionamento

Um colega revisa ou executa os testes do código do outro: o autor recebe retorno sobre falhas e o avaliador aprende a analisar sistemas concorrentes. O GitHub registra a evolução: cada commit marca um passo (código original, falha encontrada, correção, validação final).

Ciclo completo: pré-condição → etapas → pós-condição → revisão por pares → versionamento contínuo.
