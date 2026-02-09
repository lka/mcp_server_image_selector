"""Utility-Funktionen für Dateioperationen und Verzeichnisverwaltung."""

import os
import sys


def get_working_dir() -> str:
    """Ermittle das Working Directory."""
    # Aus Umgebungsvariable oder aktuelles Verzeichnis
    working_dir = os.environ.get('IMAGE_SELECTOR_WORKING_DIR', os.getcwd())
    os.makedirs(working_dir, exist_ok=True)
    return working_dir


def get_image_subdirectory() -> str:
    """Ermittle das Unterverzeichnis für Bilder, falls definiert."""
    subdir = os.environ.get('IMAGE_SUBDIRECTORY', '')
    if subdir:
        full_path = os.path.join(get_working_dir(), subdir)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    return get_working_dir()


def create_tmp_dir_if_needed() -> str:
    """Erstelle ein temporäres Verzeichnis, falls nötig."""
    tmp_dir = os.path.join(get_working_dir(), 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir


def cleanup_tmp_dir():
    """Lösche alle Dateien im temporären Verzeichnis."""
    tmp_dir = create_tmp_dir_if_needed()
    if os.path.exists(tmp_dir):
        for file in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(
                    f'Fehler beim Löschen der Datei {file_path}: {e}', file=sys.stderr
                )


def transform_coords(coords: tuple, scale_factor: float) -> tuple:
    """Transformiert Display-Koordinaten zurück auf Original-Koordinaten mithilfe des scale_factors."""
    x1, y1, x2, y2 = coords
    if scale_factor == 0:
        raise ValueError('scale_factor must be non-zero')
    return (
        int(x1 / scale_factor),
        int(y1 / scale_factor),
        int(x2 / scale_factor),
        int(y2 / scale_factor),
    )
