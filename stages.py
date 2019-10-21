from enum import Enum

class Stages(Enum):
    MENU = 'menu'
    ADLIST = 'advlist'
    AD_CONFIRM = 'ad_confirm'
    AD_TYPE_SELECT = 'ad_type_select'
    REGION_SELECT = 'region_select'
    BRAND_SELECTION = 'brand_selection'
    SHOE_NAME_SELECTION = 'shoe_name_selection'
    NUMBER_SELECTION = 'number_selection'
    CONDITION_SELECTION = 'condition_selection'
    PRICE_SELECTION = 'price_selection'
    PHOTO_INSERTION = 'photo_insertion'
    NOTE_INSERT = 'note_insert'
    NOTE_INSERT_REQ = 'note_insert_req'
    AD_INSERT = 'ad_insert'
    DELETE_AD = 'delete_ad'
