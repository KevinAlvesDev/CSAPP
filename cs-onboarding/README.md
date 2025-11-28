# CS Onboarding Platform

## Como Rodar o Projeto

### Importante: Certifique-se que o terminal está na pasta `cs-onboarding`

---

## Windows - CMD (Prompt de Comando)

### 1. Criar ambiente virtual

```cmd
python -m venv venv
```
Cria um ambiente virtual chamado "venv" (pasta isolada com Python e dependências)

### 2. Ativar ambiente virtual

```cmd
venv\Scripts\activate.bat
```
Ativa o ambiente virtual (você verá `(venv)` aparecer no terminal)

### 3. Instalar dependências

```cmd
pip install -r requirements.txt
```
Instala todas as dependências do projeto listadas no arquivo requirements.txt

### 4. Iniciar servidor

```cmd
python run.py
```
Inicia o servidor da aplicação

### 5. Acessar

Abra o navegador em: **http://localhost:5000**

**Email:** admin@gmail.com  
**Senha:** admin123@

---

## Windows - PowerShell

### 1. Criar ambiente virtual

```powershell
python -m venv venv
```
Cria um ambiente virtual chamado "venv"

### 2. Liberar execução de scripts (necessário apenas uma vez)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```
Libera a execução de scripts no PowerShell (necessário apenas uma vez)

### 3. Ativar ambiente virtual

```powershell
venv\Scripts\Activate.ps1
```
Ativa o ambiente virtual

### 4. Instalar dependências

```powershell
pip install -r requirements.txt
```
Instala todas as dependências do projeto

### 5. Iniciar servidor

```powershell
python run.py
```
Inicia o servidor da aplicação

### 6. Acessar

Abra o navegador em: **http://localhost:5000**

**Email:** admin@gmail.com  
**Senha:** admin123@

---

## Linux / Mac

### 1. Criar ambiente virtual

```bash
python3 -m venv venv
```
Cria um ambiente virtual chamado "venv"

### 2. Ativar ambiente virtual

```bash
source venv/bin/activate
```
Ativa o ambiente virtual

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```
Instala todas as dependências do projeto

### 4. Iniciar servidor

```bash
python run.py
```
Inicia o servidor da aplicação

### 5. Acessar

Abra o navegador em: **http://localhost:5000**

**Email:** admin@gmail.com  
**Senha:** admin123@

---

## 📋 Pré-requisitos

- Python 3.10 ou superior
- pip (gerenciador de pacotes Python - geralmente vem com Python)
