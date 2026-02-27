"""
API
"""
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
CONST_EXCLUDED_VENDOR_IDS = {'22', }
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
CONST_ALL_AVAILABILITY_OPTIONS = {'available_immediately', 'available', 'limited_stock', 'unavailable'}
CONST_AVAILABLE_OPTIONS = {'available_immediately', 'available', 'limited_stock'}
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

"""
SUPABASE
"""

CONST_DB_PRODUCT_EVENT_TYPES = {'ADDED', 'REMOVED', 'PRICE', 'AVAILABILITY'}
CONST_DB_VENDOR_EVENT_TYPES = {
    'VENDOR_ADDED', 'VENDOR_REMOVED', 'SHIPPING_OPTION_ADDED', 'SHIPPING_OPTION_REMOVED', 'SHIPPING_PRICE_CHANGED',
    'LOCATION_CHANGED'
}
# CONST_DB_PRODUCT_AVAILABILITY_STATUS = {'AVAILABLE_IMMEDIATELY', 'AVAILABLE', 'LIMITED_STOCK', 'UNAVAILABLE'}
CONST_SHIPPING_OPTIONS_KEYS = {'STANDARD', 'EXPRESS', 'LOCAL'}  # This is omitting 'pickup'
CONST_VENDOR_EVENT_TYPES_FOR_UPDATES = {
    'VENDOR_ADDED', 'LOCATION_CHANGED'
}  # This is obviously not maintainable.

# Supabase table names
CONST_SUPABASE_PRODUCT_LOGS_TABLE = 'product_events'
CONST_SUPABASE_VENDOR_LOGS_TABLE = 'vendor_events'

# Supabase storage filepaths
CONST_SUPABASE_STORAGE = {
    'vendor_id_to_info': {
        'bucket': 'vendor'
    }
}

CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET = 'vendor-id-to-info'
CONST_SUPABASE_INVENTORIES_BUCKET = 'inventories'
CONST_SUPABASE_PID_TO_INFO_BUCKET = 'pid-to-info'

CONST_SUPABASE_VENDOR_ID_TO_INFO_FP = 'vendor_id_to_info.json'
CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP = 'vendor_id_to_offers.json'
CONST_SUPABASE_PID_TO_VENDOR_OFFERS_FP = 'pid_to_vendor_offers.json'
CONST_SUPABASE_PID_TO_INFO_FP = 'pid_to_info.json'
