<div align="center">
  <h1>🔍 Sistema de Monitoramento de Amônia</h1>
  <p>Solução completa para monitoramento em tempo real de níveis de amônia em ambientes industriais</p>
  
  <div align="center">
    <img src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow" alt="Status do Projeto">
    <img src="https://img.shields.io/badge/Versão-1.0.0-blue" alt="Versão">
    <img src="https://img.shields.io/badge/Licença-MIT-green" alt="Licença">
  </div>
  
  <br/>
  
  <div>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6">
    <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  </div>
</div>

---

## 🚀 Visão Geral

Sistema avançado de monitoramento em tempo real de níveis de amônia projetado para ambientes industriais. Com uma interface gráfica intuitiva e recursos avançados de notificação, nossa solução garante a segurança e conformidade dos seus processos industriais.

## 🚀 Recursos

- Monitoramento em tempo real de múltiplos sensores de amônia
- Interface gráfica intuitiva com dashboard interativo
- Alertas visuais e sonoros para níveis críticos
- Notificações por e-mail e WhatsApp
- Geração de relatórios em PDF e CSV
- Histórico de leituras com análise de tendências
- Configuração personalizável de sensores e alertas

## 🛠️ Instalação

1. **Clonar o repositório**
   ```bash
   git clone [URL_DO_REPOSITORIO]
   cd Monitor_amonia
   ```

2. **Criar um ambiente virtual (recomendado)**
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instalar as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar as variáveis de ambiente**
   - Copie o arquivo `.env.example` para `.env`
   - Edite o arquivo `.env` com suas configurações

## 🚦 Iniciando o Sistema

```bash
python -m src.main
```

## 🖥️ Estrutura do Projeto

```
Monitor_amonia/
├── data/                   # Dados do banco de dados
├── docs/                   # Documentação
├── src/                    # Código-fonte
│   ├── database/           # Gerenciamento do banco de dados
│   ├── gui/                # Interface gráfica
│   │   ├── components/     # Componentes da interface
│   │   ├── pages/          # Páginas da aplicação
│   │   └── styles/         # Estilos e temas
│   ├── modbus/             # Comunicação Modbus
│   ├── notifications/      # Sistema de notificações
│   └── utils/              # Utilitários
├── tests/                  # Testes automatizados
├── .env.example            # Exemplo de variáveis de ambiente
├── requirements.txt        # Dependências do projeto
└── README.md               # Este arquivo
```

## ⚙️ Configuração

### Sensores

O sistema suporta múltiplos sensores configuráveis. As configurações podem ser ajustadas no menu de configurações da aplicação.

### Notificações

- **E-mail**: Configure o servidor SMTP e as credenciais no arquivo `.env`
- **WhatsApp**: É necessário uma conta no Twilio e configurar as credenciais

### Banco de Dados

O sistema utiliza SQLite por padrão, armazenado na pasta `data/`. É recomendado fazer backup periódico desta pasta.

## 📊 Uso

1. **Dashboard Principal**
   - Visualização em tempo real dos níveis de amônia
   - Gráficos de tendência
   - Status dos sensores

2. **Alertas**
   - Configuração de limites de alerta
   - Histórico de alertas
   - Ações corretivas sugeridas

3. **Relatórios**
   - Geração de relatórios personalizados
   - Exportação para PDF e CSV
   - Análise de tendências

## 🏢 Sobre a JC Bytes

<div align="center">
  <h3>JC Bytes - Solução em Tecnologia</h3>
  <p><em>Excelência em Desenvolvimento de Software</em></p>
  
  <p>Especializada em desenvolvimento de software personalizado, a JC Bytes entrega soluções tecnológicas inovadoras e de alta performance para diversos segmentos do mercado.</p>
  
  <div>
    <a href="https://www.instagram.com/jc.devops" target="_blank">
      <img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram">
    </a>
    <a href="https://www.linkedin.com/in/Jhon-freire" target="_blank">
      <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
    </a>
    <a href="https://github.com/JhonCleyton" target="_blank">
      <img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
    </a>
    <a href="https://wa.me/5573998547885" target="_blank">
      <img src="https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="WhatsApp">
    </a>
  </div>
  
  <p>📧 Email: <a href="mailto:tecnologiajcbyte@gmail.com">tecnologiajcbyte@gmail.com</a></p>
  <p>🌐 Site: <a href="https://jhoncleyton.dev" target="_blank">jhoncleyton.dev</a></p>
</div>

## 🤝 Contribuição

Contribuições são bem-vindas! Siga estes passos:

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Adicione suas mudanças (`git add .`)
4. Comite suas mudanças (`git commit -m 'Add some AmazingFeature'`)
5. Faça o Push da Branch (`git push origin feature/AmazingFeature`)
6. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<div align="center">
  <p>© 2025 JC Bytes - Todos os direitos reservados</p>
  <p>Desenvolvido por <a href="https://jhoncleyton.dev" target="_blank">Jhon Freire</a></p>
  
  <div>
    <a href="https://www.instagram.com/jc.devops" target="_blank">
      <img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram">
    </a>
    <a href="https://www.linkedin.com/in/Jhon-freire" target="_blank">
      <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
    </a>
    <a href="https://github.com/JhonCleyton" target="_blank">
      <img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
    </a>
  </div>
</div>

## 📧 Contato

Seu Nome - [@seu_twitter](https://twitter.com/seu_twitter) - email@exemplo.com

Link do Projeto: [https://github.com/seu_usuario/Monitor_amonia](https://github.com/seu_usuario/Monitor_amonia)

## 🙏 Agradecimentos

- [PyQt](https://www.riverbankcomputing.com/software/pyqt/)
- [MinimalModbus](https://minimalmodbus.readthedocs.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Twilio](https://www.twilio.com/)
- E todas as outras bibliotecas incríveis que tornaram este projeto possível!
