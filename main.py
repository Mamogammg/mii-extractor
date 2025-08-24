from utils import region_parse as parse
import FreeSimpleGUI as sg
from utils.virtual_amiibo_file import VirtualAmiiboFile, JSONVirtualAmiiboFile, InvalidAmiiboDump, AmiiboHMACTagError, AmiiboHMACDataError, InvalidMiiSizeError
#from utils.updater import Updater
from utils.config import Config
import os
from tkinter import filedialog
from windows import template
from copy import deepcopy
from windows import hexview
from utils.section_manager import ImplicitSumManager
from windows import about
from windows import metadata_transplant
from windows import initialize
from windows import theme
import ctypes

myappid = u'sae.editor.sae.1.7.0' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# initialize amiibo file variable
amiibo = None

# initializes the config class
config = Config()

def get_menu_def():
    """
    Creates menu definition for window

    :param bool update_available: If update is available or not
    :param bool amiibo_loaded: If amiibo has been loaded or not
    :param bool ryujinx: if loaded amiibo is ryujinx json
    :return: tuple of menu
    """
#    if amiibo_loaded:
#        file_tab = ['&File', ['&Open (CTRL+O)']]
#        mii_tab = ["&Mii", ["&Dump Mii"]]
#    else:
#        file_tab = ['&File', ['&Open (CTRL+O)']]
#        mii_tab = ["!&Mii", ["&Dump Mii"]]
    #settings_tab = ['&Settings', ['Select &Key(s)']]
    #return file_tab, mii_tab, settings_tab



"""def create_window(location=None, size=None):
    Creates the window of the application

    :param List[Sections] sections: list of section objects
    :param str column_key: key for column
    :param bool update: whether or not an update is available
    :param Tuple(int, int) location: window location to use
    :param Tuple(int, int) size: window size to use
    :return: window object
    #section_layout, last_key = create_layout_from_sections(sections)
    #menu_def = get_menu_def(update, False)

    #layout = [[sg.Menu(menu_def)],
    #          [sg.Text("The amiibo's personality is: None", key="PERSONALITY")],
    #          [sg.Column(section_layout, size=(None, 180), scrollable=True, vertical_scroll_only=True,
    #                     element_justification='left', key=column_key, expand_x=True, expand_y=True)],
    #          [sg.Button("Load", key="LOAD_AMIIBO", enable_events=True),
    #           sg.Button("Save", key="SAVE_AMIIBO", enable_events=True, disabled=True),
    #           sg.Checkbox("Shuffle SN", key="SHUFFLE_SN", default=False)]]
    if config.read_keys() is None:
        layout = [[sg.Text("Press the button to import the keys:")],
                  [sg.Button("Load keys", key="Select Key(s)")]]
    elif amiibo == None:
        layout = [[sg.Text("Press the button to import the amiibo dump in .bin format:")],
                  [sg.Button("Load amiibo", key="LOAD_AMIIBO")]]
    else:
        layout = [[sg.Text("Press the button to download the mii:")],
                  [sg.Button("Download", key="Dump Mii")]]

    #[sg.Menu(menu_def)], [sg.Text("Select the keys, import the amiibo dump in .bin format and dump the amiibo.")]]
    if location is not None:
        window = sg.Window("Mii Extractor", layout, resizable=True, location=location, size=size, icon="SAE.ico")
    else:
        window = sg.Window("Mii Extractor", layout, resizable=True, icon="SAE.ico")

    window.finalize()

    # adds event to spin widgets
    # disables all options until bin is loaded
    #for i in range(1, last_key+1):
    #    window[str(i)].bind('<KeyPress>', '')
    #    try:
    #        window[str(i)].update(disabled=True)
    #    # deals with bit numbers not having disabled property
    #    except TypeError:
    #        pass

    # for windows Control works, for MacOS change to Command

    # hot key for opening
    window.bind('<Control-o>', "Open (CTRL+O)")
    # hot key for loading template
    window.bind('<Control-l>', "Load (CTRL+L)")
    # hot key for saving gets set when an amiibo is loaded

    # needed or else window will be super small (because of menu items?)
    window.set_min_size((700, 500))
    return window
"""
def create_window(location=None, size=None):
    global amiibo, config

    page_keys = sg.Column(
        [
            [sg.Text("Press the button to import the keys:")],
            [sg.Button("Load keys", key="Select Key(s)")]
        ],
        key="PAGE_KEYS",
        visible=(config.read_keys() is None)
    )

    page_amiibo = sg.Column(
        [
            [sg.Text("Press the button to import the amiibo dump in .bin or .json format:")],
            [sg.Button("Load amiibo", key="LOAD_AMIIBO")]
        ],
        key="PAGE_AMIIBO",
        visible=(config.read_keys() is not None and amiibo is None)
    )

    page_dump = sg.Column(
        [
            [sg.Text("Press the button to download the mii:")],
            [sg.Button("Download", key="Dump Mii")]
        ],
        key="PAGE_DUMP",
        visible=(amiibo is not None)
    )

    layout = [[
        page_keys,
        page_amiibo,
        page_dump,
    ]]

    if location is not None:
        window = sg.Window("Mii Extractor", layout, resizable=True, location=location, size=size, icon="SAE.ico")
    else:
        window = sg.Window("Mii Extractor", layout, resizable=True, icon="SAE.ico")

    window.finalize()
    window.set_min_size((700, 500))

    # Atajos si los necesitas
    window.bind('<Control-o>', "Open (CTRL+O)")
    window.bind('<Control-l>', "Load (CTRL+L)")
    return window

def show_page(window, keys: bool = False, amiibo_page: bool = False, dump: bool = False):
    window["PAGE_KEYS"].update(visible=keys)
    window["PAGE_AMIIBO"].update(visible=amiibo_page)
    window["PAGE_DUMP"].update(visible=dump)

def goto_correct_page(window):
    # Decide automáticamente qué mostrar según el estado actual
    if config.read_keys() is None:
        show_page(window, keys=True)
    elif amiibo is None:
        show_page(window, amiibo_page=True)
    else:
        show_page(window, dump=True)


def show_reload_warning():
    """
    Runs a pop up window that asks user if it's okay to reset editing progress

    :return: Ok or Cancel input from popup window
    """
    popup = sg.PopupOKCancel('Doing this will reset your editing progress, continue?')
    return popup

def show_missing_key_warning():
    """
    Runs a pop up window telling the user to set keys

    :return: Ok or Cancel input from popup window
    """
    popup = sg.popup(f"Amiibo encryption key(s) are missing.\nThese keys are for encrypting/decrypting amiibo.\
                     \nYou can get them by searching for them on the internet.\nPlease select keys using Settings > Select Key",
                    title="Missing Key!")
    return popup

def reload_window(window):
    """
    Reloads the window

    :param sg.Window window: old window
    :param list[Section()] sections: list of section objects
    :param str column_key: key for column
    :param bool update: whether or not it should be updated
    :return: newly created window
    """
    window1 = create_window(window.CurrentLocation(), window.size)
    window.close()
    return window1


def create_layout_from_sections(sections):
    """
    Creates GUI objects from section list

    :param list[Section()] sections: list of section objects
    :return: List of lists of gui widgets, last key index used
    """
    output = []

    # key index 0 is reserved for menu items
    key_index = 1
    for section in sections:
        layout, new_index = section.get_widget(key_index)
        output += layout
        key_index = new_index

    return output, key_index - 1


def main():
    global config, amiibo
    if os.path.isfile(os.path.join(os.getcwd(), "update.exe")):
        os.remove(os.path.join(os.getcwd(), "update.exe"))

    sg.theme(config.get_color())

    # Avisos iniciales
    if config.read_keys() is None:
        sg.popup('Key files not present!\nPlease select key(s) using Settings > Select Key(s)')

    if config.get_region_path() is None:
        sg.popup('Region file not present! Please put a regions.txt or regions.json in the resources folder.')

    # Si quieres mantener la carga de regiones, déjala. No es necesaria para este flujo mínimo.
    # try:
    #     ...
    # except FileNotFoundError:
    #     sg.popup("Regions file could not be found, please check your config.")
    #     return

    config.save_config()

    window = create_window()
    goto_correct_page(window)

    while True:
        event, values = window.read()

        match event:
            case "LOAD_AMIIBO" | "Open (CTRL+O)":
                if config.read_keys() is None:
                    show_missing_key_warning()
                    continue

                # Diálogo de abrir (sin tkinter)
                path = sg.popup_get_file(
                    "Select amiibo dump (.bin or .json)",
                    file_types=(('amiibo files', '*.bin *.json'),),
                    no_window=True,
                    multiple_files=False
                )
                if not path:
                    continue

                try:
                    if path.endswith(".json"):
                        amiibo = JSONVirtualAmiiboFile(path, config.read_keys())
                    else:
                        amiibo = VirtualAmiiboFile(path, config.read_keys())
                        if not amiibo.is_initialized():
                            amiibo = initialize.open_initialize_amiibo_window(amiibo)

                    if amiibo is None:
                        continue

                    # Cambia a la pantalla de descarga
                    show_page(window, dump=True)

                except (InvalidAmiiboDump, AmiiboHMACTagError, AmiiboHMACDataError):
                    sg.popup("Invalid amiibo dump.", title='Incorrect Dump!')
                    continue
                except FileNotFoundError:
                    show_missing_key_warning()
                    continue

            case 'Select Key(s)':
                # Permitir múltiples .bin
                sel = sg.popup_get_file(
                    "Select key file(s)",
                    file_types=(('BIN files', '*.bin'),),
                    multiple_files=True,
                    no_window=True
                )
                if not sel:
                    continue

                # popup_get_file con multiple_files=True puede devolver str con ';' o lista
                if isinstance(sel, str):
                    key_paths = [s for s in sel.split(';') if s.strip()]
                else:
                    key_paths = list(sel)

                if not key_paths:
                    continue

                config.write_key_paths(*key_paths)
                config.save_config()

                # Cambia a pantalla de cargar amiibo
                show_page(window, amiibo_page=True)

            case "Dump Mii":
                if amiibo is None:
                    continue
                save_path = sg.popup_get_file(
                    "Save 3DSMII file",
                    save_as=True,
                    default_extension='.3dsmii',
                    file_types=(('3DSMII files', '*.3dsmii'),),
                    no_window=True
                )
                if not save_path:
                    continue
                amiibo.dump_mii(save_path)
                sg.popup("Mii dumped successfully!")

            case sg.WIN_CLOSED | sg.WINDOW_CLOSED | None:
                break

            case _:
                pass

    window.close()


if __name__ == "__main__":
    main()
