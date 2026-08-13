# -*- coding: utf-8 -*-

from tkinter import filedialog

import customtkinter as ctk

from main import run_automation_process


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_TESTLINK_URL = "https://testlink-web-service.onrender.com/lib/api/xmlrpc/v1/xmlrpc.php"


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("TestLink Automation")
        self.geometry("1000x700")
        self.minsize(800, 600)

        self.excel_path = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.build_title()
        self.build_config_frame()
        self.build_excel_frame()
        self.build_logs_frame()

    def build_title(self):
        title_label = ctk.CTkLabel(
            self,
            text="TestLink Automation",
            font=ctk.CTkFont(size=26, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

    def build_config_frame(self):
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        server_label = ctk.CTkLabel(
            config_frame,
            text="Servidor: QA EMCALI Smartflex",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        server_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        devkey_label = ctk.CTkLabel(config_frame, text="DevKey:")
        devkey_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.devkey_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="DevKey",
            show="*",
        )
        self.devkey_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    def build_excel_frame(self):
        excel_frame = ctk.CTkFrame(self)
        excel_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        excel_frame.grid_columnconfigure(1, weight=1)

        select_button = ctk.CTkButton(
            excel_frame,
            text="Seleccionar Excel",
            command=self.seleccionar_excel,
        )
        select_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.excel_path_label = ctk.CTkLabel(
            excel_frame,
            text="Ningun archivo seleccionado",
            anchor="w",
        )
        self.excel_path_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        load_button = ctk.CTkButton(
            excel_frame,
            text="Cargar a TestLink",
            command=self.cargar_a_testlink,
        )
        load_button.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

    def build_logs_frame(self):
        logs_frame = ctk.CTkFrame(self)
        logs_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")
        logs_frame.grid_columnconfigure((0, 1, 2), weight=1)
        logs_frame.grid_rowconfigure(1, weight=1)

        creados_label = ctk.CTkLabel(logs_frame, text="CREADOS", font=ctk.CTkFont(weight="bold"))
        creados_label.grid(row=0, column=0, padx=10, pady=(10, 5))

        omitidos_label = ctk.CTkLabel(logs_frame, text="OMITIDOS", font=ctk.CTkFont(weight="bold"))
        omitidos_label.grid(row=0, column=1, padx=10, pady=(10, 5))

        errores_label = ctk.CTkLabel(logs_frame, text="ERRORES", font=ctk.CTkFont(weight="bold"))
        errores_label.grid(row=0, column=2, padx=10, pady=(10, 5))

        self.creados_box = ctk.CTkTextbox(logs_frame)
        self.creados_box.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self.omitidos_box = ctk.CTkTextbox(logs_frame)
        self.omitidos_box.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="nsew")

        self.errores_box = ctk.CTkTextbox(logs_frame)
        self.errores_box.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="nsew")

    def log_message(self, textbox, message):
        textbox.insert("end", message + "\n")
        textbox.see("end")

    def seleccionar_excel(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Archivos Excel", "*.xlsx")],
        )

        if file_path:
            self.excel_path = file_path
            self.excel_path_label.configure(text=file_path)

    def format_item(self, item):
        item_type = item.get("type", "")

        if item_type == "HU":
            label = item.get("hu_name", "")
        elif item_type == "CP":
            label = f"{item.get('hu_name', '')} -> {item.get('cp_id', '')}"
        elif item_type == "SHEET":
            label = item.get("sheet_name", "")
        else:
            label = str(item)

        detail = item.get("reason") or item.get("error")

        if detail:
            return f"[{item_type}] {label} ({detail})"

        return f"[{item_type}] {label}"

    def cargar_a_testlink(self):
        if not self.excel_path:
            self.log_message(self.errores_box, "Selecciona un archivo Excel antes de continuar.")
            return

        devkey = self.devkey_entry.get().strip()

        if not devkey:
            self.log_message(self.errores_box, "Completa el DevKey antes de continuar.")
            return

        self.creados_box.delete("1.0", "end")
        self.omitidos_box.delete("1.0", "end")
        self.errores_box.delete("1.0", "end")

        self.log_message(self.creados_box, "Procesando archivo, por favor espera...")
        self.update()

        resultado = run_automation_process(
            excel_path=self.excel_path,
            testlink_url=DEFAULT_TESTLINK_URL,
            devkey=devkey,
        )

        self.creados_box.delete("1.0", "end")

        for item in resultado["created_items"]:
            self.log_message(self.creados_box, self.format_item(item))

        for item in resultado["skipped_items"]:
            self.log_message(self.omitidos_box, self.format_item(item))

        for item in resultado["error_items"]:
            self.log_message(self.errores_box, self.format_item(item))

        if not resultado["created_items"]:
            self.log_message(self.creados_box, "Sin elementos creados.")

        if not resultado["skipped_items"]:
            self.log_message(self.omitidos_box, "Sin elementos omitidos.")

        if not resultado["error_items"]:
            self.log_message(self.errores_box, "Sin errores.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
