DEBUG = False

#######################################################################
# Config values you *must* change
#######################################################################

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'localwiki',
        'USER': 'localwiki',
        'PASSWORD': '{{ postgres_db_pass }}',
        'HOST': '127.0.0.1',
    }
}

# Get an API key at http://cloudmade.com/start.
CLOUDMADE_API_KEY = 'XXX'

# For testing, you can start the python debugging smtp server like so:
# sudo python -m smtpd -n -c DebuggingServer localhost:25
EMAIL_HOST = 'localhost'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 25
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'dontreply@localwiki.net'

#######################################################################
# Other config values.
#######################################################################

SITE_THEME = 'sapling'

OLWIDGET_DEFAULT_OPTIONS = {
    'default_lat': 37,
    'default_lon': -99,
    'default_zoom': 3,
    'zoom_to_data_extent_min': 16,

    'layers': ['cachedcloudmade', 've.aerial'],
    'map_options': {
        'controls': ['Navigation', 'PanZoom', 'KeyboardDefaults'],
        'theme': '/static/openlayers/theme/sapling/style.css',
    },
    'overlay_style': {'fillColor': '#ffc868',
                      'strokeColor': '#db9e33',
                      'strokeDashstyle': 'solid'},
    'map_div_class': 'mapwidget',
}

OLWIDGET_CUSTOM_LAYER_TYPES = {
    'cachedcloudmade': """OpenLayers.Layer.CachedCloudMade('CachedCloudMade',
            ['//map-a.localwiki.org/tile/ca694687020d468283a545db191bcb81/35165/256/',
             '//map-b.localwiki.org/tile/ca694687020d468283a545db191bcb81/35165/256/',
             '//map-c.localwiki.org/tile/ca694687020d468283a545db191bcb81/35165/256/'])""",
}

DAISYDIFF_URL = 'http://localhost:8080/daisydiff/diff'
DAISYDIFF_MERGE_URL = 'http://localhost:8080/daisydiff/merge'

# list of regular expressions for white listing embedded URLs
EMBED_ALLOWED_SRC = ['.*']

HAYSTACK_SOLR_URL = 'http://localhost:8080/solr/'

LOCAL_INSTALLED_APPS = (
)

POSTGIS_VERSION = (2, 0, 3)

# cache settings
CACHE_MIDDLEWARE_SECONDS = 60
CACHE_MIDDLEWARE_KEY_PREFIX = ''
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'KEY_PREFIX': '',
	    'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60,
    }
}

SECRET_KEY = '{{ django_secret_key }}'

SENTRY_REMOTE_URL = 'https://errors.localwiki.org/sentry/store/'
SENTRY_KEY = '{{ sentry_key }}'