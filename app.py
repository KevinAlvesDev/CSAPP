import customtkinter as ctk

ctk.set_appearance_mode("dark")

def validar_login():
    usuario = campo_usuario.get()
    senha = campo_senha.get()
    if usuario == 'KevinAlves' and senha == '123456':
        resultado_login.configure(text='Login bem-sucedido!', 
                               text_color='green')
    else:
        resultado_login.configure(text='Usuário ou senha incorretos.', 
                               text_color='red')

app = ctk.CTk()
app.title('CS Onboarding')
app.geometry('500x400')

label_usuario = ctk.CTkLabel(app, text='Usuário')
label_usuario.pack(pady=10)

campo_usuario = ctk.CTkEntry(app, placeholder_text='Digite seu usuário')
campo_usuario.pack(pady=5)

label_senha = ctk.CTkLabel(app, text='Senha:')
label_senha.pack(pady=5)

campo_senha = ctk.CTkEntry(app, placeholder_text='Digite sua senha', show='*')
campo_senha.pack(pady=5)

botao_login = ctk.CTkButton(app, text='Login', command=validar_login)
botao_login.pack(pady=10)

resultado_login = ctk.CTkLabel(app, text='')
resultado_login.pack(pady=10)

app.mainloop()