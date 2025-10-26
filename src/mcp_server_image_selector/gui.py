"""
GUI-Komponente für die Bildausschnitt-Selektion
"""

import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os


class ImageSelectorGUI:
    """GUI-Komponente für die Bildauswahl"""

    def __init__(self, image_path: str, working_dir: str, create_ui: bool = True):
        from .utils import cleanup_tmp_dir

        self.working_dir = working_dir
        self.create_ui = create_ui
        self.result_ready = False
        cleanup_tmp_dir()

        # Multi-image support: Liste aller geladenen Bilder
        self.images_data = []  # Liste von Dicts: {original_path, image_path, is_pdf, extracted_path, original_image, scale_factor, regions}
        self.current_image_index = 0

        # GUI root and widgets are only created when create_ui is True.
        if self.create_ui:
            self.root = tk.Tk()
            self.root.title("Bildausschnitt-Selector - Multi-Image")
            # Fenster um 25% größer: 1250x1000 statt 1000x800
            self.root.geometry("700x800")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        else:
            self.root = None

        # Variablen für aktuelles Bild
        self.image = None
        self.photo = None
        self.canvas_image = None

        # Auswahlvariablen
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        # Only create tkinter variables when GUI is enabled
        if self.create_ui:
            self.selection_mode = tk.StringVar(value="foto")
        else:
            # lightweight dummy with get() method used by the code
            class _DummyVar:
                def __init__(self, v="foto"):
                    self._v = v

                def get(self):
                    return self._v

            self.selection_mode = _DummyVar("foto")
        self.current_selection = None

        # Erstes Bild laden
        self._add_image(image_path)

        if self.create_ui:
            self._setup_ui()
        # Always load the image data; display is conditional
        self._load_current_image()

    @staticmethod
    def compute_scale(img_width: int, img_height: int, canvas_width: int, canvas_height: int) -> float:
        """Berechnet den Skalierungsfaktor für ein Bild, begrenzt auf max 1.25 (25% vergrößert)."""
        if img_width <= 0 or img_height <= 0:
            return 1.0
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        # 25% Vergrößerung: max 1.25 statt 1.0
        return min(scale_x, scale_y, 1.25)

    def _add_image(self, image_path: str):
        """Fügt ein neues Bild zur Liste hinzu"""
        from pathlib import Path
        from .pdf_utils import extract_image_from_pdf

        is_pdf = image_path.lower().endswith('.pdf')
        extracted_path = None

        # Wenn PDF, extrahiere das Bild zuerst
        if is_pdf:
            if Path(image_path).is_absolute():
                extracted_path = extract_image_from_pdf(image_path)
            else:
                extracted_path = extract_image_from_pdf(os.path.join(self.working_dir, image_path))
            if extracted_path is None:
                raise ValueError(f"Konnte kein Bild aus PDF extrahieren: {image_path}")
            actual_image_path = extracted_path
        else:
            actual_image_path = image_path

        # Bild-Daten zur Liste hinzufügen
        image_data = {
            'original_path': image_path,
            'image_path': actual_image_path,
            'is_pdf': is_pdf,
            'extracted_path': extracted_path,
            'original_image': None,  # Wird bei _load_current_image geladen
            'scale_factor': 1.0,
            'regions': []
        }
        self.images_data.append(image_data)

    # Properties für Rückwärtskompatibilität (greifen auf aktuelles Bild zu)
    @property
    def original_image_path(self):
        """Gibt den original Pfad des aktuellen Bildes zurück"""
        if self.images_data:
            return self.images_data[self.current_image_index]['original_path']
        return None

    @property
    def image_path(self):
        """Gibt den Pfad des aktuellen Bildes zurück (kann extrahiert sein bei PDF)"""
        if self.images_data:
            return self.images_data[self.current_image_index]['image_path']
        return None

    @property
    def is_pdf(self):
        """Gibt zurück ob das aktuelle Bild ein PDF ist"""
        if self.images_data:
            return self.images_data[self.current_image_index]['is_pdf']
        return False

    @property
    def extracted_image_path(self):
        """Gibt den extrahierten Pfad zurück (bei PDF)"""
        if self.images_data:
            return self.images_data[self.current_image_index]['extracted_path']
        return None

    @property
    def original_image(self):
        """Gibt das Original PIL Image des aktuellen Bildes zurück"""
        if self.images_data:
            return self.images_data[self.current_image_index]['original_image']
        return None

    @original_image.setter
    def original_image(self, value):
        """Setzt das Original PIL Image für das aktuelle Bild"""
        if self.images_data:
            self.images_data[self.current_image_index]['original_image'] = value

    @property
    def scale_factor(self):
        """Gibt den Skalierungsfaktor des aktuellen Bildes zurück"""
        if self.images_data:
            return self.images_data[self.current_image_index]['scale_factor']
        return 1.0

    @scale_factor.setter
    def scale_factor(self, value):
        """Setzt den Skalierungsfaktor für das aktuelle Bild"""
        if self.images_data:
            self.images_data[self.current_image_index]['scale_factor'] = value

    @property
    def regions(self):
        """Gibt die Regionen des aktuellen Bildes zurück"""
        if self.images_data:
            return self.images_data[self.current_image_index]['regions']
        return []

    @regions.setter
    def regions(self, value):
        """Setzt die Regionen für das aktuelle Bild"""
        if self.images_data:
            self.images_data[self.current_image_index]['regions'] = value

    def _setup_ui(self):  # pragma: no cover
        """Erstellt die Benutzeroberfläche"""
        # Toolbar
        toolbar = tk.Frame(self.root, relief=tk.RAISED, borderwidth=2)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Hamburger-Menü Button
        menu_btn = tk.Button(
            toolbar,
            text="☰",
            command=self.show_menu,
            font=("Arial", 16),
            width=2,
            relief=tk.FLAT
        )
        menu_btn.pack(side=tk.LEFT, padx=5)

        # Separator
        tk.Frame(toolbar, width=2, relief=tk.SUNKEN, borderwidth=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=5
        )

        # Modus-Auswahl
        tk.Label(toolbar, text="Modus:").pack(side=tk.LEFT, padx=5)
        foto_radio = tk.Radiobutton(
            toolbar, text="Foto", variable=self.selection_mode, value="foto"
        )
        foto_radio.pack(side=tk.LEFT)
        text_radio = tk.Radiobutton(
            toolbar, text="Text", variable=self.selection_mode, value="text"
        )
        text_radio.pack(side=tk.LEFT, padx=5)

        # Buttons
        save_current_btn = tk.Button(
            toolbar,
            text="Auswahl speichern",
            command=self.save_current_selection,
            bg="#4CAF50",
            fg="white",
        )
        save_current_btn.pack(side=tk.LEFT, padx=20)

        finish_btn = tk.Button(
            toolbar,
            text="✓ Fertig & Exportieren",
            command=self.finish_selection,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        finish_btn.pack(side=tk.LEFT, padx=5)

        clear_btn = tk.Button(
            toolbar,
            text="Bereiche löschen",
            command=self.clear_regions,
            bg="#f44336",
            fg="white",
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        # Canvas Frame
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="gray",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # Mouse Events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        # Statusleiste
        self.status_bar = tk.Label(
            self.root,
            text="Bereit - Ziehen Sie mit der Maus einen Bereich auf",
            relief=tk.SUNKEN,
            anchor=tk.W,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Listen-Frame (Horizontal Layout)
        list_frame = tk.Frame(self.root)
        list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        # Bildliste (links)
        image_list_frame = tk.Frame(list_frame)
        image_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(
            image_list_frame, text="Geladene Bilder:", font=("Arial", 10, "bold")
        ).pack()

        self.image_listbox = tk.Listbox(image_list_frame, width=25)
        self.image_listbox.pack(fill=tk.BOTH, expand=True)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        self._update_image_list()

        # Image navigation label (shows current image)
        self.image_nav_label = tk.Label(
            image_list_frame,
            text=f"Bild 1/{len(self.images_data)}",
            font=("Arial", 9, "bold"),
            fg="#555"
        )
        self.image_nav_label.pack(pady=5)

        # Regions-Liste (rechts)
        region_list_frame = tk.Frame(list_frame)
        region_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(
            region_list_frame, text="Gespeicherte Bereiche:", font=("Arial", 10, "bold")
        ).pack()

        self.region_listbox = tk.Listbox(region_list_frame, width=25)
        self.region_listbox.pack(fill=tk.BOTH, expand=True)

    def _load_current_image(self):  # pragma: no cover
        """Lädt das aktuell ausgewählte Bild"""
        try:
            # Lade PIL Image wenn noch nicht geladen
            if self.original_image is None:
                img = Image.open(self.image_path)
                self.original_image = img

            # If GUI is created, display on canvas. Otherwise compute scale only.
            if self.create_ui:
                self._display_image()
            else:
                # use default canvas fallback sizes as in _display_image
                canvas_width = 1600  # 25% größer als 1280
                canvas_height = 1280  # 25% größer als 1024
                img_width, img_height = self.original_image.size
                self.scale_factor = self.compute_scale(img_width, img_height, canvas_width, canvas_height)
                # Precompute a resized image for downstream processing if desired
                new_width = int(img_width * self.scale_factor)
                new_height = int(img_height * self.scale_factor)
                self.image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception as e:
            if self.create_ui:
                messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden: {e}")
                self.root.destroy()
            else:
                raise

    def _display_image(self):  # pragma: no cover
        """Zeigt das Bild auf dem Canvas an"""
        if self.original_image:
            # Skalierung berechnen
            # Skalierung berechnen
            self.root.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1:
                canvas_width = 1600  # 25% größer als 1280
            if canvas_height <= 1:
                canvas_height = 1280  # 25% größer als 1024

            img_width, img_height = self.original_image.size
            self.scale_factor = self.compute_scale(img_width, img_height, canvas_width, canvas_height)

            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)

            self.image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(self.image)

            self.canvas.config(scrollregion=(0, 0, new_width, new_height))
            self.canvas.delete("all")
            self.canvas_image = self.canvas.create_image(
                0, 0, anchor=tk.NW, image=self.photo
            )

    def _update_image_list(self):  # pragma: no cover
        """Aktualisiert die Bildliste"""
        if not self.create_ui:
            return

        self.image_listbox.delete(0, tk.END)
        for idx, img_data in enumerate(self.images_data):
            base_name = os.path.basename(img_data['original_path'])
            if img_data['is_pdf']:
                base_name += " (PDF)"
            region_count = len(img_data['regions'])
            marker = "▶ " if idx == self.current_image_index else "  "
            self.image_listbox.insert(tk.END, f"{marker}{base_name} [{region_count} Bereiche]")
            if idx == self.current_image_index:
                self.image_listbox.selection_set(idx)

    def add_image(self):  # pragma: no cover
        """Öffnet Dialog zum Hinzufügen eines neuen Bildes"""
        from .utils import get_working_dir

        file_types = [
            ("Alle unterstützten Formate", "*.png *.jpg *.jpeg *.bmp *.gif *.pdf"),
            ("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.gif"),
            ("PDF-Dateien", "*.pdf"),
            ("Alle Dateien", "*.*")
        ]

        # Standardverzeichnis ist working_dir/Eingang
        eingang_dir = os.path.join(get_working_dir(), "Eingang")
        if not os.path.exists(eingang_dir):
            eingang_dir = get_working_dir()

        file_path = filedialog.askopenfilename(
            title="Bild hinzufügen",
            filetypes=file_types,
            initialdir=eingang_dir
        )

        if file_path:
            try:
                self._add_image(file_path)
                self._update_image_list()
                # Update navigation label
                self.image_nav_label.config(text=f"Bild {self.current_image_index + 1}/{len(self.images_data)}")
                self.status_bar.config(text=f"✓ Bild hinzugefügt: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Bild nicht hinzufügen: {e}")

    def on_image_select(self, event):  # pragma: no cover
        """Wird aufgerufen wenn ein Bild in der Liste ausgewählt wird"""
        selection = self.image_listbox.curselection()
        if selection:
            new_index = selection[0]
            if new_index != self.current_image_index:
                self._switch_to_image(new_index)

    def _switch_to_image(self, index: int):  # pragma: no cover
        """Wechselt zum Bild mit dem angegebenen Index"""
        if 0 <= index < len(self.images_data):
            # Aktuelle Auswahl verwerfen
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None
            self.current_selection = None

            # Index aktualisieren
            self.current_image_index = index

            # Bild laden und anzeigen
            self._load_current_image()

            # Regions-Liste aktualisieren
            self.region_listbox.delete(0, tk.END)
            for i, region in enumerate(self.regions, 1):
                coords = region["coords"]
                mode = region["mode"]
                x1, y1, x2, y2 = coords
                list_text = f"{i}. {mode.upper()} ({int(x2 - x1)}x{int(y2 - y1)})"
                self.region_listbox.insert(tk.END, list_text)

            # Bildliste und Navigation aktualisieren
            self._update_image_list()
            self.image_nav_label.config(text=f"Bild {index + 1}/{len(self.images_data)}")

            # Statusmeldung
            img_name = os.path.basename(self.original_image_path)
            self.status_bar.config(text=f"Gewechselt zu: {img_name}")

    def show_menu(self):  # pragma: no cover
        """Zeigt das Hamburger-Menü an"""
        menu = tk.Menu(self.root, tearoff=0)

        # Multi-Image Menü
        menu.add_command(label="🖼️ Bilder verwalten", state="disabled")
        menu.add_command(label="  ➕ Bild hinzufügen", command=self.add_image)

        menu.add_separator()

        # Rotation-Menü
        menu.add_command(label="🔄 Bild drehen", state="disabled")
        menu.add_command(label="  ↺ 90° links", command=lambda: self.rotate_image(-90))
        menu.add_command(label="  ↻ 90° rechts", command=lambda: self.rotate_image(90))
        menu.add_command(label="  ↻ 180°", command=lambda: self.rotate_image(180))

        menu.add_separator()
        menu.add_command(label="📖 Hilfe", command=self.show_help)
        menu.add_separator()
        menu.add_command(label="ℹ️ Über", command=self.show_about)
        menu.add_separator()
        menu.add_command(label="🚪 Beenden", command=self.on_closing)

        # Menü an der Mausposition anzeigen
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()

    def show_help(self):  # pragma: no cover
        """Zeigt das modale Hilfefenster an"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Hilfe - Bildausschnitt-Selector")
        help_window.geometry("500x450")
        help_window.resizable(False, False)

        # Fenster modal machen
        help_window.transient(self.root)
        help_window.grab_set()

        # Zentriere das Fenster
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (help_window.winfo_screenheight() // 2) - (450 // 2)
        help_window.geometry(f"500x450+{x}+{y}")

        # Titel
        title_label = tk.Label(
            help_window,
            text="🖼️ Bildausschnitt-Selector",
            font=("Arial", 16, "bold"),
            pady=10
        )
        title_label.pack()

        # Scrollbarer Text-Bereich
        text_frame = tk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        help_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            padx=10,
            pady=10
        )
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=help_text.yview)

        # Hilfetext
        help_content = """
📌 GRUNDFUNKTIONEN

1️⃣ Bild öffnen
   • Der Server startet mit einem initial angegebenen Bild oder PDF
   • PDF-Dateien werden automatisch verarbeitet

2️⃣ Weitere Bilder hinzufügen
   • Button "+ Bild hinzufügen" in der Toolbar
   • Zwischen Bildern wechseln durch Klick in der Bildliste

3️⃣ Regionen auswählen
   • Modus wählen: "Foto" oder "Text"
   • Mit der Maus einen Bereich aufziehen
   • "Auswahl speichern" klicken

4️⃣ Bild rotieren
   • Buttons zum Drehen um 90° links, 90° rechts oder 180°
   • Bereiche werden beim Rotieren zurückgesetzt

5️⃣ Export
   • "Fertig & Exportieren" exportiert alle Regionen von allen Bildern
   • Dateien werden im tmp-Verzeichnis gespeichert


🎯 MODI

• FOTO: Für Bildausschnitte (blaue Markierung)
  → Export als PNG-Datei

• TEXT: Für Textbereiche (grüne Markierung)
  → Export als PNG + TXT-Datei (Template)


📁 DATEINAMEN

Format: bildname_timestamp_regionXX_modus.png

Beispiel:
  dokument1_20250122_143022_region01_foto.png
  dokument2_20250122_143022_region02_text.png


💡 TIPPS

• Die Bildliste zeigt: ▶ dateiname.jpg [3 Bereiche]
• Jedes Bild kann unabhängig bearbeitet werden
• Bei PDF: Erstes Bild wird extrahiert oder Seite gerendert
• Alle Exporte landen im gleichen tmp-Verzeichnis


⌨️ WORKFLOW-BEISPIEL

1. Erste Datei wird geladen
2. Bereiche markieren und speichern
3. "+ Bild hinzufügen" für weitere Dateien
4. In Bildliste zwischen Dokumenten wechseln
5. Bereiche in allen Bildern markieren
6. "Fertig & Exportieren" → Alle werden exportiert
        """

        help_text.insert("1.0", help_content)
        help_text.config(state=tk.DISABLED)  # Readonly

        # Schließen-Button
        close_btn = tk.Button(
            help_window,
            text="Schließen",
            command=help_window.destroy,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15
        )
        close_btn.pack(pady=10)

        # Focus auf Fenster
        help_window.focus_set()

    def show_about(self):  # pragma: no cover
        """Zeigt das Über-Fenster an"""
        about_window = tk.Toplevel(self.root)
        about_window.title("Über")
        about_window.geometry("400x250")
        about_window.resizable(False, False)

        # Fenster modal machen
        about_window.transient(self.root)
        about_window.grab_set()

        # Zentriere das Fenster
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (about_window.winfo_screenheight() // 2) - (250 // 2)
        about_window.geometry(f"400x250+{x}+{y}")

        # Icon/Titel
        title_label = tk.Label(
            about_window,
            text="🖼️",
            font=("Arial", 48)
        )
        title_label.pack(pady=10)

        # Info-Text
        info_text = """
MCP Server Image Selector
Version 1.0.0

Ein MCP-kompatibler Server für interaktive
Bildausschnitt-Selektion mit Multi-Bild-Support.

© 2025
MIT License
        """

        info_label = tk.Label(
            about_window,
            text=info_text,
            font=("Arial", 10),
            justify=tk.CENTER
        )
        info_label.pack(pady=10)

        # Schließen-Button
        close_btn = tk.Button(
            about_window,
            text="OK",
            command=about_window.destroy,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10
        )
        close_btn.pack(pady=10)

    def on_mouse_down(self, event):  # pragma: no cover
        """Maus-Klick Event"""
        if self.image:
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)

            if self.current_rect:
                self.canvas.delete(self.current_rect)

    def on_mouse_drag(self, event):  # pragma: no cover
        """Maus-Zieh Event"""
        if self.image and self.start_x is not None:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)

            if self.current_rect:
                self.canvas.delete(self.current_rect)

            color = "blue" if self.selection_mode.get() == "foto" else "green"

            self.current_rect = self.canvas.create_rectangle(
                self.start_x,
                self.start_y,
                cur_x,
                cur_y,
                outline=color,
                width=3,
                dash=(5, 5),
            )

    def on_mouse_up(self, event):  # pragma: no cover
        """Maus-Loslassen Event"""
        if self.image and self.start_x is not None:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            x1 = min(self.start_x, end_x)
            y1 = min(self.start_y, end_y)
            x2 = max(self.start_x, end_x)
            y2 = max(self.start_y, end_y)

            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                self.current_selection = (x1, y1, x2, y2)
                self.status_bar.config(
                    text=f"Auswahl: {int(x2 - x1)}x{int(y2 - y1)} px - "
                    f"Klicken Sie 'Auswahl speichern' zum Hinzufügen"
                )
            else:
                if self.current_rect:
                    self.canvas.delete(self.current_rect)
                    self.current_rect = None
                self.current_selection = None

    def save_current_selection(self):
        """Speichert die aktuelle Auswahl"""
        if self.current_selection is None:
            messagebox.showwarning(
                "Keine Auswahl", "Bitte wählen Sie zuerst einen Bereich aus."
            )
            return

        mode = self.selection_mode.get()
        region = {
            "coords": self.current_selection,
            "mode": mode,
            "rect_id": self.current_rect,
        }

        self.regions.append(region)

        x1, y1, x2, y2 = self.current_selection
        list_text = f"{len(self.regions)}. {mode.upper()} ({int(x2 - x1)}x{int(y2 - y1)})"
        self.region_listbox.insert(tk.END, list_text)

        self.status_bar.config(
            text=f"✓ Bereich {len(self.regions)} gespeichert ({mode})"
        )

        if self.current_rect:
            # color = "blue" if mode == "foto" else "green"
            self.canvas.itemconfig(self.current_rect, dash=())

        self.current_rect = None
        self.current_selection = None

        # Update image list to show new region count
        if self.create_ui:
            self._update_image_list()

    def clear_regions(self):  # pragma: no cover
        """Löscht alle gespeicherten Bereiche"""
        if self.regions:
            if messagebox.askyesno("Bestätigen", "Alle Bereiche löschen?"):
                for region in self.regions:
                    if region["rect_id"]:
                        self.canvas.delete(region["rect_id"])
                self.regions = []
                self.region_listbox.delete(0, tk.END)
                self.status_bar.config(text="Alle Bereiche gelöscht")
                # Update image list to show cleared region count
                self._update_image_list()

    def rotate_image(self, angle: int):  # pragma: no cover
        """Dreht das Bild um den angegebenen Winkel (90, -90, oder 180 Grad)"""
        if not self.original_image:
            return

        # PIL rotate ist gegen den Uhrzeigersinn, aber expand=True passt die Größe an
        # Für 90° rechts nutzen wir -90
        if angle == 90:
            # 90° rechts = -90° in PIL (oder 270° gegen Uhrzeigersinn)
            self.original_image = self.original_image.rotate(-90, expand=True)
        elif angle == -90:
            # 90° links = 90° in PIL
            self.original_image = self.original_image.rotate(90, expand=True)
        elif angle == 180:
            self.original_image = self.original_image.rotate(180, expand=True)

        # Clear current selection and regions when rotating
        # Only access GUI elements if create_ui is True
        if self.create_ui:
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None
        else:
            self.current_rect = None

        self.current_selection = None

        # Delete all saved regions (since they won't match after rotation)
        if self.regions:
            if self.create_ui:
                for region in self.regions:
                    if region["rect_id"]:
                        self.canvas.delete(region["rect_id"])
                self.region_listbox.delete(0, tk.END)
            self.regions = []

        # Refresh display only if GUI is active
        if self.create_ui:
            self._display_image()
            # Update status
            rotation_text = "90° rechts" if angle == 90 else ("90° links" if angle == -90 else "180°")
            self.status_bar.config(text=f"Bild um {rotation_text} gedreht - Bereiche wurden zurückgesetzt")
        else:
            # Update scale factor and resized image for non-GUI mode
            img_width, img_height = self.original_image.size
            canvas_width = 1600  # 25% größer als 1280
            canvas_height = 1280  # 25% größer als 1024
            self.scale_factor = self.compute_scale(img_width, img_height, canvas_width, canvas_height)
            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)
            self.image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def finish_selection(self):  # pragma: no cover
        """Beendet die Auswahl und exportiert"""
        # Zähle alle Regionen von allen Bildern
        total_regions = sum(len(img_data['regions']) for img_data in self.images_data)

        if total_regions == 0:
            messagebox.showwarning(
                "Keine Bereiche", "Bitte wählen Sie mindestens einen Bereich aus."
            )
            return

        message = f"{total_regions} Bereiche von {len(self.images_data)} Bild(ern) exportieren?"
        if messagebox.askyesno("Bestätigen", message):
            self.result_ready = True
            self.root.quit()
            self.root.destroy()

    def on_closing(self):  # pragma: no cover
        """Wird beim Schließen des Fensters aufgerufen"""
        if messagebox.askokcancel(
            "Beenden",
            "Möchten Sie wirklich beenden? Nicht exportierte Bereiche gehen verloren.",
        ):
            self.result_ready = False
            self.root.quit()
            self.root.destroy()

    def run(self):
        """Startet die GUI und gibt alle Bilder mit ihren Regionen zurück"""
        self.root.mainloop()
        if self.result_ready:
            # Gebe alle Bilder mit ihren Regionen zurück
            return self.images_data
        return None
