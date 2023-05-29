import tkinter as tk
import pickle
from enum import Enum

from scheduler.surface_code_layout import tiles

x_len = 9
y_len = 5
border_thickness = 20

tiles_bus = set()
tiles_data = set()
tiles_resource = set()
tiles_magic = set()
tiles_storage = set()
tiles_empty = set()
tiles_all = {}


class TilesType(Enum):
    bus = 0
    data = 1
    resource = 2
    magic = 3
    empty = 4
    storage = 5


class TilesColor(Enum):
    bus = "green"
    data = "blue"
    resource = "purple"
    magic = "red"
    empty = "white"
    storage = "yellow"


tile_set_dict = dict(
    bus=tiles_bus,
    data=tiles_data,
    resource=tiles_resource,
    magic=tiles_magic,
    storage=tiles_storage,
    empty=tiles_empty,
)


def click_to_change_tile_type(coord_x, coord_y):
    # Get the corresponding tile from the
    # coordinate of the clicked button
    tile = tiles_all[(coord_x, coord_y)]

    # Get the current type
    type_current = button_dict[(coord_x, coord_y)]["text"]

    # Get new type index of the tile
    type_new_ind = TilesType[type_current].value + 1
    if type_new_ind >= len(TilesType):
        type_new_ind = 0

    add_to_new_set(type_new_ind, type_current, tile, coord_x, coord_y)


def add_to_new_set(type_new_ind, type_current, tile, coord_x, coord_y):
    # Remove the tile from current set
    tiles_to_remove = tile_set_dict[type_current]
    tiles_to_remove.remove(tile)

    # Get the new tile type from type index
    type_new = TilesType(type_new_ind).name

    # Change the text displayed
    button_dict[(coord_x, coord_y)].configure(
        text=type_new,
        highlightthickness=border_thickness,
        highlightbackground=str(TilesColor[type_new].value),
    )

    # Add the tile to the new set
    tiles_to_add = tile_set_dict[type_new]
    tiles_to_add.add(tile)


def reset():
    # Change the tile type according to the saved variables
    for coord_x in range(y_len):
        for coord_y in range(x_len):
            # Get the corresponding tile from the
            # coordinate of the clicked button
            tile = tiles_all[(coord_x, coord_y)]

            # Current type of tile
            type_current = button_dict[(coord_x, coord_y)]["text"]

            # Get new type of the tile
            type_new_ind = 0

            if TilesType[type_current] != type_new_ind:
                add_to_new_set(type_new_ind, type_current, tile, coord_x, coord_y)


def save():
    layout_tiles_coordinates = [
        frozenset(tiles_bus),
        frozenset(tiles_data),
        frozenset(tiles_resource),
        frozenset(tiles_magic),
        frozenset(tiles_empty),
        frozenset(tiles_storage),
    ]

    # Open a file and use dump()
    with open(
        "./data/inputs/layout_files/sc_bus_wrap.pkl",
        "wb",
    ) as file:
        # A new file will be created
        pickle.dump(layout_tiles_coordinates, file)


def load():
    with open(
        "./data/inputs/layout_files/sc_mixed_no_qubit_turn.pkl",
        "rb",
    ) as p:
        layout_tiles_coordinates = pickle.load(p)

    # Change the tile type according to the saved variables
    for coord_x in range(y_len):
        for coord_y in range(x_len):
            # Get the corresponding tile from the
            # coordinate of the clicked button
            tile = tiles_all[(coord_x, coord_y)]

            # Current type of tile
            type_current = button_dict[(coord_x, coord_y)]["text"]

            # Get new type of the tile
            for tile_set_ind, tile_set in enumerate(layout_tiles_coordinates):
                if tile in tile_set:
                    break
            type_new_ind = tile_set_ind

            if TilesType[type_current] != type_new_ind:
                add_to_new_set(type_new_ind, type_current, tile, coord_x, coord_y)


window = tk.Tk()
button_dict = {}
for i in range(y_len):
    window.rowconfigure(i, weight=1, minsize=50)

    for j in range(x_len):
        window.columnconfigure(j, weight=1, minsize=75)

        frame = tk.Frame(master=window, relief=tk.RAISED, borderwidth=1)
        # Create a Tile object
        current_tile = tiles.Tile(j, -i)

        # Store in the dictionary
        tiles_all[(i, j)] = current_tile

        # Add to the corresponding set
        tiles_bus.add(current_tile)

        frame.grid(row=i, column=j, padx=5, pady=5)
        button_dict[(i, j)] = tk.Button(
            master=frame,
            text="bus",
            height=10,
            width=10,
            highlightbackground="green",
            highlightthickness=border_thickness,
            command=lambda x=i, y=j: click_to_change_tile_type(x, y),
        )
        button_dict[(i, j)].pack(padx=5, pady=5)

window.columnconfigure(0, weight=1, minsize=75)
window.rowconfigure(y_len, weight=1, minsize=50)
frame = tk.Frame(master=window, relief=tk.RAISED, borderwidth=1)
frame.grid(row=y_len, column=0, padx=5, pady=5)
btn_open = tk.Button(frame, text="Load", command=load)
btn_open.pack()

window.columnconfigure(1, weight=1, minsize=75)
window.rowconfigure(y_len, weight=1, minsize=50)
frame = tk.Frame(master=window, relief=tk.RAISED, borderwidth=1)
frame.grid(row=y_len, column=1, padx=5, pady=5)
btn_save = tk.Button(frame, text="Save", command=save)
btn_save.pack()

window.columnconfigure(2, weight=1, minsize=75)
window.rowconfigure(y_len, weight=1, minsize=50)
frame = tk.Frame(master=window, relief=tk.RAISED, borderwidth=1)
frame.grid(row=y_len, column=2, padx=5, pady=5)
btn_reset = tk.Button(frame, text="Reset", command=reset)
btn_reset.pack()

window.mainloop()
