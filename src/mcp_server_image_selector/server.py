"""
MCP Server für Bildausschnitt-Selektion
Ermöglicht das interaktive Auswählen von Bildausschnitten über eine GUI
"""

import asyncio
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from pathlib import Path
import os
# import json
from typing import Any, List, Optional
from datetime import datetime
# from pathlib import Path
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent  # , ImageContent, EmbeddedResource
    import mcp.server.stdio  # type: ignore
except Exception:
    # MCP package not available in test environment; define placeholders
    Server = None
    Tool = None
    TextContent = None
    # ensure submodule names exist to avoid import errors elsewhere
    try:
        import mcp.server.stdio  # type: ignore
    except Exception:
        pass


def extract_image_from_pdf(pdf_path: str, working_dir: Optional[str] = None) -> Optional[str]:
    """
    Extrahiert das erste Bild aus einem PDF oder erstellt ein Rendering der ersten Seite.

    Args:
        pdf_path: Pfad zur PDF-Datei
        working_dir: Optional - Verzeichnis für das extrahierte Bild. Wenn None, wird ./tmp verwendet.

    Returns:
        Pfad zum extrahierten Bild oder None bei Fehler
    """
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) ist nicht installiert. Bitte installieren: pip install PyMuPDF")

    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None

        page = doc[0]  # Erste Seite

        # Versuche zunächst, eingebettete Bilder zu extrahieren
        image_list = page.get_images(full=True)

        if working_dir is None:
            output_dir = create_tmp_dir_if_needed('.')
        else:
            output_dir = create_tmp_dir_if_needed(working_dir)

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        if image_list:
            # Nimm das erste Bild
            xref = image_list[0][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            output_path = os.path.join(output_dir, f"{base_name}_extracted.png")

            with open(output_path, "wb") as img_file:
                img_file.write(image_bytes)

            doc.close()
            return output_path
        else:
            # Kein eingebettetes Bild gefunden - rendere die Seite als Bild
            # Hohe Auflösung für bessere Qualität
            mat = fitz.Matrix(2.0, 2.0)  # 2x Zoom = 144 DPI
            pix = page.get_pixmap(matrix=mat)

            output_path = os.path.join(output_dir, f"{base_name}_rendered.png")

            pix.save(output_path)
            doc.close()
            return output_path

    except Exception as e:
        print(f"Fehler beim Extrahieren des Bildes aus PDF: {e}", file=sys.stderr)
        return None


class ImageSelectorGUI:
    """GUI-Komponente für die Bildauswahl"""

    def __init__(self, image_path: str, working_dir: str, create_ui: bool = True):
        self.original_image_path = image_path
        self.is_pdf = image_path.lower().endswith('.pdf')
        self.extracted_image_path = None
        cleanup_tmp_dir()

        # Wenn PDF, extrahiere das Bild zuerst
        if self.is_pdf:
            if Path(image_path).is_absolute():
                self.extracted_image_path = extract_image_from_pdf(image_path,
                                                                   working_dir)
            else:
                self.extracted_image_path = extract_image_from_pdf(os.path.join(working_dir, image_path),
                                                                   working_dir)
            if self.extracted_image_path is None:
                raise ValueError(f"Konnte kein Bild aus PDF extrahieren: {image_path}")
            self.image_path = self.extracted_image_path
        else:
            self.image_path = image_path

        self.working_dir = working_dir
        self.regions = []
        self.result_ready = False
        self.create_ui = create_ui

        # GUI root and widgets are only created when create_ui is True.
        if self.create_ui:
            self.root = tk.Tk()
            title_name = os.path.basename(self.original_image_path)
            if self.is_pdf:
                title_name += " (PDF)"
            self.root.title(f"Bildausschnitt-Selector - {title_name}")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        else:
            self.root = None

        # Variablen
        self.image = None
        self.photo = None
        self.canvas_image = None
        self.original_image = None
        self.scale_factor = 1.0

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

        if self.create_ui:
            self._setup_ui()
        # Always load the image data; display is conditional
        self._load_image()

    @staticmethod
    def compute_scale(img_width: int, img_height: int, canvas_width: int, canvas_height: int) -> float:
        """Berechnet den Skalierungsfaktor für ein Bild, begrenzt auf max 1.0."""
        if img_width <= 0 or img_height <= 0:
            return 1.0
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        return min(scale_x, scale_y, 1.0)

    def _setup_ui(self):  # pragma: no cover
        """Erstellt die Benutzeroberfläche"""
        # Toolbar
        toolbar = tk.Frame(self.root, relief=tk.RAISED, borderwidth=2)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

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

        # Separator
        tk.Frame(toolbar, width=2, relief=tk.SUNKEN, borderwidth=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        # Rotation buttons
        tk.Label(toolbar, text="Drehen:").pack(side=tk.LEFT, padx=5)
        rotate_left_btn = tk.Button(
            toolbar,
            text="↺ 90° links",
            command=lambda: self.rotate_image(-90),
            bg="#FF9800",
            fg="white",
        )
        rotate_left_btn.pack(side=tk.LEFT, padx=2)

        rotate_right_btn = tk.Button(
            toolbar,
            text="↻ 90° rechts",
            command=lambda: self.rotate_image(90),
            bg="#FF9800",
            fg="white",
        )
        rotate_right_btn.pack(side=tk.LEFT, padx=2)

        rotate_180_btn = tk.Button(
            toolbar,
            text="↻ 180°",
            command=lambda: self.rotate_image(180),
            bg="#FF9800",
            fg="white",
        )
        rotate_180_btn.pack(side=tk.LEFT, padx=2)

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

        # Listen-Frame
        list_frame = tk.Frame(self.root)
        list_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        tk.Label(
            list_frame, text="Gespeicherte Bereiche:", font=("Arial", 10, "bold")
        ).pack()

        self.region_listbox = tk.Listbox(list_frame, width=35, height=10)
        self.region_listbox.pack(fill=tk.BOTH, expand=True)

        # Anleitung
        help_frame = tk.Frame(list_frame, relief=tk.GROOVE, borderwidth=2)
        help_frame.pack(fill=tk.X, pady=10)

        help_text = """
Anleitung:
1. Wählen Sie Modus (Foto/Text)
2. Ziehen Sie einen Bereich auf
3. Klicken Sie 'Auswahl speichern'
4. Wiederholen Sie für weitere Bereiche
5. Klicken Sie 'Fertig' zum Exportieren
        """
        tk.Label(help_frame, text=help_text, justify=tk.LEFT, font=("Arial", 8)).pack(
            padx=5, pady=5
        )

    def _load_image(self):  # pragma: no cover
        """Lädt das Bild"""
        try:
            self.original_image = Image.open(self.image_path)
            # If GUI is created, display on canvas. Otherwise compute scale only.
            if self.create_ui:
                self._display_image()
            else:
                # use default canvas fallback sizes as in _display_image
                canvas_width = 1280
                canvas_height = 1024
                img_width, img_height = self.original_image.size
                self.scale_factor = self.compute_scale(img_width, img_height, canvas_width, canvas_height)
                # Precompute a resized image for downstream processing if desired
                new_width = int(img_width * self.scale_factor)
                new_height = int(img_height * self.scale_factor)
                self.image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception as e:
            messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden: {e}")
            self.root.destroy()

    def _display_image(self):  # pragma: no cover
        """Zeigt das Bild auf dem Canvas an"""
        if self.original_image:
            # Skalierung berechnen
            # Skalierung berechnen
            self.root.update()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1:
                canvas_width = 1280
            if canvas_height <= 1:
                canvas_height = 1024

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
            canvas_width = 1280
            canvas_height = 1024
            self.scale_factor = self.compute_scale(img_width, img_height, canvas_width, canvas_height)
            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)
            self.image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def finish_selection(self):  # pragma: no cover
        """Beendet die Auswahl und exportiert"""
        if not self.regions:
            messagebox.showwarning(
                "Keine Bereiche", "Bitte wählen Sie mindestens einen Bereich aus."
            )
            return

        if messagebox.askyesno(
            "Bestätigen", f"{len(self.regions)} Bereiche exportieren?"
        ):
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
        """Startet die GUI"""
        self.root.mainloop()
        return self.regions if self.result_ready else None


# MCP Server Setup
if Server is not None and getattr(Server, "__name__", "") != "object":
    app = Server("image-selector")

    @app.list_tools()
    async def list_tools() -> List[Any]:
        """Liste verfügbarer Tools"""
        return [
            Tool(
                name="select_image_regions",
                description="Öffnet eine GUI zum interaktiven Auswählen von Bildausschnitten. "
                "Unterstützt Bildformate (JPEG, PNG, etc.) und PDF-Dateien. "
                "Bei PDFs wird das erste eingebettete Bild extrahiert oder die erste Seite gerendert. "
                "Bereiche können als 'foto' oder 'text' markiert werden. "
                "Nach Abschluss werden die Bereiche automatisch exportiert.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Pfad zum Bild oder PDF (relativ zum Working Directory oder absolut)",
                        }
                    },
                    "required": ["image_path"],
                },
            ),
            Tool(
                name="list_exported_regions",
                description="Listet alle exportierten Bildausschnitte aus dem Working Directory auf",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_working_directory",
                description="Zeigt das aktuelle Working Directory an",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]


def get_working_dir() -> str:
    """Ermittelt das Working Directory"""
    # Aus Umgebungsvariable oder aktuelles Verzeichnis
    working_dir = os.environ.get("IMAGE_SELECTOR_WORKING_DIR", os.getcwd())
    os.makedirs(working_dir, exist_ok=True)
    return working_dir


def create_tmp_dir_if_needed(base_dir: str) -> str:
    """Erstellt ein temporäres Verzeichnis, falls nötig"""
    tmp_dir = os.path.join(base_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir


def cleanup_tmp_dir():
    """Löscht das temporäre Verzeichnis, falls es nicht leer ist"""
    tmp_dir = create_tmp_dir_if_needed(get_working_dir())
    if os.path.exists(tmp_dir):
        for file in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Fehler beim Löschen der Datei {file_path}: {e}", file=sys.stderr)


def transform_coords(coords: tuple, scale_factor: float) -> tuple:
    """Transformiert Display-Koordinaten zurück auf Original-Koordinaten mithilfe des scale_factors."""
    x1, y1, x2, y2 = coords
    if scale_factor == 0:
        raise ValueError("scale_factor must be non-zero")
    return (int(x1 / scale_factor), int(y1 / scale_factor), int(x2 / scale_factor), int(y2 / scale_factor))


def format_export_paths(base_name: str, timestamp: str, i: int, mode: str, working_dir: str) -> dict:
    """Erzeugt die Ausgabe-Pfade für einen exportierten Bereich.

    Rückgabe: dict mit keys abhängig vom Modus ('foto' -> file, 'text' -> image_file,text_file).
    """
    if mode == "foto":
        output_file = os.path.join(working_dir, f"{base_name}_{timestamp}_region{i:02d}_foto.png")
        return {"type": "foto", "file": output_file, "region": i}
    else:
        img_file = os.path.join(working_dir, f"{base_name}_{timestamp}_region{i:02d}_text.png")
        text_file = os.path.join(working_dir, f"{base_name}_{timestamp}_region{i:02d}_text.txt")
        return {"type": "text", "image_file": img_file, "text_file": text_file, "region": i}


def export_regions(image_path: str, regions: list, working_dir: str, image_object: Image.Image = None) -> dict:
    """Exportiert die ausgewählten Bereiche

    Args:
        image_path: Pfad zum Originalbild (für Dateinamen)
        regions: Liste der zu exportierenden Bereiche
        working_dir: Ausgabeverzeichnis
        image_object: Optional - bereits geladenes/gedrehtes PIL Image Objekt.
                     Wenn None, wird das Bild von image_path geladen.
    """

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use provided image object if available (e.g., after rotation),
    # otherwise load from file
    if image_object is not None:
        original_image = image_object
    else:
        original_image = Image.open(image_path)

    # Ermittle scale_factor (falls nötig - hier nehmen wir an, coords sind bereits original)
    # In der GUI werden die Koordinaten bereits umgerechnet

    exported_files = []

    for i, region in enumerate(regions, 1):
        coords = region["coords"]
        mode = region["mode"]

        # coords sind in Display-Koordinaten - hier müssten sie umgerechnet werden
        # Für dieses Beispiel gehen wir davon aus, dass sie bereits korrekt sind
        x1, y1, x2, y2 = coords

        # Direkt als Original-Koordinaten verwenden (GUI sollte diese liefern)
        # Hier vereinfachte Annahme - in Produktion scale_factor übergeben

        try:
            # crop using provided coordinates
            crop = original_image.crop((int(x1), int(y1), int(x2), int(y2)))

            info = format_export_paths(base_name, timestamp, i, mode, working_dir)

            if info["type"] == "foto":
                crop.save(info["file"], "PNG")
                exported_files.append(info)
            else:
                crop.save(info["image_file"], "PNG")
                with open(info["text_file"], "w", encoding="utf-8") as f:
                    f.write(f"Textbereich {i}\n")
                    f.write(f"Bildquelle: {info['image_file']}\n")
                    f.write(f"Original: {image_path}\n")
                    f.write("\n[OCR-Text hier einfügen]\n")
                exported_files.append(info)

        except Exception as e:
            print(f"Fehler beim Export von Region {i}: {e}", file=sys.stderr)

    return {
        "success": True,
        "exported_count": len(exported_files),
        "files": exported_files,
        "working_dir": working_dir,
    }


if 'app' in globals():
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[Any]:
        """Tool-Aufrufe verarbeiten"""

        working_dir = get_working_dir()
        export_dir = create_tmp_dir_if_needed(working_dir)

        if name == "get_working_directory":
            return [TextContent(type="text", text=f"Working Directory: {working_dir}")]

        elif name == "list_exported_regions":
            files = []
            for file in os.listdir(export_dir):
                if file.endswith((".png", ".txt")):
                    files.append(file)

            files.sort()

            result = f"Exportierte Dateien in {export_dir}:\n\n"
            if files:
                result += "\n".join(f"  - {f}" for f in files)
            else:
                result += "  (keine Dateien gefunden)"

            return [TextContent(type="text", text=result)]

        elif name == "select_image_regions":
            image_path = arguments.get("image_path")

            if not image_path:
                return [TextContent(type="text", text="Fehler: image_path erforderlich")]

            # Relativen Pfad auflösen
            if not os.path.isabs(image_path):
                image_path = os.path.join(working_dir, image_path)

            if not os.path.exists(image_path):
                return [
                    TextContent(
                        type="text", text=f"Fehler: Bild nicht gefunden: {image_path}"
                    )
                ]

            # GUI in separatem Thread starten (Tkinter braucht Main-Thread)
            # Für MCP verwenden wir einen synchronen Ansatz
            try:
                gui = ImageSelectorGUI(image_path, export_dir)
                regions = gui.run()

                if regions:
                    # Exportieren mit scale_factor aus GUI
                    scale_factor = gui.scale_factor

                    # Koordinaten umrechnen
                    for region in regions:
                        region["coords"] = transform_coords(region["coords"], scale_factor)

                    # Pass the rotated image from GUI to export_regions
                    result = export_regions(image_path, regions, export_dir, image_object=gui.original_image)

                    response = (
                        f"✓ Erfolgreich {result['exported_count']} Bereiche exportiert:\n\n"
                    )
                    for file_info in result["files"]:
                        if file_info["type"] == "foto":
                            response += f"  Region {file_info['region']} (FOTO): {os.path.basename(file_info['file'])}\n"
                        else:
                            response += f"  Region {file_info['region']} (TEXT):\n"
                            response += (
                                f"    - Bild: {os.path.basename(file_info['image_file'])}\n"
                            )
                            response += (
                                f"    - Text: {os.path.basename(file_info['text_file'])}\n"
                            )

                    response += f"\nAusgabeverzeichnis: {export_dir}"

                    return [TextContent(type="text", text=response)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text="Auswahl abgebrochen - keine Bereiche exportiert",
                        )
                    ]

            except Exception as e:
                return [
                    TextContent(type="text", text=f"Fehler beim Öffnen der GUI: {str(e)}")
                ]

        return [TextContent(type="text", text=f"Unbekanntes Tool: {name}")]


async def main():
    """Hauptfunktion"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    """Startet den MCP Server"""
    asyncio.run(main())


if __name__ == "__main__":
    run()
