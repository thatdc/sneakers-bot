from telegram import KeyboardButton

CONDITIONS = ['DSWT', 'VNDS', '9/10', '8/10', '7/10', '6/10', '5/10', '4/10', '3/10', '2/10', '1/10']
REGIONS = ['Abruzzo', 'Basilicata', 'Calabria', 'Campania', 'Emilia-Romagna', 'Friuli-Venezia Giulia', 'Lazio', 'Liguria',
            'Lombardia', 'Marche', 'Molise', 'Piemonte', 'Puglia', 'Sardegna', 'Sicilia', 'Toscana', 'Trentino-Alto Adige', 
            'Umbria', 'Valle d\'Aosta', 'Veneto']
BRANDS = ['Adidas', 'Jordan', 'Nike', 'Altro']
BOOL_CHOICE = ['SI', 'NO']

def generate_sizes():
    size = 4
    ndx = 0
    kb = []
    buttons = []
    while size <= 17:
        buttons.append(KeyboardButton(str(size)))
        ndx = ndx + 1
        size = size + 0.5
        if (ndx == 4):
            kb.append(buttons)
            buttons = []
            ndx = 0
    if ndx != 0:
        kb.append(buttons)

    return kb

def generate_kb(array, row_lenght):
    kb = []
    buttons = []
    ndx = 0
    for el in array:
        buttons.append(KeyboardButton(str(el)))
        ndx = ndx + 1
        if ndx == row_lenght:
            kb.append(buttons)
            buttons = []
            ndx = 0
    if ndx != 0:
        kb.append(buttons)
    return kb

def generate_conditions():
    return generate_kb(CONDITIONS, 4)

def generate_regions():
    return generate_kb(REGIONS, 3)

def generate_brands():
    return generate_kb(BRANDS, 3)

def generate_bool_choice():
    return generate_kb(BOOL_CHOICE, 2)