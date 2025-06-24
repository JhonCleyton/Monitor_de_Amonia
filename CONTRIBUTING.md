# Guia de Contribuição

Obrigado por considerar contribuir para o Sistema de Monitoramento de Amônia! Este guia irá ajudá-lo a configurar o ambiente de desenvolvimento e enviar suas contribuições.

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Git
- Ambiente de desenvolvimento (VS Code, PyCharm, etc.)
- Conhecimento básico de Git e GitHub

## 🛠️ Configuração do Ambiente

1. **Faça um Fork do repositório**
   - Clique no botão "Fork" no canto superior direito da página do projeto
   - Clone seu fork para sua máquina local:
     ```bash
     git clone https://github.com/seu-usuario/Monitor_amonia.git
     cd Monitor_amonia
     ```

2. **Configure o ambiente virtual**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install --upgrade pip
   pip install -r requirements-dev.txt  # Inclui dependências de desenvolvimento
   pip install -e .  # Instala o pacote em modo de desenvolvimento
   ```

4. **Configure as variáveis de ambiente**
   - Copie o arquivo `.env.example` para `.env`
   - Edite o arquivo `.env` com suas configurações locais

## 🔧 Desenvolvimento

1. **Crie uma branch para sua feature**
   ```bash
   git checkout -b feature/nome-da-feature
   ```

2. **Faça as alterações necessárias**
   - Siga as convenções de código do projeto
   - Adicione testes para novas funcionalidades
   - Atualize a documentação conforme necessário

3. **Execute os testes**
   ```bash
   pytest tests/
   ```

4. **Verifique a formatação**
   ```bash
   black .
   isort .
   flake8
   ```

5. **Faça o commit das alterações**
   ```bash
   git add .
   git commit -m "Descrição concisa das alterações"
   ```

6. **Envie as alterações**
   ```bash
   git push origin feature/nome-da-feature
   ```

7. **Abra um Pull Request**
   - Acesse o repositório original no GitHub
   - Clique em "Compare & pull request"
   - Preencha o template do PR com as informações solicitadas
   - Aguarde a revisão do mantenedor

## 📝 Padrões de Código

- Siga o [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints para melhorar a legibilidade e manutenção
- Documente funções e classes usando docstrings no formato Google Style
- Escreva testes para novas funcionalidades
- Mantenha o CHANGELOG.md atualizado

## 🐛 Reportando Bugs

1. Verifique se o bug já foi reportado
2. Crie um novo issue com um título descritivo
3. Inclua etapas para reproduzir o problema
4. Descreva o comportamento esperado e o comportamento real
5. Inclua informações sobre seu ambiente (SO, versão do Python, etc.)

## 💡 Sugestões de Melhorias

1. Verifique se a sugestão já foi feita
2. Descreva o problema ou melhoria proposta
3. Explique por que esta mudança seria benéfica
4. Inclua exemplos de código ou mockups, se aplicável

## 📄 Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a Licença MIT. Consulte o arquivo [LICENSE](LICENSE) para obter mais informações.

## 🙏 Agradecimentos

Agradecemos a todos os colaboradores que ajudaram a melhorar este projeto!
