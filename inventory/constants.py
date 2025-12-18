# TODO: Split these up into multiple files, depending on the category

CONST_BASE_API_PRODUCT_REQUEST_URL = 'https://www.cannaleo.de/api/products'
CONST_VENDORS_INFORMATION_URL = 'https://cannaleo.de/api/v1/views/pharmacies'
CONST_BASE_TELEMEDICINE_PROVIDERS_API_REQUEST_URL = 'https://cannaleo.de/api/v1/views/tele_med_configurator/'
CONST_PAGE_SIZE_LIMIT = 50
CONST_ALL_ATTRIBUTES = {
    'id', 'url', 'producer', 'name', 'thc', 'cbd', 'genetic', 'irradiated', 'origin', 'created_at', 'updated_at',
    'published_at', 'created_by_id', 'updated_by_id', 'lokale', 'description', 'top_rating', 'dominance', 'strain_name',
    'producer_name', 'min_price', 'max_price', 'availibility', 'price'
}  # Does not include image
CONST_ALL_VENDOR_IDS = {
    '8', '52', '54', '57', '76', '53', '56', '37', '59', '60', '39', '73', '68', '69', '70', '78', '74', '23', '80',
    '79', '94', '85', '88', '35', '91', '33', '100', '101', '102', '106', '108', '110', '115', '116', '118', '119',
    '120', '122', '127', '129', '131', '132', '133', '134', '135', '139', '141', '144', '145', '146', '151', '153',
    '155', '156', '157', '158', '159', '160', '162', '166', '169', '175', '177', '178', '179', '180', '181', '182',
    '183', '184', '186', '187', '188', '189', '191', '192', '193', '194', '195', '198', '202', '204', '207', '209',
    '211', '212', '214', '215', '216', '222', '223', '224', '225', '229', '230', '233', '234', '235', '236', '238',
    '242', '243', '244', '245', '247', '248', '249', '250', '251', '252', '254', '255', '256', '258', '268', '270',
    '274', '276', '277', '278', '279', '280', '281', '282', '283', '285', '286', '290', '291', '294', '295', '297',
    '298', '299', '302', '303', '304', '305', '306', '307', '311', '312', '318', '320', '321', '322', '323', '326',
    '329', '330', '331', '332', '333', '335', '344', '348', '350', '351', '354', '355', '356', '358', '360', '361',
    '362', '363', '366', '373', '374', '375', '376', '383', '385', '386', '387', '388', '391', '393', '394', '395',
    '396', '399', '400', '402', '405', '411', '412', '413', '414', '415', '417', '418', '419', '420', '421', '426',
    '427', '431', '432', '434', '435', '436', '441', '442', '443', '445', '446', '454', '465'
}

CONST_AVAILABILITY_OPTIONS = {
    1, 2, 3, 4
}  # 1 -> sofort lieferbarm 2 -> lieferbar, 3 -> Restbestand, 4 -> nicht lieferbar
CONST_AVAILABLE_OPTIONS = {1, 2, 3}
CONST_DELIVERY_OPTIONS = ['shipping_cost_standard', 'express_cost_standard', 'local_coure_cost_standard']
CONST_TELEMEDICINE_OFFERS_NORMALIZATION_MAP = {
    "erstrezept": "initial",
    "erstgespräch": "initial",
    "behandlungsanfrage": "initial",

    "folgerezept": "followup",
    "folgegespräch": "followup",
    "rezeptanfrage": "followup",
    "wechselgespräch": "followup",

    "kurzer termin": "short_appointment",
    "langer termin": "long_appointment"
}
CONST_ROW_PATTERN = r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
CONST_PRICE_PATTERN = r"(?P<prefix>ab\s*)?(?P<amount>\d{1,3}(?:,\d{2})?)\s*€"
CONST_AVAILABILITY_DB_MAP = {
    1: 'available_immediately',
    2: 'available',
    3: 'limited_stock',
    4: 'unavailable'
}
CONST_NEW_AVAILABILITY_OPTIONS = {'available_immediately', 'available', 'limited_stock', 'unavailable'}
CONST_STRAIN_TYPES = {'Hybrid', 'Indica', 'Sativa', 'Indica_dominant', 'Sativa_dominant'}
CONST_STRAIN_TYPE_NORMALIZATION_MAP = {
    ('Hybrid', None): 'Hybrid',
    ('Hybrid', 'Indica'): 'Indica_dominant',
    ('Hybrid', 'Sativa'): 'Sativa_dominant',
    ('Indica', None): 'Indica',
    ('Sativa', None): 'Sativa',

    # These don't make sense
    ('Indica', 'Indica'): 'Indica',
    ('Sativa', 'Indica'): 'Indica_dominant',
    (None, 'Sativa'): 'Sativa_dominant',
    ('hybrid', None): 'Hybrid'
}

# Sensitive
CONST_SUPABASE_VENDORS_FILE_PATH = 'vendors_information.json'
CONST_SUPABASE_VENDOR_INVENTORIES_FILE_PATH = ''

CONST_PRODUCT_EVENT_TYPES = {'ADDED', 'REMOVED', 'PRICE', 'AVAILABILITY'}
CONST_VENDOR_EVENT_TYPES = {
    'VENDOR_ADDED', 'VENDOR_REMOVED', 'SHIPPING_OPTION_ADDED', 'SHIPPING_OPTION_REMOVED', 'SHIPPING_PRICE_CHANGED',
    'LOCATION_CHANGED'
}
CONST_SHIPPING_OPTIONS_KEYS = {'standard', 'express', 'local'}  # This is omitting 'pickup'
CONST_DB_TABLES = {'product_events', 'vendor_events'}
CONST_VENDOR_EVENT_TYPES_FOR_UPDATES = {
    'VENDOR_ADDED', 'LOCATION_CHANGED'
}  # This is obviously not maintainable.