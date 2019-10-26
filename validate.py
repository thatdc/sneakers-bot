BRANDS = ["jordan", "nike", "adidas", "altro"]
CONDITIONS = ['DSWT', 'VNDS', '9/10', '8/10', '7/10', '6/10', '5/10', '4/10', '3/10', '2/10', '1/10']

def validate_brand(brand_name):
    if brand_name.lower() in BRANDS:
        return True
    else:
        return False

def validate_condition(condition):
    if condition.lower in CONDITIONS:
        return True
    else:
        return False

def validate_size(size):
    pieces = size.split(".")
    try:
        flt = float(size)
        if int(pieces[1]) == 0 or int(pieces[1]) == 5:
            if pieces[0].isdigit():
                return True
            else:
                return False
        else:
            return False
    except ValueError:
        return False
