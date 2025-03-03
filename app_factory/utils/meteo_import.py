import logging.config
import time

import requests
import pandas as pd
import pytz
from datetime import datetime

from os import environ, path
from io import StringIO
from dotenv import load_dotenv

BASE_DIR = path.abspath(path.dirname(__file__))
load_dotenv(path.join(BASE_DIR, ".env"))

APPLICATION_ID = environ.get("APPLICATION_ID")
logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
mylogger = logging.getLogger(__name__)


class Client(object):

    def __init__(self):
        self.session = requests.Session()

    def request(self, method, url, **kwargs):
        # First request will always need to obtain a token first
        if 'Authorization' not in self.session.headers:
            self.obtain_token()

        # Optimistically attempt to dispatch request
        response = self.session.request(method, url, **kwargs)
        if self.token_has_expired(response):
            # We got an 'Access token expired' response => refresh token
            self.obtain_token()
            # Re-dispatch the request that previously failed
            response = self.session.request(method, url, **kwargs)

        return response

    def token_has_expired(self, response):
        status = response.status_code
        content_type = response.headers['Content-Type']
        repJson = response.text
        if status == 401 and 'application/json' in content_type:
            repJson = response.text
            if 'Invalid JWT token' in repJson['description']:
                return True
        return False

    def obtain_token(self):
        # Obtain new token
        data = {'grant_type': 'client_credentials'}
        headers = {'Authorization': 'Basic ' + APPLICATION_ID}

        access_token_response = requests.post("https://portail-api.meteofrance.fr/token", data=data, verify=False,
                                              allow_redirects=False,
                                              headers=headers)
        token = access_token_response.json()['access_token']
        # Update session with fresh token
        self.session.headers.update({'Authorization': 'Bearer %s' % token})


def get_meteo():
    id_stations = [92073001, 78481001, 94042001, 93050001, 94068001, 91027002, 91275001, 78640001, 77468001, 95088001,95527001, 75106001, 75107005, 75110001, 75114001, 75114007, 75116008, 75114001]

    client = Client()

    df = pd.DataFrame({
        'paris_time': pd.Series(dtype='datetime64[ns, Europe/Paris]'),
        'rr_per': pd.Series(dtype='float'),
        'id_station': pd.Series(dtype='str'),
        'cum_6h': pd.Series(dtype='float')
    })

    for id in id_stations:
        url = f'https://public-api.meteofrance.fr/public/DPPaquetObs/v1/paquet/infrahoraire-6m?id_station={id}&format=json'
        response = client.request('GET', url=url, verify=False)
        try:
            dfi = transform_meteo_response(response, id)
        except Exception:
            df = df
        else:

            df = pd.concat([df, dfi], axis=0)

    return pd.DataFrame(df)


def transform_meteo_response(response, id_station):
    dfi = pd.DataFrame(response.json())

    dfi['reference_time'] = pd.to_datetime(dfi['reference_time'])
    if dfi['reference_time'].duplicated().sum() > 0:
        dfi = dfi[~dfi.reference_time.duplicated(keep='first')]

    paris_tz = pytz.timezone('Europe/Paris')
    dfi['paris_time'] = dfi['reference_time'].dt.tz_convert(paris_tz)

    dfi.set_index('paris_time', inplace=True)
    dfi.sort_index(ascending=True, inplace=True)

    dfi['cum_6h'] = dfi['rr_per'].rolling(window='6h').sum()
    dfi['id_station'] = str(id_station)
    dfi.reset_index(inplace=True)
    dfi = dfi[['id_station', 'paris_time', 'rr_per', 'cum_6h']]
    return dfi


def get_climato(ti, tf, id_stations):
    ti = datetime.strptime(ti, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%SZ')
    tf = datetime.strptime(tf, '%Y-%m-%d').strftime('%Y-%m-%dT23:59:59Z')

    client = Client()

    df = pd.DataFrame({
        'paris_time': pd.Series(dtype='datetime64[ns, Europe/Paris]'),
        'RR1': pd.Series(dtype='float'),
        'id_station': pd.Series(dtype='str'),
        'cum_6h': pd.Series(dtype='float')
    })

    for id_station in id_stations:

        mylogger.info(f'telechargement des données climatologiques de la station {id_station}')

        try:
            url1 = f'https://public-api.meteofrance.fr/public/DPClim/v1/commande-station/horaire?id-station={id_station}&date-deb-periode={ti}&date-fin-periode={tf}'
            response1 = client.request('GET', url=url1, verify=False)
            id = int(response1.json()['elaboreProduitAvecDemandeResponse']['return'])
            url2 = f'https://public-api.meteofrance.fr/public/DPClim/v1/commande/fichier?id-cmde={id}'
            response2 = client.request('GET', url=url2, verify=False)
            if response2.status_code == 204:
                time.sleep(1)
                response2 = client.request('GET', url=url2, verify=False)

            dfi = transform_climato_response(response2, id_station)

        except Exception:
            df = df
            mylogger.info(f'echec du téléchargement des données climatologiques de la station {id_station}')

        else:
            df = pd.concat([df, dfi], axis=0)

    return df


def transform_climato_response(response, id_station):

    df = pd.read_csv(StringIO(response.text), delimiter=';', encoding='latin1', decimal=",")

    df['DATE'] = pd.to_datetime(df['DATE'], format='%Y%m%d%H', utc=True)
    if df['DATE'].duplicated().sum() > 0:
        df = df[~df.reference_time.duplicated(keep='first')]
    paris_tz = pytz.timezone('Europe/Paris')
    df['paris_time'] = df['DATE'].dt.tz_convert(paris_tz)

    df.set_index('paris_time', inplace=True)
    df.sort_index(ascending=True, inplace=True)
    df['cum_6h'] = df['RR1'].rolling(window='6h').sum()
    df['id_station'] = str(id_station)
    df.reset_index(inplace=True)
    df = df[['id_station', 'paris_time', 'RR1', 'cum_6h']]

    return df
