"""
MCP Server für Bildausschnitt-Selektion
Ermöglicht das interaktive Auswählen von Bildausschnitten über eine GUI
"""

import asyncio
import os
from typing import Any, List
import sys

# Lokale Imports
from .gui import ImageSelectorGUI
from .utils import get_working_dir, create_tmp_dir_if_needed, transform_coords
from .export import export_regions

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
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


if 'app' in globals():
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[Any]:
        """Tool-Aufrufe verarbeiten"""

        working_dir = get_working_dir()
        export_dir = create_tmp_dir_if_needed()

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
                images_data = gui.run()

                if images_data:
                    # Exportiere alle Regionen von allen Bildern
                    all_exported_files = []
                    total_exported = 0

                    for img_data in images_data:
                        if img_data['regions']:
                            # Koordinaten umrechnen
                            for region in img_data['regions']:
                                region["coords"] = transform_coords(
                                    region["coords"],
                                    img_data['scale_factor']
                                )

                            # Export für dieses Bild
                            result = export_regions(
                                img_data['original_path'],
                                img_data['regions'],
                                export_dir,
                                image_object=img_data['original_image']
                            )

                            all_exported_files.extend(result["files"])
                            total_exported += result["exported_count"]

                    if total_exported > 0:
                        response = (
                            f"✓ Erfolgreich {total_exported} Bereiche von {len(images_data)} Bild(ern) exportiert:\n\n"
                        )
                        for file_info in all_exported_files:
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
                                text="Keine Bereiche zum Exportieren ausgewählt",
                            )
                        ]
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
    if 'app' not in globals():
        print("Fehler: MCP Server konnte nicht initialisiert werden.", file=sys.stderr)
        print("Bitte stellen Sie sicher, dass das 'mcp' Paket installiert ist:", file=sys.stderr)
        print("  pip install mcp", file=sys.stderr)
        sys.exit(1)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    """Startet den MCP Server"""
    asyncio.run(main())


def run_standalone(image_path: str = None):
    """Startet die GUI im Standalone-Modus ohne MCP-Server

    Args:
        image_path: Optional - Pfad zum initialen Bild. Wenn None, wird ein Dateiauswahl-Dialog geöffnet.
    """
    import tkinter as tk
    from tkinter import filedialog

    # Working directory ermitteln
    working_dir = get_working_dir()
    export_dir = create_tmp_dir_if_needed()

    # Wenn kein Bildpfad angegeben, Dateiauswahl-Dialog öffnen
    if image_path is None:
        root = tk.Tk()
        root.withdraw()  # Hauptfenster verstecken

        eingang_dir = os.path.join(working_dir, "Eingang")
        if not os.path.exists(eingang_dir):
            eingang_dir = working_dir

        file_types = [
            ("Alle unterstützten Formate", "*.png *.jpg *.jpeg *.bmp *.gif *.pdf"),
            ("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.gif"),
            ("PDF-Dateien", "*.pdf"),
            ("Alle Dateien", "*.*")
        ]

        image_path = filedialog.askopenfilename(
            title="Bild auswählen",
            filetypes=file_types,
            initialdir=eingang_dir
        )

        root.destroy()

        if not image_path:
            print("Keine Datei ausgewählt. Abbruch.")
            return

    # Relativen Pfad auflösen
    if not os.path.isabs(image_path):
        image_path = os.path.join(working_dir, image_path)

    if not os.path.exists(image_path):
        print(f"Fehler: Bild nicht gefunden: {image_path}")
        return

    try:
        # GUI starten
        gui = ImageSelectorGUI(image_path, export_dir)
        images_data = gui.run()

        if images_data:
            # Exportiere alle Regionen von allen Bildern
            all_exported_files = []
            total_exported = 0

            for img_data in images_data:
                if img_data['regions']:
                    # Koordinaten umrechnen
                    for region in img_data['regions']:
                        region["coords"] = transform_coords(
                            region["coords"],
                            img_data['scale_factor']
                        )

                    # Export für dieses Bild
                    result = export_regions(
                        img_data['original_path'],
                        img_data['regions'],
                        export_dir,
                        image_object=img_data['original_image']
                    )

                    all_exported_files.extend(result["files"])
                    total_exported += result["exported_count"]

            if total_exported > 0:
                print(f"\n✓ Erfolgreich {total_exported} Bereiche von {len(images_data)} Bild(ern) exportiert:\n")
                for file_info in all_exported_files:
                    if file_info["type"] == "foto":
                        print(f"  Region {file_info['region']} (FOTO): {os.path.basename(file_info['file'])}")
                    else:
                        print(f"  Region {file_info['region']} (TEXT):")
                        print(f"    - Bild: {os.path.basename(file_info['image_file'])}")
                        print(f"    - Text: {os.path.basename(file_info['text_file'])}")

                print(f"\nAusgabeverzeichnis: {export_dir}")
            else:
                print("Keine Bereiche zum Exportieren ausgewählt")
        else:
            print("Auswahl abgebrochen - keine Bereiche exportiert")

    except Exception as e:
        print(f"Fehler: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # MCP-Modus (Default): python server.py
    # Standalone-Modus: python server.py --standalone [bildpfad]
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # Standalone-Modus
        image_path = sys.argv[2] if len(sys.argv) > 2 else None
        run_standalone(image_path)
    else:
        # MCP-Modus (default)
        run()
