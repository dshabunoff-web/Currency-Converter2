import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import os
import requests

# ---------- Конфигурация API ----------
# Используйте свой ключ реального API
API_KEY = "YOUR_API_KEY"
BASE_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/"

# ---------- Модели данных ----------
class ConversionRecord:
    def __init__(self, src, dst, amount, rate, result, ts):
        self.src = src
        self.dst = dst
        self.amount = float(amount)
        self.rate = float(rate)
        self.result = float(result)
        self.date = ts  # ISO-8601

    def to_dict(self):
        return {
            "src": self.src,
            "dst": self.dst,
            "amount": self.amount,
            "rate": self.rate,
            "result": self.result,
            "date": self.date,
        }

    @staticmethod
    def from_dict(d):
        return ConversionRecord(d["src"], d["dst"], d["amount"], d["rate"], d["result"], d["date"])

# ---------- Приложение ----------
class CurrencyConverterApp:
    HISTORY_FILE = "currency_history.json"

    def __init__(self, root):
        self.root = root
        self.root.title("Currency Converter")
        self.root.geometry("900x550")

        self.records = []  # история конвертаций
        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        # Верхняя панель ввода
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Из:", font=("Segoe UI", 12)).pack(side="left", padx=(0,6))
        self.src_var = tk.StringVar(value="USD")
        self.src_cb = ttk.Combobox(top, textvariable=self.src_var, width=10, state="readonly")
        self.src_cb['values'] = ["USD","EUR","GBP","JPY","CNY","UAH","RUB"]
        self.src_cb.pack(side="left", padx=6)
        self.src_cb.current(0)

        ttk.Label(top, text="В:", font=("Segoe UI", 12)).pack(side="left", padx=(6,0))
        self.dst_var = tk.StringVar(value="EUR")
        self.dst_cb = ttk.Combobox(top, textvariable=self.dst_var, width=10, state="readonly")
        self.dst_cb['values'] = ["USD","EUR","GBP","JPY","CNY","UAH","RUB"]
        self.dst_cb.pack(side="left", padx=6)
        self.dst_cb.current(1)

        ttk.Label(top, text="Сумма:", font=("Segoe UI", 12)).pack(side="left", padx=(6,0))
        self.amount_var = tk.StringVar(value="100")
        ttk.Entry(top, textvariable=self.amount_var, width=12).pack(side="left", padx=6)

        ttk.Button(top, text="Конвертировать", command=self.convert).pack(side="left", padx=6)

        # Результат
        result_frame = ttk.Frame(self.root, padding=(10,5))
        result_frame.pack(fill="x")
        self.result_var = tk.StringVar(value="Результат: -")
        ttk.Label(result_frame, textvariable=self.result_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")

        # Основная часть: история
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        hist_frame = ttk.LabelFrame(main, text="История конвертаций", padding=6)
        hist_frame.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(hist_frame, columns=("date","src","dst","amount","rate","result"), show="headings")
        self.tree.heading("date", text="Дата")
        self.tree.heading("src", text="Из")
        self.tree.heading("dst", text="В")
        self.tree.heading("amount", text="Сумма")
        self.tree.heading("rate", text="Курс")
        self.tree.heading("result", text="Результат")
        self.tree.column("date", width=120)
        self.tree.column("src", width=60)
        self.tree.column("dst", width=60)
        self.tree.column("amount", width=90, anchor="e")
        self.tree.column("rate", width=90, anchor="e")
        self.tree.column("result", width=90, anchor="e")
        self.tree.pack(fill="both", expand=True)

        btns = ttk.Frame(hist_frame)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Очистить историю", command=self.clear_history).pack(side="left", padx=6)
        ttk.Button(btns, text="Экспорт истории", command=self.export_history).pack(side="left", padx=6)
        ttk.Button(btns, text="Импорт истории", command=self.import_history).pack(side="left")

        # Правый: фильтры истории
        filter_frame = ttk.LabelFrame(main, text="Фильтры истории", padding=6)
        filter_frame.pack(side="right", fill="both", expand=True)

        ttk.Label(filter_frame, text="Дата после (YYYY-MM-DD):").grid(row=0, column=0, sticky="e", pady=2)
        self.filter_after_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_after_var, width=14).grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(filter_frame, text="Из валюты:").grid(row=1, column=0, sticky="e", pady=2)
        self.filter_src_var = tk.StringVar(value="Все")
        self.filter_src_cb = ttk.Combobox(filter_frame, textvariable=self.filter_src_var, width=12, state="readonly")
        self.filter_src_cb['values'] = ["Все","USD","EUR","GBP","JPY","CNY","UAH","RUB"]
        self.filter_src_cb.grid(row=1, column=1, sticky="w", pady=2)
        self.filter_src_cb.current(0)

        ttk.Label(filter_frame, text="Поиск по заметке:").grid(row=2, column=0, sticky="e", pady=2)
        self.filter_note_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_note_var, width=20).grid(row=2, column=1, sticky="w", pady=2)

        ttk.Button(filter_frame, text="Применить", command=self.apply_filters).grid(row=3, column=0, columnspan=2, pady=6)
        ttk.Button(filter_frame, text="Стереть фильтры", command=self.reset_filters).grid(row=4, column=0, columnspan=2, pady=6)

        # Меню
        self._setup_menu()

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Сохранить как...", command=self.export_history)
        filemenu.add_command(label="Импорт истории", command=self.import_history)
        filemenu.add_separator()
        filemenu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=helpmenu)

    def _show_about(self):
        messagebox.showinfo("О программе", "Currency Converter — конвертация валют через внешний API, сохранение истории и Git.")

    # ---------- Логика конвертации ----------
    def convert(self):
        src = self.src_var.get()
        dst = self.dst_var.get()
        amount_text = self.amount_var.get()
        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Сумма должна быть числом.")
            return

        if src == dst:
            rate = 1.0
            result = amount
        else:
            rate = self.fetch_rate(src, dst)
            if rate is None:
                return
            result = amount * rate

        ts = datetime.utcnow().isoformat()
        rec = ConversionRecord(src, dst, amount, rate, result, ts)
        self.records.append(rec)
        self._append_to_history_tree(rec)

        self.result_var.set(f"{amount:.2f} {src} = {result:.4f} {dst} (курс {rate:.6f})")
        self._save_history()

    def fetch_rate(self, src, dst):
        url = BASE_URL.format(key=API_KEY)
        try:
            resp = requests.get(url + dst, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "conversion_rate" in data:
                return float(data["conversion_rate"])
            elif "conversion_rates" in data and dst in data["conversion_rates"]:
                return float(data["conversion_rates"][dst])
            elif "rates" in data and dst in data["rates"]:
                return float(data["rates"][dst])
            else:
                return float(data.get("rate", 1.0))
        except Exception as e:
            messagebox.showerror("Ошибка API", f"Не удалось получить курс: {e}")
            return None

    def _append_to_history_tree(self, rec: ConversionRecord):
        self.tree.insert("", "end", values=(
            rec.date[:19], rec.src, rec.dst, f"{rec.amount:.2f}", f"{rec.rate:.6f}", f"{rec.result:.6f}"
        ))

    # ---------- История и файлы ----------
    def _load_history(self):
        if not os.path.exists(self.HISTORY_FILE):
            return
        try:
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = [ConversionRecord.from_dict(d) for d in data]
            self.refresh_history_tree()
        except Exception as e:
            messagebox.showwarning("Чтение истории", f"Не удалось загрузить историю: {e}")

    def refresh_history_tree(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.records:
            self.tree.insert("", "end", values=(
                r.date, r.src, r.dst, f"{r.amount:.2f}", f"{r.rate:.6f}", f"{r.result:.6f}"
            ))

    def clear_history(self):
        if messagebox.askyesno("Очистить историю", "Удалить всю историю конвертаций?"):
            self.records.clear()
            self.refresh_history_tree()
            self._save_history()

    def _save_history(self):
        data = [r.to_dict() for r in self.records]
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def export_history(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON files","*.json")])
        if not path:
            return
        data = [r.to_dict() for r in self.records]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Успех", "История экспортирована.")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def import_history(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files","*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = [ConversionRecord.from_dict(d) for d in data]
            self.refresh_history_tree()
            self._save_history()
            messagebox.showinfo("Успех", "История импортирована.")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    # ---------- Фильтры ----------
    def apply_filters(self):
        start = self.filter_after_var.get()
        ftype = self.filter_type_var.get() if hasattr(self, "filter_type_var") else "Все"
        self._filter_and_update(start, ftype)

    def _filter_and_update(self, start, ftype):
        self.tree.delete(*self.tree.get_children())
        total = 0.0
        for r in self.records:
            if start:
                try:
                    dt = datetime.fromisoformat(r.date)
                    start_dt = datetime.fromisoformat(start)
                    if dt < start_dt:
                        continue
                except ValueError:
                    pass
            if ftype != "Все" and r.src != ftype and r.dst != ftype:
                continue
            self._append_to_history_tree(r)
            total += r.amount
        self._update_summary(total)

    def reset_filters(self):
        if hasattr(self, "start_date_var"):
            self.start_date_var.set("")
        if hasattr(self, "filter_type_var"):
            self.filter_type_var.set("Все")
        self.apply_filters()

    def _update_summary(self, total):
        self.result_var.set(f"Итого за период: {total:.2f} ед.")

# ---------- Запуск ----------
def main():
    root = tk.Tk()
    app = CurrencyConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()