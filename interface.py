import tkinter as tk
from tkinter import ttk

# Colores y estilos personalizados
PRIMARY_COLOR = "#4CAF50"
SECONDARY_COLOR = "#388E3C"
BUTTON_COLOR = "#FFC107"
BACKGROUND_COLOR = "#F5F5F5"
TEXT_COLOR = "#FFFFFF"
FONT = ("Helvetica", 12)

class SignInteractApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SignInteract")
        self.geometry("800x600")
        self.configure(bg=BACKGROUND_COLOR)

        # Crear la interfaz principal
        self.create_main_interface()

    def create_main_interface(self):
        # Título de la aplicación
        title_label = tk.Label(self, text="SignInteract", font=("Helvetica", 24, "bold"), bg=PRIMARY_COLOR, fg=TEXT_COLOR)
        title_label.pack(pady=10)

        # Botones para cada módulo
        modules_frame = tk.Frame(self, bg=BACKGROUND_COLOR)
        modules_frame.pack(pady=20)

        self.create_module_button(modules_frame, "Módulo de Entrada de Signos", self.open_sign_input_module)
        self.create_module_button(modules_frame, "Módulo de Interpretación", self.open_interpretation_module)
        self.create_module_button(modules_frame, "Módulo de Administración", self.open_admin_module)
        self.create_module_button(modules_frame, "Módulo de Autenticación", self.open_auth_module)
        self.create_module_button(modules_frame, "Módulo de Reportes", self.open_reports_module)

    def create_module_button(self, parent, text, command):
        button = tk.Button(
            parent,
            text=text,
            font=FONT,
            bg=BUTTON_COLOR,
            fg=TEXT_COLOR,
            activebackground=SECONDARY_COLOR,
            activeforeground=TEXT_COLOR,
            relief="flat",
            command=command,
            width=25
        )
        button.pack(pady=10)
        button.configure(highlightbackground=PRIMARY_COLOR, highlightthickness=1, borderwidth=1)

    # Métodos para cada módulo (estos pueden ser ampliados)
    def open_sign_input_module(self):
        self.show_message("Abriendo Módulo de Entrada de Signos...")

    def open_interpretation_module(self):
        self.show_message("Abriendo Módulo de Interpretación...")

    def open_admin_module(self):
        self.show_message("Abriendo Módulo de Administración...")

    def open_auth_module(self):
        self.show_message("Abriendo Módulo de Autenticación...")

    def open_reports_module(self):
        self.show_message("Abriendo Módulo de Reportes...")

    def show_message(self, message):
        message_label = tk.Label(self, text=message, font=FONT, bg=BACKGROUND_COLOR, fg=SECONDARY_COLOR)
        message_label.pack(pady=5)
        # Ocultar mensaje después de un tiempo
        self.after(2000, message_label.destroy)

# Crear y ejecutar la aplicación
if __name__ == "__main__":
    app = SignInteractApp()
    app.mainloop()
