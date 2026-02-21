CONST_BASE_API_PRODUCT_REQUEST_URL = 'https://www.cannaleo.de/api/products'
CONST_VENDORS_INFORMATION_URL = 'https://cannaleo.de/api/v1/views/pharmacies'
CONST_BASE_TELEMEDICINE_PROVIDERS_API_REQUEST_URL = 'https://cannaleo.de/api/v1/views/tele_med_configurator/'
CONST_FLOWZZ_PRODUCT_URL = 'https://flowzz.com/api/raitings/'
CONST_FLOWZZ_LINK = 'https://flowzz.com/product/'
CONST_PAGE_SIZE_LIMIT = 50
CONST_ALL_ATTRIBUTES = {
    'id', 'url', 'producer', 'name', 'thc', 'cbd', 'genetic', 'irradiated', 'origin', 'created_at', 'updated_at',
    'published_at', 'created_by_id', 'updated_by_id', 'lokale', 'description', 'top_rating', 'dominance', 'strain_name',
    'producer_name', 'min_price', 'max_price', 'availibility', 'price'
}  # Does not include image
# TODO: This fucking thing has to go
CONST_ALL_VENDOR_IDS = {
    '394', '331', '162', '207', '132', '157', '119', '290', '91', '70', '88', '211', '312', '399', '400', '285', '131',
    '333', '402', '54', '236', '144', '151', '188', '278', '318', '108', '418', '149', '471', '433', '179', '195',
    '385', '175', '133', '329', '102', '158', '180', '198', '106', '283', '387', '330', '223', '39', '33', '268', '373',
    '204', '118', '100', '216', '430', '302', '101', '335', '322', '73', '94', '414', '52', '135', '178', '438', '426',
    '344', '305', '311', '354', '386', '388', '166', '237', '420', '224', '279', '194', '298', '235', '251', '415',
    '230', '183', '160', '222', '277', '297', '212', '326', '74', '411', '234', '110', '214', '249', '395', '229',
    '242', '396', '258', '281', '366', '413', '306', '362', '80', '323', '355', '191', '435', '416', '35', '225', '446',
    '76', '127', '193', '356', '57', '122', '321', '303', '170', '350', '376', '202', '155', '78', '361', '291', '304',
    '116', '421', '8', '351', '238', '243', '280', '69', '134', '295', '53', '228', '332', '427', '192', '348', '187',
    '37', '181', '299', '286', '245', '85', '68', '141', '407', '215', '247', '320', '159', '374', '391', '358', '146',
    '255', '139', '184', '417', '256', '182', '23', '360', '441', '115', '129', '60', '254', '276', '244', '307', '454',
    '412', '209', '442', '186', '294', '465', '419', '445', '383', '248', '169', '79', '189', '250', '405', '436',
    '120', '393', '56', '252', '270', '177', '434', '153', '431', '363', '156', '274', '443', '59', '375', '145', '432',
    '282', '233'
}
CONST_EXCLUDED_VENDOR_IDS = {'22', '499', }
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
CONST_AVAILABILITY_DB_MAP: dict[int, str] = {
    1: 'available_immediately',
    2: 'available',
    3: 'limited_stock',
    4: 'unavailable'
}
CONST_NEW_AVAILABILITY_OPTIONS = {'available_immediately', 'available', 'limited_stock', 'unavailable'}
CONST_AVAILABILITY_OPTIONS = {'available_immediately', 'available', 'limited_stock'}
CONST_STRAIN_TYPES = {'Hybrid', 'Indica', 'Sativa', 'Indica_dominant', 'Sativa_dominant', 'Pure Indica'}
CONST_STRAIN_TYPE_NORMALIZATION_MAP = {
    ('Hybrid', None): 'Hybrid',
    ('Hybrid', 'Indica'): 'Indica_dominant',
    ('Hybrid', 'Sativa'): 'Sativa_dominant',
    ('Indica', None): 'Indica',
    ('Sativa', None): 'Sativa',

    # These don't make sense
    ('Indica', 'Indica'): 'Pure Indica',
    ('Sativa', 'Indica'): 'Indica_dominant',
    (None, 'Sativa'): 'Sativa_dominant',
    ('hybrid', None): 'Hybrid'
}
CONST_DB_PRODUCT_EVENT_TYPES = {'ADDED', 'REMOVED', 'PRICE', 'AVAILABILITY'}
CONST_DB_VENDOR_EVENT_TYPES = {
    'VENDOR_ADDED', 'VENDOR_REMOVED', 'SHIPPING_OPTION_ADDED', 'SHIPPING_OPTION_REMOVED', 'SHIPPING_PRICE_CHANGED',
    'LOCATION_CHANGED'
}
# CONST_DB_PRODUCT_AVAILABILITY_STATUS = {'AVAILABLE_IMMEDIATELY', 'AVAILABLE', 'LIMITED_STOCK', 'UNAVAILABLE'}
CONST_SHIPPING_OPTIONS_KEYS = {'standard', 'express', 'local'}  # This is omitting 'pickup'
CONST_DB_TABLES = {'product_events', 'vendor_events'}
CONST_VENDOR_EVENT_TYPES_FOR_UPDATES = {
    'VENDOR_ADDED', 'LOCATION_CHANGED'
}  # This is obviously not maintainable.
CONST_SUPABASE_VENDORS_FILE_PATH = 'vendors_information.json'
CONST_SUPABASE_VENDOR_INVENTORIES_FILE_PATH = 'vendors_inventories.json'