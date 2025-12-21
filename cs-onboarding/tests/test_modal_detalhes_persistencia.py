"""
Teste E2E: Persistência de Dados no Modal "Detalhes da Empresa"

Fluxo do teste:
1. Abre o modal
2. Faz consulta OAMD e salva
3. Volta para página principal
4. Abre a implantação novamente
5. Abre o modal novamente
6. Verifica se os valores se mantiveram

Este teste valida o bug que passamos 5 horas resolvendo.
"""

import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestModalDetalhesEmpresaPersistencia:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup do navegador."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 15)
        yield
        self.driver.quit()
    
    def login(self):
        """Login no sistema."""
        self.driver.get("http://127.0.0.1:5000/login")
        
        username = self.driver.find_element(By.ID, "username")
        password = self.driver.find_element(By.ID, "password")
        
        username.send_keys("admin@teste.com")
        password.send_keys("senha_teste")
        
        login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        self.wait.until(EC.url_contains("/dashboard"))
    
    def aguardar_modal_carregar(self):
        """Aguarda modal carregar completamente (loading state terminar)."""
        self.wait.until(
            lambda d: d.execute_script(
                "return document.querySelector('#modalDetalhesEmpresa .modal-body').style.opacity === '1'"
            )
        )
    
    def test_persistencia_completa(self):
        """
        TESTE PRINCIPAL: Valida persistência de dados após consulta OAMD.
        
        Fluxo:
        1. Abre modal
        2. Consulta OAMD
        3. Salva
        4. Volta para dashboard
        5. Reabre implantação
        6. Reabre modal
        7. Valida que dados persistiram
        """
        # 1. Login
        self.login()
        
        # 2. Navegar para implantação
        self.driver.get("http://127.0.0.1:5000/implantacao/1")
        
        # 3. Abrir modal
        btn_abrir = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-bs-target="#modalDetalhesEmpresa"]'))
        )
        btn_abrir.click()
        
        # Aguardar modal aparecer e carregar
        self.wait.until(EC.visibility_of_element_located((By.ID, "modalDetalhesEmpresa")))
        self.aguardar_modal_carregar()
        
        # 4. Preencher ID Favorecido para consulta
        id_favorecido = self.driver.find_element(By.ID, "modal-id_favorecido")
        id_favorecido.clear()
        id_favorecido.send_keys("12345")  # Ajustar para ID válido
        
        # 5. Clicar em "Consultar OAMD"
        btn_consultar = self.driver.find_element(By.ID, "btn-consultar-oamd")
        btn_consultar.click()
        
        # Aguardar consulta completar (toast ou loading)
        time.sleep(2)
        
        # 6. Capturar valores preenchidos pela consulta
        valores_antes = {
            'responsavel_cliente': self.driver.find_element(By.ID, "modal-responsavel_cliente").get_attribute("value"),
            'email_responsavel': self.driver.find_element(By.ID, "modal-email_responsavel").get_attribute("value"),
            'telefone_responsavel': self.driver.find_element(By.ID, "modal-telefone_responsavel").get_attribute("value"),
            'id_favorecido': self.driver.find_element(By.ID, "modal-id_favorecido").get_attribute("value"),
            'chave_oamd': self.driver.find_element(By.ID, "modal-chave_oamd").get_attribute("value"),
            'cnpj': self.driver.find_element(By.ID, "modal-cnpj").get_attribute("value"),
        }
        
        print("\n📋 Valores ANTES de salvar:")
        for campo, valor in valores_antes.items():
            print(f"   {campo}: {valor}")
        
        # 7. Salvar
        btn_salvar = self.driver.find_element(By.CSS_SELECTOR, ".btn-salvar-detalhes")
        btn_salvar.click()
        
        # Aguardar toast de sucesso
        toast = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".toast.show"))
        )
        assert "sucesso" in toast.text.lower(), "❌ Salvamento falhou!"
        
        time.sleep(1)
        
        # 8. Fechar modal
        btn_fechar = self.driver.find_element(By.CSS_SELECTOR, '[data-bs-dismiss="modal"]')
        btn_fechar.click()
        
        self.wait.until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "#modalDetalhesEmpresa.show"))
        )
        
        # 9. VOLTAR PARA DASHBOARD
        self.driver.get("http://127.0.0.1:5000/dashboard")
        self.wait.until(EC.url_contains("/dashboard"))
        
        time.sleep(1)
        
        # 10. REABRIR A IMPLANTAÇÃO
        self.driver.get("http://127.0.0.1:5000/implantacao/1")
        
        time.sleep(1)
        
        # 11. REABRIR O MODAL
        btn_abrir2 = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-bs-target="#modalDetalhesEmpresa"]'))
        )
        btn_abrir2.click()
        
        # Aguardar modal aparecer e carregar
        self.wait.until(EC.visibility_of_element_located((By.ID, "modalDetalhesEmpresa")))
        self.aguardar_modal_carregar()
        
        # 12. CAPTURAR VALORES DEPOIS
        valores_depois = {
            'responsavel_cliente': self.driver.find_element(By.ID, "modal-responsavel_cliente").get_attribute("value"),
            'email_responsavel': self.driver.find_element(By.ID, "modal-email_responsavel").get_attribute("value"),
            'telefone_responsavel': self.driver.find_element(By.ID, "modal-telefone_responsavel").get_attribute("value"),
            'id_favorecido': self.driver.find_element(By.ID, "modal-id_favorecido").get_attribute("value"),
            'chave_oamd': self.driver.find_element(By.ID, "modal-chave_oamd").get_attribute("value"),
            'cnpj': self.driver.find_element(By.ID, "modal-cnpj").get_attribute("value"),
        }
        
        print("\n📋 Valores DEPOIS de reabrir:")
        for campo, valor in valores_depois.items():
            print(f"   {campo}: {valor}")
        
        # 13. VALIDAR: Valores devem ser IGUAIS
        print("\n🔍 Validando persistência...")
        
        erros = []
        for campo in valores_antes.keys():
            antes = valores_antes[campo] or ""
            depois = valores_depois[campo] or ""
            
            if antes != depois:
                erros.append(f"   ❌ {campo}: '{antes}' → '{depois}'")
            else:
                print(f"   ✅ {campo}: OK")
        
        # Resultado final
        if erros:
            print("\n❌ TESTE FALHOU! Inconsistências encontradas:")
            for erro in erros:
                print(erro)
            pytest.fail(f"Dados não persistiram! {len(erros)} campo(s) com problema.")
        else:
            print("\n✅ TESTE PASSOU! Todos os dados persistiram corretamente!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
