"""MCP Server für Bildausschnitt-Selektion.

Ermöglicht das interaktive Auswählen von Bildausschnitten über eine GUI.
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
if Server is not None and getattr(Server, '__name__', '') != 'object':
    app = Server('image-selector')

    @app.list_tools()
    async def list_tools() -> List[Any]:
        """Gib die Liste verfügbarer Tools zurück."""
        return [
            Tool(
                name='select_image_regions',
                description='Öffnet eine GUI zum interaktiven Auswählen von Bildausschnitten. '
                'Unterstützt Bildformate (JPEG, PNG, etc.) und PDF-Dateien. '
                'Bei PDFs wird das erste eingebettete Bild extrahiert oder die erste Seite gerendert. '
                'Bereiche können als "foto" oder "text" markiert werden. '
                'Ohne image_path werden automatisch die ersten 4 Bilder aus dem Bildverzeichnis geladen. '
                'Nach Abschluss werden die Bereiche automatisch exportiert. '
                'Alle erkannten Texte werden alphabetisch konkateniert und als full_recipe_text in der Antwort zurückgegeben.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'image_path': {
                            'type': 'string',
                            'description': 'Pfad zum Bild oder PDF (relativ zum Working Directory oder absolut). '
                            'Optional - ohne Angabe werden die ersten 4 Bilder aus dem Bildverzeichnis geladen.',
                        }
                    },
                },
            ),
            Tool(
                name='list_exported_regions',
                description='Listet alle exportierten Bildausschnitte aus dem Working Directory auf',
                inputSchema={
                    'type': 'object',
                    'properties': {},
                },
            ),
            Tool(
                name='get_working_directory',
                description='Zeigt das aktuelle Working Directory an',
                inputSchema={
                    'type': 'object',
                    'properties': {},
                },
            ),
        ]


if 'app' in globals():

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[Any]:
        """Verarbeite Tool-Aufrufe."""
        working_dir = get_working_dir()
        export_dir = create_tmp_dir_if_needed()

        if name == 'get_working_directory':
            return [TextContent(type='text', text=f'Working Directory: {working_dir}')]

        elif name == 'list_exported_regions':
            files = []
            for file in os.listdir(export_dir):
                if file.endswith(('.png', '.txt')):
                    files.append(file)

            files.sort()

            result = f'Exportierte Dateien in {export_dir}:\n\n'
            if files:
                result += '\n'.join(f'  - {f}' for f in files)
            else:
                result += '  (keine Dateien gefunden)'

            return [TextContent(type='text', text=result)]

        elif name == 'select_image_regions':
            image_path = arguments.get('image_path')

            # Relativen Pfad auflösen wenn angegeben
            if image_path:
                if not os.path.isabs(image_path):
                    image_path = os.path.join(working_dir, image_path)

                if not os.path.exists(image_path):
                    return [
                        TextContent(
                            type='text',
                            text=f'Fehler: Bild nicht gefunden: {image_path}',
                        )
                    ]

            # GUI starten (ohne image_path werden automatisch Bilder aus dem Bildverzeichnis geladen)
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
                                region['coords'] = transform_coords(
                                    region['coords'], img_data['scale_factor']
                                )

                            # Export für dieses Bild
                            result = export_regions(
                                img_data['original_path'],
                                img_data['regions'],
                                export_dir,
                                image_object=img_data['original_image'],
                            )

                            all_exported_files.extend(result['files'])
                            total_exported += result['exported_count']

                    if total_exported > 0:
                        response = f'✓ Erfolgreich {total_exported} Bereiche von {len(images_data)} Bild(ern) exportiert:\n\n'
                        for file_info in all_exported_files:
                            if file_info['type'] == 'foto':
                                response += f"  Region {file_info['region']} (FOTO): {os.path.basename(file_info['file'])}\n"
                            else:
                                response += f"  Region {file_info['region']} (TEXT):\n"
                                response += f"    - Bild: {os.path.basename(file_info['image_file'])}\n"
                                response += f"    - Text: {os.path.basename(file_info['text_file'])}\n"

                        response += f'\nAusgabeverzeichnis: {export_dir}'

                        # Alle Text-Dateien alphabetisch konkatenieren
                        text_files = sorted(
                            [
                                fi['text_file']
                                for fi in all_exported_files
                                if fi['type'] == 'text'
                            ],
                            key=lambda p: os.path.basename(p),
                        )
                        if text_files:
                            full_text_parts = []
                            for tf in text_files:
                                try:
                                    with open(tf, 'r', encoding='utf-8') as f:
                                        full_text_parts.append(f.read().strip())
                                except OSError:
                                    pass
                            if full_text_parts:
                                response += '\n\n--- full_recipe_text ---\n'
                                response += '\n\n'.join(full_text_parts)

                        return [TextContent(type='text', text=response)]
                    else:
                        return [
                            TextContent(
                                type='text',
                                text='Keine Bereiche zum Exportieren ausgewählt',
                            )
                        ]
                else:
                    return [
                        TextContent(
                            type='text',
                            text='Auswahl abgebrochen - keine Bereiche exportiert',
                        )
                    ]

            except Exception as e:
                return [
                    TextContent(
                        type='text', text=f'Fehler beim Öffnen der GUI: {str(e)}'
                    )
                ]

        return [TextContent(type='text', text=f'Unbekanntes Tool: {name}')]


async def main():
    """Starte den MCP Server asynchron."""
    if 'app' not in globals():
        print('Fehler: MCP Server konnte nicht initialisiert werden.', file=sys.stderr)
        print(
            "Bitte stellen Sie sicher, dass das 'mcp' Paket installiert ist:",
            file=sys.stderr,
        )
        print('  pip install mcp', file=sys.stderr)
        sys.exit(1)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    """Starte den MCP Server."""
    asyncio.run(main())


def run_standalone(image_path: str = None):
    """Starte die GUI im Standalone-Modus ohne MCP-Server.

    Args:
        image_path: Optional - Pfad zum initialen Bild. Wenn None, werden die
                    ersten 4 Bilddateien aus dem Arbeitsverzeichnis geladen.
    """
    # Working directory ermitteln
    working_dir = get_working_dir()
    export_dir = create_tmp_dir_if_needed()

    # Relativen Pfad auflösen wenn angegeben
    if image_path is not None:
        if not os.path.isabs(image_path):
            image_path = os.path.join(working_dir, image_path)

        if not os.path.exists(image_path):
            print(f'Fehler: Bild nicht gefunden: {image_path}')
            return

    try:
        # GUI starten (ohne image_path werden automatisch Bilder aus dem Arbeitsverzeichnis geladen)
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
                        region['coords'] = transform_coords(
                            region['coords'], img_data['scale_factor']
                        )

                    # Export für dieses Bild
                    result = export_regions(
                        img_data['original_path'],
                        img_data['regions'],
                        export_dir,
                        image_object=img_data['original_image'],
                    )

                    all_exported_files.extend(result['files'])
                    total_exported += result['exported_count']

            if total_exported > 0:
                print(
                    f'\n✓ Erfolgreich {total_exported} Bereiche von {len(images_data)} Bild(ern) exportiert:\n'
                )
                for file_info in all_exported_files:
                    if file_info['type'] == 'foto':
                        print(
                            f"  Region {file_info['region']} (FOTO): {os.path.basename(file_info['file'])}"
                        )
                    else:
                        print(f"  Region {file_info['region']} (TEXT):")
                        print(
                            f"    - Bild: {os.path.basename(file_info['image_file'])}"
                        )
                        print(f"    - Text: {os.path.basename(file_info['text_file'])}")

                print(f'\nAusgabeverzeichnis: {export_dir}')

                # Alle Text-Dateien alphabetisch konkatenieren
                text_files = sorted(
                    [
                        fi['text_file']
                        for fi in all_exported_files
                        if fi['type'] == 'text'
                    ],
                    key=lambda p: os.path.basename(p),
                )
                if text_files:
                    full_text_parts = []
                    for tf in text_files:
                        try:
                            with open(tf, 'r', encoding='utf-8') as f:
                                full_text_parts.append(f.read().strip())
                        except OSError:
                            pass
                    if full_text_parts:
                        print('\n--- full_recipe_text ---')
                        print('\n\n'.join(full_text_parts))
            else:
                print('Keine Bereiche zum Exportieren ausgewählt')
        else:
            print('Auswahl abgebrochen - keine Bereiche exportiert')

    except Exception as e:
        print(f'Fehler: {str(e)}')
        import traceback

        traceback.print_exc()


if __name__ == '__main__':
    # MCP-Modus (Default): python server.py
    # Standalone-Modus: python server.py --standalone [bildpfad]
    if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
        # Standalone-Modus
        image_path = sys.argv[2] if len(sys.argv) > 2 else None
        run_standalone(image_path)
    else:
        # MCP-Modus (default)
        run()
